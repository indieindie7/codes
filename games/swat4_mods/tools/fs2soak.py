"""Frozen Synapse 2 AI-vs-AI soak: Charon plays both teams, we log each turn.

  py -3.13 -I fs2soak.py [matches=3] [out=fs2soak.jsonl]

Needs the smbridge (fs2bridge.py --install) and FS2 running, not minimized.
Per match: quitSP() + playQuickFS2Skirmish() (the real QUICK SKIRMISH button;
testFS2Skirmish / playRandomSPMatch build levels with 0 nav nodes and crash at
"Generating floor splat details"). A fresh launch goes through Steam (playtime
tracking) and waits for the startup sequence to finish (wait_setup). Per turn:
$gThreadCharon=0 (threaded Charon loses the $aiTurnCallback and the turn hangs
on the loading screen), spSubmitTurn(), wait for getCurrentTurnNumber() to move,
doGoToEndOfTurn() to skip the outcome playback, log alive flags + plan sizes.
Charon plans only the AI team (units 5-8); the player team (1-4) gets no plans:
that side is where our AI plugs in. Run 10 (10-24): 2 matches, 7 turns, no crash.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs2bridge import OUT, send

STEAM_APPID = "445020"  # Frozen Synapse 2 (Door Kickers = 248610)
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


def wait_setup(pos, timeout=180):
    """The startup sequence (nextSSStage 0..4) runs for a while after a fresh
    launch; its last step 'SSReadyForMain 4' -> endGame drops back to the main
    screen. A match started before that is torn down (load timeout), and a
    submit in it crashes in Charon apply (FrozenSynapse2.dll+0x489080)."""
    t0, seen = time.time(), ""
    while time.time() - t0 < timeout:
        if os.path.exists(LOG) and os.path.getsize(LOG) < pos:
            pos = 0  # log truncated by the new launch
        txt, pos = log_tail(pos)
        seen += txt
        if "SSReadyForMain 4" in seen and "endGame" in seen.split("SSReadyForMain 4", 1)[1]:
            time.sleep(5)
            return True
        time.sleep(2)
    return False


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
    fresh = "FrozenSynapse2" not in subprocess.run(["tasklist"], capture_output=True, text=True).stdout
    p0 = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    if fresh:
        if os.path.exists(IN):
            os.remove(IN)
        # launched through Steam (user 10-24) so library playtime tracks the gym work.
        # Steam starts the exe with its own env, so the DXVK 3060 filter env below
        # only applies to a direct start (STEAM=0)
        if os.environ.get("FS2_STEAM", "1") == "1":
            subprocess.Popen([r"C:\Program Files (x86)\Steam\steam.exe", "-applaunch", STEAM_APPID, "-log", "1"])
        else:
            si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 1 if front else 4  # SW_SHOWNORMAL / SW_SHOWNOACTIVATE (a minimized start hangs the load)
            # DXVK d3d9.dll in the game dir + this filter = render on the 3060, the 4070 Ti stays free for the user
            env = dict(os.environ, DXVK_FILTER_DEVICE_NAME="RTX 3060", DXVK_LOG_PATH=os.environ["TEMP"])
            subprocess.Popen([os.path.join(GAME, "FrozenSynapse2.exe"), "-log", "1"], cwd=GAME, startupinfo=si, env=env)
        if not front:  # a Steam start shows the window normally: push it behind everything as soon as it exists
            for _ in range(120):
                time.sleep(0.5)
                try:
                    h = find("FrozenSynapse2")
                except SystemExit:
                    continue
                u32.SetWindowPos(h, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x4000)
                break
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
    if fresh and not wait_setup(p0, 300):
        print("startup sequence not seen finishing")


def match(mi, out):
    # a second playRandomSPMatch() while a match is open crashes the game
    # (skirmish.cs "Cannot re-declare object [csMGSSettings]"): leave first
    run('Canvas.popDialog(MessageLoading); Canvas.popDialog(AILoadingGui); if (Canvas.getContent().getName() !$= "MainScreenGui") quitSP();')
    time.sleep(8)
    run("Canvas.popDialog(MessageLoading); Canvas.popDialog(AILoadingGui); if (!isFunction(\"playQuickFS2Skirmish\")) Canvas.setContent(GSBRowserGui);")
    time.sleep(5)  # exec()ing skirmishGenerator.cs by hand instead left the game hung after the load
    run("playQuickFS2Skirmish();")
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
        run("Canvas.popDialog(MessageLoading); $gThreadCharon=0; spSubmitTurn();")  # $gcmAIDoesBothSides=1 stalls the 2nd submit and gives the player side no plans anyway
        while turn() <= before and time.time() - t1 < (300 if before == 0 else 30):  # -1 = no reply while busy
            time.sleep(2)
        # skip the outcome playback: without it game time stays at 4992 and the next
        # submit replays the same turn. Called before the OUTCOME screen is up it does
        # nothing, so retry until getTurnThatWeAreIn() catches up
        for _ in range(15):
            time.sleep(2)
            run("doGoToEndOfTurn();")
            time.sleep(1)
            w = ask("getTurnThatWeAreIn()")
            if w.isdigit() and int(w) >= turn() > before:
                break
        else:
            run("eventOnReachEndOfOutcomePlayback();")
        time.sleep(2)
        txt, _ = log_tail(pos)
        plans = {int(p): (int(e) if e else 0) for p, e in re.findall(
            r"Applying AI for player (\d+).*?\n\s*(?:winning plan has (\d+) edges|player has no winning plan)", txt)}
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
    run('Canvas.popDialog(MessageLoading); quitSP();')  # back to the menu, not a frozen OUTCOME screen
