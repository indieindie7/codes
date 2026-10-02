"""Talk to U2Input (the dinput8.dll proxy in Unreal II's System folder).

    from u2input import U2Input
    inp = U2Input()                 # finds the running Unreal2.exe
    inp.home()                      # cursor to the top-left corner
    inp.move(200, 150)              # relative movement, DirectInput units
    inp.click()                     # left button
    inp.focus()                     # take input while in the background
    inp.click_at(470, 246)          # point at a menu item (client pixels) and click it
    inp.vkey(0x75)                  # F6 (keys go through window messages)

Command line:  py u2input.py ping | move DX DY | click [N] | tap DIK | home
"""
import os
import subprocess
import sys
import time

DIK = {"ESCAPE": 0x01, "RETURN": 0x1C, "SPACE": 0x39, "TAB": 0x0F, "F1": 0x3B, "F6": 0x40, "F9": 0x43,
       "UP": 0xC8, "DOWN": 0xD0, "LEFT": 0xCB, "RIGHT": 0xCD, "GRAVE": 0x29}


def game_pid(image="Unreal2.exe"):
    """The running game's process id (a crashed game can linger in the list after exiting: skipped)."""
    import ctypes
    k32 = ctypes.windll.kernel32
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + image, "/NH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.lower().startswith(image.lower()):
            pid = int(line.split()[1])
            h = k32.OpenProcess(0x1000, False, pid)
            code = ctypes.c_ulong(259)
            if h:
                k32.GetExitCodeProcess(h, ctypes.byref(code))
                k32.CloseHandle(h)
            if code.value == 259:
                return pid
    return None


class U2Input:
    def __init__(self, pid=None, timeout=30):
        pid = pid or game_pid()
        if not pid:
            raise RuntimeError("Unreal2.exe is not running")
        name = r"\\.\pipe\U2Input-%d" % pid
        end = time.time() + timeout
        while True:
            try:
                self.pipe = open(name, "r+b", buffering=0)
                break
            except OSError:
                if time.time() > end:
                    raise RuntimeError("no U2Input pipe (is System\\dinput8.dll the U2Input proxy?)")
                time.sleep(0.5)

    def send(self, line):
        self.pipe.write((line + "\n").encode())
        reply = b""
        while not reply.endswith(b"\n"):
            reply += self.pipe.read(1)
        reply = reply.decode().strip()
        if reply.startswith("error"):
            raise RuntimeError(reply + " (" + line + ")")
        return reply

    def ping(self):
        return self.send("ping")

    def move(self, dx, dy):
        return self.send("move %d %d" % (dx, dy))

    def home(self):
        """Push the cursor into the top-left corner (the UI clamps it there)."""
        for _ in range(4):
            self.move(-4000, -4000)
            time.sleep(0.05)

    def click(self, button=0):
        return self.send("click %d" % button)

    def down(self, button=0):
        return self.send("down %d" % button)

    def up(self, button=0):
        return self.send("up %d" % button)

    def focus(self, on=True):
        """Let the game take input while it isn't the foreground window (never grabs your real mouse)."""
        return self.send("focus " + ("on" if on else "off"))

    def cursor(self, x, y):
        """Menu pointer to client pixel (x, y) (needs focus on)."""
        return self.send("cursor %d %d" % (x, y))

    def click_at(self, x, y, button=0, settle=0.4):
        """Point at (x, y) in the game window's client pixels and click there."""
        self.cursor(x, y)
        time.sleep(settle)
        return self.click(button)

    def vkey(self, vk):
        """Press and release a key by Windows virtual-key code (e.g. 0x75 = F6, 0x1B = Esc)."""
        return self.send("vkey %d" % vk)

    def tap(self, dik):
        return self.send("tap %d" % (DIK.get(str(dik).upper(), dik) if not isinstance(dik, int) else dik))

    def key(self, dik, down=True):
        return self.send("key %d %s" % (dik, "down" if down else "up"))


if __name__ == "__main__":
    a = sys.argv[1:]
    inp = U2Input()
    if not a or a[0] == "ping":
        print(inp.ping())
    elif a[0] == "move":
        print(inp.move(int(a[1]), int(a[2])))
    elif a[0] == "click":
        print(inp.click(int(a[1]) if len(a) > 1 else 0))
    elif a[0] == "tap":
        print(inp.tap(a[1] if not a[1].isdigit() else int(a[1])))
    elif a[0] == "home":
        inp.home(); print("ok")
