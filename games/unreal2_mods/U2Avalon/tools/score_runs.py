r"""Score existing run folders with the co-directors, CPU only (no editor, no game): a before/after check for
changes to codirect.py / compose.py / systems.py.

    py tools/score_runs.py [TutA_Cine8 TutA_Town7 ...] [out=scores.json] [systems=1] [tmp=<dir>] [root=<towns dir>]

For each run folder under Documents\U2_research\towns it reviews isl_layout.json on the natural heightmap
(isl_e.bmp) and on the graded one (isl_ec.bmp). systems=1 first re-runs systems.py on a COPY of the layout
(in tmp=, default the run folder's _rescore\ subfolder), so the run's own files are never rewritten.
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import codirect  # noqa
import systems  # noqa

TOWNS = r"C:\Users\john\Documents\U2_research\towns"


def one(run, resys=False, tmp=None, towns=None):
    d = os.path.join(towns or TOWNS, run)
    lay = os.path.join(d, "isl_layout.json")
    if resys:
        tmp = tmp or os.path.join(d, "_rescore")
        os.makedirs(tmp, exist_ok=True)
        cp = os.path.join(tmp, run + "_layout.json")
        shutil.copy(lay, cp)
        systems.run(cp, report=False)
        lay = cp
    out = {}
    for tag, bmp in (("natural", "isl_e.bmp"), ("graded", "isl_ec.bmp")):
        hm = os.path.join(d, bmp)
        if not os.path.exists(hm):
            continue
        R = codirect.review(hm, lay)
        out[tag] = {"total": R["total"], "vetoes": R["vetoes"],
                    **{k: R[k]["score"] for k in ("writer", "director", "engineer", "level", "artist")},
                    "marks": R.get("marks", {}).get("score"), "marks_checks": R.get("marks", {}).get("checks"),
                    "engineer_checks": R["engineer"].get("checks"), "level_checks": R["level"].get("checks"),
                    "notes": {k: R[k]["notes"] for k in ("writer", "director", "engineer")}}
    if resys:
        L = json.load(open(lay))
        out["systems"] = {"score": L["systems"]["score"], "unmet": L["systems"]["unmet"]}
    return out


if __name__ == "__main__":
    runs = [a for a in sys.argv[1:] if "=" not in a] or ["TutA_Cine8", "TutA_Town7", "TutA_Town6"]
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    towns = o.get("root", TOWNS)
    res = {r: one(r, o.get("systems") == "1", o.get("tmp"), towns) for r in runs if os.path.isdir(os.path.join(towns, r))}
    for r, v in res.items():
        for tag in ("natural", "graded"):
            if tag in v:
                x = v[tag]
                print("%-11s %-8s total %.3f  W %.2f D %.2f E %.2f L %.2f A %.2f  marks %s  %s" % (
                    r, tag, x["total"], x["writer"], x["director"], x["engineer"], x["level"], x["artist"], x["marks"],
                    ("VETO " + "; ".join(x["vetoes"])) if x["vetoes"] else ""))
                print("    M:", x["marks_checks"])
                print("    E:", x["engineer_checks"])
                print("    L:", x["level_checks"])
        if "systems" in v:
            print("    systems %.2f unmet %s" % (v["systems"]["score"], v["systems"]["unmet"]))
    if o.get("out"):
        json.dump(res, open(o["out"], "w"), indent=1)
