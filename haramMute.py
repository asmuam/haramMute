import sys
import queue
import argparse
import sounddevice as sd
import numpy as np
import torch
import threading
import warnings
import os
import ctypes
import time
from demucs.pretrained import get_model
from demucs.apply import apply_model

# Mengabaikan warning agar console bersih
warnings.filterwarnings("ignore")

sampleRate = 44100
numChannels = 2

# Global variables untuk pemindahan perangkat output dinamis
vuMeterEnabled = True
activeOutputName = ""
activeOutputHostApi = -1
recreateOutputStreamEvent = threading.Event()
promptActive = False

def loadEnvDefaults():
    defaults = {
        'CHUNK_DURATION': 2.7,
        'BUFFER_SIZE': 3,
        'AUDIO_MODE': 'vocals',
        'V2_CHUNK_DURATION': 0.3
    }
    envPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(envPath):
        try:
            with open(envPath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                            val = val[1:-1]
                        if key in defaults:
                            if key in ('CHUNK_DURATION', 'V2_CHUNK_DURATION'):
                                defaults[key] = float(val)
                            elif key == 'BUFFER_SIZE':
                                defaults[key] = int(val)
                            else:
                                defaults[key] = val
        except Exception as e:
            print(f"[!] Gagal membaca .env: {e}")
    return defaults

def findDeviceIdx(name, hostapi):
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['name'] == name and dev['hostapi'] == hostapi:
                return i
    except:
        pass
    return None

def promptNewDevice(deviceName, deviceHostApi):
    global vuMeterEnabled, activeOutputName, activeOutputHostApi, recreateOutputStreamEvent
    
    vuMeterEnabled = False
    time.sleep(0.2)  # Menunggu print VU meter yang sedang berjalan selesai
    
    print(f"\n\n[!] Perangkat output baru terdeteksi: {deviceName}")
    sys.stdout.write("[?] Gunakan perangkat baru ini? (y/n, default n): ")
    sys.stdout.flush()
    
    try:
        userChoice = sys.stdin.readline().strip().lower()
    except Exception:
        userChoice = 'n'
        
    if userChoice.startswith('y'):
        activeOutputName = deviceName
        activeOutputHostApi = deviceHostApi
        recreateOutputStreamEvent.set()
        print(f"[+] Beralih ke output baru: {deviceName}\n")
    else:
        print("[+] Tetap menggunakan output saat ini.\n")
        
    vuMeterEnabled = True

def checkAndPromptDevice(deviceName, deviceHostApi):
    global promptActive
    if promptActive:
        return
    promptActive = True
    try:
        promptNewDevice(deviceName, deviceHostApi)
    finally:
        promptActive = False

def deviceMonitorLoop():
    global activeOutputName, activeOutputHostApi, recreateOutputStreamEvent
    
    try:
        initialDevices = sd.query_devices()
        knownDevices = {(d['name'], d['hostapi']) for d in initialDevices if d['max_output_channels'] > 0}
    except Exception:
        knownDevices = set()
        
    while True:
        time.sleep(2.0)
        
        try:
            currentDevices = sd.query_devices()
        except Exception:
            continue
            
        currentOutputDevices = [d for d in currentDevices if d['max_output_channels'] > 0]
        currentOutputSet = {(d['name'], d['hostapi']) for d in currentOutputDevices}
        
        # 1. Cek jika perangkat output aktif terputus
        activeIdx = findDeviceIdx(activeOutputName, activeOutputHostApi)
        if activeIdx is None:
            try:
                defaultOutputIdx = sd.default.device[1]
                defaultDev = sd.query_devices(defaultOutputIdx)
                if defaultDev['max_output_channels'] > 0:
                    activeOutputName = defaultDev['name']
                    activeOutputHostApi = defaultDev['hostapi']
                else:
                    if currentOutputDevices:
                        activeOutputName = currentOutputDevices[0]['name']
                        activeOutputHostApi = currentOutputDevices[0]['hostapi']
            except Exception:
                if currentOutputDevices:
                    activeOutputName = currentOutputDevices[0]['name']
                    activeOutputHostApi = currentOutputDevices[0]['hostapi']
            
            print(f"\n[!] Perangkat output aktif terputus! Beralih otomatis ke: {activeOutputName}")
            recreateOutputStreamEvent.set()
            
        # 2. Cek jika ada perangkat output baru yang terhubung
        newDevices = currentOutputSet - knownDevices
        if newDevices and not promptActive:
            for d in currentOutputDevices:
                if (d['name'], d['hostapi']) in newDevices:
                    threading.Thread(
                        target=checkAndPromptDevice,
                        args=(d['name'], d['hostapi']),
                        daemon=True
                    ).start()
                    break
                    
        knownDevices = currentOutputSet

def getDeviceIndices():
    devices = sd.query_devices()
    inputIdx = None
    outputIdx = None
    
    print("\n--- DAFTAR PERANGKAT AUDIO ---")
    for i, dev in enumerate(devices):
        print(f"[{i}] {dev['name']} (In: {dev['max_input_channels']}, Out: {dev['max_output_channels']})")

    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and 'CABLE Output' in dev['name']:
            inputIdx = i
            break
            
    if inputIdx is None:
        try: inputIdx = int(input("\nMasukkan ID Input (CABLE Output): "))
        except: sys.exit(1)
            
    outputIdx = sd.default.device[1]
    print(f"\n-> INPUT : [{inputIdx}] {devices[inputIdx]['name']}")
    print(f"-> OUTPUT: [{outputIdx}] {devices[outputIdx]['name']}\n")
    return inputIdx, outputIdx

def printVUMeter(data, prefix=""):
    if not vuMeterEnabled:
        return
    rms = np.sqrt(np.mean(data**2))
    meter = int(rms * 50)
    bar = "█" * meter + "-" * (50 - meter)
    sys.stdout.write(f"\r{prefix} |{bar}| {rms:.4f} ")
    sys.stdout.flush()

def processAudio(chunkDuration, bufferSize, audioMode):
    print("Memuat model AI Demucs (Optimized)...")
    model = get_model('htdemucs')
    model.eval()
    
    deviceType = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Komputasi: {deviceType.upper()}")
    
    if deviceType == "cpu":
        try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
        except: pass
        torch.set_num_threads(8)
        torch.set_num_interop_threads(1)
        torch.set_flush_denormal(True)
        
    model.to(deviceType)
    if deviceType == "cuda": model.half()
    
    try: vocalIdx = model.sources.index('vocals')
    except: vocalIdx = 3
    otherIndices = [i for i, name in enumerate(model.sources) if name != 'vocals']
        
    global activeOutputName, activeOutputHostApi
    inputIdx, outputIdx = getDeviceIndices()
    
    devices = sd.query_devices()
    activeOutputName = devices[outputIdx]['name']
    activeOutputHostApi = devices[outputIdx]['hostapi']
    
    # Memulai background monitor thread
    monitorThread = threading.Thread(target=deviceMonitorLoop, daemon=True)
    monitorThread.start()
    
    chunkSamples = int(chunkDuration * sampleRate)
    audioQueue = queue.Queue(maxsize=bufferSize)
    
    def audioCallback(indata, frames, time, status):
        try: audioQueue.put_nowait(indata.copy())
        except queue.Full:
            try: audioQueue.get_nowait(); audioQueue.put_nowait(indata.copy())
            except: pass
        
    print(f"\n[+] LIVE STREAMING ({audioMode.upper()}) - Chunk: {chunkDuration}s")
    
    outQueue = queue.Queue()
    def outputWorker(stream, stopEvent):
        while not stopEvent.is_set():
            try:
                data = outQueue.get(timeout=0.2)
                if data is None:
                    break
                try:
                    stream.write(data)
                except Exception as e:
                    print(f"\n[-] Error menulis ke output: {e}")
                    recreateOutputStreamEvent.set()
                    break
            except queue.Empty:
                continue
    
    try:
        with sd.InputStream(device=inputIdx, channels=numChannels, samplerate=sampleRate, blocksize=chunkSamples, callback=audioCallback):
            while True:
                # Dapatkan indeks perangkat aktif saat ini (karena indeks bisa bergeser ketika ada cabut/colok)
                currentOutputIdx = findDeviceIdx(activeOutputName, activeOutputHostApi)
                if currentOutputIdx is None:
                    # Fallback jika tidak ditemukan
                    try:
                        defaultIdx = sd.default.device[1]
                        currentOutputIdx = defaultIdx
                        activeOutputName = sd.query_devices(defaultIdx)['name']
                        activeOutputHostApi = sd.query_devices(defaultIdx)['hostapi']
                    except Exception:
                        pass
                
                if currentOutputIdx is None:
                    print("\n[-] Tidak ada perangkat output yang tersedia. Menunggu...")
                    time.sleep(2.0)
                    continue
                
                try:
                    with sd.OutputStream(device=currentOutputIdx, channels=numChannels, samplerate=sampleRate) as outStream:
                        recreateOutputStreamEvent.clear()
                        outWorkerStopEvent = threading.Event()
                        
                        playThread = threading.Thread(
                            target=outputWorker, 
                            args=(outStream, outWorkerStopEvent), 
                            daemon=True
                        )
                        playThread.start()
                        
                        while not recreateOutputStreamEvent.is_set():
                            try:
                                chunkData = audioQueue.get(timeout=0.5)
                            except queue.Empty:
                                continue
                                
                            wavTensor = torch.tensor(chunkData.T, dtype=torch.float32).unsqueeze(0).to(deviceType)
                            
                            if deviceType == "cuda":
                                wavTensor = wavTensor.half()

                            with torch.no_grad():
                                # Set overlap=0 agar tidak ada redundansi kalkulasi
                                sources = apply_model(model, wavTensor, shifts=0, split=False, progress=False, overlap=0)
                                
                            if audioMode == 'vocals': outTensor = sources[0, vocalIdx]
                            else: outTensor = sources[0, otherIndices].sum(dim=0)
                            
                            outChunk = np.ascontiguousarray(outTensor.cpu().float().numpy().T)
                            printVUMeter(outChunk, prefix="AUDIO")
                            outQueue.put(outChunk)
                            
                        # Berhenti dari loop perangkat, stop thread playback lama
                        outWorkerStopEvent.set()
                        outQueue.put(None)
                        playThread.join(timeout=1.0)
                        
                except Exception as streamError:
                    print(f"\n[-] Gagal membuka/menjalankan output stream: {streamError}")
                    time.sleep(1.0)
                    
    except KeyboardInterrupt: print("\n\n[+] Berhenti.")
    except Exception as err: print(f"\n\n[-] Error: {err}")

if __name__ == "__main__":
    envDefaults = loadEnvDefaults()
    
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="HaramMute - Pemisah Vokal & Instrumen Real-Time menggunakan AI Demucs")
        parser.add_argument("-c", "--chunk", type=float, default=envDefaults['CHUNK_DURATION'], help=f"Durasi potongan audio dalam detik (default: {envDefaults['CHUNK_DURATION']})")
        parser.add_argument("-b", "--buffer", type=int, default=envDefaults['BUFFER_SIZE'], help=f"Kapasitas maksimal antrean buffer (default: {envDefaults['BUFFER_SIZE']})")
        parser.add_argument("-m", "--mode", choices=['vocals', 'instrumental'], default=envDefaults['AUDIO_MODE'], help=f"Mode output suara (default: {envDefaults['AUDIO_MODE']})")
        parser.add_argument("--env", action="store_true", help="Gunakan parameter default dari file .env tanpa menu interaktif")
        args = parser.parse_args()
        chunkDuration = args.chunk
        bufferSize = args.buffer
        audioMode = args.mode
    else:
        print("=== MENU KONFIGURASI ===")
        print("[-] Chunk Duration : Durasi potongan audio (detik). Kecil = minim delay; Besar = lebih stabil.")
        try:
            chunkInput = input(f"    Masukkan Chunk Duration (detik, default {envDefaults['CHUNK_DURATION']}): ").strip()
            chunkDuration = float(chunkInput) if chunkInput else envDefaults['CHUNK_DURATION']
        except ValueError:
            print(f"    [!] Input tidak valid, menggunakan default: {envDefaults['CHUNK_DURATION']}")
            chunkDuration = envDefaults['CHUNK_DURATION']
            
        print("[-] Buffer Size    : Batas antrean audio. Kecil (1-3) = real-time; Besar = mencegah putus-putus tetapi menumpuk delay.")
        try:
            bufferInput = input(f"    Masukkan Buffer Size (default {envDefaults['BUFFER_SIZE']}): ").strip()
            bufferSize = int(bufferInput) if bufferInput else envDefaults['BUFFER_SIZE']
        except ValueError:
            print(f"    [!] Input tidak valid, menggunakan default: {envDefaults['BUFFER_SIZE']}")
            bufferSize = envDefaults['BUFFER_SIZE']
            
        print(f"[-] Mode           : Tipe audio ('vocals' [v] atau 'instrumental' [i], default {envDefaults['AUDIO_MODE']}).")
        modeInput = input(f"    Masukkan Mode (v/i/vocals/instrumental, default {envDefaults['AUDIO_MODE']}): ").strip().lower()
        if modeInput.startswith('v'):
            audioMode = 'vocals'
        elif modeInput.startswith('i'):
            audioMode = 'instrumental'
        else:
            if modeInput:
                print(f"    [!] Input tidak valid, menggunakan default: {envDefaults['AUDIO_MODE']}")
            audioMode = envDefaults['AUDIO_MODE']
            
    processAudio(chunkDuration=chunkDuration, bufferSize=bufferSize, audioMode=audioMode)