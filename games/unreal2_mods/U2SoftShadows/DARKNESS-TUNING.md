# Tuning shadow darkness (U2SoftShadows, and the Advent Rising port)

Companion to `SHADOWS-HISTORY.md`. How dark a character's shadow is comes from a chain of
multipliers. Knowing the chain is what makes tuning quick: each knob answers one question.

## The chain

For each shadow (one character, one light), every update:

```
ShadowDarkness (0-255, the engine's ShadowBitmapMaterial field)
    = ShadowStrength            how dark a shadow can get at all          (config, 0-255)
    x Strength                  how strongly THIS light lights the character
    x LightShare                how much of the light here comes from this light
    x Fade                      0..1 while switching lights (FadeRate per second)
```

**Strength** (`SSLightShadow`):
- sun: a fixed `0.8`;
- lamp: `MinStrength + (1 - MinStrength) * clamp(LampIntensity / FullIntensity, 0, 1)`
  with `LampIntensity = LightBrightness * (1 - (dist / reach)^2)`,
  `reach = 25 * (LightRadius + 1)` (the engine's light radius in world units).
  A bright, close lamp gives 1; a dim or far one bottoms out at `MinStrength`.

**LightShare** (`SSShadowController`, eased in `SSLightShadow` at 2/s so it never jumps):
```
Total  = AmbientBrightness(zone) * AmbientWeight + sum over lights that reach the character of
         LightBrightness * (1 - (dist / reach)^2)          (the sun counts too when it's visible)
Share  = MinShare + (1 - MinShare) * clamp(this light's score / Total, 0, 1)
```
Only with `bRespectBaked=True`; otherwise Share = 1. This is what keeps the shadows from
fighting the baked lighting: in a room lit by many lamps (or a bright ambient zone), every single
lamp is a small part of the light, so its shadow is faint, like a real shadow filled in by
the other lights. The only lamp in a dark corridor casts a near-full shadow.

Other things that change how dark a shadow *looks* without touching ShadowDarkness:
- **The fade along the shadow** (`bGradient`, `MaxTraceDistance`). Too short a fade makes the
  whole shadow look faint even at full darkness. This was the "invisible shadows" bug in
  Unreal II: the engine uses 2048, our fit gave 131-229, and the floor was already half faded.
  Now `MaxTraceDistance = clamp(shadow length * GradientScale (3.0), half, GradientLength (2048))`.
  Advent's stock InitShadowInfo has the same trap (MaxTraceDistance 350).
- **Overlap.** Several shadows on the same floor multiply (each is a DESTCOLOR modulate), so 3
  lights at medium darkness read darker than one at full. LightShare keeps the sum sensible.
- **Texture size and blur.** A 128 shadow texture blurs more than 256, so its core is lighter.
  We keep 128 (the user's rule: shadows are always soft) and compensate with darkness.
- **PCSS** (`pcss=1` in the d3d8 fork) outputs `0.502 * average(alpha)`, the same value the stock
  blur pass would have produced, so turning it on doesn't change overall darkness, only where the
  shadow is sharp or soft. `shadowtint=R G B` tints it per channel (1 1 1 = grey).

## The knobs (Unreal II defaults; user's values in User.ini)

| Key | Default | Does | Raise it when |
|---|---|---|---|
| `ShadowStrength` | 190 (user: 135, the menu's "Darkness" 60-255) | ceiling for every shadow | everything is too faint |
| `MinStrength` | 0.2 | darkness of the dimmest/farthest lamp, relative | far lamps cast nothing visible |
| `FullIntensity` | 128 | lamp intensity that already gives full strength | only very bright lamps cast proper shadows (lower it) |
| `MinShare` | 0.35 | darkness kept even when a light is a small part of the total | lit rooms show no shadows at all |
| `AmbientWeight` | 1.0 | how much the zone's ambient counts against the lamps | shadows look too dark in bright ambient zones (raise) or too faint (lower) |
| `bRespectBaked` | True | turns LightShare on | (off = every shadow at full Strength) |
| `FadeRate` | 2.5 /s | speed of the swap fade | switching lights looks slow (raise) or pops (lower) |
| `GradientScale` | 3.0 | fade length / shadow length | the shadow's far end vanishes too early |
| `GradientLength` | 2048 | cap on the fade length | (keep at the engine's value) |
| `MaxSteepness` | (degrees) | overhead lamps tilted to at most this | shadows hide under the body |
| Advent: `MinSteepness` | 35 | low lamps raised to at least this | shadows are long, thin and faint |

## How to tune (what worked)

1. **Always compare with the stock shadow at the same spot.** U2TestHub's `hub shadows mod|stock`
   switches, `hub info` prints every shadow's light, distance, ShadowDarkness, MaxTraceDistance,
   and "light here: total (lamps + ambient)". Two screenshots, same camera.
2. **One standard lamp scene** (`hub lamp 220 45 200`: brightness 220, 45 degrees up, 200 units),
   third-person camera behind the character. Tune `ShadowStrength` here first, so a single close
   lamp reads like a clear, not black, shadow (in Unreal II: roughly the stock shadow's darkness).
3. **Then the two extremes:** a dark corridor with one lamp (should be the darkest you allow) and
   a bright room with many lamps / high ambient (should still be visible, faint). Adjust
   `MinShare` and `AmbientWeight` for these, not `ShadowStrength`.
4. **Then distance:** walk away from a lamp; the shadow should thin out smoothly, not vanish.
   `MinStrength` and `FullIntensity` set that curve.
5. **Measure pixels, don't eyeball.** Sample the floor colour inside and outside the shadow in
   the screenshots and look at the ratio (e.g. shadow at 55-70% of the lit floor in the lamp
   scene). Eyeballing between runs fooled us more than once.
6. **Change one knob per run**, and keep the screenshots (U2Pilot puts them in `runs/<time>`).
7. With several shadows per character, debugging one shadow's texture shows only the top one:
   test with `MaxShadows=1` (found in the Advent port).

## Advent Rising notes

- Advent's lamps sit low (~17 degrees): `MinSteepness` 35 and a frustum distance cap of 600 made
  them visible. Low lamps also make long shadows, so check the fade (`GradientScale`) there.
- The stock shadow is kept on with `ShadowDarkness 0` (turning `bActorShadows` off stops the
  engine updating every shadow of that pawn), and hidden shadows are darkness 0 too, so a
  darkness of 0 must never be mistaken for "a bug" during tuning.
- Check what Advent's `AmbientBrightness` values look like before trusting `AmbientWeight = 1`:
  if its zones use a different range than Unreal II's, the share math shifts and every shadow in
  bright areas comes out too faint or too dark. Print "light here: total (lamps + ambient)" in a
  few rooms first.

### Advent values that worked (from the port, 2026-10-02)

- Zone ambient vs lamps: AmbientBrightness score 8 (level03sectionb station interior) and 20
  (level04sectiona outdoors) against lamp totals of ~159 and ~320, so `AmbientWeight` barely
  matters in Advent; the lamps dominate the share.
- Clearly visible shadows with: `ShadowStrength 255`, `MinStrength 0.5`, `MinShare 0.6`,
  `MinSteepness 35`, frustum distance 600.
- Sun works (Sunlight0 in level04sectiona). Nearby NPCs on: no measurable fps cost (4 adopted,
  ~204 fps either way).
- Test framing: the mod's FOV at 115 in the test ini so the third-person camera shows the feet.
