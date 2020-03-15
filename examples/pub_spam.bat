@echo off
setlocal
call ..\venv\Scripts\activate.bat
python pub.py stress
endlocal