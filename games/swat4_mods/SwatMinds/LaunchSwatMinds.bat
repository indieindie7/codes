@echo off
rem SwatMinds launcher (GOG Galaxy primary play task): borderless helper + game, then this window closes.
cd /d "%~dp0System"
start "" pythonw "%~dp0borderless.pyw"
start "" "..\..\Content\System\Swat4.exe" -nointro %*
