"""Poke a running Unreal II through U2Input and capture its window (parked on a side monitor).

    py -3.13 probe.py OUT.png [cmd ...]      cmds: focus | home | move:DX,DY | click | wait:S
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from PIL import ImageGrab
from u2input import U2Input, game_pid

u = ctypes.windll.user32


def game_window():
    pid = game_pid()
    wins = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        p = wt.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            wins.append(h)
        return True
    u.EnumWindows(cb, 0)
    return wins[0]


class BMI(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


def capture(path):
    """The window's own contents (PrintWindow, full render), even when other windows cover it."""
    from PIL import Image
    h = game_window()
    r = wt.RECT()
    u.GetClientRect(h, ctypes.byref(r))
    w, hh = r.right, r.bottom
    gdi = ctypes.windll.gdi32
    hdc = u.GetDC(h)
    mem = gdi.CreateCompatibleDC(hdc)
    bmp = gdi.CreateCompatibleBitmap(hdc, w, hh)
    old = gdi.SelectObject(mem, bmp)
    u.PrintWindow(h, mem, 1 | 2)                 # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    gdi.SelectObject(mem, old)
    bmi = BMI(ctypes.sizeof(BMI), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * hh * 4)
    gdi.GetDIBits(mem, bmp, 0, hh, buf, ctypes.byref(bmi), 0)
    Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    gdi.DeleteObject(bmp)
    gdi.DeleteDC(mem)
    u.ReleaseDC(h, hdc)


if __name__ == "__main__":
    inp = U2Input()
    for cmd in sys.argv[2:]:
        name, _, arg = cmd.partition(":")
        if name == "focus":
            print(inp.send("focus on"))
        elif name == "home":
            inp.home()
        elif name == "move":
            dx, dy = (int(v) for v in arg.split(","))
            inp.move(dx, dy)
        elif name == "click":
            inp.click(0)
        elif name == "wait":
            time.sleep(float(arg))
        time.sleep(0.25)
    time.sleep(0.5)
    capture(sys.argv[1])
    print("captured", sys.argv[1])
