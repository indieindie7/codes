@echo off
rem U2SkipCutscenes installer. Double-click to install; "Uninstall U2SkipCutscenes.bat" removes it.
rem The batch part only launches the PowerShell script embedded below the marker line.
setlocal
set "U2SC_SELF=%~f0"
set "U2SC_HERE=%~dp0"
set "U2SC_MODE=install"
if /i "%~1"=="/uninstall" set "U2SC_MODE=uninstall"
if not "%~2"=="" set "U2SC_GAME=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:U2SC_SELF); iex $s.Substring($s.LastIndexOf('#PS-START#'))"
set "RC=%ERRORLEVEL%"
if not defined U2SC_NOPAUSE pause
exit /b %RC%

#PS-START#
$ErrorActionPreference = 'Stop'
$mode = $env:U2SC_MODE
$here = $env:U2SC_HERE.TrimEnd('\')
$mutator = 'U2SkipCutscenes.SkipCutscenes'
$files = @('System\U2SkipCutscenes.u', 'UIScripts\SkipCutscenes.ui')
$ansi = [Text.Encoding]::Default

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function Fail($msg) { Say "`nERROR: $msg" 'Red'; exit 1 }
function Is-Game($dir) { $dir -and (Test-Path (Join-Path $dir 'System\Unreal2.exe')) }

function Find-Game {
    if ($env:U2SC_GAME) { return $env:U2SC_GAME }
    foreach ($d in @($here, (Split-Path $here -Parent))) { if (Is-Game $d) { return $d } }
    $cands = @()
    try {
        $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath -replace '/', '\'
        $cands += Join-Path $steam 'steamapps\common\Unreal II The Awakening'
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $cands += Join-Path ($m.Groups[1].Value -replace '\\\\', '\') 'steamapps\common\Unreal II The Awakening'
            }
        }
    } catch {}
    $cands += Join-Path ${env:ProgramFiles(x86)} 'Steam\steamapps\common\Unreal II The Awakening'
    foreach ($key in 'HKLM:\SOFTWARE\WOW6432Node\GOG.com\Games\*', 'HKLM:\SOFTWARE\WOW6432Node\Legend Entertainment\*', 'HKLM:\SOFTWARE\WOW6432Node\Unreal Technology\Installed Apps\*') {
        try { Get-ItemProperty $key -ErrorAction Stop | ForEach-Object { if ($_.path) { $cands += $_.path }; if ($_.Folder) { $cands += $_.Folder } } } catch {}
    }
    foreach ($d in $cands) { if (Is-Game $d) { return $d } }
    Say 'Could not find Unreal II automatically.' 'Yellow'
    $d = (Read-Host 'Paste the game folder (the one containing System\Unreal2.exe)').Trim('"', ' ')
    if (Is-Game $d) { return $d }
    Fail "No System\Unreal2.exe in '$d'."
}

function Read-Ini($path) { $l = New-Object 'Collections.Generic.List[string]'; $l.AddRange([string[]][IO.File]::ReadAllLines($path, $ansi)); ,$l }
function Write-Ini($path, $lines) { [IO.File]::WriteAllLines($path, [string[]]$lines, $ansi) }
function Backup($path) {
    $bak = "$path.u2sc-backup"
    if (-not (Test-Path $bak)) { Copy-Item $path $bak; Say "  backed up $(Split-Path $path -Leaf) -> $(Split-Path $bak -Leaf)" }
}
function Section-Range($lines, $name) {
    $start = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -ieq "[$name]") { $start = $i; continue }
        if ($start -ge 0 -and $lines[$i].TrimStart().StartsWith('[')) { return @($start, ($i - 1)) }
    }
    if ($start -ge 0) { return @($start, ($lines.Count - 1)) }
    return $null
}

$game = Find-Game
$sys = Join-Path $game 'System'
$userIni = Join-Path $sys 'User.ini'
$gameIni = Join-Path $sys 'Unreal2.ini'
Say "`nUnreal II found at: $game" 'Cyan'

if (Get-Process -Name Unreal2 -ErrorAction SilentlyContinue) { Fail 'Unreal II is running. Close the game and run this again.' }
try { $probe = Join-Path $sys 'u2sc-write-test.tmp'; [IO.File]::WriteAllText($probe, 'x'); Remove-Item $probe }
catch { Fail "Can't write to the game folder. Right-click this .bat and choose 'Run as administrator'." }
if (-not (Test-Path $userIni)) { Fail 'System\User.ini does not exist yet. Start the game once, quit, then run this again.' }

if ($mode -eq 'install') {
    Say "`nInstalling U2SkipCutscenes..." 'Cyan'
    foreach ($f in $files) {
        $src = Join-Path $here $f
        if (-not (Test-Path $src)) { Fail "$f is missing next to this installer (expected $src)." }
        Copy-Item $src (Join-Path $game $f) -Force
        Say "  copied $f"
    }
    Backup $userIni
    $lines = Read-Ini $userIni
    $r = Section-Range $lines 'DefaultPlayer'
    if (-not $r) {
        $lines.Add(''); $lines.Add('[DefaultPlayer]'); $lines.Add("Mutator=$mutator")
        Say '  added [DefaultPlayer] with the Mutator line'
    } else {
        $found = $false
        for ($i = $r[0] + 1; $i -le $r[1]; $i++) {
            if ($lines[$i] -match '^\s*Mutator\s*=(.*)$') {
                $found = $true
                $list = @($Matches[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
                if ($list -contains $mutator) { Say '  Mutator line already present' }
                else { $lines[$i] = 'Mutator=' + (($list + $mutator) -join ','); Say '  added U2SkipCutscenes to the existing Mutator line' }
                break
            }
        }
        if (-not $found) {
            $at = $r[1]
            while ($at -gt $r[0] -and -not $lines[$at].Trim()) { $at-- }
            $lines.Insert($at + 1, "Mutator=$mutator")
            Say '  added Mutator line to [DefaultPlayer]'
        }
    }
    Write-Ini $userIni $lines
    Say "`nDone! Start the game and press SPACE during a cutscene to fast-forward it." 'Green'
}
else {
    Say "`nUninstalling U2SkipCutscenes..." 'Cyan'
    $lines = Read-Ini $userIni
    $r = Section-Range $lines 'DefaultPlayer'
    if ($r) {
        for ($i = $r[1]; $i -gt $r[0]; $i--) {
            if ($lines[$i] -match '^\s*Mutator\s*=(.*)$') {
                $list = @($Matches[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne $mutator })
                if ($list.Count) { $lines[$i] = 'Mutator=' + ($list -join ',') } else { $lines.RemoveAt($i) }
                Say '  removed U2SkipCutscenes from the Mutator line'
            }
        }
    }
    $muted = $false; $vol = $null
    while ($r = Section-Range $lines 'U2SkipCutscenes.SkipCutscenes') {
        # if a crash ever left the sound muted mid-skip, put it back
        for ($k = $r[0]; $k -le $r[1]; $k++) {
            if ($lines[$k] -match '^bMutedBySkip=true') { $muted = $true }
            if ($lines[$k] -match '^SavedSoundVolume=([0-9.]+)') { $vol = $Matches[1] }
        }
        $end = $r[1]; if ($r[0] -gt 0 -and -not $lines[$r[0] - 1].Trim()) { $r[0]-- }
        $lines.RemoveRange($r[0], $end - $r[0] + 1)
        Say '  removed the settings section'
    }
    Write-Ini $userIni $lines
    if ($muted -and $vol -and [double]$vol -gt 0 -and (Test-Path $gameIni)) {
        $g = Read-Ini $gameIni
        for ($k = 0; $k -lt $g.Count; $k++) { if ($g[$k] -match '^SoundVolume=0(\.0+)?$') { $g[$k] = "SoundVolume=$vol"; Say "  restored sound volume to $vol" } }
        Write-Ini $gameIni $g
    }
    foreach ($f in $files) {
        $p = Join-Path $game $f
        if (Test-Path $p) { Remove-Item $p; Say "  deleted $f" }
    }
    Say "`nDone." 'Green'
}
exit 0
