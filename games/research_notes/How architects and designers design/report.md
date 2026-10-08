# How designers design a project, and what it means for the Avalon town pipeline

Research pass, 2026-10-08 (Q36; the user: "research how architects and designers project", i.e. *projetar*). Written by a research agent.

It builds on `Believable city simulation/report.md`, `Level design practices/report.md`, `Organic settlement generation/notes.md`, `U2Avalon/tools/town.py`, `PIPELINE.md` and `compose.py`. Those cover *what* a town should contain. This report covers *how designers work*: the order of decisions, the drawings they think with, and how they judge results.

## Summary: the top 8, ranked by impact on how good the town feels per unit of effort

| # | Change | What we do now | What is new | Effort |
|---|---|---|---|---|
| 1 | **Brief + parti file** (`binder/parti.json`): one sentence, a diagram (axis, hero, edges, gateways) and 3–5 beats, each with an emotion. The generator places the parti first, and every score reads it. | The binder is the *programme*. `compose.py` scores one window frame against generic camera rules. | An organising idea the layout must serve and is judged against: "whole shape first" as data. | S–M (1 day) |
| 2 | **Serial-vision walk**: eye-height stations every 25–40 m along the main route. An offline pre-check reuses `compose.py`'s projection; the pilot then films a strip that is judged frame by frame. It ends on the peak frame. | One scored frame (the window); overview and close-up sheets. | Judging the town as a sequence of reveals (Cullen), the way a player meets it. | S–M (1 day) |
| 3 | **Option sheet + red-dot crit**: 12–24 cheap massing options on a contact sheet (figure-ground, section, window thumbnail, scores). The user dots 2–3; only those go on to the expensive stages. | `town.py` rerolls up to 6 and silently keeps one. | Visible divergence, human convergence (Double Diamond; OMA/BIG option models; Colibri + Design Explorer). | S (half a day) |
| 4 | **Framework plan vs code, with stage freezes**: tissue (spine, terraces, hero, gateways, frame) frozen first; per-district codes fill the rest; rerolls and marks attach to a named level. | Every run regenerates everything. | Habraken's levels + RIBA-style gates; user edits survive. | M (1–2 days) |
| 5 | **Figure-ground + sections** as standard drawings in every run folder: a Nolli plan at fixed scale, and 2–3 cut sections (sea → shanty → spine → company → tower) with a 1.8 m figure. | Coloured layout, walks, viewshed and pad maps; editor side views. | The two drawings architects and urbanists think with. The section is where the Aztec terraces and the catwalk frame get designed. | S (half a day) |
| 6 | **Structured crit protocol**: a fixed pin-up of ~8 images, 6 questions tied to the parti, notes logged by level (parti / framework / code / dressing). | `avalon mark` notes; no fixed format. | Reviews become decisions at the right level. | S (2–3 h) |
| 7 | **White-model pass**: the town in game in one flat grey skin under the final light. Judge silhouettes, light and frames before the art. | Final skins straight away. | The film art department's white card model: tests the one good frame on mass and light alone. | S (half a day) |
| 8 | **A small Avalon pattern language**: ~12 Alexander patterns with checks, honoured in the shanty (life) and deliberately inverted in the company zone (exposure, no refuge, no edges to sit on). | IMP/HIER metrics; Lynch checklists. | Rules about places people *stay*, and a dystopian reading built from the same rules (emotion × action). | M (1–2 days) |

Already proposed elsewhere: Lynch elements as checks (they go into crit question 3) and phasing as epochs (they sit under the "code" level).

## 1. The architect's process stages

**RIBA Plan of Work 2020:** 0 Strategic Definition, 1 Preparation and Briefing, 2 Concept Design, 3 Spatial Coordination, 4 Technical Design, 5 Manufacturing and Construction, 6 Handover, 7 Use. Stage 3 was renamed from "Developed Design" in 2020 and is about *testing and validating the concept* before technical detail. [RIBA](https://www.architecture.com/knowledge-and-resources/resources-landing-page/riba-plan-of-work) · [Designing Buildings](https://www.designingbuildings.co.uk/wiki/RIBA%20Plan%20of%20Work%202020)

**AIA phases:** Schematic Design → Design Development → Construction Documents → procurement → construction. A typical fee split is about 15/20/40/5/20 %: most effort comes late, but most value is decided in the cheap early phases. [ASD](https://asd-usa.com/blog/architectural-design-phases)

| Stage | Decides | Leaves open | Ours |
|---|---|---|---|
| Brief / programme | who it's for, the spaces, budget, ambition | form | binder + citizens. **Missing:** the ambition in one sentence |
| Site analysis | slope, sun, wind, views, access, noise | where things go | island, viewshed, terrain score. **Missing:** a one-page site drawing |
| Concept / parti | the organising idea, massing, circulation | materials, detail | **missing as an explicit step** |
| Schematic design | arrangement, sizes, plans and sections, cost | systems, details | layout + systems + compose |
| Spatial coordination | systems vs form, materials; *test the concept* | construction detail | pads, walks, metrics, utilities |
| Construction documents | everything | nothing | T3D, clutter, populate, light |
| Use | built, observed | — | pilot, autoplay, avalon mark |

**Lesson:** each stage freezes a few decisions and keeps the rest open. Our pipeline re-decides everything on every run.

## 2. How designers think

- **Problem and solution co-evolve** (Lawson; Dorst & Cross 2001). All nine designers in Dorst and Cross's study reframed the brief while designing. In Lawson's 1972 experiment, architects tested solutions while scientists mapped the rules first. [Dorst & Cross](https://oro.open.ac.uk/3278)
  - *Us:* when a generated town surprises us with a good frame, change the brief to keep it.
- **Designerly ways of knowing** (Cross 1982): design works on ill-defined problems by proposing, and thinks through sketches and models.
- **Reflection-in-action** (Schön 1983). In the Quist/Petra case, the sketch on an awkward slope "talks back". Design is "a reflective conversation with the situation". [review](https://drossbucket.com/2018/09/03/book-review-the-reflective-practitioner/)
  - *Us:* the generator is the pencil; its outputs must be drawings that talk back, not only scores.
- **The parti** (Beaux-Arts): the organising idea, fixed in a quick esquisse before plans. [Wikipedia](https://en.wikipedia.org/wiki/Parti_(architecture))
- **The primary generator** (Darke 1979): one self-chosen aim prunes the solution space; generator → conjecture → analysis.
  - *Us:* "The company holds the high ground; the town lives in its shadow and its smoke."
- **The Double Diamond** (Design Council 2005): widen then narrow, twice. [Design Council](https://www.designcouncil.org.uk/our-resources/the-double-diamond/history-of-the-double-diamond/)
  - *Us:* our reroll loop converges where the user can't see it, and there's no visible divergence.

## 3. Tools of thought

- **Diagrams first:** bubble diagrams and adjacency matrices (what must touch what), circulation diagrams, figure-ground, sections. The binder's needs list is already an adjacency matrix.
- **Figure-ground / Nolli map:** mass black, open white; Nolli's 1748 Rome also shows public interiors white. Cornell's urban design programme made it its main tool in the 1960s. [morphocode](https://morphocode.com/figure-ground-diagram/)
- **The section:** on a hill town the section *is* the design. The peak frame is a section idea: foreground cover, then a drop, then a far figure.
- **Massing models:** OMA builds many and archives the discards; BIG frames design as evolution, many mutants then selection. [Icon: Inside OMA](https://www.iconeye.com/architecture/inside-oma) · [Metropolis](https://metropolismag.com/projects/obsessive-model-making-oma-nyc-creative-process/)
- **Measured precedents:** Hashima/Gunkanjima, Longyearbyen, Barentsburg, Chuquicamata, Kiruna, not only mood boards.
- **Ching's ordering principles** (axis, symmetry, hierarchy, datum, rhythm, transformation) as the parti vocabulary:
  - axis = the spine from dock to tower;
  - datum = the straight ore line;
  - hierarchy = the tower;
  - rhythm = pylons, lamps and rack bents;
  - transformation = company prefab → shanty through additions.
- **Alexander, *A Pattern Language*.** Useful for us: 30 Activity Nodes, 31 Promenade, 53 Main Gateways, 61 Small Public Squares, 98 Circulation Realms, 106 Positive Outdoor Space, 114 Hierarchy of Open Space, 120 Paths and Goals, 160 Building Edge. [summary](https://www.patternlanguage.com/apl/aplsample/aplsamplesummary.htm)
- **Lynch, *The Image of the City*:** paths, edges, districts, nodes, landmarks; "imageability".
- **Cullen, *Townscape*: serial vision.** The walker meets the town as jerks and revelations, the existing view against the emerging view. Casebook terms (check the text): closure, deflection, narrows, punctuation, anticipation, the outdoor room. [serial vision paper](https://oars.uos.ac.uk/4769/)
- **Gehl:** figures read at ~100 m, faces from ~25 m.
  - *Us:* the peak frame's lone silhouette belongs 40–100 m away.
- **Bacon, *Design of Cities*:** movement systems shape the city; design the routes *and what they end on*.

## 4. Urban design

- **The masterplan is a framework**, and a design code fixes only what the masterplan marks as non-negotiable (CABE 2004; Scotland's PAN 83). [PAN 83](https://www.gov.scot/publications/pan-83-planning-advice-note-master-planning/pages/6/)
- **Form-based codes** use a regulating plan and a transect T1–T6, with each zone's rules on frontage, setback and height. [CNU](https://cnu.org/node/97)
  - *Us:* a district = a transect zone with its own small code table.
- **Phasing** with an infrastructure strategy: our epochs.
- **Growth nobody controls:**
  - Alexander's *Oregon Experiment*: organic order, participation, piecemeal growth, patterns, diagnosis, coordination.
  - Habraken's levels: tissue, support, infill, each with its own owner. [Habraken](https://habraken.com/html/introduction.htm)
  - *Us:* this is the Avalon story. The company is the tissue and support (spine, terraces, racks, tower); the residents are the infill (shacks, additions, laundry). A reroll at one level never touches the levels above it.
- **Parametric urbanism:** ZHA's Kartal-Pendik "soft grid", with transitions between districts designed as part of the idea. [ZHA](https://www.zaha-hadid.com/?p=11010)

## 5. Iteration and critique

- **Crits and juries** often turn adversarial (Webster; Anthony, *Design Juries on Trial*); fixed formats, written questions and red-dot reviews work better. [ACSA](https://www.acsa-arch.org/wp-content/uploads/2021/10/ACSA.Teach_.2019.5.pdf) · [Field](https://www.field-journal.org/article/id/61/)
- **Test at eye level:** walkthroughs, the sequence; Naughty Dog walks blockouts to check framing. [80.lv](https://80.lv/articles/attack-the-block-steps-to-better-level-design/)
- **Design space:** Grasshopper sweeps; Colibri writes a CSV and an image per option; Design Explorer filters them; Mueller's interactive evolution has taste pick the parents while metrics filter. [Colibri](https://www.food4rhino.com/en/app/colibri?lang=en) · [Mueller](https://dspace.mit.edu/handle/1721.1/91293)
  - *Us:* `town.py` has seeds, metrics and PNGs per candidate, but no contact sheet and no human pick.

## 6. Film and level designers (brief)

- **Film:** script → doodle → concept → plans → **white card model**, used to approve the design and plan camera angles (lipstick camera) → build → dress. [WB Studio Tour](https://www.wbstudiotour.co.uk/schools/resource-hub/set-design/)
- **Naughty Dog's "Narrative First":** story → 3D blockout → iterate → lock → playtest → polish. [GDC](https://gdcvault.com/play/1027683/Level-Design-Summit-Designing-the)
- **Valve's Cabal:** small cross-discipline groups. [VDC](https://developer.valvesoftware.com/wiki/Cabal_process)

## 7. Product design (brief)

- **Rams:** "less, but better" ("serve the piece, not a signature"). [Vitsœ](https://vitsoe.com/gb/about/good-design)
- **IDEO design thinking:** prototype early; desirable, feasible, viable.
- **frog's "form follows emotion"** (Esslinger). Our pipeline is "form follows function", which is right for believability, but *feeling* needs a second driver. The parti's beats carry the emotion and the function fills in around them: emotion × action. [Red Dot](https://www.red-dot-design-museum.org/essen/exhibitions/design-fundamentals/basic-design-principles/form-follows-emotion)

## Lessons in detail

### 1. Brief + parti before generation

`binder/parti.json`, approved once by the user:
```json
{"sentence": "The company holds the high ground; the town lives in its shadow and its smoke.",
 "axis": ["dock", "tower"], "datum": "ore_line", "hero": "tower", "second": "cooling_towers",
 "edges": ["sea", "plant_fence", "terrace_wall_main"], "gateways": ["dock_gate", "company_gate"],
 "downwind": "shanty", "high": "company",
 "beats": [
   {"at": "dock",        "emotion": "dread",      "move": "compression, tower hidden"},
   {"at": "spine_mid",   "emotion": "exposure",   "move": "tower glimpsed over roofs"},
   {"at": "company_gate","emotion": "smallness", "move": "battered wall, stair cut-in"},
   {"at": "catwalk",     "emotion": "melancholy", "move": "release: dark frame, grated catwalk, lone figure 40-100 m, dusk rain"}]}
```

- `layout_spine.py` places the parti anchors first.
- `compose.py` and the serial check score *against the parti*.
- A parti diagram is drawn at the top of every `report.md`.

### 2. Cullen serial vision (`tools/serial.py`)

1. Take the main route: dock → tower → catwalk, along walk trunks and the spine.
2. Place stations every 25–40 m at 1.6 m eye height, looking along the route (±15° toward the next beat).
3. Offline, per frame, record `hero_visible`, `emerging` (a new element in the upper third), `closure` (mass within 150 m ahead), depth layers and sky fraction.
4. Sequence rules:
   - no more than 3 stations in a row without an `emerging` change;
   - the tower hidden at least once, then re-revealed;
   - the last station matches the peak frame (dark mass on the frame edges, a grated horizontal in the lower third, a figure at 40–100 m, low sun behind).
5. The pilot flies the same stations and writes `serial_strip.png` with pass/fail under each frame.

### 3. Options sheet (`town.py stage=options n=16`)

1. Run the cheap stages only (island, layout, systems, compose, serial pre-check).
2. Write `options.csv` and `options_sheet.png` (figure-ground, section A and window thumbnail per option).
3. The user picks 2–3; only those go on to `stage=build`.
4. Keep every option folder (the OMA archive). Optionally breed the next 16 from the picks (Mueller).

### 4. Levels and freezes

- **`framework.json`** (tissue): spine, terraces, gateways, hero and anchors, frame camera, district boundaries.
- **`code.json`** (per-district rules): setbacks, gaps, storeys, party walls, skins, clutter mix, epoch.
- **`infill.json`**: shacks, additions, clutter.
- **Freezes:** `town.py freeze=framework` rerolls only the levels below.
- **Marks:** `avalon mark` notes and live edits carry a `level:` and land in that level's file.
- **Open questions:** each stage writes `open_questions.txt`, listing what it deliberately leaves open.

### 5. Drawings (`tools/drawings.py`, after pads)

- **Figure-ground** at 1 px = 1 m, north up, plus a Nolli variant (public interiors white).
- **Sections:**
  - A along the parti axis: sea → shanty → spine → company → tower;
  - B across the busiest node;
  - C through the catwalk toward its view.

  Each shows terrain, masses on their pads, retaining walls, and a 1.8 m figure with 25 m and 100 m marks.
- Both go into `report.md` and the options sheet.

### 6. The crit

**Pin-up:** the parti diagram, figure-ground, section A, the window frame, 3 serial frames (arrival, mid-climb, peak) and one close-up.

**Questions** (scored 1–3, one line of notes each):
1. Does it say the parti without words?
2. Is there one frame I'd screenshot?
3. Can I point to the Lynch elements in the figure-ground?
4. Is the official set against the improvised in every frame?
5. Does each beat's emotion land?
6. What is the *one* change?

Notes are logged by level. Crit after the white-model pass and after the art pass, never mid-change.

### 7. White model (`town.py white=1`)

- **Flat grey:** every StaticMeshActor gets one flat light-grey skin, under the final sun and fog.
- **Judging:** the serial strip and the window frame are judged on mass and light alone. If a frame fails in white, art won't save it.
- **Report:** the white and final strips sit side by side.

### 8. The Avalon pattern language (`tools/patterns.py`)

| Pattern (APL) | Check | Shanty | Company |
|---|---|---|---|
| Main Gateways (53) | marked threshold where the main route crosses a district boundary | honoured | honoured, as checkpoints |
| Activity Nodes (30) | top-integration junctions have a small space and 2+ props for staying | honoured | absent |
| Small Public Squares (61) | node spaces ~12–20 m across | honoured | inverted: oversized empty parade ground |
| Positive Outdoor Space (106) | open spaces mostly convex, enclosed on 2–3 sides | honoured | inverted: leftover, exposed |
| Hierarchy of Open Space (114) | a sheltered back-covered spot looking into each node | honoured | inverted: prospect without refuge = unease |
| Building Edge (160) | walls facing paths have steps, crates, benches | honoured | inverted: blank battered walls |
| Paths and Goals (120) | a visible goal every 50–80 m | both | both |
| Circulation Realms (98) | each district's route reads as one realm | both | both |

## Other practices mapped

| Practice | Mapping | Status |
|---|---|---|
| Lynch elements | crit question 3; an automatic sketch map | already proposed |
| Phasing / epochs | under `code.json` | done (Q35 pass 3) |
| Site analysis drawing | sun (lowsun.py), storm wind, best viewsheds, worst land | new, S (fold into lesson 1) |
| Measured precedents | Hashima, Longyearbyen and Barentsburg figure-ground + section at our scale, as code targets | new, S–M |
| Ching ordering | parti vocabulary | in lesson 1 |
| Bacon terminations | every route class ends on something | in lesson 2 |
| Gehl distances | sections, peak-frame figure, node sizes | in lessons 2, 5, 8 |
| Rams | crit question 6; a clutter budget per frame | taste rule |
| Co-evolution | update `parti.json` when an option surprises well; log why | habit |

## Suggested order

1. Lessons 5 + 1 (drawings + parti): ~1 day.
2. Lesson 3 (options sheet): half a day.
3. Lesson 2 (serial pre-check, then the pilot strip): 1 day.
4. Lessons 7 + 6 (white model + crit format): half a day.
5. Lesson 4 (levels and freezes): 1–2 days.
6. Lesson 8 (patterns): 1–2 days.

## Verification notes

**Checked online:**
- the RIBA 2020 stages and Stage 3 rename, AIA phases and fees;
- Dorst & Cross 2001, Darke 1979 (citation), the Double Diamond's origin, the Schön case (secondary sources), the parti;
- Cullen's existing/emerging view, Habraken's levels, form-based codes, PAN 83, ZHA Kartal-Pendik, OMA's models, Colibri / Design Explorer, Mueller;
- the film white card model, Naughty Dog's stages, the crit research, Rams, frog;
- Ching's six principles, and Alexander patterns 30, 98, 106, 114, 120 and 160.

**Not verified from primary text:**
- Cullen's casebook terms;
- the exact wording of patterns 53 and 61 and the square size;
- Gehl's exact numbers;
- BIG's internal massing loop;
- the details of Alexander's seven rules.

Target numbers are proposals to tune.
