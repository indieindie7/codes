@echo off
rem Builds out64\winmm.dll (x64, FPS graph) for The Solus Project.
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul
cd /d "%~dp0"
if not exist out64 mkdir out64
cl /nologo /O2 /W3 /EHsc /LD /MT /D_CRT_SECURE_NO_WARNINGS solus_fps.cpp /Fo:out64\s.obj /Fe:out64\winmm.dll /link d3d11.lib dxgi.lib user32.lib /SUBSYSTEM:WINDOWS
del /q out64\*.obj out64\*.exp out64\*.lib 2>nul
dir /b out64
