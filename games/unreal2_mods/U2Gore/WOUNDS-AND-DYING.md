# Wounds and dying: Soldier of Fortune and GTA IV in Unreal II (and Advent)

What the two games did, what we have, and what U2Gore's new `GoreDying` does. Started
2026-10-07. Game details are from memory, not checked against sources: treat them as
"how it played", not as documentation.

## The rule: dying, not a second life

Most of this happens when the enemy's health is already zero. A dying enemy is out of the
fight the moment it drops: its AI is gone, it can't shoot, and it can't be "revived" by the
player missing it. It only changes what a death looks like, so the game's balance stays as it
is. The few effects that would change fights (limping, disarming on a hit that doesn't kill)
are separate switches, off by default.

## What the games did

**Soldier of Fortune (Raven, 2000) and SoF II (2002): the GHOUL system**
- The body was split into zones: 26 in SoF, 36 in SoF II. Each zone had its own wound look and
  its own reaction.
- Reactions by zone:
  - a leg or knee hit dropped them to a knee or made them limp;
  - a groin hit doubled them over;
  - an arm hit dropped the gun (disarming);
  - a neck hit made them clutch their throat.
- Dismemberment: limbs and heads came off with layered models underneath. A shotgun up close
  took part of the head off without removing it entirely.
- Stumps and neck wounds kept pumping blood for seconds.
- Wounded enemies sometimes crawled away or writhed on the floor.
- Corpses kept taking damage: more wounds, more parts off.

**GTA IV (Rockstar, 2008): Euphoria (NaturalMotion)**
- No canned death animations: the body is a physics ragdoll with simulated muscles, trying to
  do something (stay standing, reach for a wall, protect the head).
- The wounded on the ground:
  - hold their hand on the bleeding spot (the arm reaches for where the bullet went in);
  - writhe and roll;
  - try to crawl;
  - die some seconds later.
- Shot while standing, they stumble and grab railings and cars.
- That procedural reach-for-the-wound is the part to borrow; the full Euphoria simulation isn't
  possible in a 2003 engine.

## What we already have

| Mechanic | Advent (AdventMod) | Unreal II (U2Gore) |
|---|---|---|
| Blood sprays, drips, pools | ModGore | GoreManager |
| Blood on bodies | ModBloodCoat | GoreCoat, GoreBodyDecal |
| Bleeding trails from the wounded | yes | yes (bBleedTrail) |
| Screen blood | ModScreenBlood | bScreenBlood |
| Heads and limbs off, stumps | ModSever, ModStump | no |
| Shooting corpses to sever more | ModSever (SeverHits) | no |
| Flinch toward the hit, stagger | ModReact (bone rotation) | no |
| Gibs | ModGib | the game's own |
| Breakable armour/helmet | ModArmor (parked, off) | no |
| **Hit zones** | by bone (ModSever) | **new: GoreDying.ZoneOf** |
| **Dying phase** | no | **new: GoreDying** |
| **Pumping wounds** | single spurt at a cut | **new: GoreFountain** |
| **Limp on a leg hit** | no | **new: bLimp (off)** |

## The engine's limits

**Unreal II: script can't pose bones.** U2TestHub's `hub bend` test showed
`MeshNodeSetRotation` is ignored in every space on Legend's Golem meshes (U2Pilot
`bone_bend.txt`). Reading bone positions works (`MeshNodeGetTranslation`, used by the capsule
shadows). So in U2:
- **Zones work:** the hit is placed on the nearest named bone.
- **Clutching the wound can't be procedural.** An arm can't be bent toward the wound; only the
  game's own animation clips can move the body.
- **Clips can be driven:** turning off the animation agent's channel and calling
  `PlayAnim`/`LoopAnim` works (U2TestHub's leg-speed tests). That's what the dying phase does.
- **Clip names aren't known in advance.** `GoreDying` learns them in play: right after a normal
  death or hit, the channel switches to the clip the game chose. It also logs every mesh's
  agent actions once ("survey"), a list to pick better clips from by hand (`ClipOverrides`).

**Advent: bones can be posed.** `ModReact` already rotates bones with `SetBoneRotation`, and
Advent's Karma has `KAddBoneLifter` (unused by the game, noted in `physics-plan.md`). So Advent
can do the GTA IV part properly:
- **Clutching:** while dying, rotate the shoulder and elbow so the hand ends at the wound (two-bone IK by
  the law of cosines, the same maths as the planned foot IK);
- **writhing:** bone lifters on the spine and head of a lying ragdoll pull it up and let it fall back.

That belongs in AdventMod (its own chat); this file is the plan for both.

## GoreDying (U2Gore), what it does

1. **Zones.** Every hit is placed on the nearest named bone (prefixes `Merc `, `Bip01 `,
   `Marine `). Zones are head, neck, chest, belly, groin, arm and leg. Meshes without those bones
   use the height in the collision cylinder.
2. **Dying.** A killing blow can start a dying phase instead of a death, when all of these hold:
   - it isn't to the head;
   - it isn't an overkill (more than 120 damage);
   - the victim bleeds;
   - its kind's death clip is known;
   - it is within 2500 units of the player;
   - fewer than 3 are dying already;
   - it passes a 60% chance.

   Then:
   - its AI is removed (it stands still, as U2TestHub's display dummies do);
   - the death clip plays at 0.6 speed, so it sinks down and holds the lying pose;
   - its hit clip plays now and then, blended over the upper body, as twitches;
   - a belly or leg wound drags it along the floor at 10 units a second for 4 seconds;
   - after 4 to 9 seconds, or at once when hit again, it dies the game's own way.
3. **Fountains.** A neck wound pumps blood every heartbeat (about 0.55 s), each beat a little
   weaker, each squirt leaving a fresh splat ahead of the body. A chest wound gets a weaker one.
   They also start on enemies that die outright from a neck hit.
4. **Limp** (off): a leg hit that doesn't kill slows the victim to 60% for 5 seconds.

The first enemy of each kind in a level always dies the stock way (that's where the clips are
learned), unless `ClipOverrides` names them.

### Settings (U2Gore.ini, `[U2Gore.GoreDying]`, or `set GoreDying ...`)

| Key | Default | |
|---|---|---|
| `bDying` | True | the dying phase |
| `DyingChance` | 0.6 | share of eligible deaths |
| `MinDyingTime` / `MaxDyingTime` | 4 / 9 | seconds |
| `MaxDying` | 3 | at once |
| `OverkillDamage` | 120 | a bigger killing hit kills outright |
| `FallRate` | 0.6 | speed of the death clip for the fall |
| `TwitchRate`, `TwitchBlend`, `TwitchBone` | 0.45, 0.4, `Merc Spine1` | twitches over the upper body |
| `bCrawl`, `CrawlSpeed`, `CrawlTime` | True, 10, 4 | belly and leg wounds |
| `bFountains` | True | |
| `FountainTemplate` / `GreenTemplate` | "" / `Blood.ParticleSalamander6` | particle stream on the wound (red unknown yet) |
| `bLimp`, `LimpScale`, `LimpTime` | False, 0.6, 5 | |
| `ClipOverrides` | none | `MeshName=DeathClip,HitClip` |
| `bLog` | False | a line per hit zone and death |

Test: `python u2pilot.py scripts/gore_dying.txt` (tools/python/U2Pilot). `set GoreDying
ShootZone N` gives the nearest enemy a killing hit in zone N (0 head, 1 neck, 2 chest, 3 belly,
4 groin, 5 arm, 6 leg).

## What can go wrong (not compiled or run yet)

- **Removing the AI kills the pawn.** UT2004's controller kills its pawn when destroyed. U2's
  didn't for U2TestHub's dummies, but if it does here the log says "died when its AI was
  removed" and the death goes through normally.
- **No usable death clip.** If U2 ragdolls bodies on death instead of playing a clip, nothing is
  learned ("channel 0 still ..." lines). The survey's action list is then the way to pick clips
  by hand.
- **Twitches.** `AnimBlendParams` over a held death pose is untested. If it looks wrong, set
  `TwitchBlend 0`.
- **Crawling** moves the whole standing-size collision cylinder, so it stops at the first
  obstacle.
- **The finishing death** uses `TakeDamage`, then `Died` with four parameters (the signature
  U2Seven uses).

## Next, in order of payoff

1. **Disarm on death, visible:** the weapon falls from the hand when the dying phase starts.
   This needs the U2 weapon's pickup class and how U2 drops weapons on death (it may already).
2. **Hit reactions by zone while alive,** from the survey's clip list (a leg hit plays a stumble,
   an arm hit drops the aim), only if U2 has such clips.
3. **Advent:**
   - clutching the wound by two-bone IK (the arm reaches to the wound bone while dying);
   - writhing by `KAddBoneLifter`;
   - a lasting neck and stump fountain (GoreFountain's beat on top of ModSever's spurt).
4. **Partial head damage (SoF's shotgun):** in Advent only, a head gib piece off and a stump cap
   at the jaw; U2 has no severing.
5. **Disarm on a hit that doesn't kill** (SoF), as an option. It changes fights, so off by default.

## Sources to check (not verified here)

- Raven's GHOUL: talks and interviews from 2000 to 2002 about "gore zones" in SoF and SoF II.
- NaturalMotion Euphoria: GDC talks by Torsten Reil (around 2007 to 2009), and GTA IV and Red
  Dead Redemption breakdowns.
- Advent's `research/unreal-games-gore-fx-survey.md` and `research/physics-plan.md` for what
  UE2 games and our Karma setup can do.
