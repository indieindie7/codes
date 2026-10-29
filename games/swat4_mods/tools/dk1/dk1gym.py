"""Door Kickers 1 gym: our brain plans the SWAT team through the dk1hook bridge, game AI plays the enemies.

  py -3.13 -I dk1gym.py humans                 dump humans (id team type state x y)
  py -3.13 -I dk1gym.py send "<cmd>" [...]     raw bridge commands (see dk1hook.c)
  py -3.13 -I dk1gym.py run [N] [out.jsonl] [--brain idle|rush|pairs|swatminds] [--secs 60] [--map 0/0]
  py -3.13 -I dk1gym.py launch                 start C:\Games\DoorKickers (DK1_GAME), window parked behind others

Needs bin/dbghelp.dll (build.bat) copied next to DoorKickers.exe and a mission loaded.
Launch runs the exe directly (Steam must be running; steam_appid.txt) and the window is parked behind everything, never focused.
"""
import json, math, os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 10-29: gym copy on C: (the F: USB enclosure dropped twice mid-sweep); DK1_GAME overrides
GAME = os.environ.get("DK1_GAME", r"C:\Games\DoorKickers")
BR = os.path.join(GAME, "dk1bridge")
IN, OUT = os.path.join(BR, "in.txt"), os.path.join(BR, "out.txt")
STEAM_APPID = "248610"
SWAT = 0  # m_team of the player's troopers (checked against s_playerTeam in the dump)
_seq = [int(time.time() * 1000)]  # ms: back-to-back runs in one second reused seconds-seqs and read stale answers


def send(cmds, timeout=10):
    """Write commands, wait for the matching 'seq N' answer, return result lines."""
    _seq[0] += 1
    tmp = IN + ".tmp"
    with open(tmp, "w") as f:
        f.write(f"seq {_seq[0]}\n" + "\n".join(cmds) + "\n")
    os.replace(tmp, IN)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            lines = open(OUT).read().splitlines()
            if lines and lines[0] == f"seq {_seq[0]}" and lines[-1] == "END":
                if time.time() - t0 > 3:
                    print(f"SLOW send {time.time() - t0:.1f}s {cmds[0][:60]} (+{len(cmds) - 1})", file=sys.stderr)
                return lines[1:-1]
        except OSError:
            pass
        time.sleep(0.05)
    raise TimeoutError(f"no bridge answer to {cmds[0][:60]} (+{len(cmds) - 1}) in {timeout}s (game not running, hung, or hook not loaded)")


def humans():
    out = []
    for l in send(["humans"], 30):
        f = l.split()
        if len(f) == 7 and f[0].isdigit():
            out.append(dict(id=int(f[0]), team=int(f[1]), type=int(f[2]), state=int(f[3]), x=float(f[4]), y=float(f[5]), wps=int(f[6])))
    return out


def mark_bot(secs=900):
    """Tell focusguard this DK1 is a script launch: Steam-started windows get a 60 s 'user launched' pass there,
    which let the game steal focus (10-29). The marker expires, so a later DK1 the user starts plays normally."""
    d = os.path.expanduser(r"~\Documents\Tools\focusguard\botlaunch")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "doorkickers.exe"), "w") as f:
        f.write(str(time.time() + secs))


def park():
    """Move the game window off-screen and to the bottom of the z-order, never activating or minimizing it."""
    import ctypes
    mark_bot()
    from bginput import find
    try:
        h = find("DoorKickers")
    except SystemExit:
        return
    ctypes.WinDLL("user32").SetWindowPos(h, 1, -4000, 0, 0, 0, 0x1 | 0x10 | 0x4000)  # HWND_BOTTOM, NOSIZE|NOACTIVATE|ASYNCWINDOWPOS


def launch():
    """Start DK1 (direct exe) if needed, then keep its window behind all others (not minimized)."""
    import ctypes
    from bginput import find
    u32 = ctypes.WinDLL("user32")
    mark_bot()
    if "DoorKickers" not in subprocess.run(["tasklist"], capture_output=True, text=True).stdout:
        subprocess.Popen([os.path.join(GAME, "DoorKickers.exe")], cwd=GAME)  # direct: steam_appid.txt in GAME, Steam running
    for _ in range(120):
        time.sleep(0.5)
        try:
            h = find("DoorKickers")
        except SystemExit:
            continue
        if u32.IsIconic(h):
            u32.ShowWindowAsync(h, 4)  # SW_SHOWNOACTIVATE
        park()
        return h


def state(timeout=10):
    """m_state, game time (ms), pause mask."""
    f = send(["state"], timeout)[0].split()
    return dict(state=int(f[0]), time=int(f[5]), pause=int(f[9], 16))


def start_mission(lst=0, idx=0):
    """Menu -> loaded mission -> running sim (see PORTS-HOOKS.md DK1 for the states).
    `load` straight from ENDING (11) crashed the game ("Game crashed :(" box, 10-24), so go back to MAIN_MENU first."""
    # the bridge goes silent 10-60 s after a mission ends (ENDING/ENDED teardown) and during map loads: generous timeouts.
    # (The 10-27 "0/30 timeouts" were this plus the F: stall, not the map: 0/30 runs fine from a settled game.)
    if state(90)["state"] != 5:
        send(["setstate 5"], 90)
        time.sleep(3)
        state(90)
    park()
    send([f"load {lst} {idx}"], 90)
    for _ in range(240):
        time.sleep(0.5)
        if state(60)["state"] == 7:  # LOADING_ALMOST_FINISHED waits for a click (loading blocks the bridge 10+ s)
            break
    else:
        raise TimeoutError(f"load {lst}/{idx} never reached state 7")
    send(["setstate 8"], 60)
    time.sleep(1)
    if state(60)["state"] == 9:  # map with a deploy screen: GO with the default entry points
        # DeployScreen::OnDeployGO, as the button; the bare Game::Client_FinishDeploy (`deploy`)
        # reached RUNNING but dropped the deployed troopers (10-24)
        send(["deploygo"], 60)
        for _ in range(40):  # RUNNING comes a second or two later
            time.sleep(0.5)
            if state(60)["state"] == 10:
                break
        else:
            print("WARN still in DEPLOY after deploygo", file=sys.stderr)
    park()  # loading may re-show the window
    send(["toggle 0"], 60)


def alive(h):
    return h["state"] not in (0, 1)  # Human::IsDead: m_state 0 or 1


def brain_orders(name, troopers, suspects, last):
    """Return {trooper id: (x, y)} new targets. rush: each trooper to its nearest live suspect;
    pairs: the whole team to the suspect nearest the team centre."""
    if name == "swatminds":
        import squadbrain
        return squadbrain.orders(troopers, suspects, last) if troopers else {}
    if name == "idle" or not suspects:
        return {}
    if name == "pairs":
        cx = sum(t["x"] for t in troopers) / len(troopers)
        cy = sum(t["y"] for t in troopers) / len(troopers)
        s = min(suspects, key=lambda s: math.hypot(s["x"] - cx, s["y"] - cy))
        want = {t["id"]: (s["x"], s["y"]) for t in troopers}
    else:
        want = {t["id"]: (lambda s: (s["x"], s["y"]))(min(suspects, key=lambda s: math.hypot(s["x"] - t["x"], s["y"] - t["y"])))
                for t in troopers}
    # only re-path when the target moved more than 48 px (each move resets the trooper's plan)
    return {i: p for i, p in want.items() if i not in last or math.hypot(p[0] - last[i][0], p[1] - last[i][1]) > 48}


def components(cg):
    """Connected open regions of the dumped collision grid (bridge `cgrid`, 8-neighbour): label per cell, 0 = blocked.
    A move/route whose goal is blocked or in another region can hang GeneratePath (the old 'Game crashed :(' = 90 s bridge timeout)."""
    w, h, mw, mh = map(int, cg[0].split()[1:5])
    rows, lab, n = cg[1:1 + h], [[0] * w for _ in range(h)], 0
    for y in range(h):
        for x in range(w):
            if rows[y][x] == "." and not lab[y][x]:
                n += 1; lab[y][x] = n; st = [(x, y)]
                while st:
                    cx, cy = st.pop()
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            a, b = cx + dx, cy + dy
                            if 0 <= a < w and 0 <= b < h and rows[b][a] == "." and not lab[b][a]:
                                lab[b][a] = n; st.append((a, b))
    return dict(w=w, h=h, mw=mw, mh=mh, lab=lab)


def region(comp, x, y):
    cx = min(max(int(comp["w"] * x / comp["mw"] - 0.5), 0), comp["w"] - 1)
    cy = min(max(int(comp["h"] * y / comp["mh"] - 0.5), 0), comp["h"] - 1)
    return comp["lab"][cy][cx]


def run_match(brain="rush", secs=60, lst=0, idx=0):
    start_mission(lst, idx)
    for _ in range(20):  # troopers can show up a moment after RUNNING
        if any(h["type"] == 1 for h in humans()):
            break
        time.sleep(0.5)
    send(["opendoors"], 60)  # closed doors stop a trooper dead (Human+0x29c bit 0); no brain issues door actions -> all doors open, all brains
    cg = send(["cgrid"], 30)
    comp = components(cg) if cg and cg[0].startswith("G ") else None
    if brain == "swatminds":
        import squadbrain
        squadbrain.S["ids"] = None  # new match: reset state
        squadbrain.bind(lambda c: send(c, 90), cg, (lambda x, y: region(comp, x, y)) if comp else None)  # walls/doors/props for LOS + pathfinder routes for the train
    t0, last, orders = time.time(), {}, 0
    while True:
        hs = humans()
        tr = [h for h in hs if h["type"] == 1 and alive(h)]
        su = [h for h in hs if h["type"] == 2 and alive(h)]
        st = state(60)
        if not tr or not su or (st["state"] >= 11 and time.time() - t0 > 4) or time.time() - t0 > secs:  # state 11 right after load = stale
            break
        new = brain_orders(brain, tr, su, last)
        if comp:  # goal in a blocked cell or another region than the trooper -> skip (would hang the pathfinder)
            pos = {t["id"]: (t["x"], t["y"]) for t in tr}
            new = {i: p for i, p in new.items() if i in pos and region(comp, *p) and region(comp, *p) == region(comp, *pos[i])}
        if new:
            ans = send([f"move {i} {x:.0f} {y:.0f}" for i, (x, y) in new.items()], 90)  # GeneratePath can stall the frame 10+ s on big maps (the old "crashes")
            if brain == "swatminds":
                import squadbrain
                squadbrain.feedback(list(new), ans)
            last.update(new); orders += len(new)
        time.sleep(1)
    if not any(h["type"] == 1 for h in hs):
        raise TimeoutError("no troopers in the match (load/start failed)")  # sweep.sh relaunches and retries
    n_tr = sum(1 for h in hs if h["type"] == 1)
    n_su = sum(1 for h in hs if h["type"] == 2)
    return dict(brain=brain, map=f"{lst}/{idx}", secs=round(time.time() - t0, 1), game_ms=st["time"], state=st["state"],
                troopers_alive=len(tr), troopers=n_tr, suspects_alive=len(su), suspects=n_su,
                win=bool(tr) and not su, orders=orders)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "humans":
        for h in humans():
            print(h)
    elif a[0] == "send":
        print("\n".join(send(a[1:])))
    elif a[0] == "launch":
        print(launch())
    elif a[0] == "run":
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        pos = [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and not a[i - 1].startswith("--")]
        n = int(pos[0]) if pos else 1
        path = pos[1] if len(pos) > 1 else None
        for _ in range(n):
            r = run_match(opt("--brain", "rush"), float(opt("--secs", 60)), *map(int, opt("--map", "0/0").split("/")))
            print(json.dumps(r))
            if path:
                with open(path, "a") as f:
                    f.write(json.dumps(r) + "\n")
