r"""The writer's mechanical dialogue checks for Sanctuary Open (games/research_notes/Dialogue heuristics/report.md:
mechanical first, the LLM only flags with quotes afterwards, nobody but a human scores voice or delivery).

Reads dialogue_playlist.json (playlist.py) and the OpenDirector section. Checks:
  R15  talk over a fight      a beat's conversations still playing when its encounter's first wave comes out
  R16  bark repetition        expected plays per bark over the level's fights (barks are drawn at random)
  R22  pointing words         here / there / up / this way / behind ... in lines that moved maps
  R23  named things           cameras, doors, lifts, terminals ... the line assumes; the open map has what plan.py says
  R12  greetings / sign-offs  short first or last lines that only open or close
  R26  talk vs travel         talk at a beat longer than the time to the next beat at drive speed (the next beat's
                              talk would queue behind it)
  R3   one voice at a time    (OpenDirector plays one conversation at a time: passes by construction)

    py dialogue_check.py   -> dialogue_check.md + .json (scores 0..1 per check for review_open.py's writer)
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan as S  # noqa

DRIVE = 1200.0      # Manta cruise, UU/s (HoverMutator on Prairie* maps)
FIGHT_S = 35.0      # rough length of one wave's fight
BARK_EVERY = (14 + 24) / 2 / 0.6   # OpenDirector: a try every 14-24 s, 60 % chance
DEIXIS = r"\b(here|there|this way|that way|up here|down here|over here|over there|up there|down there|behind you|ahead|" \
         r"left|right|upstairs|downstairs|next room|this door|that door|through here|in here|out here)\b"
THINGS = {"camera": r"\bcamera", "door": r"\bdoors?\b", "lift": r"\b(lift|elevator)\b", "terminal": r"\b(terminal|console|computer)\b",
          "control room": r"control room", "generator": r"\bgenerator", "drainage": r"\bdrain", "tunnel": r"\btunnel",
          "pipe": r"\bpipe", "window": r"\bwindow", "stairs": r"\bstair", "gate": r"\bgate\b", "dropship": r"\bdropship",
          "artifact": r"\bartifact"}
# what the open map has (plan.py places + make_open.py + OpenDirector): cameras are NOT built; doors only as shed doors
PRESENT = {"generator": "power", "drainage": "basin", "gate": "plant", "dropship": "lz/pad", "artifact": "shaft"}
SIGN = r"^(hi|hello|hey|ok|okay|roger|copy|got it|bye|later|out|over and out|understood|right|yes|yeah|no|thanks)\b"


def main():
    P = json.load(open(os.path.join(HERE, "dialogue_playlist.json")))
    beats, barks = P["beats"], P["barks"]
    flags, sc = [], {}
    if "Cams=(" in open(os.path.join(HERE, "..", "System", "U2Sanctuary.ini"), encoding="latin1").read():
        PRESENT["camera"] = "Miller's cameras (OpenDirector Cams)"
    if "BreakerBox" in open(os.path.join(HERE, "..", "System", "U2Sanctuary.ini"), encoding="latin1").read():
        PRESENT["control room"] = "the breaker box + screen at the shaft top (OpenDirector Props)"
    # R15 talk over a fight
    # OpenDirector now holds a beat's waves until its talk is done, and holds story while enemies live: no story under
    # fire by construction - the cost moves to the wait: a fight held back > 30 s by talk is a stall (pacing rule 1)
    src = open(os.path.join(HERE, "..", "Source", "U2Sanctuary", "Classes", "OpenDirector.uc"), encoding="latin1").read()
    waits = "function bool Talking(" in src
    over = []
    for b in beats:
        if b["fight_starts_after_s"] is not None and b["talk_secs"] > b["fight_starts_after_s"] + 1:
            if not waits:
                over.append(b)
                flags.append(("R15", b["beat"], "%.0f s of talk, the first wave is out at %.0f s: %.0f s of story under fire" % (
                    b["talk_secs"], b["fight_starts_after_s"], b["talk_secs"] - b["fight_starts_after_s"])))
            elif b["talk_secs"] > 30:
                over.append(b)
                flags.append(("R15", b["beat"], "the fight waits for %.0f s of talk (talk-then-fight): a stall - trim or split the conversation" % b["talk_secs"]))
    talky = [b for b in beats if b["talk_secs"] > 0]
    sc["R15 no story under fire" if not waits else "R15 talk then fight, no stall"] = 1 - len(over) / max(1, len(talky))
    # R16 barks
    ini = open(os.path.join(HERE, "..", "System", "U2Sanctuary.ini"), encoding="latin1").read()
    be = re.search(r"BarkEncounters=(.*)", ini)
    be = [e.strip().lower() for e in be.group(1).split(",")] if be and be.group(1).strip() else None
    nwaves = sum(1 for e in re.findall(r'Waves=\(Encounter="(\w+)"', ini) if be is None or e.lower() in be)
    fight_s = nwaves * FIGHT_S
    plays = fight_s / BARK_EVERY / max(1, len(barks))
    story_barks = [k for k in barks if any(len(l["text"].split()) > 6 for l in k["lines"])]
    flags.append(("R16", "barks", "%d barks over ~%.0f s of fighting: each heard ~%.1f times, drawn at random (repeats back to back possible); "
                  "%d of them are story lines, not generic barks: %s" % (len(barks), fight_s, plays, len(story_barks),
                                                                          ", ".join(k["topic"] for k in story_barks))))
    bag = "BarksSaid" in src
    gap = len(barks) * 30 if bag else BARK_EVERY
    if bag:
        flags.append(("R16", "barks", "shuffle bag: no bark again until all %d have played, >= 30 s apart: the same bark >= ~%.0f s apart" % (len(barks), gap)))
    sc["R16 repetition"] = (1.0 if plays <= 1 else max(0.0, 1 - (plays - 1) / 3)) if not bag else min(1.0, gap / 150) * (1.0 if plays <= 2.5 else 0.7)
    sc["R16 repetition"] *= (1 - 0.5 * len(story_barks) / max(1, len(barks)))
    # R22 / R23 / R12 per line
    n_lines = n_deix = n_thing_missing = 0
    for b in beats:
        for c in b["conversations"]:
            ls = c["lines"]
            for i, l in enumerate(ls):
                t = l["text"]
                if not t.strip():
                    continue
                n_lines += 1
                d = re.findall(DEIXIS, t, re.I)
                if d:
                    n_deix += 1
                    flags.append(("R22", "%s/%s" % (b["beat"], l["node"]), 'points ("%s") - check from the open map\'s trigger at %s: "%s"' % (
                        '", "'.join(sorted(set(x.lower() for x in d))), b["place"], t[:140])))
                for k, rx in THINGS.items():
                    if re.search(rx, t, re.I) and k not in PRESENT:
                        n_thing_missing += 1
                        flags.append(("R23", "%s/%s" % (b["beat"], l["node"]), 'names a %s, which the open map does not build: "%s"' % (k, t[:140])))
                if (i == 0 or i == len(ls) - 1) and len(t.split()) < 4 and re.search(SIGN, t.strip(), re.I):
                    flags.append(("R12", "%s/%s" % (b["beat"], l["node"]), 'opens or closes only: "%s"' % t))
    sc["R22 pointing words checked"] = 1 - n_deix / max(1, n_lines)
    sc["R23 named things exist"] = 1 - min(1.0, n_thing_missing / max(1, n_lines) * 3)
    # R26 talk vs travel to the next beat
    places = {q["id"]: q for q in S.PLACES}
    late = 0
    for a, b in zip(beats[:-1], beats[1:]):
        pa, pb = places.get(a["place"]), places.get(b["place"])
        if not pa or not pb or a["talk_secs"] == 0:
            continue
        travel = math.dist((pa["x"], pa["y"]), (pb["x"], pb["y"])) / DRIVE
        if pa is not pb and a["talk_secs"] > travel + (b["radius"] / DRIVE):
            late += 1
            flags.append(("R26", a["beat"], "%.0f s of talk but the next beat (%s) is ~%.0f s away by bike: it queues behind" % (
                a["talk_secs"], b["beat"], travel)))
    sc["R26 talk fits travel"] = 1 - late / max(1, len(talky))
    order = ["R15", "R16", "R22", "R23", "R26", "R12"]
    flags.sort(key=lambda f: order.index(f[0]))
    L = ["# Sanctuary Open - the writer's mechanical dialogue checks", "",
         "From open/dialogue_check.py (rules from games/research_notes/Dialogue heuristics). These are the checkable rules only; "
         "the craft flags (economy, subtext, exchange quality) need quotes and a human, and voice/delivery is a human listening pass.", "",
         "| Check | Score |", "|---|---|"] + ["| %s | %.2f |" % (k, v) for k, v in sc.items()] + ["", "## Flags", ""]
    L += ["- **%s** `%s`: %s" % f for f in flags]
    open(os.path.join(HERE, "dialogue_check.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"scores": sc, "flags": flags}, open(os.path.join(HERE, "dialogue_check.json"), "w"), indent=1)
    print("\n".join("%-28s %.2f" % kv for kv in sc.items()))
    print("%d flags -> dialogue_check.md" % len(flags))


if __name__ == "__main__":
    main()
