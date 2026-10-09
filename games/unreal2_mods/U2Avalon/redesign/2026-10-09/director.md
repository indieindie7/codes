# Avalon redesign: the DIRECTOR (cinematography)

2026-10-09. Written during a playtest swap: no images generated, no game, editor or pilot runs. The
references below are web pages only. Nothing was downloaded, and none of it ships in a mod (PIPELINE.md
"Playtest swap").

I read: PIPELINE.md, README.txt, codirect.py, compose.py, plans.py, binder/parti.json, the building sheets,
marks/MARKS.md and QUEUE.md (Q1-Q81), the marks Shot00038/65/75/92 and sketch-20261008-222540, the
peak frame (design-refs/avalon_peak_frames/catwalk_dusk_silhouette.png), the cinematography report and the
design-taste memories.

The parti sentence I am shooting: **"The company holds the high ground; the town lives in its shadow and
its smoke."** The four beats: dock = dread (compression, tower hidden); spine_mid = exposure (tower
glimpsed over roofs); company_gate = smallness (battered wall, stair cut-in); catwalk = melancholy
(release: dark frame, grated catwalk, a lone figure 40-100 m away, dusk rain).

---

## 0. Five things I found while reading. Fix these first.

1. **The sun rule in codirect.py is inverted.** `off = |SUN_AZ - LOOK|` = |136 - 300| = 164 deg is
   scored 1.0 and labelled "back/side light". But 136 is where the sun *is*: plans.py draws the light
   travelling toward SUN_AZ + 180, and lowsun.py says the sun is "seen from the decks at about yaw 136".
   So from the command window (yaw 300) the sun is **behind the viewer**. That is front light, the flat
   case. The memory note agrees: "Window view gets darker/bluer under the low sun (sun behind the viewer)".
   Correct rule, with `off` = the angle between the view direction and the sun's position:
   - 0-60 deg: back light (silhouettes, rim). This is the peak frame.
   - 60-120 deg: side light (form).
   - 120-180 deg: front light (flat, everything is shown, nothing is hidden).

   **Do not move the sun.** Az 136 at elevation 6-9 deg is the right hour for this town. It back-lights
   every view the user has loved (the decks and the catwalk look roughly toward 136-171). It also throws
   the tower's long shadow away from the tower toward yaw ~316, which is *into* the window's view. Score
   per view instead of with one global number: the window's job is ownership and the shadow, the decks'
   job is silhouettes (see F1, F4, F5).
2. **The window frame never shows the horizon.** compose.py looks 28 deg down with a half height of 26 deg,
   so the frame runs from -54 to -2 deg and the sky and the sea horizon are outside it. codirect then gives
   the background layer away free ("the sea horizon is always there"). Silhouettes and the "air between
   layers" need the horizon in the picture. Recommendation: pitch **-9 deg**. The horizon then sits on the
   upper third line, and the plant (about 19 deg below the eye) falls at about 70 % of the frame height:
   town in the lower third, sea and sky in the upper two thirds, never 50/50. Also set the PlayerStart's
   initial pitch to about -9 so the first frame the player sees is this one.
3. **In TutA (the campaign map) the player can only walk the tower.** The playable area is decks and
   balconies (playshots.py, 2026-10-07), so the dock-to-tower walk that serial vision (A-401) scores is
   never walked there. Two answers, and we need both:
   (a) map the four beats onto the tower's own route: command room, corridor, stairs, overhang deck,
   catwalk (section 2, "Beat map");
   (b) in the generated maps (TutA_Cine8 and later), start the player at the dock so the walk exists.
4. **"Too dark" and "peak frame" are the same note.** The user marked darkness six times (Q5, Q47, Q49,
   Q53, Q71, Q80) and also loves a frame that is 70 % near-black. The difference is legibility. In the peak
   frame the floor grating reads at about 20-25 % grey because the lit ground shows through it, and the dark
   is only the frame (the ceiling slab and the wall). In Shot00038 and Shot00065 the floor the player stands
   on is about 2 %. **Rule: the frame may be black, the path may not.** There is a value ladder for this in
   section 3.
5. **Repetition is diluting the landmark.** The crane tower (the Aztec landmark) was copied into 3 far
   "industrial complexes" (Q11), and two cranes mirrored each other (Q51). One dominant needs to stay unique:
   at most one far echo, at under a third of the hero's apparent height.

---

## 1. Shot list: the 14 frames a player should get

Coordinates: TutA world units where I know them; otherwise the binder's look frame (along, across) from the
tower at (0,0), look yaw 300. 1 m = 50 uu. FOV is the game's ~90 deg unless noted. "Build" lists what has
to be made or moved to get the shot.

### Inside the tower (the TutA route, playable today)

**F1. The Window: ownership.** *Hero frame of the map.*
- Camera: command-room PlayerStart eye (-350, 1388, 4302), yaw 300, **pitch -9**.
- In frame: FG = the mullions, sill and console tops (the darkest group, no detail). MG at 240-350 m = the
  plant: halls, silos, the cooling towers (hero) on the **right third** (u ≈ 0.67) with steam rising. Gap =
  the inlet water. BG = the rigs with flares at 450 m+, the far islands, the sea horizon on the upper third.
- Light: dusk, sun az 136 el 6-9 behind the viewer, warm front light on the plant. **The tower's own shadow
  lies across the town toward yaw ~316**: a long dark wedge over the dorm and shanty roofs, with the plant
  lit beyond it. That is the parti sentence as a picture. Blue hour: spine lamps and window strips come on
  one by one.
- Emotion: ownership, the company watching; a little guilt.
- Build: (1) the start pitch; (2) bake the terrain and meshes so the BSP tower casts onto terrain at el 6-9
  (lowsun.py relights terrain + meshes; check that the tower's shadow is baked, not just the meshes');
  (3) place layout_spine's decline layer (dorms and shanty) under the shadow wedge and keep the hero
  *outside* it (a new compose term: "hero lit, housing shadowed"); (4) keep console screens away from the
  glass. A screen brighter than the town steals the key (Shot00092: the consoles are the brightest thing
  in the room).

**F2. Hawkins against the glass: the intro cine (Q56, with the writer).**
- Camera: low, at the console row 4-6 m from the window, looking at Hawkins with the window behind him.
- In frame: Hawkins as a silhouette against the bright town, then his face.
- Light: key = the window behind him (rim); a motivated **console up-light** on his face (Fraser's bounce
  logic: the consoles are the believable source); pawn AmbientGlow ~30 so he is never a black hole (Q71).
- Emotion: Spielberg's delay. Hold on his face while he talks about the town; the player does not see the
  town yet. He turns, the camera follows his look, and F1 opens.
- Build: GMCine shot list (gm cine); a console light (AvalonLamp, warm-cyan, low radius); the window must
  read brighter than the room interior in post (bloom picks it up).

**F3. The corridor: compression.**
- Camera: tower corridor from the command room toward the stairs, one-point perspective, eye height.
- In frame: the 8 floor-corner AvalonLamps (Q31) as **stepping stones** (Pangilinan) receding to a
  single slit of daylight at the end (a door ajar or a frosted panel).
- Light: lamp pools on the floor at 20-30 % value, walls and ceiling at 5-10 %, the slit at 90 %.
- Emotion: held breath, the reveal withheld.
- Build: cut the lamp count in half and alternate sides (rhythm beats evenness); the end door as a
  bright slit, not a full opening. No window views in the corridor at all. This is where the town is hidden.

**F4. The overhang deck: shanty mountain at dusk (Q51's view).**
- Camera: deck under the overhang (-1732, 2968, 3937), yaw ~171, pitch -10 to -20.
- In frame: the overhang slab across the top 25-30 % (black frame), the rail as a leading diagonal, the
  hillside town in contour rows (hillside.py), two shanty plumes, the rich houses and water tower on the
  summit as the local landmark against the sky.
- Light: the sun at az 136 is 35 deg off this view, so it is **back light**: shack roofs get rim edges,
  the plumes glow at their edges, and the ridge is a silhouette.
- Emotion: exposure. You see how they live.
- Build: lift the deck floor out of black (Q47): a lamp pool on the floor 6-8 m from the camera and the
  zone ambient (already 46/24/140); keep the slab above unlit. Rain in the lamp cone (Q34's next item)
  makes this frame.

**F5. The peak catwalk: release, melancholy.** *The user's peak frame; protect it.*
- Camera: just inside the catwalk's root under the tower (M10_NewCatwalk1b), looking out along the
  grating toward yaw ~136-171.
- In frame: the dark interior on the left and top (wall, slab, a machinery box), the grated catwalk and its
  rails converging, **one figure 40-100 m out at the catwalk end**, the warm horizon band, the far crane
  silhouettes on the right, rain streaks crossing the whole frame.
- Light: the sun just under the horizon, ahead of the camera (back light). The figure is pure silhouette.
  Nothing in frame is brighter than the horizon band.
- Emotion: melancholy, release after compression.
- Build: (1) **staffage**: a marine posed at the catwalk end (hub dummy style, AI removed, a smoking-break
  idle; the writer gives him a name); (2) rain sheets and splashes ON (NoRain only inside); (3) the far
  cranes: keep one, as a silhouette at under 1/3 of the frame height; (4) lit ground below the grating (the
  terrain under it must be lit, because that is what makes the grating read); (5) add nothing else here.

**F6. The storm window: the turn.** (Same camera as F1, a different beat.)
- In frame: the plant reduced to silhouettes with lit window strips; the steam torn sideways by the wind;
  lightning lights the far rigs for a few frames (the dome swaps to flash-lit).
- Light and fog: storm fog 2000/60000 (Q60, keep it); ClientAdjustGlow darkens; the flash = ClientFlash +
  zone fog colour.
- Emotion: dread; the island is cut off.
- Build: nothing new. Check that the hero (cooling towers) still reads as a shape at the storm fog's mid
  distance. If it greys out, lower its fog (a per-zone fog or a darker emissive top).

### The town (generated maps; walkable from the dock)

**F7. Dock arrival: dread, compression, tower hidden (beat 1).**
- Camera: on the boat landing / dock (along ~18300-19300, across -5300..6200), eye height, looking up the
  first lane inland.
- In frame: a 6-8 m lane between the quay silos and shed_a, wet quay slabs, one sodium lamp, a slot of sky.
  **The tower is not in frame** (A-401 stations 1-4 hidden; Cine8 hides it at stations 3-4).
- Light: blue hour; the lamp is the key; close zone fog (start ~1000 uu, end ~25000) inside the dock
  zone only.
- Emotion: dread, arriving somewhere that does not want you.
- Build: the lane as a compression slot (walls 2-3x the lane width tall); one lamp, not a row; the PA
  voice (the writer's PA lines) heard before any person is seen.

**F8. The glimpse over the roofs: exposure (beat 2).**
- Camera: spine_mid (along ~12000-13000, between the mess/dorm and hall_a), eye height, looking along the
  spine toward the tower.
- In frame: the spine as a straight stretch of 60 m (the datum, the ore line beside it), the
  pylon/lamp/pipe-rack bents as rhythm, the dorm roofline (7 m) low enough that **the tower's top shows over
  it on the upper third**. This is the first time the player sees it, and it is only the top.
- Light: dusk, the sun ahead-left of the camera (side to back light); the tower top catches the last sun
  while the street is in its shadow.
- Emotion: exposure. It has been watching you the whole time.
- Build: align one spine stretch on the tower (Disney's weenie at the end of Main Street); cap the roof
  heights in that stretch; the tower's red light on top (one bold accent).

**F9. The mess window: the only warm room (exterior, blue hour).**
- Camera: across the street from the mess (along 12200, across -2400), looking at its long side.
- In frame: one long lit window strip, figures at tables, the dark wet street, a puddle reflection.
- Light: the window is the key (warm 2700 K look); the street is lit only by it and by one lamp.
- Emotion: longing; the one social building (G.U.A.R.D.S. social hub).
- Build: see I3 (the mess interior); a window strip with an emissive/translucent pane; 2-4 figures inside.

**F10. The company gate: smallness (beat 3).**
- Camera: at the company_gate, at the foot of terrace_wall_main, about 150 m from the tower, looking up
  25-35 deg.
- In frame: a **battered (sloped) concrete wall** filling the lower 60 %, a stair cut into it climbing
  diagonally (the leading line), and the stepped Aztec mass of the tower above, cut against the sky.
- Light: the wall in shadow, the tower top lit (the sun is behind the tower's left edge, so rim light on
  its edges).
- Emotion: smallness; the company holds the high ground.
- Build: the battered wall + stair cut-in on terrace_wall_main (the engineer's batters/benches/walls[]);
  a figure on the stair halfway up for scale (1.8 m against a 15-20 m wall).

**F11. The drainage culvert: the quiet stretch (LD7).**
- Camera: inside a culvert under the company terrace, looking toward the outflow.
- In frame: a round or box culvert 4-5 m across, water on the floor, the bright mouth 40-60 m ahead,
  and **a silhouette in the mouth** that is not the player's (the staged reveal).
- Light: dark interior; the mouth is the only key; the water floor reflects it (a leading line). The
  culvert lamps go out one by one as you walk (the first-Skaarj recipe: the space turns).
- Emotion: isolation, then a threat.
- Build: one culvert where a gully crosses the spine (hillside.py gullies, drainage.py when it exists);
  3-4 AvalonLamps the script switches off; a junction arena at the outflow (the level designer, LD5).

**F12. Ore Hall A: north light (interior).**
- Camera: inside hall_a by the left personnel door, looking along the hall toward the front roller bay.
- In frame: the sawtooth roof's glazing making parallel shafts (dust and steam), conveyors and
  the ore line, the half-open roller door framing the cooling towers outside.
- Light: shafts from the sawtooth (they need a dark occluder, a bright source and particles); the
  doorway at 90 %.
- Emotion: labour, scale.
- Build: hall_a as an enterable shell (I4); steam puffs inside; one roller door open.

**F13. The dorm gallery: Hashima rhythm.**
- Camera: on the dorm's outdoor access gallery (single-loaded, on the dock-path side), looking along it.
- In frame: one-point perspective of doors and window bays; laundry; every third lamp dead
  (decline); at the gallery's end an opening that frames the tower.
- Light: dusk sky at one end, lamp pools along the way.
- Emotion: crowding, routine.
- Build: an outdoor gallery on the dorm mesh (I5). It is cheaper than a full interior and gives the
  frame.

**F14. The flare rigs from the sea deck (Q70, "oil rigs in the distance sound nice").**
- Camera: the tower's seaward balcony, looking toward the rigs (15-18k uu out, inside the sea plane).
- In frame: 2-3 rigs on the horizon line, flares flickering, their reflections, smoke leaning one way.
- Light: night or late blue hour; the flares are the only warm points (the glowing-eyes-in-fog idea:
  a few bright points on a dark ground).
- Emotion: distance, other people's work going on.
- Build: Q70 (the rigs inside the sea plane); the zwrite rule (Q59) for the plumes over water.

### Beat map for TutA (where the parti's four beats live on the tower route)

| beat | parti | on the tower route | frame |
|---|---|---|---|
| 1 dread | compression, tower hidden | the corridor (no views, lamp stepping stones) | F3 |
| 2 exposure | the tower glimpsed | the overhang deck (the town shown, the tower felt above you) | F4 |
| 3 smallness | battered wall, stair | the stair down past the tower's sloped base (look up at it) | F10, tower version |
| 4 melancholy | release | the catwalk | F5 |

F1 sits before all of them (the start, ownership), and F6 is F1 again later (the turn).

---

## 2. Interiors: lighting and framing

General rules for every interior:
- **Doorways are frames.** Place every door so that the view through it lands a landmark on a third
  (LD4 for rooms). A door that opens onto nothing gets moved.
- **One key per room, and it is motivated.** The key is the window or doorway in the day and a practical
  (a lamp, a console, the flare) at night. Fill comes from the bounce (zone ambient, GI) and is never as
  bright as the key.
- **Shown, hidden, revealed inside too.** Corridors hide; rooms reveal. Never give a window view from a
  corridor if the next room has the big one.
- **The path is lit, the frame is dark** (see the value ladder in section 3).

**I1. Command room (TutA, stock BSP).** The window is the key. Zone ambient 46/24/140 (Q80) is the fill.
Recesses: the 12 floor-corner AvalonLamps (Q31), with the 4 nearest the window turned off so the glass is
unrivalled. Consoles: dim the screens that face the window (U2Shaders tint= on their texture hashes, or
lower their emissive). Characters: AmbientGlow 30, until ApplyAmbient writes AmbientVector (Q71). Rain:
NoRain box (Q50). Post: vignette 0.5 (Q54). Check that it does not crush the corners to black; 0.35 may be
the right value indoors.

**I2. The catwalk and decks (TutA).** Keep the slabs overhead unlit (they are the frame). Light the floor
from below or beside: the lit terrain under the gratings is the cheapest fill there is. One lamp pool per
deck, near where the player steps out. Rain on outside, NoRain under the slab. Q57's bright gap
texture between the deck plates breaks the frame: fix it first.

**I3. The mess (new interior, generated maps).** One long room 16 x 9 m (the sheet). One long window
strip on the street side, the bar at the back (Haldane's). 3-4 low-hanging practicals, each a warm pool
on a table, with the room between them in shadow. The camera inside looks back out through the window
strip at the plant (the steam and the cooling towers lit). This is Hopper's diner turned around: from
outside it is the only warm box (F9); from inside the cold plant is framed in it.

**I4. Ore Hall A (new interior).** Sawtooth north-light glazing → parallel shafts; the steam puffs inside
supply the particles. One roller door open, framing the hero. Lamps: high-bay sodium, every other one out.

**I5. Dorms.** No full interior. An outdoor gallery (Hashima Building 31's rhythm) on one long side, plus
one open room at the gallery's end with a bunk, a locker and a window that frames the tower (the "you
sleep under it" shot).

**I6. Drainage culvert (new).** F11. 40-60 m, a bright mouth, water floor, lamps that go out on a script.
It is also the storm-proof link (Hadley's Hope had its tunnel to the processor).

**I7. The pump house / intake (optional).** Stalker's flooded rooms: water on the floor, one shaft of
light from a roof hatch. Only if there is time. It is the second quiet space.

Interior-to-exterior reveals, ranked by payoff: F2 → F1 (the cine opens the window), F3 → F5 (the corridor
to the catwalk), I6 → the outflow arena, I3's window strip, the hall's roller door.

---

## 3. Light, fog and weather per beat (a colour script)

What U2 and our tools can do:
- **Sun:** a baked directional light (lowsun.py re-aims it and relights terrain + meshes into <map>_Dusk).
- **Ambient:** zone ambient with FLUSH live (AvalonCards Ambient="B H S", `avalon ambient`); pawn
  AmbientGlow.
- **Lights:** AvalonLamp (dynamic light + glow, traced to walls); AvalonPlume flare lights (flicker).
- **Fog:** ZoneInfo DistanceFog per zone (outdoor now 4000-90000, warm 196/176/156). The sky zone ignores
  fog, so the storm uses ClientAdjustGlow + the dome.
- **Storm:** AvalonStorm (10/3/5 min cycle; fog 2000/60000; rain streaks + mid/far rain sheets + splashes;
  lightning = dome swap + ClientFlash + fog flash; thunder/wind loops; NoRain boxes).
- **The d3d8 fork's post:** bloom, grade (lift/gamma/gain/sat), colour, sharpen, vignette (0.5 now),
  SSAO (radius 100-150 indoors, ~350 outdoors), the rim term in ssao.hlsl (off: the window glass writes
  depth), gi-cascades GI with a world cache (ambient fill in dark rooms: **the honest fix for "too dark"**),
  PCSS shadows, a LUT strip (the Advent build has lut=), grain/CA via postfx=, zwrite= for the plumes,
  the hex anti-tiling terrain shader.

**The value ladder** (luminance 0-100, check by squinting or with the blurred 4-level frame from the
report's point 4):

| group | interior | exterior dusk |
|---|---|---|
| frame (slab, pillars, mullions) | 3-8 | 5-10 |
| path / floor the player stands on | 18-30 | 15-25 |
| midground (town) | - | 30-55 |
| key (window, horizon band, doorway) | 75-95 | 70-90 (horizon) |
| accents (flare, red tower light, lit window strips) | the brightest *small* things only | |

The UE2 vertex lighting turns darks black (the palette memo), so the frame darks must be authored at
about 10, not 0, or they become holes.

**Colour script:**

| beat / frame | hour | key | fill | fog (zone) | weather | post |
|---|---|---|---|---|---|---|
| F1 ownership | dusk, sun el 6-9 behind | the low sun on the plant | sky blue, zone ambient | outdoor 4000-90000, warm | clear, parallax clouds (keep, Q52) | the "Clean" grade, bloom 0.7 |
| F2/F3 cine + corridor | same | window / lamp pools | ambient 46 + GI | none inside | rain heard, not seen | vignette 0.35-0.5 |
| F4 deck | dusk | the sun ahead-left (rim) | ground bounce | outdoor | light rain, the plumes | the same |
| F5 catwalk | sunset +5 min | the horizon band | lit ground below the grating | outdoor | rain streaks in the foreground | a little bloom on the horizon |
| F6 storm | storm | lightning, lit windows | ClientAdjustGlow | storm 2000/60000 | full storm | grade cooler (the "cold" preset values) |
| F7 dock | blue hour | the one sodium lamp | sky | **dock zone 1000-25000, cool grey** | drizzle | grain up a touch |
| F8 glimpse | dusk | sun on the tower top | street in shadow | outdoor | dry | - |
| F9/I3 mess | blue hour → night | the warm window | street lamp | outdoor | after rain (wet ground, the fork's next item) | - |
| F10 gate | dusk | sun rim on the tower edge | the wall in open shade | outdoor | dry | - |
| F11 culvert | any | the mouth | the water's reflection | culvert zone: short fog, so the mouth blooms | dripping | - |
| F14 rigs | night | the flares | none | outdoor, sea | calm | bloom on the flares |

---

## 4. Keep, cut, add

**Keep:** the peak catwalk exactly as it is; the parallax clouds (Q52); storm fog 2000/60000 (Q60, "oh
nice"); the rigs with flares (Q70); the summit-rich / slope-shanty hillside (Q74); the smoke plumes;
the crane tower as THE landmark; the side-lit low sun at az 136.

**Cut:**
- far copies of the crane tower beyond one (Q11's 3 complexes): one echo at most, at under 1/3 of the
  hero's apparent height;
- any second tall vertical in the window frame that ties with the hero (a chimney stack that matches the
  cooling towers' height: lower it or move it off the thirds);
- console screens brighter than the window;
- lamp rows where one lamp would do (F7, F3: rhythm beats evenness);
- any roofline that is tangent to the horizon or to the window mullion in F1 (the report's "no tangents").

**Add:** the F1 start pitch; the tower-shadow term (housing shadowed, hero lit); the catwalk figure; the
battered wall + stair at the company gate; the mess interior; the hall_a shell; the dorm gallery; the
culvert; rain in the light cones; wet ground; one red aircraft light on the tower top (the single accent).

---

## 5. References (web only, nothing downloaded; they inform the design and never ship)

| # | Page | Artist / source | Licence | What fits | For |
|---|---|---|---|---|---|
| R1 | https://www.pakutaso.com/en/2019035507831.html | susi-paku (PAKUTASO): Hizen Hashima lighthouse seen from a ferry through Building No. 31 | PAKUTASO free licence (commercial and non-commercial, no attribution needed, Terms of Use apply) | A landmark seen *through* a concrete company block: frame within a frame, grey mass vs a white vertical | F13 dorm gallery end; F1 mullions |
| R2 | https://www.usgs.gov/media/images/oil-drilling-platform-offshore-huntington-beach-california | Pete Markham, USGS Pacific Coastal and Marine Science Center | Public domain | An offshore rig back-lit by the setting sun: pure silhouette on a warm band, calm sea | F14 rigs; F5 horizon band |
| R3 | https://commons.wikimedia.org/wiki/File:Lagoon_Drain_-_Brisbane_-_Dark_Days_(16419817739).jpg | "darkday" (Flickr), Lagoon storm drain, Brisbane | CC BY 2.0 | A "silhouette light block" shot: a figure black against a storm-drain outflow, the tunnel as the dark frame | F11 / I6 culvert reveal |
| R4 | https://commons.wikimedia.org/wiki/File:Rolltreppe_Zeche_Zollverein.JPG | Martin Falbisoner (Zeche Zollverein, Essen; escalator by OMA) | CC BY-SA 3.0 | A long orange-lit diagonal climbing into a dark industrial mass: a stair as the leading line, the one warm colour | F10 company gate stair cut-in |
| R5 | https://digitalcommons.usf.edu/gandy/5945 | George "Skip" Gandy IV, "Structural Component of Walkway at Gulf Foundation" (c. 1970) | CC BY 3.0 (the page's badge says BY-NC-SA: treat it as reference only) | Grated walkway, bolted brackets, railings: what the catwalk's material should read as up close | F5 / I2 grating and rails (the artist's parts) |
| R6 | https://energytransition.org/gravelines | Serge Ottaviani: Gravelines nuclear plant control room | CC BY-SA 3.0 (repost; the page says modified) | A 1970s control room: long console rows, low panels, the operators' posture | I1 command room consoles (keep them low, under the glass) |
| R7 | https://unsplash.com/de/fotos/industriegebaude-silhouette-gegen-den-dammerungshimmel-xFbDJRuLz4c | Muhammad Rasel | Unsplash License | A factory with chimneys as one flat dark shape against a dusk gradient: the 2-value read of the plant | F1/F6 the plant's silhouette test |
| R8 | https://neiloseman.com/roger-deakins-oscar-winning-cinematography-blade-runner-2049/ | Neil Oseman on Roger Deakins, *Blade Runner 2049* | Article; film frames are copyrighted (reference only) | Smog, rain and mist reduce people to silhouettes; abandoned Las Vegas in one orange haze; Wallace's gold Brutalist rooms lit by moving water (motivated light) | F5, F6 (the storm turns people to shapes); I1 motivated light |
| R9 | https://xsmultimedia.com/2022/07/15/film-and-shadow-the-power-of-silhouettes-with-cinematographer-roger-deakins/ (+ https://www.motionpictures.org/2015/10/sicario-reunites-director-denis-villeneuve-cinematographer-roger-deakins/) | Roger Deakins / Denis Villeneuve, *Sicario* | Articles; frames copyrighted (reference only) | "Silhouettes crushed by the sun"; agents walking into the dark at dusk against a fire-red horizon; the storm sky as a character | F5 lone figure; the colour script's sunset band |
| R10 | https://velveteyes.net/?p=6698 | Stan Lamontagne on Tarkovsky's *Stalker* (1979) | Article; frames copyrighted (reference only) | Shot at dusk with black cloths to hold the sky down; rooms flooded with water, walls seeping, rain indoors as mood | I6 culvert, I7 pump house; "cheat the sky down" for F5 |
| R11 | https://www.combineoverwiki.net/wiki/Citadel_design_evolution | Viktor Antonov, Dhabih Eng, Eric Kirchmer (Valve), Half-Life 2 | Concept art © Valve (reference only) | "Inner wall towered by the Citadel": a wall at street level with the landmark rising over it; the train platform with the Citadel far off | F10 smallness; F8 glimpse over the roofs |
| R12 | https://www.thumbsticks.com/gdc-2015-the-art-of-firewatch | Jane Ng / Olly Moss (Campo Santo), GDC 2015 | Article; art © Campo Santo (reference only) | Fog in coloured layers for depth; a colour script per story moment; flat shapes with strong silhouettes; a lookout tower as the home view | Section 3 colour script; F1 layers |
| R13 | https://parkablogs.com/content/book-review-art-of-halo-5-guardians | Sparth (Nicolas Bouvier), *The Art of Halo 5* (review) | Book art © Microsoft (reference only) | "Strong use of black as composition elements to frame scenes" with soft colour gradations beyond: the dark-frame rule | F4, F5 the slab as frame |
| R14 | https://www.avpcentral.com/hadleys-hope-colony | *Aliens* (1986): Hadley's Hope | Fan wiki; film © 20th Century (reference only) | A company colony in constant wind and rain, a storm wall on one side only, a tunnel to the processor so nobody has to go outside | F6 storm; I6 the culvert as the storm-proof link; the writer |
| R15 | https://www.artic.edu/artworks/111628/nighthawks | Edward Hopper, *Nighthawks* (1942), Art Institute of Chicago | © Heirs of Josephine N. Hopper (licensed by the Whitney): reference only | The only lit room on a dark street; the window strip as the key; figures seen through glass | F9 / I3 the mess |

Also for the user's own board: the peak frame (design-refs/avalon_peak_frames/catwalk_dusk_silhouette.png)
is reference zero. Every frame above is tested against it: is there one dark frame, one leading line, one
silhouette, one bright band?

---

## 6. Notes for the other roles

**Writer**
- Q56 (rewrite the intro cine): my shot plan is F2 → F1. Hold on Hawkins' face, delay the town, then the
  turn. Give him the line that names the shadow ("we built it on the high ground so we'd see them coming";
  your words, not mine).
- Name the lone figure on the catwalk (F5): who stands out there at dusk, and why alone? A garrison marine
  on a smoking break, or Vask? He is the staffage that makes the frame.
- The PA lines play at the dock (F7) before any person is seen. The radio chatter goes in the culvert (F11).
- The mess (I3) is the only social room: put one overheard conversation there.

**Engineer**
- Company gate (F10): a battered retaining wall (1:4 to 1:6 batter) with a stair cut into it, 15-20 m high,
  the stair at a real grade (with landings every ~3 m of rise).
- Culvert (F11/I6): where a gully crosses the spine or the terrace; 4-5 m across, 40-60 m long, water
  depth a few cm.
- The tower's shadow (F1): it needs the real height; check the plateau, so that at el 6-9 the shadow
  reaches the housing at 200-400 m and leaves the hero lit.
- One spine stretch of 60 m aligned on the tower for F8; roof caps of about 7 m along it.

**Level designer**
- The culvert is your LD7 quiet stretch; the outflow is the LD5 arena (a bright mouth = a natural stage for
  the reveal; mind the 41 m hitscan rule on the open ground past it).
- Protect F5 and F1: no combat on the catwalk or in the command room. They are rest beats (the L4D
  relax).
- TutA's beats live on the tower route (the beat map in section 1): corridor, deck, stair, catwalk. Check
  LD2 pacing there, not only on the dock walk.
- Generated maps: put the PlayerStart at the dock so beat 1 exists.

**Artist**
- The value ladder (section 3): frame darks at about 10, never 0 (the UE2 vertex lighting crushes them).
- The grating texture needs alpha holes so the lit ground below reads through (that is why the peak frame
  works).
- One loud accent per frame: the red light on the tower top, the orange stripe on the dorm pods, the
  flares. Not all three in one frame.
- The tower silhouette: stepped and battered (Aztec), unique on the skyline. Cut the copies.
- The mess window strip: an emissive/translucent pane, warm; figures visible through it.

**For codirect.py (whoever edits it next; I did not edit any code)**
- Fix the sun rule (section 0.1) and score per view: the window by "housing in shadow, hero lit", the decks
  and catwalk by back light (off ≤ 60).
- compose.py PITCH -28 → -9, and score the horizon on the upper third (section 0.2).
- Add a "hero unique" check: no other building in the frame at ≥ 2/3 of the hero's on-screen height.
