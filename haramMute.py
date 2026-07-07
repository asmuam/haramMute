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
from demucs.pretrained import get_model
from demucs.apply import apply_model

# Mengabaikan warning agar console bersih
warnings.filterwarnings("ignore")

sampleRate = 44100
numChannels = 2

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
        
    inputIdx, outputIdx = getDeviceIndices()
    chunkSamples = int(chunkDuration * sampleRate)
    audioQueue = queue.Queue(maxsize=bufferSize)
    
    def audioCallback(indata, frames, time, status):
        try: audioQueue.put_nowait(indata.copy())
        except queue.Full:
            try: audioQueue.get_nowait(); audioQueue.put_nowait(indata.copy())
            except: pass
        
    print(f"\n[+] LIVE STREAMING ({audioMode.upper()}) - Chunk: {chunkDuration}s")
    
    outQueue = queue.Queue()
    def outputWorker(stream):
        while True:
            data = outQueue.get()
            if data is None: break
            stream.write(data)
    
    try:
        with sd.InputStream(device=inputIdx, channels=numChannels, samplerate=sampleRate, blocksize=chunkSamples, callback=audioCallback):
            with sd.OutputStream(device=outputIdx, channels=numChannels, samplerate=sampleRate) as outStream:
                playThread = threading.Thread(target=outputWorker, args=(outStream,), daemon=True)
                playThread.start()
                
                while True:
                    chunkData = audioQueue.get()
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
                    
    except KeyboardInterrupt: print("\n\n[+] Berhenti.")
    except Exception as err: print(f"\n\n[-] Error: {err}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="HaramMute - Pemisah Vokal & Instrumen Real-Time menggunakan AI Demucs")
        parser.add_argument("-c", "--chunk", type=float, default=1.0, help="Durasi potongan audio dalam detik. Nilai kecil = minim delay, nilai besar = suara stabil (default: 1.0)")
        parser.add_argument("-b", "--buffer", type=int, default=3, help="Kapasitas maksimal antrean buffer audio untuk mencegah akumulasi delay (default: 3)")
        parser.add_argument("-m", "--mode", choices=['vocals', 'instrumental'], default='instrumental', help="Mode output suara: 'vocals' (vokal saja) atau 'instrumental' (instrumen saja) (default: instrumental)")
        args = parser.parse_args()
        chunkDuration = args.chunk
        bufferSize = args.buffer
        audioMode = args.mode
    else:
        print("=== MENU KONFIGURASI ===")
        print("[-] Chunk Duration : Durasi potongan audio (detik). Kecil = minim delay; Besar = lebih stabil.")
        try:
            chunkInput = input("    Masukkan Chunk Duration (detik, default 1.0): ").strip()
            chunkDuration = float(chunkInput) if chunkInput else 1.0
        except ValueError:
            print("    [!] Input tidak valid, menggunakan default: 1.0")
            chunkDuration = 1.0
            
        print("[-] Buffer Size    : Batas antrean audio. Kecil (1-3) = real-time; Besar = mencegah putus-putus tetapi menumpuk delay.")
        try:
            bufferInput = input("    Masukkan Buffer Size (default 3): ").strip()
            bufferSize = int(bufferInput) if bufferInput else 3
        except ValueError:
            print("    [!] Input tidak valid, menggunakan default: 3")
            bufferSize = 3
            
        print("[-] Mode           : Tipe audio yang ingin didengarkan ('vocals' [v] atau 'instrumental' [i]).")
        modeInput = input("    Masukkan Mode (v/i/vocals/instrumental, default instrumental): ").strip().lower()
        if modeInput.startswith('v'):
            audioMode = 'vocals'
        elif modeInput.startswith('i'):
            audioMode = 'instrumental'
        else:
            if modeInput:
                print("    [!] Input tidak valid, menggunakan default: instrumental")
            audioMode = 'instrumental'
            
    processAudio(chunkDuration=chunkDuration, bufferSize=bufferSize, audioMode=audioMode)