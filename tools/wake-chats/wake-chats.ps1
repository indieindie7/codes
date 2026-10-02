<#
  Wake Claude chats after the PC starts, so Remote Control reconnects them and they
  can be reached from the phone. (A chat comes back idle after a restart and only
  reconnects once it gets a message; the app's own scheduled tasks are not allowed
  to message chats, hence this.) Written at the user's request, 2026-10-01.

  For each chat title in $Chats: finds the title in the Claude window's sidebar with
  Windows' built-in text recognition (OCR), clicks it, checks the chat header shows
  that title, clicks the message box, types the wake-up line and presses Enter.

    powershell -ExecutionPolicy Bypass -File wake-chats.ps1             # wake them
    powershell -ExecutionPolicy Bypass -File wake-chats.ps1 -DryRun     # only find + log, no clicks
    -Chats "goobi fangames","Daiya fangames"   -StartDelay 90

  Log: wake-chats.log next to this script.
#>
param(
    [string[]]$Chats = @("unreal modding", "goobi fangames", "advent rising modding", "Daiya fangames"),
    [string]$Message = "Good morning - automatic wake-up so Remote Control reconnects after the PC restarted. No work needed: just reply with one short line and wait for me.",
    [int]$StartDelay = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Log = Join-Path $PSScriptRoot "wake-chats.log"
function Say($t) { $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $t; Add-Content -Path $Log -Value $line; Write-Host $line }

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class WakeWin {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, int f, int e);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(150); mouse_event(2,0,0,0,0); mouse_event(4,0,0,0,0); }
  // an Alt tap lets a background process bring a window to the front
  public static void Front(IntPtr h) { if (IsIconic(h)) ShowWindow(h, 9); keybd_event(0x12,0,0,0); keybd_event(0x12,0,2,0); SetForegroundWindow(h); }
}
"@

# ---- Windows OCR (WinRT) ----
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }

# text lines on screen in a rectangle, with their centres in screen pixels
function Ocr-Lines([int]$x, [int]$y, [int]$w, [int]$h) {
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
    $g.Dispose()
    # 2x upscale: the sidebar font is small
    $big = New-Object System.Drawing.Bitmap ($w * 2), ($h * 2)
    $g = [System.Drawing.Graphics]::FromImage($big)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($bmp, 0, 0, $w * 2, $h * 2); $g.Dispose(); $bmp.Dispose()
    $path = Join-Path $env:TEMP "wake-chats-ocr.png"
    $big.Save($path, [System.Drawing.Imaging.ImageFormat]::Png); $big.Dispose()
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $sb = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $res = Await ($engine.RecognizeAsync($sb)) ([Windows.Media.Ocr.OcrResult])
    $stream.Dispose()
    foreach ($line in $res.Lines) {
        $ws = $line.Words
        $l = ($ws | ForEach-Object { $_.BoundingRect.X } | Measure-Object -Minimum).Minimum
        $t = ($ws | ForEach-Object { $_.BoundingRect.Y } | Measure-Object -Minimum).Minimum
        $r = ($ws | ForEach-Object { $_.BoundingRect.X + $_.BoundingRect.Width } | Measure-Object -Maximum).Maximum
        $b = ($ws | ForEach-Object { $_.BoundingRect.Y + $_.BoundingRect.Height } | Measure-Object -Maximum).Maximum
        [pscustomobject]@{ Text = $line.Text; X = $x + ($l + $r) / 4; Y = $y + ($t + $b) / 4 }
    }
}

function Norm($s) { ($s.ToLower() -replace '[^a-z0-9]', '') }

if ($StartDelay -gt 0) { Say "waiting $StartDelay s for the app to settle"; Start-Sleep -Seconds $StartDelay }

# the Claude app's main window (it may take a while to open after login)
$win = $null
for ($i = 0; $i -lt 60 -and -not $win; $i++) {
    $win = Get-Process -Name claude -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -eq "Claude" } | Select-Object -First 1
    if (-not $win) { Start-Sleep -Seconds 5 }
}
if (-not $win) { Say "Claude window not found; nothing done"; exit 1 }
$hwnd = $win.MainWindowHandle

$woke = @(); $missed = @()
foreach ($chat in $Chats) {
    [WakeWin]::Front($hwnd); Start-Sleep -Milliseconds 600
    $r = New-Object WakeWin+RECT; [void][WakeWin]::GetWindowRect($hwnd, [ref]$r)
    $WinW = $r.R - $r.L; $WinH = $r.B - $r.T
    # sidebar: the left ~30% of the window, below the title bar
    $lines = Ocr-Lines $r.L ($r.T + 40) ([int]($WinW * 0.30)) ($WinH - 80)
    $hit = $lines | Where-Object { (Norm $_.Text) -eq (Norm $chat) } | Select-Object -First 1
    if (-not $hit) { $hit = $lines | Where-Object { (Norm $_.Text).StartsWith((Norm $chat)) } | Select-Object -First 1 }
    if (-not $hit) { Say "not found in the sidebar: '$chat' (seen: $(($lines | ForEach-Object Text) -join ' | '))"; $missed += $chat; continue }
    Say ("found '{0}' at {1:0},{2:0}" -f $chat, $hit.X, $hit.Y)
    if ($DryRun) { continue }
    [WakeWin]::Click([int]$hit.X, [int]$hit.Y); Start-Sleep -Seconds 3
    # the chat header (top of the chat area) must now show this title
    $head = Ocr-Lines ($r.L + [int]($WinW * 0.20)) $r.T ([int]($WinW * 0.45)) 50
    if (-not ($head | Where-Object { (Norm $_.Text).Contains((Norm $chat)) })) {
        Say "clicked '$chat' but the chat header shows '$(($head | ForEach-Object Text) -join ' ')'; skipped"; $missed += $chat; continue
    }
    # message box: centre of the chat area, ~56 px above the window bottom
    $mx = $r.L + [int]($WinW * 0.62); $my = $r.B - 56
    [WakeWin]::Click($mx, $my); Start-Sleep -Milliseconds 500
    if ([WakeWin]::GetForegroundWindow() -ne $hwnd) { Say "Claude lost the foreground; stopped before typing into '$chat'"; $missed += $chat; break }
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    [System.Windows.Forms.SendKeys]::SendWait(($Message -replace '([+^%~(){}\[\]])', '{$1}'))
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Say "woke '$chat'"; $woke += $chat
    Start-Sleep -Seconds 2
}
Say ("done: woke [{0}], missed [{1}]" -f ($woke -join ', '), ($missed -join ', '))
