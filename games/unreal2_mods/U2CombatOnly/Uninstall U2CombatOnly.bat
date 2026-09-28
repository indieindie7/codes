@echo off
rem Removes U2CombatOnly (the installer does the work).
call "%~dp0Install U2CombatOnly.bat" /uninstall %1
