# DOOM (2016) and DOOM Eternal: enemy AI and combat design

Researched 2026-10-08. Source quality key: **[P]** = primary (id developers in talks/interviews), **[S]** = secondary analysis (AI and Games / journalists / indie devlog summarising a talk), **[S-fan]** = fan wiki / review. The two key primary talks (GDC 2017 Campbell, GDC 2018 Loudy & Campbell) could NOT be read directly (GDC Vault login / video only); most mechanical detail below reaches us via Tommy Thompson's written summary of those talks. No source code or licence exists for any of this (id Tech 6/7 AI is closed); everything here is design knowledge only.

Primary talks to watch if anyone has time (video, not transcribed here):
- Jake Campbell (id), "Bringing Hell to Life: AI and Full Body Animation in DOOM", GDC 2017 — [CGPress](https://cgpress.org/archives/bringing-hell-to-life-ai-and-full-body-animation-in-doom.html), [3DVF](https://3dvf.com/actualite-22540-retour-sur-ia-et-animation-doom-id-software-html/)
- Kurt Loudy & Jake Campbell (id), "Embracing Push Forward Combat in DOOM", GDC 2018 — [GDC Vault 1024940](https://gdcvault.com/play/1024940/Embracing-Push-Forward-Combat-in); a GDC talk on Doom combat is on YouTube at youtu.be/2KQNpQD8Ayo (linked by [this devlog](https://serfofcinder.itch.io/archetype-portal-to-hell/devlog/738495/enemy-ai-tech-talk); title not confirmed)
- Hugo Martin with Noclip, "Designing Demons" (DOOM Eternal) — [Bethesda Slayers Club](https://slayersclub.bethesda.net/en-AU/article/designing-demons-noclip) (page itself has no detail; the video does)

## Attack token / ticket systems

### Takeaway
DOOM 2016 limits simultaneous attacks with per-attack-type token pools (melee, ranged, charged, etc.); a demon must hold a token to attack and releases it after; pool size scales with difficulty; tokens can be stolen, notably by an on-screen demon from an off-screen one so the player never sees idle enemies in front of them. Nothing public describes how Eternal's token system differs.

### Cited Findings
- Each attack type (melee, ranged, charged, others) has its own limited token pool; a demon requests a token before attacking and releases it afterwards [S, summarising Loudy & Campbell GDC 2018] — [Game Developer / AI and Games, "Cyber Demons: The AI of DOOM (2016)"](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-) (also on [80.lv](https://80.lv/articles/cyber-demons-the-ai-of-doom))
- Token counts vary with difficulty, capping how many demons attack at once — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Demons can steal tokens from each other when a demon in front of the player needs one, so nearby demons don't stand idle — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- An indie dev summarising a GDC Doom combat talk: the victim of a steal must cancel its attack; the main use is an on-screen enemy stealing from an off-screen one so the player rarely notices; with no tokens left an enemy waits; bigger pools at higher difficulty make enemies "seem more aggressive" [S] — [serfofcinder devlog](https://serfofcinder.itch.io/archetype-portal-to-hell/devlog/738495/enemy-ai-tech-talk)
- Same devlog's own implementation (not id's): separate melee and ranged pools sized 1/2/3 by an "Enemy Aggression" setting; a behaviour-tree decorator `ExecuteWithAttackTokenNode(pool, acquireTimeout, child)` returns Running while waiting, Fails on timeout, runs the child once it holds a token, and releases the token in Reset whether the child succeeded or failed; it wraps the whole sequence (find target, path, wait, attack, wait for attack duration). No stealing implemented. — [serfofcinder devlog](https://serfofcinder.itch.io/archetype-portal-to-hell/devlog/738495/enemy-ai-tech-talk)
- During a glory kill the player is invulnerable and AI may not *start* a new attack until the current one finishes (a token-like global gate) — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Ranged accuracy uses a weighted distribution: demons miss more when the player moves fast, hit more when the player is slow; higher difficulties compensate more for player movement. Demons will not shoot explosive barrels near the player. — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)

### Inferences
- Priority by distance/visibility is only confirmed in one form: "visible/in front beats off-screen" via stealing. Any finer scoring (distance, archetype weight) is not documented; a reasonable reimplementation is: score = visible-to-player + closeness + archetype priority, steal only from a lower-scoring holder that hasn't begun its attack windup.
- The accuracy rule (miss more when the player moves fast) is itself part of the "push forward" design — it rewards movement more than the token cap does, and is trivially cheap in UE2 (scale aim error by player velocity in the projectile/hitscan aim function).
- In Advent Rising / UE2 terms: a token manager can live on the GameInfo or a SquadAI-like singleton (`RequestToken(Controller C, name Pool)`, `ReleaseToken`), checked before the Bot's attack state fires, released on attack end, death, pain-interrupt or stagger.

### Gaps
- No source on how tokens are granted in Eternal or whether Eternal changed counts/pools/stealing. No numbers for per-difficulty pool sizes. No confirmation whether tokens are per-player or per-target (single-player so moot). Exact title of the YouTube talk the devlog cites not verified.

## Push-forward combat: drops, glory kills, positioning, roles

### Takeaway
"Push forward combat" replaces regenerating health, reloading and cover with demons as walking health/ammo packs: the player must close distance to resupply (glory kill = health, chainsaw = ammo; Eternal adds flame belch = armor, glory kill also charges blood punch). Enemies are deliberately positioned and tuned ("chess pieces") to dislodge the player from ledges, stop kiting, and force target priority.

### Cited Findings
- GDC 2018 talk premise: push forward combat "stares down genre conventions like regenerating health, reload and cover" and puts the onus on the player to take what they need from adversaries [P, session abstract] — [GDC Vault](https://gdcvault.com/play/1024940/Embracing-Push-Forward-Combat-in)
- Speakers' framing: the Marine's forward momentum means no stopping to regenerate or hunt resources; AI are "walking health & ammo packs", with a bonus for glory kills [P, via search summary of GDC Q&A; page now 404] — [GDC speaker Q&A](https://gdconf.com/news/speaker-qa-kurt-loudy-jake-campbell-break-combat-philosophy-doom)
- Four pillars: movement speed, demon individuality, weapon distinctiveness, preserving player power; reloading cut; double jump added to close distance; arenas medium-large, asymmetric, vertical — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- 2016: glory kills drop health, bigger demons drop more; chainsaw kills drop ammo — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Eternal loop: chainsaw = ammo, glory kill = health, flame belch (set on fire) = armor, more glory kills = blood punch; Martin: "The solution to all the problems is to be aggressive"; Stratton via Martin: "the guns are the tool and the AI is the problem"; Arachnotron moves in to finish players who hide and peek; Carcass shields spawn near the player, blocking paths/glory kills [P interviews, by Kris Graft] — [Game Developer, "The aggressive resource management of DOOM Eternal"](https://gamedeveloper.com/design/the-aggressive-resource-management-of-i-doom-eternal-i-)
- Eternal: ammo exists in arenas but weapons hold less, so chainsaw/glory kill resupply is relied on; fodder (zombies, imps) can be deliberately left alive as resupply — [Shacknews, "Hell Razer: The Making of DOOM Eternal" p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- 2016 "exposed cover": id inverted Rage's cover system into positions near cover that maximise the demon's visibility to the player; ranged demons (imp, cacodemon, mancubus) keep their distance to keep attacking — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Martin (Eternal): enemies used "as chess pieces" to move the player around, get them off ledges and stop kiting; levels avoid corners where demons can't reach the player; "the AI does a lot of that work"; also "We don't want you constantly going point blank" so some ranged play is allowed for variety [P, roundtable] — [Fandom, "Doubling Down on Doom Eternal"](https://www.fandom.com/articles/doom-eternal-marty-stratton-hugo-martin)
- Martin: "Many AI have now been tuned to no longer allow you to rush up to them" — players must "create openings" for the super shotgun; Mancubus ground-pounds at close range; some heavies dodge slow rockets; projectile-dodgers are countered by the ballista; "If you're not prioritizing anything on the battlefield and just killing whatever's in front of you, that sucks" [P] — [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- Roles: 2016 has 16 AI archetypes each with unique behaviour/animations (pinky charges to ram, imps keep distance and throw fireballs, zombie fodder weak to shotgun); faction rules track accidental/intentional cross-faction damage to trigger infighting (imps lose to mancubus/barons; possessed UAC disliked by all demons) — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Eternal roles as described by Martin/Stratton: weaker enemies (zombies, imps) die to frag grenades; "heavies" (Mancubus, Arachnotron) are staggered by frags; blood punch staggers bruisers; Archvile is a priority target that spawns waves (does not resurrect in Eternal), with teleport + shield wall — [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- Eternal design response: new player tools (flamethrower, meathook) made fights too easy, so demons were made "smarter and more ruthless" [S, preview coverage] — [PCGamesN demons video](https://www.pcgamesn.com/doom-eternal/demons-video)

### Inferences
- The fodder / heavy / super-heavy vocabulary is the community's and the game's codex shorthand; I found no primary source using the exact words "fodder/heavy/super heavy" in a talk (Shacknews paraphrase uses "heavies"). Roles shape behaviour by: fodder = resupply and token fillers, weak to everything; heavies = need a specific answer (weak point / stagger tool) and anti-rush moves; super heavies/priority targets (Archvile, Baron, Marauder) = change the whole arena's priority.
- Cheapest UE2 wins: (1) health drop on melee/finisher kills and ammo drop on a special kill, (2) remove/limit regen, (3) "exposed cover" = pick positions with line-of-sight to the player rather than hidden from it (invert the usual cover query), (4) a close-range anti-camping move on heavies.

### Gaps
- No primary detail on how demons compute flanking or "keep pressure" movement; no numbers on drop amounts.

## Stagger, glory kills, weak points, destructible demons, telegraphs

### Takeaway
2016 used a sustained-DPS pain system escalating twitch -> falter/pushback -> stagger (glory-killable, signalled by a flash). Eternal added "destructible demons": progressive visible damage, plus specific weak points that both take bonus damage and remove an attack (Arachnotron turret, Mancubus arm cannons, Revenant shoulder rockets), forcing the AI to switch behaviour.

### Cited Findings
- Pain reactions driven by sustained DPS; escalation: mild twitch (affects AI aim) -> falter and pushback (interrupt behaviour) -> stagger (enables glory kill); weapon-specific: imps stop moving under assault rifle fire, zombies stagger fast to shotguns; a minigun perpetual-falter bug on the Cacodemon was removed pre-launch [S, citing Campbell GDC 2017] — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- Destructible demons (Eternal, revealed QuakeCon 2018): damage shown progressively based on how and where you hit; id says it accounts for distance, angle and damage value of attacks; certain weak spots take extra damage and disable attacks; Mancubus and Hell Knight can survive armless and harmless; 2016 had a prototype with limbs coming off only on lethal damage [S-fan wiki, summarising id statements] — [DoomWiki, Destructible demons](https://doomwiki.org/wiki/Destructible_demons); [DSOGaming tech details](https://www.dsogaming.com/news/doom-eternal-tech-details-id-tech-7-can-display-10-times-higher-geometric-detail-demons-will-be-destructible/)
- Arachnotron turret destroyed -> loses main attack and charges in to melee; destroying a Mancubus flamethrower makes it explode and staggers it; Cacodemon swallows a grenade then flashes to signal glory kill; pinky tail weak spot after dodging its charge — [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- Preview: targeting body parts inhibits attacks and "the enemy AI is forced to change their strategy" [S] — via search summary of [Gaming Trend E3 preview](https://gamingtrend.com/feature/previews/back-to-hell-doom-eternal-e3-preview)
- Glory kill: player invulnerable during it — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)

### Inferences
- UE2 mapping: accumulate damage in a decaying per-pawn bucket; thresholds trigger hit-flinch (add aim error), falter (abort current attack, release token, short knockback), stagger (glow/flash, open finisher for N seconds, then recover). Weak points = named bone/region hit test in TakeDamage -> set a flag that removes an attack from the Bot's attack set and swaps to a fallback behaviour (melee charge). Cheap. Visual limb loss needs mesh/skin swaps — more expensive in UE2.
- Telegraphs: the stagger flash and the "swallow then flash" are explicit readable states; the 2016 animation system (below) also makes windups readable because every attack is a start/middle/end animation chain.

### Gaps
- Exact damage thresholds, decay rates, stagger window length unknown.

## Encounter scripting / director, waves, intensity

### Takeaway
Very little public, primary detail. Known: arenas are hand-built, asymmetric and vertical; Eternal puts powerful enemies in earlier than 2016's gradual ramp; Archviles are in-arena spawners; designers deliberately choose which types spawn to vary range. No source describes a "heat"/intensity director.

### Cited Findings
- Eternal throws powerful enemies at the player earlier, unlike 2016's gradual ramp; later fights use larger groups where weak-point shots become "practically mandatory" — [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- Martin on deliberate spawn choices (e.g. imps to allow some ranged play) and level layouts that remove safe corners — [Fandom roundtable](https://www.fandom.com/articles/doom-eternal-marty-stratton-hugo-martin)
- Archvile spawns waves to drain player resources — [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4)
- Eternal also tried to make the spaces between arenas as engaging as the arenas [S, preview, speaker not named] — via search summary of [Gaming Trend](https://gamingtrend.com/back-to-hell-doom-eternal-e3-preview/)
- AI and Games' DOOM 2016 article explicitly does not cover spawning/encounters — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)

### Inferences
- Observed gameplay (not sourced here) suggests scripted wave triggers on kill counts with portal spawns; treat that as unverified. For UE2, a simple arena script (wave N spawns when alive-count < K or a priority enemy dies) plus "spawn near but out of the player's view" is the cheap reproduction.

### Gaps
- No primary source on wave logic, spawn point selection, or any intensity/heat director in either game. Not found in GDC listings; no Eternal-specific AI GDC talk found.

## Perception, movement, navigation, animation-driven behaviour

### Takeaway
2016's AI = hierarchical FSMs (from Rage / id Tech 5) authored in a custom editor, driving "AnimWeb", an animation state graph with start/middle/end chains, runtime-warped traversal animations (one imp jump animation stretched for short or long jumps) and "focus tracking" IK so demons always face the player. Perception is not documented.

### Cited Findings
- Decision layer: hierarchical FSMs grouping states into clusters with entry/exit transitions (move into position, attack ranged, attack close); custom editor reads C++ state headers; graph visualisation, but harder debugging; lineage id Tech 5 / Rage (dev from 2005) — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-)
- AnimWeb: FSM where each state is an animation, transitions blend; paths trigger start/middle/end animations for an AI state; blend points precomputed from skeletal analysis; runtime checks adjust animations to fit movement arcs — same source
- Traversal: imps jump short or long with one animation tweaked at runtime; Hell Knight lunges do environment checks to avoid clipping — same source
- Focus Tracking: IK rotation for head, chest and hips keeps demons facing the player — same source
- Perception: none described beyond Rage's cover system checking visibility to the player — same source
- Eternal adds player wall-climbing/traversal (player side) [S] — via search summary of [Bloody Disgusting hands-on](https://bloody-disgusting.com/video-games/3575726/hands-preview-doom-eternal-offers-plenty-relentless-demon-slaying-buckets-gore/)

### Inferences
- In UE2, navigation is the PathNode/ReachSpec network (no navmesh); jump traversal can be done with JumpSpots/special reach specs plus one jump anim scaled in rate by distance. Focus tracking equivalent: bone controllers (`SetBoneDirection`/`SetBoneRotation`) on head/spine toward the enemy — but memory notes say script bone posing is limited in this engine family, so test first.
- Perception can be minimal: DOOM-style demons are effectively always aware once the arena starts.

### Gaps
- Nothing primary on navmesh or how Eternal's AI navigation/traversal works; no Eternal AI tech talk found.

## Cheap vs expensive to emulate (UE2 / Advent Rising)

### Takeaway
Most of DOOM's feel comes from cheap rules (token cap, movement-scaled accuracy, resupply-on-kill, DPS stagger thresholds, weak-point attack removal, exposed-not-hidden positioning). The expensive parts are the animation systems (AnimWeb blending, runtime-warped traversals, full-body IK) and destructible visuals.

### Cited Findings
- All mechanics enumerated above — [Game Developer / AI and Games](https://www.gamedeveloper.com/design/cyber-demons-the-ai-of-doom-2016-); [Shacknews p4](https://www.shacknews.com/article/116635/hell-razer-the-making-of-doom-eternal?page=4); [DoomWiki](https://doomwiki.org/wiki/Destructible_demons)

### Inferences
- Cheap (script only): token pools with steal-from-offscreen; aim error scaled by player speed; no shots at barrels near the player; health/ammo/armor drops by kill type; finisher with invulnerability + global "no new attacks" gate; DPS pain buckets -> falter/stagger with a flash; weak-point hit regions disabling attacks; infighting via damage-instigator faction rules; "exposed" positioning (choose PathNodes with LOS to player at preferred range per archetype); anti-camping close-range attack on heavies.
- Medium: per-archetype preferred-range movement, Archvile-like spawner enemy, wave scripting.
- Expensive: AnimWeb-quality start/middle/end blending, runtime-warped jumps/lunges with environment checks, full-body focus IK, progressive damage meshes.

### Gaps
- No licensed code to reuse; id Tech AI is proprietary.
