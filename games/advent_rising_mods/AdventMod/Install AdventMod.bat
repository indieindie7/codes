@echo off
rem AdventMod installer. Double-click to install; "Uninstall AdventMod.bat" removes it.
rem The batch part only launches the PowerShell script embedded below the marker line.
setlocal
set "ADVENTMOD_SELF=%~f0"
set "ADVENTMOD_HERE=%~dp0"
set "ADVENTMOD_MODE=install"
if /i "%~1"=="/uninstall" set "ADVENTMOD_MODE=uninstall"
if not "%~2"=="" set "ADVENTMOD_GAME=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:ADVENTMOD_SELF); iex $s.Substring($s.LastIndexOf('#PS-START#'))"
set "RC=%ERRORLEVEL%"
if not defined ADVENTMOD_NOPAUSE pause
exit /b %RC%

#PS-START#
$ErrorActionPreference = 'Stop'
$mode = $env:ADVENTMOD_MODE
$here = $env:ADVENTMOD_HERE.TrimEnd('\')
$controller = 'GUIController=AdventMod.ModGUIController'
$mutator = 'AdventMod.ModMutator'
$files = 'AdventMod.u', 'AdventMod.int', 'AdventNative.dll'
$ansi = [Text.Encoding]::Default

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function Fail($msg) { Say "`nERROR: $msg" 'Red'; exit 1 }

function Is-Game($dir) { $dir -and (Test-Path (Join-Path $dir 'System\advent.exe')) }

function Find-Game {
    if ($env:ADVENTMOD_GAME) { return $env:ADVENTMOD_GAME }
    # extracted into the game folder (or its System folder)?
    foreach ($d in @($here, (Split-Path $here -Parent))) { if (Is-Game $d) { return $d } }
    $cands = @()
    # every Steam library
    try {
        $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath -replace '/', '\'
        $cands += Join-Path $steam 'steamapps\common\Advent Rising'
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $cands += Join-Path ($m.Groups[1].Value -replace '\\\\', '\') 'steamapps\common\Advent Rising'
            }
        }
    } catch {}
    $cands += Join-Path ${env:ProgramFiles(x86)} 'Steam\steamapps\common\Advent Rising'
    # GOG registers an install path
    try { Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\GOG.com\Games\*' -ErrorAction Stop | ForEach-Object { if ($_.path) { $cands += $_.path } } } catch {}
    $cands += Join-Path ${env:ProgramFiles(x86)} 'GOG.com\Advent Rising'
    $cands += 'C:\GOG Games\Advent Rising'
    foreach ($d in $cands) { if (Is-Game $d) { return $d } }
    Say 'Could not find Advent Rising automatically.' 'Yellow'
    $d = (Read-Host 'Paste the game folder (the one containing System\advent.exe)').Trim('"', ' ')
    if (Is-Game $d) { return $d }
    Fail "No System\advent.exe in '$d'."
}

function Read-Ini($path) { $l = New-Object 'Collections.Generic.List[string]'; $l.AddRange([string[]][IO.File]::ReadAllLines($path, $ansi)); ,$l }
function Write-Ini($path, $lines) { [IO.File]::WriteAllLines($path, [string[]]$lines, $ansi) }
function Backup($path) {
    $bak = "$path.adventmod-backup"
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

# index of the "Key=" line inside a section, or -1
function Find-Key($lines, $range, $key) {
    for ($i = $range[0] + 1; $i -le $range[1]; $i++) { if ($lines[$i].TrimStart() -like "$key=*") { return $i } }
    return -1
}

# the game's settings for its menu controller, which ours has to inherit by hand
function Controller-Settings($sys) {
    $out = @()
    $def = Join-Path $sys 'default.ini'
    if (Test-Path $def) {
        $lines = Read-Ini $def
        $r = Section-Range $lines 'GUI.GUIController'
        if ($r) { for ($i = $r[0] + 1; $i -le $r[1]; $i++) { if ($lines[$i].Trim() -and -not $lines[$i].TrimStart().StartsWith(';')) { $out += $lines[$i].Trim() } } }
    }
    if (-not $out) { $out = 'bModAuthor=true', 'bEmulatedJoypad=false', 'bHideMousecursor=false', 'bJoyMouse=false', 'bJoyDeadZone=0.3' }
    $out
}

# Mydefault.ini: make the game use our menu controller
function Add-Controller($ini, $sys) {
    if (-not (Test-Path $ini)) { return }
    $lines = Read-Ini $ini
    $r = Section-Range $lines 'Engine.Engine'
    if ($r) {
        $k = Find-Key $lines $r 'GUIController'
        if ($k -ge 0 -and $lines[$k].Trim() -ieq $controller -and (Section-Range $lines 'AdventMod.ModGUIController')) { Say "  $(Split-Path $ini -Leaf): already set up"; return }
    }
    Backup $ini
    if (-not $r) { $lines.Add(''); $lines.Add('[Engine.Engine]'); $lines.Add($controller) }
    elseif ($k -ge 0) { $lines[$k] = $controller }
    else { $lines.Insert($r[0] + 1, $controller) }
    if (-not (Section-Range $lines 'AdventMod.ModGUIController')) {
        $lines.Add(''); $lines.Add('[AdventMod.ModGUIController]')
        foreach ($s in (Controller-Settings $sys)) { $lines.Add($s) }
    }
    Write-Ini $ini $lines
    Say "  $(Split-Path (Split-Path $ini -Parent) -Leaf)\$(Split-Path $ini -Leaf): menu controller set"
}

function Remove-Controller($ini) {
    if (-not (Test-Path $ini)) { return }
    $lines = Read-Ini $ini
    $n = $lines.Count
    for ($i = $lines.Count - 1; $i -ge 0; $i--) { if ($lines[$i].Trim() -ieq $controller) { $lines.RemoveAt($i) } }
    $r = Section-Range $lines 'AdventMod.ModGUIController'
    if ($r) {
        $s = $r[0]; if ($s -gt 0 -and -not $lines[$s - 1].Trim()) { $s-- }
        $lines.RemoveRange($s, $r[1] - $s + 1)
    }
    if ($lines.Count -ne $n) { Write-Ini $ini $lines; Say "  $(Split-Path (Split-Path $ini -Parent) -Leaf)\$(Split-Path $ini -Leaf): menu controller removed" }
}

# MyDefUser.ini: load our mutator in every level (keeps other mutators)
function Add-Mutator($ini) {
    if (-not (Test-Path $ini)) { return }
    $lines = Read-Ini $ini
    $r = Section-Range $lines 'DefaultPlayer'
    if ($r) {
        $k = Find-Key $lines $r 'Mutator'
        if ($k -ge 0 -and ($lines[$k].Split('=', 2)[1].Split(',') | ForEach-Object { $_.Trim() }) -contains $mutator) { Say "  $(Split-Path $ini -Leaf): already set up"; return }
    }
    Backup $ini
    if (-not $r) { $lines.Add(''); $lines.Add('[DefaultPlayer]'); $lines.Add("Mutator=$mutator") }
    elseif ($k -ge 0) { $lines[$k] = $lines[$k].TrimEnd().TrimEnd(',') + ",$mutator" }
    else { $lines.Insert($r[0] + 1, "Mutator=$mutator") }
    Write-Ini $ini $lines
    Say "  $(Split-Path (Split-Path $ini -Parent) -Leaf)\$(Split-Path $ini -Leaf): mutator added"
}

function Remove-Mutator($ini) {
    if (-not (Test-Path $ini)) { return }
    $lines = Read-Ini $ini
    $r = Section-Range $lines 'DefaultPlayer'
    if (-not $r) { return }
    $k = Find-Key $lines $r 'Mutator'
    if ($k -lt 0) { return }
    $all = @($lines[$k].Split('=', 2)[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($all -notcontains $mutator) { return }
    $rest = @($all | Where-Object { $_ -ne $mutator })
    if ($rest.Count) { $lines[$k] = 'Mutator=' + ($rest -join ',') } else { $lines.RemoveAt($k) }
    Write-Ini $ini $lines
    Say "  $(Split-Path (Split-Path $ini -Parent) -Leaf)\$(Split-Path $ini -Leaf): mutator removed"
}

$game = Find-Game
$sys = Join-Path $game 'System'
Say "Advent Rising: $game" 'Cyan'
if (Get-Process advent -ErrorAction SilentlyContinue) { Fail 'The game is running. Close it first.' }
# the launcher's "restore defaults" copies these over the live files
$targets = @($sys, (Join-Path $sys 'Defaults'))

try {
    if ($mode -eq 'install') {
        foreach ($f in $files) {
            $src = Join-Path $here "System\$f"
            if (-not (Test-Path $src)) { Fail "Missing $src - extract the whole zip first." }
            Copy-Item $src (Join-Path $sys $f) -Force
        }
        Say "  copied $($files -join ', ')"
        # the Direct3D layer (shadow and post-processing shaders): an existing d3d8.dll that
        # isn't ours (dgVoodoo, an older copy...) and U2Shaders.ini are kept as backups
        $dll = Join-Path $sys 'd3d8.dll'
        if ((Test-Path $dll) -and (Get-FileHash $dll).Hash -ne (Get-FileHash (Join-Path $here 'System\d3d8.dll')).Hash) { Backup $dll }
        Copy-Item (Join-Path $here 'System\d3d8.dll') $dll -Force
        $ini = Join-Path $sys 'U2Shaders.ini'
        if (Test-Path $ini) { Backup $ini }
        Copy-Item (Join-Path $here 'System\U2Shaders.ini') $ini -Force
        New-Item -ItemType Directory -Force (Join-Path $sys 'U2Shaders') | Out-Null
        Copy-Item (Join-Path $here 'System\U2Shaders\*') (Join-Path $sys 'U2Shaders') -Force
        Say "  copied d3d8.dll, U2Shaders.ini and the U2Shaders folder (shaders)"
        # the ragdoll skeletons: the engine reads <game>\KarmaData\*.ka
        if (Test-Path (Join-Path $here 'KarmaData\Advent.ka')) {
            New-Item -ItemType Directory -Force (Join-Path $game 'KarmaData') | Out-Null
            Copy-Item (Join-Path $here 'KarmaData\Advent.ka') (Join-Path $game 'KarmaData\Advent.ka') -Force
            Say "  copied KarmaData\Advent.ka (ragdolls)"
        }
        # the armour hit data: AdventNative reads <game>\AdventMod\Armour\<mesh>.amesh
        if (Test-Path (Join-Path $here 'AdventMod\Armour')) {
            New-Item -ItemType Directory -Force (Join-Path $game 'AdventMod\Armour') | Out-Null
            Copy-Item (Join-Path $here 'AdventMod\Armour\*.amesh') (Join-Path $game 'AdventMod\Armour') -Force
            Say "  copied AdventMod\Armour (armour hit data)"
        }
        foreach ($t in $targets) {
            Add-Controller (Join-Path $t 'Mydefault.ini') $sys
            Add-Mutator (Join-Path $t 'MyDefUser.ini')
        }
        Say "`nDone! In game, Options is a hub of pages: Gameplay, Camera, Audio, Screen, Graphics, Quality, Accessibility, Controls (Graphics: post effects, shadows, GI, anti-aliasing; Screen: resolution, fullscreen mode, frame cap)." 'Green'
    }
    else {
        foreach ($t in $targets) {
            Remove-Controller (Join-Path $t 'Mydefault.ini')
            Remove-Mutator (Join-Path $t 'MyDefUser.ini')
        }
        foreach ($f in ($files + 'AdventMod.ini', 'AdventNative.log', 'd3d8.dll', 'U2Shaders.ini', 'U2Shaders.log')) {
            $p = Join-Path $sys $f
            if (Test-Path $p) { Remove-Item $p -Force; Say "  removed $f" }
        }
        $dir = Join-Path $sys 'U2Shaders'
        if (Test-Path $dir) { Remove-Item $dir -Recurse -Force; Say "  removed the U2Shaders folder" }
        $ka = Join-Path $game 'KarmaData\Advent.ka'
        if (Test-Path $ka) { Remove-Item $ka -Force; Say "  removed KarmaData\Advent.ka" }
        $am = Join-Path $game 'AdventMod\Armour'
        if (Test-Path $am) { Remove-Item $am -Recurse -Force; Say "  removed AdventMod\Armour" }
        # a d3d8.dll or U2Shaders.ini that was there before the mod comes back
        foreach ($f in 'd3d8.dll', 'U2Shaders.ini') {
            $bak = Join-Path $sys "$f.adventmod-backup"
            if (Test-Path $bak) { Move-Item $bak (Join-Path $sys $f) -Force; Say "  put back your earlier $f" }
        }
        Say "`nAdventMod removed. (The *.adventmod-backup files are yours to delete.)" 'Green'
    }
}
catch [UnauthorizedAccessException] { Fail "Windows denied access to the game folder. Right-click this .bat and choose 'Run as administrator'." }
