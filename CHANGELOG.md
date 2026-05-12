# Changelog

Semua perubahan yang signifikan pada proyek ini akan didokumentasikan di dalam file ini. 
Harap perbarui file ini jika Anda melakukan perubahan (*Pull Request*).

## [Unreleased]
### Added
- `haramMute.py`: Opsi CLI `-c` atau `--chunk` untuk mengatur ukuran buffer audio (Default dikurangi dari 5.0s ke 2.0s).
- `haramMute.py`: Opsi CLI `-b` atau `--buffer` untuk membatasi antrean audio dan mencegah akumulasi delay.
- `run.bat`: Batch script untuk menjalankan program dengan sekali klik (double-click).

### Changed
- `README.md`: Memperbarui dokumentasi pada bagian *Modifikasi Lanjutan* untuk penggunaan opsi CLI `--chunk` alih-alih mengubah variabel di dalam skrip, serta memperjelas perilaku ganti output device.

### Fixed
- `haramMute.bat`: Mengubah flag `-b` menjadi `-c` agar pengaturan durasi buffer (chunk) sesuai dengan yang diharapkan pengguna (memperbaiki masalah di mana nilai tetap 2.0).
- `haramMute.py`: Memperjelas output log dengan menampilkan informasi *chunk duration* dan *queue size* secara bersamaan agar lebih transparan bagi pengguna.

## [1.0.0] - 2026-05-06

### Added
- `haramMute.py`: Skrip utama untuk isolasi vokal (*Vocal Only*) secara *real-time* menggunakan model Demucs (`htdemucs`). Mendukung sistem *Producer-Consumer* (multithreading) untuk mencegah suara putus-putus.
- `requirements.txt`: Daftar pustaka dependensi (*library*) yang wajib diinstal (`demucs`, `sounddevice`, `torch`, `torchaudio`, `numpy`).
- `.gitignore`: Mengabaikan file-file environment lokal Python (seperti `__pycache__` dan `.venv`).
- `README.md`: Panduan lengkap penginstalan, penggunaan, dan arsitektur kerja program (VB-Cable), termasuk peringatan mengenai adanya *delay* sinkronisasi (lipsync) antara video dan audio.
- `CONTRIBUTING.md`: Pedoman kontribusi bagi publik yang ingin membuat Pull Request (PR) beserta aturan komit dan gaya penulisan *camelCase*.
