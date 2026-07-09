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
import subprocess
from demucs.pretrained import get_model
from demucs.apply import apply_model

# Mengabaikan warning
warnings.filterwarnings("ignore")

sampleRate = 44100
numChannels = 2

# Global variables untuk pemindahan perangkat output dinamis
vuMeterEnabled = True
activeInputName = ""
activeInputHostApi = -1
activeOutputName = ""
activeOutputHostApi = -1
recreateOutputStreamEvent = threading.Event()

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

def getSystemSoundDevices():
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output('wmic path Win32_SoundDevice get Name', startupinfo=startupinfo, timeout=2.0)
        lines = out.decode('utf-8', errors='ignore').splitlines()
        devices = []
        for line in lines[1:]:
            line = line.strip()
            if line and line.lower() != 'name':
                devices.append(line)
        return set(devices)
    except:
        return set()

def deviceMonitorLoop():
    global activeOutputName, recreateOutputStreamEvent
    
    knownWmiDevices = getSystemSoundDevices()
    
    while True:
        time.sleep(2.0)
        
        currentWmiDevices = getSystemSoundDevices()
        if not currentWmiDevices:
            continue
            
        # 1. Cek jika perangkat output aktif terputus dari sistem (WMI)
        activePresent = False
        if activeOutputName == "":
            activePresent = True
        else:
            for d in currentWmiDevices:
                if d.lower() in activeOutputName.lower() or activeOutputName.lower() in d.lower():
                    activePresent = True
                    break
                    
        if not activePresent:
            recreateOutputStreamEvent.set()
            knownWmiDevices = currentWmiDevices
            continue
            
        # 2. Cek jika ada perangkat baru yang terhubung
        newWmi = currentWmiDevices - knownWmiDevices
        if newWmi:
            recreateOutputStreamEvent.set()
            
        knownWmiDevices = currentWmiDevices

def getDeviceIndices():
    devices = sd.query_devices()
    inputIdx = None
    
    print("\n[+] Mencari Virtual Audio Cable...")
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and 'CABLE Output' in dev['name']:
            inputIdx = i
            break
            
    if inputIdx is None:
        print("[!] CABLE Output tidak ditemukan otomatis.")
        try: inputIdx = int(input("Masukkan ID Input: "))
        except: sys.exit(1)
            
    outputIdx = sd.default.device[1]
    print(f"-> INPUT : [{inputIdx}] {devices[inputIdx]['name']}")
    print(f"-> OUTPUT: [{outputIdx}] {devices[outputIdx]['name']}\n")
    return inputIdx, outputIdx

def printVUMeter(data):
    if not vuMeterEnabled:
        return
    rms = np.sqrt(np.mean(data**2))
    meter = int(rms * 50)
    bar = "█" * meter + "-" * (50 - meter)
    sys.stdout.write(f"\rVOLUME |{bar}| {rms:.4f} ")
    sys.stdout.flush()

def processAudio(chunkDuration):
    # MENGGUNAKAN MODEL 'hdemucs_mmi'
    # Ini adalah model Demucs V3 yang jauh lebih cepat di CPU
    print(f"Memuat Model Demucs V3 (hdemucs_mmi)...")
    model = get_model('hdemucs_mmi')
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
    
    try: vocalIdx = model.sources.index('vocals')
    except: vocalIdx = 3
        
    global activeOutputName, activeOutputHostApi, activeInputName, activeInputHostApi
    inputIdx, outputIdx = getDeviceIndices()
    
    devices = sd.query_devices()
    activeInputName = devices[inputIdx]['name']
    activeInputHostApi = devices[inputIdx]['hostapi']
    activeOutputName = devices[outputIdx]['name']
    activeOutputHostApi = devices[outputIdx]['hostapi']
    
    # Memulai background monitor thread
    monitorThread = threading.Thread(target=deviceMonitorLoop, daemon=True)
    monitorThread.start()
    
    chunkSamples = int(chunkDuration * sampleRate)
    audioQueue = queue.Queue(maxsize=5)
    
    def audioCallback(indata, frames, time, status):
        try: audioQueue.put_nowait(indata.copy())
        except: pass
        
    print(f"[+] HaramMute V2 AKTIF (Mode V3 Cepat)")
    print(f"[+] Chunk: {chunkDuration}s")
    
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
        knownPortAudioDevices = set()
        
        while True:
            # Re-initialize sounddevice untuk me-refresh cache perangkat keras audio
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass
            
            # Cari indeks perangkat aktif saat ini
            currentInputIdx = findDeviceIdx(activeInputName, activeInputHostApi)
            currentOutputIdx = findDeviceIdx(activeOutputName, activeOutputHostApi)
            
            # Jika perangkat input tidak ditemukan, cari ulang CABLE Output
            if currentInputIdx is None:
                try:
                    devicesList = sd.query_devices()
                    for i, dev in enumerate(devicesList):
                        if dev['max_input_channels'] > 0 and 'CABLE Output' in dev['name']:
                            currentInputIdx = i
                            activeInputName = dev['name']
                            activeInputHostApi = dev['hostapi']
                            break
                except Exception:
                    pass
            
            # Jika perangkat output tidak ditemukan (terputus), fallback ke default
            if currentOutputIdx is None:
                try:
                    defaultIdx = sd.default.device[1]
                    defaultDev = sd.query_devices(defaultIdx)
                    if defaultDev['max_output_channels'] > 0:
                        currentOutputIdx = defaultIdx
                        activeOutputName = defaultDev['name']
                        activeOutputHostApi = defaultDev['hostapi']
                        print(f"\n[!] Perangkat output aktif terputus! Beralih otomatis ke: {activeOutputName}")
                except Exception:
                    pass
                    
            if currentInputIdx is None or currentOutputIdx is None:
                print("\n[-] Perangkat input atau output tidak tersedia. Menunggu...")
                time.sleep(2.0)
                continue
                
            # Deteksi perangkat output baru
            try:
                devicesList = sd.query_devices()
                currentOutputDevices = [d for d in devicesList if d['max_output_channels'] > 0]
                currentOutputSet = {(d['name'], d['hostapi']) for d in currentOutputDevices}
            except Exception:
                currentOutputSet = set()
                currentOutputDevices = []
                
            if knownPortAudioDevices:
                newDevices = currentOutputSet - knownPortAudioDevices
                if newDevices:
                    for d in currentOutputDevices:
                        if (d['name'], d['hostapi']) in newDevices:
                            vuMeterEnabled = False
                            time.sleep(0.2)
                            print(f"\n\n[!] Perangkat output baru terdeteksi: {d['name']}")
                            sys.stdout.write("[?] Gunakan perangkat baru ini? (y/n, default n): ")
                            sys.stdout.flush()
                            try:
                                userChoice = sys.stdin.readline().strip().lower()
                            except Exception:
                                userChoice = 'n'
                                
                            if userChoice.startswith('y'):
                                currentOutputIdx = findDeviceIdx(d['name'], d['hostapi'])
                                if currentOutputIdx is not None:
                                    activeOutputName = d['name']
                                    activeOutputHostApi = d['hostapi']
                                    print(f"[+] Beralih ke output baru: {d['name']}\n")
                            else:
                                print("[+] Tetap menggunakan output saat ini.\n")
                            vuMeterEnabled = True
                            break
                            
            knownPortAudioDevices = currentOutputSet
            
            print(f"\n[+] Membuka streaming:")
            print(f"    INPUT : [{currentInputIdx}] {activeInputName}")
            print(f"    OUTPUT: [{currentOutputIdx}] {activeOutputName}")
            
            try:
                with sd.InputStream(device=currentInputIdx, channels=numChannels, samplerate=sampleRate, blocksize=chunkSamples, callback=audioCallback):
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
                            
                            with torch.no_grad():
                                # Shifts=0 dan Overlap=0 untuk performa maksimal
                                sources = apply_model(model, wavTensor, shifts=0, split=False, progress=False, overlap=0)
                                
                            outTensor = sources[0, vocalIdx]
                            outChunk = np.ascontiguousarray(outTensor.cpu().float().numpy().T)
                            
                            printVUMeter(outChunk)
                            outQueue.put(outChunk)
                            
                        # Berhenti dari loop perangkat, stop thread playback lama
                        outWorkerStopEvent.set()
                        outQueue.put(None)
                        playThread.join(timeout=1.0)
                        
            except Exception as streamError:
                print(f"\n[-] Gagal membuka/menjalankan stream audio: {streamError}")
                time.sleep(2.0)
                    
    except KeyboardInterrupt: print("\n\n[+] Berhenti.")
    except Exception as err: print(f"\n\n[-] Error: {err}")

if __name__ == "__main__":
    envDefaults = loadEnvDefaults()
    
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="HaramMute V2 - Pemisah Vokal Real-Time (Model Light Cepat)")
        parser.add_argument("-c", "--chunk", type=float, default=envDefaults['V2_CHUNK_DURATION'], help=f"Durasi potongan audio dalam detik (default: {envDefaults['V2_CHUNK_DURATION']})")
        parser.add_argument("--env", action="store_true", help="Gunakan parameter default dari file .env tanpa menu interaktif")
        args = parser.parse_args()
        chunkDuration = args.chunk
    else:
        print("=== MENU KONFIGURASI ===")
        print("[-] Chunk Duration : Durasi potongan audio (detik). Kecil = minim delay; Besar = lebih stabil.")
        try:
            chunkInput = input(f"    Masukkan Chunk Duration (detik, default {envDefaults['V2_CHUNK_DURATION']}): ").strip()
            chunkDuration = float(chunkInput) if chunkInput else envDefaults['V2_CHUNK_DURATION']
        except ValueError:
            print(f"    [!] Input tidak valid, menggunakan default: {envDefaults['V2_CHUNK_DURATION']}")
            chunkDuration = envDefaults['V2_CHUNK_DURATION']
            
    processAudio(chunkDuration=chunkDuration)
