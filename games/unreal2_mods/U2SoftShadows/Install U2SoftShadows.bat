@echo off
rem U2SoftShadows installer. Double-click to install; "Uninstall U2SoftShadows.bat" removes it.
rem The batch part only launches the PowerShell script embedded below the marker line.
setlocal
set "U2SS_SELF=%~f0"
set "U2SS_HERE=%~dp0"
set "U2SS_MODE=install"
if /i "%~1"=="/uninstall" set "U2SS_MODE=uninstall"
if not "%~2"=="" set "U2SS_GAME=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:U2SS_SELF); iex $s.Substring($s.LastIndexOf('#PS-START#'))"
set "RC=%ERRORLEVEL%"
if not defined U2SS_NOPAUSE pause
exit /b %RC%

#PS-START#
$ErrorActionPreference = 'Stop'
$mode = $env:U2SS_MODE
$here = $env:U2SS_HERE.TrimEnd('\')
$mutator = 'U2SoftShadows.SSShadowMutator'
$ansi = [Text.Encoding]::Default

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function Fail($msg) { Say "`nERROR: $msg" 'Red'; exit 1 }

function Is-Game($dir) { $dir -and (Test-Path (Join-Path $dir 'System\Unreal2.exe')) }

function Find-Game {
    if ($env:U2SS_GAME) { return $env:U2SS_GAME }
    # extracted into the game folder (or its System folder)?
    foreach ($d in @($here, (Split-Path $here -Parent))) { if (Is-Game $d) { return $d } }
    $cands = @()
    # every Steam library
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
    # GOG and retail installs register an install path
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
    $bak = "$path.u2ss-backup"
    if (-not (Test-Path $bak)) { Copy-Item $path $bak; Say "  backed up $(Split-Path $path -Leaf) -> $(Split-Path $bak -Leaf)" }
}

# first and last line index of a [Section] (end = last line before the next header)
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
try { $probe = Join-Path $sys 'u2ss-write-test.tmp'; [IO.File]::WriteAllText($probe, 'x'); Remove-Item $probe }
catch { Fail "Can't write to the game folder. Right-click this .bat and choose 'Run as administrator'." }
if (-not (Test-Path $userIni)) { Fail 'System\User.ini does not exist yet. Start the game once, quit, then run this again.' }

if ($mode -eq 'install') {
    Say "`nInstalling U2SoftShadows..." 'Cyan'
    $src = Join-Path $here 'System\U2SoftShadows.u'
    if (-not (Test-Path $src)) { Fail "System\U2SoftShadows.u is missing next to this installer (expected $src)." }
    Copy-Item $src (Join-Path $sys 'U2SoftShadows.u') -Force
    Say '  copied U2SoftShadows.u'

    # 1. load the add-on on every map: Mutator= in [DefaultPlayer]
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
                else { $lines[$i] = 'Mutator=' + (($list + $mutator) -join ','); Say '  added U2SoftShadows to the existing Mutator line' }
                break
            }
        }
        if (-not $found) {
            $at = $r[1]
            while ($at -gt $r[0] -and -not $lines[$at].Trim()) { $at-- }   # before trailing blank lines
            $lines.Insert($at + 1, "Mutator=$mutator")
            Say '  added Mutator line to [DefaultPlayer]'
        }
    }
    Write-Ini $userIni $lines

    # 2. enough shadow textures for 3 shadows per character
    if (Test-Path $gameIni) {
        $lines = Read-Ini $gameIni
        $changed = $false
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match "^ObjectPoolPrecacheList=\(ObjectClass=Class'Engine\.ShadowBitmapMaterial',NumObjects=(\d+)\)" -and [int]$Matches[1] -lt 48) {
                if (-not $changed) { Backup $gameIni }
                $lines[$i] = $lines[$i] -replace 'NumObjects=\d+', 'NumObjects=48'
                $changed = $true
            }
        }
        if ($changed) { Write-Ini $gameIni $lines; Say '  raised the shadow texture pool to 48' }
        else { Say '  shadow texture pool already large enough (or not listed)' }
    }
    Say "`nDone! Start the game - System\Unreal2.log should show 'U2SoftShadows: manager active'." 'Green'
    Say 'Optional settings are described in README.txt.'
}
else {
    Say "`nUninstalling U2SoftShadows..." 'Cyan'
    $lines = Read-Ini $userIni
    $r = Section-Range $lines 'DefaultPlayer'
    if ($r) {
        for ($i = $r[1]; $i -gt $r[0]; $i--) {
            if ($lines[$i] -match '^\s*Mutator\s*=(.*)$') {
                $list = @($Matches[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne $mutator })
                if ($list.Count) { $lines[$i] = 'Mutator=' + ($list -join ',') } else { $lines.RemoveAt($i) }
                Say '  removed U2SoftShadows from the Mutator line'
            }
        }
    }
    while ($r = Section-Range $lines 'U2SoftShadows.SSShadowController') {
        $end = $r[1]; if ($r[0] -gt 0 -and -not $lines[$r[0] - 1].Trim()) { $r[0]-- }
        $lines.RemoveRange($r[0], $end - $r[0] + 1)
        Say '  removed the optional settings section'
    }
    Write-Ini $userIni $lines
    $u = Join-Path $sys 'U2SoftShadows.u'
    if (Test-Path $u) { Remove-Item $u; Say '  deleted U2SoftShadows.u' }
    Say "`nDone. (The larger shadow texture pool in Unreal2.ini is harmless and was left as is.)" 'Green'
}
exit 0
