"""Offline tests for gm_commit.py (no game, no editor):  py -m unittest test_gm_commit -v"""
import math, os, sys, tempfile, unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gm_commit as g  # noqa

F = np.float32

INI = r'''[U2GM.GMMaster]
GridSize=32.000000
Ops[0]="@tuta place StaticMeshActor112 1200 -300 64 90 1.000000"
Ops[2]=@tuta mesh Terran_DecoM.Crates.Crate1Low 100 200 -50 -45 1.500000
Ops[1]="@tutb hide Rock3"
Ops[5]="@tuta terrain raise -14000 5000 1024 256"
Ops[3]="@TutA hide StaticMeshActor7"
Ops[4]=
Ops[6]="@tuta draw D1 open 0 0 0 1 1 1 note never baked"
Ops[7]="@tuta terrain smooth -14000 5000 600 0"
PanelState="seq=5:9 on=1 poss=0 frz=0 pick=- cls=- mesh=- loc=0,0,0 yaw=0 scale=1 cam=1,2,3 wseq=1073741900:3 commit=4:pending:- draw=0"
CommitRequest="tuta 4 TutA_Live2 5"
CommitStatus="4 pending"
Draws[0]="@tuta draw D1 closed 0 0 0 100 0 0 100 100 0 note shanty here"

[Other.Section]
Ops[0]="@tuta hide NotThisOne"
'''


def fork_reference(orig, t, brushes):
    """a line-by-line port of u2shaders.hpp GmRun's brush loop (bounding box, per cell, float32)"""
    H, W = orig.shape
    work = orig.astype(np.float32).copy()
    O, AX, AY, AZ = t.O, t.AX, t.AY, F(t.AZ)
    CellX, CellY = F(math.hypot(AX[0], AX[1])), F(math.hypot(AY[0], AY[1]))
    for b in brushes:
        bx, by, R, Hh = F(b["x"]), F(b["y"]), F(b["r"]), F(b["h"])
        # WorldToHeightmap of the centre (affine inverse)
        cx, cy = (bx - O[0]) / AX[0], (by - O[1]) / AY[1]
        RX, RY = R / CellX, R / CellY
        X1, X2 = max(0, int(math.floor(cx - RX - 1))), min(W - 1, int(math.ceil(cx + RX + 1)))
        Y1, Y2 = max(0, int(math.floor(cy - RY - 1))), min(H - 1, int(math.ceil(cy + RY + 1)))
        if X1 > X2 or Y1 > Y2:
            continue
        smooth = b["brush"][0] == "s"
        prev = work.copy() if smooth else None
        strength = F(min(max(float(Hh), 0.0), 1.0))
        for y in range(Y1, Y2 + 1):
            for x in range(X1, X2 + 1):
                WX = F(O[0] + F(x) * AX[0] + F(y) * AY[0])
                WY = F(O[1] + F(x) * AX[1] + F(y) * AY[1])
                D = F(math.sqrt(F(F(WX - bx) * F(WX - bx) + F(WY - by) * F(WY - by))))
                if D >= R:
                    continue
                fall = F(F(0.5) * F(F(1.0) + F(math.cos(F(F(F(3.14159265) * D) / R)))))
                v = work[y, x]
                k = b["brush"][0]
                if k == "r":
                    v = F(v + F(F(fall * Hh) / AZ))
                elif k == "l":
                    v = F(v - F(F(fall * Hh) / AZ))
                elif k == "f":
                    base = F(O[2] + F(x) * AX[2] + F(y) * AY[2])
                    v = F(v + F(fall * F(F(F(Hh - base) / AZ) - v)))
                else:
                    s, n = F(0), 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if 0 <= x + dx < W and 0 <= y + dy < H:
                                s = F(s + prev[y + dy, x + dx])
                                n += 1
                    v = F(v + F(F(fall * strength) * F(F(s / F(n)) - v)))
                work[y, x] = v
    return (np.clip(work, 0, 65535) + F(0.5)).astype(np.uint16)


class Journal(unittest.TestCase):
    def test_utf16_and_quotes(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "U2GM.ini")
            open(p, "wb").write(b"\xff\xfe" + INI.replace("\n", "\r\n").encode("utf-16-le"))
            text = g.read_text(p)
            p8 = os.path.join(d, "U2GM8.ini")
            open(p8, "w").write(INI)
            self.assertEqual(g.journal(text, "tuta"), g.journal(g.read_text(p8), "tuta"))
            # UTF-16 without a BOM (the NUL test)
            open(p, "wb").write(INI.encode("utf-16-le"))
            self.assertEqual(g.journal(g.read_text(p), "tuta"), g.journal(text, "tuta"))

    def test_family_lines_in_slot_order(self):
        j = g.journal(INI, "tuta")
        self.assertEqual([k for k, _ in j], [0, 2, 3, 5, 6, 7])
        self.assertEqual(j[0][1], "place StaticMeshActor112 1200 -300 64 90 1.000000")
        self.assertEqual(j[2][1], "hide StaticMeshActor7")          # tag compared without case
        self.assertNotIn("NotThisOne", " ".join(t for _, t in j))    # other sections ignored
        self.assertEqual(g.journal(INI, "tutb"), [(1, "hide Rock3")])

    def test_parse_ops(self):
        o = g.parse_op("place StaticMeshActor112 1200 -300 64 90 1.000000")
        self.assertEqual((o["name"], o["loc"], o["yaw"], o["scale"]), ("StaticMeshActor112", (1200, -300, 64), 90, 1.0))
        o = g.parse_op("mesh Terran_DecoM.Crates.Crate1Low 100 200 -50 -45 1.5")
        self.assertEqual((o["path"], o["scale"]), ("Terran_DecoM.Crates.Crate1Low", 1.5))
        self.assertEqual(g.parse_op("terrain smooth 1 2 300 0")["h"], 1.0)     # the fork: smooth H 0 -> 1
        self.assertEqual(g.parse_op("terrain flatten 1 2 300")["h"], 0.0)
        for bad in ("draw D1 open 0 0 0", "terrain dig 1 2 3 4", "terrain raise 1 2 0 4", "place X 1 2", "", "zap"):
            self.assertRaises(ValueError, g.parse_op, bad)

    def test_yaw(self):
        self.assertEqual(g.yaw_units(90), 16384)
        self.assertEqual(g.yaw_units(-45), -8192)
        self.assertEqual(g.yaw_units(1), 182)                         # truncated, as UnrealScript int()

    def test_panel_state_and_request(self):
        keys, st = g.state_of(INI)
        self.assertEqual(keys["commitrequest"], "tuta 4 TutA_Live2 5")
        self.assertEqual(st["wseq"], "1073741900:3")
        self.assertEqual(st["commit"], "4:pending:-")

    def test_maps(self):
        names = ["TutA", "TutA_Live1", "TutA_Live3", "TutA_Live10", "TutB"]
        self.assertEqual(g.source_map("tuta", names), "TutA_Live10")
        self.assertEqual(g.source_map("tutb", names), "TutB")
        self.assertEqual(g.next_live("TutA_Live10", names), "TutA_Live2")
        self.assertEqual(g.next_live("TutB", names), "TutB_Live1")
        self.assertEqual(g.family_of("TutA_Live3.LevelInfo0"), "tuta")


class TerrainMath(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.orig = (32768 + rng.normal(0, 600, (40, 48))).clip(0, 65535).astype(np.uint16)
        self.t = g.Terrain("T", (-14487.546875, 4835.837891, -131.845703), (512.0, 512.0, 128.0), "x", 48, 40)

    def brushes(self, lines):
        return [g.parse_op("terrain " + l) for l in lines]

    def check(self, lines, orig=None):
        orig = self.orig if orig is None else orig
        b = self.brushes(lines)
        ours, _ = g.apply_brushes(orig, self.t, b)
        ref = fork_reference(orig, self.t, b)
        d = np.abs(ours.astype(int) - ref.astype(int))
        self.assertLessEqual(int(d.max()), 1, "more than one height step apart")
        self.assertGreaterEqual(float((d == 0).mean()), 0.998)
        return ours

    def test_each_brush(self):
        c = (-14487.5 + 3 * 512, 4835.8 - 2 * 512)
        for l in ("raise %g %g 3000 256", "lower %g %g 2500 300", "flatten %g %g 4000 -200", "smooth %g %g 5000 1",
                  "smooth %g %g 5000 0.3"):
            self.check([l % c])

    def test_sequence_and_edges(self):
        out = self.check(["raise -14000 5000 4096 512", "flatten -13000 6000 3000 100", "smooth -14000 5000 6000 1",
                          "lower -26000 -5000 3000 200",           # the corner: clipped by the grid
                          "raise -14487 4835 1200 20000",          # clamps at 65535
                          "lower 90000 90000 1000 50"])            # off the terrain: nothing
        self.assertEqual(int(out.max()), 65535)

    def test_raise_amount(self):
        flat = np.full((40, 48), 32768, np.uint16)
        cx, cy = self.t.O[0] + 20 * 512, self.t.O[1] + 17 * 512
        out = self.check(["raise %r %r 2048 256" % (float(cx), float(cy))], flat)
        self.assertEqual(int(out[17, 20]) - 32768, 512)                 # 256 units / 0.5 per step
        self.assertEqual(int(out[17, 24]), 32768)                        # D == R: untouched

    def test_flatten_target(self):
        flat = np.full((40, 48), 30000, np.uint16)
        cx, cy = self.t.O[0] + 10 * 512, self.t.O[1] + 10 * 512
        out = self.check(["flatten %r %r 3000 0" % (float(cx), float(cy))], flat)
        self.assertAlmostEqual(float(self.t.world_z(int(out[10, 10]))), 0.0, delta=0.5)

    def test_bmp_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            head, hm, h = g.make_bmp16(48, 40)
            hm = self.orig
            p = os.path.join(d, "h.bmp")
            g.write_bmp16(p, head, hm, h)
            head2, hm2, h2 = g.read_bmp16(p)
            self.assertTrue((hm2 == hm).all())
            self.assertEqual((head2, h2), (head, h))


class Plan(unittest.TestCase):
    def lines(self):
        return g.journal(INI, "tuta")

    def run_plan(self, use_ops):
        with tempfile.TemporaryDirectory() as d:
            out = []
            b = g.Bake(self.lines(), "TutA_Live2", "TutA_Live3", 4, d, use_ops=use_ops, log=out.append)
            ed = g.DryEd(log=out.append)
            b.run(ed, g.DryOps(ed) if use_ops else None)
            return b, ed.cmds

    def test_ops_plan(self):
        b, cmds = self.run_plan(True)
        text = "\n".join(cmds)
        self.assertIn("!move StaticMeshActor112 1200 -300 64 - 16384 -", text)
        self.assertIn("ACTOR DELETE", text)
        self.assertIn("TEXTURE IMPORT", text)
        self.assertIn("LIGHT APPLY CHANGED=1", text)
        self.assertTrue(cmds[-1].startswith("MAP SAVE") and "TutA_Live3" in cmds[-1])
        self.assertEqual(sorted(s for s, _ in b.baked), [0, 2, 3, 5, 7])
        self.assertEqual([s for s, _, _ in b.skipped], [6])                  # the draw line
        self.assertIn("StaticMesh=StaticMesh'Terran_DecoM.Crates.Crate1Low'", b.t3d)
        self.assertIn("Rotation=(Yaw=-8192)", b.t3d)

    def test_no_ops_plan(self):
        b, cmds = self.run_plan(False)
        text = "\n".join(cmds)
        self.assertNotIn("!move", text)
        self.assertIn("SELECTNAME NAME=StaticMeshActor112", text)
        self.assertIn("Name=StaticMeshActor112", b.t3d)                     # re-imported, edited
        self.assertIn("Location=(X=1200.000,Y=-300.000,Z=64.000)", b.t3d)

    def test_answer_lines(self):
        lines = g.q_lines(g.WATCH_BASE + 5, ["baked 4 0 place A 1 2 3 4 1", "travel TutA_Live3"])
        self.assertEqual(lines[1], "gm q %d 2 travel TutA_Live3" % (g.WATCH_BASE + 5))

    def test_panel_merge_keeps_the_panels_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "U2GMPanel.txt")
            open(p, "w").write("gm q 77 3 pick\r\ngm q 77 4 hide\r\n")
            w = g.WATCH_BASE + 9
            g.panel_merge(g.q_lines(w, ["travel X"]), w, p)
            self.assertEqual(open(p).read().split(), "gm q 77 3 pick gm q 77 4 hide gm q %d 1 travel X".format().replace("%d", str(w)).split())
            g.panel_merge([], w, p)
            self.assertNotIn(str(w), open(p).read())


if __name__ == "__main__":
    unittest.main()
