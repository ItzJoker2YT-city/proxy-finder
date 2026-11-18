@echo off
cd /d "%~dp0"
python "app\PROXY finder.py"
if errorlevel 1 pause
