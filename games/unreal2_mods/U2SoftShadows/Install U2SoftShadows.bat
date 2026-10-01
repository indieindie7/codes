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

# ---------------------------------------------------------------- 1.3 additions
$pageText = @'
### U2SoftShadows options page ###

[OptionDescriptions_SOFTSHADOWS]
Class=FixedSizeContainer
Location=%0%,%1%
Component=OptionMouseOvers:SOFTSHADOWS
Component=OptionDescription:01/0/SSEnabled
Component=OptionDescription:02/26/SSMaxShadows
Component=OptionDescription:03/52/SSStrength
Component=OptionDescription:04/78/SSFadeLength
Component=OptionDescription:05/104/SSContact
Component=OptionDescription:06/130/SSHardToSoft
Component=OptionDescription:07/156/SSCapsules
Component=OptionDescription:08/182/SSCameraCull
Component=OptionDescription:09/208/SSNearDistance
Component=OptionDescription:10/234/SSMidDistance
Component=OptionDescription:11/260/SSWeighted
Component=OptionDescription:12/286/SSOpenEngine

[SSMenuHelper]
Helper=U2SoftShadows$SSMenuHelper
RegisterObj=SSMenuHelper

[OptionWidgets_SOFTSHADOWS]
Class=FixedSizeContainer
Component=SSMenuHelper
Component=U2CheckBox:0
	Object=SSMenuHelper
	Variable=Enabled
Component=U2Slider:26
	Range=0,3
	Step=1
	Format=Int2Format
	Object=SSMenuHelper
	Variable=MaxShadows
Component=U2Slider:52
	Range=60,255
	Step=5
	Format=Int4Format
	Object=SSMenuHelper
	Variable=Strength
Component=U2Slider:78
	Range=1,6
	Step=0.5
	Format=Float2Format
	Object=SSMenuHelper
	Variable=FadeLength
Component=U2CheckBox:104
	Object=SSMenuHelper
	Variable=Contact
Component=U2CheckBox:130
	Object=SSMenuHelper
	Variable=HardToSoft
Component=U2CheckBox:156
	Object=SSMenuHelper
	Variable=Capsules
Component=U2CheckBox:182
	Object=SSMenuHelper
	Variable=CameraCull
Component=U2Slider:208
	Range=300,2000
	Step=50
	Format=Int4Format
	Object=SSMenuHelper
	Variable=NearDistance
Component=U2Slider:234
	Range=500,4000
	Step=100
	Format=Int4Format
	Object=SSMenuHelper
	Variable=MidDistance
Component=U2CheckBox:260
	Object=SSMenuHelper
	Variable=Weighted
Component=FixedSizeContainer
	Component=OptionButton:SSOpen/Shadows
	Location=0,286
	Size=82,21
Location=%0%,%1%
Register=OptionWidgets_SOFTSHADOWS
'@
$intText = @'
SubTitleSoftShadows=SOFT SHADOWS
OptionButtonSSOpen=OPEN
OptionDescriptionSSOpenSoft=Soft Shadows (mod):
OptionDescriptionSSOpenEngine=Engine Shadows:
OptionDescriptionSSEnabled=Soft Shadows:
OptionDescriptionSSMaxShadows=Lights per Character:
OptionDescriptionSSStrength=Darkness:
OptionDescriptionSSFadeLength=Fade Length:
OptionDescriptionSSContact=Contact Shadow:
OptionDescriptionSSHardToSoft=Hard-to-Soft:
OptionDescriptionSSCapsules=Capsule Shadows:
OptionDescriptionSSCameraCull=Camera Culling:
OptionDescriptionSSNearDistance=Full Detail Within:
OptionDescriptionSSMidDistance=Reduced Detail Within:
OptionDescriptionSSWeighted=Varied Lights:
MouseOver_SOFTSHADOWS_01=Multi-light soft character shadows (U2SoftShadows). Off = the game's own single shadow, set up on the MISC page.
MouseOver_SOFTSHADOWS_02=How many lights cast a shadow of each character. More = heavier. 0 = contact shadow only.
MouseOver_SOFTSHADOWS_03=How dark the shadows are at full strength.
MouseOver_SOFTSHADOWS_04=How far a shadow reaches before fading out, as a multiple of its length. 1 = gone at the head, 3 = gentle.
MouseOver_SOFTSHADOWS_05=A soft dark patch on the floor under the feet that grounds the character whatever the lights do.
MouseOver_SOFTSHADOWS_06=A crisper copy of the strongest light's shadow at the feet, fading fast, under the soft one: sharp where it touches, soft as it stretches.
MouseOver_SOFTSHADOWS_07=Experimental: soft ovals per limb placed from the skeleton, always soft. Costs about 20 fps in big fights.
MouseOver_SOFTSHADOWS_08=Only characters the camera can see get shadows. Recommended.
MouseOver_SOFTSHADOWS_09=Characters closer than this get every shadow; between this and the next distance, one light shadow plus contact; beyond, contact only.
MouseOver_SOFTSHADOWS_10=Beyond this distance characters keep only the contact shadow.
'@
$pageMark = '### U2SoftShadows options page ###'
$stateHud = "`tState=OptionMenu:HUD/%0%/%1%/%2%/%3%/SubTitleHUD"
$stateOurs = "`tState=OptionMenu:SOFTSHADOWS/%0%/%1%/%2%/%3%/SubTitleSoftShadows"
$transHud = "`tTransition=Options.HUD,6,6,0,NULL"
$transOurs = "`tTransition=Options.SoftShadows,7,7,0,NULL"

# the U2SS-MENU page: our own page plus an OPEN row on the stock Shadows (MISC) page
function Add-MenuPage($ui) {
    $lines = Read-Ini $ui
    if ($lines.Contains($pageMark)) { Say "  options page already in $(Split-Path $ui -Leaf)"; return }
    $d = Section-Range $lines 'OptionDescriptions_SHADOWS'
    $w = Section-Range $lines 'OptionWidgets_SHADOWS'
    if (-not $d -or -not $w -or $lines.IndexOf($stateHud) -lt 0 -or $lines.IndexOf($transHud) -lt 0) {
        Say "  $(Split-Path $ui -Leaf): no Shadows options page found, skipped" 'Yellow'; return
    }
    Backup $ui
    # the OPEN row: next free slot on the stock page
    $rows = @(); $last = -1
    for ($i = $d[0]; $i -le $d[1]; $i++) {
        if ($lines[$i] -match '^Component=OptionDescription:\d\d/(\d+)/') { $rows += [int]$Matches[1]; $last = $i }
    }
    $y = 0; if ($rows.Count) { $y = ($rows | Measure-Object -Maximum).Maximum + 26 }
    $n = [Math]::Min($rows.Count + 1, 10)
    $locAt = -1
    for ($i = $w[0]; $i -le $w[1]; $i++) { if ($lines[$i] -eq 'Location=%0%,%1%') { $locAt = $i } }
    $regAt = $lines.IndexOf('Register=OptionWidgets_SHADOWS')
    if ($last -lt 0 -or $locAt -lt 0 -or $regAt -lt 0) { Say "  $(Split-Path $ui -Leaf): unexpected page layout, skipped" 'Yellow'; return }
    # insert from the bottom up so earlier indexes stay valid
    $lines.InsertRange($regAt + 1, [string[]](@('') + ($pageText -split "`r?`n")))
    $lines.InsertRange($locAt, [string[]]@('Component=FixedSizeContainer', "`tComponent=OptionButton:SSOpen/SoftShadows", "`tLocation=0,$y", "`tSize=82,21"))
    $lines.Insert($last + 1, ('Component=OptionDescription:{0:D2}/{1}/SSOpenSoft' -f $n, $y))
    $lines.Insert($lines.IndexOf($transHud) + 1, $transOurs)
    $lines.Insert($lines.IndexOf($stateHud) + 1, $stateOurs)
    Write-Ini $ui $lines
    Say "  added the Soft Shadows options page to $(Split-Path $ui -Leaf)"
    $script:menuSlot = $n
}

function Add-MenuText($int, $slot) {
    if (-not (Test-Path $int)) { return }
    $lines = Read-Ini $int
    if (@($lines | Where-Object { $_ -like 'OptionDescriptionSSEnabled=*' }).Count) { return }
    Backup $int
    # the OPEN row's tooltip: fill the stock page's empty slot in place (a slot with text is left alone)
    $key = 'MouseOver_SHADOWS_{0:D2}=' -f $slot
    $tip = 'Open the U2SoftShadows page: multi-light soft shadows, contact shadows and more.'
    $add = [Collections.Generic.List[string]]($intText -split "`r?`n")
    $k = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].StartsWith($key)) { $k = $i } }
    if ($k -ge 0) { if ($lines[$k].Trim() -eq $key) { $lines[$k] = $key + $tip } }
    else { $add.Add($key + $tip) }
    $at = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].StartsWith('OptionDescription')) { $at = $i } }
    if ($at -lt 0) { $at = $lines.Count - 1 }
    $lines.InsertRange($at + 1, [string[]]$add)
    Write-Ini $int $lines
    Say "  added the page's labels to $(Split-Path $int -Leaf)"
}

function Remove-MenuPage($ui) {
    if (-not (Test-Path $ui)) { return }
    $lines = Read-Ini $ui
    $s = $lines.IndexOf($pageMark)
    if ($s -lt 0) { return }
    $e = $lines.IndexOf('Register=OptionWidgets_SOFTSHADOWS', $s)
    if ($e -lt 0) { Say "  $(Split-Path $ui -Leaf): page end not found, left as is" 'Yellow'; return }
    if ($s -gt 0 -and -not $lines[$s - 1].Trim()) { $s-- }
    $lines.RemoveRange($s, $e - $s + 1)
    $b = $lines.IndexOf("`tComponent=OptionButton:SSOpen/SoftShadows")
    if ($b -gt 0) { $lines.RemoveRange($b - 1, 4) }
    foreach ($exact in @($stateOurs, $transOurs)) { $i = $lines.IndexOf($exact); if ($i -ge 0) { $lines.RemoveAt($i) } }
    for ($i = $lines.Count - 1; $i -ge 0; $i--) { if ($lines[$i] -match '^Component=OptionDescription:\d\d/\d+/SSOpenSoft$') { $lines.RemoveAt($i) } }
    Write-Ini $ui $lines
    Say "  removed the options page from $(Split-Path $ui -Leaf)"
}

function Remove-MenuText($int) {
    if (-not (Test-Path $int)) { return }
    $lines = Read-Ini $int
    $n = $lines.Count
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $l = $lines[$i]
        if ($l -match '^(SubTitleSoftShadows|OptionButtonSSOpen|OptionDescriptionSS\w+|MouseOver_SOFTSHADOWS_\d\d)=') { $lines.RemoveAt($i) }
        elseif ($l -match '^(MouseOver_SHADOWS_\d\d=)Open the U2SoftShadows page') { $lines[$i] = $Matches[1] }
    }
    if ($lines.Count -ne $n) { Write-Ini $int $lines; Say "  removed the page's labels from $(Split-Path $int -Leaf)" }
}
# U2SS-MENU

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
    # 3. 1.2 -> 1.3: settings saved by older versions would override the new defaults
    $lines = Read-Ini $userIni
    $r = Section-Range $lines 'U2SoftShadows.SSShadowController'
    if ($r) {
        $old = @('GradientLength=600', 'GradientScale=1.100000', 'GradientScale=1.1', 'LightResolution=0', 'UnseenTime=1.000000', 'UnseenTime=1')
        $n = 0
        for ($i = $r[1]; $i -gt $r[0]; $i--) {
            if ($old -contains $lines[$i].Trim() -or $lines[$i].Trim() -like 'LightResolution=*') { $lines.RemoveAt($i); $n++ }
        }
        if ($n) { Write-Ini $userIni $lines; Say "  updated $n settings from an older version to the 1.3 defaults" }
    }

    # 4. the options page (Options > MISC > "Soft Shadows (mod): OPEN")
    $script:menuSlot = 0
    foreach ($pair in @(@('UIScripts\ModMenus.ui', 'System\ModMenus.int'), @('UIScripts\U2Menus.ui', 'System\U2Menus.int'))) {
        $ui = Join-Path $game $pair[0]
        if (-not (Test-Path $ui)) { continue }
        $script:menuSlot = 0
        Add-MenuPage $ui
        if ($script:menuSlot -gt 0) { Add-MenuText (Join-Path $game $pair[1]) $script:menuSlot }
    }
    Say "`nDone! Start the game - System\Unreal2.log should show 'U2SoftShadows: manager active'." 'Green'
    Say 'Settings: in game, Options > MISC > "Soft Shadows (mod): OPEN" (or README.txt).'
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
    foreach ($pair in @(@('UIScripts\ModMenus.ui', 'System\ModMenus.int'), @('UIScripts\U2Menus.ui', 'System\U2Menus.int'))) {
        Remove-MenuPage (Join-Path $game $pair[0])
        Remove-MenuText (Join-Path $game $pair[1])
    }
    $u = Join-Path $sys 'U2SoftShadows.u'
    if (Test-Path $u) { Remove-Item $u; Say '  deleted U2SoftShadows.u' }
    Say "`nDone. (The larger shadow texture pool in Unreal2.ini is harmless and was left as is.)" 'Green'
}
exit 0
