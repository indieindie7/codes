r"""Interior plans for the shell build: per building, its levels, rooms (sizes in m and UU), doors and stairs, from the
binder's room sheets (binder/rooms/*.md, `in: <building>`) plus a default programme per building id/kind - the
engineer's interior kit (redesign/2026-10-09/engineer.md s. 2) and the level designer's interior layouts (s. 3).

    py tools/rooms.py [<run folder>] [out=<run>\rooms.json] [png=<run>\isl_rooms.png] [only=tower,drain]

Without a run folder it writes the plans for every sheet (to stdout's summary + out=). With one, it adds each
building's world placement from isl_layout.json (and the drain's length from L['drain'], anchors.py).

Player numbers are the MEASURED ones (redesign/2026-10-09/facts_measured.md): collision radius 28 UU, half-height
54 (108 tall), MaxStepHeight 37 (AI 35, so risers <= 35), ladders supported (PHYS_Ladder; a LadderVolume to test).
Local frame per building, metres: origin at the footprint's centre, x along the width (size[0]), y along the depth,
FRONT = -y (build_parts' convention), z up from the ground floor. Checks (E27/LD): headroom >= 120 UU, corridors >= 256 UU
where AI walk two abreast (>= 2 x 28 + margin elsewhere), doors >= 80 x 140 UU (Skaarj routes 128 x 192), 2 exits for
a room over 20 m long or over 50 people, no point over 45 m from an exit.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa
import floorplan  # noqa  (houses, offices and the small buildings: generated from real plans)

M = 50.0
PLAYER_R, PLAYER_HH, STEP = 28, 54, 37            # facts_measured.md
RISER_UU = 35                                     # <= the AI step (35) and the player's 37
TREAD_UU = 28
STOREY_M = 3.4
HEADROOM_UU = 120
DOOR_P = (1.6, 2.8)                               # personnel door, m (80 x 140 UU)
DOOR_R = (5.0, 5.0)                               # roller door for halls
DOOR_SKAARJ = (2.56, 3.84)                        # 128 x 192 UU


def uu(v):
    return round(v * M)


def room(rid, name, x, y, w, d, h, level=0, z=0.0, **kw):
    r = {"id": rid, "name": name, "level": level, "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
         "w": round(w, 2), "d": round(d, 2), "h": round(h, 2), "uu": [uu(w), uu(d), uu(h)]}
    r.update(kw)
    return r


def door(side, kind, x, y, z=0.0, to="outside"):
    w, h = DOOR_R if kind == "roller" else DOOR_P
    return {"side": side, "kind": kind, "x": round(x, 2), "y": round(y, 2), "z": z, "w": w, "h": h, "uu": [uu(w), uu(h)], "to": to}


def stair(x, y, z0, z1, width=1.6):
    rise = (z1 - z0) * M
    n = max(1, math.ceil(rise / RISER_UU))
    return {"kind": "stair", "x": x, "y": y, "z0": z0, "z1": z1, "risers": n, "riser_uu": round(rise / n, 1), "tread_uu": TREAD_UU,
            "width": width, "run_m": round(n * TREAD_UU / M, 2), "landings": max(0, (n - 1) // 12)}


def shell_doors(sheet, W, D):
    out = []
    pos = {"front": (0, -D / 2), "back": (0, D / 2), "left": (-W / 2, 0), "right": (W / 2, 0)}
    for side, kind in (sheet.get("doors") or {}).items():
        if side in pos and kind != "none":
            out.append(door(side, kind, *pos[side]))
    return out


# --- default programmes ----------------------------------------------------------------------------------------
def dorm(sheet, W, D, H):
    """engineer 2.4: a double-loaded 2.4 m corridor, 4.0 x 3.6 rooms (3 bunks), stair bay 4 m left, wash block 4 m right"""
    levels = max(1, int(H // STOREY_M))
    rooms, stairs = [], []
    n_side = max(1, int((W - 8.0) // 4.0))
    for lv in range(levels):
        z = lv * STOREY_M
        rooms.append(room("corridor_%d" % lv, "corridor", 0, 0, W - 8.0, 2.4, STOREY_M - 0.3, lv, z, circulation=True))
        rooms.append(room("stair_%d" % lv, "stair bay", -W / 2 + 2.0, 0, 4.0, D, STOREY_M - 0.3, lv, z, circulation=True))
        rooms.append(room("wash_%d" % lv, "wash block / drying room", W / 2 - 2.0, 0, 4.0, D, STOREY_M - 0.3, lv, z))
        for k in range(n_side):
            for s in (-1, 1):
                x = -W / 2 + 4.0 + 2.0 + k * 4.0
                rooms.append(room("room_%d_%d%s" % (lv, k, "a" if s < 0 else "b"), "bunk room (3)", x, s * (1.2 + 1.8), 4.0, 3.6,
                                  STOREY_M - 0.3, lv, z, beds=3, door_to="corridor_%d" % lv))
        if lv:
            stairs.append(stair(-W / 2 + 2.0, 0, z - STOREY_M, z))
    return levels, rooms, stairs


def mess(sheet, W, D, H):
    """engineer 2.5 / LD I4: dining 2/3, servery counter, kitchen behind, Haldane's bar in a back corner"""
    Wd = W * 2 / 3
    rooms = [room("dining", "dining hall (8 long tables, 12 seats)", -W / 2 + Wd / 2, 0, Wd, D, H - 0.3, seats=96),
             room("servery", "servery counter", -W / 2 + Wd, 0, 0.9, min(10.0, D - 1), 1.1, cover="full"),
             room("kitchen", "kitchen (production, warewash, cold room 3x3, dry store)", W / 2 - (W - Wd) / 2, 0, W - Wd, D, H - 0.3),
             room("bar", "Haldane's bar", -W / 2 + 3.0, D / 2 - 1.5, 6.0, 3.0, H - 0.3)]
    return 1, rooms, []


def hall(sheet, W, D, H):
    """engineer 2.1 / LD I2: floor 0, catwalk L1 (+5.12 m = 256 UU) and L2 (+10.24 = 512 UU), loops round the line"""
    rooms = [room("floor", "process floor (machine rows, 1.5 m aisles)", 0, 0, W, D, H - 0.3, 0, 0.0)]
    stairs = []
    z1, z2 = 256 / M, 512 / M
    if H >= 8:
        rooms.append(room("mezzanine", "operating platform (grating + rail)", 0, -D / 2 + 1.5, W - 6.0, 3.0, H - z1 - 0.3, 1, z1, grating=True, rail=True))
        stairs.append(stair(-W / 2 + 3.0, -D / 2 + 3.0, 0.0, z1, 2.0))
    if H >= 11:
        rooms.append(room("catwalk", "high catwalk (1.6 m, rail) to the gable platform", 0, D / 2 - 0.8, W - 6.0, 1.6, H - z2 - 0.3, 2, z2, grating=True, rail=True))
        stairs.append(stair(W / 2 - 3.0, D / 2 - 3.0, z1, z2, 1.6))
    return 1 + (H >= 8) + (H >= 11), rooms, stairs


def pump(sheet, W, D, H):
    """engineer 2.2: the wet-well grating, a pump row with 1.5 m aisles, the header, a hoist beam"""
    rooms = [room("pump_hall", "pump hall (2 duty + 1 standby, hoist beam)", 0, 0, W, D, H - 0.3),
             room("wet_well", "screen bay over the wet well (grating, water 2 m down)", -W / 2 + 2.0, 0, 4.0, 3.0, H - 0.3, grating=True)]
    return 1, rooms, []


def house(sheet, W, D, H):
    rooms = [room("main", "living room", 0, -D / 4, W, D / 2, min(H, STOREY_M) - 0.3),
             room("back", "bedrooms + kitchen", 0, D / 4, W, D / 2, min(H, STOREY_M) - 0.3)]
    return 1, rooms, []


def authority_tower(sheet, W, D, H):
    """LD I1: the base lobby + freight lift (new), the command room and its deck (TutA's own BSP, as it stands), the
    catwalk; z in m above the tower's ground (the tower: z -3767 -> ~4150 UU, the command room floor ~ +7900 UU)"""
    zc = (4150 - (-3767)) / M                     # ~158 m: the command room
    rooms = [room("lobby", "base lobby (hold: 2 pillars, desk, crates; mezzanine +256)", 0, 0, 1800 / M, 1400 / M, 600 / M, 0, 0.0, combat=True),
             room("lift", "freight lift cage (call 20 s)", 0, 1400 / M / 2 - 512 / M / 2, 512 / M, 512 / M, zc, 0, 0.0, lift=True),
             room("command_room", "the command room (TutA BSP, fixed)", 0, 0, 3700 / M, 1900 / M, 650 / M, 2, zc - 650 / M, existing=True),
             room("catwalk", "the catwalk (grated, rail; the peak frame)", 0, -1900 / M / 2 - 0.8, 3700 / M, 1.6, 4.0, 2, zc - 650 / M, grating=True, rail=True)]
    return 3, rooms, []


def culvert(sheet, W, D, H, drain=None):
    """LD I3: grate, culvert 384 x 320 (ledge 128), junction room 768 x 768, sluice gallery 1536 x 768 x 448, outfall.
    Lengths along the run (x = arclength from the grate, m); from L['drain'] when the layout has one"""
    segs = (drain or {}).get("segments") or [
        {"kind": "culvert", "s0_uu": 0, "s1_uu": 3600, "w": 384, "h": 320, "ledge": 128},
        {"kind": "junction_room", "s_uu": 1800, "w": 768, "l": 768, "h": 448},
        {"kind": "sluice_gallery", "s0_uu": 3600, "s1_uu": 5136, "w": 768, "h": 448}]
    rooms = []
    for k, s in enumerate(segs):
        if s["kind"] in ("culvert", "sluice_gallery") and "s0_uu" in s:
            l = (s["s1_uu"] - s["s0_uu"]) / M
            rooms.append(room("%s_%d" % (s["kind"], k), s["kind"].replace("_", " "), (s["s0_uu"] + s["s1_uu"]) / 2 / M, 0, l, s["w"] / M, s["h"] / M,
                              ledge_uu=s.get("ledge"), underground=True))
        elif s["kind"] == "junction_room":
            rooms.append(room("junction_room", "junction room (shaft light from a grate)", s["s_uu"] / M, 0, s["l"] / M, s["w"] / M, s["h"] / M, underground=True))
    return 1, rooms, []


def liandri(sheet, W, D, H):
    """writer 3.11: the scrip exchange hall, top-lit, a queue rail for a hundred, seen through glass from the gate stair"""
    rooms = [room("exchange_hall", "scrip exchange hall (top-lit, queue rail, shuttered windows)", 0, -D / 4, min(W, 30.0), min(D / 2, 20.0), 8.0,
                  0, 30.0, shown_not_given=True)]
    return 1, rooms, []


def control_room(rs, sheet, W, D, H):
    """D10 (engineer s. 2.3, binder/rooms/control_room.md): the plant control room on hall_b's UPHILL gable, on a stair
    tower, 14 x 8 x 3.6 m (the sheet's size:). The plant-facing wall is glass from a 0.6 m sill to 3.2 m, mullions
    every 2 m, sloped OUT 15 deg; a raised floor one step up; four consoles 2.4 m wide in a shallow arc 3 m back from the
    glass, in plant-bearing order; the mimic board on the back wall; two ways out, the stair and the bridge to the
    hall's catwalk. Local +x is the uphill gable here; export mirrors it when the layout says the low gable is +x
    (anchors.process_chain writes B['hall_b']['low_gable'])."""
    w, d, h = (tuple(rs.get("size") or ()) + (14.0, 8.0, 3.6))[:3]
    x = W / 2 - w / 2                                     # on the gable end, outside the hall's roof line
    arc = []
    for k in range(4):
        ang = math.radians(-24 + 16 * k)                  # a shallow arc, 2.4 m wide each, facing the glass (+x)
        arc.append({"x": round(x + w / 2 - 3.0 - 1.2 * (1 - math.cos(ang)), 2), "y": round(-3.6 + 2.4 * k, 2), "w": 2.4, "facing": "+x",
                    "order": "plant bearing from this room, left to right (no mirror imaging)"})
    r = room("control_room", rs.get("name", "the plant control room"), x, 0, w, d, h, 1, H,
             on="gable stair tower (uphill gable)", floor="raised one step (+0.2 m)",
             glass={"side": "+x (the plant)", "sill_m": 0.6, "top_m": 3.2, "mullion_m": 2.0, "slope_out_deg": 15.0},
             consoles=arc, back_wall="mimic board; MCC closet; kitchenette",
             exits=["stair tower to the ground", "bridge to the hall's high catwalk"], never_faces="the Authority tower")
    return r


BY_ROOM = {"control_room": control_room}
BY_ID = {"tower": authority_tower, "liandri_tower": liandri, "mess": mess, "drain": culvert,
         "pump_house": pump, "pump_station": pump}
BY_KIND = {"dorm": dorm, "hall": hall, "house": house, "pump": pump, "culvert": culvert, "office": house}
# the engineer's proposed shells (m) where they differ from the sheets
SHELLS = {"hall_b": (48, 20, 14), "hall_a": (36, 16, 10), "pump_house": (12, 8, 6), "mess": (24, 12, 5)}
SHEET_ROOM_DEFAULTS = {"command_room": "command_room", "catwalk": "catwalk", "tower_mess": None}


def plan(bid, sheet, room_sheets, drain=None):
    W, D, H = (tuple(SHELLS.get(bid, sheet.get("size", (10, 10, 4)))) + (4.0,))[:3]
    fn = BY_ID.get(bid) or BY_KIND.get(sheet.get("kind"))
    extra = {}
    if bid in floorplan.IDS or (sheet.get("kind") in ("house", "office") and bid not in BY_ID):
        fn = "floorplan"                                   # floorplan.py: sizes and connections from real plans
    if fn is None and not room_sheets:
        return None
    if fn == "floorplan":
        levels, rooms, stairs, extra = floorplan.plan(bid, sheet, W, D, H, seed=sheet.get("_seed", 1))
    else:
        levels, rooms, stairs = (fn(sheet, W, D, H, drain) if fn is culvert else fn(sheet, W, D, H)) if fn else (1, [], [])
    have = {r["id"] for r in rooms}
    for rid, rs in room_sheets.items():                # the binder's room sheets: merge their story keys, add the missing
        if rid in have:
            r = next(r for r in rooms if r["id"] == rid)
            if rs.get("size"):                             # the room sheet's own size wins (round 3)
                r.update(w=rs["size"][0], d=rs["size"][1], h=rs["size"][2] if len(rs["size"]) > 2 else r["h"])
                r["uu"] = [uu(r["w"]), uu(r["d"]), uu(r["h"])]
        elif rid in BY_ROOM:
            r = BY_ROOM[rid](rs, sheet, W, D, H)
            rooms.append(r)
        else:
            beds = int(rs.get("beds") or 0)
            area = max(24.0, beds * 4.0 / 3 * 1.2) if beds else 24.0     # bunk rooms at 3 beds / 4.8 m2 + circulation
            if rs.get("size"):                             # `size: w d h` on the room sheet (round 3)
                w, d, hh = (tuple(rs["size"]) + (STOREY_M - 0.3,))[:3]
            else:
                w = round(min(W, max(6.0, math.sqrt(area * 2))), 1)
                d, hh = round(area / w, 1), STOREY_M - 0.3
            r = room(rid, rs.get("name", rid), 0, 0, w, d, hh, 1, 0.0)
            rooms.append(r)
        r.update(sheet_name=rs.get("name"), users=rs["users"], lit=rs["lit"], wear=rs["wear"], **({"beds": int(rs["beds"])} if rs.get("beds") else {}))
    if any(r["id"] == "control_room" for r in rooms):     # the gable stair tower up to the control room's floor
        stairs.append(dict(stair(W / 2 - 2.0, D / 2 - 2.0, 0.0, H, width=1.2), to="control_room", tower="gable stair tower"))
    doors = shell_doors(sheet, W, D) if sheet.get("kind") != "culvert" else [door("grate", "personnel", 0, 0), door("outfall", "personnel", 0, 0)]
    if any(r.get("lift") for r in rooms):           # the lift and the catwalk deck are the tower's second way out
        doors += [door("lift", "personnel", 0, 0, to="lift"), door("deck", "personnel", 0, -D / 2, to="catwalk")]
    if extra.get("doors"):
        doors = extra.pop("doors")                       # moved so each lands in the common space
    out = {"id": bid, "kind": sheet.get("kind"), "shell_m": [W, D, H], "shell_uu": [uu(W), uu(D), uu(H)], "levels": levels,
           "rooms": rooms, "stairs": stairs, "doors": doors, "checks": checks(rooms, doors, stairs, sheet)}
    out.update(extra)                                    # walls, window_sides, graph, notes (floorplan.py)
    return out


def checks(rooms, doors, stairs, sheet):
    out = []
    for r in rooms:
        if r["h"] * M < HEADROOM_UU and not r.get("cover"):
            out.append("%s: headroom %d UU < %d" % (r["id"], r["h"] * M, HEADROOM_UU))
        if min(r["w"], r["d"]) * M < 2 * PLAYER_R + 24 and not r.get("cover"):
            out.append("%s: %d UU wide, the player (r %d) barely fits" % (r["id"], min(r["w"], r["d"]) * M, PLAYER_R))
        people = int(r.get("beds") or 0) + int(r.get("seats") or 0)
        if (max(r["w"], r["d"]) > 20 or people > 50) and len(doors) < 2 and not r.get("underground"):
            out.append("%s: %s m long / %d people but the shell has %d exit(s) (E27 wants 2)" % (r["id"], max(r["w"], r["d"]), people, len(doors)))
        if max(r["w"], r["d"]) / 2 > 45 and not r.get("underground"):
            out.append("%s: more than 45 m from an exit" % r["id"])
    for s in stairs:
        if s["riser_uu"] > RISER_UU:
            out.append("stair %s: riser %s UU > %d" % (s["z1"], s["riser_uu"], RISER_UU))
    for d in doors:
        if d["uu"][0] < 2 * PLAYER_R + 16 or d["uu"][1] < 2 * PLAYER_HH + 12:
            out.append("door %s: %s UU too small" % (d["side"], d["uu"]))
    return out


def build(sheets, rooms_by, layout=None, only=None):
    out = {}
    for bid, sheet in sheets.items():
        if only and bid not in only:
            continue
        if sheet.get("abandoned") or "size" not in sheet:
            continue
        p = plan(bid, sheet, {rid: r for rid, r in rooms_by.items() if r.get("in") == bid}, (layout or {}).get("drain") if bid == "drain" else None)
        if p is None:
            continue
        if layout and bid in layout["buildings"]:
            P = layout["buildings"][bid]
            p["world"] = {"x": P["x"], "y": P["y"], "z": P.get("z"), "yaw": P["yaw"]}
        out[bid] = p
    return out


def overlay(plans, png):
    """one small plan per building, at 4 px/m, ground floor + upper levels outlined"""
    from PIL import Image, ImageDraw
    ids = list(plans)
    cols = 6
    cw, ch = 260, 200
    img = Image.new("RGB", (cols * cw, ((len(ids) + cols - 1) // cols) * ch), (24, 24, 28))
    dr = ImageDraw.Draw(img)
    for k, bid in enumerate(ids):
        p = plans[bid]
        ox, oy = (k % cols) * cw, (k // cols) * ch
        W, D = p["shell_m"][0], p["shell_m"][1]
        span = max([W, D] + [abs(r["x"]) * 2 + r["w"] for r in p["rooms"]] + [abs(r["y"]) * 2 + r["d"] for r in p["rooms"]])
        s = min((cw - 20) / max(span, 1), (ch - 40) / max(span, 1))
        cx, cy = ox + cw / 2, oy + 20 + (ch - 30) / 2
        dr.rectangle([cx - W / 2 * s, cy - D / 2 * s, cx + W / 2 * s, cy + D / 2 * s], outline=(200, 200, 200))
        for r in p["rooms"]:
            col = (90, 170, 255) if r["level"] == 0 else (255, 170, 60)
            dr.rectangle([cx + (r["x"] - r["w"] / 2) * s, cy + (r["y"] - r["d"] / 2) * s, cx + (r["x"] + r["w"] / 2) * s, cy + (r["y"] + r["d"] / 2) * s], outline=col)
        for d in p["doors"]:
            dr.ellipse([cx + d["x"] * s - 3, cy + d["y"] * s - 3, cx + d["x"] * s + 3, cy + d["y"] * s + 3], fill=(80, 255, 120))
        dr.text((ox + 4, oy + 4), "%s %dx%dx%d m, %d rooms%s" % (bid, W, D, p["shell_m"][2], len(p["rooms"]), " !%d" % len(p["checks"]) if p["checks"] else ""),
                fill=(255, 255, 255))
    img.save(png)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if "=" not in a]
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    run = args[0] if args else None
    L = json.load(open(os.path.join(run, "isl_layout.json"))) if run else None
    _, sheets = binder.load()
    plans = build(sheets, binder.load_rooms(), L, set(o["only"].split(",")) if o.get("only") else None)
    out = o.get("out", os.path.join(run, "rooms.json") if run else os.path.join(HERE, "rooms.json"))
    json.dump(plans, open(out, "w"), indent=1)
    png = o.get("png", os.path.join(run, "isl_rooms.png") if run else None)
    if png:
        overlay(plans, png)
    for bid, p in plans.items():
        print("  %-16s %-8s shell %s m, %d levels, %2d rooms, %d stairs, %d doors%s" % (
            bid, p["kind"], p["shell_m"], p["levels"], len(p["rooms"]), len(p["stairs"]), len(p["doors"]),
            ("; " + "; ".join(p["checks"][:3])) if p["checks"] else ""))
    print("%d interior plans, %d rooms, %d check notes -> %s" % (len(plans), sum(len(p["rooms"]) for p in plans.values()),
                                                                  sum(len(p["checks"]) for p in plans.values()), out))
