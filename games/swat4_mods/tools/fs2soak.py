"""Frozen Synapse 2 AI-vs-AI soak: Charon plays both teams, we log each turn.

  py -3.13 -I fs2soak.py [matches=3] [out=fs2soak.jsonl]

Needs the smbridge (fs2bridge.py --install) and FS2 running, not minimized.
Per match: quitSP() + playQuickFS2Skirmish() (the real QUICK SKIRMISH button;
testFS2Skirmish / playRandomSPMatch build levels with 0 nav nodes and crash at
"Generating floor splat details"). Only turn 0->1 advances so far: later
submits run Charon + loadMT but reload the same turn (PORTS-HOOKS.md). Per turn:
$gcmAIDoesBothSides=1 + $gThreadCharon=0 (threaded Charon loses the
$aiTurnCallback and the turn hangs on the loading screen), spSubmitTurn(),
wait for getCurrentTurnNumber() to move, log alive flags + plan sizes.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs2bridge import OUT, send

LOG = os.path.expandvars(r"%APPDATA%\FrozenSynapse2\console.log")
UNITS = range(1, 16)


def ask(expr, pre="", timeout=60):
    """Run statements `pre`, then return TorqueScript expression `expr` as a string."""
    n = sum(1 for _ in open(OUT, encoding="latin-1")) if os.path.exists(OUT) else 0
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        send([f'{pre} SMB_out("@@" @ ({expr}));'], timeout)
    for l in open(OUT, encoding="latin-1").read().splitlines()[n:]:
        if "@@" in l:
            return l.split("@@", 1)[1]
    return ""


def run(stmt, timeout=60):
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        send([stmt], timeout)


def log_tail(pos):
    # the game holds console.log open and locks it now and then: retry
    for _ in range(40):
        try:
            with open(LOG, "rb") as f:
                f.seek(pos)
                return f.read().decode("latin-1", "replace"), f.tell()
        except PermissionError:
            time.sleep(0.5)
    return "", pos


def alive():
    s = ask("%s", '%s=""; for(%i=1;%i<16;%i++) %s=%s @ getUnitIdIsAlive(%i);')
    return [int(c) for c in s] if s.isdigit() else []


def turn():
    t = ask("getCurrentTurnNumber()")
    return int(t) if t.lstrip("-").isdigit() else -1


def launch(front=False):
    """Start FS2 (if not running) without taking focus, then park it behind
    all windows un-minimized (minimized = engine nearly stalls)."""
    import ctypes, subprocess
    from bginput import find
    from fs2bridge import GAME, IN
    u32 = ctypes.WinDLL("user32")
    if "FrozenSynapse2" not in subprocess.run(["tasklist"], capture_output=True, text=True).stdout:
        if os.path.exists(IN):
            os.remove(IN)
        si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 1 if front else 7  # SW_SHOWNORMAL / SW_SHOWMINNOACTIVE
        subprocess.Popen([os.path.join(GAME, "FrozenSynapse2.exe"), "-log", "1"], cwd=GAME, startupinfo=si)
    # restore (async: a hung window must not block us) until it stays up
    for _ in range(60):
        time.sleep(2)
        try:
            h = find("FrozenSynapse2")
        except SystemExit:
            continue
        if front:
            u32.ShowWindowAsync(h, 9)  # SW_RESTORE
            u32.SetForegroundWindow(h)
            if not u32.IsIconic(h) and _ > 15:
                break
        elif u32.IsIconic(h):
            u32.ShowWindowAsync(h, 4)  # SW_SHOWNOACTIVATE
            u32.SetWindowPos(h, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x4000)  # HWND_BOTTOM, NOSIZE|NOMOVE|NOACTIVATE|ASYNC
        elif os.path.exists(os.path.join(GAME, "smbridge", "out.txt")) and time.time() - os.path.getmtime(os.path.join(GAME, "smbridge", "out.txt")) < 600:
            break
        elif _ > 20:
            break
    run("$platform::backgroundSleepTime=0; $pref::backgroundSleepTime=0;", 120)


def match(mi, out):
    # a second playRandomSPMatch() while a match is open crashes the game
    # (skirmish.cs "Cannot re-declare object [csMGSSettings]"): leave first
    run("Canvas.popDialog(MessageLoading); Canvas.popDialog(AILoadingGui); quitSP();")
    time.sleep(8)
    run("Canvas.popDialog(MessageLoading); Canvas.popDialog(AILoadingGui); playQuickFS2Skirmish();")
    t0 = time.time()
    while turn() != 0 or not any(alive()):
        if time.time() - t0 > 120:
            return print("match load timeout")
        time.sleep(2)
    time.sleep(5)  # post-load schedules (randSPMatchPostLoad)
    for _ in range(12):
        before, a0 = turn(), alive()
        pos = os.path.getsize(LOG)
        t1 = time.time()
        run("Canvas.popDialog(MessageLoading); $gcmAIDoesBothSides=1; $gThreadCharon=0; spSubmitTurn();")
        while turn() <= before and time.time() - t1 < (300 if before == 0 else 30):  # -1 = no reply while busy
            time.sleep(2)
        txt, _ = log_tail(pos)
        plans = {int(p): (int(e) if e else 0) for p, e in re.findall(
            r"Applying AI for player (\d+).*?\n\s*(?:winning plan has (\d+) edges|player has no winning plan)", txt)}
        time.sleep(3)
        a1, now = alive(), turn()
        rec = dict(match=mi, turn=before, next=now, secs=round(time.time() - t1, 1),
                   alive_before=a0, alive_after=a1, plan_edges=plans,
                   ended=("onEndMatch" in txt or "GameOver" in txt or "activeGameNotifyGameEnded" in txt))
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"m{mi} t{before}->{now} {rec['secs']}s alive {''.join(map(str, a1[:7]))} plans {plans}")
        if now <= before or rec["ended"] or (a1 and not any(a1[:3])) or (a1 and not any(a1[3:7])):
            break


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--front"]
    n = int(a[0]) if a else 3
    path = a[1] if len(a) > 1 else "fs2soak.jsonl"
    launch("--front" in sys.argv)
    with open(path, "a") as out:
        for mi in range(n):
            match(mi, out)
