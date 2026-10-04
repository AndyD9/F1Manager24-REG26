@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "%~dp0"
cl /nologo /O2 /MT cave_test.cpp /Fe:cave_test.exe /link kernel32.lib >nul && cave_test.exe
