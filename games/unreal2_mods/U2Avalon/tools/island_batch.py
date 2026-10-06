r"""Random islands with the binder town on them, end to end, one game run each:

    py tools/island_batch.py <seed> [<seed> ...] [shift=-5300] [gen=form|noise]

Per seed: random_island.py -> terrain erosion (tools/python/terrain) -> terrain_cutfill.py (pads under the
town) -> terrain_apply.py into Maps\TutA_Rand<seed>.un2 (UnrealEd, uedlib) -> export_mutator.py (town
props into U2AvalonCards.ini, map enabled) -> U2Pilot run of the cards_binder views -> sheet copied to
Documents\U2_research\terrain\rand\Rand<seed>_sheet.png with the island picture beside it.
The UnrealEd and game steps run one at a time; the GPU announcement to the Advent chat is the caller's job.
"""
import os, re, shutil, struct, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODES = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(HERE, "tools")
TERRAIN = os.path.join(CODES, "tools", "python", "terrain", "terrain_tool.py")
PILOT = os.path.join(CODES, "tools", "python", "U2Pilot")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
INI = os.path.join(GAME, "System", "U2AvalonCards.ini")
R = r"C:\Users\john\Documents\U2_research\terrain"
OUT = os.path.join(R, "rand")
TEMPLATE = os.path.join(R, "island1.bmp")
os.makedirs(OUT, exist_ok=True)

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
seeds = [int(a) for a in args] or [1]
SHIFT = o.get("shift", "-5300")
GEN = o.get("gen", "form")
STYLE = o.get("style", "ridges")  # island_form style: ridges | plateau
PILOT = o.get("pilot", "1") != "0"   # pilot=0: no game run (editor pictures only; e.g. while another GPU job runs)
NAME = o.get("name", "TutA_Rand")    # map name prefix        # form = designed island by the terrain tool (island_form.py); noise = random_island.py + erosion


def run(cmd, **k):
    print("$", " ".join(str(c) for c in cmd)[:160], flush=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **k)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if not re.match(r"\s*(Matched Viewport|Allocating|.*arbage)", l)]
    for l in tail[-6:]:
        print("   ", l[:160], flush=True)
    if r.returncode:
        raise SystemExit("step failed: %s" % cmd[1])
    return r.stdout


def enable_map(name):
    txt = open(INI, newline="").read()
    m = re.search(r"(?m)^Maps=(.*)$", txt)
    maps = [x.strip().lower() for x in m.group(1).split(",") if x.strip()]
    if name.lower() not in maps:
        maps.append(name.lower())
        txt = txt[:m.start(1)] + ",".join(maps) + txt[m.end(1):]
        open(INI, "w", newline="").write(txt)


def read_bmp(bmp):
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    return raw, off, h < 0, (H if h < 0 else H[::-1])


def restore_sea(before, after, out, sea_h=32768 + (-4967 + 131.85) * 2):
    """the erosion deposits its spoil on the flat sea floor and lifts it over the sea surface (the floor is
    only 10 m under it): every cell that was sea before erosion keeps its pre-erosion height"""
    raw, off, up, A = read_bmp(after)
    _, _, _, B = read_bmp(before)
    sea = B <= sea_h - 60
    A = np.where(sea, B, np.maximum(A, np.where(B > sea_h, sea_h + 40, A)))     # land never drowns either
    Hn = np.clip(np.round(A), 0, 65535).astype("<u2")
    pix = (Hn if up else Hn[::-1]).tobytes()
    open(out, "wb").write(raw[:off] + pix + raw[off + len(pix):])
    print("    sea restored on %d cells" % sea.sum(), flush=True)


def island_png(bmp, png):
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    if h > 0:
        H = H[::-1]
    Z = -131.85 + (H - 32768) * 0.5
    from PIL import Image
    sea = Z <= -4967
    t = np.clip((Z + 4967) / 4000, 0, 1)
    rgb = np.zeros((128, 128, 3), "u1")
    rgb[..., 0] = np.where(sea, 30, 80 + 150 * t)
    rgb[..., 1] = np.where(sea, 60, 120 + 100 * t)
    rgb[..., 2] = np.where(sea, 140, 60 + 150 * t)
    rgb[57, 92] = (255, 0, 0)
    rgb[39, 101] = (255, 255, 0)
    Image.fromarray(rgb).resize((512, 512), Image.NEAREST).save(png)


def pilot_script(name, layout_json):
    import json, math
    L = json.load(open(layout_json))["buildings"]
    tower = L["tower"]
    plant = L.get("plant_office", tower)
    dock = L.get("dock", plant)
    halls = [L[k] for k in L if k.startswith("hall") and math.hypot(L[k]["x"] - plant["x"], L[k]["y"] - plant["y"]) < 200 * 50] + [plant]
    cx, cy = sum(h["x"] for h in halls) / len(halls), sum(h["y"] for h in halls) / len(halls)

    def face(fx, fy, tx, ty):
        return int(math.degrees(math.atan2(ty - fy, tx - fx))) % 360

    def back_off(tx, ty, d, deg):
        a = math.radians(deg)
        return tx + d * math.cos(a), ty + d * math.sin(a)
    gz = max(h.get("z", -4800) for h in halls + [plant])                          # the plant's ground
    px, py = back_off(cx, cy, 5500, face(cx, cy, tower["x"], tower["y"]))         # between the plant and the tower, high up
    sx, sy = back_off(dock["x"], dock["y"], 2500, face(dock["x"], dock["y"], cx, cy) + 180)   # out past the dock, looking in
    lines = ["# generated by island_batch.py from %s" % os.path.basename(layout_json), "background",
             "map %s?Mutator=U2AvalonCards.AvalonCards" % name, "waitcontrol 240", "wait 2", "console god",
             "turn 270 0 0.5", "move 1 0 2.2", "wait 0.8"]
    f0 = face(tower["x"], tower["y"], cx, cy)
    for dy, pitch in ((0, -22), (18, -18), (-16, -20)):
        lines += ["console hub face %d" % ((f0 + dy) % 360), "turn 0 %d 0.3" % pitch, "wait 0.6", "shot"]
    lines += ["console ghost", "console hub tp %.0f %.0f %.0f" % (px, py, gz + 5200), "console hub face %d" % face(px, py, cx, cy),
              "turn 0 -32 0.3", "wait 1", "shot",
              "console hub tp %.0f %.0f %.0f" % (sx, sy, gz + 900), "console hub face %d" % face(sx, sy, cx, cy),
              "turn 0 -4 0.3", "wait 1", "shot",
              "console hub tp %.0f %.0f %.0f" % (back_off(cx, cy, 9000, face(cx, cy, tower["x"], tower["y"]) + 90) + (gz + 12000,)),
              "console hub face %d" % face(*back_off(cx, cy, 9000, face(cx, cy, tower["x"], tower["y"]) + 90), cx, cy),
              "turn 0 -45 0.3", "wait 1", "shot", "quit"]
    return "\n".join(lines) + "\n"


def populate(name, t3d, layout_json, base):
    """UnrealEd: load the map, load the mesh packages, import the actors, save; then editor pictures"""
    import json, math
    sys.path.insert(0, os.path.join(CODES, "tools", "C", "U2EdBridge"))
    from uedlib import Ed, session
    L = json.load(open(layout_json))["buildings"]
    plant = L.get("plant_office", L["tower"])
    halls = [L[k] for k in L if k.startswith("hall") and math.hypot(L[k]["x"] - plant["x"], L[k]["y"] - plant["y"]) < 200 * 50] + [plant]
    cx, cy = sum(h["x"] for h in halls) / len(halls), sum(h["y"] for h in halls) / len(halls)
    gz = max(h.get("z", -4800) for h in halls)
    tower = L["tower"]

    def job(ed):
        ed.exec("!answer yes")
        ed.load(name)
        for pkg in ("StaticMeshes/AvalonSM.usx", "StaticMeshes/Mission_05M.usx", "StaticMeshes/Mission_03M.usx",
                    "StaticMeshes/Terran_DecoM.usx", "StaticMeshes/Flora_M.usx"):
            ed.load_package(os.path.join(GAME, pkg))
        ed.import_t3d(t3d, add=True)
        ed.light()                      # static meshes stay black in the editor until the lighting is applied
        ed.save(name)
        ed.hide_icons()
        # pictures: over the plant toward the tower, from the sea toward the plant, the whole island
        def yaw_to(fx, fy, tx, ty):
            return int(math.degrees(math.atan2(ty - fy, tx - fx)) * 65536 / 360) % 65536
        a = math.atan2(tower["y"] - cy, tower["x"] - cx)
        px, py = cx - 3500 * math.cos(a), cy - 3500 * math.sin(a)
        ed.view(px, py, gz + 3500, pitch=-7000, yaw=yaw_to(px, py, cx, cy))
        ed.screenshot(base + "_ed_plant.png")
        sx, sy = cx + 9000 * math.cos(a + math.pi / 2), cy + 9000 * math.sin(a + math.pi / 2)
        ed.view(sx, sy, gz + 1500, pitch=-1500, yaw=yaw_to(sx, sy, cx, cy))
        ed.screenshot(base + "_ed_side.png")
        ed.view(cx - 12000 * math.cos(a), cy - 12000 * math.sin(a), gz + 14000, pitch=-8500, yaw=yaw_to(cx - 12000 * math.cos(a), cy - 12000 * math.sin(a), cx, cy))
        ed.screenshot(base + "_ed_island.png")
    session(job)



def main():
    for seed in seeds:
        name = "%s%d" % (NAME, seed)
        base = os.path.join(OUT, "isl%d" % seed)
        print("\n=== seed", seed, "->", name, flush=True)
        if GEN == "form":
            # the terrain tool forms and erodes the island itself (sketch -> stream power -> droplets -> thermal)
            run(["py", os.path.join(TOOLS, "island_form.py"), seed, TEMPLATE, base + "_e.bmp", "png=" + base + "_sketch.png", "style=" + STYLE])
        else:
            run(["py", os.path.join(TOOLS, "random_island.py"), seed, TEMPLATE, base + ".bmp"])
            run(["py", TERRAIN, "erode", base + ".bmp", base + "_e.bmp", "--cell", "512", "--zstep", "0.5", "--unit", "0.02",
                 "--seed", seed])
            restore_sea(base + ".bmp", base + "_e.bmp", base + "_e.bmp")
        # the town: anchors + interest-map seeding + roads + Voronoi drift (layout.py), then pads under it
        layout = base + "_layout.json"
        run(["py", os.path.join(TOOLS, "layout.py"), base + "_e.bmp", layout, "seed=%d" % seed, "shift=" + SHIFT, "png=" + base + "_map.png"])
        run(["py", os.path.join(TOOLS, "terrain_cutfill.py"), base + "_e.bmp", base + "_ec.bmp", "shift=" + SHIFT, "layout=" + layout])
        run(["py", os.path.join(TOOLS, "terrain_apply.py"), base + "_ec.bmp", name])
        # the buildings go into the MAP as StaticMeshActors (ground Z from the final heightmap); the ini keeps the cards
        t3d = base + "_actors.t3d"
        run(["py", os.path.join(TOOLS, "export_mutator.py"), "shift=" + SHIFT, "layout=" + layout, "t3d=" + t3d,
             "heightmap=" + base + "_ec.bmp", "props=0"])
        populate(name, t3d, layout, base)
        enable_map(name)
        if not PILOT:
            print("pilot skipped (pilot=0); editor pictures ->", base + "_ed_*.png", flush=True)
            continue
        script = os.path.join(PILOT, "scripts", "cards_binder_rand%d.txt" % seed)
        open(script, "w").write(pilot_script(name, layout))
        run(["py", os.path.join(PILOT, "u2pilot.py"), script, "--background"], cwd=PILOT)
        runs = sorted(d for d in os.listdir(os.path.join(PILOT, "runs")) if d.endswith("cards_binder_rand%d" % seed))
        if runs:
            sheet = os.path.join(PILOT, "runs", runs[-1], "sheet.png")
            if os.path.exists(sheet):
                from PIL import Image
                s, m = Image.open(sheet), Image.open(base + "_map.png")
                m = m.resize((s.height, s.height))
                board = Image.new("RGB", (s.width + m.width + 8, s.height), (20, 20, 20))
                board.paste(m, (0, 0))
                board.paste(s, (m.width + 8, 0))
                board.save(os.path.join(OUT, "Rand%d_sheet.png" % seed))
                print("sheet ->", os.path.join(OUT, "Rand%d_sheet.png" % seed), flush=True)
    print("done", seeds)


if __name__ == "__main__":
    main()
