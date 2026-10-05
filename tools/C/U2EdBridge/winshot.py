"""Picture of UnrealEd's main window (and a list of its child windows) without touching the mouse:
PrintWindow with PW_RENDERFULLCONTENT, which also reads D3D-drawn viewports on Windows 10.
    <hunyuan venv python> winshot.py <out.png> [list]
"""
import ctypes, ctypes.wintypes as wt, sys
from PIL import Image

u, g = ctypes.windll.user32, ctypes.windll.gdi32
u.SetProcessDPIAware()


def pid_of(h):
    p = wt.DWORD()
    u.GetWindowThreadProcessId(h, ctypes.byref(p))
    return p.value


import subprocess
out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEd.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
pid = int(out.split(",")[1].strip('"'))
tops = []
CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def top(h, _):
    if pid_of(h) == pid and u.IsWindowVisible(h):
        r = wt.RECT(); u.GetWindowRect(h, ctypes.byref(r))
        tops.append((h, r.right - r.left, r.bottom - r.top))
    return True


u.EnumWindows(CB(top), 0)
tops.sort(key=lambda t: -t[1] * t[2])
h, w, hh = tops[0]
buf = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, buf, 256)
print("window", buf.value, w, hh)
if len(sys.argv) > 2:
    def child(c, _):
        r = wt.RECT(); u.GetWindowRect(c, ctypes.byref(r))
        b = ctypes.create_unicode_buffer(128); u.GetClassNameW(c, b, 128)
        t = ctypes.create_unicode_buffer(128); u.GetWindowTextW(c, t, 128)
        if r.right - r.left > 200 and r.bottom - r.top > 150 and u.IsWindowVisible(c):
            print("child", c, b.value, repr(t.value), r.left, r.top, r.right - r.left, r.bottom - r.top)
        return True
    u.EnumChildWindows(h, CB(child), 0)
hdc = u.GetWindowDC(h)
mdc = g.CreateCompatibleDC(hdc)
bmp = g.CreateCompatibleBitmap(hdc, w, hh)
g.SelectObject(mdc, bmp)
ok = u.PrintWindow(h, mdc, 2)


class BMI(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


bi = BMI(); bi.biSize = ctypes.sizeof(BMI); bi.biWidth = w; bi.biHeight = -hh; bi.biPlanes = 1; bi.biBitCount = 32
data = ctypes.create_string_buffer(w * hh * 4)
g.GetDIBits(mdc, bmp, 0, hh, data, ctypes.byref(bi), 0)
Image.frombuffer("RGBA", (w, hh), data, "raw", "BGRA", 0, 1).convert("RGB").save(sys.argv[1])
g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(h, hdc)
print("saved", sys.argv[1], "PrintWindow", ok)
