r"""Facades by a shape grammar (Mueller, Wonka et al., "Procedural Modeling of Buildings", SIGGRAPH 2006; Wonka et al.,
"Instant Architecture", 2003): the building's mass is split into its sides, each side into floors, each floor into
bays, and each bay becomes one element, chosen by rules that look at its context. rooms.py runs it on the plans
floorplan.py makes (houses, offices, the small buildings); shells.py builds plan["facade"] when it is there.

    py tools/facade.py [only=directors_house,plant_office] [png=data\facades]     (elevation drawings, all four sides)

The rules, in order (the first that matches wins):
  Building -> Side(front) Side(back) Side(left) Side(right) Cornice
  Side     -> Floor(0) .. Floor(n-1) Attic                    one floor per 3.4 m storey, the rest of H as a band
  Floor    -> Bay*                                            split around the shell doors: a door takes its own bay,
                                                              the spans between are cut into bays near the building's
                                                              MODULE (formal 3.6 m, informal 3.0 m, offices 3.0 m)
  Bay      -> Door(kind)          a shell door in this bay (floor 0), with its frame by owner and a canopy over a
                                  front door (houses, offices, the clinic, the bar, the store)
           -> Shop                floor 0, the street side of a bar or a store: wide glazing on a low sill
                                  (a bay of 1.4 m or more; the slivers beside a roller door stay blank)
           -> Window(room)        the room behind the bay (from the floor plan) decides:
                                    living, lounge, waiting, guard, bedroom, study, treatment -> tall
                                    a room 2+ bays wide, offices, meeting rooms               -> pair (wider)
                                    kitchen                                                   -> strip (high sill,
                                                                                                 over the counters)
                                    bathroom, WCs, lockers                                    -> small (high)
                                    stair                                                     -> stair (tall strip)
                                    storage, store, corridor end, passage                     -> blank
           -> Boarded             wear: a window boarded up with a chance (wear - 0.3) x 0.8
           -> Blank               no room behind, or a bay too narrow for a window (< 2.8 m)
  then     Symmetry               formal buildings (the director's and guest houses, the office, the clinic): the front's
                                  windows mirrored around its centre where both rooms allow it
  Cornice  -> a projecting band along the roof line (formal buildings); informal ones keep the bare parapet

Elements are kit parts on the 4 m panel module (kit_parts.py), scaled along the wall to the bay (DrawScale3D X;
bays of 2.8 m or more keep the openings near their proportions, narrower ones get a blank or a narrow shop pane).
Door panels keep their width and are Z-scaled down only when the wall is lower than the door (a roller in a 4 m
wall). Output, per element: side, level, t (offset along the
side as shells.SIDES measures it), w (bay width), z (bottom), sz (height / 3.4), part, and what decided it.
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOREY = 3.4
PANEL = 4.0
FORMAL = {"directors_house", "guest_house", "plant_office", "clinic"}
INFORMAL = {"shanty_a", "shanty_b", "shanty_c", "staff_houses", "tin_bar", "checkpoint"}
CANOPY_KINDS = {"house", "office", "hall"}
DOOR_W = {"personnel": 4.0, "main": 4.0, "roller": 6.0, "airlock": 4.0}
DOOR_PART = {"personnel": "B_k_wall_door", "main": "B_k_wall_main", "roller": "B_k_wall_roller", "airlock": "B_k_wall_door"}
WINDOW = {"living": "B_k_win_tall", "lounge": "B_k_win_tall", "waiting": "B_k_win_tall", "guard": "B_k_win_tall",
          "bedroom": "B_k_win_tall", "study": "B_k_win_tall", "treatment": "B_k_win_tall", "shack": "B_k_win_tall",
          "sleeping": "B_k_win_small", "reception": "B_k_win_pair", "office": "B_k_win_pair", "meeting": "B_k_win_pair",
          "bar": "B_k_win_tall", "shop": "B_k_win_tall", "kitchen": "B_k_wall_win", "bathroom": "B_k_win_small",
          "wc_block": "B_k_win_small", "lockers": "B_k_win_small", "stair": "B_k_win_stair"}
BLANK = "B_k_wall"
SIDES = ("front", "back", "left", "right")


def side_len(side, W, D):
    return W if side in ("front", "back") else D


def t_of_door(d):
    """shells.SIDES' along-of(door): front x, back -x, left -y, right y"""
    return {"front": d["x"], "back": -d["x"], "left": -d["y"], "right": d["y"]}[d["side"]]


def point(side, t, W, D):
    """the shell-local (x, y) of offset t along a side"""
    return {"front": (t, -D / 2), "back": (-t, D / 2), "left": (-W / 2, -t), "right": (W / 2, t)}[side]


def room_behind(rooms, side, t, level, W, D):
    x, y = point(side, t, W, D)
    best = None
    for r in rooms:
        if r.get("level", 0) != level or r.get("kind") == "counter" or r.get("cover"):
            continue
        x0, x1, y0, y1 = r["x"] - r["w"] / 2, r["x"] + r["w"] / 2, r["y"] - r["d"] / 2, r["y"] + r["d"] / 2
        touch = {"front": abs(y0 + D / 2) < 0.05, "back": abs(y1 - D / 2) < 0.05,
                 "left": abs(x0 + W / 2) < 0.05, "right": abs(x1 - W / 2) < 0.05}[side]
        inside = (x0 - 1e-6 <= x <= x1 + 1e-6) if side in ("front", "back") else (y0 - 1e-6 <= y <= y1 + 1e-6)
        if touch and inside:
            best = r
    return best


def split(lo, hi, module):
    """bays near the module between lo and hi (offsets along a side)"""
    L = hi - lo
    if L < 0.3:
        return []
    n = max(1, int(round(L / module)))
    while n > 1 and L / n < 2.8:
        n -= 1
    return [(lo + (k + 0.5) * L / n, L / n) for k in range(n)]


def bays(L, doors, module):
    """[(t, w, door)] along a side of length L: each door its own bay, the spans between cut near the module"""
    out, a = [], -L / 2
    for d in sorted(doors, key=t_of_door):
        dw = min(DOOR_W.get(d["kind"], 4.0), L)
        t = max(-L / 2 + dw / 2, min(L / 2 - dw / 2, t_of_door(d)))
        lo = t - dw / 2
        out += [(c, w, None) for c, w in split(a, lo, module)]
        out.append((t, dw, d))
        a = t + dw / 2
    out += [(c, w, None) for c, w in split(a, L / 2, module)]
    return out


def facade(bid, plan, sheet, seed=1):
    rng = random.Random("%s:facade:%s" % (bid, seed))
    W, D, H = plan["shell_m"]
    levels = plan.get("levels", 1)
    rooms = plan.get("rooms", [])
    wear = float(sheet.get("wear") or 0)
    formal = bid in FORMAL
    module = 3.0 if (bid in INFORMAL or sheet.get("kind") == "office") else 3.6
    shopfront = bid in ("tin_bar", "company_store")
    E, why = [], {}
    for side in SIDES:
        L = side_len(side, W, D)
        sdoors = [d for d in plan.get("doors", []) if d["side"] == side and d.get("z", 0) == 0]
        for lv in range(levels):
            z = lv * STOREY
            h = STOREY if levels > 1 or H >= STOREY else H
            row = []
            for t, w, d in bays(L, sdoors if lv == 0 else [], module):
                r = room_behind(rooms, side, t, lv, W, D)
                kind = (r or {}).get("kind")
                if d is not None:
                    part, rule = DOOR_PART.get(d["kind"], "B_k_wall_door"), "door"
                elif shopfront and lv == 0 and side == "front" and kind in ("bar", "shop") and w >= 1.4:
                    part, rule = "B_k_win_shop", "shop"
                elif w < 2.8 or kind is None:
                    part, rule = BLANK, "blank (narrow)" if w < 2.8 else "blank (no room)"
                elif kind in WINDOW:
                    part = WINDOW[kind]
                    big = r and (r["w"] if side in ("front", "back") else r["d"]) >= 2 * module and kind in ("living", "lounge", "reception")
                    if big:
                        part = "B_k_win_pair"
                    rule = "window(%s)" % kind
                else:
                    part, rule = BLANK, "blank (%s)" % kind
                if part.startswith("B_k_win") and part != "B_k_win_shop" and wear > 0.3 and rng.random() < (wear - 0.3) * 0.8:
                    part, rule = "B_k_win_boarded", rule + " -> boarded (wear %.1f)" % wear
                row.append({"side": side, "level": lv, "t": round(t, 3), "w": round(w, 3), "z": round(z, 3), "sz": round(h / STOREY, 4),
                            "part": part, "room": (r or {}).get("id"), "rule": rule})
            if formal and side == "front":
                n = len(row)
                for i in range(n // 2):
                    a, b = row[i], row[n - 1 - i]
                    win = lambda e: e["part"].startswith("B_k_win") and e["part"] not in ("B_k_win_boarded",)
                    if win(a) != win(b) and "door" not in (a["rule"], b["rule"]):
                        src, dst = (a, b) if win(a) else (b, a)
                        okroom = next((r for r in rooms if r["id"] == dst["room"]), None)
                        if okroom and okroom.get("kind") in WINDOW and okroom.get("kind") not in ("bathroom", "wc_block", "lockers"):
                            dst["part"], dst["rule"] = src["part"], dst["rule"] + " -> symmetry"
            E += row
        # the band above the top storey up to the roof, blank, per bay of the top floor
        top = levels * STOREY if (levels > 1 or H >= STOREY) else H
        if H - top > 0.05:
            for e in [e for e in E if e["side"] == side and e["level"] == levels - 1]:
                E.append(dict(e, level=levels, z=round(top, 3), sz=round((H - top) / STOREY, 4), part=BLANK, rule="attic band", room=None))
    extras = []
    for d in plan.get("doors", []):
        if d["side"] == "front" and d.get("kind") == "personnel" and sheet.get("kind") in CANOPY_KINDS and bid not in INFORMAL - {"tin_bar"}:
            extras.append({"side": "front", "t": round(t_of_door(d), 3), "z": 0.0, "part": "B_k_canopy", "sx": 1.0, "rule": "canopy over the front door"})
    if formal:
        for side in SIDES:
            L = side_len(side, W, D)
            n = max(1, int(math.ceil(L / PANEL - 1e-6)))
            for k in range(n):
                extras.append({"side": side, "t": round(-L / 2 + (k + 0.5) * L / n, 3), "z": round(H, 3), "part": "B_k_cornice",
                               "sx": round(L / n / PANEL, 4), "rule": "cornice"})
    return {"elements": E, "extras": extras, "module": module, "formal": formal, "wear": wear}


# ---- elevation drawings -------------------------------------------------------------------------------------
OPEN = {"B_k_win_tall": (1.6, 0.9, 2.7), "B_k_win_pair": (2.8, 0.9, 2.7), "B_k_win_small": (0.8, 2.0, 2.6),
        "B_k_win_shop": (3.2, 0.5, 2.8), "B_k_win_stair": (0.9, 0.4, 3.0), "B_k_wall_win": (3.2, 2.0, 2.9),
        "B_k_win_boarded": (1.6, 0.9, 2.7), "B_k_wall_door": (2.0, 0.0, 2.8), "B_k_wall_main": (2.56, 0.0, 3.84),
        "B_k_wall_roller": (5.0, 0.0, 5.0)}


DOOR_H = {"B_k_wall_door": STOREY, "B_k_wall_main": 4.4, "B_k_wall_roller": 6.0}     # the door panels' heights,
DOOR_W_OF = {"B_k_wall_door": 4.0, "B_k_wall_main": 4.0, "B_k_wall_roller": 6.0}    # widths (shells.DOOR_PART)


def elevation(bid, plan, F, path, s=26):
    from PIL import Image, ImageDraw
    W, D, H = plan["shell_m"]
    pad = 30
    widths = [side_len(sd, W, D) for sd in SIDES]
    img = Image.new("RGB", (int(sum(widths) * s + pad * (len(SIDES) + 1)), int((H + 2.2) * s + 70)), (250, 250, 247))
    dr = ImageDraw.Draw(img)
    ox = pad
    for side, L in zip(SIDES, widths):
        base = 50 + (H + 1.2) * s
        X = lambda t: ox + (t + L / 2) * s
        Z = lambda z: base - z * s
        dr.rectangle([X(-L / 2), Z(H), X(L / 2), Z(0)], fill=(120, 118, 115))
        dr.rectangle([X(-L / 2), Z(0), X(L / 2), Z(-1.2)], fill=(70, 70, 70))                  # the plinth
        for e in F["elements"]:
            if e["side"] != side:
                continue
            x0, x1 = X(e["t"] - e["w"] / 2), X(e["t"] + e["w"] / 2)
            dr.line([x0, Z(e["z"]), x0, Z(e["z"] + e["sz"] * STOREY)], fill=(95, 93, 90), width=1)
            o = OPEN.get(e["part"])
            if not o:
                continue
            door = e["part"] in DOOR_H
            sx = min(1.0, e["w"] / DOOR_W_OF[e["part"]]) if door else e["w"] / PANEL       # as shells.facade_side
            sz = min(1.0, e["sz"] * STOREY / DOOR_H[e["part"]]) if door else e["sz"]
            ow = o[0] * sx
            o = (o[0], o[1] * sz, o[2] * sz)
            fill = (40, 60, 85) if "door" not in e["part"] and "roller" not in e["part"] else (35, 30, 28)
            if e["part"] == "B_k_win_boarded":
                fill = (130, 90, 55)
            if e["part"] == "B_k_win_shop":
                fill = (60, 80, 100)
            dr.rectangle([X(e["t"] - ow / 2), Z(e["z"] + min(o[2], e["sz"] * STOREY)), X(e["t"] + ow / 2), Z(e["z"] + o[1])], fill=fill,
                         outline=(225, 220, 205) if "door" not in e["part"] else (200, 120, 40), width=2)
            if e["part"] in ("B_k_win_tall", "B_k_win_pair", "B_k_win_shop"):
                n = {"B_k_win_tall": 1, "B_k_win_pair": 2, "B_k_win_shop": 2}[e["part"]]
                for k in range(1, n + 1):
                    xm = X(e["t"] - ow / 2 + k * ow / (n + 1))
                    dr.line([xm, Z(e["z"] + o[2]), xm, Z(e["z"] + o[1])], fill=(225, 220, 205), width=1)
        for x in F["extras"]:
            if x["side"] != side:
                continue
            if x["part"] == "B_k_cornice":
                w = PANEL * x["sx"]
                dr.rectangle([X(x["t"] - w / 2), Z(H + 0.3), X(x["t"] + w / 2), Z(H)], fill=(185, 185, 180))
            elif x["part"] == "B_k_canopy":
                dr.rectangle([X(x["t"] - 1.5), Z(3.12), X(x["t"] + 1.5), Z(2.98)], fill=(160, 160, 165))
        dr.rectangle([X(-L / 2), Z(H + 0.7), X(L / 2), Z(H)], outline=(90, 90, 90))            # the parapet
        dr.text((X(-L / 2), 30), "%s (%.0f m)" % (side, L), fill=(20, 20, 20))
        ox += L * s + pad
    dr.text((pad, 8), "%s  facade: %s, module %.1f m, wear %.1f" % (bid, "formal" if F["formal"] else "informal", F["module"], F["wear"]),
            fill=(20, 20, 20))
    img.save(path)
    return img


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import binder, rooms, floorplan  # noqa
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    only = o["only"].split(",") if o.get("only") else floorplan.IDS
    _, sheets = binder.load()
    outdir = o.get("png", os.path.join(HERE, "data", "facades"))
    os.makedirs(outdir, exist_ok=True)
    imgs = []
    for bid in only:
        p = rooms.plan(bid, sheets[bid], {r: s for r, s in binder.load_rooms().items() if s.get("in") == bid})
        if not p or "facade" not in p:
            continue
        F = p["facade"]
        imgs.append(elevation(bid, p, F, os.path.join(outdir, "%s.png" % bid)))
        from collections import Counter
        c = Counter(e["part"] for e in F["elements"])
        print("  %-16s %3d bays: %s; %d extras" % (bid, len(F["elements"]), ", ".join("%s %d" % (k.replace("B_k_", ""), v) for k, v in c.most_common()),
                                                  len(F["extras"])))
    floorplan.contact_sheet(imgs, os.path.join(outdir, "all.png"), cols=2)
    print("%d facades -> %s" % (len(imgs), outdir))
