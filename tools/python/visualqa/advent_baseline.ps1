# Visual QA baselines for Advent Rising: random prints (with character masks) from several stock
# levels, then visual_qa.py baseline per level -> baselines\advent\<level>.json.
# The frames stay in Documents\design-refs\visualqa\advent (game imagery: not for the repo).
#   advent_baseline.ps1 [-Levels level01sectiona,...] [-Prints 10]
param([string[]]$Levels = @('level01sectiona', 'level03sectionb', 'level04sectiona', 'level06sectiona', 'level09sectiona'), [int]$Prints = 10)
$Game = 'H:\SteamLibrary\steamapps\common\Advent Rising\System'
$Mod = 'C:\Users\john\Documents\github\codes\games\advent_rising_mods\AdventMod'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = 'C:\Users\john\Documents\Tools\visualqa\Scripts\python.exe'
$Frames = Join-Path $env:USERPROFILE 'Documents\design-refs\visualqa\advent'
New-Item -ItemType Directory -Force (Join-Path $Here 'baselines\advent') | Out-Null
foreach ($L in $Levels) {
  Get-ChildItem $Game -Filter 'ShotP*' | ForEach-Object { $_.Delete() }
  Set-Location $Mod
  $r = .\test_run.ps1 -Wait (40 + $Prints * 3) -Ini @('bBorderless=False', "DebugCommands=open $L`?Menu=?Game=EonEngine.EonGameInfo") -Steps @('waitcontrol 40', "randomprints $Prints 1.2", 'wait 1') 2>&1 | Select-String 'end state|crash|GAME NOT'
  $Out = Join-Path $Frames $L
  New-Item -ItemType Directory -Force $Out | Out-Null
  Get-ChildItem $Out -Filter 'ShotP*' | ForEach-Object { $_.Delete() }
  Get-ChildItem $Game -Filter 'ShotP*' | Move-Item -Destination $Out
  $n = (Get-ChildItem $Out -Filter 'ShotP?????.bmp').Count
  "$L : $n frames ($r)"
  if ($n -ge 3) {
    & $Py (Join-Path $Here 'visual_qa.py') baseline $Out --save (Join-Path $Here "baselines\advent\$L.json") 2>&1 | Select-String 'baseline of'
    & $Py (Join-Path $Here 'visual_qa.py') score $Out --out (Join-Path $Out 'qa') --baseline (Join-Path $Here "baselines\advent\$L.json") 2>&1 | Select-String 'report.html|HUD'
  }
}
