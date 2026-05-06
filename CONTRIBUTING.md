# Berkontribusi ke haramMute

Terima kasih atas ketertarikan Anda untuk berkontribusi! 

Untuk memastikan repositori ini tetap rapi dan terstandar, kami memiliki beberapa aturan ketat yang **wajib** Anda ikuti sebelum mengirimkan *Pull Request*.

## Aturan Penulisan Kode (Code Convention)

1. **Gunakan `camelCase`**: Ini adalah aturan utama kami. Setiap variabel, fungsi, maupun struktur data di Python harus ditulis menggunakan format `camelCase` (contoh: `chunkDuration`, `processAudio`, bukan `chunk_duration` atau `ProcessAudio`).
2. **Komentar yang Rapi**: Gunakan Docstring untuk fungsi yang kompleks, serta jelaskan algoritma spesifik yang Anda ubah di dalam komentar.

## Aturan Komit (Commit Rules)

Proyek ini mewajibkan aturan **Atomic Commit** dan format **Conventional Commits**:

1. **Atomic Commit**: Satu file yang berubah = Satu komit. Tolong jangan menggabungkan banyak perubahan file dalam satu *commit message*.
2. **Format**: Gunakan awalan `feat`, `fix`, `docs`, `chore`, `refactor`, atau `style`. Contoh: `feat(audio): menambahkan fitur isolasi bass`.
3. **Changelog**: Anda **wajib** memperbarui file `CHANGELOG.md` pada setiap *pull request* yang Anda ajukan. Jelaskan apa yang Ditambahkan (Added), Diubah (Changed), atau Diperbaiki (Fixed).

## Cara Membuat Pull Request (PR)

1. Lakukan *Fork* pada repositori ini.
2. Buat *branch* fitur Anda (`git checkout -b feature/FiturKeren`).
3. Tulis kode Anda.
4. Lakukan *commit* dengan format yang benar.
5. Lakukan *Push* ke *branch* Anda (`git push origin feature/FiturKeren`).
6. Buka jendela *Pull Request* dan jelaskan perubahan yang Anda buat!
