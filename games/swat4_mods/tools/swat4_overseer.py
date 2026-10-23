"""Gym overseer (10-23, user: "yes, build the strata overseer for the gym"): runs beside swat4_autogym.py, watches it,
and hands new knob candidates from the local LLM (Strata, port 8090) to the engine search.

Every pass (each EVERY new engine cycles in autogym.log, checked every POLL s):
  1. Plain-Python health checks: stale log, tracebacks, challengers the search never retried, high-score games that
     still lost an officer or left a suspect free (possible score loophole), clear rates that do not move.
  2. Strata reads a short digest (curriculum, top candidates per active map, the checks) and proposes up to 2 knob
     sets per active map. They are clamped to the gymrun KNOBS box and queued in engine/<map>/inject.json;
     swat4_gymrun.py runs queued sets before its own ES proposals. Only measured games decide (src="strata" in
     search.json), never the model's opinion.
  3. WATCH.md (newest pass on top) + overseer.log in the autogym out dir.
The LLM step takes the GPU token (gpu_queue.py) and is skipped when the GPU is busy; checks still run.
Stops on the autogym STOP file.  Run hidden:  Start-Process py -ArgumentList '-3.13 -I tools\\swat4_overseer.py' -WindowStyle Hidden
One pass now:  py -3.13 -I tools/swat4_overseer.py --once [--no-llm]
"""
import argparse, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from swat4_gymrun import KNOBS, cand_score  # noqa: E402  (same box the search uses)

OUT = Path("C:/Users/john/Documents/SwatMindsGym/autogym")
GPUQ = Path.home() / ".claude/skills/local-gpu-ai/gpu_queue.py"
STRATA = "http://127.0.0.1:8090/v1/chat/completions"
EVERY, POLL, STALE_MIN, MAX_QUEUE = 10, 300, 40, 2
CHAT = "swat4-overseer"


def log(msg):
    with open(OUT / "overseer.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def cycles():
    """engine cycles so far = gymrun launches in autogym.log"""
    f = OUT / "autogym.log"
    return sum(1 for l in f.open(encoding="utf-8", errors="replace") if l.startswith("== ") and "swat4_gymrun.py" in l) if f.exists() else 0


def active_maps():
    st = json.loads((OUT / "curriculum.json").read_text())
    return st["order"][:st["active"]], st


def search_state(m):
    f = OUT / "engine" / m / "search.json"
    return json.loads(f.read_text()) if f.exists() else dict(tried=[], best=None)


def checks(maps, st, hist):
    out = []
    lf = OUT / "autogym.log"
    age = (time.time() - lf.stat().st_mtime) / 60
    playing = "Swat4.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq Swat4.exe", "/NH"], capture_output=True, text=True).stdout
    if age > STALE_MIN and not playing:
        out.append(f"STALL: autogym.log untouched for {age:.0f} min and no Swat4.exe running")
    tail = lf.read_bytes()[-200_000:].decode("utf-8", "replace")
    tb = tail.count("Traceback")
    if tb:
        out.append(f"ERRORS: {tb} Traceback(s) in the last 200 KB of autogym.log")
    for m in maps:
        s = search_state(m)
        b = s.get("best")
        if not b:
            continue
        ch = [t for t in s["tried"] if t.get("score") is not None and t.get("games", 0) < 6 and t["score"] > b["score"]]
        if len(ch) >= 3:
            out.append(f"{m}: {len(ch)} challengers above best #{b['n']} ({b['score']}) still under 6 games")
        rows = [json.loads(l) for l in (OUT / "engine" / m / "data.jsonl").read_text().splitlines()[-30:] if l.strip()]
        sus = [r for r in rows if r.get("last") and cand_score(r["last"]) >= 3 and (r["last"]["offDown"] or r["last"]["susFree"])]
        if sus:
            out.append(f"{m}: {len(sus)} of last {len(rows)} games scored >= 3 but lost an officer / left a suspect free (score loophole?)")
    rates = st.get("rates", {})
    hist.append(rates)
    if len(hist) >= 4 and all(h == rates for h in hist[-4:]):
        out.append(f"PLATEAU: clear rates unchanged for 4 passes {rates}")
    return out


def digest(maps, st, flags):
    lines = [f"Curriculum: active maps {maps}, clear rates (last 6 games) {st.get('rates')}, promotions {len(st.get('promotions', []))}",
             "Promotion needs clear rate >= 0.8 on every active map. clear = no suspect free and no officer down.",
             "Score per game = 2*arrests + hostagesSecured - 2*officersDown - 2*suspectsFree + 2*paintShare - 0.5*missedThreats + 3 if clear.",
             "Knob box (name: lo..hi): " + ", ".join(f"{k}: {lo}..{hi}" for k, (lo, hi, _) in KNOBS.items()),
             "Knob meaning: IntelW weight of shared intel; IntelRange/IntelLife radius and seconds intel lasts; OrderTimeout s before an order is dropped; "
             "OfficerThink s between officer decisions (lower = faster); MaxDoorDist reach for door picks; ComplyWait s officers hold a compliant suspect (<=0 off).",
             "Health checks: " + ("; ".join(flags) if flags else "none")]
    for m in maps:
        s = search_state(m)
        sc = sorted([t for t in s["tried"] if t.get("score") is not None], key=lambda t: -t["score"])[:8]
        lines.append(f"\n{m}: {len(s['tried'])} candidates, best #{s['best']['n'] if s.get('best') else '-'}")
        for t in sc:
            lasts = t.get("last", [])
            od = sum(x["offDown"] for x in lasts if x); sf = sum(x["susFree"] for x in lasts if x)
            lines.append(f"  #{t['n']} score {t['score']} over {t.get('games')} games (offDown {od}, susFree {sf}, src {t.get('src', 'es')}) knobs {t['knobs']}")
    return "\n".join(lines)


def gpu(cmd, *args):
    r = subprocess.run([sys.executable, "-I", str(GPUQ), cmd, CHAT, *args], capture_output=True, text=True)
    return r.stdout


def ask_strata(text):
    sysmsg = ("You tune a SWAT 4 squad AI training gym. Read the digest. Propose knob sets likely to raise the clear rate "
              "on the weakest active maps, using the patterns in the top candidates (what the good ones share, what is untried). "
              "Reply with ONLY a JSON object: {\"notes\": [<=4 short strings>], \"proposals\": [{\"map\": <map>, \"knobs\": {<all knob names>: number}, \"why\": <short>}]}. "
              f"At most {MAX_QUEUE} proposals per map, values inside the box.")
    body = json.dumps({"messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": text}],
                       "temperature": 0.4, "top_p": 0.95, "max_tokens": 1500,
                       "chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none"}).encode()
    req = urllib.request.Request(STRATA, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        txt = json.loads(r.read())["choices"][0]["message"]["content"]
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
    m = re.search(r"\{.*\}", txt, re.S)
    return json.loads(m.group(0)) if m else {"notes": ["unparsed reply: " + txt[:200]], "proposals": []}


def queue(props, maps):
    done = []
    for p in props:
        m = p.get("map")
        if m not in maps or not isinstance(p.get("knobs"), dict):
            continue
        b = search_state(m).get("best") or {"knobs": {}}
        kn = dict(b["knobs"])
        for k, v in p["knobs"].items():
            if k in KNOBS and isinstance(v, (int, float)):
                lo, hi, _ = KNOBS[k]
                kn[k] = round(min(hi, max(lo, float(v))), 2)
        f = OUT / "engine" / m / "inject.json"
        q = json.loads(f.read_text()) if f.exists() else []
        if len(q) >= MAX_QUEUE:
            continue
        q.append(dict(knobs=kn, why=str(p.get("why", ""))[:200], ts=time.strftime("%Y-%m-%d %H:%M:%S")))
        f.write_text(json.dumps(q, indent=1))
        done.append(f"{m}: {kn}  ({str(p.get('why', ''))[:120]})")
    return done


def strata_results(maps):
    """how earlier Strata candidates did vs the best (the measured verdict)"""
    out = []
    for m in maps:
        s = search_state(m)
        for t in s["tried"]:
            if t.get("src") == "strata" and t.get("score") is not None:
                out.append(f"{m} #{t['n']}: {t['score']} over {t.get('games')} games (best #{s['best']['n']} {s['best']['score']})")
    return out


def one_pass(hist, use_llm):
    maps, st = active_maps()
    flags = checks(maps, st, hist)
    notes, queued = [], []
    if use_llm:
        g = gpu("req", "gym overseer pass", "11", "10", "gpu=0")
        if "GRANTED" in g:
            try:
                r = ask_strata(digest(maps, st, flags))
                notes, queued = r.get("notes", []), queue(r.get("proposals", []), maps)
            except Exception as e:  # keep watching even if the model is down
                notes = [f"Strata call failed: {e}"]
            finally:
                gpu("done")
        else:
            notes = ["LLM skipped: GPU busy (" + g.strip().splitlines()[-1][:80] + ")" if g.strip() else "LLM skipped: no GPU token"]
    block = [f"## {time.strftime('%Y-%m-%d %H:%M')} pass (cycles {cycles()}, maps {maps})",
             "checks: " + ("; ".join(flags) if flags else "ok"),
             *[f"- strata: {n}" for n in notes], *[f"- queued {q}" for q in queued],
             *[f"- verdict {v}" for v in strata_results(maps)], ""]
    wf = OUT / "WATCH.md"
    old = wf.read_text(encoding="utf-8").split("\n## ", 1)[1] if wf.exists() and "\n## " in wf.read_text(encoding="utf-8") else ""
    passes = ("## " + old).split("\n## ")[:20] if old else []
    wf.write_text("# Gym overseer (tools/swat4_overseer.py), newest first\n\n" + "\n".join(block) + ("\n## ".join(passes) if passes else ""), encoding="utf-8")
    log(f"pass: {len(flags)} flags, {len(queued)} queued")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()
    hist = []
    if a.once:
        return one_pass(hist, not a.no_llm)
    last = cycles()
    log(f"start, cycles {last}")
    one_pass(hist, not a.no_llm)
    while not (OUT / "STOP").exists():
        time.sleep(POLL)
        c = cycles()
        if c - last >= EVERY:
            last = c
            one_pass(hist, not a.no_llm)
    log("STOP seen, exit")


if __name__ == "__main__":
    main()
