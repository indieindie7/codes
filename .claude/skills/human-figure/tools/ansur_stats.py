r"""Body proportions from ANSUR II (the 2012 US Army anthropometric survey, public release): percentiles of the
measures a figure needs, as millimetres, as fractions of stature and in head heights, plus allometry (how each
measure scales with stature) and a few ratios.

    python3 -I tools/ansur_stats.py "<dir with ANSUR II MALE Public.csv and ANSUR II FEMALE Public.csv>" out.json

Units in the files: millimetres, except weightkg (tenths of a kilogram: 855 = 85.5 kg) and Age (years).
Head height (chin to crown) is not a direct ANSUR measure. It is derived here as
    (sittingheight - eyeheightsitting)  [eye to crown]  +  mentonsellionlength  [chin to the nose bridge]
which counts the small eye-to-nose-bridge gap twice (a few mm) and lands near published head heights.
"""
import csv, json, math, os, sys

LENGTHS = ["stature", "eyeheight", "cervicaleheight", "acromialheight", "suprasternaleheight", "chestheight",
           "waistheightomphalion", "iliocristaleheight", "trochanterionheight", "crotchheight", "kneeheightmidpatella",
           "lateralfemoralepicondyleheight", "lateralmalleolusheight", "wristheight", "span", "acromionradialelength",
           "radialestylionlength", "handlength", "footlength", "shoulderelbowlength", "forearmhandlength", "sittingheight",
           "biacromialbreadth", "bideltoidbreadth", "chestbreadth", "chestdepth", "waistbreadth", "waistdepth",
           "hipbreadth", "buttockdepth", "headbreadth", "headlength", "headheight", "bizygomaticbreadth",
           "neckcircumference", "chestcircumference", "waistcircumference", "buttockcircumference",
           "thighcircumference", "calfcircumference", "bicepscircumferenceflexed", "wristcircumference", "handbreadth"]
RATIOS = {
    "heads_tall": lambda r: r["stature"] / r["headheight"],
    "leg_ratio": lambda r: r["crotchheight"] / r["stature"],              # inseam / stature
    "sitting_ratio": lambda r: r["sittingheight"] / r["stature"],
    "span_ratio": lambda r: r["span"] / r["stature"],
    "waist_hip_circ": lambda r: r["waistcircumference"] / r["buttockcircumference"],
    "shoulder_hip_breadth": lambda r: r["bideltoidbreadth"] / r["hipbreadth"],
    "biacromial_hip": lambda r: r["biacromialbreadth"] / r["hipbreadth"],
    "shoulders_in_heads": lambda r: r["bideltoidbreadth"] / r["headheight"],
    "hips_in_heads": lambda r: r["hipbreadth"] / r["headheight"],
    "bmi": lambda r: r["mass_kg"] / (r["stature"] / 1000) ** 2,
    "mass_kg": lambda r: r["mass_kg"],
    "age": lambda r: r["age"],
}
P = [5, 10, 25, 50, 75, 90, 95]


def load(path):
    out = []
    for row in csv.DictReader(open(path, encoding="latin-1")):
        r = {k: float(v) for k, v in row.items() if k and k[0].islower() and k != "subjectid" and v not in ("",)}
        r["mass_kg"] = r.pop("weightkg") / 10.0
        r["age"] = float(row["Age"])
        r["eyeheight"] = r["stature"] - (r["sittingheight"] - r["eyeheightsitting"])
        r["headheight"] = (r["sittingheight"] - r["eyeheightsitting"]) + r["mentonsellionlength"]
        out.append(r)
    return out


def pct(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p / 100
    a, b = int(math.floor(k)), int(math.ceil(k))
    return v[a] + (v[b] - v[a]) * (k - a)


def slope(xs, ys):
    """log-log regression slope: 1 = grows in proportion with stature, < 1 = relatively smaller in tall people"""
    lx, ly = [math.log(x) for x in xs], [math.log(y) for y in ys]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    sxx = sum((a - mx) ** 2 for a in lx)
    sxy = sum((a - mx) * (b - my) for a, b in zip(lx, ly))
    return sxy / sxx


def corr(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs)); sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (sx * sy)


def summary(rows):
    S = {"n": len(rows), "mm": {}, "of_stature": {}, "heads": {}, "allometry": {}, "corr_stature": {}, "ratios": {}}
    st = [r["stature"] for r in rows]
    for k in LENGTHS:
        v = [r[k] for r in rows]
        S["mm"][k] = {"p%d" % p: round(pct(v, p), 1) for p in P}
        S["of_stature"][k] = round(pct([r[k] / r["stature"] for r in rows], 50), 4)
        S["heads"][k] = round(pct([r[k] / r["headheight"] for r in rows], 50), 2)
        if k != "stature":
            S["allometry"][k] = round(slope(st, v), 2)
            S["corr_stature"][k] = round(corr(st, v), 2)
    for k, f in RATIOS.items():
        v = [f(r) for r in rows]
        S["ratios"][k] = {"p%d" % p: round(pct(v, p), 3) for p in P}
    return S


if __name__ == "__main__":
    d, out = sys.argv[1], sys.argv[2]
    R = {"_source": "ANSUR II public release (2012 US Army anthropometric survey; Gordon et al. 2014, NATICK/TR-15/007); "
                    "cleared for unlimited public release. Statistics only, no individual records.",
         "male": summary(load(os.path.join(d, "ANSUR II MALE Public.csv"))),
         "female": summary(load(os.path.join(d, "ANSUR II FEMALE Public.csv")))}
    json.dump(R, open(out, "w"), indent=1)
    for sex in ("male", "female"):
        S = R[sex]
        print(sex, S["n"], "stature p50", S["mm"]["stature"]["p50"], "head", S["mm"]["headheight"]["p50"],
              "heads", S["ratios"]["heads_tall"]["p50"], "leg", S["ratios"]["leg_ratio"]["p50"],
              "WHR", S["ratios"]["waist_hip_circ"]["p50"], "SHR", S["ratios"]["shoulder_hip_breadth"]["p50"],
              "bmi", S["ratios"]["bmi"]["p50"], "age", S["ratios"]["age"]["p5"], S["ratios"]["age"]["p95"])
