param([string]$Tension = 'True', [string]$Spasm = '1.0', [int]$Wait = 60)
# R1 tension clips: 5 Marine deaths + a shot into each body, recorded by wincap at 30 fps.
# -Visible: the game window stays on screen (a parked off-screen window recorded black, 10-11).
$A = "$env:USERPROFILE\Documents\github\wt9\games\advent_rising_mods\AdventMod"
$W = "$env:USERPROFILE\Documents\github\codes\tools\WinCap\wincap.ps1"
# the recorder starts once the game window exists and stops itself when advent.exe exits
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',
  "while (-not (Get-Process advent -EA 0 | Where-Object { `$_.MainWindowHandle -ne 0 })) { Start-Sleep -Milliseconds 200 }; Start-Sleep 2; & '$W' -Exe advent.exe -Fps 30 -Background"
$steps = @('WAITCONTROL', 'WAIT 2')
$kills = @(@(-120, 'spine1'), @(0, 'head'), @(120, 'leftUpLeg'), @(-60, 'rightArm'), @(60, 'spine2'))
foreach ($k in $kills) {
  $steps += "SPAWN EonCharacters.Marine 350 $($k[0])", 'WAIT 1.5', "HURT 275 EonWeapons.dmgType_HumanPistolFire $($k[1])", 'WAIT 0.25', 'SHOOTCORPSE', 'WAIT 2.5'
}
Set-Location $A
.\test_run.ps1 -Visible -Wait $Wait -Ini 'bBorderless=False', 'bGoreLog=True', 'DebugCommands=open level04sectiona', '',
  '[AdventMod.ModReact]', 'bPoweredRagdoll=True', 'bDeathAnims=False', "bTension=$Tension", "SpasmU=$Spasm",
  'bFlinch=False', 'bKnockdown=False', 'bStagger=False', '', '[AdventMod.ModMinds]', 'bMinds=False', '',
  '[AdventMod.ModGore]', 'GibOverkill=100000' -Steps $steps
