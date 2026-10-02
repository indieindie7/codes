"""U2Ctl: drive a running Unreal II from the command line or from code (through U2Input).

    py -3.13 u2ctl.py exec "summon U2Pawns.U2SkaarjLight"   # any console command
    py -3.13 u2ctl.py hold W 1.5                              # hold a key for 1.5 s (W A S D, SPACE, ...)
    py -3.13 u2ctl.py press F6                                # press and release a key
    py -3.13 u2ctl.py look 300 -50                            # turn: mouse movement in DirectInput units
    py -3.13 u2ctl.py fire 0.5                                # hold the left mouse button
    py -3.13 u2ctl.py click 455 246                           # point at client pixel and click (menus)
    py -3.13 u2ctl.py run script.txt                          # one command per line, "wait S" between

From Python:  from u2ctl import Ctl;  c = Ctl();  c.exec("god");  c.hold("W", 2)

Everything works with the game in the background: the first call switches U2Input's focus
spoofing on (the game believes it's focused; the real mouse and keyboard are never touched).
Keys go in as window messages (how Unreal II reads the keyboard); mouse as DirectInput data.
"""
import shlex
import sys
import time

from u2input import U2Input

VK = {**{c: ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"},
      **{f"F{i}": 0x6F + i for i in range(1, 13)},
      "SPACE": 0x20, "ENTER": 0x0D, "ESC": 0x1B, "TAB": 0x09, "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,
      "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27, "BACKSPACE": 0x08, "TILDE": 0xC0}


def vk(name):
    name = str(name).upper()
    if name in VK:
        return VK[name]
    if name.isdigit():
        return int(name)
    raise ValueError(f"unknown key {name!r}")


class Ctl:
    def __init__(self, pid=None):
        self.inp = U2Input(pid)
        self.inp.focus()

    def exec(self, command):
        return self.inp.exec(command)

    def press(self, key):
        return self.inp.vkey(vk(key))

    def hold(self, key, seconds):
        self.inp.vdown(vk(key))
        time.sleep(seconds)
        return self.inp.vup(vk(key))

    def look(self, dx, dy, steps=10, seconds=0.3):
        """Turn smoothly: the movement spread over a few polls instead of one jump."""
        for i in range(steps):
            self.inp.move(int(dx / steps), int(dy / steps))
            time.sleep(seconds / steps)
        return "ok"

    def fire(self, seconds=0.2, button=0):
        self.inp.down(button)
        time.sleep(seconds)
        return self.inp.up(button)

    def click(self, x, y):
        return self.inp.click_at(int(x), int(y))

    def do(self, line):
        """One text command, as on the command line ("hold W 1", "exec god", "wait 0.5")."""
        a = shlex.split(line)
        if not a or a[0].startswith("#"):
            return ""
        c, args = a[0].lower(), a[1:]
        if c == "wait":
            time.sleep(float(args[0]))
            return "ok"
        if c == "exec":
            return self.exec(" ".join(args))
        if c == "press":
            return self.press(args[0])
        if c == "hold":
            return self.hold(args[0], float(args[1]) if len(args) > 1 else 0.5)
        if c == "look":
            return self.look(float(args[0]), float(args[1]) if len(args) > 1 else 0)
        if c == "fire":
            return self.fire(float(args[0]) if args else 0.2)
        if c == "click":
            return self.click(args[0], args[1])
        raise ValueError(f"unknown command {c!r}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(0)
    ctl = Ctl()
    if a[0] == "run":
        for line in open(a[1], encoding="utf-8"):
            r = ctl.do(line.strip())
            if r:
                print(line.strip(), "->", r)
    else:
        print(ctl.do(" ".join(shlex.quote(x) for x in a)))
