# The user's marks as requirements for the new Avalon (2026-10-08, user: "keep working on the new level, but keep in mind the marks i made")

Every in-game mark on the old TutA is a lesson the new map must pass. Check each line at the greybox and final
play-tests (Phase C). Source rows: marks/QUEUE.md (pictures there).

## Keep (the user liked it)
- **The peak frame:** dark frame -> grated catwalk -> lone silhouette (Hawkins) at dusk, rain (memory: design-taste-avalon-peak-frame).
- **Parallax clouds** "look great" (Q52), "clouds are nice" (Q67): keep the system.
- **Oil rigs on the horizon** "sound nice" (Q70); horizon structures wanted twice (Q45/Q48). Put them INSIDE the level's
  visible range (the old ones were past the edge and never showed).
- **The ambient + FLUSH deck light** "looks nice" (Q61): build on it, but keep more contrast between light and dark.

## Must not happen again
- **Darkness:** the tower interior, deck and command room read too dark (Q5, Q47, Q49, Q80); the characters in the intro
  cine are darker than the room (Q71: set the zone AmbientVector too). The overhang may be dark, the horizon bright (writer F).
- **Rain inside** (Q5, Q50): NoRain boxes / roofs over every interior from day one.
- **Floating things:** rocks, building bases, masts (Q2, Q26, Q65, Q66). Every prop sits on graded ground or goes.
- **A square island** (Q3): the sea and terrain edge must never read as a square.
- **Repeating texture on flattened ground** (Q6, Q25, Q30): keep relief, use the stochastic shader, no big flat pads.
- **Fog hiding the island** (Q60): the storm fog starts far enough out that the town and its landmarks stay readable.
- **Smoke hidden by water / ball-shaped smoke** (Q59, Q84): keep the zwrite depth pass rule.
- **Cranes that look like fishing poles, cranes on pyramids** (Q26, Q83): no cranes on the pyramid towers.
- **Billboard-looking imposters** (Q1): 3D geometry for anything closer than the horizon.
- **Untextured flat-palette buildings at distance** (Q81): the world-space detail rule (CC0, low-res, stochastic).
- **Railings that don't rim the walkable edge** (Q9): rails follow the real edge of every walkway.
- **Things that make no sense:** the weird banner and the vehicle (Q7), the GM crate in the room (Q46).

## Asked for (design input)
- **A believable ~300-person town** (Q74): it must read as a big town; the rich live high, the poor do not live on the peak.
- **The mountain living remake** (Q68, research: Mountain living/report.md) and **a mountain from our refs** (Q63).
- **Roads from geometry splines** to every house (Q64; Cities Skylines report, Q73).
- **Rework the deck view** west onto the shanty mountain (Q51) with the creative team.
- **Rewrite the intro cinematic** with the director and writer (Q56); console open must pause it (Q72, fixed by key tracking).
- **Better terrain tech** (Q62).
- **New Game goes straight into the new Avalon** (Q86); the tutorial is folded into the route (Q87).
- **The PyramidTower** (Aztec dystopian, Q83) is the summit Liandri tower.

## Engine items that stay separate jobs (not map work)
Q54 vignette, Q57/Q82 stale texture hash (fixed), Q75/Q76 first-person body, Q77 sketch state (fixed), Q79 hotswap,
Q89 the hang on the Atlantis travel.
