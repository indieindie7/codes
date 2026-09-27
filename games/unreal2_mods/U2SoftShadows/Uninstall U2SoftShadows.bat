@echo off
rem Removes U2SoftShadows (the installer does the work).
call "%~dp0Install U2SoftShadows.bat" /uninstall %1
