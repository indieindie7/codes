r"""Live editing: change the running game while the user plays (AvalonLive in U2AvalonCards).

    py tools/live.py "say hello" "weather storm" "extra 20 CraneTower 1000 -9000 120 6000 8" [wait=10]
    py tools/live.py --file cmds.txt          one command per line
    py tools/live.py --where                  ask where the player stands (prints it from the log)

Each call writes System\AvalonLive.txt as one new batch ("avalon batch N" + "avalon <cmd>" lines) and,
unless wait=0, watches Unreal2.log until the game reports the batch ("Cards: live batch N"). The game
polls the file every couple of seconds through its console's EXEC command, so nothing is typed into
the user's game and nothing needs a reload. Commands: see AvalonLive.uc (say, extra, card, prop, plume,
truck, haze, weather, rebuild, save, where).
"""
import os, re, sys, time

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
LIVE = os.path.join(GAME, "System", "AvalonLive.txt")
LOG = os.path.join(GAME, "System", "Unreal2.log")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".live_seq")


def next_seq():
    # above anything already in the file, so a new batch always counts as new for the game
    n = 0
    for path in (STATE, LIVE):
        try:
            m = re.search(r"(?:batch\s+)?(\d+)", open(path).read())
            n = max(n, int(m.group(1)) if m else 0)
        except OSError:
            pass
    n += 1
    open(STATE, "w").write(str(n))
    return n


def send(cmds, wait=10.0):
    n = next_seq()
    start = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    tmp = LIVE + ".tmp"
    with open(tmp, "w", newline="\r\n") as f:
        f.write("avalon batch %d\n" % n)
        for c in cmds:
            f.write("avalon %s\n" % c.strip())
    os.replace(tmp, LIVE)                    # whole, never half-written when the game reads it
    print("batch %d: %d command(s) -> %s" % (n, len(cmds), LIVE))
    if wait <= 0:
        return n, []
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(0.5)
        try:
            with open(LOG, "rb") as f:
                f.seek(start)
                new = f.read().decode("latin1", "replace")
        except OSError:
            continue
        if "Cards: live batch %d" % n in new:
            time.sleep(0.6)
            with open(LOG, "rb") as f:
                f.seek(start)
                new = f.read().decode("latin1", "replace")
            lines = [l for l in new.splitlines() if "Cards: live" in l]
            print("applied in %.1f s" % (time.time() - t0))
            for l in lines:
                print("  ", l.split("ScriptLog:")[-1].strip())
            return n, lines
    print("not applied within %.0f s (is the game running Avalon with U2AvalonCards?)" % wait)
    return n, []


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("wait=")]
    w = float(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("wait=")), 20))
    if args and args[0] == "--file":
        cmds = [l for l in open(args[1]).read().splitlines() if l.strip() and not l.startswith("#")]
    elif args and args[0] == "--where":
        cmds = ["where"]
    else:
        cmds = args
    send(cmds, w)
