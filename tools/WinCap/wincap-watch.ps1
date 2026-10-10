# wincap-watch.ps1 - waits for a game and records every launch with wincap.ps1 -Background.
# Run at logon by the task "WinCap Advent" (install-watch.ps1). Log: %LOCALAPPDATA%\WinCap\watch.log
param([string]$Exe = 'advent.exe', [double]$Fps = 2)
$name = [IO.Path]::GetFileNameWithoutExtension($Exe)
$log = Join-Path $env:LOCALAPPDATA 'WinCap\watch.log'
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log($m) { Add-Content $log ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $m) }
Log "watching $Exe"
while ($true) {
	$p = Get-Process $name -EA 0 | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
	if (-not $p) { Start-Sleep 2; continue }
	Start-Sleep 3   # let the window settle (AdventNative resizes it)
	while (Get-Process $name -EA 0) {
		Log "recording pid $($p.Id)"
		$t = Get-Date
		& "$PSScriptRoot\wincap.ps1" -Exe $Exe -Fps $Fps -Background *>> $log
		# a capture that dies at once means the window wasn't ready: retry while the game runs
		if (((Get-Date) - $t).TotalSeconds -gt 10) { break }
		Start-Sleep 3
	}
	Log "game closed"
	while (Get-Process $name -EA 0) { Start-Sleep 2 }
}
