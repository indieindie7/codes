"""glm - drive Unreal II's Golem Studio (GlmEd.exe) through its own command layer.

    python glm.py start                       launch Golem Studio with the bridge loaded
    python glm.py exec "!windows"             every window of the editor and the GLM object behind it
    python glm.py exec "!commands"            the command table of the main window's object
    python glm.py exec "!commands 000A0B2C"   ... of another window's object (hwnd in hex, from !windows)
    python glm.py exec "EditFileSave"         run a Golem command on the main window's object
    python glm.py exec "@000A0B2C EditFolderSaveAll"   ... on another window's object
    python glm.py shell | run script.txt | stop

As a library:

    from glm import Golem
    with Golem.start() as g:
        print(g.exec("!windows"))

The reply is everything Golem logged while the command ran (its LOG_* lines, the command's own
result text, and "[dialog -> Yes/No/OK] Title: text" for message boxes the bridge answered;
Yes/No questions are answered No until "!answer yes"), then the bridge's return code.

GlmEd needs System\\dxgi.dll (BGProxy, not part of the game) out of the way: `start` renames it
to dxgi.dll.off-golem and `stop` puts it back, as golem.py does. The bridge DLL and the injector
come from ..\\U2EdBridge\\bin (u2edinject.exe) and .\\bin (GlmBridge.dll).
"""
import msvcrt
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "U2EdBridge"))
from u2ed import _alive, _running, _kill, _has_window, BridgeError, EditorCrashed, launch_suspended  # noqa: E402
import u2ed  # noqa: E402

GAME = os.environ.get("U2_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening")
SYSTEM = os.path.join(GAME, "System")
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "bin")
PIPE = r"\\.\pipe\GlmBridge-%d"
END = b"<<<GLM rc="
DXGI = os.path.join(SYSTEM, "dxgi.dll")
DXGI_OFF = DXGI + ".off-golem"


def dxgi_off():
    if os.path.exists(DXGI) and not os.path.exists(DXGI_OFF):
        os.rename(DXGI, DXGI_OFF)


def dxgi_on():
    if os.path.exists(DXGI_OFF) and not os.path.exists(DXGI):
        os.rename(DXGI_OFF, DXGI)


class Golem:
    def __init__(self, pid):
        self.pid = pid
        self.pipe = None

    @classmethod
    def start(cls, timeout=120):
        if _running("GlmEd.exe"):
            raise BridgeError("Golem Studio is already running; use Golem.attach() or close it")
        dxgi_off()
        pid = None
        try:
            u2ed.BIN = os.path.join(HERE, "..", "U2EdBridge", "bin")   # the injector lives there
            pid = launch_suspended(os.path.join(SYSTEM, "GlmEd.exe"), os.path.join(BIN, "GlmBridge.dll"), SYSTEM)
            deadline = time.time() + timeout
            while not _has_window(pid):
                if not _alive(pid):
                    raise BridgeError("GlmEd exited during startup")
                if time.time() > deadline:
                    raise BridgeError("GlmEd showed no window in %ds" % timeout)
                time.sleep(0.5)
            g = cls(pid)
            g.wait_ready(max(10, deadline - time.time()))
            return g
        except BaseException:
            if pid:
                _kill(pid)
            time.sleep(1)
            dxgi_on()
            raise

    @classmethod
    def attach(cls):
        pids = _running("GlmEd.exe")
        if not pids:
            raise BridgeError("Golem Studio is not running")
        g = cls(pids[0])
        g.wait_ready(5)
        return g

    def wait_ready(self, timeout):
        deadline = time.time() + timeout
        while True:
            try:
                if self.exec("!ping").strip() == "pong":
                    return
            except OSError:
                pass
            if time.time() > deadline:
                raise BridgeError("the bridge did not answer (is GlmBridge.dll loaded?)")
            time.sleep(0.5)

    def stop(self):
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
        dxgi_on()

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

    def exec_rc(self, command):
        import ctypes
        import ctypes.wintypes as wt
        command = command.replace("\r", " ").replace("\n", " ").strip()
        if not command:
            return 1, ""
        if self.pipe is None:
            self.pipe = open(PIPE % self.pid, "r+b", buffering=0)
        handle = msvcrt.get_osfhandle(self.pipe.fileno())
        try:
            self.pipe.write(command.encode("utf-8") + b"\n")
            buf = b""
            last = time.time()
            while True:
                i = buf.find(END)
                if i >= 0 and buf.find(b">>>\n", i) >= 0:
                    j = buf.find(b">>>\n", i)
                    return int(buf[i + len(END):j]), buf[:i].decode("utf-8", "replace")
                avail = wt.DWORD()
                if not ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
                    raise EditorCrashed("Golem closed the connection", buf)
                if avail.value:
                    buf += self.pipe.read(avail.value)
                    continue
                if time.time() - last > 1.0:
                    last = time.time()
                    if not _alive(self.pid):
                        raise EditorCrashed("Golem exited", buf)
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


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "start":
        g = Golem.start()
        print("Golem Studio is ready; the bridge is listening on", PIPE % g.pid)
    elif cmd == "stop":
        for pid in _running("GlmEd.exe"):
            Golem(pid).stop()
        dxgi_on()
        print("stopped")
    elif cmd == "exec":
        rc, out = Golem.attach().exec_rc(" ".join(argv[2:]))
        sys.stdout.write(out)
        return 0 if rc else 1
    elif cmd == "run":
        with open(argv[2], encoding="utf-8") as f:
            Golem.attach().run_script(f)
    elif cmd == "shell":
        g = Golem.attach()
        print("Golem bridge shell - Golem commands, !windows, !commands, !answer yes|no; Ctrl+C to leave")
        while True:
            try:
                line = input("glm> ")
            except (EOFError, KeyboardInterrupt):
                break
            rc, out = g.exec_rc(line)
            sys.stdout.write(out if out.endswith("\n") or not out else out + "\n")
            if not rc and line.strip():
                print("[rc=0: command not handled]")
    else:
        print("unknown command:", cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
