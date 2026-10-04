# Builds AdventMod: compiles Classes\*.uc with AdventUCC, builds AdventNative.dll,
# and installs AdventMod.u / AdventMod.int / AdventNative.dll into the game's System folder.
param([string]$Game = 'H:\SteamLibrary\steamapps\common\Advent Rising')
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Ucc = Join-Path (Split-Path -Parent $Here) 'AdventUCC'

# death clips (ModDeathAnims imports them): written on the game's own skeleton, so
# generated here rather than kept in the repo. First of all:
# it also writes Classes\ModDeathClips.uc, which the copy below must pick up
New-Item -ItemType Directory -Force "$Game\AdventMod\Anims" | Out-Null
& python (Join-Path (Split-Path -Parent $Here) 'tools\make_psa.py') "$Game\AdventMod\Anims\ModDeaths.psa" marine
if ($LASTEXITCODE -ne 0) { throw 'make_psa failed' }
# 1. script: the compiler reads <game>\AdventMod\Classes and the package list in AdventUCC's own ini
New-Item -ItemType Directory -Force "$Game\AdventMod\Classes" | Out-Null
Remove-Item "$Game\AdventMod\Classes\*.uc" -Confirm:$false -ErrorAction SilentlyContinue
Copy-Item "$Here\Classes\*.uc" "$Game\AdventMod\Classes"
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
cl /nologo /O1 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Foobj\ /LD native\adventnative.c native\d3dtrace.c native\shadowfix.c native\shadowalpha.c native\capture.c /FeSystem\AdventNative.dll /link /NOLOGO user32.lib || exit /b 1
"@ | Set-Content $bat -Encoding ascii
cmd /c $bat | Select-String 'error|warning'
if ($LASTEXITCODE -ne 0) { throw 'native build failed' }

# 3. install
Copy-Item "$Game\System\AdventMod.u" "$Here\System\AdventMod.u" -Force
Copy-Item "$Here\System\AdventNative.dll", "$Here\System\AdventMod.int" "$Game\System" -Force
'installed: ' + ((Get-ChildItem "$Game\System" | Where-Object { $_.Name -match '^Advent(Mod|Native)\.' }).Name -join ', ')
