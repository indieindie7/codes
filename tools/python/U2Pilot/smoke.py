r"""Every-map smoke run: load each map in the background, audit it, screenshot it, quit, triage the log.

    py -3.13 smoke.py [maps=M01A,M03A1,...|campaign|all] [wait=8] [autoplay=0]

For each map: a U2Pilot script (map <name>?Mutator=U2AutoPlay.AutoPlayMutator, wait for control, a
screenshot, "autoplay audit", optionally a minute of autoplay, quit), then triage.py on its log. Writes
runs/smoke_<time>/smoke.md: one row per map - loaded or not, crash, script error buckets (new ones
against triage_baseline/<map>.json flagged), audit summary (reachable nodes, one-way, unreachable
items/triggers, orphan events), autoplay events - and links to each run.
Catches: missing packages, load crashes, script errors at start-up, broken path networks.
"""
import glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import triage  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
CAMPAIGN = ["TutA", "TutB", "m01a", "m01b", "m01c", "M01d", "M03A1", "M03A2", "M03A3", "M03B1", "M03B2", "M03B3",
            "M03B4", "M03B5", "m06_acheron", "m06_obolus", "M08A1", "M08A2", "M08B", "M09A", "M09B", "M09D", "M09E",
            "M09F", "M10_Avalon", "M11", "M12"]

o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
sel = o.get("maps", "campaign")
if sel == "campaign":
    maps = CAMPAIGN
elif sel == "all":
    maps = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(GAME, "Maps", "*.un2")))
else:
    maps = sel.split(",")
WAIT = float(o.get("wait", 8))
AUTO = float(o.get("autoplay", 0))

out = os.path.join(HERE, "runs", "smoke_" + time.strftime("%Y%m%d-%H%M%S"))
os.makedirs(out, exist_ok=True)
rows = []
for m in maps:
    script = os.path.join(HERE, "scripts", "_smoke_%s.txt" % m.lower())
    lines = ["# smoke run (smoke.py)", "background", "map %s?Mutator=U2AutoPlay.AutoPlayMutator" % m,
             "waitcontrol 300", "wait %g" % WAIT, "shot", "console autoplay audit", "wait 3"]
    if AUTO > 0:
        lines += ["console god", "console autoplay on", "wait %g" % AUTO, "shot", "console autoplay status", "wait 1"]
    lines += ["quit"]
    open(script, "w").write("\n".join(lines) + "\n")
    print("== %s" % m, flush=True)
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.join(HERE, "u2pilot.py"), script, "--background"], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    m_run = re.search(r"results in (\S+)", p.stdout or "")
    run = m_run.group(1) if m_run else None
    row = {"map": m, "run": run, "secs": int(time.time() - t0)}
    log = os.path.join(run, "Unreal2.log") if run else None
    if log and os.path.exists(log):
        text = open(log, "rb").read().decode("latin1", "replace")
        t = triage.triage(text)
        bp = os.path.join(HERE, "triage_baseline", m.lower() + ".json")
        old = json.load(open(bp)) if os.path.exists(bp) else None
        row.update(loaded="AutoPlay: ready" in text, crash=t["engine"].get("crash", 0), buckets=len(t["buckets"]),
                   errors=sum(b["count"] for b in t["buckets"].values()),
                   new=[k for k in t["buckets"] if old is not None and k not in old],
                   top=sorted(t["buckets"], key=lambda k: -t["buckets"][k]["count"])[:3],
                   engine=t["engine"], events=t["events"],
                   audit=next((l for l in t["audit_lines"] if l.startswith("SUMMARY")), "-"))
        if old is None:                               # the first run is the baseline
            os.makedirs(os.path.dirname(bp), exist_ok=True)
            json.dump({k: v["count"] for k, v in t["buckets"].items()}, open(bp, "w"), indent=1)
        open(os.path.join(run, "triage.md"), "w", encoding="utf-8").write(triage.report(t, row["new"], m.lower()))
    else:
        row.update(loaded=False, crash="?", buckets="?", errors="?", new=[], top=[], engine={}, events={}, audit="no log")
    rows.append(row)
    print("   loaded %s, crash %s, %s buckets, audit: %s" % (row["loaded"], row["crash"], row["buckets"], row["audit"]), flush=True)

md = ["# Smoke run %s" % os.path.basename(out), "", "| map | loaded | crash | error buckets (lines) | new | audit | autoplay | run |",
      "|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append("| %s | %s | %s | %s (%s) | %s | %s | %s | %s |" % (
        r["map"], "yes" if r["loaded"] else "**NO**", r["crash"] or "-", r["buckets"], r["errors"],
        len(r["new"]) or "-", r["audit"].replace("SUMMARY ", ""), r["events"] or "-", os.path.basename(r["run"] or "-")))
md += ["", "## Top script errors per map", ""]
for r in rows:
    if r["top"]:
        md.append("- **%s**: " % r["map"] + "; ".join("`%s`" % k for k in r["top"]))
open(os.path.join(out, "smoke.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("->", os.path.join(out, "smoke.md"))
