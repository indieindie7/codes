param([string[]]$Ini = @('bBorderless=False'), [int]$Wait = 40, [string]$Shot = '', [string[]]$Keys = @(), [switch]$Visible, [string[]]$Steps = @())
$R = "$env:USERPROFILE\Documents\github\codes\games\advent_rising_mods"; $S = 'H:\SteamLibrary\steamapps\common\Advent Rising\System'; $shots = "$env:LOCALAPPDATA\Temp\claude\C--\f3249b13-f3e8-405c-b38e-bb64ed12fba1\scratchpad"
if (Get-Process advent -ErrorAction SilentlyContinue) { 'game already running'; exit 1 }
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class K { [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetShellWindow();
  // like U2Pilot: park the window beyond the left edge of every monitor, without activating it
  public static void Park(IntPtr h) { RECT r; GetWindowRect(h, out r); int left = GetSystemMetrics(76);
    if (r.R > left) SetWindowPos(h, IntPtr.Zero, left - (r.R - r.L) - 50, r.T, 0, 0, 0x1 | 0x4 | 0x10); }
  // the game grabbed the foreground: give it back to the window the user was in
  public static void GiveBack(IntPtr game, IntPtr prev) { if (prev == IntPtr.Zero || !IsWindow(prev)) prev = GetShellWindow();
    uint t = GetWindowThreadProcessId(game, IntPtr.Zero), me = GetWindowThreadProcessId(GetForegroundWindow(), IntPtr.Zero);
    AttachThreadInput(me, t, true); SetForegroundWindow(prev); AttachThreadInput(me, t, false); }
  // keys go to the game's window only (never global input: the user may be working in another app)
  public static void Tap(IntPtr h, byte vk) { uint sc = MapVirtualKey(vk, 0); PostMessage(h, 0x100, (IntPtr)vk, (IntPtr)(1 | (sc << 16))); System.Threading.Thread.Sleep(80); PostMessage(h, 0x101, (IntPtr)vk, (IntPtr)unchecked((int)(0xC0000001 | (sc << 16)))); } }
"@
# the game's client area, asked from the window itself (works while other windows cover it)
function Shot($name) { $h = (Get-Process advent).MainWindowHandle; $c = New-Object K+RECT; [void][K]::GetClientRect($h, [ref]$c); $bmp = New-Object System.Drawing.Bitmap $c.R, $c.B; $g = [System.Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc(); [void][K]::PrintWindow($h, $dc, 3); $g.ReleaseHdc($dc); $bmp.Save("$shots\$name"); $g.Dispose(); $bmp.Dispose() }
function Win($p) { $r = New-Object K+RECT; $c = New-Object K+RECT; [void][K]::GetWindowRect($p.MainWindowHandle, [ref]$r); [void][K]::GetClientRect($p.MainWindowHandle, [ref]$c); "window {0}x{1} at {2},{3} client {4}x{5} caption={6}" -f ($r.R-$r.L), ($r.B-$r.T), $r.L, $r.T, $c.R, $c.B, [bool]([K]::GetWindowLong($p.MainWindowHandle, -16) -band 0xC00000) }
# a test stopped half way couldn't restore the player's files: they wait in *.test-backup, put them back first
foreach ($f in 'Mydefault.ini','MyDefUser.ini','AdventMod.ini') { if (Test-Path "$S\$f.test-backup") { Copy-Item "$S\$f.test-backup" "$S\$f" -Force; "restored $f from an unfinished test" } }
$saved = Get-Content "$S\Mydefault.ini"; $savedUser = Get-Content "$S\MyDefUser.ini"; $savedMod = Get-Content "$S\AdventMod.ini"
foreach ($f in 'Mydefault.ini','MyDefUser.ini','AdventMod.ini') { Copy-Item "$S\$f" "$S\$f.test-backup" -Force }
$pilot = @(); if ($Steps) { $pilot = @('', '[AdventMod.ModPilot]') + ($Steps | ForEach-Object { "Steps=$_" }) }
(@('[AdventMod.ModSettings]') + $Ini + $pilot) | Set-Content "$S\AdventMod.ini" -Encoding ascii
$env:SteamAppId = '3800'; $env:SteamGameId = '3800'; $env:PATH = "C:\Program Files (x86)\Steam;" + $env:PATH
$prev = [K]::GetForegroundWindow()
$g = Start-Process -FilePath "$S\advent.exe" -WorkingDirectory $S -PassThru
# background mode: for the whole wait, keep the game's window beyond the left edge of every monitor
# and hand the foreground back to whatever the user was in (the game re-centres and activates
# itself when it sets its video mode, so this keeps watching instead of running once)
$end = (Get-Date).AddSeconds($Wait); $gaveBack = 0
while ((Get-Date) -lt $end) {
  if ($g.HasExited) { break }
  if (-not $Visible) {
    $g.Refresh(); $h = $g.MainWindowHandle
    if ($h -ne [IntPtr]::Zero) { [K]::Park($h); if ([K]::GetForegroundWindow() -eq $h) { [K]::GiveBack($h, $prev); $gaveBack++ } }
  }
  Start-Sleep -Milliseconds 50
}
$q = Get-Process advent -ErrorAction SilentlyContinue
if (-not $q) { 'GAME NOT RUNNING (crashed?)'; if (Test-Path "$S\advent.log") { Get-Content "$S\advent.log" | Select-Object -Last 15 }; exit 1 }
"start: " + (Win $q) + " (foreground handed back $gaveBack times)"
$n = 0
foreach ($k in $Keys) {
  if ($k -match '^shot') { Shot "$Shot$n.png"; $n++ } elseif ($k -match '^wait(\d+)') { Start-Sleep ([int]$Matches[1]) } else { [K]::Tap($q.MainWindowHandle, [byte]([Convert]::ToInt32($k, 16))); Start-Sleep -Milliseconds 1500; $q.Refresh(); "key ${k}: " + (Win $q) }
}
if ($Shot -and $n -eq 0) { Shot "$Shot.png" }
if (Test-Path "$S\AdventNative.log") { Get-Content "$S\AdventNative.log" }
"AdventMod.ini: " + ((Get-Content "$S\AdventMod.ini") -join ' ; ')
$q.Refresh(); $c1 = $q.CPU; Start-Sleep 2; $q.Refresh(); "end state: responding $($q.Responding), cpu over 2 s $([math]::Round($q.CPU - $c1, 2)) s"
$q.CloseMainWindow() | Out-Null; if (-not $q.WaitForExit(15000)) { $q.Kill(); 'had to kill the game'; Remove-Item "$S\Running.ini" -Confirm:$false -ErrorAction SilentlyContinue }
$now = Get-Content "$S\Mydefault.ini"; $d = Compare-Object $saved $now; if ($d) { "Mydefault.ini changes by the game:"; $d | ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" } }
$saved | Set-Content "$S\Mydefault.ini" -Encoding ascii
$nowU = Get-Content "$S\MyDefUser.ini"; $dU = Compare-Object $savedUser $nowU; if ($dU) { "MyDefUser.ini changes by the game:"; $dU | ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" } }
$savedUser | Set-Content "$S\MyDefUser.ini" -Encoding ascii
# the player's own AdventMod settings come back as they were
$savedMod | Set-Content "$S\AdventMod.ini" -Encoding ascii
foreach ($f in 'Mydefault.ini','MyDefUser.ini','AdventMod.ini') { [IO.File]::Delete("$S\$f.test-backup") }
