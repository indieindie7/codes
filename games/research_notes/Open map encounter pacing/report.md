# Open map encounter pacing: research for the U2 chapter-1 open map

Research agent, 2026-10-08; saved by Claude.

**Target:** one open, drivable ~1.2 km map (Sanctuary Open) with six places in route order: LZ, haul road, ore plant (on-foot interiors), open plateau field, power plant/generator, extraction pad. There is a hover bike. The enemies are Izarian grunts (shooters), Skaarj (leaping rushers) and one heavy Skaarj tank.

**Legend:** [src] = a cited source says it. [inf] = my own inference or a number I derived.

## 1. Takeaways: rules a generator can check

### Spacing along the route

1. **Quiet-travel cap of about 40 s.**
   - No critical-path stretch runs longer than ~40 s at the expected speed without something to notice: a fight, a reveal, a pickup, radio, or a visible enemy.
   - Measured open-world averages are 32 s (Witcher 3), 42 s (BotW) and 49 s (New Vegas) [src]. A gap over ~90 s fails.
   - A POI guide allows 60–120 s between POIs, but that counts optional content [src].
   - How to score it: segment time = length / speed, using bike speed on the road and plateau and on-foot speed in the plant.
2. **Relax after every peak.**
   - 30–45 s of low threat after a fight: no new waves, stragglers only. End it early if the player pushes on (Left 4 Dead's "Relax") [src].
   - Start the relax timer only after the fight has actually wound down ("Peak Fade") [src].
3. **Encounter length.**
   - Each fight is a ~30 s loop (see, plan, execute) inside a ~3 min encounter (reinforcements, retreats, waves), inside the mission [src].
   - Each place holds 1–3 encounters of 1–3 min [inf].
4. **Change the context at every place.**
   - Each place differs from the previous one in at least 2 of: space type, enemy mix, bike or foot, objective type. Griesemer: "No 30 second stretch of Halo is ever repeated" [src].
   - No two adjacent places share both the enemy mix and the movement mode [inf].

### Waves, triggers, reinforcements

5. **Two-stage fallback per defended place.**
   - Enemies hold forward territory, fall back below 75% alive, and make a last stand below 50%. This is Halo 3's "3 generators" example, with groups capped at 10 [src].
   - Each encounter gets one "spice" element: a sniper, a turret or a dropship [src].
6. **Leaders break squads.**
   - Halo pairs a Brute with 3 Grunts; when the leader dies, the followers are "broken" and flee or panic [src].
   - In U2 terms: a Skaarj or veteran grunt leading 3 grunts [inf].
7. **Concurrent cap.**
   - Halo CE ran 20–25 actors and 2–4 vehicles [src].
   - Warframe caps at about 20–30 live enemies, raised slightly in an alert; that figure is a community claim [src].
   - For U2/UE2: about 12 live enemies near the player, about 20 map-wide [inf].
8. **Every reinforcement has a visible cause.** No silent spawns. Examples [src]:
   - Far Cry 3 outposts hold 5–10 guards, and an alarm panel calls a truck.
   - Orb Vallis beacons, up to 4 at once, raise the alert; destroying them lowers it.
   - Warframe Liberation and Resource Theft are 1:30 holds with reinforcements "en masse".
   - Warframe Spy gives a 60 s alarm window.
   - BotW lookout horns alert the whole camp.
9. **Waves.**
   - Destiny events usually run 2–3 waves then a boss [src]. Warframe Exterminate is 25 kills in 5–7 min [src].
   - For this map: an objective fight is 2–3 waves of 4–8, then an optional elite. Wave n+1 comes when wave n drops to 25–50% alive or after 45–60 s, whichever is first [inf].
10. **Mob size grows.**
    - L4D mob size ramps from a minimum to a maximum over time [src].
    - The first wave in each place is the smallest [inf].

### Hidden spawns, visible entrances

11. **Spawn out of sight, enter where it can be seen.**
    - L4D spawns only in active, not-visible areas, 75% of them behind the team [src]. Warframe spawns in unobserved rooms [src].
    - Every spawn is out of sight when it triggers and enters through a readable entrance: dropship, door, burrow, cliff-top leap or elevator. At most one telegraphed wave from behind per encounter [inf].
12. **Carriers can be killed before they unload.**
    - Orb Vallis Condors and Coildrives can be destroyed before deploying [src].
    - At least one wave per mission arrives in the open by dropship over the plateau [inf].

### Story beats, optional content, rest

13. **The critical path is a 3–5 stage chain.**
    - Warframe bounties reveal the next marker only when the current stage is done, each stage has a bonus, and rewards get rarer by stage [src].
    - Here: LZ plus 5 stages, each with one bonus condition [inf].
14. **Optional content sits off the spine.**
    - Models: Destiny Lost Sectors, Halo Infinite HVTs, BotW skull camps [src].
    - 1–2 optional pockets on the whole map, each visible from the critical path, taking 1–3 min, and paying out something useful later [inf].
15. **Don't run everything at full intensity.**
    - 343: a Golden Path dialled to 11 "starts feeling pretty flat" [src].
    - At least one clear low (rest or vista) between any two highs [inf].
16. **Safe points are earned and functional.**
    - Halo Infinite FOBs resupply, provide vehicles and reveal POIs. Destiny 2 announces events 5 min ahead, with a rally flag [src].
    - Here: the LZ and the cleared plant become safe points [inf].

### Vehicles vs on foot

17. **Vehicle fights need a vehicle.** Isla: "Vehicle encounters are not fun without a vehicle." So the bike is within ~50 m of every road or plateau fight [src/inf].
18. **Vehicles connect places; fights happen on foot.** Silent Cartographer's Warthog circles the island, and its interior is on foot; Halo Infinite alternates open areas with linear interiors [src].
19. **Bike lockout.**
    - Griesemer used rocks to force on-foot Hunter fights, and letting players skip encounters "ruins" them [src].
    - Interiors and the heavy-Skaarj arena are bike-blocked by doors, rubble or narrow gates, with a visible parking stop [inf].

### Escalation

20. **Escalation order.**
    - Halo's toolbox is "exhausted around the halfway point" [src], and boss fights skip adaptive relax [src].
    - Order for this map: grunts only, then grunts plus a dropship, then the first Skaarj with a staged reveal, then mixed fights in the open, then everything plus the heavy Skaarj boss, then a timed hold [inf].
21. **A global alert ratchet.**
    - Orb Vallis alert runs 0–4 stars, rising while beacons live [src].
    - One alert value (0–3) rises on stage completion or tripped alarms and scales wave size x1.0 / 1.25 / 1.5 / 1.75 [inf].

### Blocking and unblocking space

22. **Gate by stage, and make the gate visible.**
    - Halo Infinite opens zones with the story; Destiny's Darkness Zones are mission-only [src].
    - Each gate is part of the world, seen before it opens: a power door, a lift bridge, a shield wall, a rockfall. The previous stage opens it [inf].
23. **Reuse by changing state, not geometry.**
    - Destiny reuses spaces through systemic changes [src].
    - The return trip re-crosses a visited place in a changed state: night, alarm, new spawns [inf].

## 2. Per-game findings (with sources)

### Halo (Bungie)

- **"The Illusion of Intelligence"** (Butcher and Griesemer, 2002), https://www.jmeiners.com/shamans/papers/ai/the_illusion_of_intelligence.pdf
  - Code owns the 30 s scope, design owns the 3 min scope.
  - Budget: 20–25 actors and 2–4 vehicles, about 15% of the CPU.
  - Tools: battle lines, killing zones, retreat conditions.
  - Playtests: tough enemies rated "about right" by 92% of players, weak ones by 52%.
- **The "30 seconds of fun" quote, read in full:** "No 30 second stretch of Halo is ever repeated." The loops nest 3 s / 30 s / 3 min. https://www.engadget.com/2011-07-14-half-minute-halo-an-interview-with-jaime-griesemer.html
- **Halo 3, "Building a Better Battle"** (Isla), https://web.cs.wpi.edu/~rich/courses/imgd4000-d11/lectures/halo3.pdf and https://gamedeveloper.com/game-platforms/in-depth-bungie-on-eight-years-of-i-halo-i-ai
  - The encounter runs territory, then fallback, then last stand, then the enemy breaks.
  - Spice: snipers, turrets, dropships.
  - Halo 2's triggers were "<75% alive" and "<25% alive". Groups are capped at 10.
  - Squads are assigned to tasks by priority ("plinko").
  - A leader's death breaks the followers.
  - Vehicle encounters need a vehicle.
- **Revisiting Halo 3:** wide outdoor spaces split into discrete encounters; leaders are the priority targets. https://www.gamedeveloper.com/design/revisiting-halo-3
- **Silent Cartographer:** a beach landing, then the Warthog circles the island and meets resistance at each point. It feels open, but the sequence after the LZ is strict. https://pcgamer.com/halo-infinite-is-not-the-silent-cartographer ; https://www.halopedia.org/CE:The_Silent_Cartographer/Walkthrough
- **Halo Infinite:**
  - FOBs reveal POIs and provide fast travel, resupply and vehicles. HVTs are named minibosses. Bases support many approaches. Zones unlock with the story. https://gameinformer.com/2021/11/10/off-the-golden-path-progression-and-exploration-in-halo-infinite
  - HVTs were placed in spaces at risk of being cut: https://kalebnek.artstation.com/projects/RnK1Vr
  - A full-intensity path feels flat: https://mobilesyrup.com/2021/12/07/xbox-343-industries-halo-infinite-interview/

### Destiny 1/2 (Bungie)

- **Public events:** announced 5 min ahead in D2, with a rally flag; zero or one per sector. D1 events were timed with Bronze/Silver/Gold grades (Extraction Crews was 3 waves; Cryo-Pod was waves then a boss). https://www.destinypedia.com/Public_Event ; https://primagames.com/eguides/destiny-2-eguide/public-events
- **Heroic versions** come from an optional condition met during the event. https://www.shacknews.com/article/101337/destiny-2-how-to-trigger-all-heroic-public-events ; https://destinytracker.com/article/201/heroic-public-events-how-to-start-them
- **Protocols:** Escalation Protocol is 7 waves with a boss; Altars of Sorrow is time-per-kill.
- **Lost Sectors:** hidden doors into small hand-made dungeons, "meant to be done pretty quickly". https://stevivor.com/news/destinys-dungeon-like-lost-sectors-arent-procedurally-generated/
- **Darkness/Restricted Zones:** mission-only space. https://www.destinypedia.com/Darkness_Zone
- **GDC talks:**
  - Truman, "Shared World Shooter": https://gdcvault.com/play/1022247/Shared-World-Shooter-Destiny-s
  - Blaine, the seven difficulty stressors (2022): https://gdcvault.com/play/1027550/1000-Hours-of-Difficulty-How ; https://massivelyop.com/2022/03/29/gdc-2022-learning-from-the-seven-game-stressors-in-destiny-2/
- **Rotating hot zone:** Lightfall's Vex Incursion Zone moves daily. https://www.destructoid.com/how-to-complete-the-vex-strikeforce-public-event-in-destiny-2/

### Warframe (Digital Extremes)

- **Bounties:** 3–5 random stages, the next one revealed on completion, each with a bonus, and rewards kept on failure. https://wiki.warframe.com/w/Bounty
- **Plains of Eidolon stages:**

  | Stage | Requirement |
  |---|---|
  | Assassinate | 15 kills in 5 min |
  | Cache | 3 caches in about 3 min |
  | Capture | 5 s, then drop pods |
  | Drone Hijack | Escort 700 m, moving only within 50 m of a player, with drop pods along the path |
  | Exterminate | 25 kills in 5 min |
  | Liberation | Kill the marked enemies, then a 1:30 hold with heavy reinforcements |
  | Rescue | Starts a 30 s collar timer on alert |
  | Supply Sabotage | 3 drops in 5 min, with 4–5 reinforcements each |

- **Orb Vallis stages:** Coildrive hack plus a 1:30 defence; Spy with a 60 s alarm window.
- **Enemy level tiers:** 5–15 up to 40–60.
- **Orb Vallis alert:** up to 4 stars; beacons (at most 4) raise it. Reinforcements arrive by Condor, Coildrive or beam drop, and the carriers can be destroyed before unloading.
  - https://www.warframe.com/patch-notes/switch/24-0-0 ; https://wiki.warframe.com/w/Terra ; https://wiki.warframe.com/w/Coildrive
- **Spawns (community, low confidence):** enemies appear in unoccupied rooms within a min/max distance, with a 20–30 live cap. https://wiki.warframe.com/w/User_blog:FocusedTub/Enemy_spawns

### Left 4 Dead AI Director (Valve)

Booth, "The AI Systems of Left 4 Dead" (2009): https://steamcdn-a.akamaihd.net/apps/valve/2009/ai_systems_of_l4d_mike_booth.pdf

- **Pacing states:**
  - Build Up: full threat until intensity peaks.
  - Sustain Peak: 3–5 s.
  - Peak Fade: minimal threat until a natural break.
  - Relax: 30–45 s, or until the team has travelled far enough.
- **Intensity** rises with damage and with nearby kills.
- **Bosses** are excluded from adaptive pacing.
- **Mobs** come every 90–180 s, and their size ramps up.
- **Placement:** 75% behind the team, never in view. Slow specials spawn ahead; smokers above.
- **L4D2 script defaults differ:** Sustain Peak 5–10 s, Relax 1–5 s. https://developer.valvesoftware.com/wiki/L4D2_Director_Scripts

### Far Cry outposts

- 5–10 guards per outpost, and an alarm panel calls a reinforcement truck.
- A cleared outpost turns friendly with fast travel and shops; an outpost reset option was added later.
- Sources: https://pcgamer.com/far-cry-3-review ; https://www.thesixthaxis.com/2012/10/11/far-cry-3-interview-with-dan-hay/

### Breath of the Wild

- **Visible attractions:** 1–2 towers and a couple of attractions on screen; 2–3 places revealed per crest. Triangle-shaped terrain hides what lies behind and forces choices. https://gmtk.substack.com/p/how-nintendo-solved-zeldas-open-world
- **Camps:** skull rocks make them readable from far away, lookout horns alert the camp, and chests open only when it's cleared. https://zeldawiki.wiki/wiki/Monster_Stronghold
- **The 40-second rule:** measured BotW 41.8 s, Witcher 3 32.2 s, New Vegas 48.8 s. Ghost of Tsushima's developers said every 3 min is "too long". https://www.gameinformer.com/2021/05/20/more-than-just-dots-on-a-map-the-challenges-behind-open-world-game-creation

## 3. Applying it to the 1.2 km, six-place map [inf]

- **Speeds:** on foot ~440 uu/s; the Manta cruises at 1100–1200 uu/s on this map (measured in U2Hover; the research assumed 1500–2000).
- **Crossing times:** the whole map takes ~150 s on foot and ~50 s by bike.
  - Bike legs need a contact or reveal every 250–400 m: a roadblock, a dropship flyover, a Skaarj leaping onto the road, a vista.
  - Foot legs need no more than ~40 s of walking between contacts.
- **Beat sheet, about 15–20 min on a first play:**

  | # | Place | Content | Intensity |
  |---|---|---|---|
  | 0 | LZ | A small grunt tutorial; becomes a safe point | low → mid |
  | 1 | Haul road | A roadblock, plus a dropship drop that can be shot down; one optional pocket (the crashed hauler) | mid |
  | – | Road end | Rest at the gate stop | low |
  | 2 | Ore plant | The outpost template, a staged first Skaarj; becomes a checkpoint | mid → high |
  | – | Plant exit | Rest | low |
  | 3 | Plateau | 2–3 objectives in any order, each raising the alert; dropships and burrowing Skaarj; the bike within 50 m; an optional nest | high, in pulses |
  | – | Generator ridge | Rest, with a reveal of the power plant | low |
  | 4 | Power plant | Bike-blocked; 2 waves (≤ 8; next at 25–50% alive or 60 s), then the heavy Skaarj; heroic bonus | peak |
  | 5 | Extraction | A 1:30–2:00 timed hold, with entrances only through visible openings | high → end |

- **Generator checks:**
  - Quiet-travel gap ≤ 40 s.
  - A rest of ≥ 30 s after each peak.
  - Squads ≤ 10; ≤ 12 enemies active near the player.
  - Every spawn hidden when it triggers, entering through a tagged entrance.
  - Adjacent places differ in ≥ 2 of the 4 context axes.
  - Every gate tagged with the stage that opens it.
  - ≥ 1 bike-locked fight and ≥ 1 fight that needs the bike.
  - ≤ 2 optional pockets.
  - The intensity curve has one peak (the power plant) and ends with the final hold.

## 4. Gaps

- **Destiny:** no primary Bungie source on patrol-zone layout or activity density. Bungie.net didn't render for the fetcher, and the GDC 2022 coverage returned 403. Check GDC Vault (Blaine, Truman) and Bungie's "Director's Cut" posts by hand.
- **Warframe:** extraction rules for the open landscapes and the per-stage enemy-level ramp weren't found. The spawn-cap figures are community claims, and Cambion Drift wasn't read.
- **Halo Infinite:** no FOB density or base-assault spawn counts.
- **Far Cry and BotW:** no developer talks; the details come from reviews and wikis.
- **The 40 s rule** depends on playstyle: use it as a ceiling, not a target.
