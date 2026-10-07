"""Live sessions in Advent Rising: reload or restart the game around a player who keeps playing.

    python tools/live_reload.py on          the d3d8 layer's command channel on (live=1 in U2Shaders.ini)
    python tools/live_reload.py off         and off again (it is off by default)
    python tools/live_reload.py status      is the game up, on which map
    python tools/live_reload.py send CMD... console commands through the channel (one batch)
    python tools/live_reload.py reload      the same map opened again, the player put back where they
                                            were (after a level rebuilt in the editor, or ini changes
                                            the level only reads at load)
    python tools/live_reload.py restart [--build]
                                            the player's place saved, the game closed, the mod built
                                            again (--build: script changes need a new AdventMod.u,
                                            which a running game can't take), the game started
                                            straight into the same map and the player put back

The channel: lines written to System\\U2Live.cmd run as console commands at the game's next frame
(d3d8to9 fork, live=1); U2Live.ack holds the last batch number run, U2Live.status says the game
is up. The resume itself is the mod's ModLive ("live save|reload|forget" at the console).
Look edits (U2Shaders.ini, the .hlsl shaders) need none of this: the layer reloads them by itself.
"""
import os
import re
import subprocess
import sys
import time

GAME = r"H:\SteamLibrary\steamapps\common\Advent Rising\System"
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "AdventMod", "build.ps1")
INI = os.path.join(GAME, "U2Shaders.ini")
MODINI = os.path.join(GAME, "AdventMod.ini")
LOG = os.path.join(GAME, "AdventNative.log")


def say(*a):
    print("live:", *a, flush=True)


def set_live(on):
    raw = open(INI, "rb").read().decode("latin-1")
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = [l for l in raw.split(nl) if not re.match(r"\s*live\s*=", l)]
    if on:
        lines.append("live=1")
    open(INI, "wb").write(nl.join(lines).encode("latin-1"))
    say("command channel", "on" if on else "off", "(U2Shaders.ini; the game picks it up within a second)")


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


_batch = int(time.time()) % 1000000


def send(lines, wait=8.0):
    """one batch through the channel; True once the game has run it"""
    global _batch
    if status() is None:
        say("the channel isn't up (is the game running, with live=1? python tools/live_reload.py on)")
        return False
    _batch += 1
    tmp = os.path.join(GAME, "U2Live.cmd.tmp")
    with open(tmp, "w") as f:
        f.write("live batch %d\n" % _batch)
        for l in lines:
            f.write(l + "\n")
    os.replace(tmp, os.path.join(GAME, "U2Live.cmd"))
    ack = os.path.join(GAME, "U2Live.ack")
    t = time.time()
    while time.time() - t < wait:
        if os.path.exists(ack) and open(ack).read().strip() == str(_batch):
            return True
        time.sleep(0.1)
    say("no acknowledgement for batch", _batch)
    return False


def log_size():
    return os.path.getsize(LOG) if os.path.exists(LOG) else 0


def wait_log(pattern, since, timeout):
    t = time.time()
    while time.time() - t < timeout:
        if os.path.exists(LOG):
            with open(LOG, "rb") as f:
                if os.path.getsize(LOG) < since:
                    since = 0                       # a new log (the game restarted)
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
    if not send(["live reload"]):
        return
    say("reloading", status()["map"] if status() else "")
    got = wait_log(r"live: resumed [^\r\n]*", since, 90)
    say(got or "no resume seen in AdventNative.log within 90 s")


def restart(build):
    if not send(["live save"]):
        return
    m = resume_map()
    say("saved the player's place on", m, "- closing the game")
    send(["exit"], wait=2)
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
    since = 0
    subprocess.Popen([os.path.join(GAME, "advent.exe")], cwd=GAME)
    say("started the game into", m)
    got = wait_log(r"live: resumed [^\r\n]*", since, 180)
    # the title screen's one-off command back as it was
    set_debug_commands(old.split("=", 1)[1] if old else "")
    say(got or "no resume seen within 3 minutes")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "on":
        set_live(True)
    elif cmd == "off":
        set_live(False)
    elif cmd == "status":
        s = status()
        say("up on %s (%s)" % (s["map"], s["exe"]) if s else "not up")
    elif cmd == "send":
        say("ran" if send(sys.argv[2:]) else "not run")
    elif cmd == "reload":
        reload()
    elif cmd == "restart":
        restart("--build" in sys.argv)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
