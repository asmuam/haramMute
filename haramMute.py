import sys
import queue
import sounddevice as sd
import numpy as np
import torch
import threading
import warnings
from demucs.pretrained import get_model
from demucs.apply import apply_model

# Mengabaikan warning yang tidak relevan agar console bersih
warnings.filterwarnings("ignore")

# Konfigurasi Parameter
chunkDuration = 3.0  # Waktu buffer dalam detik (semakin kecil = minim delay, tapi butuh CPU kencang)
sampleRate = 44100   # Standar sampling rate audio
numChannels = 2      # Stereo

def getDeviceIndices():
    """
    Mencari indeks dari Virtual Audio Cable sebagai Input, 
    dan default speaker sebagai Output.
    """
    devices = sd.query_devices()
    inputIdx = None
    outputIdx = None
    
    print("Mencari Virtual Audio Cable (VB-Cable)...")
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and 'CABLE Output' in dev['name']:
            inputIdx = i
            break
            
    if inputIdx is None:
        print("Virtual Audio Cable ('CABLE Output') tidak ditemukan secara otomatis!")
        print("Daftar perangkat:")
        print(devices)
        try:
            inputIdx = int(input("\nMasukkan ID untuk input device (CABLE Output): "))
        except ValueError:
            print("ID harus berupa angka. Keluar.")
            sys.exit(1)
            
    # Menggunakan default speaker untuk output
    outputIdx = sd.default.device[1]
    
    print(f"\n-> Menggunakan Input Device ID : {inputIdx} ({devices[inputIdx]['name']})")
    print(f"-> Menggunakan Output Device ID: {outputIdx} ({devices[outputIdx]['name']})\n")
    return inputIdx, outputIdx

def processAudio():
    """
    Fungsi utama untuk membaca stream dari VB-Cable, memproses audio ke Demucs,
    dan memutarnya kembali ke output audio (Speaker).
    """
    print("Memuat model AI Demucs (ini mungkin memakan waktu beberapa detik)...")
    
    # Load model (htdemucs adalah model standar yang bagus)
    modelName = 'htdemucs'
    model = get_model(modelName)
    model.eval()
    
    # Cek apakah bisa menggunakan GPU (CUDA)
    deviceType = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Menggunakan perangkat komputasi: {deviceType.upper()}")
    
    # Optimasi performa CPU untuk Intel i7
    if deviceType == "cpu":
        torch.set_num_threads(8) # Fokus pada Performance Cores
        
    model.to(deviceType)
    
    # Mencari index output yang merupakan "vokal"
    try:
        vocalIdx = model.sources.index('vocals')
    except ValueError:
        vocalIdx = 3 # Biasanya posisi default untuk vokal di htdemucs
        
    inputIdx, outputIdx = getDeviceIndices()
    chunkSamples = int(chunkDuration * sampleRate)
    audioQueue = queue.Queue()
    
    def audioCallback(indata, frames, time, status):
        """
        Callback ini akan dipanggil otomatis saat buffer input sudah penuh
        """
        if status:
            print(status, file=sys.stderr)
        audioQueue.put(indata.copy())
        
    print(f"\n[+] Memulai streaming audio (Ukuran Buffer: {chunkDuration} detik)...")
    print("[!] MAINKAN MUSIK ANDA SEKARANG.")
    print("Tekan Ctrl+C untuk berhenti.")
    
    outQueue = queue.Queue()
    
    def outputWorker(stream):
        while True:
            data = outQueue.get()
            if data is None: # Sinyal berhenti
                break
            stream.write(data)
    
    try:
        # Buka InputStream (membaca dari Chrome -> VB-Cable)
        with sd.InputStream(device=inputIdx, channels=numChannels, samplerate=sampleRate, blocksize=chunkSamples, callback=audioCallback):
            
            # Buka OutputStream (menulis vokal saja -> Speaker)
            with sd.OutputStream(device=outputIdx, channels=numChannels, samplerate=sampleRate) as outStream:
                
                # Jalankan thread terpisah khusus untuk output playback
                playThread = threading.Thread(target=outputWorker, args=(outStream,), daemon=True)
                playThread.start()
                
                while True:
                    # Ambil antrean rekaman audio terbaru
                    chunkData = audioQueue.get()
                    
                    # Konversi array Numpy ke Tensor PyTorch
                    # Bentuk tensor yang dibutuhkan Demucs: (batch, channels, frames)
                    wavTensor = torch.tensor(chunkData.T, dtype=torch.float32).unsqueeze(0).to(deviceType)
                    
                    # Proses pemisahan
                    with torch.no_grad():
                        sources = apply_model(model, wavTensor, shifts=0, split=False, progress=False)
                        
                    # Ambil hanya bagian vokal
                    vocalsTensor = sources[0, vocalIdx]
                    
                    # Konversi kembali ke format Numpy: (frames, channels) dan pastikan formatnya C-contiguous
                    outChunk = np.ascontiguousarray(vocalsTensor.cpu().numpy().T)
                    
                    # Lempar ke antrean pemutaran (tidak lagi blocking/menunggu)
                    outQueue.put(outChunk)
                    
    except KeyboardInterrupt:
        print("\n[+] Program dihentikan oleh pengguna.")
    except Exception as err:
        print(f"\n[-] Terjadi kesalahan: {err}")

if __name__ == "__main__":
    processAudio()