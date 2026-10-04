@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "%~dp0"
if not exist build mkdir build
cl /nologo /O2 /EHa /LD /MT hwbp.cpp /Fo:build\ /Fe:build\hwbp.dll /link kernel32.lib
