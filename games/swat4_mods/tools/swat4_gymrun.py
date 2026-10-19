"""In-engine AI-vs-AI gym: run SWAT 4 with SwatMinds auto officers unattended, A/B a knob, tally outcomes.

Each run: live file = stock lines + ghost player + the mode's `set` lines, launch minimized, wait, kill,
keep the log, restore the live file. Outcome = last `SwatMinds tally` line (written every 30 s).

Run:   py -3.13 -I swat4_gymrun.py [--runs 3] [--secs 330] [--map SP-FoodWall] [--modes nearest,scored]
Parse: py -3.13 -I swat4_gymrun.py --parse-only
"""
import argparse, json, re, shutil, subprocess, sys, time
from pathlib import Path

GAME = Path(r"F:\gogGames\SWAT 4")
SYS = GAME / "SwatMinds" / "System"
LIVE = SYS / "SwatMindsLive.txt"
OUT = GAME / "SwatMinds" / "gymruns"
MODES = {
    "nearest": ["set SwatMinds.SwatMindsMutator bScoreDoors False"],
    "scored": ["set SwatMinds.SwatMindsMutator bScoreDoors True"],
}
TALLY = re.compile(r"SwatMinds tally t=(\d+) score=\w+ orders=(\d+) susDown=(\d+) susArrest=(\d+) susFree=(\d+) hostSecured=(\d+) offDown=(\d+) intel=(\d+)")
KEYS = ["t", "orders", "susDown", "susArrest", "susFree", "hostSecured", "offDown", "intel"]


def kill():
    subprocess.run(["taskkill", "/F", "/IM", "Swat4.exe"], capture_output=True)


def one_run(mode, i, secs, map_, extra=()):
    orig = LIVE.read_text(encoding="latin-1")
    try:
        LIVE.write_text(orig.rstrip("\n") + "\nset SwatMinds.SwatMindsMutator bGhostPlayer True\n" + "\n".join(list(extra) + MODES[mode]) + "\n", encoding="latin-1")
        (SYS / "Swat4.log").unlink(missing_ok=True)
        si = subprocess.STARTUPINFO(); si.dwFlags = 1; si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        subprocess.Popen([str(GAME / "Content" / "System" / "Swat4.exe"), f"{map_}?Mutator=SwatMinds.SwatMindsMutator", "-nointro"],
                         cwd=str(SYS), startupinfo=si)
        time.sleep(secs)
    finally:
        kill(); time.sleep(3)
        LIVE.write_text(orig, encoding="latin-1")
    dst = OUT / f"{mode}_{i}.log"
    shutil.copy(SYS / "Swat4.log", dst)
    return dst


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
    ap.add_argument("--secs", type=int, default=330)
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
        for i in range(a.runs):
            for mode in a.modes.split(","):  # interleave modes so drift hits both
                print(mode, i, one_run(mode, i, a.secs, a.map, ["set SwatMinds.SwatMindsMutator " + x for x in a.set]), flush=True)
    summarize()


if __name__ == "__main__":
    sys.exit(main())
