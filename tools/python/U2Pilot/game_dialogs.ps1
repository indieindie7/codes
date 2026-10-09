# List the text of any dialog boxes (#32770) the running Unreal2.exe has open: a load that stops at "Browse:" with
# ~0 CPU is usually a hidden modal box ("Paths in <map> should be rebuilt (level changed)! Press OK to exit").
#   powershell -File game_dialogs.ps1 [-Kill]
param([switch]$Kill)
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class GameDialogs { public delegate bool P(IntPtr h, IntPtr l);
[DllImport("user32.dll")] static extern bool EnumWindows(P p, IntPtr l);
[DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr w, P p, IntPtr l);
[DllImport("user32.dll")] static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h, int m, IntPtr w, StringBuilder l);
public static List<string> Dump(int pid) { var r = new List<string>();
 EnumWindows((h,l)=>{ int p; GetWindowThreadProcessId(h,out p); var c=new StringBuilder(256); GetClassName(h,c,256);
  if (p==pid && c.ToString()=="#32770"){ EnumChildWindows(h,(k,l2)=>{ var tt=new StringBuilder(4096); SendMessage(k,0x000D,(IntPtr)4096,tt); if (tt.Length>0) r.Add(tt.ToString()); return true; }, IntPtr.Zero);} return true; }, IntPtr.Zero); return r; } }
"@
$g = Get-Process Unreal2 -ErrorAction SilentlyContinue
if (-not $g) { "no game running"; exit 0 }
foreach ($p in $g) { "pid $($p.Id):"; [GameDialogs]::Dump($p.Id) | ForEach-Object { "  $_" } }
if ($Kill) { Stop-Process -Name Unreal2 -Force; "killed" }
