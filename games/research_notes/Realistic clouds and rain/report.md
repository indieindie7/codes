# Realistic clouds and rain in an old engine (Unreal Engine 2 / Unreal II)

Written 2026-10-08 by a research agent for Q34 (the user: "clouds and rain still not great do some research on how to make them look realistic").
Target scene: stormy dusk on a coastal island (~60000 uu across). Camera mostly on the ground, sometimes high on a tower.

Each technique gets a fit tag:

- **[S]** script only (sprites, meshes, emitters, SkyZoneInfo, lights, traces).
- **[T]** a texture or mesh made offline (Python, Blender).
- **[P]** the HLSL fork (post pass, or a shader swapped in by hash with `replace=` / `layer=`).

The ranked action list is at the end.

## 0. Why the current version reads wrong

**Clouds.** 10-16 soft puffs per bank at ~11000 uu read as small grey blobs. Five reasons:

1. **Scale.** At about 52 uu per metre, 11000 uu is only ~210 m up. The island is ~1.1 km. A real storm deck sits 300-1500 m up and fills the sky from edge to edge. One real cumulus cell is often as wide as this whole island.
2. **One frequency.** Many same-size sprites give one size of detail. Real clouds are fractal: one big silhouette, then bulges, then wisps. Same-size puffs read as "cotton balls".
3. **No shared lighting.** Each puff is lit alone, with its own dark base and bright top. A real bank is lit as one volume: a dark underside across the whole bank, a bright rim only where the sun-facing edge is thin.
4. **Wrong cloud type for the weather.** A stormy dusk is mostly a continuous overcast (nimbostratus or stratocumulus). It has ragged low scud moving fast under it, and often a bright slot at the horizon where the setting sun gets under the deck. Isolated cumulus banks belong to fair weather.
5. **No atmospheric perspective.** Far clouds should get lower in contrast and take on the horizon haze colour. They should sink into the haze, not stop at a hard edge.

**Rain.** It reads as evenly spaced white dashes. Six reasons:

1. **Spacing.** The spawn pattern is too regular. Real rain is random, so you see clumps and gaps.
2. **Colour.** The streaks are pure white and opaque. A real streak is a faint refraction of the sky, about 6% darker than the bright drop. It is mostly visible against dark backgrounds and almost invisible against bright sky (ToyShop, Lagarde).
3. **One depth.** There is no near/mid/far layering, so there is no parallax and no veil.
4. **Straight down.** A coastal storm with 10 m/s wind and ~8 m/s fall speed slants rain by tens of degrees. The slant also changes in gusts.
5. **Same length.** Streak length should come from speed × exposure time. Drops near the camera should look longer and wider on screen.
6. **No ground contact.** There are no splashes, no wet look and no ripples. Without these the world does not look rained on.

## 1. Clouds: how shipped games and papers do it

### 1.1 Sky dome / skybox layering [S][T]

- **UT2004 / UE2 skyboxes.** These use a SkyZoneInfo in a sealed box: a painted backdrop, plus 2 or more translucent cloud sheets near the top that pan at different speeds. The lower sheet uses a bigger texture scale so it seems to move faster (parallax). The Unreal Wiki advises pan speeds of about 0.3, because faster looks fake. It also says sun and moon look better as flat sheets than as spheres. Sources: [Unreal Wiki: SkyBox](https://unrealarchive.org/wikis/unreal-wiki/Legacy:SkyBox.html), [Epic UDN: Example sky zones](https://docs.unrealengine.com/udk/Two/ExampleMapsSkyZones.html).
- **Half-Life 2 3D skybox.** Distant scenery is built at 1/16 scale around a `sky_camera` and drawn behind the world, so the far terrain gets slight parallax. HL2's skies are high-quality photo/painted cube maps. Most of the realism comes from the photo texture, not from geometry. Source: [VDC: 3D Skybox](https://developer.valvesoftware.com/wiki/3D_Skybox).
- **The lesson for us.** In 2003-2006 most of the realism in the sky came from **one good texture on the dome**. Moving sheets and a few near cards were added on top. A baked, correctly lit storm panorama for our fixed dusk sun direction is cheap and beats live puffs.
- **Layer order (back to front):**
  1. Sky gradient and sun glow.
  2. Far overcast deck (static, baked).
  3. 1-2 panning cloud sheets (scud), each with a soft alpha.
  4. Horizon haze band: a ring mesh with a vertical gradient that blends the sea into the sky.
  5. A few world-space near clouds or scud cards, only where parallax matters (the tower view).

### 1.2 Sprite clouds done right: Flight Simulator 2004 / Crysis 1 [S][T]

- **Niniane Wang, Microsoft Flight Simulator 2004.** Each cloud is a box volume filled with textured sprites. A dozen cloud types come from choosing sprite textures and box layouts. Shading is a **vertical gradient across the whole cloud**, so the base is dark and the top is bright, plus a term for direction to the sun. It is not per-sprite lighting. Sources: [Wang, SIGGRAPH 2003 sketch](https://history.siggraph.org/learning/realistic-and-fast-cloud-rendering-in-computer-games), JGT 2004 "Realistic and Fast Cloud Rendering" ([index](https://ftp.math.utah.edu/pub/tex/bib/idx/jgraphtools/9/3/21-40.html)).
- **CryEngine 2 (Crysis 1).** Its clouds are based on Wang's method, with three additions: gradient-based shading; soft clipping against terrain and the near/far planes using scene depth; and a **back-lighting term with respect to the sun**, which gives glowing edges when a cloud partly covers the sun. Cloud shadows are cast on the ground in one full-screen pass from scene depth. Source: [Wenzel, "Real-time Atmospheric Effects in Games", SIGGRAPH 2006, ch. 6](https://advances.realtimerendering.com/s2006/Chapter6-Real-time%20Atmospheric%20Effects%20in%20Games.pdf).
- **Harris & Lastra 2001.** Multiple forward scattering is baked offline. First-order anisotropic scattering is done at runtime. Distant clouds become impostors. Sources: [Real-Time Cloud Rendering](https://diglib.eg.org/handle/10.2312/8851), [Harris GDC 2002](https://aurora.cs.uaf.edu/~olawlor/academic/thesis/ref/RTCloudsForGames_HarrisGDC2002.pdf).
- **Far Cry (2004).** Mostly a skydome plus painted/panning layers; no technical write-up found.

**How to apply it here:** tint each sprite **by its height inside the bank**, not one dark base per puff. One line of script: lerp base colour to top colour by `(Z - bankBottom)/bankHeight`, plus a sun-side bias. This alone removes most of the "blob" look.

### 1.3 Lit cloud impostors: normal-mapped and 6-way lightmaps [T][P]

- **Unity six-way lighting.** Six directional lightmaps baked per sprite, packed in two RGBA textures (A: right/top/back/alpha; B: left/bottom/front/emissive), blended at runtime by light direction. Sources: [Unity manual](https://docs.unity3d.com/Packages/com.unity.visualeffectgraph@17.0/manual/six-way-lighting.html), [Unity blog](https://unity.com/blog/engine-platform/realistic-smoke-with-6-way-lighting-in-vfx-graph).
- **Fit:** not in D3D8 fixed function; possible in the fork with a cloud-sprite shader swapped by hash.
- **Cheaper option for a fixed sun.** Our dusk sun does not move: bake **one** lit texture per cloud card in Blender with the real sun direction. For the tower view, pick 1 of N azimuth-baked frames from the view angle (the 8-angle card idea). Script plus textures, no shader.
- **Normal-mapped cloud sprites** with wrap lighting `(N·L + w)/(1 + w)`, w ≈ 0.5-1, are a halfway house; they look plastic without heavy wrap.

### 1.4 Silver lining, Henyey-Greenstein, and the powder effect [T][S][P]

1. **Beer's law.** `T = exp(-σ·d)`: dark undersides and dark cores.
2. **Henyey-Greenstein phase.** Strong forward scattering gives the **silver lining** toward the sun. `HG(θ,g) = (1-g²) / (4π (1 + g² - 2g cosθ)^1.5)`, g ≈ 0.6-0.8, often blended with a weaker back lobe (g ≈ -0.3).
3. **Powder effect.** Sun-facing edges look darker than the interior. Common form `E = 2·exp(-d)·(1 - exp(-2d))`. Horizon also raises absorption for rain clouds: relevant for our storm.

- **[T]** Bake all three into the cloud textures or panorama offline (cheapest correct option).
- **[S]** A per-bank additive "edge" sprite (alpha mask of thin edges) whose brightness is set each tick to `HG(dot(viewDir, sunDir), 0.7)`: lights up only looking toward the dusk sun (the Crysis back-light trick in script).
- **[P]** Per pixel in a swapped cloud shader: `rim = HG · (1 - alpha)^k`.

### 1.5 Horizon Zero Dawn: Nubis [P, mostly out of reach]

Raymarched volumetric clouds; strato layer 1500-4000 m, Perlin-Worley noise eroded by a weather map, 64-128 steps, ~2 ms on PS4. Before that Guerrilla tried polygon clouds with baked SH, multi-orientation billboards and pre-rendered skydomes. Sources: [SIGGRAPH 2015 slides](https://www.advances.realtimerendering.com/s2015/The%20Real-time%20Volumetric%20Cloudscapes%20of%20Horizon%20-%20Zero%20Dawn%20-%20ARTR.pdf), [Nubis Evolved](https://www.guerrilla-games.com/read/nubis-evolved), [Nubis Cubed 2023](https://advances.realtimerendering.com/s2023/Nubis%20Cubed%20(Advances%202023).pdf), [80.lv](https://80.lv/articles/creating-clouds-in-horizon-zero-dawn).

Fit: a sky-only quarter-res raymarch in the post pass (depth = far) is possible but large. With a fixed sun a baked panorama looks almost as good: use Schneider's lighting model **offline**.

### 1.6 Microsoft Flight Simulator 2020/2024 [reference only]

Full volumetric clouds; no published technical talk found. MSFS 2004 (Wang) is the relevant model for us.

### 1.7 Scale and density rules

- Main cloud shapes should span **20-60° of view**; 2-5° clouds read as toys. A storm deck covers 70-100% of the sky.
- Storm base ~25000-50000 uu, running past the island to the horizon; better still, the deck in the SkyZone.
- Fewer, bigger sprites: one large silhouette card per bank + 3-6 bulge cards, small detail baked in.
- Underside ≈ fog/ambient × 0.4-0.6; top lit only where the sun reaches; rim brightens only toward the sun.
- Atmospheric perspective: lerp toward the horizon haze colour by distance; deck bottom fades into the haze band, no hard line.
- **Horizon slot:** a dark deck with a narrow bright orange gap at the horizon. Cheap, reads at once as "storm at dusk", fits the one-good-frame test.

## 2. Rain: how shipped games and papers do it

### 2.1 Velocity-stretched streaks [S][T]

- Streak length = fall speed × exposure: 6.5-9 m/s, 1/30-1/60 s → 10-30 cm long (5-15 uu), 1-3 mm wide. Beyond a few metres a drop is sub-pixel: draw thin and faint.
- Orient each streak along velocity relative to the camera (fall + wind − camera velocity).
- Randomise length ±30%, alpha 0.05-0.35, fully random spawn (no grid), slight speed spread.
- Colour from the scene ambient (dusk blue-grey), brightened only near lights. Source: [Tatarchuk, ToyShop, SIGGRAPH 2006 ch. 3](https://advances.realtimerendering.com/s2006/Chapter3-Artist-Directable_Real-Time_Rain_Rendering_in_City_Environments.pdf).

### 2.2 Streak textures with motion blur and refraction [T][P]

- **Garg & Nayar (SIGGRAPH 2006)** streak database ([CAVE](https://cave.cs.columbia.edu/projects/categories/project?cid=Physics-Based+Vision&pid=Photorealistic+Rendering+of+Rain+Streaks)). A download: ask before fetching; generating our own is the plan.
- **NVIDIA "Rain" sample (D3D10 SDK, 2007)**: GPU particles, geometry-shader quads, Garg textures picked by light/view angle ([NVIDIA SDK samples](https://developer.nvidia.com/w/SDK/10/direct3d/samples.html); the Sarah Tariq credit comes from secondary sources).
- Refraction: a drop refracts ~165° and is brighter than what's behind it. ToyShop uses a pre-blurred droplet normal map, Fresnel edges, and blurs the rain layer in post.
- Fit: [T] a Python streak atlas (8-16 tapered Gaussian variants, faint bright core, soft tail); [P] use the rain layer as a distortion mask for cheap refraction.

### 2.3 Rain at several depths [S][T][P]

- **FS2004:** four scrolling rain textures on a double cone tilted toward the camera.
- **Remember Me (UE3):** four layers on a camera-centred cone, scrolled/scaled/rotated; near layers use a height map + soft depth test, far layers noise masks + depth fades; ~1.7 ms on PS3/360. Source: [Lagarde, "Water drop 2a"](https://seblagarde.wordpress.com/2012/12/27/water-drop-2a-dynamic-rain-and-its-effects/).
- **ToyShop:** all rain layers in one full-screen pass with a projective depth parameter; one global rain direction vector.
- **Far curtains:** big vertical cards with slow low-contrast streaks, fading top and bottom, shaped as rain shafts under the deck, over the sea.
- Fit: near [S] particles within ~10 m; mid [S][T] camera cone with 3 panning layers (TexPanner if Unreal II has it, else a `layer=` rule); far [S][T] curtain cards + fog; or [P] a ToyShop-style depth-tested composite.

### 2.4 Camera-attached cones [S]

Follow camera location, not rotation; tilt into the wind and counter by camera velocity; spawn near drops only in a box in front of the camera (Space Marine): 3-4× cheaper than a ring.

### 2.5 Density, wind slant and gusts [S]

- Visible streaks mostly within 5-20 m; past that, layers and fog. Drive drops, splashes and lens drops from one intensity value.
- One wind vector for everything: streaks, cone, layer UVs, scud, spray, foliage, curtains. 8-15 m/s coastal wind → 25-55° slant.
- Gusts: slow noise (2-8 s) plus occasional sharp gusts with more rain and spray ([VDC: Rain splashes](https://developer.valvesoftware.com/wiki/Rain_splashes)).

### 2.6 Rain that catches the light [S][P]

Rain at dusk is seen mostly where a light is in front of or beside it. [S] extra warm additive streak emitters inside key light cones (tower lamps, beacon), general rain dim. [P] multiply the rain by blurred scene luminance (the bloom buffer) and widen bloom a little in rain (ToyShop "misty halos").

### 2.7 Splashes, ripples, wet surfaces [S][T][P]

- **Splashes:** ToyShop drew 5000-8000 from one filmed crown sequence; Remember Me spawns 20/40/60 over 20 m. [S] downward traces from random points within ~15 m, view-biased; [T] 8-16 frame crown flipbook from Blender.
- **Ripples:** expanding-ring normal flipbook on water, puddles, decks ([CRYENGINE Rain entity](https://www.cryengine.com/docs/static/engines/cryengine-5/categories/23756816/pages/29796935)); [P] via `layer=`.
- **Wet surfaces:** albedo ×0.5-0.7, more gloss, puddles in hollows. **Splinter Cell: Chaos Theory** (UE2.5) proves the engine family can do it ([PC Gamer making-of](https://www.pcgamer.com/au/the-making-of-splinter-cell-chaos-theory)). [P] easiest: normals from depth (SSAO has them), up-facing pixels darkened + Fresnel sky sheen + vertical streaks of bright lights, masked under cover.

### 2.8 Rain occlusion [S][P]

Remember Me / CryEngine use a top-down rain occlusion map. [S] upward traces from spawn points or a cached coarse covered-cell grid; fade the camera cone under roofs; indoor zones switch rain off and sound to "rain on roof".

### 2.9 Fog and mist [S][P]

Distance fog colour must exactly match the horizon haze. Add low sea-mist cards in coves, wind-driven shoreline spray on gusts; [P] a slight luminance glow around lights.

### 2.10 Lightning [S][T][P]

ToyShop: two baked lightning lightmaps flashed in all materials, rain more transparent during flashes, thunder after. [S] 2-3 flickers of 60-120 ms, a pre-baked flash-lit sky swap, a bolt sprite in the SkyZone, thunder delayed by distance / 343 m/s; [P] a short exposure spike.

### 2.11 Lens drops [P][S]

Remember Me: view-space refracting drops, more when looking up, none under cover, 0.3-0.5 ms. Low priority for first-person U2: a sparse visor effect at most.

### 2.12 Sound [S]

Far hiss bed; surface patter (rock, metal, foliage, water); close drips; muffled rain-on-roof under cover (same occlusion test); gust swells synced to the visual wind; surf; delayed thunder. Audio does half of the "heavy rain" read at no render cost ([BOOM RAIN](https://boomlibrary.com/sound-effects/rain/) is organised the same way).

### 2.13 Named games

- **Crysis 2/3:** Rain entity = occlusion, wet surfaces, puddles, ripples, splashes, drops.
- **GTA V:** rain lit by street lights, wet reflective roads ([graphics study](https://cgpress.org/archives/gta-v-graphics-study.html); no rain-specific breakdown).
- **The Last of Us:** window drips = normal texture + UV distortion ([RealtimeVFX](https://realtimevfx.com/t/last-of-us-how-are-the-windows-rain-drips-made/2526)).
- **Batman: Arkham Knight:** wet characters sell the rain ([GameSpot](https://gamespot.com/articles/watch-batman-arkham-knight-s-incredible-effects-us/1100-6427873/)).
- **Ghost of Tsushima:** art-direction lesson: one strong wind drives grass, leaves, rain and clouds ([GDC Vault](https://www.gdcvault.com/play/1027399/Exploration-in-Ghost-of-Tsushima)).
- **Splinter Cell: Chaos Theory:** same-engine proof of storm + wet.
- **Half-Life 2 Ep2:** `func_precipitation`, shared wind, splash percentage ([VDC](https://developer.valvesoftware.com/wiki/Func_precipitation)).
- **MGS2 Tanker:** wind-carried rain + deck splashes on PS2; no official breakdown.
- **Max Payne:** snow, not rain; mood lesson only (fog + slant + sound).
- **Unreal 1:** not a good reference.

## 3. Fit summary

| Technique | Script | Offline texture | HLSL fork | Effort |
|---|---|---|---|---|
| Baked storm panorama in SkyZone | yes | yes | - | low-med |
| Panning scud sheets + horizon haze ring | yes | yes | - | low |
| Bank-gradient tint for cloud sprites | yes | - | - | very low |
| HG rim sprite (silver lining) | yes | yes | optional | low |
| Lit impostor cards (fixed sun) / azimuth frames | yes | yes | - | low-med |
| 6-way cloud sprites | - | yes | yes | med |
| Live sky raymarch (Nubis-lite) | - | noise tex | yes | high |
| Velocity-stretched, random, tinted streaks | yes | yes | - | low |
| Camera cone with 3 panning layers | yes | yes | (layer=) | low-med |
| Far rain curtains / shafts | yes | yes | - | low |
| ToyShop full-screen depth-tested rain | - | yes | yes | med |
| Rain only in light cones | yes | - | or bloom | low / med |
| Splashes via traces + crown flipbook | yes | yes | - | low-med |
| Global wetness | - | - | yes | med |
| Ripples | - | yes | yes | med |
| Rain occlusion (traces, zones) | yes | - | - | low |
| Lightning | yes | yes | optional | low |
| Lens drops | optional | yes | yes | med (low value) |
| Layered rain audio | yes | - | - | low |

## 4. Ranked top-8 actions (impact ÷ effort, stormy-dusk coastal island)

1. **Baked storm sky in the SkyZone** [T][S]: a volumetric overcast deck rendered in Blender or a Python raymarch (Beer + HG + powder, real dusk sun), dark rain cores, a bright horizon slot; 1-2 panning scud sheets; a haze ring matching the zone fog; only a few big world-space scud cards near the tower. Fixes scale, lighting and horizon fade together.
2. **Rebuild the rain streaks** [S][T]: Python atlas of thin tapered soft streaks; random spawn in a box in front of the camera; length from relative velocity; alpha 0.05-0.35; blue-grey; tilt from one gusting wind vector shared with clouds and spray.
3. **Depth layers** [S][T]: camera-attached double cone with 3 panning layers; far rain-shaft curtain cards over the sea fading into fog.
4. **Lightning** [S][T]: quick flickers, a flash-lit sky swap, a bolt sprite, thunder delayed by distance/343 m/s.
5. **Rain catching the light** [S] then [P]: dense warm streaks inside lamp and beacon cones; later rain × blurred luminance and wider bloom in rain.
6. **Wet ground** [S][T][P]: trace-placed splashes with a crown flipbook; a fork wetness pass on up-facing pixels; ripple flipbook via `layer=`.
7. **If world-space banks stay, light each as one volume** [S][T]: fewer bigger baked-lit cards, height-in-bank tint, HG rim sprite, haze lerp by distance.
8. **Occlusion and sound** [S]: traces + indoor zones switch rain off; layered audio with gust swells and delayed thunder.

**Later / optional:** lens drops; a ToyShop-style full-screen depth-tested rain composite; a Nubis-lite sky raymarch in post.
