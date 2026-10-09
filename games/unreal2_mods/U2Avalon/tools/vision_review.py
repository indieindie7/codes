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
                              [--out <dir>] [--type auto|overview|close-up|interior|detail] [--single] [--fewshot 4]

  <run folder>  Documents\U2_research\towns\<Name><seed>: its shots are <run>\shots\*.png|jpg|bmp when that exists,
                else the latest U2Pilot runs for it (runs\*_town_<name> and *_closeups_<name>: frames\f*.bmp)
  pilot run dir a U2Pilot runs\<stamp>_<script> folder (frames\f*.bmp), or any folder of images, or image files
  --type        the shot type (rules that do not fit it are not asked): from <frames>\shot_types.json (a sidecar
                {"f00003": "interior"}) or the run dir (`_town_` -> overview, `_closeups_` -> close-up), else `auto` asks
                the model one cheap question first; overview | close-up | interior | detail forces it
  --single      the old mode: ONE request with all four rubrics (default: one request per role, 2-4 points + the type)
  --fewshot N   N example pairs of the user's own marks (marks/fewshot.json, built once from marks/*.png + their QUEUE.md
                notes, 512 px) sent as earlier chat turns before the real shot, for the roles they cover (marks, artist);
                0 = off, default 4. A request the server rejects (context) is retried with half as many, down to none.
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
import base64, io, json, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT_RUNS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "tools", "python", "U2Pilot", "runs"))
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp")
DEFAULT_SERVER = "http://127.0.0.1:8081"
ROLES = ("director", "artist", "level", "marks")

# ---------------------------------------------------------------- shot types + the rubrics (2-4 points per role and type)
TYPES = ("overview", "close-up", "interior", "detail")
TYPE_HELP = {"overview": "a wide view of the island/town from outside or above, sea or horizon in frame",
             "close-up": "a ground-level or near view of buildings and props outdoors",
             "interior": "inside a room, corridor, tower or under a deck roof",
             "detail": "one object, a weapon, a menu or a small texture patch"}
RUBRIC = {
    "director": {
        "overview": "(1) FRAME: the hero building on a third of the width, the town 30-60 % of it, a leading line (road, pipe, shore) into the hero; "
                    "(2) LAYERS: near ground, mid town, far sea/sky with air between them, not one flat wall; "
                    "(3) HOUR: low back or side light (long shadows, rim light, a hard silhouette is the right hour); flat even front light scores low.",
        "close-up": "(1) HOUR: low directional light, long shadows, rim light on the edges; (2) FRAME: one clear subject with a leading line into it; "
                    "(3) the subject reads against the sky or a lit wall.",
        "interior": "(1) FRAME: a dark near edge is fine; one lit focal point (window, lamp, door) draws the eye; "
                    "(2) the walkable floor reads at 20 % grey or more; (3) the light has a direction (a shaft, window light).",
        "detail": "(1) the object reads clearly, lit from one side; (2) the background does not fight it.",
    },
    "artist": {
        "overview": "(1) ONE LANDMARK: one dominant mass; copies or equal masses dilute it; (2) GRAIN: coarse company blocks, fine shanty shacks, "
                    "visibly different sizes between districts; (3) PALETTE/WEAR: value separation between body, trim and accent, rust and patches, "
                    "not one flat clay colour; (4) FIGURE-GROUND: buildings on terraces or graded ground, not on a slope like pieces on a board.",
        "close-up": "(1) WEAR: rust, streaks, patches, nothing reads as new plastic; (2) PALETTE: value separation body/trim/accent, no identical "
                    "colour on every piece; (3) SHAPE: a distinct silhouette, no windows-and-door faces, a crane has a lattice and counterweight, "
                    "not one thin line; it sits on the ground.",
        "interior": "(1) materials differ (metal, concrete, wood) and are worn; (2) palette with one accent; (3) props that say how the room is used.",
        "detail": "(1) the material is textured, not flat colour; (2) its palette has value separation.",
    },
    "level": {
        "overview": "(1) LANDMARK in view to steer by; (2) 2+ routes or lanes visible; (3) long open ground is broken by masses.",
        "close-up": "(1) COVER: 3+ chest-high pieces (crates, walls, drums) within 10-40 m; (2) ENTRIES: 2+ ways in or out; (3) a high spot (+3 m).",
        "interior": "(1) COVER: pillars, crates or walls to fight behind; (2) ENTRIES: 2+ doors or openings; (3) sightlines broken, not one long hall.",
        "detail": "Not a play space: score 0.5 and report no findings.",
    },
}
MARKS_ITEMS = (   # (code, shot types it applies to, rule): the user's checklist, only what fits the shot is asked
    ("M1", ("overview", "close-up", "interior"), "NOTHING FLOATS: rocks, building bases, masts, props touch the ground (a gap under a rock, a base hanging in air = finding)"),
    ("M2", ("overview",), "no SQUARE ISLAND: the sea or terrain edge must not read as a straight cut or a square"),
    ("M3", ("overview", "close-up"), "no REPEATING TEXTURE on flat ground, no big flat pads"),
    ("M4", ("overview", "close-up", "interior"), "NOT TOO DARK: only when the floor or walkable surface is in frame, it must be legible (a dark frame is fine, a black floor is not)"),
    ("M5", ("interior",), "no RAIN or weather drawn inside roofed spaces"),
    ("M6", ("overview",), "HORIZON structures (oil rigs, flares, far towers) visible when the sea horizon is shown"),
    ("M7", TYPES, "ANYTHING WRONG: BILLBOARD or card-like imposters (a flat cut-out standing in the scene), cranes on pyramids, a crane that is one thin fishing-pole line, "
                  "untextured flat-colour buildings, railings off the walkable edge, things that make no sense, ball-shaped smoke, white squares or boxes in the sky"),
)


def role_rules(role, stype):
    if role == "marks":
        return "; ".join("(%s) %s" % (c, t) for c, ty, t in MARKS_ITEMS if stype in ty)
    return RUBRIC[role][stype]


SYSTEM = ("You are the creative team's reviewer for an Unreal II (2003) level: a company mining town on an island, a Liandri pyramid tower "
          "as the hero landmark on the summit, a shanty in the works' smoke, dusk, rain. Judge the screenshot ONLY by what is visible and "
          "ONLY by the rules given for its shot type: never report something the rules for that type do not cover (a town missing from "
          "an interior is not a finding). Be concrete: name what you see and where. Answer with JSON only.")
ROLE_SHAPE = ('{"score": 0..1, "findings": [{"what": "<one concrete sentence>", "where": "<left|centre|right> <near|far>", '
              '"severity": 0..1, "rule": "%s:<rule, e.g. M1 floats>"}], "one_line": "<the picture in one sentence>"}')
ANSWER_SHAPE = ('{"scores": {"director": 0..1, "artist": 0..1, "level": 0..1, "marks": 0..1}, '
                '"findings": [{"what": "<one concrete sentence>", "where": "<left|centre|right> <near|far>", '
                '"severity": 0..1, "rule": "<director|artist|level|marks>:<rule name, e.g. M1 floats, HOUR, GRAIN>"}], '
                '"one_line": "<the picture in one sentence>"}')


def role_system(role):
    """one role's system message: the base + that role's rules for every shot type (the user turn names the type)"""
    body = "\n".join("- %s: %s" % (t, role_rules(role, t)) for t in TYPES)
    return ("%s\n\nYou are the %s. Score 0..1 (1 = passes every rule that applies, 0.5 = half, 0 = fails) and list each concrete problem as a "
            "finding with a severity (1 = ruins the frame, 0.2 = minor). The rules by shot type:\n%s\n\nAnswer with exactly this JSON and "
            "nothing else:\n%s" % (SYSTEM, role.upper(), body, ROLE_SHAPE % role))


def user_text(stype):
    return "Shot type: %s (%s). Apply only the rules for this type. JSON only." % (stype, TYPE_HELP[stype])


def prompt_text(label, stype="overview"):
    """the --single prompt: all four roles in one request (type-aware rules)"""
    return ("Review this screenshot (%s). Shot type: %s (%s). Apply ONLY the rules that fit this type.\n\n%s\n\nAnswer with exactly this JSON and "
            "nothing else:\n%s" % (label, stype, TYPE_HELP[stype], "\n".join("%s: %s" % (r.upper(), role_rules(r, stype)) for r in ROLES), ANSWER_SHAPE))


CATEGORIES = {   # for --against: the user's notes and the model's findings, matched by these
    "dark": r"\bdark|black|too dim|unlit|cannot see|can't see|illegible",
    "float": r"float|hover|above the ground|off the ground|not touch|gap under|hanging",
    "square": r"square|straight edge|straight cut|straight line|hard edge of the (sea|island|terrain)|edge of the sea",
    "rain": r"rain|drops|weather inside|falling through",
    "repeat": r"repeat|tiling|tiled|same texture|pattern repeats|flat pad|flat ground",
    "fog": r"\bfog|haze hid|hidden by fog",
    "smoke": r"smoke|plume",
    "crane": r"crane|fishing pole",
    "billboard": r"billboard|imposter|impostor|card|flat sprite|cutout|cut-out|cut out",
    "flat": r"untextured|flat.?palette|flat colou?r|one colou?r|clay|no texture|flat.?shaded|low.?detail",
    "rail": r"rail|railing|handrail",
    "clouds": r"cloud",
    "bug": r"\bbug|glitch|artifact|artefact|white square|box(es)? in the sky|missing geometry|texture box",
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


def declared_type(path):
    """the shot type the pilot's own names give: a sidecar shot_types.json ({"f00003": "interior"}) beside the frames or in the
    run dir, else the run dir's suffix (`_town_` = overview, `_closeups_` = close-up); None when nothing says"""
    stem = os.path.splitext(os.path.basename(path))[0]
    d = os.path.dirname(path)
    for side in (os.path.join(d, "shot_types.json"), os.path.join(os.path.dirname(d), "shot_types.json")):
        if os.path.exists(side):
            try:
                m = json.load(open(side, encoding="utf-8"))
                t = m.get(stem) or m.get(os.path.basename(path))
                if t in TYPES:
                    return t
            except (OSError, ValueError):
                pass
    low = path.lower().replace("/", "\\")
    if "_closeups_" in low:
        return "close-up"
    if "_town_" in low:
        return "overview"
    return None


def encode(path, resize=1024, quality=85):
    """the picture as a base64 JPEG no wider/taller than resize (BMP pilot frames included); (b64, (w, h))"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if resize and max(im.size) > resize:
        im.thumbnail((resize, resize), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii"), im.size


# ---------------------------------------------------------------- the few-shot examples (the user's own marks)
MARKS_DIR = os.path.normpath(os.path.join(HERE, "..", "marks"))
FEWSHOT_FILE = os.path.join(MARKS_DIR, "fewshot.json")
# the categories the first marks pass MISSED (floating objects, billboard cards, repeating texture, the fishing-pole crane), picked
# from the user's marked shots; the answers are written from his notes (marks/QUEUE.md) and what is in the picture.
EXAMPLES = (
    {"shot": "Shot00041", "type": "overview", "answers": {"marks": {"score": 0.3, "findings": [
        {"what": "A dark rock hangs in mid-air in front of the crane tower with open sky under it; it is not touching the ground", "where": "centre near", "severity": 0.9, "rule": "marks:M1 floats"},
        {"what": "The sea edge on the left runs as a straight line, so the island reads square", "where": "left far", "severity": 0.6, "rule": "marks:M2 square"},
        {"what": "The crane tower's base is a pale slab floating over the shore", "where": "centre far", "severity": 0.5, "rule": "marks:M1 floats"}],
        "one_line": "A rocky island under a dusk sky with a floating rock and a floating crane tower."}}},
    {"shot": "Shot00030", "type": "overview", "answers": {"marks": {"score": 0.35, "findings": [
        {"what": "The crane tower on the left is a flat cut-out card standing in the scene, a billboard rather than 3D geometry", "where": "left far", "severity": 0.8, "rule": "marks:M7 billboard"},
        {"what": "The two rigs on the sea are dark flat cards with no depth", "where": "centre far", "severity": 0.6, "rule": "marks:M7 billboard"},
        {"what": "The foreground below the camera is pitch black", "where": "bottom centre", "severity": 0.4, "rule": "marks:M4 dark"}],
        "one_line": "A bright island view where the crane tower and the rigs read as flat cards."}}},
    {"shot": "Shot00042", "type": "overview", "answers": {"marks": {"score": 0.2, "findings": [
        {"what": "The rock surface repeats the same small texture tile over the whole slope", "where": "left near", "severity": 0.7, "rule": "marks:M3 repeat"},
        {"what": "Dozens of square texture boxes float in the sky and over the hill", "where": "centre far", "severity": 0.9, "rule": "marks:M7 rendering bug"},
        {"what": "The railing and the floor on the right are solid black", "where": "right near", "severity": 0.5, "rule": "marks:M4 dark"}],
        "one_line": "A rocky hillside under a dark sky covered in floating texture squares."}}},
    {"shot": "Shot00048", "type": "overview", "answers": {
        "marks": {"score": 0.45, "findings": [
            {"what": "The crane on the tower is a single thin line with no lattice, a fishing pole rather than a crane", "where": "left far", "severity": 0.7, "rule": "marks:M7 fishing-pole crane"},
            {"what": "Several buildings sit on slabs that hover over the rock, their bases floating in the air", "where": "centre near", "severity": 0.6, "rule": "marks:M1 floats"},
            {"what": "The pyramid tower carries a crane, which makes no sense on a pyramid", "where": "centre far", "severity": 0.5, "rule": "marks:M7 crane on pyramid"}],
            "one_line": "A pale pyramid tower with a pole crane over a rocky island with floating building bases."},
        "artist": {"score": 0.4, "findings": [
            {"what": "Every building is the same flat grey-green clay colour with no separation between body, trim and accent", "where": "centre near", "severity": 0.7, "rule": "artist:PALETTE"},
            {"what": "The crane has no lattice and no counterweight, it reads as a fishing pole", "where": "left far", "severity": 0.7, "rule": "artist:SHAPE"}],
            "one_line": "A pale pyramid tower with a pole crane over a rocky island."}}},
    {"shot": "Shot00096", "type": "overview", "answers": {"marks": {"score": 0.5, "findings": [
        {"what": "A red crane is mounted on the pyramid tower, which makes no sense on a pyramid building", "where": "left far", "severity": 0.7, "rule": "marks:M7 crane on pyramid"},
        {"what": "The smoke columns are smooth dark balls", "where": "right far", "severity": 0.4, "rule": "marks:M7 ball smoke"}],
        "one_line": "A tan pyramid tower with a red crane on a rocky island at midday."}}},
)


def build_fewshot(force=False, size=512):
    """marks/fewshot.json (built once, cached; the marks folder is gitignored): each EXAMPLES shot at `size` px as base64 JPEG, the
    user's own QUEUE.md/MARKS.md note(s) for it, and the answer per role. Returns the list."""
    if not force and os.path.exists(FEWSHOT_FILE):
        try:
            return json.load(open(FEWSHOT_FILE, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    notes = {}
    for f in ("QUEUE.md", "MARKS.md"):
        for k, v in load_user_notes(os.path.join(MARKS_DIR, f)).items():
            notes.setdefault(k, []).extend(v)
    out = []
    for e in EXAMPLES:
        p = os.path.join(MARKS_DIR, e["shot"] + ".png")
        if not os.path.exists(p):
            continue
        b64, sz = encode(p, size, 80)
        out.append({"shot": e["shot"], "type": e["type"], "size": list(sz), "user_notes": notes.get(e["shot"], []), "jpeg_b64": b64,
                    "answers": {r: json.dumps(a, ensure_ascii=False) for r, a in e["answers"].items()}})
    json.dump(out, open(FEWSHOT_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def fewshot_messages(role, n, shots):
    """prior chat turns for one role: up to n examples that carry an answer for the role (image + short question -> JSON)"""
    msgs, used = [], []
    for e in shots:
        if len(used) >= n:
            break
        if role not in e["answers"]:
            continue
        msgs.append({"role": "user", "content": [{"type": "text", "text": user_text(e["type"])},
                                                 {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + e["jpeg_b64"]}}]})
        msgs.append({"role": "assistant", "content": e["answers"][role]})
        used.append(e["shot"])
    return msgs, used


# ---------------------------------------------------------------- the model
def probe(server=DEFAULT_SERVER, timeout=1.0):
    """does a llama-server answer on the port? (a 1 s GET /health; no model call, no GPU work)"""
    try:
        with urllib.request.urlopen(server.rstrip("/") + "/health", timeout=timeout) as r:
            return b"ok" in r.read()
    except Exception:
        return False


def chat(server, model, messages, max_tokens=700, temp=0.2, timeout=600):
    """one chat completion (storysim.chat's request shape); -> (text, usage dict)"""
    body = {"model": model, "messages": messages, "temperature": temp, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(server.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"], d.get("usage") or {}


def _img(b64):
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}


def classify_type(server, model, b64_small):
    """the one cheap question: overview, close-up, interior or detail? (a 512 px picture, <= 8 tokens out)"""
    q = ("Which is it: overview (%s), close-up (%s), interior (%s) or detail (%s)? Answer with one word."
         % tuple(TYPE_HELP[t] for t in TYPES))
    text, _ = chat(server, model, [{"role": "user", "content": [{"type": "text", "text": q}, _img(b64_small)]}], max_tokens=8, temp=0.0, timeout=120)
    t = text.lower()
    for key, pat in (("close-up", r"close"), ("interior", r"interior|inside|indoor"), ("detail", r"detail"), ("overview", r"overview|wide")):
        if re.search(pat, t):
            return key
    return "overview"


def parse_answer(text, role=None):
    """the model's JSON, robustly: <think> blocks and code fences stripped, the first {...} taken, keys defaulted,
    scores clamped to 0..1; None when there is no JSON object. role=: a one-role answer ({"score": x} or {"scores": {role: x}}),
    findings whose rule names another role are dropped"""
    if not text:
        return None
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    t = re.sub(r"```[a-zA-Z]*\s*", "", t).replace("```", "")
    if t.find("{") < 0:
        return None
    dec = json.JSONDecoder()
    d = None
    for start in [m.start() for m in re.finditer(r"\{", t)]:
        try:
            cand, _ = dec.raw_decode(t[start:])
        except ValueError:
            continue
        if isinstance(cand, dict) and ("scores" in cand or "score" in cand or "findings" in cand):
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
        if 1.0 < x <= 10.0:   # a 0..10 scale slipped in
            x /= 10.0
        return max(0.0, min(1.0, x))
    sc = d.get("scores") if isinstance(d.get("scores"), dict) else {}
    if role:
        scores = {role: num(sc.get(role, d.get("score")), 0.5)}
    else:
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
        rule = str(f.get("rule") or "").strip()
        pre = rule.split(":")[0].lower()
        if role and pre in ROLES and pre != role:
            continue
        if role and pre not in ROLES:
            rule = (role + ":" + rule) if rule else role + ":"
        finds.append({"what": what, "where": str(f.get("where") or "").strip(), "severity": num(f.get("severity"), 0.5), "rule": rule})
    finds.sort(key=lambda f: -f["severity"])
    return {"scores": scores, "findings": finds, "one_line": str(d.get("one_line") or d.get("summary") or "").strip()}


def ask(server, model, role, stype, b64, shots, n_few, retry=True):
    """one role's request: system (rules) + up to n_few example turns + the real shot. Falls back to fewer examples when the server
    rejects the request (context); -> (parsed or None, raw, info)"""
    n = n_few
    last_err = None
    while True:
        few, used = fewshot_messages(role, n, shots) if n else ([], [])
        msgs = [{"role": "system", "content": role_system(role)}] + few + [
            {"role": "user", "content": [{"type": "text", "text": user_text(stype)}, _img(b64)]}]
        t0 = time.time()
        try:
            raw, usage = chat(server, model, msgs)
        except urllib.error.HTTPError as e:                  # 400 = over the context: halve the examples
            last_err = "HTTP %s" % e.code
            if n == 0:
                raise
            n = n // 2
            continue
        info = {"role": role, "seconds": round(time.time() - t0, 1), "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"), "fewshot": used, "fewshot_requested": n_few, "error_before": last_err}
        ans = parse_answer(raw, role)
        if ans is None and retry:
            msgs2 = msgs[:-1] + [{"role": "user", "content": [{"type": "text", "text": user_text(stype) + " Your previous answer was not JSON: reply with the JSON object only."}, _img(b64)]}]
            t0 = time.time()
            raw, usage = chat(server, model, msgs2)
            info["seconds"] = round(info["seconds"] + time.time() - t0, 1)
            info["retried"] = True
            ans = parse_answer(raw, role)
        return ans, raw, info


def review_shot(label, path, server, model, resize, dry=False, fake=None, out_dir=None, stype="auto", single=False, fewshot=0):
    b64, size = encode(path, resize)
    rec = {"label": label, "path": path, "size": list(size), "jpeg_kb": round(len(b64) * 3 / 4 / 1024), "mode": "single" if single else "roles"}
    # the shot type: forced, else the pilot's own names, else one cheap question to the model
    if stype not in TYPES:
        stype_d = declared_type(path)
        if stype_d:
            rec["type_from"], stype = "pilot", stype_d
        elif dry or fake is not None:
            rec["type_from"], stype = "default (no model asked)", "overview"
        else:
            small, _ = encode(path, 512, 80)
            stype = classify_type(server, model, small)
            rec["type_from"] = "model"
    else:
        rec["type_from"] = "forced"
    rec["type"] = stype
    few = build_fewshot() if (fewshot and not single) else []
    rec["fewshot_n"] = fewshot if few else 0
    if out_dir and (dry or fake is not None):
        pdir = os.path.join(out_dir, "vision_prompts")
        os.makedirs(pdir, exist_ok=True)
        if single:
            body = "SYSTEM:\n%s\n\nUSER (+ image %dx%d, %d kB JPEG):\n%s\n" % (SYSTEM, size[0], size[1], rec["jpeg_kb"], prompt_text(label, stype))
        else:
            body = ""
            for r in ROLES:
                fm, used = fewshot_messages(r, fewshot, few) if few else ([], [])
                body += "=== %s request (type %s; %d few-shot examples: %s)\nSYSTEM:\n%s\n\nUSER (+ image %dx%d, %d kB JPEG):\n%s\n\n" % (
                    r.upper(), stype, len(used), ", ".join(used) or "-", role_system(r), size[0], size[1], rec["jpeg_kb"], user_text(stype))
        open(os.path.join(pdir, re.sub(r"[^A-Za-z0-9_.-]+", "_", label) + ".txt"), "w", encoding="utf-8").write(body)
    if dry:
        rec["status"] = "dry"
        return rec
    t0 = time.time()
    reqs, raws = [], []
    if single:
        text = prompt_text(label, stype)
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": [{"type": "text", "text": text}, _img(b64)]}]
        if fake is not None:
            raw, usage = fake, {}
        else:
            raw, usage = chat(server, model, msgs, max_tokens=900)
        ans = parse_answer(raw)
        if ans is None and fake is None:
            msgs[1]["content"][0]["text"] += "\n\nYour previous answer was not JSON. Reply with the JSON object only, no prose, no code fence."
            raw, usage = chat(server, model, msgs, max_tokens=900)
            ans = parse_answer(raw)
        reqs.append({"role": "all", "seconds": round(time.time() - t0, 1), "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")})
        raws.append(raw)
    else:
        ans = {"scores": {k: None for k in ROLES}, "findings": [], "one_line": ""}
        parsed_any = False
        for r in ROLES:
            if fake is not None:
                a, raw, info = parse_answer(fake, r), fake, {"role": r, "seconds": 0.0, "prompt_tokens": None, "completion_tokens": None, "fewshot": [], "fewshot_requested": fewshot}
            else:
                a, raw, info = ask(server, model, r, stype, b64, few, fewshot if few else 0)
            reqs.append(info)
            raws.append("[%s] %s" % (r, raw))
            if a is None:
                continue
            parsed_any = True
            ans["scores"][r] = a["scores"][r]
            ans["findings"] += a["findings"]
            ans["one_line"] = ans["one_line"] or a["one_line"]
        ans["findings"].sort(key=lambda f: -f["severity"])
        if not parsed_any:
            ans = None
    rec["seconds"] = round(time.time() - t0, 1)
    rec["requests"] = reqs
    rec["raw"] = "\n".join(raws)[-2400:]
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


def agreement(recs, notes, exclude=()):
    """per shot with a user note: the user's categories vs the model's (findings + one_line); the share that share one.
    exclude= shots left out (the few-shot examples: the model has seen the user's note for them). Also per user category: how many
    marked shots carry it and how many the model hit."""
    rows, hit, n = [], 0, 0
    cat = {}
    for r in recs:
        base = os.path.splitext(os.path.basename(r["path"]))[0]
        if base not in notes or r.get("status") not in ("ok", "fake") or base in exclude:
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
        for c in ucat:
            a = cat.setdefault(c, [0, 0])
            a[0] += 1
            a[1] += 1 if c in mcat else 0
        rows.append({"shot": base, "type": r.get("type"), "user": notes[base], "user_cat": sorted(ucat), "model_cat": sorted(mcat), "shared": sorted(shared)})
    return {"rate": round(hit / n, 2) if n else None, "n": n, "agree": hit, "excluded": sorted(exclude), "rows": rows,
            "by_category": {c: {"user_marks": a[0], "model_hits": a[1]} for c, a in sorted(cat.items())}}


def _f(x):
    return "-" if x is None else "%.2f" % x


def write_outputs(recs, out_dir, server, model, marks=False, against=None, title="", exclude=()):
    os.makedirs(out_dir, exist_ok=True)
    M = mean_scores(recs)
    top = merge_findings(recs)
    agr = agreement(recs, load_user_notes(against), exclude) if against else None
    secs = [r["seconds"] for r in recs if r.get("seconds")]
    J = {"when": time.strftime("%Y-%m-%d %H:%M"), "server": server, "model": model, "title": title, "shots": recs,
         "mean": M, "top": top, "agreement": agr, "seconds_per_shot": round(sum(secs) / len(secs), 1) if secs else None}
    json.dump(J, open(os.path.join(out_dir, "vision_review.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    L = ["# Vision review %s" % title, "", "%s shots, model %s on %s, %s%s" % (
        len(recs), model, server, J["when"], (", %.1f s per shot" % J["seconds_per_shot"]) if J["seconds_per_shot"] else ""), ""]
    if all(r.get("status") == "dry" for r in recs):
        L += ["DRY RUN: the prompts are in vision_prompts\\ (no model call).", ""]
    L += ["## Mean scores", "", "| director | artist | level | marks | mean |", "|---|---|---|---|---|",
          "| %s |" % " | ".join(_f(M[k]) for k in ROLES + ("mean",)), ""]
    types = {}
    for r in recs:
        types[r.get("type", "-")] = types.get(r.get("type", "-"), 0) + 1
    L += ["Shot types: " + ", ".join("%s %d" % kv for kv in sorted(types.items())), ""]
    if top:
        L += ["## Top findings (merged over the shots, by severity)", "", "| sev | rule | finding | where | shots |", "|---|---|---|---|---|"]
        L += ["| %.2f | %s | %s | %s | %s |" % (a["severity"], a["rule"], a["what"].replace("|", "/"), a["where"], ", ".join(a["shots"][:4]) + (" +%d" % (len(a["shots"]) - 4) if len(a["shots"]) > 4 else "")) for a in top]
        L.append("")
    if agr:
        L += ["## Against the user's marks (%s)" % os.path.basename(against), "",
              "agreement %s on %d marked shots (the model's findings share a category with the user's note%s)" % (
                  "-" if agr["rate"] is None else "%.0f %%" % (100 * agr["rate"]), agr["n"],
                  "; %d few-shot example shots left out" % len(agr["excluded"]) if agr["excluded"] else ""), "",
              "| category | user marks | model hits |", "|---|---|---|"]
        L += ["| %s | %d | %d |" % (c, v["user_marks"], v["model_hits"]) for c, v in agr["by_category"].items()]
        L += ["", "| shot | type | user said | user categories | model categories | shared |", "|---|---|---|---|---|---|"]
        L += ["| %s | %s | %s | %s | %s | %s |" % (r["shot"], r.get("type") or "-", "; ".join(r["user"])[:120].replace("|", "/"), ", ".join(r["user_cat"]), ", ".join(r["model_cat"]), ", ".join(r["shared"]) or "-") for r in agr["rows"]]
        L.append("")
    L += ["## Per shot", ""]
    for r in recs:
        L += ["### %s" % r["label"], "", "`%s` (%dx%d, %d kB sent), type %s (%s)%s" % (
            r["path"], r["size"][0], r["size"][1], r["jpeg_kb"], r.get("type", "-"), r.get("type_from", "-"),
            (", %.1f s in %d requests" % (r["seconds"], len(r["requests"]))) if r.get("requests") else "")]
        if r.get("status") == "dry":
            L += ["", "dry: prompt written", ""]
            continue
        if r.get("status") == "unparsed":
            L += ["", "UNPARSED answer (see vision_review.json raw)", ""]
            continue
        L += ["", r.get("one_line") or "-", "", "| director | artist | level | marks |", "|---|---|---|---|",
              "| %s |" % " | ".join(_f(r["scores"].get(k)) for k in ROLES), ""]
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
    lines = ["mean %s over %d shots (model %s): %s" % (_f(M.get("mean")), len(J["shots"]), J.get("model"),
             ", ".join("%s %s" % (k, _f(M.get(k))) for k in ROLES))]
    for a in J.get("top") or []:
        lines.append("- %.2f %s: %s (%s)" % (a["severity"], a["rule"], a["what"], ", ".join(a["shots"][:3])))
    return lines


def hook(run_dir, name, server=DEFAULT_SERVER, model="local", max_shots=16, resize=1024, log=print, fewshot=4):
    """town.py's step after the pilot: when a server answers, review the run's pilot shots and return the report.md
    lines; None (with a one-line note) when no server answers or nothing was shot. Never starts a server."""
    if not probe(server):
        log("vision review: no llama-server on %s (start Documents\\Tools\\llm with --mmproj and run py tools/vision_review.py %s); skipped" % (server, run_dir))
        return None
    shots = find_shots([run_dir])[:max_shots]
    if not shots:
        log("vision review: no pilot shots found for %s; skipped" % name)
        return None
    recs = [review_shot(lab, p, server, model, resize, out_dir=run_dir, fewshot=fewshot) for lab, p in shots]
    J = write_outputs(recs, run_dir, server, model, marks=True, title=name)
    return summary_md(J) + ["(vision_review.md, vision_review.json, vision_marks.txt)"]


def main(argv):
    args, o = [], {"server": DEFAULT_SERVER, "model": "local", "max_shots": "0", "resize": "1024", "dry": False, "fake": None,
                   "marks": False, "against": None, "out": None, "type": "auto", "single": False, "fewshot": "4"}
    it = iter(argv)
    for a in it:
        if a in ("--dry", "--marks", "--single"):
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
    nfew = 0 if o["single"] else int(o["fewshot"])
    if nfew:
        ex = [e["shot"] for e in build_fewshot()]
        print("few-shot: %d example shots %s (excluded from the agreement rate)" % (len(ex), ", ".join(ex)), flush=True)
    recs = []
    for i, (lab, p) in enumerate(shots):
        r = review_shot(lab, p, o["server"], o["model"], int(o["resize"]), dry=o["dry"], fake=fake, out_dir=out_dir,
                        stype=o["type"], single=o["single"], fewshot=nfew)
        recs.append(r)
        if r.get("status") in ("ok", "fake"):
            print("%2d/%d %-26s %-8s %5.1fs  %s  %s" % (i + 1, len(shots), lab, r["type"], r["seconds"], " ".join("%s %s" % (k[:3], _f(r["scores"][k])) for k in ROLES), r.get("one_line", "")[:60]), flush=True)
        else:
            print("%2d/%d %-26s %s" % (i + 1, len(shots), lab, r.get("status")), flush=True)
    excl = [e["shot"] for e in build_fewshot()] if nfew else []
    J = write_outputs(recs, out_dir, o["server"], o["model"], marks=o["marks"], against=o["against"], title=os.path.basename(out_dir), exclude=excl)
    print("\n".join(summary_md(J)))
    if J.get("agreement"):
        a = J["agreement"]
        print("agreement with the user's marks: %s (%d of %d marked shots)" % ("-" if a["rate"] is None else "%.0f %%" % (100 * a["rate"]), a["agree"], a["n"]))
    print("->", os.path.join(out_dir, "vision_review.md"))


if __name__ == "__main__":
    main(sys.argv[1:])
