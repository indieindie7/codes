r"""Avalon story simulation: the binder's citizens as agents living a few days in the town, with the WRITER evolved
into a drama manager (user 2026-10-09: "lets do the drama manager that makes a safety net on those small agents and
lets have for important characters bigger agents. lets evolve the writer").

    py tools/storysim.py [days=3] [out=<dir>] [small=URL] [big=URL|claude] [dm=claude|URL] [step=60] [only=a,b]
                         [backend=live|dry] [model_dm=opus] [think_big=0|1]

Three tiers (research_notes/Local models for character writing):
  SMALL  the minor citizens and the groups (dock gang, Tin Row families ...): a local model, fast and parallel
         (llama-server on `small`, default http://127.0.0.1:8081/v1, Gemma 4 12B)
  BIG    the characters the story turns on (BIG below: Hawkins, Rook, Oduya, Nkemelu, Okafor, Marau): a bigger,
         reasoning role-play model (llama-server on `big`, default http://127.0.0.1:8082/v1, Pantheon-Reasoning
         26B-A4B), or big=claude (the Claude CLI, `claude -p`)
  DRAMA MANAGER  the writer, once per in-game day, through the Claude CLI (dm=claude, default): reads the day's log
         and is the safety net (see DRAMA_MANAGER below)

Every agent turn is one JSON object (schema TURN): where it is, what it does, a line it says (or ""), who it is with,
and a memory note. The per-turn safety net is deterministic and cheap (check_turn): valid JSON, a known place,
the routine respected unless the agent gives a reason, a short line, no invented named people; a failed turn is asked
once more at a lower temperature and then replaced by the agent's routine (logged as "fallback").

Nothing here touches the game. Output in <out>: log.jsonl (every turn), day_N.md (the day as prose + the drama
manager's review), memories.json, nudges.json, and story.md (the run in one read).
"""
import json, os, random, re, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
DAYS = int(o.get("days", 3))
STEP = int(o.get("step", 60))                    # minutes per tick
OUT = o.get("out", os.path.join(r"C:\Users\john\Documents\U2_research\storysim", time.strftime("%Y%m%d-%H%M%S")))
SMALL = o.get("small", "http://127.0.0.1:8081/v1")
BIG = o.get("big", "http://127.0.0.1:8082/v1")
DM = o.get("dm", "claude")
DM_MODEL = o.get("model_dm", "opus")
BACKEND = o.get("backend", "live")
BIG_IDS = o.get("bigs", "hawkins,rook,oduya,nkemelu,okafor,marau").split(",")
DAY_START, DAY_END = 6 * 60, 23 * 60

citizens, buildings = binder.load()
if o.get("only"):
    citizens = {k: v for k, v in citizens.items() if k in o["only"].split(",")}
parti = json.load(open(os.path.join(HERE, "binder", "parti.json")))
PLACES = sorted(set(list(buildings) + [r for c in citizens.values() for _, r in c.get("routine", [])]))
NAMES = {c["name"].split()[-1].lower() for c in citizens.values()} | set(citizens)

WORLD = (
    "Avalon: a small company island on a stormy alien sea (the Unreal II universe). Liandri, the mining company, "
    "runs the ore plant and holds the high ground; its stepped tower stands on the summit. The Colonial Authority "
    "(Cmdr. Hawkins, a handful of marines and techs) holds the old tower by the dock and is mostly ignored. The "
    "town lives below in the company's smoke: dorms, the mess, Tin Row and Ship Row shanties (officially 380 "
    "people, really about 470; the shanties are 'not here' on paper), smugglers who use the drain and the dead rig. "
    "Scrip is the money. Rain, wind, sirens at shift change. The story's sentence: " + parti["sentence"])

TURN = {"type": "object", "properties": {
    "place": {"type": "string"}, "doing": {"type": "string"}, "with": {"type": "array", "items": {"type": "string"}},
    "line": {"type": "string"}, "memory": {"type": "string"}, "off_routine_reason": {"type": "string"}},
    "required": ["place", "doing", "with", "line", "memory", "off_routine_reason"]}

DRAMA_MANAGER = """You are the WRITER of the Avalon creative team, evolved into its DRAMA MANAGER.
The town's people are agents who act on their own goals; you never script them. Your job, once per in-game day:

1. SAFETY NET. Read the day's log. Veto turns that break a character (out of voice, against their wants/fears
   without cause), break the world (invented people, places or technology; a group of 30 acting as one person;
   anything the setting can't hold), or contradict an earlier turn. A vetoed turn is erased from every memory
   (a retcon): list its id and a one-line reason.
2. KEEP THE BEATS, NOT A PLOT. The story has must-happen beats with windows (BEATS below). Never force one;
   change CONDITIONS so it happens naturally (a supply drop postponed, a truck late, a lamp seen in the drain, the
   rain, a siren, a rumour put in one mouth). Give at most 3 nudges per day, each a world event at a time and place.
3. GIVE THE QUIET ONES SOMETHING TO DO. The team's blind spot (the cube test, 2026-10-09): our people wait and
   watch and nobody acts. Each day, pick one or two characters who only drifted and give them a private directive
   rooted in their own wants (a want, made urgent) - action, not mood.
4. KEEP MEMORY HONEST. For each character, rewrite their memory to at most 6 short notes of what they know now.
5. NOTICE STORY. Say in 3-6 lines what emerged today that is worth keeping (a relationship, a grudge, a secret,
   a habit) - the material the user's level and dialogue can use.

Character truth first, the beats second, your taste last. Return ONE JSON object:
{"vetoes":[{"id":N,"why":"..."}], "nudges":[{"at":"HHMM","place":"...","event":"..."}],
 "directives":{"<citizen id>":"..."}, "memories":{"<citizen id>":["..."]}, "emerged":["..."],
 "beats":[{"id":"...","status":"done|on track|at risk","note":"..."}], "prose":"the day in 120-200 words"}"""

BEATS = [
    {"id": "catwalk", "by_day": 1, "text": "Hawkins goes out on the tower catwalk at about 19:30 with one cigarette and looks at the company tower until its lights come on, then for the light on the dead rig."},
    {"id": "supply_drop", "by_day": 2, "text": "The Authority supply drop is postponed again (the rifle stays on the requisition list); somebody in the Authority says so out loud."},
    {"id": "census", "by_day": 2, "text": "The gap between the official 380 and the real town shows: someone counts, or is told Tin Row is 'not here'."},
    {"id": "drain_lamp", "by_day": 3, "text": "Rook's people use the drain at night; a lamp is seen there, and something in the drain goes wrong (a man missing, a light that dies)."},
]


def tier(cid):
    return "big" if cid in BIG_IDS else "small"


def hm(t):
    return "%02d%02d" % (t // 60, t % 60)


def routine_place(c, t):
    r = [p for m, p in c.get("routine", []) if m <= t]
    return (r[-1] if r else c.get("lives") or c.get("works") or "town")


def sheet(c):
    path = os.path.join(HERE, "binder", "citizens", c["_file"])
    body = open(path, encoding="utf-8").read()
    prose = body.split("\n\n", 1)[1].strip() if "\n\n" in body else ""
    head = "%s (%s). Employer: %s. Lives: %s. Works: %s.\nWants: %s\nFears: %s" % (
        c["name"], c["role"], c.get("employer"), c.get("lives"), c.get("works"), c.get("wants"), c.get("fears"))
    if c.get("headcount"):
        head += "\nThis is a GROUP of %s people: speak and act as the group (one representative voice), never as one person." % c["headcount"]
    return head + "\n\n" + prose[:1500]


# ---- backends -------------------------------------------------------------------------------------------------
THINK_BIG = o.get("think_big", "0") == "1"      # Pantheon's reasoning: better turns, ~7 tok/s on the CPU, so off by default


def chat(url, messages, temp=0.8, schema=None, max_tokens=500, think=False):
    body = {"model": "local", "messages": messages, "temperature": temp, "max_tokens": max_tokens,
            # both local models think by default and can spend the whole budget on it (an empty answer)
            "chat_template_kwargs": {"enable_thinking": bool(think)}}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "turn", "schema": schema}}
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"]


def claude(prompt, model="sonnet", timeout=900):
    exe = os.path.expanduser(r"~\.local\bin\claude.exe")
    r = subprocess.run([exe, "-p", "--model", model, "--output-format", "text"], input=prompt, capture_output=True,
                       text=True, encoding="utf-8", timeout=timeout)
    if r.returncode:
        raise RuntimeError("claude -p failed: " + (r.stderr or r.stdout)[-400:])
    return r.stdout


def first_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


# ---- one agent turn + the per-turn safety net -------------------------------------------------------------------
def reason_of(d):
    """the off-routine reason, '' when the model wrote a placeholder ('None', 'n/a', 'none; on schedule' ...)"""
    r = str(d.get("off_routine_reason", "") or "").strip()
    return "" if re.match(r"(?i)^(none|n/?a|no|null|-|nothing)", r) else r


def check_turn(cid, c, t, d):
    """problems with a turn (empty list = accepted)"""
    bad = []
    if not isinstance(d, dict):
        return ["no JSON"]
    for k in TURN["required"]:
        if k not in d:
            bad.append("missing " + k)
    place = str(d.get("place", "")).strip().lower()
    if place and place not in PLACES and not any(place.startswith(p) for p in PLACES):
        bad.append("unknown place '%s'" % place)
    if place and place != routine_place(c, t) and not reason_of(d):
        bad.append("left the routine (%s) without a reason" % routine_place(c, t))
    if len(str(d.get("line", "")).split()) > 40:
        bad.append("line too long")
    # capitalised words NOT at the start of a sentence (a sentence-initial "Keep" or "Stoking" is not a name)
    caps = set(re.findall(r"(?<=[a-z,;:] )([A-Z][a-z]{3,})\b", str(d.get("line", "")) + " " + str(d.get("doing", ""))))
    common = {"Liandri", "Authority", "Avalon", "Tin", "Row", "Ship", "Hawkins", "Commander", "Sector", "Colonial",
              "Skaarj", "Izarian", "Company", "Thursday", "Monday", "Tuesday", "Wednesday", "Friday", "Saturday", "Sunday", "The", "They", "There", "This", "That", "When", "What", "Then", "Just", "Some"}
    stray = [w for w in caps if w.lower() not in NAMES and w not in common and w.lower() not in PLACES]
    if len(stray) > 2:
        bad.append("possibly invented names: %s" % ", ".join(sorted(stray)[:4]))
    return bad


def agent_turn(cid, c, t, day, state):
    here = routine_place(c, t)
    others = [x for x, cc in citizens.items() if x != cid and state["where"].get(x) == here]
    mem = state["memory"].get(cid, [])
    nudges = [n for n in state["nudges"] if n.get("at", "9999") <= hm(t) and not n.get("_seen_%s" % cid)]
    directive = state["directives"].get(cid, "")
    prompt = (
        "%s\n\nYOU ARE: %s\n\nDay %d, %s. Your routine puts you at: %s. Also there: %s.\n"
        "What you remember: %s\nWhat is happening in town today: %s\n%s\n"
        "Places on the island: %s.\n\n"
        "Decide what you do this hour, in character, from your own wants and fears. You may leave your routine if you "
        "have a reason (then say it). Keep 'line' to one short spoken line or \"\"; 'memory' is one short note worth "
        "keeping. Answer with one JSON object with keys place, doing, with, line, memory, off_routine_reason."
        % (WORLD, sheet(c), day, hm(t), here, ", ".join(citizens[x]["name"] for x in others) or "nobody you know",
           "; ".join(mem) or "nothing yet", "; ".join(n["event"] + " (" + n.get("place", "") + ")" for n in nudges) or "nothing unusual",
           ("A private urge today: " + directive) if directive else "", ", ".join(PLACES)))
    if BACKEND == "dry":
        return {"place": here, "doing": "follows the routine", "with": others[:2], "line": "", "memory": "",
                "off_routine_reason": ""}, "dry", []
    url = BIG if tier(cid) == "big" else SMALL
    tries = []
    for temp in (0.8, 0.4):
        try:
            if url == "claude":
                d = first_json(claude(prompt, "sonnet"))
            else:
                d = first_json(chat(url, [{"role": "user", "content": prompt}], temp, TURN,
                                    (1200 if THINK_BIG else 400) if tier(cid) == "big" else 300, think=THINK_BIG and tier(cid) == "big"))
        except Exception as e:
            d, tries = None, tries + ["error: %s" % e]
        bad = check_turn(cid, c, t, d)
        if not bad:
            return d, tier(cid), tries
        tries.append("; ".join(bad))
    return {"place": here, "doing": "keeps to the routine", "with": [], "line": "", "memory": "",
            "off_routine_reason": ""}, "fallback", tries


# ---- the drama manager ----------------------------------------------------------------------------------------
def drama_manager(day, events, state):
    log = "\n".join("#%d %s %s @%s: %s%s" % (e["id"], e["time"], citizens[e["who"]]["name"], e["place"], e["doing"],
                                            (' - "%s"' % e["line"]) if e["line"] else "") for e in events)
    cast = "\n".join("- %s: %s (wants %s; fears %s)" % (k, v["name"] + ", " + v["role"], v.get("wants"), v.get("fears"))
                     for k, v in citizens.items())
    prompt = "%s\n\nWORLD: %s\n\nCAST:\n%s\n\nBEATS (must happen, by day):\n%s\n\nCURRENT MEMORIES:\n%s\n\nDAY %d LOG:\n%s\n" % (
        DRAMA_MANAGER, WORLD, cast, json.dumps(BEATS, indent=1), json.dumps(state["memory"], indent=1), day, log)
    if BACKEND == "dry":
        return {"vetoes": [], "nudges": [], "directives": {}, "memories": state["memory"], "emerged": [], "beats": [],
                "prose": "(dry run)"}
    raw = claude(prompt, DM_MODEL) if DM == "claude" else chat(DM, [{"role": "user", "content": prompt}], 0.5, None, 3000)
    return first_json(raw) or {"vetoes": [], "nudges": [], "directives": {}, "memories": state["memory"],
                               "emerged": [], "beats": [], "prose": raw[:1500]}


# ---- the run --------------------------------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    state = {"where": {}, "memory": {}, "nudges": [], "directives": {}}
    logf = open(os.path.join(OUT, "log.jsonl"), "a", encoding="utf-8")
    story = ["# Avalon story simulation (%s)\n\n%d citizens (%d big), %d days, step %d min; small %s, big %s, drama "
             "manager %s/%s\n" % (time.strftime("%Y-%m-%d %H:%M"), len(citizens), sum(tier(c) == "big" for c in citizens),
                                 DAYS, STEP, SMALL, BIG, DM, DM_MODEL)]
    eid = 0
    for day in range(1, DAYS + 1):
        events = []
        for t in range(DAY_START, DAY_END + 1, STEP):
            for cid, c in citizens.items():
                state["where"][cid] = routine_place(c, t)
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = {cid: pool.submit(agent_turn, cid, c, t, day, state) for cid, c in citizens.items()}
            for cid, f in futs.items():
                d, how, tries = f.result()
                eid += 1
                e = {"id": eid, "day": day, "time": hm(t), "who": cid, "tier": how, "place": str(d.get("place", "")),
                     "doing": str(d.get("doing", "")), "line": str(d.get("line", "")), "with": d.get("with", []),
                     "memory": str(d.get("memory", "")), "reason": reason_of(d), "retries": tries}
                events.append(e)
                logf.write(json.dumps(e, ensure_ascii=False) + "\n")
                logf.flush()
                state["where"][cid] = e["place"] or state["where"][cid]
                if e["memory"]:
                    state["memory"].setdefault(cid, []).append("day %d %s: %s" % (day, e["time"], e["memory"]))
                    state["memory"][cid] = state["memory"][cid][-10:]
            print("day %d %s: %d turns (%d fallback)" % (day, hm(t), len(citizens),
                                                          sum(1 for e in events[-len(citizens):] if e["tier"] == "fallback")), flush=True)
        r = drama_manager(day, events, state)
        vetoed = {v.get("id") for v in r.get("vetoes", [])}
        if vetoed:     # the retcon: memories built on a vetoed turn go
            for cid in state["memory"]:
                state["memory"][cid] = [m for m in state["memory"][cid]
                                        if not any(e["id"] in vetoed and e["who"] == cid and e["memory"] and e["memory"] in m for e in events)]
        if r.get("memories"):
            state["memory"].update({k: v for k, v in r["memories"].items() if k in citizens})
        state["nudges"] = [dict(n) for n in r.get("nudges", [])][:3]
        state["directives"] = {k: v for k, v in r.get("directives", {}).items() if k in citizens}
        json.dump(r, open(os.path.join(OUT, "day_%d_review.json" % day), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        kept = [e for e in events if e["id"] not in vetoed and (e["line"] or e["reason"])]
        md = ["## Day %d\n" % day, r.get("prose", ""), "\n### What emerged", *["- " + x for x in r.get("emerged", [])],
              "\n### Beats", *["- %s: %s %s" % (b.get("id"), b.get("status"), b.get("note", "")) for b in r.get("beats", [])],
              "\n### Vetoed (the safety net)", *["- #%s: %s" % (v.get("id"), v.get("why")) for v in r.get("vetoes", [])],
              "\n### Tomorrow: nudges and private urges", *["- %s %s: %s" % (n.get("at"), n.get("place"), n.get("event")) for n in state["nudges"]],
              *["- %s: %s" % (k, v) for k, v in state["directives"].items()],
              "\n### Lines spoken", *['- %s %s (%s): "%s"%s' % (e["time"], citizens[e["who"]]["name"], e["place"], e["line"],
                                                              (" [off routine: %s]" % e["reason"]) if e["reason"] else "") for e in kept if e["line"]]]
        open(os.path.join(OUT, "day_%d.md" % day), "w", encoding="utf-8").write("\n".join(md) + "\n")
        story.append("\n".join(md))
        json.dump(state["memory"], open(os.path.join(OUT, "memories.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("day %d reviewed: %d vetoes, %d nudges, %d directives" % (day, len(vetoed), len(state["nudges"]), len(state["directives"])), flush=True)
    open(os.path.join(OUT, "story.md"), "w", encoding="utf-8").write("\n\n".join(story) + "\n")
    print("story ->", os.path.join(OUT, "story.md"))


if __name__ == "__main__":
    main()
