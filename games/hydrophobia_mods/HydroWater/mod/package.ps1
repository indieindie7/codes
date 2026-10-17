# Builds the DLL and zips the Nexus release: mod\dist\HydroWater-<version>.zip containing
# dinput8.dll, HydroWater.ini and README.txt (drop all three into the game folder).
param([string]$Version = '0.1.0')
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$Here\build.ps1"
New-Item -ItemType Directory -Force "$Here\dist" | Out-Null
$Zip = "$Here\dist\HydroWater-$Version.zip"
Remove-Item $Zip -ErrorAction SilentlyContinue
Compress-Archive -Path "$Here\bin\dinput8.dll", "$Here\HydroWater.ini", "$Here\README.txt" -DestinationPath $Zip
Get-Item $Zip | ForEach-Object { "{0} {1} bytes" -f $_.Name, $_.Length }
