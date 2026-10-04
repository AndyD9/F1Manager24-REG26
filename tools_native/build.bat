@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "%~dp0"
if not exist build mkdir build
cl /nologo /O2 /EHa /LD /MT hwbp.cpp /Fo:build\ /Fe:build\hwbp.dll /link kernel32.lib
cl /nologo /O2 /LD /MT reg2026patch.cpp /Fo:build\ /Fe:..\ue4ss\Reg2026\Reg2026Patch.dll /link kernel32.lib
