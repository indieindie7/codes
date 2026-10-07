r"""Live sessions in Advent Rising: reload or restart the game around a player who keeps playing.

    python tools/live_reload.py save        the player's place saved (put back at the next load of that map)
    python tools/live_reload.py reload      the same map opened again, the player put back where they
                                            were (after a level rebuilt in the editor, or settings the
                                            level only reads when it loads)
    python tools/live_reload.py restart [--build]
                                            the player's place saved, the game closed, the mod built
                                            again (--build: script changes need a new AdventMod.u,
                                            which a running game can't take), the game started
                                            straight into the same map and the player put back
    python tools/live_reload.py status      the d3d8 layer's status file: is the game up, on which map

Requests go to the mod as one word in System\AdventLive.req (save, reload, forget, quit), read
twice a second by its ModLive through AdventNative; nothing in the file is ever run as a command,
and the game deletes it when it takes the request. ("live save|reload|forget" also works typed
at the console.) Look edits (U2Shaders.ini, the .hlsl shaders) need none of this: the d3d8 layer
reloads them by itself.
"""
import os
import re
import subprocess
import sys
import time

GAME = r"H:\SteamLibrary\steamapps\common\Advent Rising\System"
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "AdventMod", "build.ps1")
MODINI = os.path.join(GAME, "AdventMod.ini")
LOG = os.path.join(GAME, "AdventNative.log")


def say(*a):
    print("live:", *a, flush=True)


def status():
    p = os.path.join(GAME, "U2Live.status")
    if not os.path.exists(p):
        return None
    parts = open(p).read().split()
    if len(parts) < 4 or parts[0] != "up" or time.time() - int(parts[1]) > 6:
        return None
    return {"exe": parts[2], "map": parts[3]}


def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq advent.exe", "/NH"], capture_output=True, text=True).stdout
    return "advent.exe" in out.lower()


def request(word, wait=6.0):
    """a word for the mod's ModLive in System\\AdventLive.req; True once the game has taken it"""
    p = os.path.join(GAME, "AdventLive.req")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        f.write(word + "\n")
    os.replace(tmp, p)
    t = time.time()
    while time.time() - t < wait:
        if not os.path.exists(p):
            return True
        time.sleep(0.1)
    if os.path.exists(p):
        os.remove(p)
    say("the game didn't take the request (is it running, in a level?)")
    return False


def log_size():
    return os.path.getsize(LOG) if os.path.exists(LOG) else 0


def wait_log(pattern, since, timeout):
    t = time.time()
    while time.time() - t < timeout:
        if os.path.exists(LOG):
            if os.path.getsize(LOG) < since:
                since = 0                           # a new log (the game restarted)
            with open(LOG, "rb") as f:
                f.seek(since)
                text = f.read().decode("latin-1", "replace")
            m = re.search(pattern, text)
            if m:
                return m.group(0)
        time.sleep(0.5)
    return None


def resume_map():
    """the map ModLive saved (AdventMod.ini [AdventMod.ModLive])"""
    sec = False
    for l in open(MODINI, encoding="latin-1"):
        l = l.strip()
        if l.startswith("["):
            sec = l.lower() == "[adventmod.modlive]"
        elif sec and l.lower().startswith("resumemap="):
            return l.split("=", 1)[1]
    return None


def set_debug_commands(value):
    """ModSettings' DebugCommands (run once on the title screen): returns the old line"""
    lines = open(MODINI, encoding="latin-1").read().split("\n")
    sec, old, done = False, None, False
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("["):
            if sec and not done:
                lines.insert(i, "DebugCommands=" + value)
                done = True
                break
            sec = s.lower() == "[adventmod.modsettings]"
        elif sec and s.lower().startswith("debugcommands="):
            old = l
            lines[i] = "DebugCommands=" + value
            done = True
    if not done:
        lines.append("DebugCommands=" + value)
    open(MODINI, "w", encoding="latin-1").write("\n".join(lines))
    return old


def reload():
    since = log_size()
    if not request("reload"):
        return
    say("reloading")
    got = wait_log(r"live: resumed [^\r\n]*", since, 90)
    say(got or "no resume seen in AdventNative.log within 90 s")


def restart(build):
    if not request("quit"):                       # ModLive saves the player's place, then exits
        return
    time.sleep(1)
    m = resume_map()
    say("saved the player's place on", m, "- the game is closing")
    t = time.time()
    while game_running() and time.time() - t < 30:
        time.sleep(0.5)
    if game_running():
        say("the game didn't close; stopping here")
        return
    if build:
        say("building the mod")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", BUILD], capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        say("build:", " | ".join(tail))
        if r.returncode != 0:
            say("build failed: the game stays closed")
            return
    old = set_debug_commands("open %s?Game=EonEngine.EonGameInfo" % m)
    subprocess.Popen([os.path.join(GAME, "advent.exe")], cwd=GAME)
    say("started the game into", m)
    got = wait_log(r"live: resumed [^\r\n]*", 0, 180)
    set_debug_commands(old.split("=", 1)[1] if old else "")   # the title screen's one-off command back as it was
    say(got or "no resume seen within 3 minutes")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "status":
        s = status()
        say("up on %s (%s)" % (s["map"], s["exe"]) if s else "not up")
    elif cmd == "save":
        say("saved" if request("save") else "not taken")
    elif cmd == "reload":
        reload()
    elif cmd == "restart":
        restart("--build" in sys.argv)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
