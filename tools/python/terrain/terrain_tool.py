"""Command line for the terrain package on Unreal Engine 2 heightmaps.

    py terrain_tool.py form   <sketch.json> <out.npy|out.bmp> [--template in.bmp] [--size N] [--steps N]
             [--seed 0] [--preset hills|alpine|canyon] [--preview out.png] [--masks folder] [--cell 512] [--zstep 0.5] [--unit 0.02]
    py terrain_tool.py score  <in.bmp|.npy> [--cell 512] [--zstep 0.5] [--unit 0.02]
    py terrain_tool.py erode  <in.bmp|.npy> <out.bmp|.npy> [--cell 512] [--zstep 0.5] [--unit 0.02]
             [--freeze mask.png] [--steps 250] [--droplets 60000] [--thermal 50] [--seed 0] [--masks folder]
    py terrain_tool.py preview <in.bmp|.npy> <out.png> [--cell 512] [--zstep 0.5] [--unit 0.02] [--masks folder]

form: a designed map from a sketch (see terrain_sketch's docstring for the JSON): uplift
primitives -> stream power from flat -> strata/droplets/thermal -> detail -> pads -> masks.
Writes .npy (metres) or, with --template, a G16 BMP with the template's header (UnrealEd's
16-bit heightmap export: TEXTURE IMPORT takes the same bytes back); the template must have the
sketch's size. Heights in a G16: Z = Z0 + (value - 32768) * zstep world units, a cell is
`cell` units wide, `unit` is metres per world unit (Unreal II: 2 cm), so TutA (cell 512,
ScaleZ 128 -> zstep 0.5) is 10.24 m per cell. The sea level / zero of the sketch lands at 32768.
--masks writes the layer masks and the simulation state as 8-bit PNGs of the heightmap's size,
which is exactly what a UE2 alpha map has to be.
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import terrain_erode as te   # noqa: E402
import terrain_score as ts   # noqa: E402


def read_g16(path):
    raw = open(path, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    bpp = struct.unpack_from("<H", raw, 28)[0]
    assert bpp == 16, "not a 16-bit heightmap BMP (bpp %d)" % bpp
    rows_up = h < 0
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
    if not rows_up:
        H = H[::-1]
    return H, raw, off


def write_g16(path, H, raw, off):
    w = H.shape[1]; hh = struct.unpack_from("<i", raw, 22)[0]
    assert (abs(hh), w) == H.shape, "template size %dx%d differs from the heightmap %dx%d" % (w, abs(hh), H.shape[1], H.shape[0])
    rows = H if hh < 0 else H[::-1]
    pix = np.clip(np.rint(rows), 0, 65535).astype("<u2").tobytes()
    open(path, "wb").write(raw[:off] + pix + raw[off + len(pix):])


def load(path):
    if path.lower().endswith(".npy"):
        return np.load(path).astype(np.float64), None, None
    return read_g16(path)


def arg(name, default, cast=float):
    if name in sys.argv:
        return cast(sys.argv[sys.argv.index(name) + 1])
    return default


def write_masks(folder, out):
    from PIL import Image
    os.makedirs(folder, exist_ok=True)
    masks = out["masks"] if "masks" in out else te.layer_masks(out)
    for k, v in masks.items():
        Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).save(os.path.join(folder, k + ".png"))
    for k in ("flow", "deposit", "wear", "debris", "hardness", "uplift"):
        if k not in out:
            continue
        a = np.asarray(out[k], dtype=np.float64); a = np.log1p(a) if k == "flow" else a
        a = a / max(a.max(), 1e-9)
        Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(folder, "state_" + k + ".png"))
    if "pads" in out and out["pads"].any():
        Image.fromarray((out["pads"] * 255).astype(np.uint8)).save(os.path.join(folder, "freeze_pads.png"))
    print("masks written to", folder)


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    cmd, src = sys.argv[1], sys.argv[2]
    cell = arg("--cell", 512.0); zstep = arg("--zstep", 0.5); unit = arg("--unit", 0.02)
    mpc = cell * unit
    if cmd == "form":
        import terrain_form as tf_
        import terrain_preview as tp
        dst = sys.argv[3]
        out = tf_.form(src, preset=arg("--preset", None, str), seed=int(arg("--seed", 0, int)), size=arg("--size", None, int), steps=arg("--steps", None, int))
        mpc = out["metres_per_cell"]
        if dst.lower().endswith(".npy"):
            np.save(dst, out["h"])
        else:
            tpl = arg("--template", None, str)
            assert tpl, "a .bmp output needs --template <g16 export of the right size>"
            _, raw, off = read_g16(tpl)
            vals = out["h"] / (zstep * unit) + 32768.0
            write_g16(dst, vals, raw, off)
        print("written", dst)
        pv = arg("--preview", None, str)
        if pv:
            tp.save_png(pv, tp.render(out["h"], mpc, out["masks"]))
            print("preview", pv)
        folder = arg("--masks", None, str)
        if folder:
            write_masks(folder, out)
        return
    H, raw, off = load(src)
    is_g16 = raw is not None
    metres = (H - 32768.0) * zstep * unit if is_g16 else H
    if cmd == "score":
        ts.report(ts.score(metres, mpc))
        return
    if cmd == "preview":
        import terrain_preview as tp
        masks = None
        folder = arg("--masks", None, str)
        if folder:
            from PIL import Image
            masks = {}
            for k in ("grass", "wet", "scree", "rock", "snow", "sand"):
                p = os.path.join(folder, k + ".png")
                if os.path.exists(p):
                    masks[k] = np.array(Image.open(p).convert("L")) / 255.0
        tp.save_png(sys.argv[3], tp.render(metres, mpc, masks))
        print("preview", sys.argv[3])
        return
    if cmd == "erode":
        dst = sys.argv[3]
        fixed = None
        fz = arg("--freeze", None, str)
        if fz:
            from PIL import Image
            fixed = np.array(Image.open(fz).convert("L")) > 0
            assert fixed.shape == H.shape, "freeze mask size differs from the heightmap"
        print("before:"); ts.report(ts.score(metres, mpc))
        out = te.erode(metres, mpc, fixed=fixed, seed=int(arg("--seed", 0, int)), sp_steps=int(arg("--steps", 250, int)),
                       droplet_count=int(arg("--droplets", 60000, int)), thermal_iterations=int(arg("--thermal", 50, int)))
        print("after:"); ts.report(ts.score(out["h"].astype(np.float64), mpc))
        if is_g16:
            vals = out["h"] / (zstep * unit) + 32768.0
            write_g16(dst, vals, raw, off)
        else:
            np.save(dst, out["h"])
        print("written", dst)
        folder = arg("--masks", None, str)
        if folder:
            write_masks(folder, out)
        return
    print(__doc__)


if __name__ == "__main__":
    main()
