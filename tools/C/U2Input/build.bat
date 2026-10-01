@echo off
rem Builds bin\dinput8.dll (32-bit) with Visual Studio's x86 compiler.
setlocal
set VCVARS="C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsamd64_x86.bat"
call %VCVARS% >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
cl /nologo /O2 /W3 /LD /MT src\dinput8proxy.c /Fo:bin\ /Fe:bin\dinput8.dll /link /DEF:src\dinput8.def user32.lib || exit /b 1
echo built bin\dinput8.dll
