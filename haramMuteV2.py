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

# Mengabaikan warning
warnings.filterwarnings("ignore")

sampleRate = 44100
numChannels = 2

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
        
    inputIdx, outputIdx = getDeviceIndices()
    chunkSamples = int(chunkDuration * sampleRate)
    audioQueue = queue.Queue(maxsize=5)
    
    def audioCallback(indata, frames, time, status):
        try: audioQueue.put_nowait(indata.copy())
        except: pass
        
    print(f"[+] HaramMute V2 AKTIF (Mode V3 Cepat)")
    print(f"[+] Chunk: {chunkDuration}s")
    
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
                    
                    with torch.no_grad():
                        # Shifts=0 dan Overlap=0 untuk performa maksimal
                        sources = apply_model(model, wavTensor, shifts=0, split=False, progress=False, overlap=0)
                        
                    outTensor = sources[0, vocalIdx]
                    outChunk = np.ascontiguousarray(outTensor.cpu().float().numpy().T)
                    
                    printVUMeter(outChunk)
                    outQueue.put(outChunk)
                    
    except KeyboardInterrupt: print("\n\n[+] Berhenti.")
    except Exception as err: print(f"\n\n[-] Error: {err}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="HaramMute V2 - Pemisah Vokal Real-Time (Model Light Cepat)")
        parser.add_argument("-c", "--chunk", type=float, default=0.5, help="Durasi potongan audio dalam detik. Nilai kecil = minim delay, nilai besar = suara stabil (default: 0.5)")
        args = parser.parse_args()
        chunkDuration = args.chunk
    else:
        print("=== MENU KONFIGURASI ===")
        print("[-] Chunk Duration : Durasi potongan audio (detik). Kecil = minim delay; Besar = lebih stabil.")
        try:
            chunkInput = input("    Masukkan Chunk Duration (detik, default 0.5): ").strip()
            chunkDuration = float(chunkInput) if chunkInput else 0.5
        except ValueError:
            print("    [!] Input tidak valid, menggunakan default: 0.5")
            chunkDuration = 0.5
            
    processAudio(chunkDuration=chunkDuration)
