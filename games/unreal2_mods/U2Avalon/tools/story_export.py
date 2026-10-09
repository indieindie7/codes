r"""The story keys as StaticMeshActors: the drain (anchors.drain -> L["drain"]) built from the culvert parts, and the
taps (takes.taps -> L["taps"]) built from the crooked poles, sagging cables, hoses and drums. All parts are
kit_parts.py's, imported as AvalonSM.Liandri.B_* at scale 50 (world units) with zero=<name> and their MCDCX_ hulls.

    py tools/story_export.py <isl_layout.json> [out=<run>\isl_story.t3d] [pkg=AvalonSM.Liandri] [entry=stair|hatch]
                             [drain=1] [taps=1] [heightmap=<final bmp>]

As a library (export_mutator.py story=1): drain_actors(L) and tap_actors(L, ground) return T3D actor strings;
hole_notes(L) the terrain-hole rectangle the entrance needs.

The drain: the polyline (x, y, z_ground, z_invert per point, every ~half cell) is simplified (Douglas-Peucker, 1.2 m)
with the special spans kept as vertices: the junction room (768 long, centred on segments[2].s_uu), the sluice
gallery (segments[3] s0..s1) and the outfall (the last 128 UU). Between them: straight B_culvert pieces from vertex
to vertex (yaw, pitch to the invert fall, DrawScale3D X = length / 512); where the fall is steeper than 30 deg, a
B_culvert_drop + B_shaft_slab (a 3.6 m ladder shaft; deeper drops get two). At turns over 12 deg, B_culvert_bendP/N
elbows of 22.5 deg each (the residual up to 11 deg is overlapped, the pieces are hollow tubes so the overlap is a
small inner pleat). The entrance at the grate is B_drain_stair (17 risers, DrawScale3D Z = depth / 7.4 m, risers stay
<= 35 UU up to 11.8 m) or B_drain_hatch (a ladder shaft) when deeper or entry=hatch. The terrain above stays solid:
the entrance needs a visibility hole painted in the editor (see STORY_ASSETS.md).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

M = 50.0
PIVOTS = json.load(open(os.path.join(HERE, "Models", "glb", "kit_pivots.json")))
PKG = "AvalonSM.Liandri"
CULVERT_UU = 512.0           # B_culvert's length
BEND_DEG, BEND_A = 22.5, 4.0 * M
DROP_UU = 256.0              # B_culvert_drop's length (2.56 upper floor + 2.56 shaft)
DROP_MAX = 3.6 * M
MAX_PITCH = math.radians(30)
MIN_BEND = 12.0
STAIR_DEPTH, STAIR_MAX_Z = 7.4 * M, 1.6
GAL_L, GAL_W, JUN_L = 1536.0, 768.0, 768.0
OUTFALL_UU = 128.0
STEP = 37.0


def rot(v, yaw, pitch=0.0):
    """UE2 applies pitch, then yaw (Roll, Pitch, Yaw order); pitch positive = nose up"""
    x, y, z = v
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, z = x * cp - z * sp, x * sp + z * cp
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (x * cy - y * sy, x * sy + y * cy, z)


def actor(part, ox, oy, oz, yaw, pitch=0.0, sx=1.0, sy=1.0, sz=1.0, pkg=None, cull=0):
    """a StaticMeshActor of the part placed by its AUTHORED origin (ox, oy, oz) - kit_pivots.json gives the origin's
    offset from the mesh pivot (the bounds centre) in metres, turned with the actor and scaled with it"""
    pv = PIVOTS.get(part, {"dx": 0, "dy": 0})
    off = rot((-pv["dx"] * M * sx, -pv["dy"] * M * sy, 0.0), yaw, pitch)
    x, y, z = ox + off[0], oy + off[1], oz + off[2]
    r = "Rotation=(Pitch=%d,Yaw=%d)" % (int(round(math.degrees(pitch) * 65536 / 360)) % 65536, int(round(math.degrees(yaw) * 65536 / 360)) % 65536)
    s = "DrawScale3D=(X=%.4f,Y=%.4f,Z=%.4f)" % (sx, sy, sz)
    extra = "    CullDistance=%d\n" % cull if cull else ""
    return ("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s.%s'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    %s\n    %s\n%s"
            "    bStatic=True\nEnd Actor" % (pkg or PKG, part, x, y, z, r, s, extra))


# --- the drain ---------------------------------------------------------------------------------------------------
def arclen(path):
    s = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return s


def at_s(path, s, sv):
    """the point (x, y, zg, zi) at arclength sv by linear interpolation"""
    sv = max(0.0, min(s[-1], sv))
    for k in range(len(s) - 1):
        if s[k] <= sv <= s[k + 1]:
            t = (sv - s[k]) / max(1e-9, s[k + 1] - s[k])
            return [path[k][i] + (path[k + 1][i] - path[k][i]) * t for i in range(4)]
    return list(path[-1])


def douglas_peucker(pts, keep, tol):
    """indices to keep: the forced ones plus DP (XY only) between them"""
    keep = sorted(set(keep) | {0, len(pts) - 1})
    out = set(keep)

    def rec(i0, i1):
        if i1 - i0 < 2:
            return
        ax, ay = pts[i0][0], pts[i0][1]
        bx, by = pts[i1][0], pts[i1][1]
        L = math.hypot(bx - ax, by - ay) or 1e-9
        dmax, imax = -1, -1
        for i in range(i0 + 1, i1):
            d = abs((bx - ax) * (ay - pts[i][1]) - (ax - pts[i][0]) * (by - ay)) / L
            if d > dmax:
                dmax, imax = d, i
        if dmax > tol:
            out.add(imax)
            rec(i0, imax)
            rec(imax, i1)
    for a, b in zip(keep[:-1], keep[1:]):
        rec(a, b)
    return sorted(out)


def drain_actors(L, entry="stair", pkg=None, notes=None):
    """T3D actors for L['drain']; notes (a list) collects the warnings and the terrain-hole rectangle"""
    dr = L.get("drain")
    notes = notes if notes is not None else []
    if not dr or len(dr.get("path", [])) < 2:
        notes.append("no drain in the layout")
        return []
    path = dr["path"]
    s = arclen(path)
    total = s[-1]
    segs = {g["kind"]: g for g in dr["segments"]}
    jn = segs["junction_room"]["s_uu"]
    g0, g1 = segs["sluice_gallery"]["s0_uu"], segs["sluice_gallery"]["s1_uu"]
    specials = [("junction", jn - JUN_L / 2, jn + JUN_L / 2), ("gallery", g0, g1), ("outfall", total - OUTFALL_UU, total)]
    # the special spans as vertices (cut the dense path there), then simplify between them
    cuts = sorted({v for _, a, b in specials for v in (a, b) if 0 < v < total})
    dense, sd = [list(path[0])], [0.0]
    for k in range(1, len(path)):
        for c in cuts:
            if sd[-1] < c < s[k]:
                dense.append(at_s(path, s, c))
                sd.append(c)
        dense.append(list(path[k]))
        sd.append(s[k])
    forced = [i for i, sv in enumerate(sd) if any(abs(sv - c) < 0.5 for c in cuts)]
    keep = douglas_peucker(dense, forced, 1.2 * M)
    V = [dense[i] for i in keep]
    SV = [sd[i] for i in keep]

    def special_of(sa, sb):
        mid = (sa + sb) / 2
        for name, a, b in specials:
            if a - 0.5 <= mid <= b + 0.5:
                return name
        return None

    A = []
    cur = [V[0][0], V[0][1], V[0][3]]            # x, y, invert z
    heading = None
    n_straight = n_bend = n_drop = 0
    k = 0
    while k < len(V) - 1:
        nxt = V[k + 1]
        sp = special_of(SV[k], SV[k + 1])
        tx, ty = nxt[0], nxt[1]
        dxy = math.hypot(tx - cur[0], ty - cur[1])
        if dxy < 5:
            k += 1
            continue
        yaw = math.atan2(ty - cur[1], tx - cur[0])
        if sp is not None:
            # the room covers this whole span: one piece along the chord at the span's start invert
            end_k = k
            while end_k < len(V) - 1 and special_of(SV[end_k], SV[end_k + 1]) == sp:
                end_k += 1
            ex, ey = V[end_k][0], V[end_k][1]
            chord = math.hypot(ex - cur[0], ey - cur[1])
            yaw = math.atan2(ey - cur[1], ex - cur[0])
            if sp == "junction":
                A.append(actor("B_junction", cur[0], cur[1], cur[2], yaw, 0, chord / JUN_L, 1, 1, pkg))
            elif sp == "gallery":
                A.append(actor("B_gallery", cur[0], cur[1], cur[2], yaw, 0, chord / GAL_L, 1, 1, pkg))
                for i in range(4):
                    for side in (-1, 1):
                        px = 3.84 * M + i * 7.68 * M * (chord / GAL_L)
                        py = side * (GAL_W / 2 - 1.1 * M)
                        off = rot((px, py, 0), yaw)
                        A.append(actor("B_pillar", cur[0] + off[0], cur[1] + off[1], cur[2], yaw, 0, 1, 1, 1, pkg))
            else:
                mid = rot((chord / 2, 0, 0), yaw)
                A.append(actor("B_outfall", cur[0] + mid[0], cur[1] + mid[1], cur[2], yaw, 0, 1, 1, 1, pkg))
            cur = [ex, ey, cur[2]]
            heading = yaw
            k = end_k
            continue
        # bends where the heading turns
        if heading is not None:
            turn = math.degrees((yaw - heading + math.pi) % (2 * math.pi) - math.pi)
            if abs(turn) >= MIN_BEND:
                nb = max(1, int(round(abs(turn) / BEND_DEG)))
                for _ in range(nb):
                    part = "B_culvert_bendP" if turn > 0 else "B_culvert_bendN"
                    A.append(actor(part, cur[0], cur[1], cur[2], heading, 0, 1, 1, 1, pkg))
                    th = math.radians(BEND_DEG) * (1 if turn > 0 else -1)
                    ex = cur[0] + BEND_A * (math.cos(heading) + math.cos(heading + th))
                    ey = cur[1] + BEND_A * (math.sin(heading) + math.sin(heading + th))
                    cur = [ex, ey, cur[2]]
                    heading += th
                    n_bend += 1
                # skip vertices the elbows passed
                while k < len(V) - 2 and ((V[k + 1][0] - cur[0]) * math.cos(heading) + (V[k + 1][1] - cur[1]) * math.sin(heading)) < 1.0 * M \
                        and special_of(SV[k + 1], SV[k + 2]) is None:
                    k += 1
                nxt = V[k + 1]
                tx, ty = nxt[0], nxt[1]
                dxy = math.hypot(tx - cur[0], ty - cur[1])
                yaw = math.atan2(ty - cur[1], tx - cur[0])
        dz = nxt[3] - cur[2]
        if dz < -STEP and math.atan2(-dz, dxy) > MAX_PITCH:
            # too steep for a ramp: a drop shaft, then the lower culvert from its end at the lower invert
            drop = -dz
            nshaft = int(math.ceil(drop / DROP_MAX))
            for i in range(nshaft):
                d_i = drop / nshaft
                A.append(actor("B_culvert_drop", cur[0], cur[1], cur[2], yaw, 0, 1, 1, 1, pkg))
                ex, ey = cur[0] + DROP_UU * math.cos(yaw), cur[1] + DROP_UU * math.sin(yaw)
                A.append(actor("B_shaft_slab", cur[0] + 3.84 * M * math.cos(yaw), cur[1] + 3.84 * M * math.sin(yaw), cur[2] - d_i, yaw, 0, 1, 1, 1, pkg))
                cur = [ex, ey, cur[2] - d_i]
                n_drop += 1
            heading = yaw
            while k < len(V) - 2 and ((V[k + 1][0] - cur[0]) * math.cos(yaw) + (V[k + 1][1] - cur[1]) * math.sin(yaw)) < 1.0 * M \
                    and special_of(SV[k + 1], SV[k + 2]) is None:
                k += 1
            continue
        length = math.hypot(dxy, dz)
        pitch = math.atan2(dz, dxy)
        mid = rot((length / 2, 0, 0), yaw, pitch)
        A.append(actor("B_culvert", cur[0] + mid[0], cur[1] + mid[1], cur[2] + mid[2], yaw, pitch, length / CULVERT_UU * 1.01, 1, 1, pkg))
        n_straight += 1
        cur = [tx, ty, nxt[3]]
        heading = yaw
        k += 1
    # the entrance at the grate: the stair climbs back along -heading0 from the first invert point to the ground
    x0, y0, zg0, zi0 = path[0]
    yaw0 = math.atan2(path[1][1] - y0, path[1][0] - x0)
    depth = zg0 - zi0
    part = "B_drain_hatch" if (entry == "hatch" or depth / STAIR_DEPTH > STAIR_MAX_Z) else "B_drain_stair"
    if part == "B_drain_hatch" and entry != "hatch":
        notes.append("entrance: the grate is %.1f m deep (> %.1f m): the ladder hatch instead of the stair" % (depth / M, STAIR_DEPTH * STAIR_MAX_Z / M))
    A.append(actor(part, x0, y0, zi0, yaw0, 0, 1, 1, depth / STAIR_DEPTH, pkg))
    if part == "B_drain_stair":
        run = PIVOTS["B_drain_stair"]["run"] * M
        c = [rot((-run - 0.3 * M, sgn * 1.58 * M, 0), yaw0) for sgn in (-1, 1)] + [rot((0.3 * M, sgn * 1.58 * M, 0), yaw0) for sgn in (1, -1)]
        hole = [[round(x0 + p[0], 1), round(y0 + p[1], 1)] for p in c]
    else:
        c = [rot((sx * 1.73 * M, sy * 1.73 * M, 0), yaw0) for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
        hole = [[round(x0 + p[0], 1), round(y0 + p[1], 1)] for p in c]
    notes.append({"terrain_hole": hole, "entrance": part, "depth_uu": round(depth, 1), "top_z": round(zg0, 1),
                  "note": "paint this rectangle as a terrain visibility hole (UnrealEd terrain tool, visibility/hole mode); the terrain stays solid elsewhere"})
    notes.append("drain: %d straight culverts, %d elbows, %d drop shafts, junction, gallery + 8 pillars, outfall, %s; %d actors"
                 % (n_straight, n_bend, n_drop, part, len(A)))
    return A


# --- the taps ------------------------------------------------------------------------------------------------------
def tap_actors(L, ground=None, pkg=None, notes=None):
    """poles (B_pole_a/b/c by position hash), cables (B_sagcable per span and drop: X = length / 500, Z = sag /
    30 UU, pitched to the chord), hoses (B_hose per 10 m piece) and drums (B_drum) for every ok tap in L['taps']"""
    A = []
    notes = notes if notes is not None else []
    taps = L.get("taps") or []
    n_pole = n_cable = n_hose = n_drum = 0
    for t in taps:
        if not t.get("ok"):
            continue
        if t["style"] in ("sag_cable", "splice_cable"):
            for k, (x, y, g, h) in enumerate(t["poles"]):
                if k == 0 and t["style"] == "sag_cable" and t.get("from_line") is not None:
                    continue                                    # the hook is on the company's own line
                part = "B_pole_%s" % "abc"[int(abs(x * 7 + y * 13)) % 3]
                yaw = math.radians((abs(x * 3 + y * 5)) % 360)
                z = ground(x, y) if ground else g
                A.append(actor(part, x, y, z, yaw, 0, 1, 1, 1, pkg, cull=12000))
                n_pole += 1
            for sp in t.get("spans", []) + t.get("drops", []):
                a, b = sp["a"], sp["b"]
                dxy = math.hypot(b[0] - a[0], b[1] - a[1])
                if dxy < 20:
                    continue
                dz = b[2] - a[2]
                yaw = math.atan2(b[1] - a[1], b[0] - a[0])
                pitch = math.atan2(dz, dxy)
                length = math.hypot(dxy, dz)
                sag = max(0.2, sp.get("sag_m", 0.5)) * M
                A.append(actor("B_sagcable", a[0], a[1], a[2], yaw, pitch, length / 500.0, 1, sag / 30.0, pkg, cull=12000))
                n_cable += 1
        else:
            hose = t.get("hose") or []
            for a, b in zip(hose[:-1], hose[1:]):
                dxy = math.hypot(b[0] - a[0], b[1] - a[1])
                if dxy < 20:
                    continue
                yaw = math.atan2(b[1] - a[1], b[0] - a[0])
                za = (ground(a[0], a[1]) if ground else a[2] - 5)
                zb = (ground(b[0], b[1]) if ground else b[2] - 5)
                pitch = math.atan2(zb - za, dxy)
                A.append(actor("B_hose", a[0], a[1], za, yaw, pitch, math.hypot(dxy, zb - za) / 500.0, 1, 1, pkg, cull=9000))
                n_hose += 1
            for k, (x, y) in enumerate(t.get("drums", [])):
                if ground:
                    z = ground(x, y)
                else:
                    near = min(hose, key=lambda p: math.hypot(p[0] - x, p[1] - y)) if hose else None
                    z = near[2] - 5 if near else 0.0
                A.append(actor("B_drum", x, y, z, math.radians((k * 47) % 360), 0, 1, 1, 1, pkg, cull=9000))
                n_drum += 1
    notes.append("taps: %d poles, %d cables, %d hose pieces, %d drums; %d actors" % (n_pole, n_cable, n_hose, n_drum, len(A)))
    return A


def ground_fn(heightmap):
    """the final G16 BMP -> ground(x, y) in the TutA frame (export_mutator's mapping)"""
    import struct
    import numpy as np
    raw = open(heightmap, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w_, h_ = struct.unpack_from("<ii", raw, 18)
    H_ = np.frombuffer(raw[off:off + w_ * abs(h_) * 2], dtype="<u2").reshape(abs(h_), w_).astype(float)
    if h_ > 0:
        H_ = H_[::-1]
    LOC_ = (-14487.546875, 4835.837891, -131.845703)

    def ground(x, y):
        fi, fj = (x - LOC_[0]) / 512.0 + 64, (y - LOC_[1]) / 512.0 + 64
        i0, j0 = int(math.floor(fi)), int(math.floor(fj))
        if not (0 <= i0 < 127 and 0 <= j0 < 127):
            return -4967.0
        ti, tj = fi - i0, fj - j0
        hv = (H_[j0, i0] * (1 - ti) * (1 - tj) + H_[j0, i0 + 1] * ti * (1 - tj) + H_[j0 + 1, i0] * (1 - ti) * tj + H_[j0 + 1, i0 + 1] * ti * tj)
        return LOC_[2] + (hv - 32768) * 0.5
    return ground


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if "=" not in a]
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    if not pos:
        raise SystemExit(__doc__)
    L = json.load(open(pos[0]))
    run = os.path.dirname(os.path.abspath(pos[0]))
    out = o.get("out", os.path.join(run, "isl_story.t3d"))
    g = ground_fn(o["heightmap"]) if o.get("heightmap") else None
    notes = []
    A = []
    if o.get("drain", "1") != "0":
        A += drain_actors(L, o.get("entry", "stair"), o.get("pkg"), notes)
    if o.get("taps", "1") != "0":
        A += tap_actors(L, g, o.get("pkg"), notes)
    open(out, "w").write("Begin Map\n" + "\n".join(A) + "\nEnd Map\n")
    json.dump(notes, open(out[:-4] + "_notes.json", "w"), indent=1)
    for n in notes:
        print(n if isinstance(n, str) else json.dumps(n))
    print(len(A), "actors ->", out)
