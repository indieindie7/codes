r"""U2Pilot - launches Unreal II, plays a scripted sequence of inputs, and records it.

    python u2pilot.py scripts\smoke_test.txt
    python u2pilot.py scripts\smoke_test.txt --keep-open

Each run writes to runs\<timestamp>_<script>\: video.mp4, sheet.png (contact
sheet), any `shot` screenshots, the game log and a pilot log.

While a script runs it drives the real keyboard and mouse, so don't touch the
PC. Press F12 at any time to abort (the pilot releases all keys, stops the
recording and leaves the game open).

Script commands (one per line, '#' starts a comment):
  map NAME                 start the game straight into this map (must come first)
  waitlevel [TIMEOUT]      wait until the log says a level is up for play (default 60s)
  waitlog TEXT [TIMEOUT]   wait until the game log contains TEXT
  waitplay [TIMEOUT]       wait until any cutscene (letterboxed view) is over (default 120s)
  wait SECONDS
  record start | record stop
  key K [SECONDS]          tap a key, or hold it for SECONDS
  keys K1+K2 SECONDS       hold several keys together (e.g. w+shift 3)
  look DX DY [SECONDS]     turn by a relative mouse movement, spread over SECONDS
  click [left|right] [SECONDS]   tap or hold a mouse button
  clickat X Y              move the cursor to X,Y (in 1600x900 window coords) and click
  console TEXT             open the console, type TEXT, press Enter
  type TEXT                type text into whatever has focus
  shot NAME                save a screenshot as NAME.png
  quit                     close the game via the console 'exit' command

Background mode (--background, or a first line "background"): the steps are run
by the PilotDriver mutator inside the game instead, so the game never takes
focus and your keyboard/mouse stay yours. Frames come from in-game screenshots.
Steps there: map, waitcontrol, wait, move FWD STRAFE SECS, turn YAW PITCH SECS,
fire SECS, altfire SECS, jump, crouch 1|0, run 1|0, console CMD, shots INTERVAL,
shot, mark TEXT, quit (see U2PilotDriver\Classes\PilotDriver.uc).
"""
import argparse, ctypes, ctypes.wintypes as wt, datetime, glob, os, re, shutil, subprocess, sys, time

import imageio_ffmpeg

GAME_SYSTEM = os.environ.get("U2PILOT_SYSTEM",   # U2PILOT_SYSTEM: run from another System folder (a test copy)
                             r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System")
GAME_EXE = os.path.join(GAME_SYSTEM, "Unreal2.exe")
# U2PILOT_FULLSCREEN=1: start the game fullscreen and in front (it won't go fullscreen while in the
# background); it covers the screen for the whole run, so only use it when the user is at the PC
FULLSCREEN = os.environ.get("U2PILOT_FULLSCREEN") == "1"
# U2PILOT_LOG=Name.log: the game logs there instead (LOG= on its command line), e.g.
# when a crashed game stuck in the graphics driver still holds Unreal2.log open
LOG_NAME = os.environ.get("U2PILOT_LOG", "Unreal2.log")
LOG_ARGS = [] if LOG_NAME.lower() == "unreal2.log" else ["LOG=" + LOG_NAME]
GAME_LOG = os.path.join(GAME_SYSTEM, LOG_NAME)
REF_W, REF_H = 1600, 900
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)   # real pixel coordinates
except OSError:
    pass

# ---------------------------------------------------------------- input ----

ULONG_PTR = ctypes.c_size_t

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]

class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x4, 0x8
MOUSEEVENTF_MOVE = 0x1
MOUSE_BUTTONS = {"left": (0x2, 0x4), "right": (0x8, 0x10), "middle": (0x20, 0x40)}
VK_F12 = 0x7B

# DirectInput games read scan codes, so keys are sent as scan codes, not VKs
SCAN = {
    "esc": 0x01, "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07,
    "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B, "-": 0x0C, "=": 0x0D, "backspace": 0x0E,
    "tab": 0x0F, "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15,
    "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19, "[": 0x1A, "]": 0x1B, "enter": 0x1C,
    "ctrl": 0x1D, "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23,
    "j": 0x24, "k": 0x25, "l": 0x26, ";": 0x27, "'": 0x28, "tilde": 0x29, "`": 0x29,
    "shift": 0x2A, "\\": 0x2B, "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30,
    "n": 0x31, "m": 0x32, ",": 0x33, ".": 0x34, "/": 0x35, "rshift": 0x36, "alt": 0x38,
    "space": 0x39, "capslock": 0x3A,
    "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F, "f6": 0x40, "f7": 0x41,
    "f8": 0x42, "f9": 0x43, "f10": 0x44, "f11": 0x57,
}
EXTENDED = {"up": 0x48, "down": 0x50, "left": 0x4B, "right": 0x4D, "home": 0x47,
            "end": 0x4F, "pgup": 0x49, "pgdn": 0x51, "insert": 0x52, "delete": 0x53,
            "rctrl": 0x1D, "ralt": 0x38}

held_keys, held_buttons = set(), set()


class Aborted(Exception):
    pass


def send(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def key_event(name, up):
    name = name.lower()
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    if name in EXTENDED:
        code, flags = EXTENDED[name], flags | KEYEVENTF_EXTENDEDKEY
    elif name in SCAN:
        code = SCAN[name]
    else:
        raise ValueError(f"unknown key '{name}'")
    send(INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, code, flags, 0, 0))))
    (held_keys.discard if up else held_keys.add)(name)


def button_event(name, up):
    down_flag, up_flag = MOUSE_BUTTONS[name]
    send(INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(0, 0, 0, up_flag if up else down_flag, 0, 0))))
    (held_buttons.discard if up else held_buttons.add)(name)


def mouse_move(dx, dy):
    send(INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, 0))))


def type_text(text):
    for ch in text:
        for up in (False, True):
            flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
            send(INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, ord(ch), flags, 0, 0))))
        time.sleep(0.02)


def release_all():
    for k in list(held_keys):
        key_event(k, True)
    for b in list(held_buttons):
        button_event(b, True)


def check_abort():
    if user32.GetAsyncKeyState(VK_F12) & 0x8000:
        raise Aborted("F12 pressed")


def sleep(seconds):
    end = time.time() + seconds
    while time.time() < end:
        check_abort()
        time.sleep(min(0.02, max(0, end - time.time())))

# --------------------------------------------------------------- window ----

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def find_window(pid):
    found = []

    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value:
                found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found[0] if found else (None, None)


def client_rect(hwnd):
    r = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, r.right - r.left, r.bottom - r.top


def focus(hwnd):
    if user32.GetForegroundWindow() == hwnd:
        return
    # Windows only lets the foreground process hand over focus; a stray Alt
    # press makes this process count as having had input.
    key_event("alt", False); key_event("alt", True)
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)


def game_pids():
    """Live Unreal2.exe processes. A crashed game can linger in the list after it has
    exited (stuck in the graphics driver); those are skipped."""
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Unreal2.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        if "Unreal2.exe" not in line:
            continue
        pid = int(line.split('","')[1])
        h = kernel32.OpenProcess(0x1000, False, pid)    # PROCESS_QUERY_LIMITED_INFORMATION
        code = wt.DWORD(259)
        if h:
            kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            kernel32.CloseHandle(h)
        if code.value == 259:                           # STILL_ACTIVE
            pids.append(pid)
    return pids


def game_running():
    return bool(game_pids())

# ------------------------------------------------------------ recording ----

def grab_args(hwnd, title, mode):
    if mode == "gdigrab":
        return ["-f", "gdigrab", "-framerate", "30", "-draw_mouse", "0", "-i", f"title={title}"]
    x, y, w, h = client_rect(hwnd)
    w, h = w - w % 2, h - h % 2
    return ["-f", "lavfi", "-i",
            f"ddagrab=framerate=30:draw_mouse=0:offset_x={x}:offset_y={y}:video_size={w}x{h},hwdownload,format=bgra"]


def tiny_frame(hwnd, title, mode):
    """Grab one 64x36 greyscale frame as bytes (empty on failure)."""
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", *grab_args(hwnd, title, mode),
           "-frames:v", "1", "-vf", "scale=64:36", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=15).stdout
    except subprocess.TimeoutExpired:
        return b""


def frame_brightness(hwnd, title, mode):
    data = tiny_frame(hwnd, title, mode)
    return sum(data) / len(data) if data else 0


def play_sample(hwnd, title, mode):
    """Return (looks_like_play, top_level, bottom_level, mean). A cutscene is
    letterboxed: every row of the top and bottom bars is perfectly flat and dark
    (not always pure black - dgVoodoo lifts some rows slightly). Gameplay always
    has HUD and scenery in the bottom band. A fade to black also counts as not play."""
    data = tiny_frame(hwnd, title, mode)
    if len(data) != 64 * 36:
        return False, 0, 0, 0

    def flat_dark(r):
        row = data[r * 64:(r + 1) * 64]
        return max(row) - min(row) <= 3 and max(row) < 16

    rows = (0, 1, 2, 3, 32, 33, 34, 35)   # letterbox bars cover ~7 of 36 rows each
    top = sum(data[:64 * 3]) / (64 * 3)
    bottom = sum(data[64 * 33:]) / (64 * 3)
    mean = sum(data) / len(data)
    letterboxed = all(flat_dark(r) for r in rows)
    return (not letterboxed) and mean > 8, top, bottom, mean


class Recorder:
    def __init__(self, run_dir, log):
        self.run_dir, self.log, self.proc, self.mode, self.parts = run_dir, log, None, None, []

    def pick_mode(self, hwnd, title):
        if self.mode is None:
            b = frame_brightness(hwnd, title, "gdigrab")
            self.mode = "gdigrab" if b > 3 else "ddagrab"
            self.log(f"capture mode: {self.mode} (window capture brightness {b:.1f})")
        return self.mode

    def start(self, hwnd, title):
        if self.proc:
            return
        mode = self.pick_mode(hwnd, title)
        path = os.path.join(self.run_dir, f"part{len(self.parts) + 1}.mp4")
        cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *grab_args(hwnd, title, mode),
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p", path]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        self.parts.append(path)
        self.log(f"recording -> {os.path.basename(path)}")

    def stop(self):
        if not self.proc:
            return
        try:
            self.proc.stdin.write(b"q"); self.proc.stdin.flush()
            self.proc.wait(timeout=15)
        except Exception:
            self.proc.kill()
        self.proc = None
        self.log("recording stopped")

    def finish(self):
        self.stop()
        parts = [p for p in self.parts if os.path.exists(p) and os.path.getsize(p) > 0]
        if not parts:
            return None
        video = os.path.join(self.run_dir, "video.mp4")
        if len(parts) == 1:
            os.replace(parts[0], video)
        else:
            lst = os.path.join(self.run_dir, "parts.txt")
            with open(lst, "w") as f:
                f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                            "-safe", "0", "-i", lst, "-c", "copy", video], cwd=self.run_dir)
        return video


def contact_sheet(video, out):
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", video], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
    dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 16
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-vf",
                    f"fps={16 / max(dur, 1):.4f},scale=400:-1,tile=4x4", "-frames:v", "1", out])

# ------------------------------------------------------------------ run ----

def log_size():
    return os.path.getsize(GAME_LOG) if os.path.exists(GAME_LOG) else 0


def log_since(offset):
    try:
        with open(GAME_LOG, "rb") as f:
            f.seek(offset)
            return f.read().decode("latin-1")
    except OSError:
        return ""


def parse(path):
    steps = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split("#", 1)[0].strip()
        if line:
            cmd, _, rest = line.partition(" ")
            steps.append((n, cmd.lower(), rest.strip()))
    return steps


def default_mutators():
    """The Mutator= value from User.ini's [DefaultPlayer] (so installed mods still load)."""
    section = None
    for line in open(os.path.join(GAME_SYSTEM, "User.ini"), encoding="latin-1"):
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == "[DefaultPlayer]" and line.lower().startswith("mutator="):
            return [m for m in line.split("=", 1)[1].split(",") if m]
    return []


PILOT_INI, PILOT_USER_INI = "PilotRun.ini", "PilotRunUser.ini"


def ini_has_section(path, section):
    want = f"[{section.lower()}]"
    return any(l.strip().lower() == want for l in open(path, encoding="latin-1"))


def set_ini_keys(path, section, values):
    """Set key=value pairs inside [section] of a CRLF ini file (adding missing keys)."""
    lines = open(path, encoding="latin-1").read().splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip().lower() == f"[{section.lower()}]"), None)
    if start is None:
        lines += ["", f"[{section}]"]
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    todo = dict(values)
    for i in range(start + 1, end):
        key = lines[i].split("=", 1)[0].strip()
        if key in todo:
            lines[i] = f"{key}={todo.pop(key)}"
    lines[end:end] = [f"{k}={v}" for k, v in todo.items()]
    with open(path, "w", encoding="latin-1", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def make_pilot_inis():
    """Throwaway copies of the user's configs (so installed mods still load) with
    mouse capture off and a small window. The user's own files are never written."""
    ini, user = os.path.join(GAME_SYSTEM, PILOT_INI), os.path.join(GAME_SYSTEM, PILOT_USER_INI)
    shutil.copy(os.path.join(GAME_SYSTEM, "Unreal2.ini"), ini)
    shutil.copy(os.path.join(GAME_SYSTEM, "User.ini"), user)
    set_ini_keys(ini, "WinDrv.WindowsClient", {"CaptureMouse": "False", "StartupFullscreen": "true" if FULLSCREEN else "false",
                                               "WindowedViewportX": "960", "WindowedViewportY": "540"})
    return [f"-ini={PILOT_INI}", f"-userini={PILOT_USER_INI}"]


def hide_offscreen(hwnd):
    """Park the window beyond the left edge of the desktop without activating it.
    U2PILOT_PARK=X,Y parks it at that screen position instead (e.g. on a spare
    monitor, to watch or capture the run without it taking focus)."""
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    park = os.environ.get("U2PILOT_PARK")
    if park:
        px, py = (int(v) for v in park.split(","))
        if (r.left, r.top) != (px, py):
            user32.SetWindowPos(hwnd, None, px, py, 0, 0, 0x1 | 0x4 | 0x10)
        return
    left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN: leftmost point of all monitors
    if r.right > left:
        SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE = 0x1, 0x4, 0x10
        user32.SetWindowPos(hwnd, None, left - (r.right - r.left) - 50, r.top, 0, 0,
                            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)


def give_focus_back(game_hwnd, prev_hwnd):
    """The game grabbed the foreground (Unreal re-activates its window when it hands
    control back after a cutscene). Return it to the window the user was in.
    Attaching to the foreground thread is what lets us call SetForegroundWindow."""
    if not prev_hwnd or not user32.IsWindow(prev_hwnd):
        prev_hwnd = user32.GetShellWindow()
    fg_thread = user32.GetWindowThreadProcessId(game_hwnd, None)
    me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(me, fg_thread, True)
    try:
        user32.SetForegroundWindow(prev_hwnd)
        user32.SetWindowPos(game_hwnd, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)   # HWND_BOTTOM, no move/size/activate
    finally:
        user32.AttachThreadInput(me, fg_thread, False)


def clip_is_game(hwnd):
    """Is the current cursor clip the game window's rectangle (not another app's)?"""
    clip, win = wt.RECT(), wt.RECT()
    user32.GetClipCursor(ctypes.byref(clip))
    user32.GetWindowRect(hwnd, ctypes.byref(win))
    return (abs(clip.left - win.left) < 40 and abs(clip.top - win.top) < 60 and
            abs(clip.right - win.right) < 40 and abs(clip.bottom - win.bottom) < 40)


def cursor_clipped():
    r, full = wt.RECT(), (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
                          user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))
    user32.GetClipCursor(ctypes.byref(r))
    return (r.right - r.left, r.bottom - r.top) != (full[2], full[3])


def crash_dialog(pid):
    """The game's "Critical Error" window, if it shows one: (hwnd, its text). A crash in a background
    run puts this dialog off-screen where nobody clicks it, and the process hangs half-dead (it held
    System files for hours on 2026-10-02); a second assertion (TopChunk==NULL, UnMem.cpp) often
    follows while the engine shuts down after the first error."""
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def top(h, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            if "critical" in buf.value.lower() or "error" in buf.value.lower():
                found.append(h)
        return True
    user32.EnumWindows(top, 0)
    if not found:
        return None, ""
    texts = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def child(h, _):
        n = user32.SendMessageW(h, 0x000E, 0, 0)          # WM_GETTEXTLENGTH
        if n > 0:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.SendMessageW(h, 0x000D, n + 1, buf)    # WM_GETTEXT
            if buf.value.strip() and buf.value.strip() not in ("Ok", "OK", "Copy Text", "Submit Bug Report"):
                texts.append(buf.value.strip())
        return True
    user32.EnumChildWindows(found[0], child, 0)
    return found[0], "\n".join(texts)


def close_crash(pid, run_dir, log):
    """Save the crash dialog's text into the run and close it so the process can exit."""
    hwnd, text = crash_dialog(pid)
    if not hwnd:
        return False
    with open(os.path.join(run_dir, "crash.txt"), "a", encoding="utf-8") as f:
        f.write(text + "\n----\n")
    log("GAME CRASHED: " + " | ".join(l for l in text.splitlines() if l.strip())[:300])
    user32.PostMessageW(hwnd, 0x0010, 0, 0)                 # WM_CLOSE (same as Ok)
    return True


def run_background(steps, run_dir, log, keep_open, sound=False):
    """Background mode: the in-game PilotDriver mutator plays the steps, so the
    game runs unfocused and the real keyboard/mouse are never touched. Frames
    come from the game's own screenshots."""
    # the game overwrites Unreal2.log on launch: keep the user's last session log
    # (unless it's from an earlier pilot run) so a real crash/hang can still be read
    try:
        head = open(GAME_LOG, encoding="latin-1", errors="replace").read(4000)
        if "PilotRun=" not in head:
            keep = os.path.join(GAME_SYSTEM, "Unreal2.user-last.log")
            shutil.copy(GAME_LOG, keep)
            log(f"saved the user's previous game log to {keep}")
    except OSError:
        pass
    # "ini Section Key=Value" lines set values in the throwaway pilot config only
    ini_overrides = [(cmd, rest) for _, cmd, rest in steps if cmd in ("ini", "userini")]
    # "mutators A,B" = load exactly these mods (instead of the installed ones)
    exact = [rest for _, cmd, rest in steps if cmd == "mutators"]
    steps = [st for st in steps if st[1] not in ("ini", "userini", "mutators")]
    game_map = steps.pop(0)[2] if steps and steps[0][1] == "map" else "m01a"
    driver_steps = [f"{cmd} {rest}".strip() for _, cmd, rest in steps]
    # let the last screenshots land before the game closes
    driver_steps = [s for s in driver_steps if s.split()[0] != "quit"] + ["wait 1", "quit"]
    with open(os.path.join(GAME_SYSTEM, "U2Pilot.ini"), "w", encoding="latin-1", newline="\r\n") as f:
        f.write("[U2PilotDriver.PilotDriver]\n" + "".join(f"Steps={s}\n" for s in driver_steps))
    shot_interval = next((float(s.split()[1]) for s in driver_steps if s.startswith("shots ")), 0.5)

    extra = re.search(r"Mutator=([^?]+)", game_map)
    base = [m for m in exact[-1].split(",") if m] if exact else default_mutators()
    mutators = base + (extra[1].split(",") if extra else [])
    mutators = list(dict.fromkeys(m for m in mutators if m != "U2PilotDriver.PilotDriver")) + ["U2PilotDriver.PilotDriver"]
    run_id = os.path.basename(run_dir)
    # the unknown ?PilotRun= option is ignored by the game but marks this launch in the log
    # keep the map's other options (e.g. Atlantis?MissionCompleted=2)
    opts = "".join("?" + o for o in game_map.split("?")[1:] if o and not o.lower().startswith("mutator="))
    url = f"{game_map.split('?')[0]}{opts}?Mutator={','.join(mutators)}?PilotRun={run_id}"
    existing = set(glob.glob(os.path.join(GAME_SYSTEM, "Shot*.bmp")))
    ini_args = make_pilot_inis()
    for kind, o in ini_overrides:
        section, kv = o.split(" ", 1)
        key, value = kv.split("=", 1)
        target = PILOT_USER_INI if kind == "userini" else PILOT_INI
        if kind == "ini" and not ini_has_section(os.path.join(GAME_SYSTEM, PILOT_INI), section) \
                and ini_has_section(os.path.join(GAME_SYSTEM, PILOT_USER_INI), section):
            # config(User) classes (e.g. U2SoftShadows' SSShadowController) only read User.ini:
            # a key written to Unreal2.ini would be silently ignored
            target = PILOT_USER_INI
            log(f"pilot ini: [{section}] lives in User.ini, writing it there")
        set_ini_keys(os.path.join(GAME_SYSTEM, target), section, {key.strip(): value.strip()})
        log(f"pilot {kind}: [{section}] {key.strip()}={value.strip()} ({target})")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 1 if FULLSCREEN else 4   # SW_SHOWNOACTIVATE: show the window without taking focus
    log(f"background launch: Unreal2.exe {url}")
    extra = [] if sound else ["-nosound"]
    game = subprocess.Popen([GAME_EXE, url, "-forcelogflush", *extra, *ini_args, *LOG_ARGS], cwd=GAME_SYSTEM, startupinfo=si)
    stole_focus = clipped = 0
    prev_fg = user32.GetForegroundWindow()   # where the user is working

    seen, done_at, deadline = 0, None, time.time() + 600
    crashes = 0
    while game.poll() is None and time.time() < deadline:
        if close_crash(game.pid, run_dir, log):
            crashes += 1
            if crashes >= 3:          # dialogs keep coming: the process is stuck in its error handler
                log("still crashing after closing 3 dialogs - killing the game")
                game.kill()
                break
            time.sleep(1.0)
            continue
        text = log_since(0)
        # keep the window out of the way and check it never grabs the user's focus or mouse
        hwnd, _ = find_window(game.pid)
        fg = user32.GetForegroundWindow()
        if hwnd and not FULLSCREEN:
            if not os.environ.get("U2PILOT_VISIBLE"):   # set to keep the window on the desktop
                hide_offscreen(hwnd)
            if fg == hwnd:
                stole_focus += 1
                give_focus_back(hwnd, prev_fg)
            elif fg:
                prev_fg = fg
        if cursor_clipped():
            clipped += 1
            if hwnd and clip_is_game(hwnd):
                user32.ClipCursor(None)   # the game trapped the mouse: release it
        if f"PilotRun={run_id}" not in text[:6000]:   # still the previous run's log
            time.sleep(0.1)
            continue
        lines = text.splitlines()
        for line in lines[seen:]:
            if "PilotDriver:" in line and "PilotDriver: shot " not in line:
                log("  " + line.split("PilotDriver:", 1)[1].strip())
                if line.rstrip().endswith("PilotDriver: done"):
                    done_at = time.time()
        seen = len(lines)
        if done_at and time.time() - done_at > 15 and not keep_open:
            log("game didn't exit after the script - terminating it")
            game.terminate()
        time.sleep(0.1)
    if game.poll() is None and not keep_open:
        close_crash(game.pid, run_dir, log)       # a dialog left at the end: close it before killing
        time.sleep(0.5)
        if game.poll() is None:
            game.kill()

    log(f"game grabbed focus {stole_focus} time(s) (handed straight back), cursor clipped in {clipped} checks (released if it was the game's)")
    shots = sorted(set(glob.glob(os.path.join(GAME_SYSTEM, "Shot*.bmp"))) - existing, key=os.path.getmtime)
    if shots and len(shots) > 1 and os.path.getsize(shots[-1]) < os.path.getsize(shots[0]):
        os.remove(shots.pop())   # last one was cut off mid-write
    frames = os.path.join(run_dir, "frames")
    os.makedirs(frames, exist_ok=True)
    for i, s in enumerate(shots):
        shutil.move(s, os.path.join(frames, f"f{i:05d}.bmp"))
    log(f"{len(shots)} in-game screenshots")
    if shots:
        video = os.path.join(run_dir, "video.mp4")
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-framerate", f"{1 / shot_interval:.3f}",
                        "-i", os.path.join(frames, "f%05d.bmp"), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", video])
        contact_sheet(video, os.path.join(run_dir, "sheet.png"))
    if game.poll() is not None and os.path.exists(GAME_LOG):
        shutil.copy(GAME_LOG, os.path.join(run_dir, "Unreal2.log"))
    log(f"results in {run_dir}")


def main():
    ap = argparse.ArgumentParser(description="Script, play and record Unreal II.")
    ap.add_argument("script")
    ap.add_argument("--keep-open", action="store_true", help="leave the game running afterwards")
    ap.add_argument("--sound", action="store_true", help="background mode: keep game audio on")
    ap.add_argument("--background", action="store_true",
                    help="drive the game from inside (PilotDriver mutator): no focus, no real input")
    args = ap.parse_args()

    steps = parse(args.script)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(HERE, "runs", f"{stamp}_{os.path.splitext(os.path.basename(args.script))[0]}")
    os.makedirs(run_dir)
    pilot_log = open(os.path.join(run_dir, "pilot.log"), "w", encoding="utf-8")
    t0 = time.time()

    def log(msg):
        line = f"[{time.time() - t0:7.2f}] {msg}"
        print(line); pilot_log.write(line + "\n"); pilot_log.flush()

    if game_running():
        sys.exit("Unreal II is already running - close it first.")

    if args.background or (steps and steps[0][1] == "background"):
        if steps and steps[0][1] == "background":
            steps.pop(0)
        run_background(steps, run_dir, log, args.keep_open, args.sound)
        pilot_log.close()
        return

    launch_args = []
    if steps and steps[0][1] == "map":
        launch_args = [steps.pop(0)[2]]
    # -forcelogflush makes the game write its log live, so waitlevel/waitlog work
    launch_args.append("-forcelogflush")
    launch_args += LOG_ARGS
    log(f"launching Unreal2.exe {' '.join(launch_args)}")
    game = subprocess.Popen([GAME_EXE, *launch_args], cwd=GAME_SYSTEM)

    hwnd = title = None
    for _ in range(600):
        hwnd, title = find_window(game.pid)
        if hwnd:
            break
        time.sleep(0.1)
    if not hwnd:
        sys.exit("game window never appeared")
    log(f"window: '{title}'")
    # only trust the log once the game has started a fresh one for this launch
    for _ in range(300):
        if "-forcelogflush" in log_since(0)[:4000]:
            break
        time.sleep(0.1)
    log_start = 0
    rec = Recorder(run_dir, log)
    quit_sent = aborted = False

    try:
        for n, cmd, rest in steps:
            check_abort()
            if game.poll() is not None:
                log("game exited"); break
            hwnd, title = find_window(game.pid)
            focus(hwnd)
            a = rest.split()
            log(f"line {n}: {cmd} {rest}")

            if cmd == "wait":
                sleep(float(a[0]))
            elif cmd in ("waitlevel", "waitlog"):
                if cmd == "waitlevel":
                    text, timeout = "up for play", float(a[0]) if a else 60
                else:
                    parts = rest.rsplit(" ", 1)
                    text, timeout = (parts[0], float(parts[1])) if len(parts) == 2 and re.fullmatch(r"[\d.]+", parts[1]) else (rest, 120)
                def seen():
                    t = log_since(log_start).lower()
                    if cmd == "waitlevel":
                        # the game loads a tiny Entry level first; wait for the
                        # level named by the latest Browse: line instead
                        i = t.rfind("browse:")
                        return i >= 0 and text in t[i:]
                    return text.lower() in t
                end = time.time() + timeout
                while time.time() < end and not seen():
                    sleep(0.5)
                if time.time() >= end:
                    log(f"  (timed out waiting for '{text}' - the log may be buffered; continuing)")
                log_start = log_size()
            elif cmd == "waitplay":
                # cutscenes are letterboxed; wait for 3 continuous seconds that look like play
                timeout = float(a[0]) if a else 120
                end, since = time.time() + timeout, None
                mode = rec.pick_mode(hwnd, title)
                while time.time() < end:
                    ok, top, bottom, mean = play_sample(hwnd, title, mode)
                    log(f"    sample: top {top:5.1f}  bottom {bottom:5.1f}  mean {mean:5.1f}  {'play' if ok else 'cutscene/black'}")
                    since = (since or time.time()) if ok else None
                    if since and time.time() - since >= 3:
                        break
                    sleep(0.4)
                log("  player in control" if since and time.time() - since >= 3 else "  (timed out waiting for play - continuing)")
            elif cmd == "record":
                rec.start(hwnd, title) if a[0] == "start" else rec.stop()
            elif cmd == "key":
                if len(a) > 1:
                    key_event(a[0], False); sleep(float(a[1])); key_event(a[0], True)
                else:
                    key_event(a[0], False); time.sleep(0.05); key_event(a[0], True)
            elif cmd == "keys":
                names = a[0].split("+")
                for k in names:
                    key_event(k, False)
                sleep(float(a[1]) if len(a) > 1 else 0.05)
                for k in reversed(names):
                    key_event(k, True)
            elif cmd == "look":
                dx, dy = float(a[0]), float(a[1])
                dur = float(a[2]) if len(a) > 2 else 0.3
                steps_n = max(1, int(dur / 0.01))
                done_x = done_y = 0
                for i in range(1, steps_n + 1):
                    tx, ty = round(dx * i / steps_n), round(dy * i / steps_n)
                    mouse_move(tx - done_x, ty - done_y)
                    done_x, done_y = tx, ty
                    sleep(dur / steps_n)
            elif cmd == "click":
                btn = a[0] if a and a[0] in MOUSE_BUTTONS else "left"
                hold = float(a[-1]) if a and re.fullmatch(r"[\d.]+", a[-1]) else 0.05
                button_event(btn, False); sleep(hold); button_event(btn, True)
            elif cmd == "clickat":
                x, y, w, h = client_rect(hwnd)
                user32.SetCursorPos(int(x + float(a[0]) * w / REF_W), int(y + float(a[1]) * h / REF_H))
                time.sleep(0.1)
                button_event("left", False); time.sleep(0.05); button_event("left", True)
            elif cmd == "console":
                key_event("tilde", False); time.sleep(0.05); key_event("tilde", True)
                sleep(0.4); type_text(rest); sleep(0.1)
                key_event("enter", False); time.sleep(0.05); key_event("enter", True)
                sleep(0.3)
            elif cmd == "type":
                type_text(rest)
            elif cmd == "shot":
                out = os.path.join(run_dir, f"{rest or 'shot'}.png")
                subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                                *grab_args(hwnd, title, rec.pick_mode(hwnd, title)), "-frames:v", "1", out])
                log(f"  saved {os.path.basename(out)}")
            elif cmd == "quit":
                rec.stop()
                key_event("tilde", False); time.sleep(0.05); key_event("tilde", True)
                sleep(0.4); type_text("exit")
                key_event("enter", False); time.sleep(0.05); key_event("enter", True)
                try:
                    game.wait(timeout=20)
                    quit_sent = True
                except subprocess.TimeoutExpired:
                    log("  console exit didn't close the game (cutscene?) - terminating it")
            else:
                log(f"  unknown command '{cmd}' - skipped")
    except Aborted as e:
        log(f"ABORTED: {e} - leaving the game open")
        aborted = True
    except Exception as e:
        log(f"ERROR on script step: {e!r}")
    finally:
        release_all()
        video = rec.finish()
        if video:
            contact_sheet(video, os.path.join(run_dir, "sheet.png"))
            log(f"video: {video}")
        if not (quit_sent or aborted or args.keep_open) and game.poll() is None:
            log("closing the game")
            game.terminate()
            try:
                game.wait(timeout=15)
            except subprocess.TimeoutExpired:
                game.kill()
        if game.poll() is not None and os.path.exists(GAME_LOG):
            shutil.copy(GAME_LOG, os.path.join(run_dir, "Unreal2.log"))
        log(f"results in {run_dir}")
        pilot_log.close()


if __name__ == "__main__":
    main()
