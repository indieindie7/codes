# Character creation pipeline (concept image -> textured low-poly game mesh)

Internal working doc, state of 2026-10-05. Written so another chat can pick the pipeline up without
the history. Benchmark character: the green "hardsuit" (`Documents\U2Golem\hardsuit\hf`).
All scripts named here are in this folder unless a path is given.

## The pipeline in one table

| # | Stage | Tool | Time | GPU | Status |
|---|-------|------|------|-----|--------|
| 1 | Concept image | Sana (`Downloads\sana-diffusers\generate.py`, has `--negative`) | 1 min | yes | works |
| 2 | A-pose reference views | StdGEN (`Tools\StdGEN\stdgen.sh <img> <out> "apose multiview"`) or a drawn turnaround sheet | 5 min | yes | works |
| 3 | High-poly shape | Hunyuan3D-2mv (`Tools\Hunyuan3D-2\img2shape_mv.py ... octree=384 faces=0`) | 6 min | 6 GB | works |
| 4 | Check shape against the views | `confirm_views.py` (silhouette IoU per view, flags < 0.75) | 10 s | no | works |
| 5 | Paint | Hunyuan3D-Paint (`Tools\Hunyuan3D-2\paint_mesh.py`) with front + back + side references | 3-4 min | 7 GB | works |
| 6 | Colour-correct the paint to the references | `project_views.py` + `retopo_bake.py extra=Trust` + `blend_paint.py mix=0` | 2 min | no | works |
| 7 | Low-poly + bakes | `retopo_bake.py method=decimate tris=3000` (colour, AO, normal; diffuse = colour x AO) | 1 min | no | works |
| 8 | Separate head (optional) | Hunyuan on a head crop + `attach_head.py` | 10 min | yes | works |
| 9 | Rig onto a game skeleton | `rig_to_skeleton.py` + `blend2psk.py` + `psk_keep_bones.py` | 2 min | no | works |
| 10 | Import as a wardrobe outfit | `u2import.py` (drives the real mouse) + `U2Wardrobe.ini` | 5 min | game | works |
| 11 | Normal map + PBR highlights in game | `make_pbr_map.py` + the d3d8to9 fork's `pbr=` rule | 1 min | game | works, one level tested |

Stages 8-11 were added on 2026-10-05; see "From the low-poly into the game" below. First character through
the whole pipeline: wardrobe outfit "Dalton Peacekeeper" (`Documents\U2Golem\dalton_pk`).

## Update, evening of 2026-10-04: the route for a character with ONE concept image

Decided with the user on Dalton (peacekeeper concept `design-refs\dalton_peacekeeper\dalton_p1_s23.png`):
**skip stage 2 and StdGEN entirely.** StdGEN redraws the character onto its own body template and lost the
sash, the big pauldron and the face. Sana "five-view sheets" from the text prompt are new characters, not
turns of the concept.

    img2shape.py <concept.png> high.glb full octree=384 faces=0        # 517k faces, 3 min, 6 GB
    paint_mesh.py high.glb paint.glb high_input.png faces=40000        # the concept as the only reference, 3 min
    turnaround.py paint.glb turn angles=0,45,90,135,180,225,270,315    # reference views from the model (CPU)
    project_views.py high.glb painted front=high_input.png subdiv=0    # reference colours + Trust
    retopo_bake.py (blend painted) A method=decimate tris=3000 extra=Trust cpu=1
    retopo_bake.py A_hp high=paint.glb low=A.glb cage=0.02 cpu=1
    blend_paint.py A_albedo.png A_trust.png A_hp_albedo.png match_in.png mix=0
    retopo_bake.py (blend painted) A_match low=A.glb cage=0.02 albedo=match_in.png cpu=1

Result: `Documents\U2Golem\dalton_pk\direct\dalton_c_A_match.*`. Caveats: the model keeps the concept's
pose (relaxed, arms down, head tilted), not an A-pose; an A-pose sheet "without heavy hallucination" is
still an open wish. `cpu=1` makes every preview render on the CPU, so the bakes can run while a game has the GPU.

## Update, night of 2026-10-04: FLUX Kontext makes the reference views (best route so far)

An image-EDITING model redraws the concept in a new pose or from a new angle and keeps the character,
which a text-to-image model (Sana) cannot do.

    cd Documents\Tools\flux-kontext        (run with Downloads\sana-diffusers\venv\Scripts\python)
    kontext_edit.py concept.png tpose_front.png "Change the pose of this man: he now stands in a T-pose ..." --steps 24 --guidance 4
    kontext_edit.py tpose_front.png tpose_back.png "Rotate the camera 180 degrees and show this character from directly behind ..."
    (same for 45 and 135 degrees; always edit FROM tpose_front so the views agree)
    img2shape_mv.py high.glb front=tpose_front.png back=tpose_back.png octree=384 faces=0
    paint_mesh.py high.glb paint.glb front back 45 135 faces=40000
    ... then the low-poly / bake / colour-match commands above.

- About 3 minutes per image, peak 10 GB VRAM. Weak instructions ("stand in an A-pose") return a copy of the
  input; say exactly what changes.
- It cannot draw a clean T-pose side profile (twists the body). Leave the side out: front + back is enough
  for the shape.
- **Memory:** a run froze the PC once (32 GB RAM). The script now loads the text encoder and the model one
  after the other and refuses to start when RAM is short. Never run it next to another heavy job.
- Result: `Documents\U2Golem\dalton_pk\tpose\dalton_t_A_match.*`.

## From the low-poly into the game (stages 8-11, done on Dalton Peacekeeper 2026-10-05)

### 8. A separate head (optional)

The body model's face is a few hundred pixels. Generate the head on its own from a crop of the concept
(`img2shape.py` + `paint_mesh.py` on the crop: a bust with hat and collar), then:

    blender -b --python attach_head.py -- out body=body_paint.glb head=bust_paint.glb body_high=body_high.glb head_high=bust_high.glb collar=0.80 depth=1.5 scale=1.05

It scales the bust by HAT WIDTH (the collar hides the jaw, so heights are unusable), removes the body's
head column and keeps the bust's collar so the collar hides the join. Then stage 7 on `out_high.glb` /
`out_paint.glb` (Dalton: 3,200 triangles, `tpose\dalton_th_game.*`).

### 9. Rig

The mesh must be in a T-pose (the FLUX Kontext route). The skeleton is borrowed from a UT2004 character
that the importer already handles; the marines' animations then just work.

    blender -b --python psk2blend.py -- MercDonor.blend MercMaleD.psk
    blender -b MercDonor.blend --python rig_to_skeleton.py -- DaltonPK.blend low=dalton_th_game.glb test=1 smooth=4 cloth=0.6 slim=1.2
    blender -b DaltonPK.blend --python blend2psk.py -- DaltonPK_raw.psk
    python psk_keep_bones.py DaltonPK_raw.psk MercMaleD.psk DaltonPK.psk

- `psk_keep_bones.py` is REQUIRED. Blender does not keep bone roll, so the exported bones have other axes;
  the game's animations then lean the body about 45 degrees and splay the limbs. The step puts the donor's
  own bone records back.
- Do not rig on the game's own Dalton skeleton (gem2blend): same splayed limbs, and no fix for it.
- `rig_to_skeleton.py` takes weights from the nearest point on the donor's surface PER POINT (per corner
  tears the mesh along UV seams). `cloth=` sends skirts and tabards to the pelvis so they do not split
  between the legs; `slim=` narrows the trunk toward the donor's body. Look at `_rest.png` / `_pose.png`.
- Known limits: the fingers move as one block; the pose matcher wants hands and feet clearly visible.

### 10. Import and wardrobe

    (move <game>\Meshes\DaltonPK away first: the importer refuses when the gem already exists)
    set PYTHONUTF8=1
    py -3.13 u2import.py DaltonPK --psk DaltonPK.psk --tex DaltonPKSkin.png

`DaltonPKSkin.png` is the `_diffuse` bake (albedo x AO). **The importer drives the real mouse in Golem
Studio: ask the user first and tell the other chat.** Then in `System\U2Wardrobe.ini` add `Labels=<name>`,
`Meshes=Glm<Name>G.<Name>` and `CalMeshes=...` (height calibration). The F6 portrait atlas holds 8 pictures
and is full.

Looking at the result (U2Pilot, `scripts\dalton_pk_dummy.txt`): use `hub dummy Glm<Name>G.<Name> <yaw> <dist>`,
an armed, lit marine. `wardrobe photo` shows an UNARMED pawn standing at ease with its hands behind the back,
which looks like broken arms on a wide character. In scripts use `wardrobe view` after `wear`, not
`behindview 1`. The big gun "slabs" in the debug behind view are most likely the game's first-person weapon
overlay (read from the code, not tested), not a fault of the outfit.

### 11. Normal map and PBR

Unreal II has no normal maps; the d3d8to9 fork does it in the wrapper (branch gi-cascades, commit 6f37ee7,
worktree `Documents\github\d3d8to9-gi`, owned by the Advent chat: copy from it, never edit or commit there).

    python make_pbr_map.py dalton_th_game_normal.png dalton_th_game_albedo.png DaltonPK_pbr.dds preview=check.png

Install in `<game>\System`: the fork's `d3d8.dll`, `U2Shaders\char_pbr.hlsl`, the `.dds` in `U2Shaders\`,
and as the first line under `[U2Shaders]` in `U2Shaders.ini`:

    pbr=c99a529e DaltonPK_pbr.dds 1.6 1.5        (texture hash, map, highlight strength, normal strength)

- The hash is the fork's hash of the skin texture: run once with `log=2` and find the skin in
  `U2Shaders\dump`. It changes when the skin changes. The rule is read at startup only.
- The baked normal's green channel must be flipped for the game (the tool does it). Without it relief reads
  as dents; `pbrdebug=1..4` shows the channels.
- Roughness and metal are guessed from the albedo's colours (gold trim = metal, white plates = smooth,
  cloth = rough). They are guesses; tune the numbers per character.
- Do not put a `surface=` rule on the same hash. Tested only in HoverTest under one light.
- Backups made: `d3d8.dll.before-pbr`, `U2Shaders.ini.before-pbr`, `U2Wardrobe.ini.before-daltonpk`.

## Reference views (stage 2)

Wanted set, agreed with the user: **front (0), 45, side (90), 135, back (180)**, plus the mirrored
side where available. More angles = better paint on the corners.

- StdGEN gives six views at 0, 45, 90, 180, 270, 315 degrees (1024 px frames, figure about 55% of the
  height) from ONE concept image. It has no 135 / 225 view.
- A drawn turnaround sheet (Sana, text prompt) gives front / side / back; `split_sheet.py` cuts it.
- Hunyuan's "left" input is the view from the camera at -X. A sheet's side view usually needs mirroring;
  `confirm_views.py` tells which way is right (hardsuit: IoU 0.81 mirrored vs 0.61 not).
- Sana gotcha: writing "no X" in a prompt makes X appear. Use `--negative`.

## Shape (stage 3)

    cd Documents\Tools\Hunyuan3D-2
    venv\Scripts\python img2shape_mv.py out.glb front=f.png back=b.png left=l.png octree=384 faces=0

**The biggest single finding:** the script used to reduce the mesh to 20,000 faces at octree 256. That, not
the low-poly step, was why everything downstream looked bad. `octree=384 faces=0` gives about 290,000 faces
with real panel lines. Always bake from this mesh.

## Paint (stages 5-6)

    venv\Scripts\python paint_mesh.py high.glb painted.glb front.png back.png side.png faces=40000

- Reduces the mesh to 40,000 faces, unwraps it, generates six consistent views and bakes them.
- The references are style guides, not views to copy: a detail seen only in the side drawing can land on
  the front (hardsuit: the visor band). The user likes the result with the side included.
- It drifts in colour (orange -> pale yellow, grey -> white). `blend_paint.py mix=0` corrects that: it learns
  the shift per colour cluster where the drawings clearly show the surface and applies it everywhere.
- `blend_paint.py` (mix=1) can also put the drawings' own pixels back on front/back. It keeps ink lines but
  looks rougher; not the chosen look.
- Install notes (no compiler needed): see `hunyuan\README.md`. Weights 13.5 GB in
  `~\.cache\hy3dgen\tencent\Hunyuan3D-2`.

Our own projection paint (`project_views.py`) is now only the colour reference for stage 6. What it does:
orthographic projection of front / back / side (+ mirrored side) into vertex colours, with the drawings'
outline ink rejected, thin parts (hands) kept on front/back colour, and a "Trust" attribute (1 = front/back
saw the surface squarely). It cannot invent what no drawing shows; Hunyuan3D-Paint can.

## Low-poly and bakes (stage 7)

    blender -b painted_high.blend --python retopo_bake.py -- out method=decimate tris=3000 size=2048
    blender -b --python retopo_bake.py -- out high=painted.glb low=lowpoly.glb cage=0.02 [albedo=corrected.png]

Decided by the user: **Blender's Decimate on the fine high-poly ("A")**. Outputs `_albedo`, `_ao`, `_normal`,
`_diffuse` (albedo x AO, for Unreal II which has no normal maps), `.glb`, `.blend` and a preview sheet
(textured row + wireframe row).

Tried and dropped, with the reason:

| Method | Verdict |
|--------|---------|
| MeshAnything V2 | guesses a mesh for the whole character: holes, edges follow nothing |
| Instant Meshes, DeepMesh | broke thin shells / did not reduce; deleted |
| Tube retopo on the high-poly (`retopo_bake.py method=tube`) | clean loops, but loses armour shapes |
| Modelling from the sheet (`sheet_model.py`, Noggi/Aka method) | clean, exact front outline, but boxy in 3/4; dropped by the user |
| k-means flat-colour clean-up (`flatten_bake.py`) | caused the camouflage blotches |

## The hardsuit commands, end to end

    T=Documents/U2Golem/hardsuit/hf
    img2shape_mv.py $T/hs_high.glb front=s17_front.png back=s17_back.png left=s17_side_mirror.png octree=384 faces=0
    paint_mesh.py $T/hs_high.glb $T/paint/hs_paint3.glb front back side faces=40000
    project_views.py $T/hs_high.glb $T/hs_painted2 front= side= back= subdiv=0          # reference colours + Trust
    retopo_bake.py (blend hs_painted2) $T/hs_dec2 method=decimate tris=3000              # the low-poly "A"
    retopo_bake.py (blend hs_painted2) $T/paint/hs_A_proj low=hs_dec2.glb cage=0.02 extra=Trust
    retopo_bake.py $T/paint/hs_A_hp3 high=paint/hs_paint3.glb low=hs_dec2.glb cage=0.02
    blend_paint.py hs_A_proj_albedo.png hs_A_proj_trust.png hs_A_hp3_albedo.png match3_in.png mix=0
    retopo_bake.py (blend hs_painted2) $T/paint/hs_A_match3 low=hs_dec2.glb cage=0.02 albedo=match3_in.png

Result the user approved: `paint/hs_A_match3.*` (3,000 triangles, 2048 textures).

## Gotchas

- Blender is `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`; system Python has no PIL (use
  `Tools\Hunyuan3D-2\venv\Scripts\python.exe` for image scripts).
- Joining meshes whose UV layers have different names keeps two layers and the bake goes black.
- An open shell (a hand cut at the wrist) can come out inside-out; check normals before baking.
- Bakes from an identical surface need a tiny cage (0.003 of height); from a reduced one, 0.02.
- YouTube transcripts: see the memory note `video-watch-queue` (grab the player's caption request; no playback).

## GPU etiquette on this PC (12 GB card, shared)

One heavy GPU job at a time. Before starting one, message the other active chat ("GPU: <job>, <minutes>,
<VRAM>"), wait if it is mid-job, and send "GPU free" after. Never start a game or UnrealEd while another
chat's D3D app is starting (device-lost crashes). While the user is playing a game: no GPU jobs at all.

## Open items

- Dalton Peacekeeper: the single big pauldron came out as a matching pair; fingers move as a block; PBR values
  are guesses and tested in one level; no first-person check of the outfit yet.
- 135-degree reference view: no generator for it yet (see "Reference views").
- Details that exist only in the side drawing (elbow disc, pauldron face) are not reproduced.
- UT2004 / UT3 extracts and anything derived from them stay private: never upload.
