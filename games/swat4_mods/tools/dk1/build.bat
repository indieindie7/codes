@echo off
rem Builds bin\dbghelp.dll (32-bit DK1 gym hook) with the VS x86 compiler.
setlocal
set VCVARS="C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsamd64_x86.bat"
call %VCVARS% >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
cl /nologo /O2 /W3 /LD /MT /D_CRT_SECURE_NO_WARNINGS dk1hook.c /Fo:bin\ /Fe:bin\dbghelp.dll /link /DEF:dbghelp.def user32.lib || exit /b 1
echo built bin\dbghelp.dll
