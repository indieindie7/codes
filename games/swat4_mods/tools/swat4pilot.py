"""SWAT 4 pilot: run SWAT 4 + SwatMinds behind the user's windows and drive it from code.

Uses the U2Input dinput8 proxy (codes/tools/C/U2Input, bin/dinput8.dll copied to
Content\\System): pipe \\\\.\\pipe\\U2Input-<pid> for focus/cursor/click/keys, PrintWindow for shots.

  py swat4pilot.py start            launch (refuses if the user's own game is running), park behind
  py swat4pilot.py shot out.png     capture the game window (works while covered)
  py swat4pilot.py click X Y        client pixels
  py swat4pilot.py key VK|NAME      e.g. key ESCAPE, key 0x0D
  py swat4pilot.py exec "cmd"       console line (opens with the console key, types, Enter)
  py swat4pilot.py hold W 1.5       hold a key
  py swat4pilot.py look DX DY       turn
  py swat4pilot.py fire 0.3         hold fire
  py swat4pilot.py log [PATTERN]    SwatMinds lines (or PATTERN) from the game log
  py swat4pilot.py stop             close the pilot's game
"""
import ctypes, os, re, subprocess, sys, time
from ctypes import wintypes as W

U2INPUT = r"C:\Users\john\Documents\github\codes\tools\C\U2Input"
sys.path.insert(0, U2INPUT)
import u2input  # noqa: E402

GAME = r"F:\gogGames\SWAT 4"
EXE = GAME + r"\Content\System\Swat4.exe"
SYSDIR = GAME + r"\SwatMinds\System"
LOG = SYSDIR + r"\Swat4.log"
PIDFILE = os.path.join(os.environ["TEMP"], "swat4pilot.pid")
IMAGE = "Swat4.exe"
u = ctypes.windll.user32
VK = {"ESCAPE": 0x1B, "ENTER": 0x0D, "TAB": 0x09, "SPACE": 0x20, "F1": 0x70, "BACK": 0x08,
      "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27, "TILDE": 0xC0, "PGUP": 0x21}


def vk(name):
    name = name.upper()
    if name in VK:
        return VK[name]
    if name.startswith("0X"):
        return int(name, 16)
    if len(name) == 1:
        return ord(name)
    raise SystemExit("unknown key " + name)


def pilot_pid():
    try:
        pid = int(open(PIDFILE).read())
    except (OSError, ValueError):
        return None
    return pid if pid == u2input.game_pid(IMAGE) else None


def window(pid):
    found = []

    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def cb(h, _):
        p = W.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        t = ctypes.create_unicode_buffer(64)
        u.GetWindowTextW(h, t, 64)
        if p.value == pid and t.value == "Swat4":            # the game window, not splash/log/IME ones
            found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None


def park(h, prev):
    """Move the game left of the monitor (PrintWindow still captures it) and keep the user's focus."""
    u.ShowWindow(h, 4)                                    # SW_SHOWNOACTIVATE (also un-minimizes)
    u.SetWindowPos(h, 0, -2400, 0, 0, 0, 0x1 | 0x4 | 0x10)  # NOSIZE|NOZORDER|NOACTIVATE
    if prev and u.GetForegroundWindow() == h:
        u.SetForegroundWindow(prev)


def inp():
    pid = pilot_pid()
    if not pid:
        raise SystemExit("no pilot game running (py swat4pilot.py start)")
    return u2input.U2Input(pid=pid), pid


def start():
    if u2input.game_pid(IMAGE) and not pilot_pid():
        raise SystemExit("the user's own SWAT 4 is running; not touching it")
    if pilot_pid():
        stop()
    prev = u.GetForegroundWindow()
    si = subprocess.STARTUPINFO()
    si.dwFlags, si.wShowWindow = 1, 7                     # SW_SHOWMINNOACTIVE: never shows on screen
    ini = open(SYSDIR + r"\Swat4.ini", encoding="latin-1").read()  # windowed copy: fullscreen grabs focus
    ini = re.sub(r"(?m)^StartupFullscreen=.*$", "StartupFullscreen=False", ini)
    open(SYSDIR + r"\SwatPilot.ini", "w", encoding="latin-1").write(ini)
    p = subprocess.Popen([EXE, "-nointro", "INI=SwatPilot.ini"], cwd=SYSDIR, startupinfo=si)
    open(PIDFILE, "w").write(str(p.pid))
    h = None
    for _ in range(240):                                  # wait for the menu window, touch it once
        time.sleep(0.25)
        h = window(p.pid)
        if h:
            break
    if not h:
        raise SystemExit("no game window")
    time.sleep(20)                                        # let the splash scene + menu load first
    park(window(p.pid), prev)                                         # (re-ordering it every 250 ms crashed the game)
    u2input.U2Input(pid=p.pid).focus(True)
    print("pilot game pid", p.pid)


def stop():
    pid = pilot_pid()
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass


def shot(path):
    pid = pilot_pid()
    h = window(pid) if pid else None
    if not h:
        raise SystemExit("no pilot window")
    u2input_probe = __import__("probe")
    u2input_probe.game_window = lambda: h
    u2input_probe.capture(path)
    print(path)


def log(pattern=r"^SwatMinds:"):
    rx = re.compile(pattern)
    with open(LOG, "rb") as f:
        for line in f.read().decode("latin-1").splitlines():
            if rx.search(line):
                print(line)


def main(a):
    if not a:
        raise SystemExit(__doc__)
    c = a[0]
    if c == "start":
        return start()
    if c == "stop":
        return stop()
    if c == "shot":
        return shot(a[1] if len(a) > 1 else os.path.join(os.environ["TEMP"], "swat4pilot.png"))
    if c == "log":
        return log(a[1]) if len(a) > 1 else log()
    i, _ = inp()
    if c == "click":                                      # SWAT 4 menus read window messages, not DirectInput
        i.cursor(int(a[1]), int(a[2])); time.sleep(0.3)
        i.send("wdown 0"); time.sleep(0.15); i.send("wup 0")
    elif c == "cursor":
        i.cursor(int(a[1]), int(a[2]))
    elif c == "key":
        i.vkey(vk(a[1]))
    elif c == "exec":
        i.exec(a[1], open_key=vk(a[2]) if len(a) > 2 else 0xC0)
    elif c == "hold":
        i.vdown(vk(a[1])); time.sleep(float(a[2])); i.vup(vk(a[1]))
    elif c == "look":
        i.move(int(a[1]), int(a[2]))
    elif c == "fire":
        i.down(0); time.sleep(float(a[1]) if len(a) > 1 else 0.2); i.up(0)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
