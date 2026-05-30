@echo off
title HaramMute V2 (Demucs Light)
echo Menjalankan HaramMute V2...
echo.
set /p choiceVal="Gunakan parameter default (Chunk: 0.3s)? [Y/N, default Y]: "
if /i "%choiceVal%"=="N" (
    echo Menjalankan mode interaktif...
    python haramMuteV2.py
) else (
    echo Menjalankan dengan parameter default...
    python haramMuteV2.py -c 0.3
)
pause
