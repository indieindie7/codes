<#
.SYNOPSIS
    Starts Claude Code's Remote Control server in this repository at login, so the PC can be
    reached from the Claude app (phone or claude.ai/code) every morning, without waking old chats.

.DESCRIPTION
    Runs `claude remote-control` in the repository folder (two levels above this script) and
    starts it again whenever it stops (network drop, update, crash), waiting a little longer
    each time it stops quickly. It first waits until the internet is reachable, as it starts at
    login. Everything it does goes to %LOCALAPPDATA%\claude-remote-control-startup.log.

    Each morning this gives a fresh session: it doesn't carry the old chats' memory. What
    matters between sessions lives in the repo (SESSION_NOTES.md, HANDOFF.md).

    Install once (creates a Startup shortcut that runs this, minimized, at login):
        powershell -ExecutionPolicy Bypass -File tools\remote-control\start-remote-control.ps1 -Install
    Remove it again:
        powershell -ExecutionPolicy Bypass -File tools\remote-control\start-remote-control.ps1 -Uninstall
    Close its window to stop it for this login.

.PARAMETER Dir
    The folder sessions work in. Default: the repository this script is in.
.PARAMETER Name
    The name the first session shows in the Claude app. Default: "<computer name> codes".
.PARAMETER PermissionMode
    Passed to --permission-mode for the sessions (e.g. acceptEdits). Default: Claude's own.
.PARAMETER NetworkWaitSeconds
    How long to wait for the internet at login before trying anyway. Default 300.
#>
[CmdletBinding()]
param(
    [string]$Dir = '',
    [string]$Name = "$env:COMPUTERNAME codes",
    [string]$PermissionMode = '',
    [int]$NetworkWaitSeconds = 300,
    [switch]$Install,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
if (-not $Dir) { $Dir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$Log = Join-Path $env:LOCALAPPDATA 'claude-remote-control-startup.log'

function Write-Log([string]$Message) {
    $line = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $Message
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

function Find-Claude {
    $cmd = Get-Command claude -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
            (Join-Path $env:USERPROFILE '.local\bin\claude.exe'),
            (Join-Path $env:APPDATA 'npm\claude.cmd'),
            (Join-Path $env:LOCALAPPDATA 'Programs\claude\claude.exe'))) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

if ($Install -or $Uninstall) {
    $Shortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'Claude Remote Control.lnk'
}

if ($Install) {
    $claude = Find-Claude
    if (-not $claude) {
        Write-Host 'Claude Code (the claude command) was not found. Install it first: https://claude.com/claude-code'
        exit 1
    }
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Shortcut)
    $link.TargetPath = 'powershell.exe'
    $link.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$PSCommandPath`""
    $link.WorkingDirectory = $Dir
    $link.WindowStyle = 7            # minimized
    $link.Description = 'Claude Code Remote Control in ' + $Dir
    $link.Save()
    Write-Host "Installed: $Shortcut"
    Write-Host "At each login it runs 'claude remote-control' in $Dir (log: $Log)."
    Write-Host "If you have never run 'claude' in that folder, do it once now: it asks whether to trust the folder,"
    Write-Host 'and the login window has nowhere to ask.'
    exit 0
}

if ($Uninstall) {
    if (Test-Path $Shortcut) { Remove-Item $Shortcut; Write-Host "Removed: $Shortcut" }
    else { Write-Host 'Not installed.' }
    exit 0
}

$Host.UI.RawUI.WindowTitle = 'Claude Remote Control (close to stop)'
$claude = Find-Claude
if (-not $claude) {
    Write-Log 'claude not found (not on PATH, nor in the usual install folders): nothing started'
    exit 1
}

# at login the network may not be up yet
$deadline = (Get-Date).AddSeconds($NetworkWaitSeconds)
while ((Get-Date) -lt $deadline) {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        if ($tcp.ConnectAsync('api.anthropic.com', 443).Wait(5000) -and $tcp.Connected) { break }
    } catch { }
    finally { $tcp.Dispose() }
    Start-Sleep -Seconds 5
}

Set-Location $Dir
$rcArgs = @('remote-control', '--name', $Name)
if ($PermissionMode) { $rcArgs += @('--permission-mode', $PermissionMode) }
$delay = 10
while ($true) {
    Write-Log "starting: $claude $($rcArgs -join ' ')   (in $Dir)"
    $started = Get-Date
    & $claude @rcArgs
    Write-Log "claude remote-control stopped (exit code $LASTEXITCODE)"
    # ran for a while: restart soon; stopped quickly: back off (up to 10 minutes)
    if (((Get-Date) - $started).TotalMinutes -gt 10) { $delay = 10 }
    else { $delay = [Math]::Min($delay * 2, 600) }
    Write-Log "starting again in $delay s (close this window to stop)"
    Start-Sleep -Seconds $delay
}
