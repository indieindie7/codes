param([string[]]$Ini = @('bBorderless=False'), [int]$Wait = 40, [string]$Shot = '', [string[]]$Keys = @())
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
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  // keys go to the game's window only (never global input: the user may be working in another app)
  public static void Tap(IntPtr h, byte vk) { uint sc = MapVirtualKey(vk, 0); PostMessage(h, 0x100, (IntPtr)vk, (IntPtr)(1 | (sc << 16))); System.Threading.Thread.Sleep(80); PostMessage(h, 0x101, (IntPtr)vk, (IntPtr)unchecked((int)(0xC0000001 | (sc << 16)))); } }
"@
function Shot($name) { $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); $bmp.Save("$shots\$name"); $g.Dispose(); $bmp.Dispose() }
function Win($p) { $r = New-Object K+RECT; $c = New-Object K+RECT; [void][K]::GetWindowRect($p.MainWindowHandle, [ref]$r); [void][K]::GetClientRect($p.MainWindowHandle, [ref]$c); "window {0}x{1} at {2},{3} client {4}x{5} caption={6}" -f ($r.R-$r.L), ($r.B-$r.T), $r.L, $r.T, $c.R, $c.B, [bool]([K]::GetWindowLong($p.MainWindowHandle, -16) -band 0xC00000) }
$saved = Get-Content "$S\Mydefault.ini"; $savedUser = Get-Content "$S\MyDefUser.ini"
(@('[AdventMod.ModSettings]') + $Ini) | Set-Content "$S\AdventMod.ini" -Encoding ascii
$env:SteamAppId = '3800'; $env:SteamGameId = '3800'; $env:PATH = "C:\Program Files (x86)\Steam;" + $env:PATH
[void](Start-Process -FilePath "$S\advent.exe" -WorkingDirectory $S -PassThru)
Start-Sleep $Wait
$q = Get-Process advent -ErrorAction SilentlyContinue
if (-not $q) { 'GAME NOT RUNNING (crashed?)'; if (Test-Path "$S\advent.log") { Get-Content "$S\advent.log" | Select-Object -Last 15 }; exit 1 }
"start: " + (Win $q)
$n = 0
foreach ($k in $Keys) {
  if ($k -match '^shot') { Shot "$Shot$n.png"; $n++ } elseif ($k -match '^wait(\d+)') { Start-Sleep ([int]$Matches[1]) } else { [K]::Tap($q.MainWindowHandle, [byte]([Convert]::ToInt32($k, 16))); Start-Sleep -Milliseconds 1500; $q.Refresh(); "key ${k}: " + (Win $q) }
}
if ($Shot -and $n -eq 0) { Shot "$Shot.png" }
if (Test-Path "$S\AdventNative.log") { Get-Content "$S\AdventNative.log" }
"AdventMod.ini: " + ((Get-Content "$S\AdventMod.ini") -join ' ; ')
$q.CloseMainWindow() | Out-Null; if (-not $q.WaitForExit(15000)) { $q.Kill(); 'had to kill the game'; Remove-Item "$S\Running.ini" -Confirm:$false -ErrorAction SilentlyContinue }
$now = Get-Content "$S\Mydefault.ini"; $d = Compare-Object $saved $now; if ($d) { "Mydefault.ini changes by the game:"; $d | ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" } }
$saved | Set-Content "$S\Mydefault.ini" -Encoding ascii
$nowU = Get-Content "$S\MyDefUser.ini"; $dU = Compare-Object $savedUser $nowU; if ($dU) { "MyDefUser.ini changes by the game:"; $dU | ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" } }
$savedUser | Set-Content "$S\MyDefUser.ini" -Encoding ascii
"[AdventMod.ModSettings]`r`nbBorderless=False" | Set-Content "$S\AdventMod.ini" -Encoding ascii
