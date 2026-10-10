# wincap.ps1 - record one window at a low, spaced frame rate into C:\Users\john\Videos,
# named like OBS files ("2026-10-10 14-03-22.mp4").
# Uses ffmpeg's gfxcapture source (Windows Graphics Capture, the same API as OBS window capture):
# the window can be covered or off-screen, but not minimised.
#
#   .\wincap.ps1 -Exe advent.exe                 # 2 frames a second, plays back in real time
#   .\wincap.ps1 -Title 'Hydrophobia' -Fps 0.5   # one frame every 2 seconds
#   .\wincap.ps1 -Exe advent.exe -Timelapse      # same frames, played back at 30 fps (sped up)
#   .\wincap.ps1 -Exe advent.exe -Seconds 600    # stop after 10 minutes
#   .\wincap.ps1 -Exe advent.exe -Background     # no console; stops cleanly when advent.exe exits
# Stops when the window closes, after -Seconds, or on 'q' / Ctrl+C in the console.
# wincap-watch.ps1 runs it with -Background for every Advent launch.
param(
	[string]$Exe,                 # process exe name, e.g. advent.exe
	[string]$Title,               # regex on the window title
	[double]$Fps = 2,             # frames captured per second (0.5 = one every 2 s)
	[switch]$Timelapse,           # play the spaced frames back at 30 fps instead of real time
	[int]$Seconds = 0,            # 0 = until the window closes
	[int]$Crf = 23,
	[string]$OutDir = "$env:USERPROFILE\Videos",
	[switch]$Background           # hidden ffmpeg, sent 'q' when the -Exe process exits (mp4 stays valid)
)
if (-not $Exe -and -not $Title) { throw 'give -Exe or -Title' }

$ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe" -EA 0 | Select-Object -First 1
if (-not $ff) { $ff = Get-Command ffmpeg -EA Stop }
$ff = if ($ff.FullName) { $ff.FullName } else { $ff.Source }

# gfxcapture option values are regexes; ':' and ',' would end the option, so escape them.
function Esc([string]$s) { $s -replace '([:,\\''])', '\$1' }
$match = if ($Exe) { 'window_exe=(?i)^' + (Esc ([regex]::Escape($Exe))) + '$' } else { 'window_title=' + (Esc $Title) }

$rate = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $Fps)
$vf = "gfxcapture=${match}:max_framerate=${rate}:capture_cursor=0,hwdownload,format=bgra,fps=${rate}"
# fps= does the spacing: on Win10 gfxcapture can't lower its own update rate.
# The timelapse speed-up goes in the output -vf, so -t still counts real capture time.
$post = if ($Timelapse) { 'setpts=N/(30*TB),' } else { '' }

$out = Join-Path $OutDir ((Get-Date -Format 'yyyy-MM-dd HH-mm-ss') + '.mp4')
$a = @('-hide_banner', '-loglevel', 'warning', '-stats')
if ($Seconds -gt 0) { $a += @('-t', $Seconds) }   # input option: capture time, not output time
$a += @('-f', 'lavfi', '-i', $vf)
$a += @('-c:v', 'libx264', '-preset', 'veryfast', '-crf', $Crf, '-pix_fmt', 'yuv420p',
	'-vf', ($post + 'pad=ceil(iw/2)*2:ceil(ih/2)*2'))
$a += if ($Timelapse) { @('-r', '30') } else { @('-fps_mode', 'vfr') }
$a += @('-movflags', '+faststart', $out)

Write-Host "recording -> $out"
if (-not $Background) { & $ff @a }
else {
	$psi = New-Object Diagnostics.ProcessStartInfo $ff
	$psi.Arguments = ($a | ForEach-Object { '"' + ([string]$_ -replace '"', '\"') + '"' }) -join ' '
	$psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardInput = $true
	$proc = [Diagnostics.Process]::Start($psi)
	$name = if ($Exe) { [IO.Path]::GetFileNameWithoutExtension($Exe) } else { $null }
	while (-not $proc.HasExited) {
		Start-Sleep -Milliseconds 500
		if ($name -and -not (Get-Process $name -EA 0)) { $proc.StandardInput.Write('q'); $proc.StandardInput.Flush(); break }
	}
	if (-not $proc.WaitForExit(15000)) { $proc.Kill() }
}
if (Test-Path $out) { Write-Host "saved $out ($([math]::Round((Get-Item $out).Length/1MB,1)) MB)" }
