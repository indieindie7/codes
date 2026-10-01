"""Headless test of bake_lightmaps.py (pip install bpy): bakes test/capture_sample, a capture
U2Shaders' lmcapture=1 wrote from its own test program (a lightmapped wall, Wine), with a
point light near the wall's top left, and checks the DDS that comes out.

    python test/test_bake.py"""
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bake_lightmaps  # noqa: E402

failures = []

def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failures.append(what)

with tempfile.TemporaryDirectory() as tmp:
    shutil.copytree(os.path.join(HERE, "capture_sample"), os.path.join(tmp, "U2Shaders"))
    cap = os.path.join(tmp, "U2Shaders", "capture")
    rc = bake_lightmaps.main(["--capture", cap, "--point=0,20,20,800", "--samples", "16"])
    check(rc == 0, "bake ran")
    out = os.path.join(tmp, "U2Shaders", "baked", "e5d228fd.dds")
    check(os.path.isfile(out), "baked lightmap written")
    if os.path.isfile(out):
        data = open(out, "rb").read()
        h = struct.unpack("<32I", data[:128])
        check((h[4], h[3], h[7]) == (64, 64, 7), "64x64 with 7 mip levels")
        px = lambda x, y: data[128 + (y * 64 + x) * 4 + 2]
        check(px(4, 4) > 3 * px(60, 60), "brighter near the light (top left %d) than far (bottom right %d)" % (px(4, 4), px(60, 60)))
        mean = sum(data[128 + i * 4 + 2] for i in range(64 * 64)) / (64 * 64 * 255)
        orig = bake_lightmaps.dds_mean(os.path.join(tmp, "U2Shaders", "dump", "e5d228fd_64x64.dds"))
        check(abs(mean - orig) < 0.02, "average matched to the original (%.3f vs %.3f)" % (mean, orig))
    lines = open(os.path.join(tmp, "U2Shaders", "baked", "replace_lines.txt")).read()
    check("replace=e5d228fd baked\\e5d228fd.dds" in lines, "replace= line for U2Shaders.ini")

print("FAILED: %d" % len(failures) if failures else "all passed")
sys.exit(1 if failures else 0)
