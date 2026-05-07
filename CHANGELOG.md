# Changelog

Semua perubahan yang signifikan pada proyek ini akan didokumentasikan di dalam file ini. 
Harap perbarui file ini jika Anda melakukan perubahan (*Pull Request*).

## [1.0.0] - 2026-05-06

### Added
- `haramMute.py`: Skrip utama untuk isolasi vokal (*Vocal Only*) secara *real-time* menggunakan model Demucs (`htdemucs`). Mendukung sistem *Producer-Consumer* (multithreading) untuk mencegah suara putus-putus.
- `requirements.txt`: Daftar pustaka dependensi (*library*) yang wajib diinstal (`demucs`, `sounddevice`, `torch`, `torchaudio`, `numpy`).
- `.gitignore`: Mengabaikan file-file environment lokal Python (seperti `__pycache__` dan `.venv`).
- `README.md`: Panduan lengkap penginstalan, penggunaan, dan arsitektur kerja program (VB-Cable), termasuk peringatan mengenai adanya *delay* sinkronisasi (lipsync) antara video dan audio.
- `CONTRIBUTING.md`: Pedoman kontribusi bagi publik yang ingin membuat Pull Request (PR) beserta aturan komit dan gaya penulisan *camelCase*.
