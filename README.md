# haramMute 🎧

**haramMute** adalah skrip Python sederhana namun kuat yang dirancang untuk mengisolasi atau menghapus suara instrumen dari *output* sistem Anda secara *real-time* menggunakan model AI **Demucs** (oleh Meta Research). 

Awalnya dirancang untuk digunakan bersama Last.fm dan YouTube agar Anda hanya mendengarkan vokal murni (Vocal Only) secara instan!

---

## 🎯 Fitur Utama

- **Real-Time Processing**: Menangkap audio secara langsung dari sistem menggunakan *Virtual Audio Cable* (VB-Cable).
- **AI-Powered Separation**: Menggunakan **Demucs** (`htdemucs`) untuk isolasi vokal beresolusi tinggi.
- **Multithreaded Playback**: Penggunaan CPU (khususnya untuk prosesor *multicore* seperti Intel i7) telah dioptimalkan agar tidak memblokir antrean (*queue*), memastikan audio yang diputar tidak putus-putus.
- **camelCase Convention**: Basis kode ini secara konsisten menggunakan gaya penulisan `camelCase`.

## ⚙️ Persyaratan Sistem

1. **OS**: Windows 10/11.
2. **Python**: Versi 3.10 atau lebih tinggi (3.13 didukung).
3. **VB-Audio Virtual Cable**: Wajib diinstal untuk mencegah terjadinya *feedback loop*. Anda bisa mengunduhnya [secara gratis di sini](https://vb-audio.com/Cable/).

## 🚀 Cara Instalasi

1. Lakukan *Clone* (Salin) repositori ini:
   ```bash
   git clone https://github.com/username/haramMute.git
   cd haramMute
   ```

2. Instal seluruh modul yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
   > **Perhatian pengguna GPU AMD/NVIDIA**: Jika Anda memiliki GPU yang didukung CUDA/ROCm, pastikan untuk menginstal versi PyTorch yang tepat via [situs web PyTorch](https://pytorch.org/) untuk performa yang lebih baik.

## 🎧 Cara Penggunaan

1. Pastikan Anda telah menetapkan *output* dari aplikasi sumber suara Anda (misal: Google Chrome yang sedang membuka Last.fm atau YouTube) ke **CABLE Input (VB-Audio Virtual Cable)**.
2. Buka terminal pada *folder* ini dan jalankan skrip:
   ```bash
   python haramMute.py
   ```
3. Skrip akan secara otomatis melacak *output* dari VB-Cable, mengisolasi vokalnya, lalu memutarnya ke *speaker* atau *headset* bawaan PC Anda.

> **⚠️ Catatan Penting Terkait Video:** Karena sistem membaca dan memproses audio dalam bentuk paket data (*chunking*) sebesar 3 detik (waktu komputasi), **audio yang Anda dengar akan mengalami *delay*** sekitar 3 detik di belakang videonya. Jadi wajar jika pergerakan mulut penyanyi di video YouTube Anda akan berjalan lebih dulu daripada suaranya (lipsync tidak akan pas).
### 🎛️ Modifikasi Lanjutan
Jika audio masih terasa *delay* berlebih atau justru putus-putus, buka `haramMute.py` dan ubah variabel `chunkDuration` (Default: `3.0` detik).
- **Turunkan nilainya** (misal `1.5`) agar audio lebih responsif, namun ini butuh performa CPU/GPU yang kuat.
- **Naikkan nilainya** (misal `4.0`) jika suara terputus karena PC tidak sanggup memproses data dengan cepat.

## 📄 Lisensi

Proyek ini dirilis secara bebas. Silakan merujuk pada lisensi Demucs untuk hak cipta spesifik terkait model AI yang digunakan.
