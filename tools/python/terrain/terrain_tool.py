"""Command line for terrain_erode / terrain_score on Unreal Engine 2 heightmaps.

    py tools/python/terrain/terrain_tool.py score  <in.bmp|.npy> [--cell 512] [--zstep 0.5] [--unit 0.02]
    py tools/python/terrain/terrain_tool.py erode  <in.bmp|.npy> <out.bmp|.npy> [--cell 512] [--zstep 0.5]
             [--unit 0.02] [--freeze mask.png] [--steps 250] [--droplets 60000] [--thermal 50] [--seed 0]
             [--masks folder]      writes the layer masks as 8-bit PNGs (same size as the heightmap)

The .bmp is UnrealEd's 16-bit G16 heightmap export (TEXTURE IMPORT takes the same bytes
back); the header is kept, only the pixels change. Heights: Z = Z0 + (value - 32768) * zstep
world units, a cell is `cell` units wide, and `unit` is metres per world unit (Unreal II:
2 cm), so TutA (cell 512, ScaleZ 128 -> zstep 0.5) is 10.24 m per cell and 1 cm per step.
--freeze: a PNG/BMP whose non-black pixels mark cells to leave untouched (building pads);
the Avalon pipeline runs its cut-and-fill after this instead.
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


def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    cmd, src = sys.argv[1], sys.argv[2]
    cell = arg("--cell", 512.0); zstep = arg("--zstep", 0.5); unit = arg("--unit", 0.02)
    mpc = cell * unit
    H, raw, off = load(src)
    is_g16 = raw is not None
    metres = (H - 32768.0) * zstep * unit if is_g16 else H
    if cmd == "score":
        ts.report(ts.score(metres, mpc))
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
            from PIL import Image
            os.makedirs(folder, exist_ok=True)
            for k, v in te.layer_masks(out).items():
                Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).save(os.path.join(folder, k + ".png"))
            for k in ("flow", "deposit", "wear", "debris"):
                a = out[k]; a = np.log1p(a) if k == "flow" else a
                a = a / max(a.max(), 1e-9)
                Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(folder, "state_" + k + ".png"))
            print("masks written to", folder)
        return
    print(__doc__)


if __name__ == "__main__":
    main()
