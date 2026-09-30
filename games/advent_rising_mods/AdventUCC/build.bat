@echo off
rem Builds AdventUCC.exe and AdventUCCHook.dll (32-bit, like the game).
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsamd64_x86.bat" >nul 2>nul
cd /d "%~dp0"
if not exist obj mkdir obj
cl /nologo /O1 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Foobj\ /LD src\hook.c /FeAdventUCCHook.dll /link /NOLOGO || exit /b 1
cl /nologo /O1 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Foobj\ src\adventucc.c /FeAdventUCC.exe /link /NOLOGO advapi32.lib || exit /b 1
