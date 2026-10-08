r"""Log triage for Unreal II runs: script errors bucketed, crashes, autoplay events, audit findings.

    py triage.py <Unreal2.log or run folder> [baseline=<name>] [save=1] [md=<out.md>]

Buckets every ScriptWarning by (function, kind of error) - "Accessed None", "array out of bounds",
"remove element -1", ... - with counts and one sample line; plus engine errors (Failed to load, can't
find, SpawnActor failed, runaway loop, Critical / General protection fault = a crash). With
baseline=NAME it compares against triage_baseline/NAME.json and lists the NEW buckets (a run fails on a
new bucket or a crash); save=1 writes the current buckets as that baseline. Also summarises U2AutoPlay's
"AutoPlay: EVT ..." events (STUCK, FELL, DIED, NOPROGRESS) and "AutoPlay: AUDIT ..." findings.

Exit code: 0 clean, 1 new buckets or a crash (for scripts and nightly runs).
"""
import json, os, re, sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "triage_baseline")

WARN = re.compile(r"ScriptWarning: (\S+) (\S+) \(Function ([\w.]+):\w+\) (?:[\d.]+ )?(.*)$")   # the time is there only in some builds
KINDS = [
    ("accessed none", re.compile(r"Accessed None")),
    ("assign through none", re.compile(r"Attempt to assign variable through None")),
    ("array out of bounds", re.compile(r"Accessed array .* out of bounds|out of bounds")),
    ("bad array remove", re.compile(r"Attempt to remove element")),
    ("null class context", re.compile(r"Accessed null class context")),
    ("infinite loop", re.compile(r"[Ii]nfinite (script )?recursion|[Rr]unaway loop")),
]
ENGINE = [
    ("failed to load", re.compile(r"Failed to load|Can't find (file|package)|couldn't load", re.I)),
    ("spawn failed", re.compile(r"SpawnActor failed|failed to spawn", re.I)),
    ("runaway loop", re.compile(r"Runaway loop", re.I)),
    ("crash", re.compile(r"^Critical:|General protection fault|Unhandled exception|Assertion failed")),
]


def kind_of(msg):
    for k, rx in KINDS:
        if rx.search(msg):
            return k
    return re.sub(r"[-\d.]+", "N", msg.strip())[:60]


def triage(text):
    buckets = OrderedDict()
    engine = Counter()
    engine_sample = {}
    events = Counter()
    event_lines = []
    audit = Counter()
    audit_lines = []
    for line in text.splitlines():
        m = WARN.search(line)
        if m:
            cls, obj, func, msg = m.groups()
            key = "%s | %s" % (func, kind_of(msg))
            b = buckets.setdefault(key, {"count": 0, "sample": line.strip()[:220]})
            b["count"] += 1
            continue
        for k, rx in ENGINE:
            if rx.search(line):
                engine[k] += 1
                engine_sample.setdefault(k, line.strip()[:220])
        if "AutoPlay: EVT " in line:
            w = line.split("AutoPlay: EVT ", 1)[1].split()
            if w:
                events[w[0]] += 1
                event_lines.append(" ".join(w))
        elif "AutoPlay: AUDIT " in line:
            w = line.split("AutoPlay: AUDIT ", 1)[1].split()
            if w and w[0] not in ("NODE", "EDGE", "started:"):     # the network dump is heatmap.py's
                audit[w[0]] += 1
                audit_lines.append(" ".join(w))
    return {"buckets": buckets, "engine": dict(engine), "engine_sample": engine_sample,
            "events": dict(events), "event_lines": event_lines, "audit": dict(audit), "audit_lines": audit_lines}


def report(t, new=None, baseline=None):
    out = ["# Run triage", ""]
    crash = t["engine"].get("crash", 0)
    status = "CRASH" if crash else ("NEW ERRORS" if new else "clean")
    out.append("**%s** - %d script error buckets (%d lines), engine: %s, autoplay events: %s, audit: %s" % (
        status, len(t["buckets"]), sum(b["count"] for b in t["buckets"].values()),
        t["engine"] or "none", t["events"] or "none", t["audit"] or "none"))
    if baseline:
        out.append("Baseline `%s`: %d new bucket(s)." % (baseline, len(new or [])))
    if new:
        out += ["", "## New since the baseline", ""] + ["- `%s` x%d  \n  `%s`" % (k, t["buckets"][k]["count"], t["buckets"][k]["sample"]) for k in new]
    out += ["", "## Script errors (by count)", ""]
    for k, b in sorted(t["buckets"].items(), key=lambda kv: -kv[1]["count"]):
        out.append("- %5d  `%s`" % (b["count"], k))
    if t["engine"]:
        out += ["", "## Engine", ""] + ["- %s x%d: `%s`" % (k, n, t["engine_sample"][k]) for k, n in t["engine"].items()]
    if t["event_lines"]:
        out += ["", "## Autoplay events", ""] + ["- " + l for l in t["event_lines"][:80]]
    if t["audit_lines"]:
        out += ["", "## Audit", ""] + ["- " + l for l in t["audit_lines"][:200]]
    return "\n".join(out) + "\n"


def main():
    a = [x for x in sys.argv[1:] if "=" not in x]
    o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    path = a[0]
    if os.path.isdir(path):
        path = os.path.join(path, "Unreal2.log")
    t = triage(open(path, "rb").read().decode("latin1", "replace"))
    new, name = None, o.get("baseline")
    if name:
        os.makedirs(BASE, exist_ok=True)
        bp = os.path.join(BASE, name + ".json")
        old = json.load(open(bp)) if os.path.exists(bp) else {}
        new = [k for k in t["buckets"] if k not in old]
        if o.get("save") == "1":
            json.dump({k: v["count"] for k, v in t["buckets"].items()}, open(bp, "w"), indent=1)
    md = report(t, new, name)
    out = o.get("md") or os.path.join(os.path.dirname(path), "triage.md")
    open(out, "w", encoding="utf-8").write(md)
    print(md[:1500])
    print("->", out)
    sys.exit(1 if (t["engine"].get("crash") or new) else 0)


if __name__ == "__main__":
    main()
