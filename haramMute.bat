@echo off
title HaramMute Runner
echo Checking dependencies...
pip install -r requirements.txt
echo.
set /p choiceVal="Gunakan parameter default dari .env? [Y/N, default Y]: "
if /i "%choiceVal%"=="N" (
    echo Menjalankan mode interaktif...
    python haramMute.py
) else (
    echo Menjalankan dengan parameter default dari .env...
    python haramMute.py --env
)
pause
