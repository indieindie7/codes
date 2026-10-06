# Options menu: UX pass (draft for approval)

Written 2026-10-05. The user's brief: menus are trees, depth is bad, redistribute the pages.

## Today's tree (depth = presses from the pause menu)

```
Pause > Options (depth 1)
  Difficulty                      (stock page)
  Game Options                    (stock + our "More Gameplay Options" row)
    > Gameplay                    (ours, depth 3): boss damage x2, running speed, blood, damage x2
  Camera Options                  (stock)
  Audio Options                   (stock + our Dialogue Volume)
  Video Options                   (stock brightness/contrast/gamma + our fullscreen rows)
    > Display Options             (ours, depth 3): widescreen, trilinear, min frame rate, FOV, colourblind x2
      > Graphics                  (ours, depth 4): post, soft shadows, GI, SMAA, frame cap, shadow darkness, sharpen
  Graphics Options                (stock "PC options": resolution, shadows, projectors, distortion, draw/fog distance, dynamic lights)
  Controls                        (stock)
```

Problems:
1. Our best-known features (soft shadows, GI, post effects) sit at depth 4, behind two "More ..." rows.
2. Two pages are both called Graphics: the stock one (resolution, draw distance) and ours.
3. "Display" vs "Video" vs "Graphics" mean nothing to a player; they were split by the 7-row limit.
4. Gameplay tuning (damage, blood, speed) hides behind Game Options' "More ..." row.
5. Rows are grouped by when we added them, not by what a player is looking for.

## Proposed tree: everything at depth 2, grouped by intent

The stock Options list becomes the only hub. Every page is one press from it, and no page has a
"More ..." row. The 7-row limit stays, so pages are split by topic, never by overflow.

```
Pause > Options
  Difficulty                  (stock, unchanged)
  Gameplay                    boss damage dealt / taken, damage dealt / taken, running speed,
                              blood (gore on/off), + stock: toggle crouch  [7]
  Controls                    (stock key config, unchanged)
  Camera                      (stock: inverts, sensitivities, flick) + Field of View  [7]
  Audio                       (stock + Dialogue Volume, unchanged)
  Screen                      resolution, Fullscreen mode (Off / Borderless / Exclusive, one row),
                              VSync, Frame Cap, Widescreen, Brightness, Gamma  [7]
  Graphics                    Shadows (Off / Yours / Everyone's), Shadow Darkness, Global
                              Illumination, Post Effects, Anti-Aliasing, Sharpening, Trilinear  [7]
  Advanced                    stock PC rows nobody touches: projectors, distortion, draw distance,
                              fog distance, dynamic lights, contrast, min frame rate  [7]
  Accessibility               Colorblind mode, correction strength, subtitles, vibration, fading
                              HUD, slow-mo weapon select, auto-aim mode  [7]
```

Changes in detail:
- **Fullscreen** becomes one row with three states instead of two bools that fight each other.
- **Field of View** moves to Camera, where players look for it.
- **Frame Cap** and **VSync** sit together on Screen (both are "how the picture reaches the monitor").
- **Stock Game Options** rows (crouch mode, vibration, dodge, fading HUD, slow-mo select,
  levitate, auto-aim) are split: feel-of-play rows go to Gameplay or Accessibility.
  "Double Tap Dodging" and "Levitate Objects" stay on Gameplay if a row is free; otherwise Advanced.
- Resolution's "Apply" prompt stays as the stock page does it (it needs a restart of the renderer).
- Nothing is removed; every stock row keeps working through the stock code paths.

Depth: 2 everywhere (was 4). Pages: 9 (was 10 counting the stock Graphics and ours).

## How it would be built
- `ModGUIController` already redirects stock page names to our classes; the hub
  (`Interface.MenuPauseOptions`) gets a redirect too, to a `ModOptionsHub` with the nine rows.
- The stock pages we keep (Difficulty, Controls, Audio) open unchanged.
- Each new page is a `MenuPauseOptionsBase` subclass like today's; rows move between pages by
  changing which settings they bind, with the current apply code reused.
- Localised captions in `AdventMod.int`.
- One hidden test run per page through the existing debug menu driver (DebugOpenMenu /
  DebugActions click/slide), screenshots to compare.

## Decisions (user, 2026-10-05 evening)
- Tree approved. No "Advanced" page: it's an untangible name against common menu tropes. Its rows
  go to a **Quality** page instead (a trope players know: draw distance, fog distance, dynamic
  lights, projectors, distortion effects, trilinear filtering, minimum frame rate = 7), and
  Contrast joins Brightness and Gamma on Screen (Screen then holds 8, so Widescreen moves to
  Quality and Trilinear to Graphics... final split below).
- Difficulty stays as the first row of the hub.
- The hub shows each row's current values ("Graphics: Shadows Yours, GI On").

Final pages (7 rows each, depth 2):
- Gameplay: boss damage dealt, boss damage taken, damage dealt, damage taken, running speed, blood, toggle crouch
- Camera: invert horizontal, invert vertical, invert flight, horizontal sens., vertical sens., flick sens., field of view
- Screen: resolution, fullscreen mode (Off / Borderless / Exclusive), VSync, frame cap, brightness, contrast, gamma
- Graphics: shadows (Off / Yours / Everyone's), shadow darkness, global illumination, post effects, anti-aliasing, sharpening, trilinear filtering
- Quality: draw distance, fog distance, dynamic lights, projectors, distortion effects, widescreen, minimum frame rate
- Accessibility: colorblind mode, correction strength, subtitles, vibration, fading HUD, slow-mo weapon select, auto-aim mode
- Audio, Controls, Difficulty: stock pages (Audio keeps our Dialogue Volume row)
- Leftovers from stock Game Options (double-tap dodging, levitate objects): Gameplay is full, so they go on Accessibility only if a row frees up; otherwise they stay reachable on the stock Game Options page, which remains as a row called "Game Options" only if needed. To decide while building.

## Open questions for the user (answered above)
1. Is "Screen / Graphics / Advanced" a split you'd read correctly, or should Advanced merge into
   Graphics with the rarely used rows at the bottom (which would need two Graphics pages)?
2. Keep the stock Difficulty page as the first row, or move it under Gameplay?
3. Should the hub show the current value next to each row (e.g. "Graphics: GI On, Shadows Yours")?
   It costs a little code and makes the depth-2 pages discoverable without opening them.
