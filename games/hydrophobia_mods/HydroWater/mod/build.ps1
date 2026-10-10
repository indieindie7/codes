# Builds mod\bin\dinput8.dll (32-bit, the game's architecture) from src\hwmod.c plus the
# HydroWater solver, with Zig as the C compiler (Documents\Tools\zig).
param([string]$Zig = "$env:USERPROFILE\Documents\Tools\zig\zig.exe")
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force "$Here\bin" | Out-Null
& $Zig cc -target x86-windows-gnu -O2 -std=gnu99 -Wall -shared `
    -o "$Here\bin\dinput8.dll" "$Here\src\hwmod.c" "$Here\..\src\hydrowater.c" `
    -lkernel32 -luser32
if ($LASTEXITCODE -ne 0) { throw 'build failed' }
Get-ChildItem "$Here\bin\dinput8.dll" | ForEach-Object { "{0} {1} bytes" -f $_.Name, $_.Length }
