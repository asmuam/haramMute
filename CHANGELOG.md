# Changelog

Semua perubahan yang signifikan pada proyek ini akan didokumentasikan di dalam file ini. 
Harap perbarui file ini jika Anda melakukan perubahan (*Pull Request*).

## [Unreleased]
### Added
- `haramMute.py` & `haramMuteV2.py`: Fitur pemuatan parameter default dari file konfigurasi `.env` secara dinamis (tanpa perlu melakukan hardcode nilai parameter default di dalam kode python atau batch files).
- `.env` & `.env.example`: Menambahkan file konfigurasi default dan template `.env.example` untuk memudahkan konfigurasi parameter pengguna.
- `haramMute.py` & `haramMuteV2.py`: Fitur pemindahan output audio secara dinamis (switching) jika perangkat output terputus secara tiba-tiba (fallback otomatis) atau saat mendeteksi adanya perangkat output baru (prompts interaktif).
- `haramMute.py` & `haramMuteV2.py`: Menu konfigurasi parameter interaktif di terminal jika program dijalankan tanpa parameter tambahan (dilengkapi dengan deskripsi penjelasan fungsi tiap parameter).
- `haramMute.py` & `haramMuteV2.py`: Deskripsi penjelasan opsi bantuan (`--help`) pada argumen CLI `argparse`.
- `haramMute.bat` & `haramMuteV2.bat`: Prompt interaktif untuk memilih antara parameter default atau input parameter manual di terminal.
- `haramMute.py`: Fitur `--mode` untuk memilih antara `instrumental` (tanpa vokal) atau `vocals` (vokal saja).
- `haramMute.py`: Indikator VU Meter di konsol untuk memantau output suara secara visual (debugging).
- `haramMute.py`: Optimasi 8-thread P-Core & `flush_denormal` untuk kestabilan i7-12700.
- `haramMute.py`: Optimasi khusus Intel i7-12700 (High Process Priority).
- `haramMute.py`: Optimasi FP16 (Half Precision) untuk pengguna GPU NVIDIA agar inferensi lebih cepat.
- `haramMute.bat`: Penyesuaian default chunk ke 1.0 detik untuk kestabilan suara (mencegah stutter).
- `haramMute.py`: Opsi CLI `-c` atau `--chunk` untuk mengatur ukuran buffer audio (Default dikurangi dari 5.0s ke 2.0s).
- `haramMute.py`: Opsi CLI `-b` atau `--buffer` untuk membatasi antrean audio dan mencegah akumulasi delay.
- `run.bat`: Batch script untuk menjalankan program dengan sekali klik (double-click).
- `haramMute.bat`: Penyesuaian default chunk ke 0.5 detik untuk minim delay (sebelumnya 5.0 detik).

### Changed
- `README.md`: Memperbarui dokumentasi pada bagian *Modifikasi Lanjutan* untuk penggunaan opsi CLI `--chunk` alih-alih mengubah variabel di dalam skrip, serta memperjelas perilaku ganti output device.
- `haramMute.py`: Mendukung inisial `v` (vocals) atau `i` (instrumental) untuk pemilihan mode di menu konfigurasi interaktif.

### Fixed
- `haramMute.py` & `haramMuteV2.py`: Memperbaiki bug di mana audio terputus total/hilang saat perangkat output aktif dicabut. Sekarang sistem mendeteksi pencabutan secara OS-level via WMI, me-refresh PortAudio, dan secara otomatis memindahkan aliran suara ke default active speaker yang tersedia di Windows.
- `haramMute.bat`: Mengubah flag `-b` menjadi `-c` agar pengaturan durasi buffer (chunk) sesuai dengan yang diharapkan pengguna (memperbaiki masalah di mana nilai tetap 2.0).
- `haramMute.py`: Memperjelas output log dengan menampilkan informasi *chunk duration* dan *queue size* secara bersamaan agar lebih transparan bagi pengguna.

## [1.0.0] - 2026-05-06

### Added
- `haramMute.py`: Skrip utama untuk isolasi vokal (*Vocal Only*) secara *real-time* menggunakan model Demucs (`htdemucs`). Mendukung sistem *Producer-Consumer* (multithreading) untuk mencegah suara putus-putus.
- `requirements.txt`: Daftar pustaka dependensi (*library*) yang wajib diinstal (`demucs`, `sounddevice`, `torch`, `torchaudio`, `numpy`).
- `.gitignore`: Mengabaikan file-file environment lokal Python (seperti `__pycache__` dan `.venv`).
- `README.md`: Panduan lengkap penginstalan, penggunaan, dan arsitektur kerja program (VB-Cable), termasuk peringatan mengenai adanya *delay* sinkronisasi (lipsync) antara video dan audio.
- `CONTRIBUTING.md`: Pedoman kontribusi bagi publik yang ingin membuat Pull Request (PR) beserta aturan komit dan gaya penulisan *camelCase*.
