r"""Random islands with the binder town on them, end to end, one game run each:

    py tools/island_batch.py <seed> [<seed> ...] [shift=-5300]

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


for seed in seeds:
    name = "TutA_Rand%d" % seed
    base = os.path.join(OUT, "isl%d" % seed)
    print("\n=== seed", seed, "->", name, flush=True)
    run(["py", os.path.join(TOOLS, "random_island.py"), seed, TEMPLATE, base + ".bmp"])
    run(["py", TERRAIN, "erode", base + ".bmp", base + "_e.bmp", "--cell", "512", "--zstep", "0.5", "--unit", "0.02",
         "--seed", seed])
    restore_sea(base + ".bmp", base + "_e.bmp", base + "_e.bmp")
    run(["py", os.path.join(TOOLS, "terrain_cutfill.py"), base + "_e.bmp", base + "_ec.bmp", "shift=" + SHIFT])
    island_png(base + "_ec.bmp", base + "_map.png")
    run(["py", os.path.join(TOOLS, "terrain_apply.py"), base + "_ec.bmp", name])
    run(["py", os.path.join(TOOLS, "export_mutator.py"), "shift=" + SHIFT])
    enable_map(name)
    script = os.path.join(PILOT, "scripts", "cards_binder_rand%d.txt" % seed)
    src = open(os.path.join(PILOT, "scripts", "cards_binder_cut.txt")).read()
    open(script, "w").write(re.sub(r"(?m)^map \S+\?", "map %s?" % name, src))
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
