"""In-engine AI-vs-AI gym: run SWAT 4 with SwatMinds auto officers unattended, A/B a knob, tally outcomes.

Runs up to 3 games at once, each from its own exe copy (Swat4Gym<k>.exe: own single-instance mutex and
ScriptLog name), own ini (Engine.NullRenderDevice: no D3D at all), own live file (?SMLive=) and log (LOG=).
Live file per slot = SwatMindsLive.txt lines + ghost player + --set lines + the mode's lines. Outcome = last `SwatMinds tally` line (written every 30 s).

Run:   py -3.13 -I swat4_gymrun.py [--runs 3] [--secs 300] [--jobs 3] [--set "OrderTimeout 45"] [--out dir] [--map SP-FoodWall] [--modes nearest,scored]
Search: py -3.13 -I swat4_gymrun.py --search 1 --secs 300 --out <dir>   (score = arrests + hostSecured - 2*offDown - susFree, mean of 3 games)
Parse: py -3.13 -I swat4_gymrun.py --parse-only
"""
import argparse, json, random, re, shutil, subprocess, sys, time
from pathlib import Path

GAME = Path(r"F:\gogGames\SWAT 4")
SYS = GAME / "SwatMinds" / "System"
LIVE = SYS / "SwatMindsLive.txt"  # read only: base lines for every slot
CSYS = GAME / "Content" / "System"
OUT = GAME / "SwatMinds" / "gymruns"
STALL = 150  # s after launch by which a slot must have logged "SwatMinds url", else it is relaunched once
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


def batch(jobs, secs, map_, extra, dest=None):
    """jobs = [(mode, i)], at most 3; all run at once, one slot each."""
    logs = [launch(k, mode, map_, extra) for k, (mode, i) in enumerate(jobs, 1)]
    t0 = time.time()
    time.sleep(min(STALL, secs))
    for k, (mode, i) in enumerate(jobs, 1):  # a slot that never reached the mutator (stuck loading) gets one relaunch
        log = logs[k - 1]
        if not (log.exists() and "SwatMinds url" in log.read_text(encoding="latin-1", errors="replace")):
            print(f"slot {k} stalled loading, relaunching", flush=True)
            kill(k); time.sleep(2)
            launch(k, mode, map_, extra)
    time.sleep(max(0, secs - 10 - (time.time() - t0)))
    for k in range(1, len(jobs) + 1):  # clean quit via the live file so the log gets flushed (a kill cuts its tail)
        with open(SYS / f"GymLive{k}.txt", "a", encoding="latin-1") as f:
            f.write("exit\n")
    time.sleep(10)
    for k in range(1, len(jobs) + 1):
        kill(k)
    time.sleep(3)
    out = []
    for log, (mode, i) in zip(logs, jobs):
        dst = (dest or OUT) / f"{mode}_{i}.log"
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


# --search: random -> (1+lambda)-ES over the hot knobs; each candidate = 3 parallel games with the same --set lines
KNOBS = {  # name: (lo, hi, log-scale?)
    "IntelW": (0.0, 4.0, False), "IntelRange": (300.0, 1500.0, False),
    "IntelLife": (20.0, 180.0, True), "OrderTimeout": (20.0, 90.0, False),
}


def cand_score(last):
    """arrests + hostSecured - 2*offDown - susFree from the last tally line (None if the run left no tally)."""
    if not last:
        return None
    return last["susArrest"] + last["hostSecured"] - 2 * last["offDown"] - last["susFree"]


def propose(tried, rng, n_random=4, sigma=0.2):
    """first n_random candidates uniform in the box; after that Gaussian mutation (sigma = fraction of range) of the best."""
    scored = [t for t in tried if t["score"] is not None]
    if len(scored) < n_random or not scored:
        return {k: round(rng.uniform(lo, hi), 2) if not lg else round(lo * (hi / lo) ** rng.random(), 1) for k, (lo, hi, lg) in KNOBS.items()}
    best = max(scored, key=lambda t: t["score"])["knobs"]
    out = {}
    for k, (lo, hi, lg) in KNOBS.items():
        out[k] = round(min(hi, max(lo, rng.gauss(best[k], sigma * (hi - lo)))), 2)
    return out


def run_knobs(knobs, a, d):
    """3 parallel games with these knobs; returns per-game rows (also appended to <out>/data.jsonl)."""
    extra = ["set SwatMinds.SwatMindsMutator %s %s" % kv for kv in knobs.items()] + ["set SwatMinds.SwatMindsMutator " + x for x in a.set]
    d.mkdir(exist_ok=True)
    logs = batch([("scored", i) for i in range(3)], a.secs, a.map, extra, dest=d)
    rows = [parse(l) for l in logs]
    with open(OUT / "data.jsonl", "a") as f:
        for l, r in zip(logs, rows):
            f.write(json.dumps(dict(ts=time.strftime("%Y-%m-%d %H:%M:%S"), map=a.map, secs=a.secs, knobs=knobs, set=a.set,
                                    log=str(l), score=cand_score(r["last"]), **r)) + "\n")
    return rows


def search(a):
    """--search N new candidates; --reeval M reruns the current best M times (scores are noisy, the mean over all its runs counts)."""
    sdir = OUT / "search_logs"; sdir.mkdir(exist_ok=True)
    sj = OUT / "search.json"
    state = json.loads(sj.read_text()) if sj.exists() else dict(tried=[], best=None)
    rng = random.Random(a.seed + len(state["tried"]) + int(time.time()) % 100000)
    kill()
    for k in range(1, 4):
        prep_slot(k)
    plan = ["new"] * a.search + ["reeval"] * a.reeval
    for what in plan:
        if what == "reeval" and state["best"]:
            rec = next(t for t in state["tried"] if t["n"] == state["best"]["n"])
            rows = run_knobs(rec["knobs"], a, sdir / f"c{rec['n']:03d}_r{len(rec['run_scores'])}")
            rec["run_scores"] += [cand_score(r["last"]) for r in rows]
            rec["last"] += [r["last"] for r in rows]
        else:
            n = len(state["tried"])
            knobs = propose(state["tried"], rng)
            rows = run_knobs(knobs, a, sdir / f"c{n:03d}")
            rec = dict(n=n, knobs=knobs, run_scores=[cand_score(r["last"]) for r in rows], last=[r["last"] for r in rows], asserts=0)
            state["tried"].append(rec)
        rec["asserts"] += sum(r["asserts"] for r in rows)
        ok = [x for x in rec["run_scores"] if x is not None]
        rec["score"] = round(sum(ok) / len(ok), 3) if ok else None
        rec["games"] = len(ok)
        # best = highest mean among candidates with >= 6 good games (2 batches) once any has them (one 3-game batch is too noisy to trust)
        sc_all = [t for t in state["tried"] if t["score"] is not None]
        sure = [t for t in sc_all if t.get("games", 0) >= 6] or sc_all
        state["best"] = max(sure, key=lambda t: t["score"]) if sure else None
        sj.write_text(json.dumps(state, indent=1))
        print(f"{what} {rec['n']}: {rec['knobs']} -> runs {rec['run_scores']} mean {rec['score']}  best {state['best'] and (state['best']['n'], state['best']['score'])}", flush=True)


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
    ap.add_argument("--search", type=int, default=0, metavar="N", help="run N knob-search candidates (3 parallel games each) over IntelW/IntelRange/IntelLife/OrderTimeout; writes <out>/search.json")
    ap.add_argument("--reeval", type=int, default=0, metavar="M", help="with --search: also rerun the current best M times")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    OUT = Path(a.out)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.search or a.reeval:
        return search(a)
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
