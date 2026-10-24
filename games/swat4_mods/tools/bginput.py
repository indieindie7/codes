"""Background window input + capture for DK1 / FS2 (no focus steal).

  py -3.13 -I bginput.py shot <proc> out.png        PrintWindow capture
  py -3.13 -I bginput.py move <proc> x y           WM_MOUSEMOVE (client px)
  py -3.13 -I bginput.py click <proc> x y [r]      L (or R) down/up
  py -3.13 -I bginput.py key <proc> VK             WM_KEYDOWN/UP (e.g. 0x20)
  py -3.13 -I bginput.py info <proc>               hwnd, client size

Messages are posted to the game's window, so the user's real mouse and
keyboard focus stay where they are. Games that read raw input or poll
GetAsyncKeyState will ignore posted messages; then a DLL hook is needed.
"""
import ctypes, sys, struct, zlib
from ctypes import wintypes as W

u32 = ctypes.WinDLL("user32", use_last_error=True)
g32 = ctypes.WinDLL("gdi32")
WM_MOUSEMOVE, WM_LBD, WM_LBU, WM_RBD, WM_RBU = 0x200, 0x201, 0x202, 0x204, 0x205
WM_KEYDOWN, WM_KEYUP = 0x100, 0x101
u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]


def find(proc):
    import subprocess
    pid = None
    out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        f = [x.strip('"') for x in line.split('","')]
        if f[0].lower().startswith(proc.lower()):
            pid = int(f[1]); break
    if pid is None:
        sys.exit(f"no process {proc}")
    found = []
    cb = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    def each(h, _):
        p = W.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            found.append(h)
        return True
    u32.EnumWindows(cb(each), 0)
    if not found:
        sys.exit("no window")
    return found[0]


def size(h):
    r = W.RECT(); u32.GetClientRect(h, ctypes.byref(r))
    return r.right, r.bottom


def lp(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def shot(h, path, tries=10):
    # DK1 (OpenGL) returns an all-black frame now and then: retry
    for _ in range(tries):
        if grab(h, path):
            return
        import time; time.sleep(0.1)


def grab(h, path):
    w, ht = size(h)
    hdc = u32.GetDC(h); mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, ht); g32.SelectObject(mdc, bmp)
    ok = u32.PrintWindow(h, mdc, 3)  # client only | render full content
    hdr = struct.pack("<IiiHHIIiiII", 40, w, -ht, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * ht * 4)
    g32.GetDIBits(mdc, bmp, 0, ht, buf, hdr, 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(h, hdc)
    raw = buf.raw
    if not any(raw[i] | raw[i + 1] | raw[i + 2] for i in range(0, len(raw), 4 * 997)):
        return False
    rows = b"".join(b"\0" + bytes(c for i in range(x0, x0 + w * 4, 4) for c in (raw[i + 2], raw[i + 1], raw[i]))
                    for x0 in range(0, len(raw), w * 4))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, ht, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)
    nonblack = sum(1 for i in range(0, len(raw), 4 * 97) if raw[i] | raw[i + 1] | raw[i + 2])
    print(f"PrintWindow={ok} {w}x{ht} nonblack_samples={nonblack}/{len(raw)//(4*97)} -> {path}")
    return True


def main(a):
    cmd, h = a[0], find(a[1])
    if cmd == "info":
        print(h, size(h))
    elif cmd == "shot":
        shot(h, a[2])
    elif cmd == "move":
        u32.PostMessageW(h, WM_MOUSEMOVE, 0, lp(a[2], a[3]))
    elif cmd == "click":
        # DK1 drops input while inactive: fake activation first (no real
        # focus change), then hover a few frames, then press/release slowly.
        import time
        for m, w in ((0x1C, 1), (0x86, 1), (0x06, 1), (0x07, 0)):  # ACTIVATEAPP, NCACTIVATE, ACTIVATE, SETFOCUS
            u32.PostMessageW(h, m, w, 0)
        time.sleep(0.2)
        for _ in range(5):
            u32.PostMessageW(h, WM_MOUSEMOVE, 0, lp(a[2], a[3])); time.sleep(0.05)
        d, up = (WM_RBD, WM_RBU) if len(a) > 4 and a[4] == "r" else (WM_LBD, WM_LBU)
        time.sleep(0.2)
        u32.PostMessageW(h, d, 1 if d == WM_LBD else 2, lp(a[2], a[3])); time.sleep(0.1)
        u32.PostMessageW(h, up, 0, lp(a[2], a[3]))
    elif cmd == "key":
        vk = int(a[2], 0)
        u32.PostMessageW(h, WM_KEYDOWN, vk, 1)
        u32.PostMessageW(h, WM_KEYUP, vk, 0xC0000001)


if __name__ == "__main__":
    main(sys.argv[1:])
