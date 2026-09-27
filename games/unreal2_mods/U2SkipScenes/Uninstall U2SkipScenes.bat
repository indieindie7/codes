@echo off
rem Removes U2SkipScenes (the installer does the work).
call "%~dp0Install U2SkipScenes.bat" /uninstall %1
