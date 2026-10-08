r"""The WRITER and the LEVEL DESIGNER score Sanctuary's enemies (the user, 2026-10-08), per enemy kind per map.

WRITER (the story, STORY.md: the Izarians are the "creatures" that overran the station - Miller's "space monkeys",
blue; the Skaarj stand behind them - "checking up on his Izarian grunts" - and want the artifact; the first Skaarj
is the level's own title in M08A2, "TheSkaarjEncounter"):
  foreshadow   signs before its first appearance on the walk: bodies, blood, sounds and scripted scares (>= 3)
  reveal       its first appearance is staged: a scripted AI (CommandFileName), a triggered spawn (factory or a
               tag an event fires), not just standing there
  voice        the dialogue reacts to it (the map's .dlg lines name it: Izarian/creature/space monkey, Skaarj)
  place        its place in the plot: the grunts come first and in numbers; the masters come later, fewer, and
               near what they want (the generator and the artifact)
LEVEL DESIGNER (arenas.py):
  arenas       the mean score of the fights it is in
  teach        its first fight: small (<= 2 of it) and alone (Unreal 1's first Skaarj)
  roles        it fights beside a different role (a shooter with a rusher or a tank): combined arms
  ai           its AI design score (role, mobility, cover use, a signature move, distinct, fair)

    py enemies.py <dir with M08*.t3d + zones logs> [out.md]
"""
import glob, os, re, sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arenas, mapreview  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
DLG = {"M08A1": "M08A", "M08A2": "M08A", "M08B": "M08B"}
NAMES = {"U2Izarian": r"izarian|creature|space.?monkey|monkey|those things|alien",
         "U2SkaarjLight": r"skaarj", "U2SkaarjMedium": r"skaarj", "U2SkaarjHeavy": r"skaarj"}
SIGN = re.compile(r"scare|noise|growl|creak|laugh|something|howl|mating|scurry|breaking|blood|dead|death|kill|stab|scream|izarian|skaarj", re.I)
ORDER = {"U2Izarian": 0, "U2SkaarjLight": 1, "U2SkaarjMedium": 2, "U2SkaarjHeavy": 3}


def dialogue(m):
    out = []
    for f in glob.glob(os.path.join(GAME, "Dialog", DLG.get(m, m), "*.dlg")):
        out += re.findall(r"^LongText=(.*)$", open(f, encoding="latin1").read(), re.M)
    return out


def score_map(path):
    m = os.path.splitext(os.path.basename(path))[0]
    X = arenas.arenas(path)
    A = mapreview.parse(path)
    Rv = mapreview.review(path)
    R = Rv["_draw"]["route"]
    acc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))])
    tags_fired = {a.get("Event") for a in A if a.get("Event")}

    def along(p):
        d = np.linalg.norm(R - p, axis=1)
        k = int(np.argmin(d))
        return acc[k], d[k]
    signs = []
    for a in A:
        txt = a.get("Tag", "") + " " + a.get("Event", "") + " " + a.get("CommandFileName", "")
        if (mapreview.COLONIST.match(a["cls"]) or (a["cls"] in ("AmbientSound", "AlarmTrigger", "U2Dispatcher", "ParticleSalamander", "Trigger", "Emitter") and SIGN.search(txt))):
            s, d = along(a["p"])
            if d < 1000:
                signs.append(s)
    lines = dialogue(m)
    kinds = sorted({k for f in X["fights"] for k in f["line_up"]}, key=lambda k: ORDER.get(k, 9))
    ai = {a["class"]: a for a in X["ai"]}
    rows = []
    # every enemy of the map (not only the route's fights) for the staging check
    pawns = defaultdict(list)
    for a in A:
        if arenas.ENEMY.match(a["cls"]):
            pawns[a["cls"]].append(a)
        elif a["cls"] == "PawnFactory" and "Prototype" in a:
            pawns[a["Prototype"].split(".")[-1].rstrip("'")].append(a)
    for k in kinds:
        fights = [f for f in X["fights"] if k in f["line_up"]]
        first = fights[0]
        t0 = first["at_s"] * mapreview.SPEED
        W, L, notes = {}, {}, []
        nsign = sum(1 for s in signs if s < t0)
        W["foreshadow"] = min(1.0, nsign / 3)
        # staged: the pawn nearest the first fight's centre is scripted / triggered
        c = np.array(first["centre"])
        near = sorted(pawns[k], key=lambda a: np.linalg.norm(a["p"] - c))[:max(1, first["line_up"][k])]
        staged = [a for a in near if a.get("CommandFileName") or a["cls"] == "PawnFactory" or
                  (a.get("Tag") and a["Tag"] != a["cls"] and a["Tag"] in tags_fired)]
        W["reveal"] = len(staged) / len(near)
        said = [l for l in lines if re.search(NAMES.get(k, k[2:]), l, re.I)]
        W["voice"] = min(1.0, len(said) / 2)
        if said:
            notes.append('voiced: "%s"' % said[0][:70])
        if k == "U2Izarian":
            cnt = sum(f["line_up"].get(k, 0) for f in X["fights"])
            W["place"] = 1.0 if first["fight"] <= 2 and cnt >= 5 else 0.5
        else:
            iz = [f for f in X["fights"] if "U2Izarian" in f["line_up"]]
            later = not iz or iz[0]["at_s"] <= first["at_s"]
            fewer = sum(f["line_up"][k] for f in fights) <= max(3, sum(f["line_up"].get("U2Izarian", 0) for f in X["fights"]))
            W["place"] = (0.5 if later else 0.0) + (0.5 if fewer else 0.0)
        L["arenas"] = float(np.mean([f["score"] for f in fights]))
        fs = X["first_seen"].get(k, {})
        L["teach"] = 1.0 if fs.get("count", 9) <= 2 and fs.get("alone") else (0.5 if fs.get("count", 9) <= 2 else 0.0)
        roles = {ai[o]["role"] for f in fights for o in f["line_up"] if o in ai}
        mixed = [f for f in fights if len({ai[o]["role"] for o in f["line_up"] if o in ai}) > 1]
        L["roles"] = len(mixed) / len(fights)
        L["ai"] = ai[k]["score"] if k in ai else 0.5
        if nsign < 3:
            notes.append("only %d signs before it shows" % nsign)
        if W["reveal"] < 1:
            notes.append("its first appearance is just placed, not staged")
        if L["roles"] == 0:
            notes.append("never fights beside another role")
        rows.append({"map": m, "enemy": k, "fights": len(fights), "count": sum(f["line_up"][k] for f in fights),
                     "first_at_s": first["at_s"], "writer": {a: round(b, 2) for a, b in W.items()},
                     "level": {a: round(b, 2) for a, b in L.items()},
                     "writer_score": round(float(np.mean(list(W.values()))), 2),
                     "level_score": round(float(np.mean(list(L.values()))), 2), "notes": notes})
    return rows


def report(rows):
    L = ["# Sanctuary's enemies: the writer and the level designer", "",
         "| map | enemy | fights | count | first at | WRITER | foreshadow / reveal / voice / place | LEVEL DESIGNER | arenas / teach / roles / ai |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s | %d | %d | %d s | **%.2f** | %s | **%.2f** | %s |" % (
            r["map"], r["enemy"][2:], r["fights"], r["count"], r["first_at_s"], r["writer_score"],
            " / ".join("%.1f" % v for v in r["writer"].values()), r["level_score"], " / ".join("%.1f" % v for v in r["level"].values())))
    L += ["", "## Notes"] + ["- **%s %s**: %s" % (r["map"], r["enemy"][2:], "; ".join(r["notes"])) for r in rows if r["notes"]]
    by = defaultdict(list)
    for r in rows:
        by[r["enemy"]].append(r)
    L += ["", "## Over the three maps", "", "| enemy | WRITER | LEVEL DESIGNER |", "|---|---|---|"]
    for k, rs in sorted(by.items(), key=lambda kv: ORDER.get(kv[0], 9)):
        L.append("| %s | %.2f | %.2f |" % (k[2:], np.mean([r["writer_score"] for r in rs]), np.mean([r["level_score"] for r in rs])))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    src = sys.argv[1]
    rows = []
    for m in ("M08A1", "M08A2", "M08B"):
        rows += score_map(os.path.join(src, m + ".t3d"))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, "sanctuary_enemies.md")
    open(out, "w", encoding="utf-8").write(report(rows))
    print(report(rows))
