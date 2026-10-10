# Builds and runs tests\hooktest.exe (32-bit) against the mod source with HW_TEST plumbing.
param([string]$Zig = "$env:USERPROFILE\Documents\Tools\zig\zig.exe")
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Mod = Split-Path -Parent $Here
& $Zig cc -target x86-windows-gnu -O1 -std=gnu99 -Wall -DHW_TEST -o "$Here\hooktest.exe" `
    "$Here\hooktest.c" "$Mod\src\hwmod.c" "$Mod\..\src\hydrowater.c" -lkernel32
if ($LASTEXITCODE -ne 0) { throw 'build failed' }
Push-Location $Here
try { & "$Here\hooktest.exe"; $rc = $LASTEXITCODE } finally { Remove-Item "$Here\HydroWater.log" -ErrorAction SilentlyContinue; Pop-Location }
exit $rc
