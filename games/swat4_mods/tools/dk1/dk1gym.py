"""Door Kickers 1 gym: our brain plans the SWAT team through the dk1hook bridge, game AI plays the enemies.

  py -3.13 -I dk1gym.py humans                 dump humans (id team type state x y)
  py -3.13 -I dk1gym.py send "<cmd>" [...]     raw bridge commands (see dk1hook.c)
  py -3.13 -I dk1gym.py run [N] [out.jsonl] [--brain idle|rush|pairs] [--secs 60] [--map 0/0]
  py -3.13 -I dk1gym.py launch                 start through Steam, window parked behind others

Needs bin/dbghelp.dll (build.bat) copied next to DoorKickers.exe and a mission loaded.
Launch goes through Steam (248610) and the window is parked behind everything, never focused.
"""
import json, math, os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

GAME = r"F:\SteamLibrary\steamapps\common\DoorKickers"
BR = os.path.join(GAME, "dk1bridge")
IN, OUT = os.path.join(BR, "in.txt"), os.path.join(BR, "out.txt")
STEAM_APPID = "248610"
SWAT = 0  # m_team of the player's troopers (checked against s_playerTeam in the dump)
_seq = [int(time.time())]


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
                return lines[1:-1]
        except OSError:
            pass
        time.sleep(0.05)
    raise TimeoutError("no bridge answer (game not running, minimized, or hook not loaded)")


def humans():
    out = []
    for l in send(["humans"]):
        f = l.split()
        if len(f) == 7 and f[0].isdigit():
            out.append(dict(id=int(f[0]), team=int(f[1]), type=int(f[2]), state=int(f[3]), x=float(f[4]), y=float(f[5]), wps=int(f[6])))
    return out


def launch():
    """Start DK1 through Steam if needed, then keep its window behind all others (not minimized)."""
    import ctypes
    from bginput import find
    u32 = ctypes.WinDLL("user32")
    if "DoorKickers" not in subprocess.run(["tasklist"], capture_output=True, text=True).stdout:
        subprocess.Popen([r"C:\Program Files (x86)\Steam\steam.exe", "-applaunch", STEAM_APPID])
    for _ in range(120):
        time.sleep(0.5)
        try:
            h = find("DoorKickers")
        except SystemExit:
            continue
        if u32.IsIconic(h):
            u32.ShowWindowAsync(h, 4)  # SW_SHOWNOACTIVATE
        u32.SetWindowPos(h, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x4000)  # HWND_BOTTOM, no size/move/activate, async
        return h


def state():
    """m_state, game time (ms), pause mask."""
    f = send(["state"])[0].split()
    return dict(state=int(f[0]), time=int(f[5]), pause=int(f[9], 16))


def start_mission(lst=0, idx=0):
    """Menu -> loaded mission -> running sim (see PORTS-HOOKS.md DK1 for the states).
    `load` straight from ENDING (11) crashed the game ("Game crashed :(" box, 10-24), so go back to MAIN_MENU first."""
    if state()["state"] != 5:
        send(["setstate 5"])
        time.sleep(3)
    send([f"load {lst} {idx}"])
    for _ in range(60):
        time.sleep(0.5)
        if state()["state"] == 7:  # LOADING_ALMOST_FINISHED waits for a click
            break
    send(["setstate 8"])
    time.sleep(1)
    send(["toggle 0"])


def alive(h):
    return h["state"] not in (0, 1)  # Human::IsDead: m_state 0 or 1


def brain_orders(name, troopers, suspects, last):
    """Return {trooper id: (x, y)} new targets. rush: each trooper to its nearest live suspect;
    pairs: the whole team to the suspect nearest the team centre."""
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


def run_match(brain="rush", secs=60, lst=0, idx=0):
    start_mission(lst, idx)
    t0, last, orders = time.time(), {}, 0
    while True:
        hs = humans()
        tr = [h for h in hs if h["type"] == 1 and alive(h)]
        su = [h for h in hs if h["type"] == 2 and alive(h)]
        st = state()
        if not tr or not su or st["state"] >= 11 or time.time() - t0 > secs:
            break
        new = brain_orders(brain, tr, su, last)
        if new:
            send([f"move {i} {x:.0f} {y:.0f}" for i, (x, y) in new.items()])
            last.update(new); orders += len(new)
        time.sleep(1)
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
