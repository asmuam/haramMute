@echo off
title HaramMute V2 (Demucs Light)
echo Menjalankan HaramMute V2...
echo.
set /p choiceVal="Gunakan parameter default dari .env? [Y/N, default Y]: "
if /i "%choiceVal%"=="N" (
    echo Menjalankan mode interaktif...
    python haramMuteV2.py
) else (
    echo Menjalankan dengan parameter default dari .env...
    python haramMuteV2.py --env
)
pause
