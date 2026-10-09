# Armour-hit pilot run (ARMOUR.md test list). NOT to be run until the user says "GPU free, run".
#   .\run_armour_test.ps1 [-Map level14sectiond] [-Enemy EonCharacters.SeekerInfantry] [-Damage 5]
# The game starts hidden on the map, the pilot waits for control, spawns the enemy 450 units ahead,
# and 3 s later ModArmourGrid fires a 5x8 grid of rays across its body (each a real pistol-sized hit
# when -Damage > 0: sparks on armour, blood on flesh), then the frame is captured (SHOTP). The
# AdventNative.log lines "armour hit:" / "armourgrid:" / "armourcam:" are copied next to this script
# for armour_sheet.py, which draws the hit points over the ref-pose render and the screenshot.
param([string]$Map = 'level14sectiond', [string]$Enemy = 'EonCharacters.SeekerInfantry', [int]$Damage = 5, [int]$Wait = 120, [int]$GridDelay = 20, [int]$Ahead = 200, [string[]]$More = @(), [switch]$NoSpawn, [switch]$Fight, [switch]$Fallback, [switch]$Visible)
$R = "$env:USERPROFILE\Documents\github\codes\games\advent_rising_mods\AdventMod"
$S = 'H:\SteamLibrary\steamapps\common\Advent Rising\System'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$steps = @(
  'WAITCONTROL 30',
  "SPAWN $Enemy $Ahead",
  'WAIT 1',
  'AIM 0 -8',
  "WAIT $($GridDelay - 2)",   # ModArmourGrid fires GridDelay s after the level started (ModArmor's PostBeginPlay)
  'SHOTP',
  'WAIT 1',
  'SHOT',
  'WAIT 2'
)
# GridTest = cols rows damage delay; the delay counts from the mod's start on the level, so it has
# to cover the load + WAITCONTROL + the spawn: 40 s is what a level load takes here, tune after the first run
# the level: a console command on the title screen (ModSettings.DebugCommands); the ?Menu=?Game= part is
# needed. bD3DTrace=True is NOT passed: with it the level's first tick is a General Protection Fault (7 runs, every build)
if ($NoSpawn) { $steps = $steps | Where-Object { $_ -notmatch '^SPAWN' } }
# -Fight: no grid; the player's own gun on the spawned enemy (level14sectiond: Gideon is armed there)
if ($Fight) { $steps = @('WAITCONTROL 30', "SPAWN $Enemy $Ahead", 'WAIT 1', 'AIM 0 -4', 'HOLD FIRE 1.5', 'WAIT 0.5', 'AIM 0 -6', 'HOLD FIRE 1.5', 'WAIT 0.5', 'AIM 0 -2', 'HOLD FIRE 1.5', 'WAIT 1', 'SHOTP', 'WAIT 1'); $GridDelay = 0 }
# -Fallback: the infantry's .amesh moved aside for this run: every hit must come from the bone table
$am = 'H:\SteamLibrary\steamapps\common\Advent Rising\AdventMod\Armour\seekerinfantry.amesh'
if ($Fallback) { Move-Item $am "$am.aside" -Force }
$grid = @("GridTest=5 8 $Damage $GridDelay"); if ($Fight) { $grid = @() }
$ini = @("DebugCommands=open ${Map}?Menu=?Game=EonEngine.EonGameInfo", 'bBorderless=False', 'bGoreLog=True', '', '[AdventMod.ModArmor]', 'bArmorLog=True') + $grid + $More
& "$R\test_run.ps1" -Ini $ini -Wait $Wait -Shot 'armour_run' -Steps $steps -Visible:$Visible
Copy-Item "$S\AdventNative.log" "$Here\armour_run.log" -Force
if ($Fallback) { Move-Item "$am.aside" $am -Force }
Select-String -Path "$Here\armour_run.log" -Pattern 'armour|armor' | ForEach-Object { $_.Line } | Select-Object -First 80
