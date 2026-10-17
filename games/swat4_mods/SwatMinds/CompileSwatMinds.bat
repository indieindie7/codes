@echo off
rem Build in BuildSystem (holds SDK-rebuilt base packages); runtime System gets only SwatMinds.u
cd /d "%~dp0BuildSystem"
if exist SwatMinds.u del SwatMinds.u
..\..\Content\System\UCC.exe make -nobind
if exist SwatMinds.u copy /y SwatMinds.u ..\System\SwatMinds.u
