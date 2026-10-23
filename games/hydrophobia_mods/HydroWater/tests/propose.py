"""propose.py: ask the local Coder model (127.0.0.1:8091) for ONE change to the HydroWater solver that should bring
the dam-break front speed closer to the lab mean, write it as a unified diff, and queue it as an ops idea whose test
applies the patch, rebuilds, runs tests/score_irl.py (postcheck: gain <= 0 reverts) and writes the verdict.

The model may change src/hydrowater.c or src/hydrowater.h only (a default value or a patch of at most 30 lines).
It never sees or touches tests/score_irl.py, tests/irl_refs.json, tests/irl_baseline.json (the target).
Usage: py -3.13 propose.py [--dry] [--model coder|strata]   (--dry: write the patch, do not queue)
Output: tests/proposals/<YYYYMMDD-HHMM>.patch, .test.json, .prompt.txt, .reply.txt; `ideas.py add` id on the last line.
"""
import argparse, re, datetime, glob, json, os, subprocess, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PY = "C:/Users/john/Documents/Tools/kimodo/venv/Scripts/python.exe"
IDEAS = os.path.expanduser("~/Documents/Tools/ops/ideas.py")
LOGS = os.path.expanduser("~/Documents/Tools/llm/autorun/logs")
DOC = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "hydrophobia-water-upgrade.md")
PORTS = {"coder": 8091, "strata": 8090}
ALLOWED = ("src/hydrowater.c", "src/hydrowater.h")


def doc_section():
    s = open(DOC, encoding="utf-8").read()
    i = s.find("### IRL reference: lab dam break")
    return s[i:i + 3500] if i >= 0 else "(doc section missing)"


def last_verdicts(n=5):
    out = []
    for p in sorted(glob.glob(os.path.join(LOGS, "idea*.verdict.json")), key=os.path.getmtime)[-n:]:
        try: out.append(os.path.basename(p) + " " + open(p, encoding="utf-8").read().strip())
        except Exception: pass
    return "\n".join(out) or "(none yet)"


def solver_excerpt():
    c = open(os.path.join(ROOT, "src/hydrowater.c"), encoding="utf-8").read().splitlines()
    want = [i for i, l in enumerate(c) if "edge_damp" in l or "c_adapt" in l or "alpha = 1.0f" in l]
    seen, out = set(), []
    for i in want:
        for j in range(max(0, i - 3), min(len(c), i + 4)):
            if j not in seen: seen.add(j); out.append(f"{j+1}: {c[j]}")
    return "\n".join(out[:120])


def ask(model, prompt):
    req = {"model": "any", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 8000,
           "chat_template_kwargs": {"enable_thinking": False}}
    r = urllib.request.Request(f"http://127.0.0.1:{PORTS[model]}/v1/chat/completions", json.dumps(req).encode(), {"Content-Type": "application/json"})
    m = json.load(urllib.request.urlopen(r, timeout=900))["choices"][0]["message"]
    return m.get("content") or ("(no content; reasoning only) " + (m.get("reasoning_content") or ""))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--model", default="coder")
    a = ap.parse_args()
    tag = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    base = os.path.join(HERE, "proposals", tag); os.makedirs(os.path.dirname(base), exist_ok=True)
    cur = json.load(open(os.path.join(HERE, "irl_baseline.json"), encoding="utf-8"))
    prompt = f"""You tune a shallow-water solver (C99, src/hydrowater.c) for a game mod. Goal: the dry-bed dam-break front
speed v/sqrt(gH) over t*=1..2.5 should match the lab mean 1.47 (band 1.14..1.74) for column heights 100..400 units
and wet thresholds 0.5..5 %. Current mean score {cur['score']} over {cur['rows']} rows (1 = every row on the mean).
Defaults: alpha 1.0 (bed-change wave only), c_adapt 0.2 (body stamping only), edge_damp 0.7, cfl 0.5, recon 1.
What is known:
{doc_section()}
Last verdicts of earlier proposals (gain > 0 was kept):
{last_verdicts()}
Solver lines around the knobs:
{solver_excerpt()}
Note: alpha only scales bed changes and c_adapt only body velocity stamps; neither acts in this dry-bed dam break, so
changing them is wasted. Candidates that do act: edge_damp, recon (face reconstruction), wet/dry threshold, flux or
wave-speed choices, the time step.
Propose exactly ONE change: a new default value, or a patch of at most 30 changed lines, to src/hydrowater.c or
src/hydrowater.h only. Do not touch tests. Reply with a first line `Title: <at most 8 words>`, then `Why: <one line>`, then a unified diff
(--- a/src/hydrowater.c / +++ b/src/hydrowater.c, correct hunk headers) in a ```diff block. Nothing else."""
    open(base + ".prompt.txt", "w", encoding="utf-8").write(prompt)
    reply = ask(a.model, prompt)
    open(base + ".reply.txt", "w", encoding="utf-8").write(reply)
    m = re.search(r"```diff\s*\n(.*?)```", reply, re.S)
    if not m: print("no diff block in the reply, see", base + ".reply.txt"); sys.exit(1)
    diff = m.group(1)
    files = set(re.findall(r"^\+\+\+ b/(\S+)", diff, re.M))
    if not files or not files <= set(ALLOWED): print("patch touches disallowed files:", files); sys.exit(1)
    if sum(1 for l in diff.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")) > 60:
        print("patch too large"); sys.exit(1)
    open(base + ".patch", "w", encoding="utf-8", newline="\n").write(diff if diff.endswith("\n") else diff + "\n")
    chk = subprocess.run(["git", "apply", "--check", base + ".patch"], cwd=ROOT, capture_output=True, text=True)
    if chk.returncode: print("git apply --check failed:", chk.stderr.strip()); sys.exit(1)
    title = ""
    for ln in reply.strip().splitlines():
        t = ln.strip().strip("#*` ")
        if not t or t.startswith(("```", "---", "+++", "@@", "diff ", "+", "-")) or t.lower().startswith(("title:", "why:")) and len(t) < 8:
            continue
        if t.lower().startswith("title:"): title = t.split(":", 1)[1].strip(); break
        if not title: title = t
    files = re.findall(r"^\+\+\+ b/(\S+)", patch, re.M)
    hunk = re.search(r"^@@[^\n]*@@[ \t]*(.*)$", patch, re.M)
    where = ", ".join(os.path.basename(f) for f in files) + (f" ({hunk.group(1).strip()[:40]})" if hunk and hunk.group(1).strip() else "")
    if len(title) > 70 or not title: title = where or "solver patch"
    else: title = title + " @ " + where
    targets = [os.path.join(ROOT, f) for f in files]
    build = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "build.ps1")]
    test = [{"type": "backup", "target": t} for t in targets] + [
        {"name": "apply", "cmd": ["git", "apply", base + ".patch"], "cwd": ROOT, "timeout": 60},
        {"name": "build", "cmd": build, "cwd": ROOT, "timeout": 600, "after": "apply"},
        {"name": "score", "type": "postcheck", "cmd": [PY, os.path.join(HERE, "score_irl.py")], "cwd": ROOT,
         "min_rows": 20, "revert": targets, "timeout": 1800, "after": "build"},
        {"name": "rebuild", "cmd": build, "cwd": ROOT, "timeout": 600, "after": "score"}]
    json.dump(test, open(base + ".test.json", "w", encoding="utf-8"), indent=1)
    print("patch", base + ".patch"); print("title", title)
    if a.dry: print("dry run, not queued"); return
    how = f"proposal by {a.model} {tag}: apply patch, rebuild, score_irl.py vs irl_baseline.json (postcheck reverts on gain<=0)"
    r = subprocess.run(["py", "-3.13", "-I", IDEAS, "add", f"hydro scorer: {title}", "quality", "Hydrophobia", how, base + ".test.json"],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())


if __name__ == "__main__":
    main()
