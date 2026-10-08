# Sanctuary Open: writer pass

Writer review, 2026-10-08. Inputs: `dialogue_playlist.md`, `dialogue_check.md`, `STORY.md`, the shipped `.dlg` files (M08A, M08B, PA_Sanctuary) and the OpenDirector section of `System/U2Sanctuary.ini`. Rules are numbered as in `research_notes/Dialogue heuristics/report.md`. I am an LLM judge, so these are the limits I worked to:

- every flag quotes the node and its text;
- criterion 7 (voice and performance) is **not scored**;
- there are no rewrites, only cut, trim, move, retime, bark/unbark and props;
- anything that depends on delivery goes on the EAR list at the end.

## Who speaks (inferred; the Speaker field says "Player")

| Node(s) | Speaker | Basis |
|---|---|---|
| 06_002, 06_004 | Aida (from orbit) | "Yes, mother." (06_003) answers 06_002; 06_004 "come down there" is said from the ship |
| 06_003, 06_005 | Dalton | |
| 15G_002/004/006a-c/007/008, 16G, 17G, 18G, 19G, 20G, 22G, 23G, 98, 99_002, all G barks | Miller (SoundActor=LookTarget = a camera) | |
| 15G_003, 15G_005 | Dalton (the "can you hear me" pair) | |
| 20_002 (end of 15G) | Aida | "Jesus, John." |
| 10_002 / 10_003 | Aida / Dalton | |
| 13_002 / 13_003 | Dalton / Aida | "Hey Aida" / "I don't like this, John." |
| 99_003-005 (NOT played now) | Dalton | shouting at Miller, who can't hear him |
| 15_001-007 | Miller (screams) | |
| 15_011-015, 17_003-010 | the plant's computer voice | |
| 16_002 Aida, 16_003 Dalton, 16_004 Aida, 16_005 Dalton, 16_006 Aida, 16_007 Dalton, 16_008 Aida | | |
| 18_002 | Aida ("I decrypted a Skaarj intercept") | |
| 19_002 / 19_003 | Dalton / Aida | |
| XX | a Marine and Dalton | |

**STORY.md correction:** STORY.md says Miller "calls HQ, and the Marines are coming for it". That is wrong. In 19_003 Aida says "I called HQ and they went ape", after Dalton reports "I got the artifact" (19_002). STORY.md also gives "search and rescue. No rough stuff" (06_002) to Dalton; it is Aida's line, and Dalton answers "Yes, mother." Confirm both by ear.

## Rubric (criteria 1-6, as it plays now)

| # | Criterion | Score | Evidence (quoted) |
|---|---|---|---|
| 1 | Truth to the world | **1** | (a) 15G_002: "Sir! Up here! The camera!", but the open map builds no camera (the R23 flag). The same goes for 16G_002 "Get away from the camera" and 15G_008 "There's a camera on the other side". (b) 22G_002: "Oh, right! The security door." There is no door, and nothing the player did prompts "Oh, right!". (c) 17_003: "Main terminal online." There is no terminal and nobody used one. (d) field: 19G_002 "I don't see any of those creatures around" plays about 30 s after 98_002 "I can't track you outside". (e) Barks: Miller's "Great shot!" (17bG_002) can play in the road fight, before Miller has been introduced at the gate, and in the shaft and pad fights, after his death at `power`. (f) 16_008 sends the player to "the control room"; none is built. |
| 2 | Timing vs play load | **1** | The mechanical check scores R15 at 0.42. gate: 57 s of 15G under fire, from "Sir! Up here!" to "Were WE ever that green?". power: the whole Miller death and Aida argument (99_002, 15_001, 16_002, about 34 s) runs while a SkaarjMedium arrives at +3 s. shaft: 18_002 "If you're going down there, be careful" plays with the Heavy Skaarj already out (+2 s). field: 13_002 "vacation spot for Skaarj?" is queued 4 s before the Skaarj exists. |
| 3 | Repetition | **1** | Two of the five bark files are the same words: 16bG_002 and 24G_002 are both "Behind you!". The draw is random every 14-24 s with no shuffle bag, so the same file can play twice inside 30 s. Over ~595 s of fighting each bark is heard about 3.8 times. No story line repeats. |
| 4 | Reactivity / relevance | **3** | Most story lines sit at their own place. The barks, though, are pure timer chatter that claims events: "Behind you!", "Great shot!" and "Kick ass!" play whether or not anything is behind the player or anything was hit (R17). Story lines fire before their cause: 10_002 "How's your suit pressure?" plays on entering the basin radius, before the swim; 13_002 plays before the Skaarj appears. 23G_002 "So...? Nothing happened, right?" answers a worry (22G_004 "None of the cameras work") that the playlist doesn't play. |
| 5 | Economy | **3** | Every exchange has a point. Padding: 06_001 and 15_001/15_008 are empty nodes (silent 1 s slots, harmless). 20G_002 opens with "Whew! I thought I'd lost you." although Miller spoke seconds earlier at the basin (17G_002). 22G_002 + 23G_002 is ~9 s that leads nowhere. 17_003 "Main terminal online." is a one-line orphan. |
| 6 | Exchange quality | **3** | Turn-taking inside the authored chains is clean. Exchanges that turn nothing or are left hanging: 99_002 "I'm right around the corner. Be right out!" goes unanswered, because Dalton's replies 99_003 "No! It's not safe. I haven't cleared the area yet!", 99_004 "Stay put!" and 99_005 "Damn kid's going to get himself killed." are not played. That drops the level's best friction beat (Dalton shouting at a man who can't hear him) right before Miller dies. Probable clash: Miller barks run on the fight timer during the 59 s gate conversation, so one Miller voice can cut across his own story line (R3; verify in the log whether barks wait for the story queue). |
| 7 | Voice and performance | **not scored** | Human only (see EAR). |

Note on the mechanical R22 list: 06_004 "come down there" is **true**, because Aida is in orbit. 16_005 "Get me down there!" and 18_002 "If you're going down there" are true only if the shaft reads as a hole going down, so check what the player sees from the trigger.

## Edits

One row per conversation or line. "Beat X'" means a new OpenDirector beat at the same place with `After="X!"` (fires once X's fight is cleared); the director already supports the `!` suffix.

| # | Node | Quote | Problem (rule) | Edit | Conf. |
|---|---|---|---|---|---|
| 1 | Barks (all Miller G barks) | "Great shot!" / "Behind you!" | Miller barks before his intro (road), outdoors after "I can't track you outside" (field, pit), and after his death (shaft, pad) (19, 21, 24) | **Gate barks by place and state:** allow them only in the gate, yard and drainage fights (after 15G_002 has played and before 98_002). No Miller barks at road, field, pit, power, shaft or pad. | high |
| 2 | 24G_002 | "Behind you!" | duplicate of 16bG_002 (16) | Cut it from the bark set (see the bark set below) | high |
| 3 | gate: 15G_002..008 + 20_002 | "Sir! Up here! The camera!" | 57 s of story under fire (15, 18); no camera (23) | Start the gate wave (1 Izarian) **after** the 15G chain ends (Delay ≈ 62 s or a talk-done trigger). **Add prop:** a security camera high on the gate wall, facing the arrival point, so "Up here! The camera!" is true. Keep the whole chain; with the fight out of the way it is the level's setup. | high |
| 4 | gate → yard | (whole 15G) | The yard (its own fight at +1 s) can trigger while the gate talk is still running (20, 26) | Make `yard` wait for the gate talk to end, or make the gate a NoBike zone so the player stays on foot for the 59 s | med |
| 5 | 18G_002 (yard) | "Careful--a lot of that stuff is unstable." | Only one ExplosiveCannister in the yard: "a lot of that stuff" isn't true (19, 23); it currently plays after 16G, during the fight | Reorder the yard topics to **18G_002 first, then 16G_002**, and move the yard's first wave to Delay ≈ 6 s so the warning lands before the enemies. **Add prop:** 4-6 more explosive canisters/barrels near the two Izarian doors. | high |
| 6 | 16G_002 (yard) | "Get away from the camera, you space-monkey freaks!" | A reaction with no camera and no Izarians at a camera (19, 21, 23) | Fire it as the first yard Izarians appear (it falls naturally right after 18G with edit 5). **Add prop:** a camera on the yard wall between the two doors (LookTarget1). One-shot, never a bark. | med |
| 7 | 10_002 / 10_003 (basin) | "How's your suit pressure?" / "blood is thicker than water" | Fires on entering the basin radius, before the swim (21) | Fire on **leaving the water**: a new beat `basin_out` at the far side of the swim, small radius, After=`basin`, Topics=`10_002,17G_002`. The `basin` beat itself gets no talk. If there is no swimmable water, cut 10_002 and trim 15G to 002..006c + 20_002. | med |
| 8 | 17G_002 / 17G_002b | "Miller here. You're a mess. And blue is definitely not your color." / "...pulled this alien...thing up from the mine... Broke a drill bit on it" | 15G_008 promised "There's a camera on the other side"; no camera (23). 002b is a protected beat line (25): the only setup for the artifact | Keep both, at `basin_out` after 10_002. **Add prop:** a camera at the basin exit. Optional: blue Izarian gore near the exit so "blue is not your color" reads. The pit's broken drill rig already makes 002b true if the player visits it. | high |
| 9 | 20G_002 (drainage) | "Whew! I thought I'd lost you. Next up is the drainage room..." | "I thought I'd lost you" is false: Miller spoke seconds earlier (19, 21). "Next up is the drainage room" plays as the wave arrives at +1 s: setup after reveal (15, 21) | **Trim** the opening "Whew! I thought I'd lost you." so it starts at "Next up is the drainage room." **Move the drainage wave to Delay ≈ 9 s** (after the line). Drainage must also wait for basin_out's talk. | med (trim: EAR) |
| 10 | 22G_002 (+22G_003, 22G_004 if the game follows the lower-case NextNode) | "Oh, right! The security door. Hold on, I'll open it up." | No door, nothing for "Oh, right!" to answer (1, 19, 23) | **Cut** the whole 22G conversation | high |
| 11 | 23G_002 | "So...? Nothing happened, right? That's a relief." | Orphan reply: its setup (22G_004) is cut or unplayed (1, 21) | **Cut** | high |
| 12 | 19G_002 | "Good news, sir! I don't see any of those creatures around. I think you've got an easy ride from here on in." | At `field` it contradicts 98_002 "I can't track you outside" (19, 24) | **Move it to `dark`** (after drainage is cleared, inside the plant, where Miller has cameras). It plays before 98_002, and the irony still pays off when the Skaarj leaps at the bike in the field. | high |
| 13 | 98_002 (exit) | "The exit is up ahead. I can't track you outside..." | none; it explains Miller's silence outdoors | Keep. Check that "up ahead" faces the exit from the exit trigger (22). | high |
| 14 | 13_002 / 13_003 (field) | "Hey Aida, does your guidebook list this as a vacation spot for Skaarj?" / "He's probably checking up on his Izarian grunts. I don't like this, John." | Fires 4 s before the Skaarj exists (21) and under fire (15) | Move it to a new beat `field'` (After=`field!`). It plays after the open-ground fight, in the quiet before the drive, over the dead Skaarj and Izarians, so "grunts" is backed up by what the player just fought. The field arrival stays silent, so the Skaarj leap is the reveal. | med |
| 15 | 99_003 / 99_004 / 99_005 (unplayed) | "No! It's not safe. I haven't cleared the area yet!" / "Stay put!" / "Damn kid's going to get himself killed." | 99_002 "Be right out!" goes unanswered (1, 11) | **Add** them to the `power` topics right after 99_002 (they are separate nodes; keep their Delay 1.5 / 2.0). "I haven't cleared the area yet" is true only before the power fight, so they must play on arrival. | high |
| 16 | 15_011 / 15_012 / 15_015 (unplayed) | "Obstruction detected." / "Emergency shutdown in 3...2...1..." / "Emergency shutdown complete." | Without them, nothing shows how Miller died, and 16_005 "That kid just died" has no cause on screen (21, 24) | **Add** after 15_001 (the screams) in `power`. | med |
| 17 | power wave 1 (SkaarjMedium, +3 s) | (under 99/15/16) | The emotional peak plays under fire (15) | Move the power wave to **after the arrival talk** (99_002..005, 15_001, 15_011..015, about 35 s): the Skaarj arrives straight after "Emergency shutdown complete." Optional prop: a blood trail from the security office door toward the shaft (STORY's Miller vignette). | high |
| 18 | 16_002..16_008 | "Pull out!" ... "That kid just died..." ... "go to the control room and power up the generator" | Under fire at power (15); "control room" not built (23) | **Fire after the power fight:** new beat `power'` (After=`power!`) with Topics=`16_002,18_002`. Show the objective "Find the generator control room" with this beat, not on arrival. `shaft` waits for `power'` (After=`power'`). **Add prop:** a console/terminal block at the top of the shaft so "the control room" names something. | med (EAR: does "Pull out!" still land a minute after the death?) |
| 19 | 18_002 | "If you're going down there, be careful. I decrypted a Skaarj intercept..." | Plays as the Heavy Skaarj spawns (15) | **Move it to `power'`**, after 16_008, so it's heard at the shaft top before going down | high |
| 20 | 17_003 | "Main terminal online." | No terminal, no player action; an orphan (1, 19, 23) | **Cut** | high |
| 21 | 17_004 / 17_005 / 17_006 (unplayed) | "Foreign object detected in generator." / "Analyzing..." / "Alien lifeform detected in generator." | none; an optional build-up for the Heavy Skaarj | Optional: play them on `shaft` arrival and delay the Heavy Skaarj wave until after 17_006 (≈ +8 s). The computer announces the Skaarj, then it appears. Needs the console prop from edit 18. | low |
| 22 | 17_008 / 17_009 / 17_010 (unplayed) | "Startup sequence engaged." / "Retracting shield." / "Generator now online." | The objective "Reactivate the generator" has no line marking it done (21) | Optional: play them on `shaft!` before `artifact`'s 19_002. Cut 17_007 ("press override button": there's no button). Only if the shaft shows a shield/artifact reveal. | low |
| 23 | 19_002 / 19_003 (artifact) | "I got the artifact..." / "Get to the surface and hunker down until they get there." | The pad waves start at t+5 while this plays (15, minor: the player is at the shaft, 9 s from the pad) | Start the hold timer, or at least the first pad wave, **after 19_003 ends** (≈ +16 s) | med |
| 24 | XX_001..006 (marines) | "Nice work, Marshal. You shoulda been a Marine." | Can fire with the t+120 wave still alive (15) | Fire after `hold` **and** the pad is clear (or have the landing clear it). Keep XX_006 "Will do. Semper Fi.": a sign-off that carries character (the Marine sore point) (12). | med |
| 25 | 06_001..06_005 (arrival) | "Remember now, search and rescue..." / "Relax. I'm sure the natives are friendly." | 14 s; the road fight is ~10 s away (26) | No cut. Make the road wave wait for the arrival talk to end, so the "natives are friendly" irony lands on the road bodies rather than over gunfire. | med |
| 26 | road / pit | (no lines) | | **Keep both silent.** No unused line is about the outdoors, the drive or the mine pit. The pit's drill rig pays off 17G_002b visually, and the cache message is text. Don't move Miller there: he can't track the player outside (98_002). | high |

Rejected options:
- 11_002 "Go back!" and 14_002 "Thank God! Help me!" both need a living scientist pawn, and a voice from nowhere would be false (19).
- PD_Sanctuary_01 "We've got more trouble down there" belongs to a different mission.
- 22G_004 "None of the cameras work, so I can't see if anything's in there" as a field setup: "in there" points indoors.

## Proposed bark set

Speaker: Miller only. Barks are **only allowed in plant fights** (gate, yard, drainage), from after 15G_002 to 98_002. No barks at road, field, pit, power, shaft or pad: Miller can't see outdoors and is dead after `power`, and no Aida or Dalton barks exist. So the 150 s pad hold is fought without voice, which is correct.

Priority: story line > bark. A bark never starts while a story line is playing or queued, and it is dropped rather than queued.

Preferred version (event-triggered):

| Category | Event | Lines | Cooldown |
|---|---|---|---|
| Kill reaction | player kills an Izarian | 17bG_002 "Great shot!", 24G_003 "Nailed 'em!", 16bG_005 "One more dead alien!", 21G_002 "Kick ass!", 16bG_003 "Eat that, space monkey!" (play its chained 003b "Over there!" only if enemies remain) | 20 s category; shuffle bag, no repeat until all are used |
| Spotted | a wave spawns | 16bG_004 "There's one!" (+004b "Lock and load!"), 25G_002 "Die, you monkey freaks!" | 10 s category; once per wave |
| Explosion | a canister detonates | 25G_004 "Boom!" | 15 s |
| Threat | player damaged by an enemy behind them / damaged | 16bG_002 "Behind you!" (behind only) / 25G_003 "Watch out!" | 30 s each |
| **One-shot** | first yard kill | 16G_003 "I dont know what those things are, but I hate 'em." | once |
| **One-shot** | drainage cleared (last kill) | 21G_007 "Woohoo!" + 21G_007b "Man, I hope I never get YOU angry." | once (plays before `dark`'s 19G) |

Cut from barks: 24G_002 (a duplicate "Behind you!") and 21G_004 "Over there!" (points at nothing the player can see from a camera, R7).

Fallback, if the director can only do timer barks: use only lines that are true at any moment of a fight: 25G_002 "Die, you monkey freaks!", 16bG_004 + 004b "There's one! / Lock and load!", 21G_002 "Kick ass!", 16bG_003 "Eat that, space monkey!".
- Timing: global gap 20-30 s, shuffle bag, per-file minimum 60 s.
- Never on a timer: "Behind you!", "Great shot!", "Nailed 'em!", "One more dead alien!", "Boom!".

Must never be barks (one-shot story): 16G_002, 18G_002, 19G_002, 20G_002, 98_002, 99_*, and every 15G, 17G and 23G node.

## EAR list (a human listens in game before deciding)

1. **06_002-06_005**: confirm the speakers (Aida opens, Dalton "Yes, mother.") and that it sounds like radio from orbit, so "come down there" reads.
2. **15G_002** "...get this thing working.": opens mid-sentence. Does it sound like Miller fumbling with the camera, or like a broken file? Does the camera-speaker filter sound right outdoors at the gate (R27)?
3. **20G_002 trim**: is there a clean breath between "I thought I'd lost you." and "Next up is the drainage room."?
4. **99_003-99_005**: confirm it is Dalton, shouting, and that the Delay 1.5 / 2.0 spacing after "Be right out!" plays as a reaction.
5. **15_001-15_007 + 15_011-15_015**: do the screams and the computer voice read as Miller dying in the generator, heard from the power plant ~2000 UU from the shaft? Is the computer voice distinct from Miller's?
6. **16_002-16_008 moved to after the power fight**: does the urgent "Pull out!" / "Negative!" still land a minute after the death, or does it now sound late? If it sounds late, keep it on arrival before the wave and push the wave behind it instead (edit 17 already clears the arrival talk).
7. **13_002/13_003 after the field fight**: does Dalton's wry delivery fit after the kill rather than at the sighting?
8. **19G_002 at `dark`**: does "easy ride from here on in" still read as tempting fate once the Skaarj shows up ~40 s later?
9. **17_004-17_006 / 17_008-17_010** (if used): is the computer voice usable on its own, without the original's terminal?
10. **XX_001-XX_006** at the pad: the cutscene mix outdoors after a 150 s fight, and whether "Semper Fi" lands as a sore-point jab or a flat sign-off.
11. **Bark set**: with no camera in sight, do Miller's filtered barks still sound like "through the camera"? This is the reason for the camera props in edits 3, 6 and 8.
12. **10_003** "blood is thicker than water": a visual check too. Does the basin water look bloody?

## Mechanical caveat for the playlist tool

Several NextNode values are written in lower case: `Sanctuary_22g_003`, `Sanctuary_16bg_003b`, `Sanctuary_21g_007b`. playlist.py did not follow them; for 22G it lists only 22G_002. UE2 names are case-insensitive, so the game probably plays them. Make playlist.py and dialogue_check.py match NextNode case-insensitively. This doesn't change edit 10, which cuts 22G either way.
