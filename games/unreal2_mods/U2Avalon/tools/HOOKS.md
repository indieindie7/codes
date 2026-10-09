# Hooks: the binder's story keys in the town generator

Binder 1940260 added keys the generator did not read: room sheets, `building:room` stops, `takes:`, the `conc`
resource, rule-placed story buildings, and the parti's hero. This file records where each one is wired in. The
wiring was applied on top of 24a454b. That commit already did the hero swap in compose.py, codirect.py and
layout_spine.py, and the `conc` chain in systems.py, so those parts are not repeated here.

## The modules

| module | reads | writes | CLI on a run folder |
|---|---|---|---|
| `binder.py` | `binder/rooms/*.md`, `rooms:`/`takes:` keys, `tower:catwalk` stops | `load_rooms()`; the checks | `py tools/binder.py` |
| `anchors.py` | heightmap + spine / layout | hero summit + truck road, guest_house, water_tower (E14'), the drain | `py tools/anchors.py <run>` -> `anchors.json`, `isl_anchors.png` |
| `takes.py` | layout with systems connections | `L["taps"]`, clutter props, conc report | `py tools/takes.py <run>` -> `taps.json`, `isl_taps.png` |
| `rooms.py` | sheets + room sheets (+ layout) | interior plans | `py tools/rooms.py <run>` -> `rooms.json`, `isl_rooms.png` |

The standalone CLIs never rewrite the run's layout unless you pass `write=1`.

## Pipeline order (town.py)

1. island, relief, viewshed (unchanged)
2. per candidate: `layout_spine.py`
   - section 3, after the anchors: `anchors.summit()` puts the parti's hero on the summit and adds its truck road
     as a branch;
   - section 4: `RULED` = {guest_house, water_tower, drain} are left out of the plot order;
   - after the plots: `anchors.beside()` (guest_house) and `anchors.water_tower_site()`;
   - at the output: `anchors.drain()` -> `out["drain"]` + `buildings["drain"]` (underground, at its grate), and
     `out["anchors"]`.
3. town.py: if a reused layout lacks the hero or the drain (an older layout), `anchors.apply()` places them
   late; then `systems.run()` (conc already in its chain, 24a454b), compose, codirect.
4. cut/fill, viewshed, `walks.py` (the drain is a tunnel edge between its grate and outfall:
   `anchors.walk_edges()`; kind `culvert` isn't walled).
5. **`story_extras()`** (new step after walks): `takes.taps()` -> `L["taps"]`; `rooms.build()` -> `<run>/rooms.json`;
   `isl_taps.png`, `isl_rooms.png`, `story.txt` (summit, water head, drain, taps, conc chain, interiors);
   report.md gets a "Story keys" section.
6. drawings, plans, metrics, the final review (unchanged); `clutter.py` places the taps' poles and drums
   (`takes.clutter_items`).

## The diffs, in short

layout_spine.py, after the anchor loop in section 3:

```python
import anchors
RULED = {"guest_house", "water_tower", "drain"}
SUMMIT = None
if PARTI_HERO in buildings and PARTI_HERO != "tower" and PARTI_HERO not in placed and o.get("summit", "1") != "0":
    SUMMIT = anchors.summit(Z, SPINE.pts, buildings[PARTI_HERO], MAIN, avoid=[...tower, authority_pad, dock, mine...])
    if SUMMIT:
        place(PARTI_HERO, SUMMIT["x"], SUMMIT["y"], SUMMIT["yaw"])
        ROADS.append(Road([tuple(p) for p in SUMMIT["road"][::-1]], "branch_summit"))
```

```diff
-order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed]
+order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed and bid not in RULED]
```

After the plot loop: `anchors.beside(placed, buildings, "directors_house", "guest_house", Z)` and
`anchors.water_tower_site(Z, placed, buildings, main=MAIN)`, each followed by `place()`. Before `json.dump(out)`:
`anchors.drain(Z, out, buildings, MAIN)`. Flags: `summit=0` and `drain=0` turn them off.

walks.py:

```diff
-NOT_WALLED = (..., "mast")
+NOT_WALLED = (..., "mast", "culvert")
+TUNNELS = anchors.walk_edges(L.get("drain"), to_fine, nearest_free, NF)
-        G = graph(wear, [(S, k, pen) for _, k, pen in ea])
+        G = graph(wear, [(S, k, pen) for _, k, pen in ea] + TUNNELS)
```

clutter.py, section 2d: `for mesh, x, y, yaw, scale, lift in takes.clutter_items(L["taps"]): actor(...)`.

compose.py (the coordinator's pick, 2026-10-09): `PITCH = -15.0`, so `PITCH_RU = 62805` (-2731). codirect's
horizon check reads `compose.PITCH`, so it follows. The command room's PlayerStart in the map should face Pitch
62805.

## The hero

Already done in 24a454b: `parti.json "hero"` with a `"tower"` fallback.
- compose.py: hero = the parti's hero if it is in frame, else `second` (cooling_towers), else the tallest.
- codirect.py: `hero_id()`.
- layout_spine.py: `PARTI_HERO` in `hides_tower`.

The ids that still read `"tower"` mean the Authority tower on purpose: the window's eye, the walk's end, the 150 m
squatter guard.

## The rules, round 2 (the coordinator, 2026-10-09)

- **The hero in the window.** The summit candidates are scored in compose's frame: yaw 300 ± 34, pitch −15 ± 26,
  with the top not hidden by the terrain.
  - Any spot in the frame beats any spot outside it, so a lower summit inside the cone wins over a higher one
    outside.
  - Inside the frame, height wins, plus 25 m of "height" for a vertical third. A spot at the frame's side edge
    (u < 0.1 or u > 0.9) gets half the bonus.
  - If the town's strip has no spot in the frame, the search widens to 600 m from the town's spine. Only then does
    it fall back to the highest spot outside the frame, logged on stderr and marked `fallback`.
  - The hero's dock clearance is 100 m (it was 150 m, which emptied Cine8's frame).
- **The truck road** is grade-capped. A step over `MAX_GRADE` (12 %) is closed, the routing uses 16 headings
  (knight moves), and the road switchbacks. The cap is relaxed only when no capped road exists (×1.25, ×1.5, ×2,
  then soft), and `road_cap` records it.
- **E16 for rule-placed dwellings.** The guest house stays ≥ 100 m from every fuel store (`systems.spec_of`
  providers of fuel). It walks up to 60 m further out, or behind the host, to manage it. If it can't, it is
  flagged `e16_ok: false`.
- **The drain profile** is laid from the outfall upstream:
  - The invert is +0.5 m over the sea at the outfall (a free outfall). Going upstream it rises by the 0.5 % fall,
    and the cover over the roof never exceeds 12 m.
  - Where the invert then drops faster than the fall, the step is a drop shaft (`drop_shafts`).
  - Where the cover is under 1 m (outside the last 15 m, the headwall), the run is a covered cut at grade
    (`shallow_m`).
  - The route avoids ground more than 12 m over the grate, and the outfall prefers a bank high enough for the
    culvert.
- **Splices.** When a company line already passes the shanty block (a run under 4 m), the tap becomes a splice:
  sagging leads (power) or hoses with drums (water) from the line to the nearest 3 shacks, each at least 3 m long.
  The styles are `splice_cable` and `splice_hose`.

## Still open

- No sagging-cable mesh exists. The spans and drops are in `L["taps"]` as lines with `sag_m`, and the poles use
  the Pylon at 0.45 scale. A crooked-pole part and a cable part are build_parts work.
- export_mutator doesn't build the drain yet. `L["drain"]` has the polyline with ground and invert z, the section
  sizes and the segments (grate, culvert, junction room, sluice gallery, outfall). The shell build needs a
  `B_culvert` part (artist s. 5).
- `rooms.json` is input for the hollow-shell kit (engineer s. 2.0), which doesn't exist yet.
