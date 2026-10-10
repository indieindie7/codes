# Builds bin\hydrowater.dll (64-bit, for the Python harness) and bin\hydrowater32.dll
# (32-bit, the game's architecture) with Zig as the C compiler.
param([string]$Zig = "$env:USERPROFILE\Documents\Tools\zig\zig.exe")
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force "$Here\bin" | Out-Null
& $Zig cc -target x86_64-windows-gnu -O2 -std=c99 -Wall -shared -o "$Here\bin\hydrowater.dll" "$Here\src\hydrowater.c"
if ($LASTEXITCODE -ne 0) { throw 'build failed (64-bit)' }
& $Zig cc -target x86-windows-gnu -O2 -std=c99 -Wall -shared -o "$Here\bin\hydrowater32.dll" "$Here\src\hydrowater.c"
if ($LASTEXITCODE -ne 0) { throw 'build failed (32-bit)' }
Get-ChildItem "$Here\bin\*.dll" | ForEach-Object { "{0} {1} bytes" -f $_.Name, $_.Length }
