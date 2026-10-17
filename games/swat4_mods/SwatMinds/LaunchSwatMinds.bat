@echo off
cd /d "%~dp0System"
start "" pythonw "%~dp0borderless.pyw"
..\..\Content\System\Swat4.exe -nointro %*
