# Black (Criterion, 2006): destruction and impact effects, and what we can borrow

Date: 2026-10-10. Method: web search plus fetch. Headline: no GDC talk, postmortem, Digital Foundry piece, decompilation or modder write-up on Black's destruction tech turned up. The only developer-sourced technical material is one retrospective interview (Burly Bird). Everything else is press describing what the effects looked like. Anything about mechanism beyond "pre-fractured" is INFERRED.

Tags: [S] = sourced (URL), [I] = inferred from what was seen / PS2-era practice.

## 1. Wall / cover destruction

- [S] Destructible objects were pre-fractured, not broken in real time; destructible elements were added wherever possible so the world felt organic (Michael Othen). Engine derived from the Burnout engine, built for effects and speed. https://burlybirdmedia.com/archive/criterionsblackfeature
- [S] Aim was pervasive destruction rather than Red Faction's few controlled spots (Othen, same URL). Press: masonry blasted off walls, letters crushed off signs, doors off hinges, windshields/headlights shattered, tyres blown, ricochets off steel gratings. https://www.gamespot.com/ps2/action/black/preview_6098217.html/
- [S] Inconsistent in practice: some pillars and walls break, other things barely react to an RPG. https://www.honestgamers.com/8205/playstation-2/black/review.html (search snippet only)
- [S] Designer-driven: gravestones timed to crumble when a sniper hits them; invisible "targets" steer enemy fire to destructible scenery; destructible scenery placed behind enemies; buckled concrete on the bridge level makes tilted cover (Bunn/Othen). Burly Bird URL.
- [S] Aftermath persisted: bodies stayed, casings and bullet holes littered the floor. https://www.gamespot.com/ps2/action/black/preview_6098217.html/ ; https://www.empireonline.com/gaming/reviews/black-review-2/ ; https://worthplaying.com/article/2006/3/19/reviews/31897-ps2-review-black/
- [I] Mechanism: each destructible prop/wall chunk is an authored intact mesh plus a pre-broken version, swapped when a damage counter or explosion trips it; probably 2 states, maybe a chipped middle state for pillars. Chunks spawn as rigid debris. State counts are not documented anywhere I found.
- [I] Glass: binary swap/removal plus shard particles. Wood, tiles, sandbags, cars: no per-material source.

## 2. Bullet impacts

- [S] Bullet-hole decals, dust on every impact, rock particles flying (Richard Bunn). Burly Bird URL.
- [S] Hits on characters give dust and armour padding instead of blood (Bunn). Same URL.
- [S] Casings eject to the LEFT (opposite real guns) so they cross the player's view (Bunn). Same URL.
- [S, secondhand] Hits kick up debris, dust and smoke; glass shatters; ricochets; casings. https://forum.beyond3d.com/threads/criterions-shooter-black-impressions-inside.10723/ (403 on fetch; known only via search snippet)
- [S, weak] German preview says smoke, dust, fire, splinters, casings were "physically" simulated; reviewer impression. https://www.gameswelt.de/black/test/black-662 (snippet only)
- [I] Numbers (decal cap, particle size, lifetime, colour per surface): none published. Plausible PS2 practice: ring buffer of decals (oldest recycled), short-lived (0.3-1 s) camera-facing dust sprites tinted per surface, a few chips per hit, distance culling of small particles.
- [I] "Chunky" feel: decal + dust puff + 2-4 chips + loud sound on the same frame, and misses that still hit something reactive.

## 3. Explosions, smoke, dust, fill rate

- [S] Many particle effects, airborne dust, explosions; bloom pushed high for semi-volumetric light and god rays; PS2 version was the dev favourite (Bunn). Burly Bird URL.
- [S] Press called the PS2 build a technical achievement; credited Criterion's PS2 familiarity. https://www.gamespot.com/articles/black-final-hands-on/1100-6144038/
- [I] No source on overdraw. Likely: small sprites, short life, few large clouds, additive or alpha-test instead of sorted blend, near-camera fade, cap on simultaneous emitters.

## 4. Sound and camera

- [S] "All faders to 10", Hollywood over-the-top rather than authentic recordings (Ben Minto). Burly Bird URL.
- [S] "GUNSU": gunfire samples marked per shot so sustained fire is stitched from short pieces; "Choir of Guns": same weapon uses different sample sets per enemy. Same URL.
- [S] Material substitution: bullets hitting trees played metal/glass/plastic sounds. Same URL.
- [S] PS2 ADPCM compression, but about 1 s of main RAM reserved so the first second of each shot plays at 48 kHz WAV quality. Same URL.
- [S] "Gun porn" was the pitch. https://kotaku.com/that-time-burnouts-developers-made-a-first-person-shoot-1762039213 ; https://www.imfdb.org/wiki/Black
- [I] Camera shake / motion blur: no source found. Bloom is the only sourced camera-side effect.

## 5. RenderWare-level detail

- [S] RenderWare, Burnout-derived engine; about nine months total; no level tools (spawners, counters, timers); Lightwave (Bunn). Burly Bird URL; https://en.wikipedia.org/wiki/Black_(video_game)
- Nothing sourced on poly, particle or decal budgets.

## Ranked cheap techniques for our setup

1. Same-frame impact bundle [S+I]: on every hit spawn decal + dust puff + 2-4 chips + sound together, one UnrealScript function per surface type. The sync reads as "chunky".
2. Surface-tinted dust per material [S+I]: one small Emitter class per surface (concrete grey, dirt brown, wood tan), life 0.4-0.8 s, 3-6 sprites; choose by hit material.
3. Decal ring buffer with hard cap [I]: N projectors (64-128), recycle oldest, shorter fade when far. Keeps projector cost flat while still giving "hundreds of holes" feel.
4. Pre-fractured swap for set pieces [S]: intact static mesh plus broken mesh (or 3-4 chunk meshes) for pillars, walls, gravestones. After N hits or an explosion, hide intact, spawn broken plus dust burst. Add a "chipped" middle mesh for pillars. No runtime deformation needed.
5. Chips as pooled tiny static meshes or sprite quads [I]: 2-4 per hit, 1-2 s life, simple physics, scale to zero to fade.
6. Cheap smoke to fix 13 fps [I]: fewer, smaller, shorter-lived sprites; cap sprite screen size; fade alpha near camera; additive/alpha-test where possible; cap simultaneous explosion emitters; in our pixel shader discard low-alpha pixels early.
7. Armour-dust hits instead of blood option [S]: dust/padding puff for armoured enemies; variant of #2.
8. Redirect misses into reactive scenery [S]: place destructible props behind enemies and have AI aim at them; zero render cost.
9. Sound layering [S]: random sample set per enemy per weapon; harsher impact sounds substituted for soft materials; keep a sharp, full-quality attack.
10. Bloom boost on blasts [S]: brief post-shader bloom gain spike decaying over ~0.5 s.

Open leads if more certainty is wanted: Beyond3D thread (needs a real browser), Edge/Eurogamer 2005-06 previews. Items 1, 3, 5, 6 are our inference of PS2 practice, not documented Black internals.
