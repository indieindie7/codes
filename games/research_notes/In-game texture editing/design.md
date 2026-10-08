# In-game texture editing for Unreal II (d3d8 fork) - design

Status: research and design only (2026-10-08). Nothing built, nothing run. Sources read:
`d3d8to9-gi/source/u2shaders.hpp` (8.1k lines), `d3d8to9_device.cpp` (draw hooks), `U2GM/README.md`,
memory notes u2testhub-project, u2-texture-upscale-todo, u2gm-project, and the read-only
`System\U2Shaders\dump\seen.txt` from earlier runs.

Goal, three levels:
1. **Adjust** the texture under the mouse (brightness, contrast, hue, saturation, sharpness), live, saved as a replacement.
2. **Paint on the flat image** in a GM-panel canvas; the world updates live.
3. **Paint on world surfaces** (screen pixel -> texel).

---

## 0. What the fork already has (the pieces this builds on)

| Piece | Where | What it gives us |
|---|---|---|
| Texture identity | `Hash()` ~l.417 | FNV-1a over the first 16 KB of mip 0, seeded with `W ^ (H<<12)`. Cached once per game texture in `Direct3DTexture8::U2Hash` (d3d8to9.hpp:242) on first draw (`Known()`); `0xFFFFFFFF` = unreadable (default-pool/dynamic textures). |
| Per-draw stage tracking | `U2Stages[0..3]` in the device | Each draw knows the wrapper (hence hash) on stages 0-3. `DrawKinds`/`Seen` are logging tables (`seen.txt`: hash, size, format, draw count). |
| Replacement | `Replacement()` ~l.783, swap in `Direct3DDevice8::U2Begin`, restore in `U2After` | Per draw, stages 0-3: if a hash has an entry in `Replacements`, our texture is `SetTexture`'d for that one draw and the game's is put back after. The game never sees ours. Entries are made lazily on first draw (`Tried`). |
| `replace=HASH file.dds` | `LoadDDS()` | 32-bit BGRA or DXT1/3/5 with the file's own mips, `D3DPOOL_MANAGED`. |
| `texgrade=HASH lift desat r g b` | `GradeCopy()` | **Already a level-1 prototype**: an in-memory graded copy of the game's own texture, 32-bit per pixel, DXT by grading the block endpoints (with DXT1 order/transparency fix-up). Nothing touches disk. |
| Live reload | `ReloadPost`/`ReloadRules` ~l.7490/7674 | `U2Shaders.ini` is re-read when its time changes (every 10 frames); all replacements are dropped and remade on next draw. So editing a `texgrade=` line in the ini is already "live", just coarse (every rule and shader is dropped). |
| Redraw-the-same-geometry pattern | `MaskBegin/MaskEnd` (shotmask) ~l.3676, `GlossBegin` | After the game's draw, the same Draw*Primitive is issued again with our pixel shader into our own screen-sized target, **with the game's depth surface still bound** (Z test LESSEQUAL, Z write off). This is exactly an ID/UV pass. Hooked in all three draw paths of `d3d8to9_device.cpp` (l.1430-1440 etc.). |
| Readback | `MaskSave` | MSAA resolve via `StretchRect` to a plain RT, then `GetRenderTargetData` -> sysmem -> `LockRect`. |
| Scene view | `GmCaptureView`/`GmTakeView`, `GmMouseRay` | View/projection of the scene, inverse VP, the mouse ray -> "gm ray". |
| ImGui panel | `GmPanelDraw`, ImGui 1.92.9b, dx9 backend | Drawn at Present after the HUD; `ImTextureID` is an `IDirect3DTexture9*`, so `ImGui::Image` can show any D3D9 texture directly. |
| Depth as texture | INTZ swap (`DepthFor`) | Only when gi/ssao is on; not needed here (the redraw pattern uses the bound depth surface). |
| DDS writer | `SaveDDS()` | Top mip only, 32-bit or raw DXT. Needs a mip-chain variant for saving edits. |

Facts from `seen.txt` (168 textures on the logged maps): DXT5 81, A8R8G8B8 53, DXT1 22, DXT3 12; sizes up to
1024x1024 (14 of them). No P8 reaches D3D (the engine converts palettised textures before upload).
`Unreal2.exe` is **not** large-address-aware (PE characteristics 0x10F): 2 GB user address space.

Two things the hash scheme implies:
- Textures that agree in their first 16 KB (for a 1024^2 DXT1 that is only the top 1/32 of the image) and size
  share a hash. Edits apply to all of them. Rare, but the panel should show "N textures share this hash" when the
  `Seen` map ever records two different wrappers for one hash.
- Replacements key on the **original** hash and the cached `U2Hash` never changes, so editing can never "lose" a
  texture: the edited copy is ours, the game's texture is never written.

---

## 1. Picking: "the texture under the mouse"

### Options

| Option | How | Cost | Robustness |
|---|---|---|---|
| **A. ID pass (recommended)** | On the pick frame, after each on-screen game draw, redraw it (MaskBegin pattern) into an A8R8G8B8 target with a tiny ps_2_0 that outputs a 24-bit **draw serial** in RGB. Scissor test on, rect = the cursor pixel (or the brush rect). CPU keeps a table serial -> {hash on stages 0-3, blend/alpha-test state, address modes, texture transform flags, FVF}. Read back one pixel. | One frame with every draw issued twice. Fill cost ~0 (1 pixel). Vertex cost: a few hundred extra draw calls, est. 0.5-2 ms, only on the click frame. One `GetRenderTargetData` of a 1x1 copy (via `StretchRect` of the 1x1 rect into a 1x1 RT). | Topmost visible draw wins automatically: later draws that pass the depth test overwrite the serial. Survives Unreal II's mid-frame depth clears (sky box, first-person weapon), because each redraw is tested against the depth that is bound at that moment, exactly like the game draw. Works with MSAA (target uses the depth's multisample type, like MaskRT). |
| B. Occlusion query per draw | Redraw each draw scissored to the cursor pixel inside an `IDirect3DQuery9` (OCCLUSION); the last draw with count > 0 is topmost. | Hundreds of queries, results next frame. | Same visibility logic as A, but no colour target needed. Gives the whole **stack** under the cursor (every draw that touched the pixel), which A does not. |
| C. Stencil | Increment stencil per draw... | Needs a stencil-capable depth format the game owns; Unreal II's depth may have no stencil. | Fragile. Rejected. |
| D. CPU ray cast | Use the vertex-buffer shadow copies (`U2Shadow`, lmcapture) + world/view transforms; intersect the mouse ray. | Needs CPU copies of every buffer every frame. | Exact barycentrics, but heavy and duplicates the GPU. Rejected for picking; possible later for UV-space painting (see 5c). |

**Details that matter for A:**
- D3D8 has no scissor rect, so the game never uses it: the layer may enable `D3DRS_SCISSORTESTENABLE` and set the
  rect freely during the redraw (restore after).
- **Alpha-tested draws** (grates, foliage, the Avalon catwalk grating): the ID shader must sample s0 and return the
  texture alpha in `.a`, with the game's ALPHATESTENABLE/ALPHAREF left as they are. Otherwise a grate's holes pick
  the grate. So the shader is `return float4(serialRGB, tex2D(s0,uv).a * diffuse.a)` for alpha-tested draws.
- **Non-depth-writing draws** (decals, particles, blood, glass): drawn into the ID target too, so a decal is
  pickable; the panel then offers "pick through" which re-runs the pass ignoring ZWRITE-off draws. With option B
  folded in (one query per redraw in the same frame) the panel can list the whole stack: decal, wall texture,
  lightmap (stage 1), detail texture.
- Skip offscreen draws (`Offscreen(Dev)`: shadow maps, mirrors) and XYZRHW draws (HUD).
- Readback latency: issue the pass on frame N, read on frame N+1 (no extra stall needed; `GetRenderTargetData`
  of a 1x1 surface is tiny).

**Result shown in the panel:** hash, size, format, mip count, stage, draws-per-frame from `Seen`, a thumbnail
(`ImGui::Image` of the game texture itself), and a "show uses" toggle that tints every draw of that hash for a
moment (the existing `tint=` path, made live).

---

## 2. Live replacement: updating a texture's pixels

### Can the layer update a D3D9 texture in place? Yes, three ways:

1. **`D3DPOOL_MANAGED` + `LockRect` + `AddDirtyRect`** - simplest (what `LoadDDS`/`GradeCopy` already do). Costs a
   system-memory copy **inside the 2 GB process** for every level.
2. **`D3DPOOL_SYSTEMMEM` staging texture + `UpdateTexture` into a `D3DPOOL_DEFAULT` texture** - recommended for
   painting. `AddDirtyRect` on the staging texture makes `UpdateTexture` send only the stroke's rectangle. If the
   DEFAULT texture is created with `D3DUSAGE_AUTOGENMIPMAP`, D3D9 updates level 0 only and regenerates the
   sub-levels (check `CheckDeviceFormat(..., D3DUSAGE_AUTOGENMIPMAP, ...)`; fall back to our own box filter over
   the dirty rect, which is ~20 lines and cheap). DEFAULT textures must be released in `OnLost` and remade after
   Reset (the panel already does this for ImGui).
3. **Render target as the replacement** - the source texture is drawn through a pixel shader into a
   `D3DUSAGE_RENDERTARGET | D3DUSAGE_AUTOGENMIPMAP` A8R8G8B8 texture, which is then the replacement. Best for
   level 1 (see 3).

### DXT

- Editing in place in DXT is only exact for **affine colour transforms** (brightness, contrast, saturation, hue
  rotation, tint are all `rgb' = M*rgb + b`): grading the two endpoints grades every interpolated texel too, up
  to 565 rounding and clipping. That is why `texgrade=` works on DXT. Sharpness, curves and painting are not affine.
- For everything else: **decompress to A8R8G8B8, edit, keep the uncompressed copy as the replacement.** The
  cheapest decompressor is the GPU: draw the DXT texture into an A8R8G8B8 render target (point sampling, 1:1) and
  `GetRenderTargetData` once. No CPU DXT decoder needed (one is ~60 lines if wanted).
- Uncompressed costs 4x (DXT5/3) or 8x (DXT1) the memory: a 1024^2 with mips = 5.6 MB vs 1.4/0.7 MB. Fine for the
  handful of textures being edited. Re-compression (for shipping paint layers smaller) can use stb_dxt
  (public domain / MIT, fits the licence rule) at save time only, never live.

### Memory budget (2 GB, not LAA)

The game plus fork already use a lot of address space (managed textures keep a CPU copy). Proposed cap for the
editor: **64 MB of process memory**, enforced, with a warning in the panel:
- per texture being edited: original RGBA (4 MB at 1024^2) + paint layer RGBA (4 MB) + staging texture (4 MB);
- undo ring 32 MB (dirty-rect before-images, oldest dropped);
- live replacements of *finished* edits are DEFAULT-pool (GPU memory, not process memory under native D3D9; under
  DXVK only host-visible staging is mapped). Their CPU sources are freed once applied, reloaded from disk on Reset.

---

## 3. Level 1 - adjustments: shader rule or pixel edit?

**Per-draw "tone" shader rule** (like `gloss=`/`glass=`): binding a pixel shader on a fixed-function draw
replaces the **whole texture-stage cascade**. The shader then has to reproduce the draw's stages (texture x vertex
colour x lightmap x detail, MODULATE2X...), which is exactly the job `surface=`/`layer=` do, and they already
refuse stage setups they don't know (`"stage setup not supported"`). A tone rule would inherit those holes and
would also fight with any other rule on the same draw (only one pixel shader per draw).

**Recommended instead: a GPU-baked replacement ("texadjust").** Draw the game's texture once through an adjust
shader into a render-target texture and use that as the replacement (route 3 above). Because it is still only a
texture swap, it works under **any** stage setup, on any stage (lightmaps too), combines with every other rule,
and costs nothing per frame. On a slider change it is re-baked: one full-screen quad at the texture's size,
< 0.1 ms. Fully live while dragging.

Adjustments and whether they fit ps_2_0 (64 ALU, 32 tex, 12 temps; ps_2_a/2_b more):

| Adjustment | Fits? | How |
|---|---|---|
| Brightness / exposure, contrast, levels (black/white/gamma) | ps_2_0 | affine + one `pow` |
| Saturation, hue rotation, tint, colour balance | ps_2_0 | a 3x4 colour matrix in constants (hue = rotation about the grey axis) |
| HSV hue shift (true hue, not matrix) | ps_2_0, tight; ps_2_a comfortable | rgb->hsv->rgb ~30 ALU |
| Curves (per channel) | ps_2_0 | 256x1 LUT texture, dependent read |
| Sharpness (unsharp mask) | ps_2_0 | 5 taps (cross) or 9 taps, using `1/size` in a constant |
| Blur / soften | ps_2_0 | same taps, negative amount |
| Alpha adjust (cutout threshold, opacity) | ps_2_0 | affine on `.a` |
| Detail-preserving recolour (e.g. hue only where saturated) | ps_2_0 | mask from saturation |

Mips: `AUTOGENMIPMAP` on the RT texture (or bake each level with the source's own mip as input, which keeps the
artist's mips and is equally cheap: one quad per level, with sharpness scaled per level).

Saved form: a recipe line, e.g. `texadjust=1a2b3c4d b=0.1 c=1.2 s=0.8 h=15 sharp=0.5 gamma=1`. No pixels at all.
`texgrade=` stays as is (it becomes a subset; the parser can map it to texadjust).

---

## 4. Level 2 - painting on the flat image

Panel "Texture" tab (inside the existing gmpanel, F7):
- Canvas: `ImGui::Image((ImTextureID)composite, size, uv0, uv1)` with zoom/pan (wheel, middle drag), a checkerboard
  behind for alpha (an `ImDrawCallback` that turns blending off for "show alpha as-is" mode), a 1:1 pixel grid
  when zoomed in.
- Brush: colour (with eyedropper reading the **composite texel**, not the lit screen pixel), radius, hardness,
  opacity, flow; tools: paint, erase-to-original (erases the paint layer, i.e. alpha 0), and fill.
- The data model is **layers, never a modified copy**:
  `composite = paint_layer OVER adjust(base)`, where `base` = the game's texture (or a `replace=` file).
  - `adjust(base)` is the level-1 GPU bake.
  - `paint_layer` is an RGBA buffer that holds only the user's strokes (alpha 0 elsewhere). Its resolution may
    be **higher** than the base (2x), which gives sharper paint on low-res game textures.
  - Compositing is one more ps_2_0 quad (two samples, lerp by layer alpha) into the replacement RT. So the CPU
    keeps only the paint layer; each stroke updates its dirty rect in the paint layer's staging texture ->
    `UpdateTexture` -> re-composite (whole texture, < 0.1 ms) -> the world shows it next frame.
- Undo/redo inside a session: per stroke, the paint layer's dirty rect before the stroke goes on the undo ring
  (32 MB cap). Redo stores the after-rect.

Effort: canvas + brush + layer + composite + undo is the biggest single chunk (see plan).

---

## 5. Level 3 - painting directly on world surfaces

### 5a. UV pass (screen pixel -> texel)

While the brush is down, each frame (or every other frame) the redraw pattern runs again, scissored to the
**brush rectangle** only (e.g. 64x64 to 256x256 px), with a uv shader:

- **Every** on-screen draw is redrawn (so occluders drawn *after* the picked surface still overwrite it), but only
  draws using the picked hash on the picked stage write their uv; all others write "not mine". Draws that don't
  write depth (decals, particles) are skipped by default so they don't block the brush.
- The uv comes from **`TEXCOORDn` where n = the picked stage**. With fixed-function vertex processing and a pixel
  shader bound, the FF pipeline still does the texgen (`TEXCOORDINDEX` incl. CAMERASPACEPOSITION for terrain) and
  the stage texture transform (`TEXTURETRANSFORMFLAGS` COUNTn): the shader receives the coordinates the sampler
  would have got. This is what `layer=` relies on. **Do not** disable the stage transform the way `shader=` does
  for anchoring: here we want the panned/scaled coordinate, because that is the one the texel is fetched with.
- **`D3DTTFF_PROJECTED` is ignored when a ps_2 shader is bound**: the shader must divide by the last component
  itself (the fork already passes this as `c1.x` for projector decals; same here, read from the stage's TTF).
- **Address modes**: read the stage's `ADDRESSU/V` and apply them in the shader: WRAP -> `frac(uv)`, CLAMP ->
  `saturate`, MIRROR -> `1 - abs(frac(uv*0.5)*2-1)`. Then `texel = uv * size` (size in a constant).
- Encoding: A8R8G8B8 (works with MSAA and every card): R,G,B = 12-bit x + 12-bit y texel (up to 4096), A =
  texture alpha for alpha-tested draws (same as the ID pass). "Not mine" = all ones. A float target
  (G32R32F) would be simpler but can't be multisampled, and the MSAA build binds a multisampled depth.
  MSAA resolve averages edge samples: reject pixels whose decoded texel jumps from both neighbours.
- Readback: `StretchRect` the brush rect into a small RT of the same size, `GetRenderTargetData` (64x64 = 16 KB,
  128x128 = 64 KB), read on the next frame to avoid stalling. One frame of latency is fine for a brush.

### 5b. Splatting into the texture

For each brush pixel with a valid texel and brush weight w (screen-space falloff around the cursor):
paint the texel's **footprint**: the local screen->texel Jacobian is taken from the decoded neighbours (right and
down pixels, when they are the same draw and not across a wrap jump), and a small quad/ellipse of that size is
painted into the paint layer. This:
- has no holes when the surface is minified (one screen pixel covers many texels),
- handles UV seams and triangle edges naturally (each screen pixel paints its own texel; nothing interpolates
  across the seam),
- respects tiling: the texel is the wrapped one.

Then dirty rect -> UpdateTexture -> composite, as in level 2. Both views (canvas and world) show the same layer.

### 5c. Later, if needed: projection painting in UV space

Blender-style: rasterise the picked draw's triangles in texture space using the CPU vertex shadows (`U2Shadow`,
from lmcapture) and test each texel's projected screen position against the brush and the depth. Exact and
hole-free at any angle, but needs the vertex copies and transforms of the draw; only worth it if 5b shows
artefacts on grazing angles.

### Caveats to show in the UI (not bugs)
- **Tiling and sharing**: most world textures tile and are shared across many surfaces and maps. A stroke on one
  wall appears on every repeat of that texture, everywhere. The panel must say "this texture: N draws on screen,
  tiles Kx" and offer **"paint as decal instead"** (a journal op that places a projector/decal with a paint layer
  of its own; reuses the blood decal path) for one-off marks.
- Lit vs texel colour: what you see is texture x lightmap x vertex colour; the brush paints texel colour. Offer a
  "compensate lighting" toggle later (divide by the readback lightmap value), not in v1.
- Animated textures (Unreal's TexPanner/TexRotator via stage transforms) are fine: paint lands in texture space.
  Procedural/scripted textures that the engine re-uploads each frame are read-locked or hash-unstable (`U2Hash`
  0xFFFFFFFF): refuse with a message.
- Lightmaps are on stage 1 with their own hashes: painting them = painting light. Allowed (it is just a stage).

---

## 6. Saving, journal and commit

### Files
New folder `System\U2Shaders\texedit\<hash>\` (fork-owned; the fork already writes in `U2Shaders\`):
- `recipe_<rev>.txt` - the adjustments (text).
- `paint_<rev>.dds` - the paint layer: A8R8G8B8 with mips (needs a `SaveDDS` variant writing the mip count flag
  `0x20000`, `DDSCAPS_COMPLEX|MIPMAP`, and every level; `LoadDDS` already reads mips). Optional DXT5 on save via stb_dxt.
- `meta_<rev>.txt` - author, date, base hash, size, tools used, and the **taint flag** (below).
Revisions are immutable files; undo only moves a pointer.

`U2Shaders.ini` is **not** written by the editor: a write there triggers `ReloadRules`, which drops every shader
and replacement. Texture edits get their own state, so a change re-makes only that hash.

### Journal (U2GM)
The fork cannot write `U2GM.ini` (the game rewrites it from memory), so it goes through the panel's existing
command channel: on "Apply" (stroke batch end / slider release) the panel sends `GmSend("tex HASH REV")`
(hex + digits pass the whitelist). U2GM journals `@* tex 1a2b3c4d 7` (`@*`: texture edits are global, keyed by
content hash, not by map family). The fork already watches `U2GM.ini` for terrain lines; it reads `tex` lines the
same way and applies the **latest REV per hash**. So `gm undo`/`gm redo` work exactly as for terrain, and a map
load restores the edits. Fine-grained stroke undo stays local to the panel; the journal gets one line per Apply.

### Commit (bake)
Recommendation: **texture edits are not baked into .utx by `gm commit`.** They stay a runtime layer of the fork:
- Baking means writing a composite (game pixels + edit) into a package: that package then contains the game's
  pixels and can never be shared. It would also need the hash -> `Package.Group.Name` mapping and re-pointing
  BSP surfaces/meshes/materials at the new texture (UnrealEd `TEXTURE IMPORT` works, as gm_commit.py uses it for
  heightmaps, but re-pointing references is unverified work).
- If a local bake is wanted later: `gm_commit.py --bake-textures` writes composites into the `<Map>_LiveN`'s
  MyLevel (local only, flagged "never ship"), via `TEXTURE IMPORT FILE=... PACKAGE=<Map>_LiveN GROUP=GMTex`.
- Useful side tool either way: a **hash index** (`hash -> Pkg.Group.Name`), built offline by hashing mip 0 of
  every texture in `Textures\*.utx` the same way as `Hash()` (DXT data is uploaded unchanged, so it matches;
  32-bit ones too). Lets the panel show names and lets `replace=` lines be written by name.

---

## 7. Undo, multiple users, and never shipping the game's pixels

**The rule: the game's texture pixels are never redistributed.** Design so that the shareable form of an edit
contains no game pixels at all:

| Part | Contains game pixels? | Shareable |
|---|---|---|
| `recipe` (adjust numbers) | no | yes |
| `paint` layer from own-colour tools (paint, fill, erase, eyedropper colour) | no: only the user's strokes; alpha 0 elsewhere | yes |
| `paint` layer that ever got sampled pixels (clone/stamp, smudge, "bake adjustments into layer", blur of the composite) | **yes** (derived) | **local only** |
| composite / full replacement DDS / upscaled textures / dumps | yes | **local only** |

- Tools that copy pixels set `taint=1` in the layer's meta; once tainted, a layer stays local.
- The composite is always rebuilt on the user's own machine from their own game install (by hash), so a shared
  pack = recipes + clean paint layers + `tex` journal lines.
- A pack exporter (`tools/texpack.py`, later) whitelists `recipe_*.txt`, untainted `paint_*.dds`, and meta; refuses
  everything else; and as a second guard checks painted pixels against the original dump (high correlation in the
  painted area -> refuse, "looks derived").
- `U2Shaders\dump\` and `texedit\*\local\` stay gitignored and out of any release zip (same as today's dumps).

**Undo:** two levels, as above: in-panel stroke ring (memory), journal revisions (disk, immutable files).

**Multiple users** (several people or several chats editing the same hash): each Apply is an immutable
`(hash, author, rev)` file set; layers from different authors **stack** in journal order (each its own paint layer,
composited in order), so nobody overwrites another's pixels; a recipe from a later line wins per parameter.
Conflicts are just ordering, same as the GM journal. Hash keys are content-based, so packs work on any install of
the same game build (a different build -> different hash -> the edit simply doesn't apply, and the panel lists
it as "base not found").

---

## 8. Staged plan and effort

Estimates are in Claude working days, offline build + the unreal chat's in-game test on its restarts.
All new code in a **new header `source/texedit.hpp`** (class `U2TexEdit`), with only a few hook lines in
`u2shaders.hpp`/`d3d8to9_device.cpp` (they are being edited in parallel now; add the hooks after that lands).

| Stage | Content | Effort |
|---|---|---|
| **0. Pick** | ID pass (MaskBegin clone with scissor + 24-bit serial + alpha-test aware shader), draw table, 1x1 readback next frame; panel "Texture" tab: hash/size/format/stage/draws, thumbnail via `ImGui::Image`, "show uses" tint, optional stack via occlusion queries | 1 day |
| **1. Adjust** | GPU bake into RT replacement (adjust ps_2_0: matrix, levels, gamma, unsharp), `Replacement()` hook returns it, sliders live, Reset handling, recipe save + `tex` journal line + fork reading `@* tex` from U2GM.ini | 1.5 days |
| **2. Flat paint** | paint layer (CPU + SYSTEMMEM staging + UpdateTexture dirty rects), composite shader, canvas with zoom/pan/alpha view, brush/eraser/eyedropper/fill, stroke undo ring, mip-writing DDS saver, revisions + taint meta | 3 days |
| **3. World paint** | uv pass (stage n TEXCOORD, projected divide, address modes, 12+12 encoding, all-draws occlusion), brush-rect readback, footprint splat, "paint as decal" fallback stub, caveat UI | 3 days (+1-2 polish on seams/grazing angles) |
| **4. Sharing** | `texpack.py` exporter with whitelist + derived-pixel check; hash index tool for names | 1.5 days |
| Optional | 5c UV-space projection paint; local `.utx` bake | 2-4 days each, only if needed |

Total for levels 1-3: about 9-10 days.

### First concrete step

Build **stage 0 offline**: `source/texedit.hpp` with `TexPickBegin/TexPickEnd` modelled on `MaskBegin/MaskEnd`
(same three hook points after `U2After` in DrawPrimitive / DrawIndexedPrimitive / DrawPrimitiveUP; scissor on,
rect = cursor pixel; ps_2_0 `float4(c0.rgb, tex2D(s0,t0).a * d0.a)` with the serial in c0), a per-frame
`std::vector<TexPickDraw>` of `{serial, hash[4], alphatest, zwrite, stage TCI/TTF, addressU/V}`, and a panel
click mode "pick texture" that arms the pass for one frame and shows the result next frame. Testable in game
with one click on a wall, one on a grate hole (must pick what is behind), one on the first-person weapon
(must pick the weapon, after the mid-frame depth clear). That one click answers the robustness questions for the
uv pass too, since level 3 reuses the same redraw machinery.
