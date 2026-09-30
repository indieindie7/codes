@echo off
rem Removes AdventMod (the installer does the work).
call "%~dp0Install AdventMod.bat" /uninstall %1
