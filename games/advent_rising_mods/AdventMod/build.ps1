# Builds AdventMod: compiles Classes\*.uc with AdventUCC, builds AdventNative.dll,
# and installs AdventMod.u / AdventMod.int / AdventNative.dll into the game's System folder.
param([string]$Game = 'H:\SteamLibrary\steamapps\common\Advent Rising', [switch]$GraphicsOnly, [switch]$JiggleSkin)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Ucc = Join-Path (Split-Path -Parent $Here) 'AdventUCC'

# death clips (ModDeathAnims imports them): written on the game's own skeleton, so
# generated here rather than kept in the repo. First of all:
# it also writes Classes\ModDeathClips.uc, which the copy below must pick up
New-Item -ItemType Directory -Force "$Game\AdventMod\Anims" | Out-Null
& python (Join-Path (Split-Path -Parent $Here) 'tools\make_psa.py') "$Game\AdventMod\Anims\ModDeaths.psa" marine
if ($LASTEXITCODE -ne 0) { throw 'make_psa failed' }
# the energy blade's swings (ModBladeAnims): the chosen Kimodo takes in AnimsBlade
& python (Join-Path (Split-Path -Parent $Here) 'tools\make_psa.py') "$Game\AdventMod\Anims\ModBladeSwings.psa" marine (Join-Path $Here 'AnimsBlade')
if ($LASTEXITCODE -ne 0) { throw 'make_psa (blade) failed' }
# the Seeker hound's knockdowns and deaths (ModHoundAnims): hand-keyed in AnimsHound, on its own skeleton
& python (Join-Path (Split-Path -Parent $Here) 'tools\make_psa.py') "$Game\AdventMod\Anims\ModHound.psa" seekerhound (Join-Path $Here 'AnimsHound')
if ($LASTEXITCODE -ne 0) { throw 'make_psa (hound) failed' }
# 1. script: the compiler reads <game>\AdventMod\Classes and the package list in AdventUCC's own ini
New-Item -ItemType Directory -Force "$Game\AdventMod\Classes" | Out-Null
Remove-Item "$Game\AdventMod\Classes\*.uc" -Confirm:$false -ErrorAction SilentlyContinue
Copy-Item "$Here\Classes\*.uc" "$Game\AdventMod\Classes"
# -GraphicsOnly: the AdventGraphicalMod build (same classes, gore and combat off by default);
# the result is kept as System\AdventMod-graphics.u for package.py --graphics, and the game is
# left with the full build only if you build again without the switch
if ($GraphicsOnly) {
  $ms = "$Game\AdventMod\Classes\ModSettings.uc"
  (Get-Content $ms -Raw) -replace 'bGraphicsOnly=False', 'bGraphicsOnly=True' | Set-Content $ms -NoNewline -Encoding ascii
}
# -JiggleSkin: the Seeker skin with the plates filled from the flesh (tools/jiggle_fill.py, JIGGLE.md
# phase B) goes into THIS build only: the .tga is copied beside the game's textures and the GAME-FOLDER
# copy of ModJiggleSkinBase.uc (not the repo) gets the #exec TEXTURE IMPORT and the Skin default, so the
# texture lands in the local AdventMod.u and ModJiggle can put it on the Seekers' Skins[0] (bJiggleSkin;
# a run-time load by name of anything inside AdventMod answers nothing, hence compile time). Game pixels:
# never in git, never in the release package (package.py builds without the switch)
if ($JiggleSkin) {
  $tga = "$env:USERPROFILE\Documents\AdventRising_meshes\jiggle\tex\seeker_infantry_filled.tga"
  if (-not (Test-Path $tga)) { throw "jiggle skin missing: $tga (run tools/jiggle_fill.py, see JIGGLE.md)" }
  New-Item -ItemType Directory -Force "$Game\AdventMod\Textures" | Out-Null
  Copy-Item $tga "$Game\AdventMod\Textures\seeker_infantry_filled.tga" -Force
  $sb = "$Game\AdventMod\Classes\ModJiggleSkinBase.uc"
  $t = Get-Content $sb -Raw
  $t = $t -replace 'class ModJiggleSkinBase extends Object;', "class ModJiggleSkinBase extends Object;`r`n`r`n#exec TEXTURE IMPORT NAME=SeekerSkinJ FILE=Textures\seeker_infantry_filled.tga GROUP=Skins MIPS=1"
  $t = $t -replace 'defaultproperties\s*\{', "defaultproperties`r`n{`r`n     Skin=Texture'AdventMod.Skins.SeekerSkinJ'"
  Set-Content $sb $t -NoNewline -Encoding ascii
}
# textures the classes import with #exec (paths relative to <game>\AdventMod)
New-Item -ItemType Directory -Force "$Game\AdventMod\Textures" | Out-Null
Copy-Item "$Here\Textures\*.tga" "$Game\AdventMod\Textures" -Force
# gib parts (ModGibParts imports them): cut from the game's own meshes, so they live
# outside the repo, in Documents\AdventRising_meshes\gibs (tools/ukx_mesh.py + GibSplit)
$Gibs = "$env:USERPROFILE\Documents\AdventRising_meshes\gibs"
New-Item -ItemType Directory -Force "$Game\AdventMod\Gibs" | Out-Null
foreach ($set in (Select-String -Path "$Here\Classes\ModGibParts.uc" -Pattern 'FILE=Gibs\\(\S+)' -AllMatches).Matches) {
  $f = $set.Groups[1].Value; $src = Join-Path $Gibs (Join-Path ($f -replace '_(head|torso_\w+|[lr]_\w+)\.ase$', '') $f)
  if (-not (Test-Path $src)) { throw "gib part missing: $src (run tools/ukx_mesh.py and GibSplit)" }
  # the engine's ASE import mirrors an axis, which turns the parts inside out: reverse
  # their winding on the way in
  & python (Join-Path (Split-Path -Parent $Here) 'tools\ase_flip.py') $src "$Game\AdventMod\Gibs\$f"
  if ($LASTEXITCODE -ne 0) { throw "ase_flip failed on $f" }
}
# the energy blade (ModBlade), our own mesh
Copy-Item "$Here\Meshes\blade.ase" "$Game\AdventMod\Gibs\blade.ase" -Force
# rubble pieces (ModRubble), our own meshes
Copy-Item "$Here\Meshes\rubble*.ase" "$Game\AdventMod\Gibs" -Force
# armour plates (ModArmorPlate), our own meshes
Copy-Item "$Here\Meshes\plate_*.ase" "$Game\AdventMod\Gibs" -Force
# the gib card (ModGibCard), our own quad
Copy-Item "$Here\Meshes\gib_card.ase" "$Game\AdventMod\Gibs" -Force
# the stump cap (ModStump), our own mesh
Copy-Item "$Here\Meshes\stump.ase" "$Game\AdventMod\Gibs\stump.ase" -Force
# the Seeker infantry with jiggle bones (ModJiggleMesh imports it, JIGGLE.md): re-rigged from the
# game's own mesh by tools/jiggle_rig.py into Documents\AdventRising_meshes\jiggle, so it lives
# outside the repo. Missing = the rig step wasn't run: the build stops rather than ship a stale mesh
$JiggleDir = "$env:USERPROFILE\Documents\AdventRising_meshes\jiggle"
$JigglePsk = "$JiggleDir\seekerinfantry_jiggle_import.psk"
if (-not (Test-Path $JigglePsk)) { throw "jiggle mesh missing: $JigglePsk (run tools/jiggle_rig.py build, see JIGGLE.md)" }
New-Item -ItemType Directory -Force "$Game\AdventMod\Meshes" | Out-Null
Copy-Item $JigglePsk "$Game\AdventMod\Meshes\seekerinfantry_jiggle.psk" -Force
# the stock-space copy beside the game's meshes, so the armour data (below) covers the jiggle mesh too
Copy-Item "$JiggleDir\seekerinfantry_jiggle.psk" "$env:USERPROFILE\Documents\AdventRising_meshes\SeekerInfantryJ.psk" -Force
# armour sections (ModArmor's per-hit test, ARMOUR.md): the enemies' triangles with their armour
# flag, from the game's own meshes and masks, so they live in the game folder, not the repo
New-Item -ItemType Directory -Force "$Game\AdventMod\Armour" | Out-Null
& py -I (Join-Path (Split-Path -Parent $Here) 'tools\make_armour_data.py') "$env:USERPROFILE\Documents\AdventRising_meshes" "$Game\Textures" "$Game\AdventMod\Armour" | Select-String 'armour faces|refused|no psk'
if ($LASTEXITCODE -ne 0) { throw 'make_armour_data failed' }
# ragdoll skeletons (tools/make_ka.py): the engine reads <game>\KarmaData\*.ka
New-Item -ItemType Directory -Force "$Game\KarmaData" | Out-Null
Copy-Item "$Here\KarmaData\*.ka" "$Game\KarmaData" -Force
$ini = "$Ucc\work\AdventUCC.ini"
if (-not (Test-Path $ini)) { New-Item -ItemType Directory -Force "$Ucc\work" | Out-Null; Copy-Item "$Game\System\default.ini" $ini }
$lines = Get-Content $ini | Where-Object { $_ -ne 'EditPackages=UnrealEd' }
if ($lines -notcontains 'EditPackages=AdventMod') { $lines = $lines -replace '^EditPackages=Interface$', "EditPackages=Interface`r`nEditPackages=AdventMod" }
$lines | Set-Content $ini -Encoding ascii
# make only builds a package that isn't there: move the installed one aside, and put it
# back if the compile fails (a game started without AdventMod.u crashes at its first menu)
$prev = "$Game\System\AdventMod.u.build-previous"
if (Test-Path "$Game\System\AdventMod.u") { Move-Item "$Game\System\AdventMod.u" $prev -Force }
& "$Ucc\AdventUCC.exe" make | Select-Object -Last 8
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$Game\System\AdventMod.u")) {
  if (Test-Path $prev) { Move-Item $prev "$Game\System\AdventMod.u" -Force; 'compile failed: the previous AdventMod.u is back in place' }
  throw 'script compile failed'
}
if (Test-Path $prev) { [IO.File]::Delete($prev) }

# 2. native
$bat = "$env:TEMP\adventnative_build.bat"
@"
@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsamd64_x86.bat" >nul 2>nul
cd /d "$Here"
if not exist obj mkdir obj
cl /nologo /O1 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Foobj\ /LD native\adventnative.c native\d3dtrace.c native\shadowfix.c native\karmafix.c native\shadowalpha.c native\capture.c native\footik.c native\armour.c native\jiggle.c /FeSystem\AdventNative.dll /link /NOLOGO user32.lib || exit /b 1
"@ | Set-Content $bat -Encoding ascii
cmd /c $bat | Select-String 'error|warning'
if ($LASTEXITCODE -ne 0) { throw 'native build failed' }

# 3. install
if ($GraphicsOnly) { Copy-Item "$Game\System\AdventMod.u" "$Here\System\AdventMod-graphics.u" -Force; "graphics-only build: the game now runs it too; build again without -GraphicsOnly for the full mod" }
else { Copy-Item "$Game\System\AdventMod.u" "$Here\System\AdventMod.u" -Force }
Copy-Item "$Here\System\AdventNative.dll", "$Here\System\AdventMod.int" "$Game\System" -Force
'installed: ' + ((Get-ChildItem "$Game\System" | Where-Object { $_.Name -match '^Advent(Mod|Native)\.' }).Name -join ', ')
