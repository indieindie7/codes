r"""Vision review: a local vision model looks at the pilot shots the way the creative team's rubrics would (the user,
2026-10-09: "wire the shots review as part of the process and run it please"). codirect.py scores the LAYOUT (numbers
from the heightmap and the sheets); this scores the PICTURES the game actually drew, with the same four eyes that can
read an image:

  DIRECTOR  the frame (hero on a third, layers with air between them), the hour (back/side light, not flat front
            light), the reveal, the hero as a silhouette against the sky; "the frame may be black, the path may not"
  ARTIST    one dominant landmark, grain contrast between districts, wear, the palette (value separation body/trim/
            accent), figure-ground (nothing lost in the sea, the town compact)
  LEVEL     cover, sightlines and entries as they read from the picture (hitscan mercs win on open ground)
  MARKS     the user's six checklist items (redesign/2026-10-09/marks_checklist.md): nothing floats, no square island,
            no repeating texture on flat ground, not too dark, no rain inside, the horizon rigs visible; plus anything
            that looks wrong (cranes on pyramids, billboard imposters, flat untextured buildings, rails off the edge)

The model is llama-server with a vision projector (--mmproj; storysim.py's `small` server on port 8081, Gemma 4 12B,
OpenAI chat API). One request per shot: the picture (downscaled JPEG) + the rubric, answered as JSON
  {scores: {director, artist, level, marks}: 0..1,
   findings: [{what, where: left/centre/right + near/far, severity: 0..1, rule}], one_line}

    py tools/vision_review.py <run folder | pilot run dir | image...> [--server http://127.0.0.1:8081] [--model local]
                              [--max-shots N] [--resize 1024] [--dry] [--fake answer.txt] [--marks] [--against QUEUE.md]
                              [--out <dir>]

  <run folder>  Documents\U2_research\towns\<Name><seed>: its shots are <run>\shots\*.png|jpg|bmp when that exists,
                else the latest U2Pilot runs for it (runs\*_town_<name> and *_closeups_<name>: frames\f*.bmp)
  pilot run dir a U2Pilot runs\<stamp>_<script> folder (frames\f*.bmp), or any folder of images, or image files
  --dry         write the prompts (<out>\vision_prompts\<shot>.txt) and skip the model; --fake FILE answers every shot
                with FILE's text instead of the model (the parser's test); neither touches the server
  --marks       also write <out>\vision_marks.txt: one `MARK V<n> | <note> | <shot>` line per finding, the line
                format markwatch.sh prints for the user's own `avalon mark` notes
  --against     marks/QUEUE.md (or MARKS.md): the user's notes per Shot*.png; the model's findings are matched to
                them by category and an agreement rate is reported

Outputs: <out>\vision_review.md (a table per shot, the merged top findings, the mean scores) and vision_review.json
(codirect.review reads it as the sixth "vision" entry, beside the five-role mean like the marks). <out> defaults to
the run folder (or the first image's folder).
As a library: probe(server) -> bool (a 1 s /health check); hook(run_dir, name) -> the report.md paragraph or None.
"""
import base64, io, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT_RUNS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "tools", "python", "U2Pilot", "runs"))
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp")
DEFAULT_SERVER = "http://127.0.0.1:8081"
ROLES = ("director", "artist", "level", "marks")

# ---------------------------------------------------------------- the rubrics (compact; the sources are in the docstring)
RUBRIC = {
    "director": (
        "DIRECTOR (cinematography): (1) FRAME: one hero building sits on a third of the width, the town spans 30-60 % of "
        "the width, a leading line (road, pipe, shore) runs into the hero; (2) LAYERS: three depth layers with air "
        "between them (near ground, mid town, far shore/sea/sky), not one flat wall; (3) HOUR: low back or side light "
        "(long shadows, rim light, silhouettes); flat front light or no readable light direction scores low; "
        "(4) REVEAL: the hero is either clearly shown or deliberately hidden by a near mass, never half-cut by the frame "
        "edge; (5) SILHOUETTE: the hero's top crosses the skyline against the sky. The frame may be black (a dark "
        "near edge is fine) but the path the player walks may not: the floor must read at 20 % grey or more."),
    "artist": (
        "ARTIST (the look): (1) ONE LANDMARK: one dominant mass; copies of the landmark or two equal masses dilute it; "
        "(2) GRAIN: coarse big blocks for the company, fine small shacks for the shanty, visibly different sizes between "
        "districts; (3) WEAR: rust, streaks, patches, lean-tos, nothing reads as new plastic; (4) PALETTE: value "
        "separation between body, trim and accent; no 'one flat grey-green clay' look; no identical rim colour on every "
        "shack; no cone towers that read as faces; (5) FIGURE-GROUND: buildings sit on terraces or graded ground, "
        "not on a slope like pieces on a board; nothing lost in the sea; the town reads compact."),
    "level": (
        "LEVEL DESIGNER (how it plays, read from the picture): (1) COVER: within 10-40 m of the viewpoint are there "
        "3+ chest-high pieces (crates, walls, drums, parapets)? (2) SIGHTLINES: are long open lines broken by masses "
        "(open ground past 40 m is where hitscan enemies win)? (3) ENTRIES: can you see 2+ ways in or out of the space "
        "(doors, lanes, stairs, gaps)? (4) a high spot (+3 m) the player could take? (5) a landmark in view to steer "
        "by (tower, hall, stack)?"),
    "marks": (
        "MARKS (the user's own checklist; each failure is a finding): (M1) nothing floats: rocks, building bases, "
        "masts, props must touch the ground; (M2) the island or sea edge must never read as a square or a straight "
        "cut; (M3) no repeating/tiled texture on flat ground, no big flat pads; (M4) not too dark: interiors, decks "
        "and the floor the player stands on must be legible (a dark frame is fine, a black floor is not); (M5) no "
        "rain or weather drawn inside roofed spaces; (M6) horizon structures (oil rigs, flares, far towers) visible "
        "inside the view when the sea horizon is shown. Also anything that looks wrong: cranes on pyramids, billboard "
        "or card-like imposters, untextured flat-palette buildings, railings that do not follow the walkable edge, "
        "things that make no sense (vehicles, banners, crates in rooms), ball-shaped smoke, fog hiding the island, "
        "rendering bugs (white squares, boxes in the sky)."),
}

SYSTEM = ("You are the creative team's reviewer for an Unreal II (2003) level: a company mining town on an island, "
          "a Liandri pyramid tower as the hero landmark on the summit, a shanty in the works' smoke, dusk, rain. Judge "
          "the screenshot ONLY by what is visible. Be concrete: name what you see and where. Answer with JSON only.")

ANSWER_SHAPE = ('{"scores": {"director": 0..1, "artist": 0..1, "level": 0..1, "marks": 0..1}, '
                '"findings": [{"what": "<one concrete sentence>", "where": "<left|centre|right> <near|far>", '
                '"severity": 0..1, "rule": "<director|artist|level|marks>:<rule name, e.g. M1 floats, HOUR, GRAIN>"}], '
                '"one_line": "<the picture in one sentence>"}')

CATEGORIES = {   # for --against: the user's notes and the model's findings, matched by these
    "dark": r"\bdark|black|too dim|unlit|cannot see|can't see",
    "float": r"float|hover|above the ground|off the ground|not touch",
    "square": r"square|straight edge|hard edge of the (sea|island|terrain)|edge of the sea",
    "rain": r"rain|drops|weather inside|falling through",
    "repeat": r"repeat|tiling|tiled|same texture|pattern repeats|flat pad|flat ground",
    "fog": r"\bfog|haze hid|hidden by fog",
    "smoke": r"smoke|plume",
    "crane": r"crane|fishing pole",
    "billboard": r"billboard|imposter|impostor|card|flat sprite|cutout|cut-out",
    "flat": r"untextured|flat.?palette|flat colou?r|one colou?r|clay|no texture|flat.?shaded|low.?detail",
    "rail": r"rail|railing|handrail",
    "clouds": r"cloud",
    "bug": r"\bbug|glitch|artifact|artefact|white square|box(es)? in the sky|missing geometry",
    "weird": r"weird|out of place|makes no sense|odd|strange",
    "face": r"\bface|pareidolia",
    "horizon": r"horizon|oil rig|rigs?\b|far tower",
}


# ---------------------------------------------------------------- shots
def _images_in(d):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(IMG_EXT))


def pilot_runs_for(name):
    """the latest U2Pilot runs for a town: town_<name> then closeups_<name> (town.py's scripts), else any *_<name>"""
    if not os.path.isdir(PILOT_RUNS):
        return []
    runs = sorted(os.listdir(PILOT_RUNS))
    out = []
    for tag in ("town_%s" % name.lower(), "closeups_%s" % name.lower()):
        hits = [r for r in runs if r.lower().endswith("_" + tag)]
        if hits:
            out.append(os.path.join(PILOT_RUNS, hits[-1]))
    if not out:                                         # any script on this map, the seedless name too (route_TutA_Remake)
        for nm in (name.lower(), name.lower().rstrip("0123456789")):
            hits = [r for r in runs if r.lower().endswith("_" + nm) and os.path.isdir(os.path.join(PILOT_RUNS, r, "frames"))]
            if hits:
                out.append(os.path.join(PILOT_RUNS, hits[-1]))
                break
    return out


def find_shots(inputs):
    """inputs: run folders, pilot run dirs, image folders or image files -> [(label, path)]"""
    shots = []
    for inp in inputs:
        inp = os.path.abspath(inp)
        if os.path.isfile(inp):
            shots.append((os.path.splitext(os.path.basename(inp))[0], inp))
        elif os.path.isdir(os.path.join(inp, "frames")):                       # a U2Pilot run dir
            tag = os.path.basename(inp).split("_", 1)[-1]
            shots += [("%s/%s" % (tag, os.path.splitext(os.path.basename(p))[0]), p) for p in _images_in(os.path.join(inp, "frames"))]
        elif os.path.isdir(os.path.join(inp, "shots")):                        # <run>\shots
            shots += [("shots/" + os.path.splitext(os.path.basename(p))[0], p) for p in _images_in(os.path.join(inp, "shots"))]
        elif os.path.isdir(inp):
            imgs = [p for p in _images_in(inp) if not os.path.basename(p).startswith("isl_")]
            if imgs and not os.path.exists(os.path.join(inp, "isl_layout.json")):   # a plain folder of pictures (marks\)
                shots += [(os.path.splitext(os.path.basename(p))[0], p) for p in imgs]
            else:                                                                 # a town run folder: its pilot runs
                for pr in pilot_runs_for(os.path.basename(inp)):
                    shots += find_shots([pr])
    seen, out = set(), []
    for lab, p in shots:
        if p not in seen:
            seen.add(p)
            out.append((lab, p))
    return out


def encode(path, resize=1024, quality=85):
    """the picture as a base64 JPEG no wider/taller than resize (BMP pilot frames included); (b64, (w, h))"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if resize and max(im.size) > resize:
        im.thumbnail((resize, resize), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii"), im.size


# ---------------------------------------------------------------- the model
def prompt_text(label):
    return ("Review this screenshot (%s) against the four rubrics. Score each rubric 0..1 from what is visible "
            "(1 = passes every point, 0.5 = half, 0 = fails). List every concrete problem as a finding with a severity "
            "(1 = ruins the frame, 0.2 = minor), where it is (left/centre/right, near/far) and which rule it breaks. "
            "Interiors: skip the island rules, judge the floor's legibility and the frame.\n\n%s\n\n%s\n\n%s\n\n%s\n\n"
            "Answer with exactly this JSON and nothing else:\n%s"
            % (label, RUBRIC["director"], RUBRIC["artist"], RUBRIC["level"], RUBRIC["marks"], ANSWER_SHAPE))


def probe(server=DEFAULT_SERVER, timeout=1.0):
    """does a llama-server answer on the port? (a 1 s GET /health; no model call, no GPU work)"""
    try:
        with urllib.request.urlopen(server.rstrip("/") + "/health", timeout=timeout) as r:
            return b"ok" in r.read()
    except Exception:
        return False


def chat_image(server, model, text, b64, max_tokens=900, temp=0.2, timeout=600, retry_note=None):
    """one chat completion with the picture (storysim.chat's request shape + an image_url content part)"""
    content = [{"type": "text", "text": text + (("\n\n" + retry_note) if retry_note else "")},
               {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
            "temperature": temp, "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(server.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def parse_answer(text):
    """the model's JSON, robustly: <think> blocks and code fences stripped, the first {...} taken, keys defaulted,
    scores clamped to 0..1; None when there is no JSON object"""
    if not text:
        return None
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    t = re.sub(r"```[a-zA-Z]*\s*", "", t).replace("```", "")
    i = t.find("{")
    if i < 0:
        return None
    dec = json.JSONDecoder()
    d = None
    for start in [m.start() for m in re.finditer(r"\{", t)]:
        try:
            cand, _ = dec.raw_decode(t[start:])
        except ValueError:
            continue
        if isinstance(cand, dict) and ("scores" in cand or "findings" in cand):
            d = cand
            break
        if d is None and isinstance(cand, dict):
            d = cand
    if not isinstance(d, dict):
        return None

    def num(v, default=0.5):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return default
        if x > 1.0 and x <= 10.0:   # a 0..10 scale slipped in
            x /= 10.0
        return max(0.0, min(1.0, x))
    sc = d.get("scores") if isinstance(d.get("scores"), dict) else {}
    scores = {k: num(sc.get(k), 0.5) for k in ROLES}
    finds = []
    for f in d.get("findings") or []:
        if isinstance(f, str):
            f = {"what": f}
        if not isinstance(f, dict):
            continue
        what = str(f.get("what") or f.get("finding") or f.get("issue") or "").strip()
        if not what:
            continue
        finds.append({"what": what, "where": str(f.get("where") or "").strip(), "severity": num(f.get("severity"), 0.5),
                      "rule": str(f.get("rule") or "").strip()})
    finds.sort(key=lambda f: -f["severity"])
    return {"scores": scores, "findings": finds, "one_line": str(d.get("one_line") or d.get("summary") or "").strip()}


def review_shot(label, path, server, model, resize, dry=False, fake=None, out_dir=None):
    b64, size = encode(path, resize)
    text = prompt_text(label)
    rec = {"label": label, "path": path, "size": list(size), "jpeg_kb": round(len(b64) * 3 / 4 / 1024)}
    if out_dir and (dry or fake is not None):
        pdir = os.path.join(out_dir, "vision_prompts")
        os.makedirs(pdir, exist_ok=True)
        open(os.path.join(pdir, re.sub(r"[^A-Za-z0-9_.-]+", "_", label) + ".txt"), "w", encoding="utf-8").write(
            "SYSTEM:\n%s\n\nUSER (+ image %dx%d, %d kB JPEG):\n%s\n" % (SYSTEM, size[0], size[1], rec["jpeg_kb"], text))
    if dry:
        rec["status"] = "dry"
        return rec
    t0 = time.time()
    raw = fake if fake is not None else chat_image(server, model, text, b64)
    ans = parse_answer(raw)
    if ans is None and fake is None:                     # one retry: JSON only
        raw = chat_image(server, model, text, b64, retry_note="Your previous answer was not JSON. Reply with the JSON object only, no prose, no code fence.")
        ans = parse_answer(raw)
    rec["seconds"] = round(time.time() - t0, 1)
    rec["raw"] = raw[-2000:] if isinstance(raw, str) else str(raw)[-2000:]
    if ans is None:
        rec["status"] = "unparsed"
        rec["scores"], rec["findings"], rec["one_line"] = {k: None for k in ROLES}, [], ""
    else:
        rec["status"] = "fake" if fake is not None else "ok"
        rec.update(ans)
    return rec


# ---------------------------------------------------------------- merging + reporting
def _key(f):
    w = re.sub(r"[^a-z ]", "", f["what"].lower())
    words = [x for x in w.split() if len(x) > 3][:4]
    return (f["rule"].split(":")[0].lower(), " ".join(words))


def merge_findings(recs, top=12):
    """the findings over all shots, same rule + similar wording merged (severity = the max, shots counted)"""
    agg = {}
    for r in recs:
        for f in r.get("findings") or []:
            k = _key(f)
            a = agg.setdefault(k, {"what": f["what"], "rule": f["rule"], "severity": 0.0, "shots": [], "where": f["where"]})
            a["severity"] = max(a["severity"], f["severity"])
            a["shots"].append(r["label"])
    out = sorted(agg.values(), key=lambda a: (-a["severity"], -len(a["shots"])))
    return out[:top]


def mean_scores(recs):
    ok = [r for r in recs if r.get("status") in ("ok", "fake")]
    m = {}
    for k in ROLES:
        v = [r["scores"][k] for r in ok if r["scores"].get(k) is not None]
        m[k] = round(sum(v) / len(v), 3) if v else None
    vals = [x for x in m.values() if x is not None]
    m["mean"] = round(sum(vals) / len(vals), 3) if vals else None
    return m


def categories(text):
    t = (text or "").lower()
    return {c for c, rx in CATEGORIES.items() if re.search(rx, t)}


def load_user_notes(path):
    """marks/QUEUE.md or MARKS.md: {ShotNNNNN: [note, ...]} from table rows that reference ![](ShotNNNNN.png)"""
    notes = {}
    if not path or not os.path.exists(path):
        return notes
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        shots = re.findall(r"\((Shot\d+)\.png\)", line)
        if not shots:
            continue
        note = "%s: %s" % (cells[0], cells[1])
        for s in shots:
            notes.setdefault(s, []).append(note)
    return notes


def agreement(recs, notes):
    """per shot with a user note: the user's categories vs the model's (findings + one_line); the share that share one"""
    rows, hit, n = [], 0, 0
    for r in recs:
        base = os.path.splitext(os.path.basename(r["path"]))[0]
        if base not in notes or r.get("status") not in ("ok", "fake"):
            continue
        ucat = set()
        for nt in notes[base]:
            ucat |= categories(nt)
        mtext = " ".join([f["what"] + " " + f["rule"] for f in r.get("findings") or []] + [r.get("one_line", "")])
        mcat = categories(mtext)
        if not ucat:                                   # a note with no checkable category (a request, a typo)
            continue
        n += 1
        shared = ucat & mcat
        hit += 1 if shared else 0
        rows.append({"shot": base, "user": notes[base], "user_cat": sorted(ucat), "model_cat": sorted(mcat), "shared": sorted(shared)})
    return {"rate": round(hit / n, 2) if n else None, "n": n, "agree": hit, "rows": rows}


def write_outputs(recs, out_dir, server, model, marks=False, against=None, title=""):
    os.makedirs(out_dir, exist_ok=True)
    M = mean_scores(recs)
    top = merge_findings(recs)
    agr = agreement(recs, load_user_notes(against)) if against else None
    J = {"when": time.strftime("%Y-%m-%d %H:%M"), "server": server, "model": model, "title": title, "shots": recs,
         "mean": M, "top": top, "agreement": agr}
    json.dump(J, open(os.path.join(out_dir, "vision_review.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    L = ["# Vision review %s" % title, "", "%s shots, model %s on %s, %s" % (len(recs), model, server, J["when"]), ""]
    dry = all(r.get("status") == "dry" for r in recs)
    if dry:
        L += ["DRY RUN: the prompts are in vision_prompts\\ (no model call).", ""]
    L += ["## Mean scores", "", "| director | artist | level | marks | mean |", "|---|---|---|---|---|",
          "| %s |" % " | ".join("-" if M[k] is None else "%.2f" % M[k] for k in ROLES + ("mean",)), ""]
    if top:
        L += ["## Top findings (merged over the shots, by severity)", "", "| sev | rule | finding | where | shots |", "|---|---|---|---|---|"]
        L += ["| %.2f | %s | %s | %s | %s |" % (a["severity"], a["rule"], a["what"].replace("|", "/"), a["where"], ", ".join(a["shots"][:4]) + (" +%d" % (len(a["shots"]) - 4) if len(a["shots"]) > 4 else "")) for a in top]
        L.append("")
    if agr:
        L += ["## Against the user's marks (%s)" % os.path.basename(against), "",
              "agreement %s on %d marked shots (the model's findings share a category with the user's note)" % ("-" if agr["rate"] is None else "%.0f %%" % (100 * agr["rate"]), agr["n"]), "",
              "| shot | user said | user categories | model categories | shared |", "|---|---|---|---|---|"]
        L += ["| %s | %s | %s | %s | %s |" % (r["shot"], "; ".join(r["user"])[:120].replace("|", "/"), ", ".join(r["user_cat"]), ", ".join(r["model_cat"]), ", ".join(r["shared"]) or "-") for r in agr["rows"]]
        L.append("")
    L += ["## Per shot", ""]
    for r in recs:
        L += ["### %s" % r["label"], "", "`%s` (%dx%d, %d kB sent)" % (r["path"], r["size"][0], r["size"][1], r["jpeg_kb"])]
        if r.get("status") == "dry":
            L += ["", "dry: prompt written", ""]
            continue
        if r.get("status") == "unparsed":
            L += ["", "UNPARSED answer (see vision_review.json raw)", ""]
            continue
        L += ["", r.get("one_line") or "-", "", "| director | artist | level | marks |", "|---|---|---|---|",
              "| %s |" % " | ".join("%.2f" % r["scores"][k] for k in ROLES), ""]
        if r.get("findings"):
            L += ["| sev | rule | finding | where |", "|---|---|---|---|"]
            L += ["| %.2f | %s | %s | %s |" % (f["severity"], f["rule"], f["what"].replace("|", "/"), f["where"]) for f in r["findings"]]
            L.append("")
    open(os.path.join(out_dir, "vision_review.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    if marks:
        ml, n = [], 0
        for r in recs:
            for f in r.get("findings") or []:
                if f["severity"] < 0.3:
                    continue
                n += 1
                ml.append("MARK V%d | %s (%s; %s; sev %.1f; vision review) | %s" % (n, f["what"], f["where"] or "-", f["rule"] or "-", f["severity"], r["path"]))
        open(os.path.join(out_dir, "vision_marks.txt"), "w", encoding="utf-8").write("\n".join(ml) + ("\n" if ml else ""))
    return J


def summary_md(J):
    """the report.md paragraph (town.py) / the notes (codirect)"""
    M = J["mean"]
    lines = ["mean %s over %d shots (model %s): %s" % ("-" if M.get("mean") is None else "%.2f" % M["mean"], len(J["shots"]), J.get("model"),
             ", ".join("%s %s" % (k, "-" if M.get(k) is None else "%.2f" % M[k]) for k in ROLES))]
    for a in J.get("top") or []:
        lines.append("- %.2f %s: %s (%s)" % (a["severity"], a["rule"], a["what"], ", ".join(a["shots"][:3])))
    return lines


def hook(run_dir, name, server=DEFAULT_SERVER, model="local", max_shots=16, resize=1024, log=print):
    """town.py's step after the pilot: when a server answers, review the run's pilot shots and return the report.md
    lines; None (with a one-line note) when no server answers or nothing was shot. Never starts a server."""
    if not probe(server):
        log("vision review: no llama-server on %s (start Documents\\Tools\\llm with --mmproj and run py tools/vision_review.py %s); skipped" % (server, run_dir))
        return None
    shots = find_shots([run_dir])[:max_shots]
    if not shots:
        log("vision review: no pilot shots found for %s; skipped" % name)
        return None
    recs = [review_shot(lab, p, server, model, resize, out_dir=run_dir) for lab, p in shots]
    J = write_outputs(recs, run_dir, server, model, marks=True, title=name)
    return summary_md(J) + ["(vision_review.md, vision_review.json, vision_marks.txt)"]


def main(argv):
    args, o = [], {"server": DEFAULT_SERVER, "model": "local", "max_shots": "0", "resize": "1024", "dry": False, "fake": None,
                   "marks": False, "against": None, "out": None}
    it = iter(argv)
    for a in it:
        if a in ("--dry", "--marks"):
            o[a[2:]] = True
        elif a.startswith("--") and a[2:].replace("-", "_") in o:
            o[a[2:].replace("-", "_")] = next(it)
        else:
            args.append(a)
    if not args:
        sys.exit(__doc__)
    shots = find_shots(args)
    n = int(o["max_shots"])
    if n > 0:
        shots = shots[:n]
    if not shots:
        sys.exit("no shots found in %s" % args)
    out_dir = o["out"] or (args[0] if os.path.isdir(args[0]) else os.path.dirname(os.path.abspath(args[0])))
    fake = open(o["fake"], encoding="utf-8").read() if o["fake"] else None
    if not o["dry"] and fake is None and not probe(o["server"]):
        sys.exit("no llama-server answers on %s (it needs --mmproj for pictures); use --dry to write the prompts" % o["server"])
    recs = []
    for i, (lab, p) in enumerate(shots):
        r = review_shot(lab, p, o["server"], o["model"], int(o["resize"]), dry=o["dry"], fake=fake, out_dir=out_dir)
        recs.append(r)
        if r.get("status") in ("ok", "fake"):
            print("%2d/%d %-28s %s  %s" % (i + 1, len(shots), lab, " ".join("%s %.2f" % (k[:3], r["scores"][k]) for k in ROLES), r.get("one_line", "")[:80]), flush=True)
        else:
            print("%2d/%d %-28s %s" % (i + 1, len(shots), lab, r.get("status")), flush=True)
    J = write_outputs(recs, out_dir, o["server"], o["model"], marks=o["marks"], against=o["against"], title=os.path.basename(out_dir))
    print("\n".join(summary_md(J)))
    if J.get("agreement"):
        a = J["agreement"]
        print("agreement with the user's marks: %s (%d of %d marked shots)" % ("-" if a["rate"] is None else "%.0f %%" % (100 * a["rate"]), a["agree"], a["n"]))
    print("->", os.path.join(out_dir, "vision_review.md"))


if __name__ == "__main__":
    main(sys.argv[1:])
