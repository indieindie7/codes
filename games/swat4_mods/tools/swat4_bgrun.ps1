# Run SWAT 4 (SwatMinds) windowed behind other windows, never taking focus.
# Minimized windows skip rendering, which stalls AI movement (10-19), so tests that need moving AI use this.
param([string]$Map = "SP-FoodWall", [int]$Seconds = 120)
$s = "F:\gogGames\SWAT 4\SwatMinds\System"
Add-Type -Namespace W -Name U -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
[DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
'@
Remove-Item "$s\Swat4.log" -ErrorAction SilentlyContinue
$p = Start-Process "F:\gogGames\SWAT 4\Content\System\Swat4.exe" -ArgumentList "`"$Map`?Mutator=SwatMinds.SwatMindsMutator`" -nointro -windowed" -WorkingDirectory $s -WindowStyle Minimized -PassThru
$t = 0
while ($t -lt $Seconds) {
    Start-Sleep 2; $t += 2; $p.Refresh()
    $h = $p.MainWindowHandle
    if ($h -ne [IntPtr]::Zero) {
        [void][W.U]::ShowWindow($h, 4)                                   # SW_SHOWNOACTIVATE
        [void][W.U]::SetWindowPos($h, [IntPtr]1, 0, 0, 0, 0, 0x0013)     # HWND_BOTTOM, NOSIZE|NOMOVE|NOACTIVATE
    }
}
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
