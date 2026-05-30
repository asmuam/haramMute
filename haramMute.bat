@echo off
title HaramMute Runner
echo Checking dependencies...
pip install -r requirements.txt
echo.
set /p choiceVal="Gunakan parameter default (Chunk: 2.7s, Buffer: 3, Mode: vocals)? [Y/N, default Y]: "
if /i "%choiceVal%"=="N" (
    echo Menjalankan mode interaktif...
    python haramMute.py
) else (
    echo Menjalankan dengan parameter default...
    python haramMute.py -c 2.7 -b 3 --mode vocals
)
pause
