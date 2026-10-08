r"""Live editing: change the running game while the user plays (AvalonLive in U2AvalonCards).

    py tools/live.py "say hello" "weather storm" "extra 20 CraneTower 1000 -9000 120 6000 8" [wait=20]
    py tools/live.py --file cmds.txt          one command per line
    py tools/live.py --where                  ask where the player stands (prints it from the log)
    py tools/live.py --status                 is the game listening, and how

Each call writes one new batch ("avalon batch N" + "avalon <cmd>" lines) two ways:
  * the native channel, when it is up (the d3d8 fork with live=1 in U2Shaders.ini rewrites
    System\U2Live.status every 2 s): System\U2Live.cmd, run at the next frame through the console and
    acknowledged in System\U2Live.ack - well under a second;
  * System\AvalonLive.txt, which the U2AvalonCards mutator EXECs every couple of seconds (the fallback,
    and what re-applies the last batch after a map load).
A batch runs once, whichever way arrives first. Unless wait=0 it waits for the game to confirm
("Cards: live batch N" in Unreal2.log). Nothing is typed into the user's game and nothing needs a
reload. Commands: see AvalonLive.uc and AvalonEditor.uc.
"""
import os, re, sys, time

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
SYS = os.path.join(GAME, "System")
LIVE = os.path.join(SYS, "AvalonLive.txt")
LOG = os.path.join(SYS, "Unreal2.log")
CMD = os.path.join(SYS, "U2Live.cmd")
ACK = os.path.join(SYS, "U2Live.ack")
STATUS = os.path.join(SYS, "U2Live.status")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".live_seq")


def next_seq():
    # above anything already sent, so a new batch always counts as new for the game
    n = 0
    for path in (STATE, LIVE, ACK):
        try:
            m = re.search(r"(?:batch\s+)?(\d+)", open(path).read())
            n = max(n, int(m.group(1)) if m else 0)
        except OSError:
            pass
    n += 1
    open(STATE, "w").write(str(n))
    return n


def native_up():
    """the fork's channel: U2Live.status rewritten in the last ~5 s ("up <unix> <exe> <map>")"""
    try:
        w = open(STATUS).read().split()
        t = float(w[1]) if len(w) > 1 and w[0] == "up" else os.path.getmtime(STATUS)
        return time.time() - t < 5, (w[3] if len(w) > 3 else "?")
    except (OSError, ValueError, IndexError):
        return False, None


def write_atomic(path, n, cmds):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="\r\n") as f:
        f.write("avalon batch %d\n" % n)
        for c in cmds:
            f.write("avalon %s\n" % c.strip())
    os.replace(tmp, path)                    # whole, never half-written when the game reads it


def acked(n):
    try:
        return int(open(ACK).read().split()[-1]) >= n
    except (OSError, ValueError, IndexError):
        return False


def pending_batch(timeout=15.0):
    """wait (up to timeout) until the batch now in the live file has been run: the game reads the file only
    every LivePoll seconds, so writing the next batch too soon replaced it unseen (2026-10-07: a shanty
    group was lost that way)"""
    try:
        m = re.search(r"batch\s+(\d+)", open(LIVE).read())
    except OSError:
        return
    if not m:
        return
    want = "Cards: live batch %s" % m.group(1)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with open(LOG, "rb") as f:
                f.seek(max(0, os.path.getsize(LOG) - 400000))
                if want.encode() in f.read():
                    return
        except OSError:
            pass
        time.sleep(0.25)


def send(cmds, wait=20.0):
    pending_batch()
    n = next_seq()
    start = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    write_atomic(LIVE, n, cmds)
    up, mapname = native_up()
    if up:
        write_atomic(CMD, n, cmds)
    print("batch %d: %d command(s) -> %s%s" % (n, len(cmds), "native channel (%s) + " % mapname if up else "", LIVE))
    if wait <= 0:
        return n, []
    t0 = time.time()
    resent = False
    while time.time() - t0 < wait:
        time.sleep(0.25)
        # the fork drops a batch while the map is loading: send it once more if it wasn't acknowledged
        if up and not resent and not os.path.exists(CMD) and time.time() - t0 > 2.5 and not acked(n):
            write_atomic(CMD, n, cmds)
            resent = True
        try:
            with open(LOG, "rb") as f:
                f.seek(start)
                new = f.read().decode("latin1", "replace")
        except OSError:
            continue
        if "Cards: live batch %d" % n in new:
            time.sleep(0.5)
            with open(LOG, "rb") as f:
                f.seek(start)
                new = f.read().decode("latin1", "replace")
            lines = [l for l in new.splitlines() if "Cards: live" in l or "Cards: edit" in l]
            print("applied in %.1f s%s" % (time.time() - t0, " (native)" if acked(n) else ""))
            for l in lines:
                print("  ", l.split("ScriptLog:")[-1].strip())
            return n, lines
    print("not applied within %.0f s (is the game running Avalon with U2AvalonCards?)" % wait)
    return n, []


def marks(n=3):
    """the user's last marks ("avalon mark [note]"): place, view, what the crosshair was on, and the
    screenshot taken with each (the newest Shot*.bmp files, saved next to the game as PNGs)"""
    import glob
    text = open(LOG, "rb").read().decode("latin1", "replace") if os.path.exists(LOG) else ""
    found = [l.split("Cards: edit ", 1)[1] for l in text.splitlines() if "Cards: edit MARK" in l][-n:]
    shots = sorted(glob.glob(os.path.join(SYS, "Shot*.bmp")) + glob.glob(os.path.join(GAME, "ScreenShots", "Shot*.bmp")),
                   key=os.path.getmtime)[-len(found):] if found else []
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marks")
    os.makedirs(out, exist_ok=True)
    pngs = []
    for s in shots:
        try:
            from PIL import Image
            p = os.path.join(out, os.path.splitext(os.path.basename(s))[0] + ".png")
            Image.open(s).convert("RGB").save(p)
            pngs.append(os.path.abspath(p))
        except Exception as e:
            pngs.append("%s (%s)" % (s, e))
    for i, m in enumerate(found):
        print(m)
        if i < len(pngs):
            print("   shot:", pngs[i])
    if not found:
        print("no marks yet (in game: avalon mark [note])")
    return found, pngs


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("wait=")]
    if args and args[0] == "--marks":
        marks(int(args[1]) if len(args) > 1 else 3)
        sys.exit(0)
    w = float(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("wait=")), 20))
    if args and args[0] == "--status":
        up, m = native_up()
        print("native channel:", "up, map %s" % m if up else "down (file poll only)")
        sys.exit(0)
    if args and args[0] == "--file":
        cmds = [l for l in open(args[1]).read().splitlines() if l.strip() and not l.startswith("#")]
    elif args and args[0] == "--where":
        cmds = ["where"]
    else:
        cmds = args
    send(cmds, w)
