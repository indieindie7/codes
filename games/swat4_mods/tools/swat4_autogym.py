"""Autogym: endless SwatMinds training loop that keeps generating data until told to stop.

Each cycle:
  1. Python sim (tools/cqbgym/gym_v0.py --train, new seed, ~35 s): CMA-ES self-play, result row -> sim.jsonl.
  2. In-engine (tools/swat4_gymrun.py): one new knob candidate (3 parallel null-render games); every REEVAL_EVERY-th
     cycle the current best is rerun instead, so the best is backed by >= 6 games. Rows -> engine/data.jsonl,
     state -> engine/search.json. Maps rotate through --maps (one search state per map).
  3. REPORT.md rewritten (counts, best knobs per map, last sim result).

Stops when STOP exists in the out dir (touch it; it is removed on start), after --hours, or on Ctrl+C.
Skips the engine step (sim only) while a real Swat4.exe is running, so the user can play.
Run hidden:  pythonw swat4_autogym.py   (or: Start-Process py -ArgumentList '-3.13 -I swat4_autogym.py' -WindowStyle Hidden)
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable.replace("pythonw.exe", "python.exe")
OUT = Path(r"F:\gogGames\SWAT 4\SwatMinds\autogym")
REEVAL_EVERY = 2  # 10-20 b: rerun the best every 2nd visit (scores are noisy)


def user_playing():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Swat4.exe", "/NH"], capture_output=True, text=True)
    return "Swat4.exe" in r.stdout


def run(cmd, log):
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n== {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(map(str, cmd))}\n"); f.flush()
        return subprocess.run(cmd, cwd=str(HERE), stdout=f, stderr=subprocess.STDOUT, creationflags=0x08000000).returncode  # CREATE_NO_WINDOW


def sim_step(cycle, log):
    wout = OUT / "sim" / f"weights_{cycle:04d}.json"
    wout.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    rc = run([PY, "-I", str(HERE / "cqbgym" / "gym_v0.py"), "--train", "--seed", str(1000 + cycle), "--train-out", str(wout), "--v0", str(HERE / "cqbgym" / "weights_v0.json")], log)
    row = dict(ts=time.strftime("%Y-%m-%d %H:%M:%S"), cycle=cycle, rc=rc, secs=round(time.time() - t), weights=str(wout))
    if wout.exists():
        try:
            r = json.loads(wout.read_text())
            row["result"] = {k: r[k] for k in ("suspect_weights", "officer_knobs", "held_out_suspect_win_vs")}
        except ValueError:
            pass
    with open(OUT / "sim.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")


def engine_step(cycle, map_, secs, log):
    d = OUT / "engine" / map_
    reeval = cycle % REEVAL_EVERY == REEVAL_EVERY - 1 and (d / "search.json").exists()
    args = ["--reeval", "1"] if reeval else ["--search", "1"]
    run([PY, "-I", str(HERE / "swat4_gymrun.py"), *args, "--secs", str(secs), "--map", map_, "--out", str(d), "--seed", str(cycle)], log)


def report(t0, cycles):
    lines = [f"# Autogym report ({time.strftime('%Y-%m-%d %H:%M')})", "",
             f"running since {time.strftime('%Y-%m-%d %H:%M', time.localtime(t0))}, {cycles} cycles this run", ""]
    for sj in sorted((OUT / "engine").glob("*/search.json")):
        st = json.loads(sj.read_text())
        rows = sum(1 for _ in open(sj.parent / "data.jsonl")) if (sj.parent / "data.jsonl").exists() else 0
        b = st.get("best")
        lines.append(f"## {sj.parent.name}: {len(st['tried'])} candidates, {rows} games")
        if b:
            lines.append(f"best #{b['n']}: score {b['score']} over {b.get('games', '?')} games, knobs {b['knobs']}")
        top = sorted([t for t in st["tried"] if t["score"] is not None], key=lambda t: -t["score"])[:5]
        lines += ["", "| n | score | games | knobs |", "|---|---|---|---|"] + [f"| {t['n']} | {t['score']} | {t.get('games', '?')} | {t['knobs']} |" for t in top] + [""]
    sim = OUT / "sim.jsonl"
    if sim.exists():
        rows = sim.read_text().splitlines()
        lines += [f"## sim: {len(rows)} trainings", "last: " + rows[-1][:600], ""]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", default="SP-FoodWall", help="comma list, rotated per cycle")
    ap.add_argument("--secs", type=int, default=600, help="wall seconds per engine batch (3 games)")
    ap.add_argument("--hours", type=float, default=0, help="stop after this many hours (0 = until STOP)")
    ap.add_argument("--no-sim", action="store_true")
    ap.add_argument("--no-engine", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    stop = OUT / "STOP"
    stop.unlink(missing_ok=True)
    log = OUT / "autogym.log"
    maps = a.maps.split(",")
    t0 = time.time()
    done = len(list((OUT / "sim").glob("weights_*.json"))) if (OUT / "sim").exists() else 0  # cycle numbers continue across restarts
    cycles = 0
    while not stop.exists() and not (a.hours and time.time() - t0 > a.hours * 3600):
        cycle = done + cycles
        if not a.no_sim:
            sim_step(cycle, log)
        if not a.no_engine:
            if user_playing():
                run(["cmd", "/c", "echo", "Swat4.exe running (user), engine step skipped"], log)
                time.sleep(60)
            else:
                engine_step(cycle, maps[cycle % len(maps)], a.secs, log)
        cycles += 1
        report(t0, cycles)
    report(t0, cycles)


if __name__ == "__main__":
    sys.exit(main())
