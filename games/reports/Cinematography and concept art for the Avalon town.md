# Cinematography and concept art for the Avalon town

Research report, 2026-10-07. Question from the user: "help me research what good cinematography is, and how artists approach concept art for games and movies", applied to the generated mining/refinery company town (~380 people, sea island, under a tower) that the player mostly sees from the tower's command-room window, balconies and stairways in Unreal II.

We already work as a film director rather than a game developer (Anatomy of Decay: place the camera first, build and light only what it sees, cheat lights, photo skies). This report adds the rules that sit under that idea and turns them into generator changes.

Confidence: claims backed by a named source are marked with it. Things I could not confirm, or that are my own reading, are marked **(uncertain)** or **(our inference)**.

---

## 1. Cinematography fundamentals for establishing shots

### 1.1 Composition

**Rule of thirds, and what it really says.** John Thomas Smith first wrote the "rule of thirds" down in *Remarks on Rural Scenery* (1797). He was reading Joshua Reynolds, whose actual point was that when a picture has two areas of different brightness, one should dominate and they should not be equal (Michael Freeman's reading, via Wikipedia, "Rule of thirds"). The usable rule is therefore about **dominance**: sky or land should take about 2/3 of the frame, and no two masses should be equal. Intersections of the thirds lines are good places for the focal point, but the deeper rule is "never 50/50".

**Golden ratio.** A phi grid puts its lines at 0.382 and 0.618 instead of 0.333 and 0.667. No historical link to the rule of thirds has been shown, and there is no good evidence that it reads better (same sources). Treat it as a slightly more central variant, not as magic. **(uncertain: claims that phi compositions measurably please viewers are weak.)**

**Three layers plus "staffage".** Mateusz Piaskiewicz ("Composition in Level Design", Game Developer, 2014) carries the painter's model straight into level design:
- **Foreground**: frames and isolates the view. Mostly silhouette, little detail.
- **Centre of interest**: the dominant (focal point) plus a counterpoint or two. It stands out through brightness and placement.
- **Background**: depth and scale. Calm colours, little detail.
- **Staffage**: small living figures (people, animals, vehicles) that show scale and steer the eye.

He also lists what pulls the eye, roughly strongest first in practice: **light/brightness, contrast, detail density, saturation, scale, line direction and motion**. Motion "strengthens dominants". Line meanings: horizontal = calm, vertical = strength, diagonal = dynamism, curve = softness. Blain Brown's *Cinematography: Theory and Practice* (chapter "The Lens and the Frame") lists the same depth cues: overlap, relative size, vertical position, linear perspective, foreshortening, chiaroscuro and atmospheric perspective.

**Framing within the frame.** Naughty Dog uses pillars, walls and openings as frames that draw the eye, and lines that run down paths as leading lines (Uncharted 2 art direction talk, Erick Pangilinan, GDC 2010, via GDC Vault and Game Maker's Toolkit's "Why Nathan Drake Doesn't Need a Compass"). Pangilinan's advice is to place shapes along the path as "stepping stones" that carry the eye inward. Our command-room window *is* a frame within the frame: mullions, the sill and the balcony rails are the foreground layer for free.

**Negative space.** Sparth (Nicolas Bouvier, art director on Halo 4 and 5) gets vastness from a few precise geometric forms, controlled palettes and empty space, not from piling on detail (Art-Spire interview; DesignCurial). His Forerunner structures are hard-edged and set against soft organic terrain, and that shape contrast is what makes them the focal point. For us: open sea and sky are not wasted pixels. They are the calm field that makes the town read.

**Scale cues.** Any known-size object fixes scale: people (1.8 m), a truck, a crane hook, a door, a window grid. Without staffage, a town reads as a model. Disneyland goes the other way and *cheats* scale. Main Street's second floors are 5/8 scale and third floors 1/2, and Sleeping Beauty Castle shrinks with each storey, so a 77 ft castle reads much taller (Disney trivia sources: hunker.com, duchessofdisneyland.com).

### 1.2 Lens and focal length

Unreal II gives us a field of view, not a lens. For orientation, these are horizontal FOVs on a 36 mm (full-frame) gate:

| Focal length | Horizontal FOV | Character |
|---|---|---|
| 18 mm | ~90 deg | Typical game FOV. Exaggerated depth; distant things shrink to nothing |
| 24 mm | ~74 deg | Wide establishing shot |
| 35 mm | ~54 deg | Wide but natural |
| 40-50 mm | ~48-40 deg | "Human eye" normal. Deakins' preferred range |
| 85 mm | ~24 deg | Mild compression; background looks closer |
| 200 mm | ~10 deg | Strong stacking: rows of buildings pile into a wall |

- **Deakins** prefers primes around 40 mm and dislikes both very long and ultra-wide lenses (ymcinema.com, 2021). Because primes cannot zoom, he has to move the camera, and he says that is what makes him think about angle. On his own forum he says camera distance and height come from intent and context (foreground, blocking), not from measurement.
- **Compression**: at the same framing, a longer lens means the camera stands farther away, so far objects grow relative to near ones. About 70 mm gives mild stacking and 200 mm obvious stacking (Tamron, DIYPhotography, PictureCorrect). Telephoto views of towns emphasise **density**. Wide views emphasise **space and the viewer's position**.
- **Our problem (our inference)**: a ~90 deg game FOV from a high tower makes a 380-person town look small and scattered. Two fixes: (a) build the town denser and larger than "real", like Disney's cheat; (b) for scripted look moments, narrow the FOV to around 40-55 deg (PlayerController FOV in UnrealScript; **uncertain** whether U2's controller exposes this cleanly at runtime).

### 1.3 Camera height and angle

Piaskiewicz: a **high angle** looking down makes the viewer feel small relative to the world but gives an overview. A **low angle** looking up shows depth and makes the subject imposing. A **flat** eye-level angle is the most boring and needs a strong dominant. Front-on views show pattern. Half-side views (about 30-60 deg off-axis) show volume and perspective best.

Our fixed viewpoints are high angles (command room) and mid-heights (balconies, stairways). So: the tower window sells **overview and ownership** (the company watching its town), and lower balconies can be dramatic low-angle views up at the tower or at stacks. **(Our inference: give each viewpoint a different emotional job instead of showing the same town three times.)**

### 1.4 How reveals are staged

- **Spielberg, Jurassic Park's brachiosaurus.** The camera holds on the characters' faces as they react to something off-screen, with sound only. Only after a hand turns Sattler's head do we see the dinosaur (What's in a Scene; Slashfilm on Sam Neill's improvised reaction). Rule: **delay, then react, then reveal**. Anticipation is built by withholding the view.
- **Deakins** plans composition from the cut: what comes before and after, and whether the next shot is wide. Skyfall uses panoramic establishing shots with strong colour (CCEA fact file, FDTimes interviews).
- **Lubezki, The Revenant**: natural light only, shot in short windows at dawn and dusk. On some days only about 5 of 8 usable hours were shot, and artificial light was used once, at a campfire (Variety via Slashfilm, Videomaker, Tribeca). For us the lesson is **choose the hour, then everything else**. The time of day is the biggest single lighting decision.
- **Greig Fraser, Dune**: desert scenes use hard light and open shade. He up-lights faces because real sun bounces off the sand (Cinematography Podcast ep. 257; ASC). The lesson is **motivated bounce**: fill light comes from a believable source (ground, sea, wall), not from nowhere.

For a game without cutscenes, the Spielberg delay maps onto **architecture**: the stairway or corridor hides the town (walls, a frosted door), then the view opens at a threshold. The "reaction" is the player stopping.

### 1.5 Colour scripts and value structure

- **Colour script** (Pixar: Ralph Eggleston, Lou Romano). Small abstract colour and value thumbnails for every sequence, laid out in a strip so the emotional arc is visible at once. Eggleston worked in chalk pastel on black paper. Lasseter liked that colours intensified with emotion and muted when the story turned sombre (MoMA *Pixar: 20 Years*, Thunderchunky interview with Romano). For us, a colour script means **one palette and value key per viewpoint per story beat** (e.g. arrival dusk, night shift, the day things go wrong).
- **Value first, hue second.** Notan (Japanese "dark/light") studies limit an image to 2-3 values. Mass similar values together, and the structure either works in three values or not at all (Artists Network; Proko's value-composition thumbnail course). The **squint test** throws away hue and detail to check the value pattern.
- **Rule**: an establishing shot should read as **3-4 value groups**, for example sky = light, distant island/sea = light-mid, town mass = mid-dark, foreground frame = darkest. The focal point gets the **highest local contrast** (its lightest light against the darkest dark).

### 1.6 Lighting

- **Key / fill / rim.** In exteriors the sun or the brightest source is the key, the sky and bounce are fill, and a back or rim light separates silhouettes from the background (Brown). A **back-lit** town (sun behind it, low) gives rim-lit edges and long shadows toward the camera. A **front-lit** town is flat. Side light (sun 60-90 deg off the view axis) shows form best. **(This last ranking is standard teaching; I found no single numeric source.)**
- **Motivated vs cheated.** Every light should have a plausible source, but its exact position, strength and colour may be cheated for the camera. Fraser's up-lighting is a motivated cheat. Our refinery has plenty of motivation: flare stacks, sodium yard lights, furnace mouths, lit windows.
- **Golden and blue hour.** Low sun gives long shadows, warm key, cool sky fill and maximum rim light. Lubezki bet a whole film on it. Blue hour (after sunset) lets practical lights (windows, lamps, flares) become the key while the sky still holds detail, which makes silhouettes against a bright sky easy.
- **Atmospheric perspective** (Gurney, *Color and Light*). With distance, contrast drops, values move toward the sky value (dark objects get lighter), colours desaturate and cool. Exceptions come with warm haze or dust, and those shift toward the light colour. Jane Ng's *Art of Firewatch* (GDC 2015) builds whole scenes from flat colour layers that lighten toward the horizon, with several fog types so different layers get different colours.
- **Light shafts** need three things: a dark occluder, a bright source behind it, and particulate in the air (smoke, dust, steam). A refinery town supplies all three.

---

## 2. How concept artists work

### 2.1 Deliverables

- **Thumbnails**: dozens of tiny (stamp-sized) value sketches to explore composition before any detail. Dylan Cole (LOTR senior matte painter, Avatar production designer) starts every piece this way (School of Motion, Maxon interviews).
- **Keyframes**: finished, story-moment images from a specific camera, with lighting, mood and characters. Jama Jurabaev's Gnomon course *Creating Keyframe Illustrations for Film* treats these as film frames.
- **Environment design sheets**: orthographic or 3/4 views, callouts and material notes for builders. Feng Zhu's Design Cinema (e.g. ep. 109, the "3/4 room") teaches environment design as functional logic first. Every structure has a job, and detail follows function (FZD; Tuts+ feature).
- **Colour keys and colour scripts**: see 1.5.

### 2.2 Paint-over of blockouts and photobashing

The modern pipeline paints over a 3D blockout:
- **Jurabaev**: about 30 min of rough Blender blockout, a 5 min render, then about 2 h of Photoshop paint-over. The result has camera-correct perspective and plausible light (Gnomon blog).
- **Sparth** paints over renders of untextured Halo level geometry to fix perspective, then "breathes life" into it.
- **Matte painting** (Dylan Cole; ILM). Photo elements are masked and projected onto simple geometry to match the camera, then unified by painting. ILM made about 70 matte paintings for *The Empire Strikes Back*, by Harrison Ellenshaw, Michael Pangrazio and Ralph McQuarrie (starwars.com). McQuarrie's Cloud City drawings were designed as the view from an approaching ship (choicecollect photostat description). That is a concept painted for a *specific approach view*, just like our window.
- **Photobashing**: photo textures dropped into a painting for realism, then painted over for unity.

**Relevance**: our generator already produces blockouts. The cheapest concept art is a screenshot of the generated town from the window, painted over (by the user, or roughly by a script that adjusts values, fog and sky), then used as the **target image** the generator is scored against.

### 2.3 Focal point, detail hierarchy and "read"

Common teaching across Mullins, Sparth, Feng Zhu and Piaskiewicz:
- **One dominant, a few subordinates.** Visual weight comes from size, detail, saturation and contrast. Balance them so one thing wins.
- **Detail budget falls off with distance from the focal point.** The highest edge density and sharpest contrast sit at the focal point. The periphery and background are simplified. (A craft rule rather than a measured one; I found no numeric falloff in a primary source. A practical stand-in is to halve the detail per layer.)
- **Read at a glance.** The image should work as a thumbnail, roughly 1-2 s or a 128 px wide image. Craig Mullins, called the "godfather of digital painting" (Halo: CE matte and concept work, Marathon, BioShock), is the standard example of economy: big value masses, few edges (Sessions College "Why They Work"; Halopedia). **(Uncertain: I could not find a primary Mullins interview stating a rule. This is the common reading of his work.)**
- **Silhouette readability.** Landmarks must be recognisable as a solid black shape. Sparth's hard-edged forms against soft terrain, and Antonov's Citadel (see 3.2), are designed as silhouettes first.
- **Shape language.** Destiny's "mythic science fiction" (Christopher Barrett and Joe Staten, GDC 2013 "Brave New World"; 80.lv) took its world-building feel from 1970s sci-fi paintings with big simple ideas. Syd Mead's industrial-design approach (functional, believable machinery) and Feng Zhu's "function first" belong in the same tradition. **(Syd Mead noted from general knowledge; not re-sourced in this session.)** For a company town the shapes are cylinders (tanks, stacks), long horizontals (pipe racks, conveyors) and repeated boxes (worker housing), with one vertical exception (the tower) as the dominant.

### 2.4 Game examples

- **Half-Life 2 / City 17 (Viktor Antonov).** The Citadel dominates the skyline over Soviet-era brutalist blocks (Wikipedia; Combine OverWiki). Mechanically it lives in the Source **3D skybox**, built at 1/16 scale and drawn 16x. Only its base is real map geometry, and the two parts blend seamlessly. The sky part "grows" as the player approaches (Valve Developer Wiki, *3D Skybox*). This is the canonical game landmark, and a precedent for cheating far geometry with a separate, cheaper scene.
- **Firewatch (Jane Ng, Olly Moss).** Bold flat colour layers, multiple fog colours, and a fixed lookout tower as the player's home viewpoint. It is the closest analogue to our tower window that I found.
- **Naughty Dog (Uncharted, The Last of Us).** Framing, light as the guide, and blockmesh-first level design. Evan Hill's GDC 2022 TLOU2 museum talk and Anthony Vaccaro's aquarium blockouts are on 80.lv. **(I could not get specific composition rules from those articles; the talks themselves are on GDC Vault.)**
- **Horizon Zero Dawn (Guerrilla).** Jan-Bart van Beek's GDC Art Direction Bootcamp talk covers world design. Tallnecks act as walking landmarks. **(Talk contents not verified in detail.)**

---

## 3. Staging cinematic views without cutscenes

1. **Funnel the player to the camera position.** Piaskiewicz: use choke points, windows and ledges to put players at the best observation spot, and keep compositions consistent across the angles players can actually take. A fixed window is the strongest funnel there is: we know the eye position to within about 1 m and the view cone to within the window opening.
2. **Weenies (Disney).** A weenie is a visual magnet on the horizon that pulls people forward. At Disneyland the castle closes the view down Main Street, and secondary weenies (Astro Orbitor, Mark Twain riverboat) pull visitors into each land (Disney Blog; MousePlanet; TouringPlans). For a still view, a weenie is the **destination the player will want to reach**: the mine head, a burning flare stack, the dock with a ship.
3. **Threshold reveals.** Hide the view, then open it (Spielberg's delay in architecture). Stairway landings with a solid wall that suddenly gives way to an opening are the game version of the held reaction shot.
4. **Motion brings stills to life.** Piaskiewicz notes that motion strengthens a dominant. Firewatch and countless other games use moving clouds, birds, smoke and traffic. Motion should be *slow and large* in the background (smoke columns, cloud shadows, a ship), and *small and intermittent* in the midground (a truck, a crane swing, a door light flicking on). Sound reinforces it: a distant horn or a conveyor rumble placed at the source (Audiokinetic ambience-design blog).
5. **View-specific lighting rigs.** Film lights per shot. Games with fixed viewpoints can do the same: the lights that only matter for the window view (rim lights on the far ridge, a fill on the dock face) are placed relative to the view and can be cheated freely, because the player never sees them from the wrong side. That is exactly the Anatomy of Decay idea.
6. **Far geometry as a separate cheap layer.** Valve's 3D skybox; ILM's projected mattes; McQuarrie's paintings designed for an approach view. Unreal II has SkyZoneInfo sky zones that render a separate area as the backdrop. **(Uncertain how far U2's sky zone supports parallax or scale tricks; check in the engine before relying on it.)**

---

## 4. What changes for us

Ranked by expected effect on "feels cinematic" per unit of work. Each item says what to do and how the generator could do it. Everything assumes the generator knows the **viewpoint set** `V = {command window, balcony N/E/S/W, stairway landings}`, each with eye position, look direction, FOV and a 2D frame mask (the window opening).

**1. Score layouts through the window frame (camera-first generation).**
*Rule*: compose for the picture, not the plan (Deakins, Anatomy of Decay, Piaskiewicz).
*Implement*: after each candidate layout, project key objects (landmarks, building bounding boxes, coastline, horizon) into each viewpoint's frame and compute a **frame score**: focal landmark near a thirds intersection (distance to the nearest of the 4 points, normalised), sky/land split near 1/3 or 2/3 and never 0.45-0.55, a dominant mass covering 2/3 of the area, a frame-coverage ratio (town fills 30-60% of the opening; sea and sky the rest), and no **tangents** (a roofline exactly touching the horizon or a mullion). Generate N seeds, keep the best-scoring one, or nudge placement by gradient. This is the single most leveraged change, because every later rule depends on knowing what the camera sees.

**2. One hero landmark (weenie) per view, on a third, as a silhouette.**
*Rule*: a single dominant (Disney weenie, Citadel, Sparth). Counterpoints are smaller.
*Implement*: choose 1 hero per viewpoint (mine headframe, flare stack, refinery cracking tower, harbour crane) and place it so it projects onto a thirds intersection with sky behind it. Check that its silhouette is unobstructed (ray-cast the outline against nearer geometry) and that it is at least 2x taller on screen than anything near it. Give it a unique shape (the only cylinder plus lattice, the only flame). Add 1-2 counterpoints on the opposite third, at less than half its visual weight.

**3. Enforce three depth layers with a gap of air between them.**
*Rule*: foreground frame, midground focal band, background (Piaskiewicz, Brown, Firewatch).
*Implement*: classify every generated object by view distance into FG (the tower itself: rails, pipes, rooftop kit, 0-40 m), MG (town core and hero, ~80-400 m) and BG (far shore, other islands, sea horizon, 600 m+). Leave a band of **empty space between layers** (a road, yard, water or slope) so they separate in value. Place deliberate FG framing objects (a pipe, an antenna, a crane jib entering the frame edge) at the edges of balcony views, darkened and low-detail.

**4. Atmospheric perspective: haze per layer and a value ladder.**
*Rule*: distance lightens darks, lowers contrast, cools and desaturates (Gurney). Aim for 3-4 value groups (notan).
*Implement*: tune U2 ZoneInfo DistanceFog start/end and colour per viewpoint zone, so the MG keeps about 70-80% of its contrast and the BG keeps about 30-40% (**our starting numbers, to tune by eye**). Use a warm-grey fog toward the sun and a cooler one away from it. For a separate far layer (islands), bake the haze into the textures or vertex colours. Add an automated **squint check**: render the view, blur it heavily, quantise it to 4 luminance levels, and confirm that the sky, BG, MG and FG land mostly in different bins and that the hero sits in the highest-contrast patch.

**5. Choose the hour first: low sun behind or beside the town.**
*Rule*: Lubezki/Deakins golden-hour logic. Back or side light gives rim and form; front light is flat.
*Implement*: set the sun azimuth so it sits 90-160 deg from the command window's look direction (side to back light), with elevation about 5-20 deg. Keep a **dusk/blue-hour preset** where window lights, sodium yard lights and the flare are the key and the sky still holds a gradient for silhouettes. Choose the photo sky to match. The generator picks sun and sky from a small colour-script table, so each story beat has its own key.

**6. Rim light and cheated, view-specific lights.**
*Rule*: separate silhouettes from the background; motivated, cheated lights (Brown, Fraser).
*Implement*: for each viewpoint, place a few non-shadowing lights *behind* the hero and the main rooflines relative to the camera, colour-matched to the sun or flare, so edges pick up a highlight. Add a ground or sea bounce fill (Fraser's up-light) as a low warm or cool light under the dock and the town edge. Tag these lights per view and cull them from the other views. Every light should have a believable motivation (flare, furnace, lamp, sky).

**7. Spend detail by on-screen visibility (detail budget).**
*Rule*: detail falls off from the focal point (Mullins, Piaskiewicz).
*Implement*: compute per-building **max projected screen area across all viewpoints**, plus a bonus for proximity to the hero on screen. The top ~10% get full props (signs, pipes, stairs, lit windows, laundry lines). The next ~30% get a medium kit. The rest get boxes with good silhouettes and window cards. Anything never visible from V gets no detail at all, or is not built (Anatomy of Decay). This also keeps the UE2 polycount and draw calls in budget.

**8. Staffage and scale cues, plus a Disney scale cheat.**
*Rule*: known-size objects make scale readable; forced perspective makes things grander (Disney 5/8 and 1/2 storeys).
*Implement*: put visible people, trucks, rail cars and a docked ship at **known sizes** in the MG near the hero. Grow vertical structures (stacks, headframe, tanks) about 1.2-1.5x above "real" (**our guess, to tune**), and scale upper storeys and far buildings down slightly so the town reads larger and deeper from the tower. Keep a denser, taller cluster around the hero so the town does not look scattered at the game's wide FOV.

**9. Motion elements, slow far and small near.**
*Rule*: motion strengthens the dominant (Piaskiewicz).
*Implement*: smoke and steam plumes from 2-4 stacks (emitters drifting with one wind vector shared by the clouds), a flare flicker, scrolling cloud shadows or a slowly panning sky, birds (a small flock path around the hero), a ship crossing the BG over minutes, and MG trucks and rail cars on spline loops with intermittent headlights at dusk. Attach positional ambient sound to each. Put at least one motion element **at or near the hero** so the eye is pulled there.

**10. Leading lines that point into the hero.**
*Rule*: roads, pipe racks, conveyors, shorelines and rails as leading lines (Naughty Dog, Framed Ink).
*Implement*: when routing the main road, conveyor and pipe rack, add a cost term that rewards segments whose **screen-space direction points toward the hero's screen position** from the command window. Use a curved shoreline or road as an S-curve into depth. Avoid lines that lead out of the frame corners.

**11. Threshold reveals on the stairways and balconies.**
*Rule*: delay, then reveal (Spielberg; Disney's Main Street as a framed approach).
*Implement*: on generated stair and walkway routes, place solid walls or enclosed sections before each balcony door, so the town is hidden until the threshold. At the opening, the generator checks that the view's hero lands on a third (rule 1). Different viewpoints get different emotional jobs: the command window is **overview/ownership** (high angle), a low balcony looks **up at the tower and stacks** (low angle, imposing), and one landing gets a **telephoto-like** narrow slot view of the mine head (compression and density).

**12. Paint-over loop: the generator's own concept art.**
*Rule*: blockout + paint-over (Jurabaev, Sparth, ILM).
*Implement*: after generation, auto-capture each viewpoint (the uedlib viewport-screenshot recipe), produce a squinted 4-value version and a thumbnail, and save the images next to the seed. The user paints over the best one (or picks among seeds). That image becomes the target for tuning fog, sun and hero placement. Over time these images form a **colour script strip** for the Avalon beats.

---

## Sources

- Mateusz Piaskiewicz, "Composition in Level Design", Game Developer, 2014. https://www.gamedeveloper.com/design/composition-in-level-design
- Wikipedia, "Rule of thirds" (Smith 1797, Reynolds, Freeman). https://en.wikipedia.org/wiki/Rule_of_thirds
- Roger Deakins on lenses (ymcinema.com, 2021) and on camera distance (rogerdeakins.com forum). https://ymcinema.com/2021/08/06/roger-deakins-talks-about-lenses-spherical-primes-preferred ; https://www.rogerdeakins.com/forums/topic/distance-and-position-of-camera/
- Lubezki and The Revenant natural light: Slashfilm, Videomaker, Tribeca interview. https://slashfilm.com/827956/every-day-on-the-revenant-set-was-a-race-against-time
- Greig Fraser, The Cinematography Podcast ep. 257. https://www.camnoir.com/ep257/
- Jurassic Park reveal: What's in a Scene. https://whatsinascene.substack.com/p/jurassic-park
- Lens compression: Tamron, DIYPhotography. https://www.diyphotography.net/telephoto-lens-for-landscape-compression/
- James Gurney, *Color and Light* (2010): atmospheric perspective. Book; summaries via LibreTexts.
- Marcos Mateu-Mestre, *Framed Ink* (2010); Francis Glebas, *Directing the Story* (2008); Blain Brown, *Cinematography: Theory and Practice*. Books; contents checked via publisher pages and reviews only.
- Notan and value grouping: Artists Network; Proko value-composition thumbnails. https://www.artistsnetwork.com/art-mediums/pastel/the-value-of-notan/
- Pixar colour scripts: MoMA *Pixar: 20 Years of Animation*; Thunderchunky interview with Lou Romano. https://www.thunderchunky.co.uk/articles/pixar-colour-and-tent-poles-with-lou-romano/
- Jane Ng, "The Art of Firewatch", GDC 2015. https://gdcvault.com/play/1022296/The-Art-of
- Erick Pangilinan, "Uncharted 2 Art Direction", GDC 2010. https://gdcvault.com/play/1012799/Uncharted-2-Art
- Evan Hill, TLOU2 level design, GDC 2022 (via 80.lv). https://80.lv/articles/a-deep-dive-into-level-design-behind-the-last-of-us-part-ii
- Jan-Bart van Beek, Horizon Zero Dawn Art Direction Bootcamp, GDC. https://gdcvault.com/play/1025049/Art-Direction-Bootcamp-A-No
- Joe Staten & Christopher Barrett, Destiny "Brave New World", GDC 2013 (80.lv). https://80.lv/articles/world-building-and-art-direction-of-destiny/
- Viktor Antonov / City 17: Wikipedia; Valve Developer Wiki, "3D Skybox". https://developer.valvesoftware.com/wiki/3D_Skybox
- Disney weenie: Disney Blog; MousePlanet. https://disneyblog.com/blog/the-weenie-walt-disneys-most-important-design-idea/ ; forced perspective: https://duchessofdisneyland.com/tips-trivia/forced-perspective/
- Jama Jurabaev, Gnomon "Creating Keyframe Illustrations for Film". https://ilm.thegnomonworkshop.com/blog/creating-keyframe-illustrations-for-film/
- Sparth: Art-Spire interview; DesignCurial. https://old.designcurial.com/news/home-is-where-the-sparth-is-halo-5s-creator-4763463/
- Dylan Cole: School of Motion. https://www.schoolofmotion.com/blog/dylan-cole-world-creator
- Craig Mullins: Halopedia; Sessions College. https://www.sessions.edu/notes-on-design/why-they-work-craig-mullins/
- ILM Empire matte paintings and McQuarrie. https://starwars.com/news/empire-at-40-5-amazing-matte-paintings-from-star-wars-the-empire-strikes-back
- Feng Zhu / FZD Design Cinema: Tuts+ feature. https://design.tutsplus.com/articles/the-work-of-master-concept-artist-feng-zhu--psd-17368
