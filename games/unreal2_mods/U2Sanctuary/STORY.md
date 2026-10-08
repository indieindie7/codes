# Sanctuary: what the game says the place is, and what happens there

Read from the game's own files on 2026-10-08. The full extracted dialogue (not committed: it is the game's script) is in `Documents\U2_research\sanctuary\dialogue\` (`sanctuary_dialogue_raw.md`, `sanctuary_context_raw.md`).
- `Dialog\Atlantis0\*.dlg`: the briefing aboard the Atlantis.
- `Dialog\PA_Sanctuary`, `M08A`, `M08B`, `PD_Sanctuary`: the mission.
- `System\M08a1.int`, `M08a2.int`, `M08b.int`, `PA_Sanctuary.int`: the objectives and on-screen text.
- `Dialog\Atlantis1`: the next briefing, which looks back on it.

The game's internal names (M08A1, M08A2, M08B) hide the order. **Sanctuary is the first real mission of Unreal II**, straight after the Avalon prologue (TutA/TutB).

## The place

- **Sanctuary** is Elara V, the fifth planet of the Elara system. Aida's briefing describes it as an Earth-like world under dense jungle, uninhabited except for a **Liandri mining operation**. The on-screen captions are `Elara V, "Sanctuary"` and `Liandri Mining Facility`. The station's call sign is **Liandri Station Lima Six**.
- **The complex has two parts:**
  - the **ore processing unit**, which grinds rock and extracts precious minerals (the "collection plant": runoff basin, drainage room, sewers);
  - the **Power Plant**, whose huge generator runs the rock crushers. It stands a few hundred yards away across ground cleared of jungle.
  - The TCA has no blueprints of the interior.
- **The level titles** are "Elara V: Sanctuary" (M08A1) and "TheSkaarjEncounter" (M08A2's internal title).

## Who is there

- **The Liandri staff:** scientists, workmen and technicians. On the security cameras they are all dead. One survivor remains: **Danny Miller, level-one technician**, barricaded in a security office in the generator building.
- **The Izarians**, the "creatures" and "space monkeys" to Miller. They are blue aliens, and they overran the station.
- **The Skaarj** stand behind them. Aida reads a Skaarj as "checking up on his Izarian grunts", and Miller decrypts a Skaarj intercept: "they want that thing pretty bad".
- **Dalton** is the TCA marshal, the Colonial Authority's "quietest patrol". **Aida** is in his ear, **Ne'Ban** flies the ship, and **Isaak** supplies the guns.
- **TCA Marines** arrive at the end by speedship to collect the artifact.

## What happened

The miners pulled an alien relic up from the mine: "really old, like a relic", and they broke a drill bit on it. The creatures showed up right after. The station sent a Mayday: overrun by hostile aliens, multiple casualties, nobody knows what they are or where they came from.

## The mission, beat by beat

1. **Briefing:** a distress call from the Elara system. Aida's version of the mission: get in, save whoever you can, get out. Aida's last word to Dalton is "search and rescue. No rough stuff.", and he answers "Yes, mother."
2. **M08A1, the landing:**
   - The intro cutscene shows the colonists dying: an Izarian stabbing, a "blood bath", an Izarian looking up at the arriving dropship.
   - Inside, a scientist cries for help; another shouts "Go back!"
   - Miller hacks into the security network. It's one-way: he sees and talks, but can't hear.
   - He routes Dalton through the collection plant and opens the hatches to the flooded **runoff basin**: "a short swim".
   - Izarians break the cameras. Miller cheers Dalton on through the fights ("space monkey").
3. **M08A2, the plant:**
   - Next comes the **drainage room**, "chock-full of those creatures, but there's no other way".
   - Then a security door, and a stretch where no cameras work ("be careful").
   - Then the first Skaarj ("TheSkaarjEncounter").
   - Miller warns that a lot of the stuff in the plant is unstable: explosive barrels and canisters.
4. **M08B, the generator:**
   - He sees Dalton on camera and runs out to meet him, against orders: "No! It's not safe."
   - He is caught. A Skaarj takes him into the generator (an emergency shutdown, "obstruction detected"), and he dies. In Dalton's words: "That kid just died to keep the artifact from the Skaarj."
   - Aida tells him to pull out, since fighting Skaarj isn't in the mission profile. Dalton refuses and goes down anyway.
   - The new objectives:
     - find the generator control room;
     - reactivate the generator (the terminal reports an "alien lifeform detected in generator");
     - retrieve the artifact from the bottom of the generator;
     - get out.
   - Dalton brings the artifact up from the generator ("I got the artifact...whatever it is"). Aida calls HQ, and a speedship of Marines is coming for it (19_003 is Aida, not Miller).
5. **The end:**
   - The Marines take the artifact: "Doesn't look like much." "Must be important to someone, though."
   - The marine's parting line, "You shoulda been a Marine", hits Dalton's sore point: Hawkins has just refused his reinstatement again.
6. **Afterwards:** the next briefing (Hell, an Axon research station) mentions researchers working on "an artifact that sounds a lot like the one we recovered from Sanctuary". Sanctuary's relic is **the first of the artifacts**, and the whole game's plot starts here.

## The tone

- The humour is gallows humour between Dalton and Aida. At the runoff basin: "blood is thicker than water... well, it's true". About Miller: "Were WE ever that green?"
- The tension: the Authority was sent on a rescue it isn't equipped for, the company dug up something it shouldn't have, the aliens came for it, and the one survivor dies trying to hand it over.
- This is the keystone the user set for the remix (AVALON_BRIEF.md): a backwater forgotten by the centre, a company (Liandri) exploiting it, and the Authority arriving underpowered and too late.

## What this means for the Sanctuary pass

- **The canon look is a jungle world with a raw mining station:** jungle, a cleared field, an ore plant and a generator building. Our earlier `U2Seven/SANCTUARY_REDESIGN.md` (rusted Gothic colony on pylons, red sky, buried alien blocks) is **our own invention**, not the game's. The remix rule is to keep the level's own look, so that brief should stay an alternative, not the target.
- **The gore has a story to serve:**
  - the colonists died where the Izarians caught them, and the blood should show where they ran (the security doors, the camera rooms, toward the generator building);
  - the Izarians are blue (Miller: "blue is definitely not your color"), so the layer's purple for their blood is close enough;
  - Miller's death in the generator is the level's emotional peak, and it deserves the strongest vignette: a trail toward the generator, his blood on the shield.
- **Miller is the level's voice.** He watches through cameras and can't hear Dalton. A camera that turns to follow the player, and dead cameras where he says they are dead, would sell it without new lines.
- **Water:** the runoff basin swim is written into the story ("a short swim"), so the water is canon. That makes the engineer's finding (no AI paths in the water) worth fixing.
- **Unclear:** `M08B.int` has a trigger whose message is "Go to Marsh cutscene", and `Dialog\Swamp\Marsh_02.dlg` has Marines who "dug [the artifact] out of the wreckage" and Dalton "bringing the Atlantis down". It looks like a cut or reworked ending for the artifact pickup, not what ships.
