# Avalon redesign, 2026-10-09: the WRITER

Role: the story and the town model (codirect.py WRITER). I own the parti (the sentence, the beats and their
emotions), the citizens, why each place exists and who uses it, and the systems that make the town work.
Written during the playtest swap (PIPELINE.md "Playtest swap"), so nothing here was generated or rendered.
The web references in section 7 are for reading only: nothing was downloaded and none of it ships.

Sources read: PIPELINE.md, README.txt, codirect.py, binder/ (parti, 22 citizen sheets, 44 building sheets, PA and
radio lines), marks/MARKS.md + QUEUE.md (to Q81), U2AvalonCards/AVALON_BRIEF.md and building_plans.py, the
cinematography report, and the memory notes (peak frame, Aztec, Y2K, Emotion x Action, Sam Hyde, encounters,
remix rules).

---

## 0. The short version

1. **Two towers, two characters.** The binder's `tower` is the Authority's: old survey concrete, the
   player's home, the camera. The hero the parti needs is a different building, the Liandri stepped
   temple-tower (CraneTower in U2AvalonCards), on the summit. The company built lower and still stands higher.
   The sentence finally reads literally: *the company holds the high ground*. (Section 1.)
2. **The lone figure in the peak frame is Hawkins.** At dusk she stands on the tower catwalk and looks at the
   company's tower. The player sees her from 40-100 m on the way up. Beat 4 (melancholy) becomes a person, not just a view.
3. **Interiors tell the three-powers story by whose stuff is where.** Every room has an owner, one prop that
   is the room's sentence, and one sign of the other two powers intruding. (Section 3.)
4. **The drain is the outlaws' road.** A new building, the outfall culvert, runs under the spine from the
   works to the sea. Arashiro's stain, Haldane's weep and Rook's crates are all down there. It is the
   level designer's LD7 quiet stretch, and its end is the staged reveal: one light on where there should be none.
5. **The census is the story.** The binder counts 380 people, which is the company's number. The shanty the
   user asked for (Q74: "doesn't look like a 300 people town") holds about 500. The gap is Tin Row:
   "officially not here". I raise the Tin Row groups and add the laid-off deckhands of Ship Row. (Section 4.)

---

## 1. The parti, kept and sharpened

The sentence stays (approved, Q36): **"The company holds the high ground; the town lives in its shadow and its
smoke."**

**What changes: the hero.** `parti.json` says `"hero": "tower"`, and the binder's `tower` is the Authority
tower, "the tallest building on the island and the poorest". U2AvalonCards' building_plans.py makes the
CraneTower the HERO ("the company's stepped temple-tower on the high ground"), and the user picked that
Aztec mass as Avalon's Liandri landmark (memory: design-taste-aztec-dystopian). The two documents contradict
each other. The player also *lives in* the Authority tower (TutA), and you cannot frame the building you stand in.

Proposal:
- `hero: liandri_tower` (new sheet below). It stands on the summit where Q74 already put "the rich/company".
  Battered stepped base, setback tower, red domes, lattice crane. It is the weenie of the whole walk and the focal
  point of the command-room window.
- `tower` stays the Authority's. Rewrite its line to "the **oldest** building on the island and the poorest".
  Measured from its own foot it is the tallest. The Liandri tower's top stands higher only because of the hill.
  That is the whole politics of the island in one section drawing (A-201 section A should show it).
- `second: cooling_towers` stays as the counterpoint, with the steam as the motion that strengthens it.

**Beats: the four approved ones stay**, in order, with the same emotions. I add interior beats *between* them
(section 2) and give beat 4 a person:

| # | at | emotion | move (as approved) | writer's addition |
|---|---|---|---|---|
| 1 | dock | dread | compression, tower hidden | the barge's mooring lines groan; the PA (pa08) fees; the Liandri tower hidden behind the quay silos (already PASS in Town7) |
| 2 | spine_mid | exposure | tower glimpsed over roofs | the glimpse is the **Liandri** tower, lit; the Authority tower behind it is dark |
| 3 | company_gate | smallness | battered wall, stair cut-in | the gate is the foot of the Liandri tower's plinth: the stair is ceremonial, the road beside it is for trucks |
| 4 | catwalk | melancholy | release: dark frame, grated catwalk, lone figure 40-100 m, dusk rain | **the lone figure is Hawkins**, at the catwalk rail, facing the company's tower and the dead rig's one light |

Proposed `parti.json` diff (for the user to approve; I have not edited the binder):

```json
 "hero": "liandri_tower",
 "second": "cooling_towers",
 "beats": [
  {"at": "dock", "emotion": "dread", "move": "compression, tower hidden"},
  {"at": "spine_mid", "emotion": "exposure", "move": "tower glimpsed over roofs"},
  {"at": "company_gate", "emotion": "smallness", "move": "battered wall, stair cut-in"},
  {"at": "catwalk", "emotion": "melancholy", "move": "release: dark frame, grated catwalk, lone figure 40-100 m, dusk rain", "figure": "hawkins"}
 ],
 "interiors": ["mess", "tin_bar", "drain", "tower:command_room", "tower:catwalk"]
```

---

## 2. The beat sequence, exterior and interior (Emotion x Action)

Each row says what the player DOES and what they should FEEL, and checks that the space does both. The route
runs dock to tower, as in the parti. TutA's canon flow (command room, then the lift, then the dropship) runs the
other way and is the *bookend*: the player sees this town from the window first and walks it after.

| # | place | in/out | ACTION | EMOTION | what the space does |
|---|---|---|---|---|---|
| 0 | command room (TutA opening) | in | listening to Hawkins, looking out | irony: "the quietest patrol" | the window shows a busy, lit town; the room is dim; Oduya's board shows only company flights |
| 1 | dock | out | stepping off the shuttle, walking the quay | **dread** | silos and containers close in, the hero is hidden, the barge creaks, the PA speaks |
| 1a | the mess | in | passing through the one warm room | belonging that excludes you | everyone eats here; nobody looks up at a marine; the mural sells the company you just saw |
| 2 | spine mid | out | climbing the main street | **exposure** | the roofs open and the Liandri tower appears, lit; the cooling towers steam |
| 2a | Tin Row lane + the Tin Bar | out/in | a side lane, a door ajar | intimacy, then guilt | the company kit turned into homes; the bar is the one table where a hand and a marine sit |
| 2b | the drain (LD7 quiet stretch) | in | following the culvert under the spine | unease, then curiosity | 25-60 s of no beat: water, a pump, the weep, Rook's crates; it ends at a junction where one light is on |
| 3 | company gate | out | climbing beside the battered plinth | **smallness** | a ceremonial stair for nobody, a truck road for everything; the checkpoint hut is tiny next to it |
| 3a | the checkpoint (Authority hut) | in | passing Nkemelu's barrier | sympathy | a log nobody reads; the barrier is up |
| 3b | the tower lift and stair | in | going up, alone | compression | concrete, few lights, one company cable cored through the wall |
| 4 | catwalk | out | stepping out of the dark frame | **melancholy** | grated catwalk, dusk rain, Hawkins at the rail 40-100 m off, the Liandri tower lit on its hill, the dead rig's one light |

Rhythm check: the three exterior beats (1, 2, 3) are already in the level designer's LD2 budget (a beat every
60 s ≈ 315 m). The interiors add rests, not walking time, apart from the drain. The drain IS the LD7 quiet stretch
and has to be timed (see notes for the LD).

---

## 3. Interiors: what story each room tells, and whose stuff is where

Format per room: **owner**, the **sentence** (one line, the "one good frame" of the room), the **props by owner**,
the **intrusion** (the other powers showing up), light, and what the room needs from the others. Sizes are in
metres (1 m = 50 UU). The player walks 5.3 m/s.

### 3.1 The command room (TutA, existing): "busy out there, nothing in here"
- **Owner:** the Authority (Hawkins, Oduya).
- **Sentence:** the long window is the brightest thing in the room, and the room behind it is dim.
- **Props, Authority:** Hawkins's desk, clean and unused (she stands); her binoculars on the sill, aimed at the
  dead rig, not at the plant; Oduya's traffic board, a row of green company callsigns (LIANDRI CARGO 21, RIG
  SHUTTLE) and no Authority traffic; one drawer of complaint forms in order; a charter-survey brass plate by the
  door from before the company came.
- **Intrusion, company:** the one power cable comes in through a rough cored hole with a stencilled tag, LIANDRI
  SUPPLY / PROPERTY OF. The Thursday brownout (pa03) dims this room first. The buzzing lamp (Q16) is the
  room's sound.
- **Intrusion, outlaw:** none inside. Only the light on the dead rig, *through the window*, if you know to look.
- **Light:** the window as the key light; warm practicals at the floor recesses (Q31) as low fill; the desk lamp off.
  This answers Q80 ("too dark now") as a story: dim by design, but the faces must read. Keep the AmbientGlow on
  pawns.
- **Leak:** Q50 fixed the rain falling inside. One drip under a skylight with a company-branded bucket under it
  says "nobody fixes the Authority's roof" without breaking the room.

### 3.2 The tower mess and garrison bunks (inside the tower, new rooms)
- **Owner:** the garrison (30 marines in rooms built for 60; `beds: 60` on the tower sheet).
- **Sentence:** half the bunks have rolled mattresses, so the room shows who isn't coming.
- **Props:** rolled mattresses, footlockers with stencilled names; one wall of transfer requests (Oduya's is the
  neatest); a card table with the Tin Bar's home-stilled bottle hidden in a locker; a TV/radio set to the
  company PA because it is the only channel.
- **Intrusion, company:** the food crates in the tower mess are stencilled with the company store's mark. The
  Authority buys its dinner from the landlord.
- **Light:** fluorescent tubes, one in three working.

### 3.3 The catwalk (TutA deck, existing): the peak frame
- **Owner:** nobody. It is the tower's maintenance catwalk; Hawkins uses it.
- **Sentence:** a dark overhang frame, a grated catwalk, one person at the rail at dusk, rain.
- **Props:** the railing (Q7/Q9 edge), a coffee tin of cigarette ends at the rail (Hawkins's), a wind sock, the
  antenna guy-wires as leading lines.
- **Figure:** Hawkins at 1930 (see her sheet below). If the engine cannot put her there, the garrison sentry
  stands in the same spot. The frame works with any lone figure, and it works best with her.
- **Fix that serves the story:** Q47/Q61, "deck too dark". The overhang should be dark; the *horizon* must be
  bright. That is the compression-release, so do not light the overhang flat.

### 3.4 The checkpoint, the Authority hut (sheet `checkpoint`)
- **Owner:** Nkemelu.
- **Sentence:** a thick logbook on a thin shelf.
- **Props:** the log (every company truck since she arrived); a chalk list on the wall of Benedek's drivers by their
  horns (two short = Petrak, one long = the fuel truck); a two-bar heater; a field radio; one chair; a mug.
- **Intrusion, company:** the barrier arm is up and tied up with a company strap, because the trucks don't stop.
  A company calendar on the wall (the only calendar she was given).
- **Reference:** the GDR command watchtower at Nieder Neuendorf (ref 13): observation floor, field telephone,
  holding cell below. Ours is the poor cousin: a hut, not a tower.

### 3.5 The company mess (sheet `mess`): the one warm room
- **Owner:** the company, run by the kitchen crew; the bar at the back is Haldane's, unofficially.
- **Sentence:** long tables under a heroic company mural, and everyone eating with their backs to it.
- **Props by owner:**
  - kitchen crew: a chalk "sick list" by the hatch (they know who is sick before the medic does); a tray rack;
    the urn that never cools;
  - the shifts: two halves of the room. The day line sits by the windows. The night line's end has its blinds down
    and a breakfast tray set at 1730;
  - rig crews: on their weeks in they hold the big table, with a rotation calendar crossed off in marker;
  - Haldane: a shelf of bottles behind a hatch that "isn't a bar"; his kettle is in shed B, his bottles are here;
  - the memorial: a framed copy of the eleven names by the door (the original is the plinth at the shore).
- **The mural (the room's sentence):** a stepped Liandri tower, a heroic miner, a gas giant, "PRODUCTIVITY IS
  PROSPERITY". This is the Pyramiden canteen mosaic idea (ref 5), turned to company propaganda. It also puts the
  hero building *inside*, so the player has seen the tower before the street shows it to them.
- **Intrusion, Authority:** no marines inside. The pa04 escort line plays from the speaker over the door.
- **Intrusion, outlaw:** a Tin Row trader's thermos of home-stilled spirit under a table.
- **Light:** warm, the warmest interior on the island. It is "belonging that excludes you", so the player feels
  the warmth and is not part of it.

### 3.6 The halls (hall_a, hall_b, hall_c)
- **hall_a (core):** patched panels; a **painted line on the floor** from the right door along the line: the
  director's five o'clock walk. The hands keep their tools off it. A shift clock with a punch-card rack.
- **hall_b (boom):** the canteen corner at the left end: a microwave on a pallet, a radio, a girlie calendar
  replaced by a company safety poster, someone's child's drawing taped to the poster.
- **hall_c, the dead hall (decline):** the roller door jammed half up. Inside: eleven lockers with names stencilled.
  They are the eleven of the memorial, never emptied. Blowout-year work orders on a clipboard. One locker is new:
  Rook stores fuel cans in it. **A staged-reveal room:** a light inside that should be off (Rook's lamp). This is
  the first time the player sees the third power up close (see 3.10).

### 3.7 The dorms
- **dorm (core, A):** two storeys of bunk rooms; per bunk, a photo, a scrip chit and a padlock. Reyes's bunk
  faces the window toward the dead rig because it was the last one free. Shared shower block with the pa06
  four-minute sign.
- **dorm_b (the long blocks):** the night shift's **blackout curtains** in every window (from outside this is the
  only dark row at night, and that tells the shift system without words). A drying room full of wet overalls that
  never dry.
- **dorm_c (the bunkhouse):** boots on the porch, dust on every floor, a peg rail of **masks that don't fit**
  (mine_crew "wants: masks that fit"), with a fitted one stencilled to a name nobody recognises.
- **Reference:** Gullfaks A's move from eight-man to single cabins (ref 4). Avalon's company has gone *back* to four to a room.
  Hashima's Nikkyu miners' flats, lightwell and kitchen (ref 3).

### 3.8 Tin Row interiors (shanty_a, shanty_b, shanty_c, tin_bar)
Rule (parti "transformation"): **the same company kit, turned into homes by additions.** Company panels
show up inside the shacks, often upside down, so the LIANDRI stencil reads backwards.
- **shanty_a (traders):** a barber's chair made from a dropship seat; a scale; a chalk price board in scrip AND in
  "real" (credits); Rook's goods behind a curtain.
- **shanty_b (families):** a **school corner**: a company hazard board scrubbed into a blackboard, children's
  benches made of pipe-rack offcuts ("wants: a school"). Water drums from the dock. Cables strung off the dock
  lights through a window.
- **shanty_c (Ship Row):** salvaged from the wreck: porthole windows, a ship's bell over a door, deck plating as a
  floor. Laid-off deckhands (new group below).
- **tin_bar:** two huts knocked into one, the seam still visible; the card table (a hand's cap and a marine's
  beret on the same table); a home still; a dart board with a Liandri logo for the target.
- **Reference:** Kowloon Walled City (ref 11): an "organic megastructure" that keeps changing to fit its residents.

### 3.9 The company store (sheet `company_store`)
- **Sentence:** the ledger is the island's real bank.
- **Props:** a counter with the ledger open; shelves of boots, tobacco, tinned fish, cards; a sign "SCRIP IS NOT
  LEGAL TENDER OUTSIDE THE COMPANY STORE" (pa02); the exchange window shuttered.
- **Reference:** Russell Lee's 1946 coal survey (refs 1-2, public domain): company stores and miners' homes.

### 3.10 The drain: the works under the town (NEW sheet `drain`)
- **Why it exists:** the plant's runoff and the desalination brine must reach the sea. The company dug one
  culvert from the works plateau under the spine to an outfall below the pump house. Everything the town wants to
  forget runs down it.
- **Who uses it:** Arashiro (inspects the outfall), Haldane (the weep at km3 is where the pipeline crosses
  it), and **Rook** (the culvert links the old boat landing to Tin Row and the dead hall without passing the
  checkpoint). It is the outlaws' road.
- **Sentence:** a long low vault of pillars, ankle-deep water, a tide line on every pillar, and at the far end one
  lamp that should not be lit.
- **Props:** Haldane's bucket and chalk mark under the weep ("KM3, 2nd YR"); Arashiro's sample jars on a ledge,
  dated, with the outfall stain getting darker jar by jar; Rook's crates on a pallet above the waterline, a
  rope to the boat landing; a company sign "NO ACCESS. MAINTENANCE MATTER" (the pa07 voice in paint).
- **The reveal (Unreal 1 first-Skaarj recipe):** foreshadow (the crates, wet footprints that are not yours, a radio
  playing r10 "there's a light on the old rig again"), isolate (the 25-60 s quiet stretch), stage (the lamp at
  the end is on; the player reaches it and it goes off). The fight, if the level designer wants one, is Rook's
  people at the junction where the drain opens into the dead hall.
- **Reference:** the G-Cans discharge tank (ref 12): pillars, puddles, low light, the scale of a cathedral.
  Ours is far smaller, about 6 m high.

### 3.11 The Liandri tower interior (NEW sheet `liandri_tower`): the one room the player is shown and not given
- **Sentence:** the scrip exchange hall: top-lit concrete, a queue rail for a hundred people, nobody in it, the
  windows shuttered "until further notice" (pa02).
- **Why the player sees it:** it is the counterpart of the command room. The company's room is generous with light
  and empty of people. The Authority's room is short of light and busy with nothing. Seen from the gate stair
  through a glass door; probably not enterable (LD's call).
- **Reference:** Kahn's National Assembly, Dhaka (ref 10), light as the material; Lasdun's UEA ziggurats (ref 9) for
  the stepped, terraced mass.

---

## 4. The census, the systems and the binder

### 4.1 The census is the story
The binder heads add up to about 380 (garrison 30 + 4 Authority named, hands 48, night 48, rig 36, mine 50,
dock 30, hauliers 24, kitchen 18, security 16, plant 20, families 24, traders 26, named 6). That is **the
company's census**. The shanty Q74 built has 105 homes (beds well over 260), and the user wants the town to look
like it holds 300+. Instead of shrinking the shanty, the writer's answer: **Tin Row is undercounted on
purpose.** The company counts its workers. The clinic treats families "off the books".
- tin_row_families 24 -> **60**; tin_row_traders 26 -> **40**;
- NEW `ship_row` (40): laid-off deckhands from the boom's end (shanty_c's sheet already says so, but has no
  group for them);
- result about 470 people, of whom about 140 are "officially not here". Put the company's 380 on the PA (pa13 below).

### 4.2 Systems the story needs to be visible (asks for systems.py)
- **The informal taps.** Tin Row has `needs:` empty because it has no legal supply. It still gets water (drums
  from the dock) and power (cables off the dock lights). Proposal: a key `takes: power water` = an informal
  connection, drawn as sagging cables and a drum path rather than pipes. The player should be able to *see the
  theft*. That is the transformation rule applied to systems.
- **The one cable to the Authority tower.** Already in the brief. Keep it a single line with no redundancy, and
  route it past the checkpoint so the company's line and the Authority's road cross at the hut.
- **Shanty in the smoke (Q36/Q37 finding).** The story reason the shanty must be downwind: *the downwind land
  was free because nobody would pay for it*. Write that into the generator as "reserve the plume land as
  nobody's land when the boom places", and let the decline layer take it. (Engineer/LD to check the order.)
- **The drain.** `provides:` none, `needs:` none, but it is a route: it counts as a path in walks.py for Rook,
  Arashiro and Haldane (it is how Rook reaches Tin Row without the checkpoint).

### 4.3 Keep, cut, add

**Keep**
- The parti sentence and the four beats (approved).
- The prefab-kit look (the user: it "really sells the industrial island where everyone is cutting costs").
- The dead rig's one light, the memorial, the old/new rig pair, the PA and radio voices. They are the cheapest
  storytelling on the map.
- Q51's shanty on contour terraces, Q74's rich on the summit, Q64's ring roads: they already serve "company
  high, town below".

**Cut or fold**
- **The second director's house (Q74).** There is one director. Fold it into a **guest house kept for the
  sector inspection that never comes**: lit, aired, unused (users: okafor; see the draft sheet).
- **The "Liandri business venue" (Q12: villa, lounge hall, flare lamps)** as a separate place. Fold it into the
  Liandri tower's terrace (the company's own lounge on the steps), so the high ground has one owner and one shape.
- **Duplicate crane towers (Q11's "sparse industrial complexes").** Three copies of the hero dilute it. Keep
  ONE Liandri tower. The copies become plain works (stacks, tanks) without the stepped base and red domes. The
  hero shape must be unique.
- **staff_houses abandoned in Town7 (Q37).** The generator's "abandon the lowest-value boom dwellings" picked the
  home of 20 plant staff, which makes them homeless in the binder. Exclude buildings with named residents from
  abandonment, or move plant_staff.

**Add**
- `liandri_tower` (the hero), `drain` (the outfall culvert), `guest_house` (the inspector's house), and room
  sub-sheets for the tower (command room, tower mess, catwalk). Drafts below.
- Citizens: the clinic's medic (the clinic sheet says "one medic" and no one is that medic, a hole in the binder);
  Tin Row's unofficial teacher; the Ship Row deckhands; the scrip clerks of the Liandri tower.
- Hawkins's 1930 catwalk routine.

---

## 5. Draft sheets (binder format; NOT written to the binder)

New header key proposed for rooms: `in: <building id>` (a room sheet lives inside a building; binder.py would
treat `tower:command_room` as reachable when `tower` is). Room sheets would go in `binder/rooms/`. Prop lines are
prose for the artist, not machine keys.

### 5.1 buildings/liandri_tower.md
```
id: liandri_tower
name: Liandri House, the company tower
owner: liandri
layer: boom
kind: tower
at: (summit; LD + engineer to place, Q74's company summit)
size: 58 48 90
users: okafor plant_staff scrip_clerks security
doors: front:personnel left:roller
beds: 0
roof: dome
wear: 0.05
lit: yes
function: bank
mesh: CraneTower
provides: comms
needs: power water
motion: flare
ref: tower

Built in the boom on the island's summit, after the company let the Authority keep the old survey tower
because it was useless to them. A battered stepped plinth, a ceremonial stair nobody climbs, a truck road
beside it that everybody uses, a setback tower, red domes, the lattice crane that lifts nothing any more
and stays because it looks like work. Inside: the scrip exchange hall, top-lit, shuttered "until further
notice". The company built lower than the Authority tower and still stands higher, because it owns the hill.
```

### 5.2 buildings/drain.md
```
id: drain
name: the outfall culvert
owner: liandri
layer: core
kind: pump
at: (under the spine: works plateau -> outfall below pump_house; engineer to route)
size: 6 6 6
users: arashiro haldane rook
doors: front:personnel back:personnel
roof: flat
wear: 0.7
lit: no
pipes: pump_house
ref: processing_hall

A concrete vault of pillars that takes the plant's runoff and the brine to the sea under the town. A tide
line on every pillar, sample jars on a ledge, a bucket under the weep at kilometre three. The company
sign says maintenance matter. Rook's boats tie up at its sea end, and his crates wait on a pallet above
the waterline for the Tin Row traders.
```
(Checker note: `lit: no` with users is fine, because it is not abandoned. Its "door" sides are the two ends.)

### 5.3 buildings/guest_house.md
```
id: guest_house
name: the inspector's house
owner: liandri
layer: boom
kind: house
at: (beside directors_house on the summit, Q74's second villa)
size: 14 10 6
users: okafor
beds: 4
doors: front:personnel
roof: flat
wear: 0.0
lit: yes
ref: processing_hall

Kept ready for the sector inspection that never comes: beds made, lights on a timer, the incident board
from the clinic copied and framed in the hall. Okafor-Strand airs it on the first of every month.
```

### 5.4 rooms/command_room.md (and two siblings, short)
```
id: command_room
name: the command room
in: tower
owner: authority
users: hawkins oduya garrison
lit: yes
wear: 0.5

The long window is the brightest thing in the room. Hawkins's desk is clean and unused, her binoculars on
the sill aimed at the dead rig. Oduya's board shows green company callsigns and nothing of the Authority's.
The one power cable comes in through a cored hole with LIANDRI SUPPLY stencilled on its tag. A bucket
under one skylight.
```
```
id: tower_mess
name: the tower mess and bunks
in: tower
owner: authority
users: garrison oduya nkemelu vask
beds: 60
lit: yes
wear: 0.55

Thirty marines in rooms for sixty: rolled mattresses on the empty bunks, transfer requests on one wall,
food crates stencilled with the company store's mark.
```
```
id: catwalk
name: the tower catwalk
in: tower
owner: authority
users: hawkins garrison
lit: no
wear: 0.5

The maintenance catwalk under the overhang: grated floor, guy-wires, a coffee tin of cigarette ends at the
rail. At dusk, Hawkins.
```

### 5.5 citizens/hawkins.md: changed routine
```
routine: 0630 tower; 0800 tower; 1230 tower; 1300 tower; 1800 tower; 1930 tower:catwalk; 2200 tower
```
Prose addition: *At half past seven she goes out on the catwalk with one cigarette and looks at the company's
tower on its hill until its lights come on. Then she looks for the light on the dead rig. Some nights she finds it.*

### 5.6 citizens/ilunga.md (NEW: the medic the clinic already describes)
```
id: ilunga
name: Tomas Ilunga
role: Liandri clinic medic
employer: liandri
lives: dorm
works: clinic
routine: 0700 clinic; 1200 mess; 1300 clinic; 1500 shanty_b; 1700 clinic; 2000 dorm
wants: an X-ray machine; the silicosis numbers in a report someone reads
fears: the day the company counts the families he treats

Forty-one. One medic, four beds, a cabinet of inhalers. Keeps two sets of books: the incident board by
the door for the sector, and a school exercise book for Tin Row. Goes to the lower end every afternoon
with a bag, which the company records as "community relations".
```

### 5.7 citizens/marau.md (NEW: Tin Row's teacher)
```
id: marau
name: Ines Marau
role: unofficial teacher, Tin Row
employer: outlaw
lives: shanty_b
works: shanty_b
routine: 0700 shanty_b; 0800 shanty_b; 1200 company_store; 1300 shanty_b; 1800 mess; 2000 shanty_b
wants: a school with a door
fears: the permit notice (pa11)

Thirty-five, a haulier's widow. Teaches eleven children on benches made from pipe-rack offcuts, in front
of a company hazard board scrubbed into a blackboard. Washes dishes in the mess at night for scrip, which
is how the kitchen crew knows her and why there is always bread on the school's windowsill.
```

### 5.8 citizens/ship_row.md (NEW group)
```
id: ship_row
name: the Ship Row deckhands (forty)
role: laid-off deckhands and their families
employer: outlaw
headcount: 40
lives: shanty_c
works: dock
routine: 0600 shanty_c; 0700 dock; 1100 boat_landing; 1300 shanty_c; 1900 tin_bar; 2300 shanty_c
wants: the boom back
fears: the wreck being cut up for scrap

They came on the ships when the dock was built and stayed when the ships stopped coming. They live under
the wreck's patio in shacks built from its plating, take day work at the dock when Benedek is short, and
crew Rook's boats when he isn't.
```

### 5.9 citizens/scrip_clerks.md (NEW group)
```
id: scrip_clerks
name: the scrip clerks (six)
role: Liandri accounts and exchange staff
employer: liandri
headcount: 6
lives: staff_houses
works: liandri_tower
routine: 0730 staff_houses; 0800 liandri_tower; 1200 liandri_tower; 1700 company_store; 1800 staff_houses
wants: the exchange windows opened, once, so they have something to do
fears: the queue the day they open

They work in the biggest room on the island and serve nobody. The ledger at the company store is theirs.
```
(staff_houses beds 54 > plant_staff 20 + clerks 6: fine.)

### 5.10 Changes to existing sheets (one line each)
- `tower`: "the tallest building on the island" -> "the oldest building on the island, and the poorest"; add rooms
  `command_room tower_mess catwalk`.
- `tin_row_families`: headcount 24 -> 60. `tin_row_traders`: 26 -> 40. `shanty_c`: users + `ship_row`.
- `clinic`: users + `ilunga`. `shanty_b`: users + `marau`. `mess`: users + `marau ilunga`.
- `hall_c`: users stay empty and abandoned stays yes. Add to the prose "eleven lockers with names; one locker is new".
  Rook's use is secret, so he is NOT listed. That is deliberate: the checker should not know either.
- `directors_house`: unchanged. The second summit villa becomes `guest_house`.
- `company_mast`: keep "taller than the Authority's antenna", but it now stands beside `liandri_tower`, its comms
  provider.

### 5.11 New PA and radio lines (pa_voice.py format)
```
pa13 | Liandri Avalon is home to three hundred and eighty employees. Thank you for being one of them.
pa14 | The culvert is a maintenance area. Personnel are reminded that the tide reaches the outfall gallery without warning.
pa15 | The exchange windows at Liandri House remain closed until further notice. Scrip balances are unaffected.
r11  | en_US-john-medium | Avalon checkpoint, this is Liandri fuel. Two long, Private. You know who it is.
```
(pa13 is the census line: the player has just walked through a shanty of five hundred.)

---

## 6. The intro cinematic (Q56: "have the director and writer rewrite this cinematic")

The writer's draft for the director to stage. Rules held to: the original writers' voice (keep Hawkins's lines
and the "quietest patrol" beat as written; no new dialogue), show don't tell, delay-react-reveal.
1. **Sea at dusk, low.** The flare on the new rig, the dead rig's single light far off. Radio r01 over it ("We
   won't need anything from you").
2. **The company first.** The camera rides alongside the cargo dropship lifting from the big pad. The Liandri
   tower on its hill is lit; the cooling towers steam. Everything moves.
3. **Then the Authority.** The camera lets the cargo ship go and drops to the small pad in the corner of the
   frame. Vask's Atlantis is small, alone, with a fuel hose from a company bowser.
4. **The tower, dark.** Tilt up the Authority tower: few lights, one cable climbing to it from the plant.
5. **Inside.** Hawkins is at the window, not the desk. Hold on her back with the lit town beyond (the peak-frame
   logic: dark frame, bright horizon, lone figure). The original dialogue plays here.
6. **Out.** On "quietest patrol", the brownout (pa03) dims the room for a second. Nobody remarks on it.

---

## 7. Web references (playtest swap; nothing downloaded; none of it ships)

Licence "all rights reserved" means look and learn only; it never ships and is never traced. Only refs 1-2 are
public domain.

| # | Reference | Source / artist | Licence (as stated) | What fits | For |
|---|---|---|---|---|---|
| 1 | Scene in front of company store, Westland PA, 12 June 1946 (NAID 540334) — https://www.docsteach.org/documents/document/scene-in-front-of-company-store | Russell Lee, 1946 coal survey (US National Archives, RG 245) | Public domain, free of known copyright restrictions | the company store as the town's living room: people loitering on the porch, signage, the store as a bank | `company_store`, the PA's scrip lines |
| 2 | Typical home for miners, U.S. Coal & Coke, Lynch KY, 1946 (NAID 541404) — https://www.docsteach.org/documents/document/typical-home-for-miners-us-coal-coke-company ; series overview: https://prologue.blogs.archives.gov/?p=36929 | Russell Lee / National Archives | Public domain (NARA DocsTeach records) | identical company housing, cost-cut material, family life squeezed into company stock | `dorm`, `staff_houses`, Tin Row families |
| 3 | Hashima: lightwell and walkways, kitchen in the Nikkyu Company miners' flats — https://old.designcurial.com/news/hashima---the-abandoned-japanese-island-4199747/ | Andrew Meredith (meredithphoto.com), Designcurial | © all rights reserved | a company island town: dense miners' blocks, walkways over a lightwell, kitchens left mid-use, the school and hospital on the same rock | `dorm`/`dorm_b` interiors, the stacked housing, `clinic` |
| 4 | Single cabins on Gullfaks A (8-man cabins on Ekofisk, then 4- and 2-man) — https://gullfaks.industriminne.no/en/single-cabins-on-gullfaks-a-a-crucial-choice-for-the-offshore-work-environment/ | Photo: Shadé B. Martins / Norwegian Petroleum Museum | © Norsk Oljemuseum | offshore bunk history: fold-up second bunks for peak crews; Avalon going *back* to four to a room is a story | `dorm_b` (rig crews), `new_rig` crew quarters |
| 5 | Pyramiden cafeteria: the big dining room with the mosaic of the Svalbard landscape and Norse heroes — https://www.urbex.nl/pyramiden-cafeteria/ (also https://www.smithsonianmag.com/travel/soviet-ghost-town-arctic-circle-pyramiden-stands-alone-180951429/) | urbex.nl author (unnamed, visited 2018); Smithsonian | © site, no licence given | a mining company's canteen as its showpiece: one giant mural over long tables, a huge kitchen | `mess`: the company mural is the room's sentence |
| 6 | Outland (1981), the Con-Am 27 mining colony on Io — https://en.wikipedia.org/wiki/Outland_(film) ; review: https://moriareviews.com/sciencefiction/outland-1981.htm | Production design Philip Harrison, art direction Malcolm Middleton | film © (Ladd Co./Warner); pages © | THE company-town sci-fi: cage bunks stacked atop each other, mess hall, bar, a marshal the company tolerates; the Authority-vs-company plot itself | `dorm_b`, `mess`, `tin_bar`; Hawkins and Vask as the tolerated law |
| 7 | Aliens (1986), Hadley's Hope: prefab modular colony, operations centre, medlab, corridors with piping — https://avp.fandom.com/wiki/Peter_Lamont ; https://www.domusweb.it/en/news/2025/09/19/alien-design-nostromo.amp.html (Domus, "the menacing architecture of Alien", not fetched: 403) | Production design Peter Lamont | film © 20th Century; fan wiki CC BY-SA text, images vary | a company colony built from prefab kit, families included, run from one ops room; Y2K-era industrial sci-fi in its purest form | the prefab kit read; `plant_office`; the company side of the command room |
| 8 | Chornobyl NPP Control Room 3 and 4, the AZ-5 buttons — https://www.thisiscolossal.com/2020/10/darmon-richter-chernobyl/ ; Control Room #4, 2023 — https://www.gerdludwig.com/no-end-in-sight | Darmon Richter (book "Chernobyl: A Stalkers' Guide", FUEL); Gerd Ludwig | © Richter/FUEL, shared with permission; © Gerd Ludwig, use without permission prohibited | a control room whose power has gone elsewhere: walls of dead instruments, one important button, the room outliving its purpose | `tower:command_room` (Oduya's board, the Authority's dead consoles) |
| 9 | UEA "Ziggurats", Norfolk and Suffolk Terraces (1962-68) — https://bluecrowmedia.com/blogs/news/brutalist-building-denys-lasdun-university-of-east-anglia ; https://sosbrutalism.org/cms/15888753 | Denys Lasdun (architect); photo Simon Phipps | © Blue Crow Media, all rights reserved | stepped concrete residences down a slope, each roof the next one's terrace, raised walkways linking to a long spine block | `liandri_tower`'s stepped base; terraced company housing; the spine as a "teaching wall" |
| 10 | National Assembly of Bangladesh, Dhaka — https://archeyes.com/bangladeshs-national-parliament-house-by-louis-kahn-a-masterpiece-of-modern-architecture/ ; https://www.atlasobscura.com/places/national-assembly-of-bangladesh | Louis I. Kahn (architect) | © page photographers | monumental concrete with marble inlay, huge geometric cut-outs as light wells, top-lit voids; power shown as mass and light | `liandri_tower` interior (the empty, top-lit exchange hall); the battered gate wall |
| 11 | Kowloon Walled City, 1986-92 — https://mplus.org.hk/en/magazine/exploring-kowloon-walled-city-photographic-journey ; https://hongkongfp.com/2019/10/13/hkfp-lens-city-darkness%e2%81%a0-greg-girard-ian-lambot-revisit-kowloons-long-gone-walled-city/ (not fetched: 1854.photography gave 403) | Greg Girard and Ian Lambot, "City of Darkness" (1993) / "Revisited" (2014) | © photographers/M+ | an "organic megastructure" continually adapted by its residents: wiring, workshops in homes, light from above only | Tin Row interiors (`shanty_a/b/c`), the transformation rule, the cables off the dock lights |
| 12 | G-Cans, Metropolitan Area Outer Underground Discharge Channel — https://metropolisjapan.com/g-cans/ | Photos and text Tamatha Roman, Metropolis Japan | © Metropolis Japan, all rights reserved | 59 x 18 m pillars, puddles with reflections, low light, a drop-off at one end; a "cathedral" of drainage | `drain` (scaled down to ~6 m): the pillar rhythm, the tide line, the reveal at the far end |
| 13 | GDR border command tower, Nieder Neuendorf (1987) — https://www.dark-tourism.com/index.php/1202-watchtower-nieder-neuendorf | Peter Hohenhaus, dark-tourism.com | © Peter Hohenhaus | a small state post with a field telephone, searchlight control, binoculars, a holding cell: the state's eye on a border | `checkpoint` (Nkemelu's hut); Hawkins's binoculars |
| 14 | Sparth's method: paint-over of untextured level renders; hard Forerunner forms against soft terrain to pull the eye — https://www.destructoid.com/?p=151415 ; https://halopedia.org/Sparth | Nicolas "Sparth" Bouvier (343 Industries) | © 343/Microsoft; pages © | one hard-edged geometric hero against soft ground: the reason the Liandri tower must be the ONLY stepped shape | `liandri_tower` silhouette on the summit; cut the duplicate crane towers |

---

## 8. Notes for the other four roles (where this needs your check)

**DIRECTOR**
- Approve or reject the hero swap (`tower` -> `liandri_tower`). compose.py's hero test and serial vision (A-401)
  would need the new id. Does the Liandri tower on the Q74 summit land on a third from the command-room window
  (yaw 300 +-34, 28 deg down) and read as a silhouette above the skyline? If the summit is out of the window's
  cone, the window hero stays the cooling towers and the Liandri tower is the deck/catwalk hero (Q51's
  view is west onto that mountain, which may be the better fit).
- The catwalk beat: Hawkins at 40-100 m, back-lit at dusk. Sun az 136 vs the catwalk's facing: check that she
  reads as a silhouette.
- Q56: stage the 6-shot cinematic in section 6. Hawkins's lines unchanged.
- Interiors: each has one "sentence" prop. Frame it from the door.

**ENGINEER**
- Route the `drain` culvert: works plateau to an outfall below the pump house, grade to the sea, under the spine.
  It crosses the pipeline at "km3" (the weep). Does it fit E12/E14 with the existing ore line and water head?
- The Liandri tower on the summit needs power, water and a truck road at a real grade (E1); the ceremonial
  stair can be steep, the road cannot.
- Shanty in the smoke: test "reserve the plume land as nobody's land at boom time". Fuel tanks must stay 100 m
  off Tin Row (E16) even when Tin Row grows to ~500 people.
- binder.py: the `in:` key for room sheets and the `takes:` key (informal taps). Abandonment must never pick a
  building with named residents (staff_houses, Q37).

**LEVEL DESIGNER**
- The drain as LD7: 25-60 s of quiet at 5.3 m/s is 130-320 m of culvert. That is too long for a real culvert,
  so make it a loop through the dead hall (hall_c) with the reveal light at the junction. It needs 2 entries,
  cover (Rook's crates, pillars) and a high spot (the dead hall's gantry).
- Interiors are rests, not gauntlets, apart from the drain and the dead hall. Mess, Tin Bar and the command room
  are no-combat.
- The mess and the Tin Bar have 4 and 3 doors: fine for flow, and they are the two places the three powers meet.
- Can the player enter the Liandri tower? My proposal: see it through glass at the gate, don't enter it (shown, not given).

**ARTIST**
- The prop lists in section 3 are a clutter-pass brief per room. Signature props to build first: the company
  mural (mess), the cored cable with its LIANDRI SUPPLY tag (command room), the upside-down company panels (Tin
  Row), the eleven lockers (dead hall), the tide-lined pillars (drain).
- Palette: the company prefab (blue, orange top band) turns into Tin Row by additions. The Liandri tower is the
  only sand/beige-and-red-dome mass. The Authority is grey concrete with few lights. Three powers, three palettes.
- Night read: dorm_b is the only dark row (the blackout curtains). The dead rig's single light, and the drain's
  lamp, are the only "wrong" lights.
- IMP/HIER: the Tin Row census increase (to ~500) may raise the shanty density. Check the figure-ground stays
  compact.

---

*Open questions for the user:* (1) the hero swap, Authority tower to Liandri tower; (2) Hawkins as the catwalk
figure; (3) raising Tin Row's numbers so the town matches the shanty you asked for, with the company's count
staying at 380; (4) whether the player may enter Liandri House.
