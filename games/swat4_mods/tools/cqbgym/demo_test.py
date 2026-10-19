"""Few-shot test (bycloud Gen 1.5 idea, video-notes tree/142): does a suspect that watches K "demo" rooms of an
unknown officer and then picks from a small candidate set beat the fixed generalist weights from --train?

Per trial: random officer style (knobs uniform in the --train ranges). Candidates = generalist + N Gaussian
perturbations (the "few gradient steps near pretrained weights" analog). Each candidate is scored on K demo rooms vs
that officer; the best is then tested on fresh held-out rooms. gain = adapted - generalist suspect win rate.

Run: py -3.13 -I demo_test.py --weights <weights_NNNN.json> [--trials 20] [--ks 0,2,5,10] [--out demo_test.json]
"""
import argparse, json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
import gym_v0 as g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--ks", default="0,2,5,10")
    ap.add_argument("--cands", type=int, default=24)
    ap.add_argument("--sigma", type=float, default=0.35)
    ap.add_argument("--test-rooms", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="demo_test.json")
    a = ap.parse_args()
    rng = random.Random(a.seed); t0 = time.time()
    w0 = list(json.load(open(a.weights))["suspect_weights"].values())
    ks = [int(k) for k in a.ks.split(",")]
    res = {k: [] for k in ks}
    for tr in range(a.trials):
        ost = g.off_style([rng.random() for _ in range(5)])
        cands = [w0] + [[x + rng.gauss(0, a.sigma) for x in w0] for _ in range(a.cands)]
        demo = g.rand_rooms(max(ks), rng)
        test = g.rand_rooms(a.test_rooms, rng)
        demo_sc = [[g.fight(c, ost, [r], rng, 2) for r in demo] for c in cands]  # per candidate, per demo room
        base = g.fight(w0, ost, test, rng, 2)
        for k in ks:
            pick = 0 if k == 0 else max(range(len(cands)), key=lambda i: sum(demo_sc[i][:k]))
            res[k].append(round(g.fight(cands[pick], ost, test, rng, 2) - base, 3) if pick else 0.0)
        print(f"trial {tr} style={ {kk: round(v, 2) if isinstance(v, float) else v for kk, v in ost.items()} } base={base:.3f} "
              + " ".join(f"k{k}={res[k][-1]:+.3f}" for k in ks) + f" t={time.time() - t0:.0f}s", flush=True)
    summ = {f"k{k}": dict(mean_gain=round(sum(v) / len(v), 4), wins=sum(x > 0 for x in v), losses=sum(x < 0 for x in v)) for k, v in res.items()}
    out = dict(weights=a.weights, trials=a.trials, cands=a.cands, sigma=a.sigma, test_rooms=a.test_rooms, summary=summ, per_trial=res, secs=round(time.time() - t0))
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
