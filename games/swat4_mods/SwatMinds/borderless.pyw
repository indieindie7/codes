# SwatMinds borderless helper: makes the windowed Swat4 window borderless fullscreen
# on its monitor and locks the mouse inside it while it has focus. Exits with the game.
# Run: pythonw borderless.pyw   (LaunchSwatMinds.bat starts it)
import ctypes, time
from ctypes import wintypes as W

u = ctypes.windll.user32
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_POPUP, WS_VISIBLE = 0x80000000, 0x10000000
WS_EX_DLGMODALFRAME, WS_EX_CLIENTEDGE, WS_EX_STATICEDGE, WS_EX_WINDOWEDGE = 0x1, 0x200, 0x20000, 0x100
SWP_FRAMECHANGED, SWP_NOZORDER, SWP_NOOWNERZORDER, SWP_NOACTIVATE = 0x20, 0x4, 0x200, 0x10
MONITOR_DEFAULTTONEAREST = 2
u.GetWindowLongW.restype = ctypes.c_long
u.SetWindowLongW.argtypes = [W.HWND, ctypes.c_int, ctypes.c_long]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD)]

def find_game():
    found = []
    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def cb(h, _):
        pid = W.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if u.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            u.GetClassNameW(h, buf, 256)
            t = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(h, t, 256)
            if "SWAT 4" in t.value or "Swat4" in t.value or "SWAT4" in t.value:
                found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None

def make_borderless(h):
    mi = MONITORINFO(); mi.cbSize = ctypes.sizeof(mi)
    u.GetMonitorInfoW(u.MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST), ctypes.byref(mi))
    r = mi.rcMonitor
    style = u.GetWindowLongW(h, GWL_STYLE)
    want = ctypes.c_long(WS_POPUP | WS_VISIBLE).value
    ex = u.GetWindowLongW(h, GWL_EXSTYLE)
    cur = W.RECT(); u.GetWindowRect(h, ctypes.byref(cur))
    if style == want and (cur.left, cur.top, cur.right, cur.bottom) == (r.left, r.top, r.right, r.bottom):
        return r
    u.SetWindowLongW(h, GWL_STYLE, want)
    u.SetWindowLongW(h, GWL_EXSTYLE, ex & ~(WS_EX_DLGMODALFRAME | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE | WS_EX_WINDOWEDGE))
    u.SetWindowPos(h, 0, r.left, r.top, r.right - r.left, r.bottom - r.top,
                   SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_NOACTIVATE)  # never steal focus
    return r

def main():
    t0 = time.time()
    h = None
    while h is None:
        h = find_game()
        if h is None:
            if time.time() - t0 > 120:
                return
            time.sleep(0.5)
    clipped = False
    r = None
    while u.IsWindow(h):
        if u.IsIconic(h):  # minimized: leave it, restyling would restore it
            if clipped:
                u.ClipCursor(None); clipped = False
            time.sleep(0.25)
            continue
        r = make_borderless(h)  # re-apply: the game resets its window on resolution changes
        if u.GetForegroundWindow() == h:
            u.ClipCursor(ctypes.byref(r))
            clipped = True
        elif clipped:
            u.ClipCursor(None)
            clipped = False
        time.sleep(0.25)
    u.ClipCursor(None)

main()
