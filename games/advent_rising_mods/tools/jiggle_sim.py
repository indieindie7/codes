"""Reference soft-body simulation for the Seeker's flesh (JIGGLE.md, phase A.4), headless Blender.

    blender -b --python tools/jiggle_sim.py -- <jiggle dir> [clip ...]

Reads <jiggle dir>/regions.json (tools/jiggle_rig.py) and anim_<clip>.npz (the mesh skinned by the
clip, every frame), builds the mesh in Blender (UE mesh space -Y up -> Blender Z up, 1 unit =
2 cm), drives it with one shape key per frame, and runs Blender's soft body on it with a goal:
armour points and every point outside the jiggle regions have goal 1 (they follow the clip
rigidly, pinned to their bones), region points a goal that falls with their jiggle weight (down
to GOAL_MIN at a region's centre), so they lag and overshoot the clip under gravity and the body's
own motion. A pre-roll settles the body in the clip's first frame; looping clips run twice and
the second pass is kept. Writes sim_<clip>.npz: sim (frames x points x 3, UE mesh space), goal
(the clip's own positions), rate.
"""
import json
import os
import sys

import bpy
import numpy as np

SCALE = 0.02          # UE units -> metres
GOAL_MIN = 0.5        # the goal at a region's centre (0 = free, 1 = pinned); 0.12 gave mush that lagged a metre behind a punch
PREROLL = 20
LOOPED = {"walk_f", "run", "idle_active", "walk_b", "walk_l", "walk_r"}


def to_blender(v):
    return np.stack([v[..., 0] * SCALE, v[..., 2] * SCALE, -v[..., 1] * SCALE], axis=-1)


def from_blender(v):
    return np.stack([v[..., 0] / SCALE, -v[..., 2] / SCALE, v[..., 1] / SCALE], axis=-1)


def run(jdir, clips):
    reg = json.load(open(os.path.join(jdir, "regions.json")))
    # the faces from the psk
    import struct
    d = open(reg["psk"], "rb").read()
    o, ch = 0, {}
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        size, count = struct.unpack_from("<ii", d, o + 24)
        ch[cid] = (d[o + 32:o + 32 + size * count], size, count)
        o += 32 + size * count
    b, s, n = ch["VTXW0000"]
    wedge_pt = [struct.unpack_from("<H", b, s * i)[0] for i in range(n)]
    b, s, n = ch["FACE0000"]
    faces = [tuple(wedge_pt[w] for w in struct.unpack_from("<3H", b, s * i)) for i in range(n)]
    faces = [f for f in faces if len(set(f)) == 3]
    jw = {}
    for r in reg["regions"]:
        for i, w in r["verts"]:
            jw[i] = max(jw.get(i, 0.0), w)
    for clip in clips:
        a = np.load(os.path.join(jdir, "anim_%s.npz" % clip))
        verts = a["verts"].astype(np.float64)
        rate = float(a["rate"])
        nf = len(verts)
        loops = 2 if clip.lower() in LOOPED else 1
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
        sc = bpy.context.scene
        sc.render.fps = int(round(rate))
        sc.frame_start = 1
        total = PREROLL + loops * nf
        sc.frame_end = total
        me = bpy.data.meshes.new("seeker")
        bv = to_blender(verts)
        me.from_pydata([tuple(p) for p in bv[0]], [], faces)
        me.update()
        obj = bpy.data.objects.new("seeker", me)
        sc.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        # goal weights
        vg = obj.vertex_groups.new(name="goal")
        for i in range(len(me.vertices)):
            w = jw.get(i, 0.0)
            vg.add([i], 1.0 - (1.0 - GOAL_MIN) * min(1.0, w / 0.6), "REPLACE")
        # shape keys: the Basis is frame 0; key f is frame f, on only at its own frame
        obj.shape_key_add(name="Basis", from_mix=False)
        schedule = []     # (scene frame, clip frame)
        for k in range(PREROLL):
            schedule.append((1 + k, 0))
        for l in range(loops):
            for f in range(nf):
                schedule.append((1 + PREROLL + l * nf + f, f))
        keys = []
        for f in range(nf):
            sk = obj.shape_key_add(name="f%d" % f, from_mix=False)
            sk.interpolation = "KEY_LINEAR"
            co = bv[f].astype(np.float32).ravel()
            sk.data.foreach_set("co", co)
            keys.append(sk)
        for f, sk in enumerate(keys):
            frames_on = [sf for sf, cf in schedule if cf == f]
            if not frames_on:
                continue
            if f == 0:
                # the basis is frame 0 already: key 0 stays off
                continue
            sk.value = 0.0
            for sf in frames_on:
                sk.keyframe_insert("value", frame=sf - 1)
                sk.value = 1.0
                sk.keyframe_insert("value", frame=sf)
                sk.value = 0.0
                sk.keyframe_insert("value", frame=sf + 1)
        # the soft body
        mod = obj.modifiers.new("SB", "SOFT_BODY")
        sb = mod.settings
        sb.mass = 1.0
        sb.friction = 0.5
        sb.speed = 1.0
        sb.use_goal = True
        sb.vertex_group_goal = "goal"
        sb.goal_default = 1.0
        sb.goal_min = 0.0
        sb.goal_max = 1.0
        sb.goal_spring = 0.5
        sb.goal_friction = 4.0
        sb.use_edges = True
        sb.pull = 0.7
        sb.push = 0.7
        sb.damping = 1.0
        sb.bend = 0.4
        sb.use_stiff_quads = False
        sb.use_self_collision = False
        sb.collision_type = "MANUAL"
        sb.step_min = 4
        sb.step_max = 60
        sb.error_threshold = 0.02
        mod.point_cache.frame_start = 1
        mod.point_cache.frame_end = total
        dg = bpy.context.evaluated_depsgraph_get()
        sim = np.zeros((nf, len(me.vertices), 3))
        goal = np.zeros_like(sim)
        maxdev = 0.0
        for sf, cf in schedule:
            sc.frame_set(sf)
            dg = bpy.context.evaluated_depsgraph_get()
            ev = obj.evaluated_get(dg)
            co = np.zeros(len(ev.data.vertices) * 3, dtype=np.float32)
            ev.data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3).astype(np.float64)
            if sf > PREROLL + (loops - 1) * nf:
                sim[cf] = from_blender(co)
                goal[cf] = verts[cf]
                maxdev = max(maxdev, float(np.max(np.linalg.norm(sim[cf] - verts[cf], axis=1))))
        np.savez_compressed(os.path.join(jdir, "sim_%s.npz" % clip), sim=sim.astype(np.float32), goal=goal.astype(np.float32), rate=rate)
        dev = np.linalg.norm(sim - goal, axis=2)
        jidx = np.array(sorted(jw))
        print("JIGGLE_SIM %s: %d frames (%d simulated), deviation from the clip: all points mean %.2f max %.2f, region points mean %.2f max %.2f units" % (clip, nf, total, dev.mean(), dev.max(), dev[:, jidx].mean(), dev[:, jidx].max()))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    jdir = args[0]
    clips = args[1:] or [os.path.basename(f)[5:-4] for f in sorted(os.listdir(jdir)) if f.startswith("anim_") and f.endswith(".npz")]
    run(jdir, clips)
