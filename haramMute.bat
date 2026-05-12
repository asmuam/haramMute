@echo off
title HaramMute Runner
echo Checking dependencies...
pip install -r requirements.txt
echo Starting HaramMute...
python haramMute.py -c 5
pause
