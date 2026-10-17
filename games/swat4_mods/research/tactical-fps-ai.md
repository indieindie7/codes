# Tactical FPS enemy and squad AI: survey for SwatMinds

Scope: what the best tactical shooters do, in a form we can port to UnrealScript on SWAT 4 (Tyrion core is native; we can wrap actions, change scores, add actions). Breach/cover/officer design lives in `breach-cover-ai.md`; not repeated here. Sources marked (search only) were confirmed from search snippets, not read in full. Technique details marked (recalled) come from my background knowledge of the talk and were not re-verified this session.

## 1. Survey

### F.E.A.R. (Jeff Orkin)
- Tiny FSM (Goto, Animate, UseSmartObject); the planner (GOAP, A* over actions) picks sequences. Goals and actions carry costs, so tuning is by numbers, not scripts.
- Squad behaviours sit on top: a coordinator assigns slots by proximity (search only: squads emerge from grouping, no explicit squad plan). Suppress, flank and advance emerge because the plan re-runs when cover is lost. Dialogue narrates plans (recalled), so the player hears the reasoning.
- https://gdcvault.com/play/1013459/Three-States-and-a-Plan ; paper: https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf

### Killzone (Straatman, van der Sterren, Beij; Guerrilla)
- Position picking: score every candidate point with one weighted evaluation (cover from threats, distance to target, exposure to allies' fire, path danger, spacing from squad) and take the best. Same machinery gives tactical pathing, suppression and indirect fire.
- Search found this for the first Killzone and GDC Europe 2005; a Killzone 2/3 multiplayer-bot chapter ("Hierarchical AI for Multiplayer Bots in Killzone") is in Game AI Pro 360. I did not confirm a K2/K3 waypoint-cover chapter.
- https://www.guerrilla-games.com/media/News/Files/gdce05_killzone_ai.pdf ; https://www.guerrilla-games.com/media/News/Files/VUA07_Verweij_Hierarchically-Layered-MP-Bot_System.pdf

### Halo 2/3 (Damian Isla)
- Behaviour tree as a prioritised list with self-describing behaviours; each behaviour states its own relevance, so the tree is data, not code. Impulses can interrupt or redirect (search only).
- Squad-level reactions (recalled): grunts flee when the leader (elite) dies, panic and then recover; characters share enemy knowledge so one sighting alerts the group. Morale-like state changes which branch wins.
- https://web.cs.wpi.edu/~rich/courses/imgd4000-d10/lectures/halo3.pdf ; original: Gamasutra "GDC 2005 Proceeding: Handling Complexity in the Halo 2 AI" (live link unverified).

### Crysis / Far Cry (Crytek)
- Perception is explicit: separate visual and audio senses, plus "bullet rain" (near misses count as a stimulus). Stimuli raise alertness through staged states (unaware, suspicious, alerted, combat) and the AI then investigates the last known position (partly recalled).
- https://www.cryengine.com/docs/static/engines/cryengine-3/categories/1114113/pages/17829009

### Arma (Bohemia)
- Per-unit sub-skills (courage, aimingAccuracy, aimingShake, spotTime, spotDistance, commanding...) interpolated by difficulty. Courage drives morale: AI fear rises from being suppressed, losing friends and being outnumbered; low-morale units retreat or surrender (surrender via community scripts, suppression-to-courage via mods like TPWCAS; vanilla is weaker).
- https://community.bistudio.com/wiki/CfgAISkill ; https://forums.bohemia.net/forums/topic/231770-release-pog-surrender/

### The Last of Us (Naughty Dog)
- Enemies read real-time level analysis (cover, flank routes, player position), share knowledge, and talk to each other via a dialogue system with individual and collective knowledge (search only). Buddy AI (Ellie) is built to stay out of the way and add value in short bursts.
- GDC Vault "The Last of Us: Human Enemy AI" (McIntosh); Game AI Pro chapters (McIntosh, Dyckhoff). Overview: https://gamedeveloper.com/design/endure-and-survive-the-ai-of-the-last-of-us ; https://naughtydog.com/blog/2014_naughty_dog_gdc_talks_and_the_last_of_us_accolades

### SWAT 4 and Ready or Not (suspect behaviour)
- SWAT 4: lead AI designer John Abercrombie said suspects weigh options: surrender when morale is low, take or threaten a hostage if one is near, or flee the room. Testers found wounding before demanding surrender made arrests too easy, so morale rules were adjusted. Stun effects usually make suspects drop weapons. https://www.gamespot.com/articles/swat-4-updated-impressions/1100-6120098/
- Ready or Not: suspects can fake death, fake surrender then draw, or use hostages as shields; an update added a graded chance to leave surrender and grab a weapon (higher on hard) and Rally/Support/Attack/Retreat squad behaviours. Player complaints: hesitation and fear are gone versus SWAT 4. https://voidinteractive.net/?p=2442 ; https://en.wikipedia.org/wiki/Ready_or_Not_(video_game)
- I found no developer source on SWAT 4 officer AI internals or the Tyrion name.

### The Division / Ghost Recon (role-based enemies)
- Division: named archetypes (rusher, sniper, support/healer, tank, heavy, thrower, leader, controller). Each role forces a different player response, and mixes create readable pressure. Division 2 varies archetypes per faction (a rusher that sneaks along flanks). https://www.gamedeveloper.com/design/enemy-ai-design-in-tom-clancy-s-the-division ; https://news.ubisoft.com/en-us/article/347598/The-Division-2-Making-Enemies-Tougher-and-Friendlies-Smarter
- Ghost Recon: Future Soldier reviews note enemies try to flank, else fall back to better cover (anecdotal). https://www.gamedeveloper.com/design/flanking-and-cover-and-flee-oh-my-

### Suppression and flank systems (Spec Ops: The Line and others)
- I found no primary source for Spec Ops: The Line. Best substitute: Killzone position picking giving suppression and indirect fire as products of the same evaluator (above). Common pattern (recalled): one group pins the target with fire while another takes a flank point scored by low exposure to the target's view.

### Utility AI (Dave Mark)
- Score each option as the product of response curves over inputs (distance, health, fear...), pick the best or sample the top few. Behaviours need no transition tables; adding a consideration changes behaviour smoothly. Sources: GDC AI Summit lectures (Mark and Dill, 2010, 2012) and book *Behavioral Mathematics for Game AI* (2009). I did not find the GDC pages; search GDC Vault for "Improving AI Decision Modeling Through Utility Theory".
- https://en.wikipedia.org/wiki/Utility_system

## 2. Best ideas for SwatMinds

Mod model: fear/anger/stress/nerve per suspect; wrap/rescale stock Attack, Cover, Flee, Regroup scores; new Tyrion actions allowed. Ranked by fun per effort (best first).

1. **Staged surrender with morale triggers (SWAT 4 / Arma courage).** Surrender score = f(fear, nerve, outnumbered, ally down, flashbang/stun, officer shouting). Wounded no longer auto-lowers it (the exploit SWAT 4 designers patched). Hook: scale the stock Surrender/Flee score from a curve over nerve; add "ally went down in sight" and "outnumbered" terms. Effort: low.
2. **Feign surrender then ambush (Ready or Not).** A small subclass of surrendering suspects keeps a hidden weapon and has a delayed, graded chance (time x anger x stress, higher on hard difficulty) to leave the surrender state and fire. Delay it a minute or so for paranoia (player request on DevTrackers, unconfirmed as shipped). Hook: new Tyrion action `FeignSurrender` that wraps Surrender and schedules an `Attack` score spike; officers can be shown a tell (hands slightly low, quick glance). Effort: low-medium.
3. **Leader-death panic and rally (Halo grunts).** When a designated leader (or highest-nerve suspect) dies in view, nerve of nearby suspects drops by a set amount; they flee or surrender. A surviving leader also raises nerve for followers (rally). Hook: Hive event on death, plus Flee/Regroup score modifiers; leader flag on spawn. Effort: low.
4. **Suppression as fear (Arma/TPWCAS, Killzone).** Near-miss bullets and sustained fire raise a per-suspect suppression value that lowers nerve and aim accuracy and pushes score toward Cover/Flee. Hook: weapon hit/near-miss event adds fear; wrap Attack to cut accuracy when suppressed and boost Cover. Effort: medium.
5. **Alertness ladder with search (Crysis).** Unaware, suspicious, alerted, combat. Noise (breach, gunshot, door) raises it; suspects go to the last known position instead of snapping to combat. Hook: change Idle/Patrol so noise triggers an Investigate action; scale Attack by alert level. Effort: medium.
6. **Role tags per suspect (Division).** Assign at spawn: rusher (Attack bonus, ignores cover when angry), holder (Cover bonus, stays off the funnel), flanker (Regroup goes to a side route). Hook: per-role multipliers on stock action scores, set by one Mutator pass over the actor list; mixing roles on a map makes the same room play differently each run. Effort: medium.
7. **Position picking for suspects (Killzone).** A single weighted function for cover choice: low exposure to the entry door, distance to the player, spacing from ally, hostage proximity. Hook: wrap the Cover action's point choice, or override cover-point scores; reuse for ambush spots behind a door. Effort: medium-high.
8. **Utility response curves for everything (Dave Mark).** Implement items 1-7 as small curves over fear/anger/stress/nerve rather than if/else, tuned in one config table. Hook: one scoring helper called from each wrapped action; this is infrastructure that makes 1-7 tunable and cheap to extend. Effort: low-medium; do it first in practice.

## Gaps
Not read in full: all GDC talks and Game AI Pro PDFs (search snippets only); no primary source for Spec Ops: The Line, Ghost Recon role AI, Killzone 2/3 waypoint cover, Crysis search internals, or SWAT 4 officer AI. Next step: fetch gameaipro.com chapters and the GDC Vault slides to verify the recalled items.
