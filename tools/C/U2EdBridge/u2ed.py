"""u2ed - drive Unreal II's UnrealEd from the command line or from Python.

    python u2ed.py start                 launch UnrealEd with the bridge loaded
    python u2ed.py exec "MAP LOAD FILE=..\\Maps\\M08A1.un2"
    python u2ed.py run script.txt        one editor command per line (# = comment)
    python u2ed.py shell                 interactive prompt
    python u2ed.py stop                  close the editor (nothing is saved)

As a library:

    from u2ed import Editor
    with Editor.start() as ed:           # stops the editor on exit
        print(ed.exec("MAP IMPORT FILE=C:\\maps\\arena.t3d"))
        ed.exec("MAP REBUILD")
        ed.exec("PATHS BUILD")
        ed.exec("MAP SAVE FILE=..\\Maps\\Arena.un2")

Every command is an ordinary UnrealEd command, the same text you would type
into the editor's command box. The reply is everything the editor logged while
running it; message boxes it tried to show are listed as
"[dialog -> No] Title: text" (Yes/No questions are answered No; send
"!answer yes" to flip that).

dgVoodoo's d3d8.dll makes UnrealEd crash, so `start` renames it to
d3d8.dll.dgvoodoo-editor-off and `stop` puts it back. The game must not be
running meanwhile.
"""
import ctypes
import ctypes.wintypes as wt
import msvcrt
import os
import subprocess
import sys
import time

GAME = os.environ.get("U2_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening")
SYSTEM = os.path.join(GAME, "System")
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "bin")
PIPE = r"\\.\pipe\U2EdBridge-%d"   # %d = the editor's process id
END = b"<<<U2ED rc="
D3D8 = os.path.join(SYSTEM, "d3d8.dll")
D3D8_OFF = D3D8 + ".dgvoodoo-editor-off"

user32 = ctypes.windll.user32


class BridgeError(RuntimeError):
    pass


class EditorCrashed(OSError):
    """The editor crashed or quit while running a command; .output holds what it
    logged before that."""
    def __init__(self, message, output=b""):
        super().__init__(message)
        self.output = output.decode("utf-8", "replace") if isinstance(output, bytes) else output


def _alive(pid):
    """False once the process has exited (a crashed editor can linger in the
    process list after exiting)."""
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = wt.DWORD()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return bool(ok) and code.value == 259     # STILL_ACTIVE


def _running(image):
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + image, "/NH"],
                         capture_output=True, text=True).stdout
    pids = [int(l.split()[1]) for l in out.splitlines() if l.lower().startswith(image.lower())]
    return [p for p in pids if _alive(p)]


def _kill(pid):
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)


def _windows(pid):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(h):
            found.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return found


def _has_window(pid):
    return bool(_windows(pid))


def _text(h):
    b = ctypes.create_unicode_buffer(4096)
    user32.GetWindowTextW(h, b, 4096)
    if not b.value:   # controls of another process: ask them directly
        user32.SendMessageTimeoutW(h, 0x000D, 4096, b, 2, 1000, None)  # WM_GETTEXT
    return b.value


def crash_text(pid):
    """The message of Unreal's 'Critical Error' window, or None if none is open."""
    for h in _windows(pid):
        if _text(h) == "Critical Error":
            texts = []

            @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
            def cb(c, _):
                b = ctypes.create_unicode_buffer(8192)
                user32.SendMessageTimeoutW(c, 0x000D, 8192, b, 2, 1000, None)
                if b.value.strip() and b.value not in ("Ok", "Copy Text", "Submit Bug Report"):
                    texts.append(b.value.strip())
                return True

            user32.EnumChildWindows(h, cb, 0)
            return "\n".join(texts) or "Critical Error"
    return None


def dgvoodoo_off():
    if os.path.exists(D3D8) and not os.path.exists(D3D8_OFF):
        os.rename(D3D8, D3D8_OFF)


def dgvoodoo_on():
    if os.path.exists(D3D8_OFF) and not os.path.exists(D3D8):
        os.rename(D3D8_OFF, D3D8)


class Editor:
    def __init__(self, pid=None):
        self.pid = pid
        self.pipe = None

    # --- lifetime ---
    @classmethod
    def start(cls, timeout=180):
        """Launch UnrealEd with the bridge already loaded, and wait until it answers.

        Launches CREATE_SUSPENDED and injects before the first ResumeThread,
        so the bridge (and anything it hooks, e.g. the D3D8 device capture for
        !screenshot) is in place before UnrealEd's own main thread runs a
        single instruction -- a pid-based post-hoc injection loses that race,
        since UnrealEd creates its D3D8 device in the same synchronous init
        that creates its main window."""
        # U2ED_WITH_GAME=1 (carve.py, live editing): the game may run - its d3d8.dll (the fork since
        # dgVoodoo went, 2026-10-02) stays loaded in the game while it is renamed aside for the editor
        if _running("Unreal2.exe") and os.environ.get("U2ED_WITH_GAME") != "1":
            raise BridgeError("the game is running; close it first (the editor needs dgVoodoo off)")
        if _running("UnrealEd.exe"):
            raise BridgeError("UnrealEd is already running; use Editor.attach() or close it")
        dgvoodoo_off()
        pid = None
        try:
            pid = launch_suspended(os.path.join(SYSTEM, "UnrealEd.exe"),
                                    os.path.join(BIN, "U2EdBridge.dll"), SYSTEM)
            deadline = time.time() + timeout
            while not _has_window(pid):
                if not _alive(pid):
                    raise BridgeError("UnrealEd exited during startup")
                if time.time() > deadline:
                    raise BridgeError("UnrealEd showed no window in %ds" % timeout)
                time.sleep(0.5)
            ed = cls(pid)
            ed.wait_ready(max(10, deadline - time.time()))
            return ed
        except BaseException:
            if pid:
                _kill(pid)
            time.sleep(1)
            dgvoodoo_on()
            raise

    @classmethod
    def attach(cls):
        """Talk to an editor that already has the bridge loaded."""
        pids = _running("UnrealEd.exe")
        if not pids:
            raise BridgeError("UnrealEd is not running")
        ed = cls(pids[0])
        ed.wait_ready(5)
        return ed

    def wait_ready(self, timeout):
        deadline = time.time() + timeout
        while True:
            try:
                if self.exec("!ping").strip() == "pong":
                    return
            except OSError:
                pass
            if time.time() > deadline:
                raise BridgeError("the bridge did not answer (is U2EdBridge.dll loaded?)")
            time.sleep(0.5)

    def stop(self):
        """Close the editor without saving and restore dgVoodoo."""
        try:
            self.exec("!quit")
        except OSError:
            pass
        self.close()
        for _ in range(40):
            if not _alive(self.pid):
                break
            time.sleep(0.25)
        else:
            _kill(self.pid)
            time.sleep(1)
        dgvoodoo_on()

    def close(self):
        if self.pipe:
            try:
                self.pipe.close()
            except OSError:
                pass
            self.pipe = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    # --- commands ---
    def exec_rc(self, command):
        """Run one editor command; returns (return value, output text)."""
        command = command.replace("\r", " ").replace("\n", " ").strip()
        if not command:
            return 1, ""
        if self.pipe is None:
            self.pipe = open(PIPE % self.pid, "r+b", buffering=0)
        handle = msvcrt.get_osfhandle(self.pipe.fileno())
        try:
            self.pipe.write(command.encode("utf-8") + b"\n")
            buf = b""
            last_check = time.time()
            while True:
                i = buf.find(END)
                if i >= 0 and buf.find(b">>>\n", i) >= 0:
                    j = buf.find(b">>>\n", i)
                    return int(buf[i + len(END):j]), buf[:i].decode("utf-8", "replace")
                avail = wt.DWORD()
                if not ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
                    raise EditorCrashed("the editor closed the connection", buf)
                if avail.value:
                    buf += self.pipe.read(avail.value)
                    continue
                # nothing yet: a long command, or a crash (Unreal's crash box keeps
                # the process alive, so the pipe alone never tells)
                if time.time() - last_check > 1.0:
                    last_check = time.time()
                    if not _alive(self.pid):
                        raise EditorCrashed("the editor exited", buf)
                    crash = crash_text(self.pid)
                    if crash:
                        raise EditorCrashed(crash, buf)
                time.sleep(0.02)
        except OSError:
            self.close()
            raise

    def exec(self, command):
        return self.exec_rc(command)[1]

    def run_script(self, lines, echo=True):
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rc, out = self.exec_rc(line)
            if echo:
                print(">", line, "" if rc else "   [rc=0]")
                if out.strip():
                    print(out.rstrip())


def inject(pid):
    """Post-hoc injection into an already-running process. Kept for attaching
    to an editor started outside this tool; Editor.start() itself uses
    launch_suspended() instead, since this path can lose the race against
    whatever the target does before its first window appears."""
    exe = os.path.join(BIN, "u2edinject.exe")
    dll = os.path.join(BIN, "U2EdBridge.dll")
    r = subprocess.run([exe, str(pid), dll], capture_output=True, text=True)
    if r.returncode:
        raise BridgeError("injection failed: " + (r.stderr or r.stdout).strip())


def launch_suspended(exe_path, dll, cwd, timeout=30):
    """Launch exe_path CREATE_SUSPENDED in cwd, inject dll before it runs,
    then resume it. Returns the new process id."""
    injector = os.path.join(BIN, "u2edinject.exe")
    r = subprocess.run([injector, "launch", exe_path, dll, cwd], capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise BridgeError("launch+injection failed: " + (r.stderr or r.stdout).strip())
    return int(r.stdout.strip())


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "start":
        ed = Editor.start()
        print("UnrealEd is ready; the bridge is listening on", PIPE % ed.pid)
    elif cmd == "stop":
        for pid in _running("UnrealEd.exe"):
            Editor(pid).stop()
        dgvoodoo_on()
        print("stopped")
    elif cmd == "exec":
        rc, out = Editor.attach().exec_rc(" ".join(argv[2:]))
        sys.stdout.write(out)
        return 0 if rc else 1
    elif cmd == "run":
        with open(argv[2], encoding="utf-8") as f:
            Editor.attach().run_script(f)
    elif cmd == "shell":
        ed = Editor.attach()
        print("UnrealEd bridge shell - editor commands, !answer yes|no, Ctrl+Z/Ctrl+C to leave")
        while True:
            try:
                line = input("ued> ")
            except (EOFError, KeyboardInterrupt):
                break
            rc, out = ed.exec_rc(line)
            sys.stdout.write(out if out.endswith("\n") or not out else out + "\n")
            if not rc and line.strip():
                print("[rc=0: command not handled]")
    else:
        print("unknown command:", cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
