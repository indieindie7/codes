"""In-engine AI-vs-AI gym: run SWAT 4 with SwatMinds auto officers unattended, A/B a knob, tally outcomes.

Runs up to 3 games at once, each from its own exe copy (Swat4Gym<k>.exe: own single-instance mutex and
ScriptLog name), own ini (Engine.NullRenderDevice: no D3D at all), own live file (?SMLive=) and log (LOG=).
Live file per slot = SwatMindsLive.txt lines + ghost player + --set lines + the mode's lines. Outcome = last `SwatMinds tally` line (written every 30 s).

Run:   py -3.13 -I swat4_gymrun.py [--runs 3] [--secs 300] [--jobs 3] [--set "OrderTimeout 45"] [--out dir] [--map SP-FoodWall] [--modes nearest,scored]
Parse: py -3.13 -I swat4_gymrun.py --parse-only
"""
import argparse, json, re, shutil, subprocess, sys, time
from pathlib import Path

GAME = Path(r"F:\gogGames\SWAT 4")
SYS = GAME / "SwatMinds" / "System"
LIVE = SYS / "SwatMindsLive.txt"  # read only: base lines for every slot
CSYS = GAME / "Content" / "System"
OUT = GAME / "SwatMinds" / "gymruns"
MODES = {
    "nearest": ["set SwatMinds.SwatMindsMutator bScoreDoors False"],
    "scored": ["set SwatMinds.SwatMindsMutator bScoreDoors True"],
}
TALLY = re.compile(r"SwatMinds tally t=(\d+) score=\w+ orders=(\d+) susDown=(\d+) susArrest=(\d+) susFree=(\d+) hostSecured=(\d+) offDown=(\d+) intel=(\d+)")
KEYS = ["t", "orders", "susDown", "susArrest", "susFree", "hostSecured", "offDown", "intel"]


def kill(slot=None):
    names = [f"Swat4Gym{slot}.exe"] if slot else ["Swat4.exe"] + [f"Swat4Gym{k}.exe" for k in range(1, 4)]
    for n in names:
        subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)


def prep_slot(k):
    """Per-slot copies: exe with its own single-instance mutex and ScriptLog name, ini with the null renderer."""
    src = (CSYS / "Swat4.exe").read_bytes()
    exe = CSYS / f"Swat4Gym{k}.exe"
    if not exe.exists():
        b = src.replace("Swat4IsRunning".encode("utf-16le"), f"Swat4IsRunnin{k}".encode("utf-16le"))
        b = b.replace("ScriptLog.log".encode("utf-16le"), f"ScriptLo{k}.log".encode("utf-16le"))
        exe.write_bytes(b)
    ini = (SYS / "Swat4.ini").read_text(encoding="latin-1")
    ini = re.sub(r"(?m)^RenderDevice=.*$", "RenderDevice=Engine.NullRenderDevice", ini)
    ini = re.sub(r"(?m)^WindowedViewportX=.*$", "WindowedViewportX=320", ini)
    ini = re.sub(r"(?m)^WindowedViewportY=.*$", "WindowedViewportY=240", ini)
    (SYS / f"Gym{k}.ini").write_text(ini, encoding="latin-1")
    shutil.copy(SYS / "User.ini", SYS / f"GymUser{k}.ini")


def launch(k, mode, map_, extra):
    lines = LIVE.read_text(encoding="latin-1").splitlines() + ["set SwatMinds.SwatMindsMutator bGhostPlayer True"] + list(extra) + MODES[mode]
    (SYS / f"GymLive{k}.txt").write_text("\n".join(lines) + "\n", encoding="latin-1")
    log = SYS / f"gym{k}.log"
    log.unlink(missing_ok=True)
    si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    subprocess.Popen([str(CSYS / f"Swat4Gym{k}.exe"), f"{map_}?Mutator=SwatMinds.SwatMindsMutator?SMLive=GymLive{k}.txt", "-nointro",
                      f"-ini=Gym{k}.ini", f"-userini=GymUser{k}.ini", f"LOG=gym{k}.log"], cwd=str(SYS), startupinfo=si)
    return log


def batch(jobs, secs, map_, extra):
    """jobs = [(mode, i)], at most 3; all run at once, one slot each."""
    logs = [launch(k, mode, map_, extra) for k, (mode, i) in enumerate(jobs, 1)]
    time.sleep(max(0, secs - 10))
    for k in range(1, len(jobs) + 1):  # clean quit via the live file so the log gets flushed (a kill cuts its tail)
        with open(SYS / f"GymLive{k}.txt", "a", encoding="latin-1") as f:
            f.write("exit\n")
    time.sleep(10)
    for k in range(1, len(jobs) + 1):
        kill(k)
    time.sleep(3)
    out = []
    for log, (mode, i) in zip(logs, jobs):
        dst = OUT / f"{mode}_{i}.log"
        shutil.copy(log, dst); out.append(dst)
    return out


def parse(log):
    txt = log.read_text(encoding="latin-1", errors="replace")
    rows = [dict(zip(KEYS, map(int, m.groups()))) for m in TALLY.finditer(txt)]
    last = rows[-1] if rows else {}
    cmds = re.findall(r"SwatMinds officers (MoveAndClear|BangAndClear|BreachAndClear|BreachBangAndClear|secure|timeout)", txt)
    return dict(last=last, cmds={c: cmds.count(c) for c in set(cmds)},
                asserts=len(re.findall(r"Assertion failed", txt)), crash="Critical:" in txt)


def summarize():
    res = {}
    for log in sorted(OUT.glob("*_*.log")):
        mode = log.stem.rsplit("_", 1)[0]
        res.setdefault(mode, []).append(dict(run=log.stem, **parse(log)))
    lines = ["| mode | runs | t | orders | susDown | susArrest | susFree | hostSecured | offDown | asserts |", "|---|---|---|---|---|---|---|---|---|---|"]
    for mode, runs in res.items():
        ok = [r for r in runs if r["last"]]
        avg = lambda k: round(sum(r["last"][k] for r in ok) / len(ok), 2) if ok else "-"
        lines.append(f"| {mode} | {len(ok)}/{len(runs)} | {avg('t')} | {avg('orders')} | {avg('susDown')} | {avg('susArrest')} | {avg('susFree')} | {avg('hostSecured')} | {avg('offDown')} | {sum(r['asserts'] for r in runs)} |")
    (OUT / "summary.json").write_text(json.dumps(res, indent=1))
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--secs", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument("--map", default="SP-FoodWall")
    ap.add_argument("--modes", default="nearest,scored")
    ap.add_argument("--set", action="append", default=[], help="extra live line for every mode, e.g. \"OrderTimeout 45\" (SwatMindsMutator prop value)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--parse-only", action="store_true")
    a = ap.parse_args()
    OUT = Path(a.out)
    OUT.mkdir(exist_ok=True)
    if not a.parse_only:
        kill()
        for k in range(1, a.jobs + 1):
            prep_slot(k)
        todo = [(mode, i) for i in range(a.runs) for mode in a.modes.split(",")]  # interleaved so drift hits both
        extra = ["set SwatMinds.SwatMindsMutator " + x for x in a.set]
        for n in range(0, len(todo), a.jobs):
            print(batch(todo[n:n + a.jobs], a.secs, a.map, extra), flush=True)
    summarize()


if __name__ == "__main__":
    sys.exit(main())
