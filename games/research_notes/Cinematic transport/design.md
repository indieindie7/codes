# Cinematic transport for Unreal II

The goal, in the user's words: "when the console is opened the cinematics pause and a movie time slide and buttons with pause and stop and play appear."

So: while a cutscene plays, opening the console pauses it. The d3d8 fork's ImGui layer then shows a transport bar: a time slider (scrub), Play/Pause, Stop, frame step and a speed control. Everything goes through U2GM as `gm cine ...` commands.

Status (2026-10-08): this design is done. The script side is written as `U2GM/Classes/GMCine.uc`, but it has **not been compiled**: the permission classifier blocked writing the classes into the game folder. The fork UI is specified here but not built.

---

## 1. How Unreal II plays cinematics

### 1.1 Matinee: the SceneManager

Unreal II uses UE2's early (UT2003-era) Matinee and adds a few fields of its own. Its source is embedded in `System\Engine.u`. I extracted it to `Documents\Tools\u2_export\full_Engine\Classes\` (`SceneManager.uc`, `MatAction.uc`, `MatSubAction.uc`, `SubAction*.uc`, `ActionMoveCamera.uc`, `ActionPause.uc`, `InterpolationPoint.uc`, `MatObject.uc`). I decompiled the native side from the Ghidra project `Documents\U2_research\ghidra` into `decomp\Engine.dll_ASceneManager__*.c` and `Engine.dll_USubAction*__Update_*.c`.

- **`SceneManager extends Info`** (placeable, native). It holds `Actions` (MatAction: `ActionMoveCamera` / `ActionPause`, each with `Duration`, an `IntPoint` and its own `SubActions`).
  - `Affect` is either `AFFECT_ViewportCamera` (the player's camera) or `AFFECT_Actor` (moves `AffectedActor`, for example a dropship).
  - `bLooping`, `bCinematicView` (letterbox) and `SceneEndedPlayerFocusTag` are the other settings.
  - Runtime state: `CurrentTime`, `TotalSceneTime`, `PctSceneComplete`, `SceneSpeed`, `Viewer`, `OldPawn`, `bIsRunning`, `bIsSceneStarted`, `SubActions` (a flat list of all sub actions), `CamOrientation`.
  - U2's `StopScene()` is a hack: `CurrentTime = TotalSceneTime + 0.01`. It skips every remaining event, and `U2PlayerTestController.StopScenes` warns that it breaks gameplay.
- **Start.** `Trigger()` sets `bIsRunning` and disables Trigger. On the next native tick, `SceneStarted()` runs:
  - The Viewer is the first PlayerController that has a Player.
  - The pawn is hidden and frozen. `Level.Game.NotifyCutSceneStart()` hides the HUD, disables saving and disables the use reticle (`U2GameInfo`).
  - `UnPossessMatinee()` and `StartInterpolation()` run, which sets `PC.bInterpolating`.
- **End.** `SceneEnded()` reverses all of that: `PossessMatinee`, `bInterpolating = false`, `NotifyCutSceneEnd`. Then `TriggerEvent(Event)` fires, which is how scenes chain (U2's SceneManager has no `NextSceneTag`).
- **Sub action classes in U2.** There are 8: Trigger, ConsoleCommand, Orientation, FOV, Fade, GameSpeed, SceneSpeed and ParticleTrigger.
  - There is **no** PlaySound sub action and no dialogue sub action. All audio comes from events: a `SubActionTrigger` triggers a DialogTrigger, an AIScript, a sound actor and so on.

### 1.2 The native tick

From `ASceneManager::Tick` @ `0x10418d40`. Field offsets: `+0x3e8` CurrentTime, `+0x3d4` SceneSpeed, `+0x3d8` TotalSceneTime, `+0x3e4` bits (1 = bIsRunning, 2 = bIsSceneStarted).

```
if (!AActor::Tick(dt) && !bIsRunning) return;     // a RUNNING scene ticks even when AActor::Tick says no
if (bIsRunning) {
  if (!bIsSceneStarted) { bIsSceneStarted = 1; SceneStarted(); Viewer.Location = Actions[0].IntPoint.Location; }
  else CurrentTime += dt * SceneSpeed;
  Pct = CurrentTime / TotalSceneTime;
  if (Pct > 1 || Viewer == None || Viewer.bDeleteMe || (AFFECT_Actor && pawn dead)) { SceneEnded(); if (bLooping) TriggerEvent(...) }
  else UpdateViewerFromPct(Pct);   // camera place + rotation from Pct, then Update() on every sub action not Expired
}
```

- **The camera is a pure function of `CurrentTime`.** `UpdateViewerFromPct` works out the action, path sample and rotation from Pct on every tick. So writing `CurrentTime` is a seek for the camera.
- **Sub action state only moves forward.** `UMatSubAction::Update`: Waiting → Running while `PctStarting < p < PctEnding`. Once `p > PctEnding` it goes to Ending, which fires or applies once more, and on the next tick to Expired.
  - Trigger and ConsoleCommand fire once, on that Ending tick.
  - Orientation, FOV, Fade, GameSpeed and SceneSpeed blend while Running and apply their final value on Ending.
  - Only the editor's `RefreshSubActions` resets the statuses (called from `SetCurrentTime`, which script can't reach).
- **`SubActionSceneSpeed` writes `SM.SceneSpeed` on every tick while it runs.** `SubActionGameSpeed` writes `Level.TimeDilation` and calls `GameInfo.NotifyGameSpeedChanged`.
- **Lost events at the very end.** The end test runs *before* `UpdateViewerFromPct`, so sub actions that fall inside the last tick's jump past 1.0 never fire. U2SkipCutscenes' `RescueSceneTriggers` exists for this reason.
- **Which clock does a scene use?** `ULevel::Tick` @ `0x103b5be0` passes actors `dt * TimeDilation`, clamped (max 0.4). By the decompile, scene time should follow game speed. U2SkipCutscenes' notes say the opposite, that "scenes play on real time", and it tops up `CurrentTime` by hand. GMCine doesn't depend on which is true (see `Pace` below). Test T8 measures it.

### 1.3 Dialogue and sound

The dialogue system lives in `Documents\Tools\u2_export\full_U2Dialog\Classes`.

- **Actors.** `DialogEngine`, `DialogSession` and `DialogNode` are all Actors (`Dialog extends Actor`). A scene starts conversations through events (DialogTrigger).
- **How a line plays.**
  - `DialogSession` plays each line with `PlayVoice(Ogg)` or `PlaySound(SLOT_Dialog)` (`PlaySoundFile`, DialogSession.uc:671-748).
  - It schedules the line's end and the gap that follows with `AddTimer(AudioFinishedTimer / NoInterruptTimeFinishedTimer, AudioLen + PostDelay)` (:641). These are game-time timers.
  - The line's timed actions (NPC pause/unpause, gestures, anims, events) run at a percentage of the line through `ProcessActions` timers (:1187).
- **Keeping lines in sync with the audio.** `DialogNode.GetAudioLength` (DialogNode.uc:124-160) multiplies a line's length by `Level.TimeDilation` while a cutscene runs, unless `DialogEngine.AllowSlomo` is set. So lines stay in sync with voice audio, which does **not** speed up with game speed.
  - `AllowSlomo = true` (U2SkipCutscenes' trick) lets lines shorten with game speed.
  - `DialogSession.NotifyGameSpeedChanged` rescales running timers only when AllowSlomo is set.
- **Stopping a line.** `DoStopAudio` → `StopVoiceFile(ogg)` / `StopSoundSlot(SLOT_Dialog)`.
- **Consequence for scrubbing back.** A voice line that has started can only be stopped, never rewound. A conversation session, once started, keeps its own clock and its own state (spoken counts, exit events, NPC control).
- **Pausing audio.** `Actor.PauseAudio(optional bool bPauseMusic)` and `UnPauseAudio()` are U2 natives. `GameInfo.SetPause` calls them, and the save code uses them too. So the engine's pause also pauses sounds, and with `true` it pauses music as well.

### 1.4 How U2SkipCutscenes skips

Source: `unreal2_mods/U2SkipCutscenes/Source/.../SkipCutscenes.uc`. U2SkipScenes is the same code with conversations off.

- `TimeDilation = 12`.
- Moves `SM.CurrentTime` forward by `RealDelta * 11` each tick, in steps of at most 0.25 s and never past `Total - 0.1`. This way the engine plays the end itself and fires `SceneEnded`.
- Sets `DialogEngine.AllowSlomo = true` and adds to `Session.TimeElapsed` so dialogue gaps keep up.
- Mutes through the ini `SoundVolume`, saved to config first so a crash can be undone.
- Rescues dialogue actions that get dropped when a line's end and its actions expire in the same frame (`RescueDroppedActions`). Without this, an NPC can stay paused forever.
- Rescues scene triggers that never fired (`RescueSceneTriggers`).
- Stops at a dialogue choice or when an enemy targets the player.

That is the proven, progression-safe way to go **forward** fast. GMCine reuses it for Stop and for long seeks.

### 1.5 Pause: what keeps ticking

From the decompiled `ULevel::Tick`, `AActor::Tick` and `ULevel::IsPaused`:

| Mechanism | What ticks | The scene | Audio |
|---|---|---|---|
| `Level.Pauser != None` (game pause; `IsPaused` = Pauser set and `PauseDelay <= TimeSeconds`) | PlayerControllers with a viewport (input only), plus **actors with `bAlwaysTick`** (flag `0x2000000`, which gets a full Tick with timers and script). ScriptedLights still flicker. `TimeSeconds` stops. | Frozen, unless the SceneManager has bAlwaysTick | `SetPause` → `PauseAudio` pauses sounds (and music with `true`) |
| `Level.bPlayersOnly` (`gm freeze`) | Tick type becomes ViewportsOnly, so script runs only for player-controlled actors. **bAlwaysTick does not help here**, despite the comment on Actor.uc:248. | **A running SceneManager keeps ticking** (it bypasses the check), so freeze does **not** stop cinematics | Not paused |
| `Level.TimeDilation` | Everything, scaled | Scaled by the decompile; "real time" by U2SkipCutscenes' notes | Voices keep their speed |
| `SM.SceneSpeed = 0` | Everything | Camera frozen, but SceneSpeed sub actions overwrite it | Not paused |

Other facts that matter:

- **Console commands run while paused.** `exec` and console commands run straight from input, so they work under Pauser. **Timers and Tick don't**, unless the actor has bAlwaysTick. GMMaster's 0.25 s timer, which execs `U2GMPanel.txt` and saves PanelState, is therefore frozen under any pause.
  - `gm freeze` has the same problem, and also under bPlayersOnly. Unfreezing from the panel's button probably doesn't work; typing it does.
- **`SetPause` takes a lock key.** U2's menus use 314, 278 and 777. While a key holds the lock, other keys can neither pause nor unpause.
  - `U2PlayerController.Fire/AltFire` unpause with key 0. Our lock blocks that too.
  - The menu stays usable during our pause, and closing the menu doesn't unpause ours.
- **`bAlwaysTick` is `const` in script.** It is set in defaultproperties for our own actor. On the SceneManager we set it at runtime with `SetPropertyText("bAlwaysTick","True")`; UE2's SetPropertyText doesn't check const. **Needs test T4.**

---

## 2. What each control can do, and its limits

The idea that makes this work: **the camera can be scrubbed, the world can't be rewound.** Everything the scene *causes* (dialogue sessions, voices, NPC scripts, spawns, door movers, objectives) happens through one-shot events, each with its own clock and state. So the transport tracks a **world head**: the furthest scene time the world has really played.

| Control | Mechanism | Limits |
|---|---|---|
| **Pause** | The game's own pause (`SetPause(true, PC, 4141)`: Pauser + PauseAudio, plus `PauseAudio(true)` for music). The held SceneManager gets bAlwaysTick and `SceneSpeed = 0`, and `CurrentTime` is re-pinned every tick. | Real-time UI timers keep running, so a subtitle may disappear during a long pause. A pause can't start while a menu holds its lock. |
| **Scrub / seek T ≤ head** | Set `CurrentTime` while paused. The scene keeps ticking (bAlwaysTick), so the camera follows at once. On a jump **back**, Orientation/FOV/Fade/SceneSpeed sub actions are reset to Waiting, so the next tick re-applies them in order and the camera state at T is correct. | Camera only. Characters stay where the world is (at the head). Triggers before T are not fired again, which is deliberate: no doubled voices, doors or spawns. A fade-out that happened *after* T stays dark if no earlier fade sub action exists to reset it, and FOV behaves the same (polish item). |
| **Seek T > head** | Run the world there: unpause and play up to T, fast and muted if more than 1.5 s ahead, then pause. Events fire in order, as in U2SkipCutscenes. | Takes real time: about (T − head) / 10 s. An instant jump would fire every skipped trigger in one tick, which overlaps dialogue, so it isn't offered. |
| **Play** | If the camera is behind the head: a **preview**. The game stays paused and the camera replays silently up to the head, then the world goes live with sound. Otherwise: unpause. | The preview is silent and the characters are frozen. |
| **Stop** | Fast-forward to the end, muted, at 10×, with dialogue rescue. When the scene ends, any end triggers that never fired are fired. | Not an instant cut: a 60 s scene takes about 6 s. Conversations the scene started go on at normal speed afterwards. |
| **Step ±DT** | A seek from the paused time. Back is camera only. Forward past the head runs the world DT (normal speed, so a moment of sound), then pauses. | Same limits as seek. |
| **Speed S** | `TimeDilation = authored × S` (it follows any GameSpeed sub action). The scene clock is paced to S× its own speed, whichever clock the engine really uses. Above 1.5: voices muted, `AllowSlomo` on, and dialogue time pushed forward so lines keep up. | Between 1 and 1.5 and below 1, voices play at normal speed and lines stretch to match the audio, so the dialogue and the camera drift apart. The slow-motion camera is good for looking, not for dialogue. |
| **Rewind (true)** | Not possible live. Stage 4 option: save as a scene starts, then load and fast-forward to T. | U2 disables saving during cutscenes (`bSaveDisabled`), so it is experimental. |

More rules:

- **Which scene is held.** The transport holds the running SceneManager whose `Viewer == PC` (the camera scene). AFFECT_Actor scenes, such as a dropship path, freeze with the world under the pause but aren't scrubbed.
- **Looping scenes** (attract loops): `len` is one loop. Stop fast-forwards forever, because the loop never ends; use release. This is a polish item.
- **U2SkipCutscenes.** If it is fast-forwarding, the transport won't take hold. Pausing also freezes its Tick (it has no bAlwaysTick), so Space does nothing while paused.

---

## 3. Recommended mechanism

1. **GMCine (U2GM, new class, a `bAlwaysTick` Info) owns the transport.**
   - It watches for the camera scene, gated on `PC.bInterpolating`, with an AllActors search at most every 0.25 s.
   - It reads GMMaster's `bConBig` / `bConQuick` (set by Console.ui's `gm con` triggers).
   - When the console opens during a scene, it **auto-pauses**. When the console closes, it **plays again**, unless the user pressed something in between.
2. **Pause is the game pause with our lock key**, not `bPlayersOnly` (cinematics run through that) and not `SceneSpeed` alone (the NPCs, voices and dialogue timers would go on). The held SceneManager is given bAlwaysTick so the camera can still be scrubbed while everything else is frozen.
3. **The world head separates the camera preview from real playback**, as in section 2.
4. **While GMCine holds the pause, it pumps the panel.** Every 0.25 s it runs `exec U2GMPanel.txt` and `Master.SaveState()`, so the fork's q-lines, acks and `con=` keep working (GMMaster's timer is frozen).
5. **The state goes to the fork as one ini line**, `[U2GM.GMCine] CineState` in `U2GM.ini`:
   ```
   CineState="seq=17 st=pause scene=SceneManager3 len=41.20 spd=1.00 loop=0 ev=0.50,8.00,12.30,40.90 t=12.34 head=20.10"
   ```
   - `st` is one of `none | free` (playing, not held) `| play | pause | preview | ff | run`.
   - `ev` lists the scene's Trigger and ConsoleCommand times, for tick marks on the slider.
   - The line is written every 0.25 s while the console is open or a scene is held, and otherwise only when something other than the time changes.
   - The fork moves the slider on smoothly between reads, using its own clock times `spd` (or ×FastSpeed for `ff`).

---

## 4. Commands and panel UI

### 4.1 Script commands (GMCine.Command)

```
gm cine [status]        print: mode, scene, t / len, world head, speed
gm cine pause | play | toggle
gm cine stop            finish the scene (fast, muted, events kept)
gm cine seek T          camera-only at or before the head; the world runs there past it
gm cine step [DT]       default StepTime 0.1 s; negative steps back
gm cine speed S         0.05..16
gm cine release         let go (unpause, normal speed, sound back); the scene plays on
gm cine auto 1|0        auto-pause when the console opens (config bAutoPause)
```

Config (`[U2GM.GMCine]` in U2GM.ini): `FastSpeed=10`, `FastFrom=1.5`, `StepTime=0.1`, `bAutoPause`, `bResumeOnClose`, `bPauseMusic`, `bMuteFast` (all true). There are also the crash-recovery fields `bMutedByCine` / `SavedSoundVolume`.

### 4.2 Hook lines for GMMaster.uc

These are the only edits GMMaster needs; another job is editing that file:

1. After `var bool bConBig, bConQuick; ...` (around line 118):
   ```
   var GMCine Cine;                    // the cinematic transport (gm cine ...)
   ```
2. In `PostBeginPlay()`, after `SetTimer(0.25, true);`:
   ```
   	Cine = Spawn(class'GMCine');
   	if (Cine != None)
   		Cine.Master = Self;
   ```
3. In `DoCommand()`, before `else if (Cmd == "tex")` (around line 1303):
   ```
   	else if (Cmd == "cine")
   	{
   		if (Cine != None)
   			Cine.Command(After(Args, 1));
   	}
   ```
4. Optional, in the `help` block:
   ```
   		Say("gm cine [status] | pause | play | toggle | stop | seek T | step [DT] | speed S | release | auto 1|0");
   ```

GMCine uses these GMMaster members, all of which exist today: `PC`, `bConBig`, `bConQuick`, `PanelPoll`, `PanelFile`, `SaveState()`, `Say()`, and the static `Word()` / `After()`.

### 4.3 Fork panel (u2shaders.hpp), not built

- **Read.** In the U2GM.ini reader (`GmReadIni`, around line 2791), also read the section `[U2GM.GMCine]`, key `CineState`, into a `GmCineT { st, scene, t, len, head, spd, loop, ev[], seq, DWORD ReadAt }`.
- **Show.** Draw `CineBar()` next to `SketchStrip()` (around line 3675) when `GmSt.Con != 0 && Cine.st != none`. Also add a "Cinematic" section to the F7 panel.
  - It is an ImGui window with no title bar and auto-resize, centred at 82 % of the screen height so it sits above the bottom letterbox bar.
  - Layout:
    ```
    [|<] [<] [ > / || ] [■] [>]   ──────●───────────|────  12.3 / 41.2 s   [1x ▾]
                                      ^played (head)   ^event ticks
    ```
  - `|<` sends `cine seek 0`. `<` / `>` send `cine step -0.1` / `cine step 0.1`; Shift+click steps 1 s. Play/Pause sends `cine toggle`. ■ sends `cine stop`. The speed combo (0.25, 0.5, 1, 2, 4) sends `cine speed S`.
  - The slider covers 0..len. Draw the part up to `head` brighter (the world has played it) and draw the `ev` ticks.
  - When `t < head`, show the line "preview: world waits at {head}s".
- **Dragging.**
  - Show the dragged value straight away.
  - Up to the head, send `cine seek T` at most every 120 ms.
  - Past the head, don't send during the drag. On release, send one `cine seek T`, which fast-forwards; show "running to T…" while `st=ff`.
  - In `GmSend`, treat `cine seek ` like `preview `: a newer one replaces the waiting ones.
- **Mouse.** The strip already takes `WM_LBUTTONDOWN` while the console is open (around line 3553). Generalise this: while `CineBarShown`, pass mouse messages to ImGui and swallow them if the cursor is inside the bar's last rectangle **or** a slider drag is active. Everything else still reaches the game.
- **Extrapolation.** If `st` is `play` or `preview`: `t_shown = min(len, t + (now - ReadAt) * spd)`. For `ff`, multiply by FastSpeed.

---

## 5. Staged plan

| Stage | Work | Estimate |
|---|---|---|
| 0 | Add the GMMaster hooks, compile U2GM (GMCine is written but **not compiled**), then run tests T1–T6 | 0.5 day |
| 1 | Fork transport bar (sections 4.3 and 3.5), with mouse routing, drag-seek and extrapolation | 1 day |
| 2 | Tests T7–T14. Fixes: fade/FOV reset on backward seek (remember the PC's fade and FOV when the scene is held), looping scenes (Stop releases, `len` = loop), chained scenes (offer "next scene"), a "Cinematic" section in the F7 panel | 1 day |
| 3 | Comfort: keyboard shortcuts while the bar shows (Space conflicts with typing, so use F-keys or the bar only), thumbnails / a bookmark list on the slider (scene times of `ev`), U2SkipCutscenes interop (Skip button = `cine stop`) | 0.5–1 day |
| 4 (optional) | True rewind: on scene start (`bIsRunning && !bIsSceneStarted`), save to a scratch slot (check that `SaveGame` ignores `bSaveDisabled`); "rewind to T" = load, then fast-forward muted to T and pause | 1–2 days, risky |

### Test list (for the session that runs the game)

1. **T1** Compile with the hooks, using `<game>\SystemBuild` and `ucc make`.
2. **T2** During a scene (TutA opening, Atlantis talks inside a scene, a PA_* arrival), `gm cine` shows the scene name, time and length.
3. **T3** Open the console during a scene. It auto-pauses: camera, NPCs, voice and music all stop. Check the log for "GM: cine holds".
4. **T4** While paused, `gm cine seek <earlier>`: **the camera moves**. This tests SetPropertyText on const `bAlwaysTick` and the scene ticking under pause.
   - If the camera doesn't move: the fallback is a one-frame `Level.Pauser=None` + `bPlayersOnly` per seek, re-paused from a UIConsole render listener.
5. **T5** `gm cine play` after seeking back: a silent preview up to the head, then live with sound.
6. **T6** `gm cine step` ×5, `gm cine step -0.5`.
7. **T7** Seek 1 s past the head (normal speed, then pause). Seek 10 s past it (ff, muted, then pause; check the sound volume comes back).
8. **T8** `gm cine speed 2`, 10 s, `status`: compare the scene time with the real time. This settles the "real time" question. Check whether the dialogue drifts.
9. **T9** `gm cine stop` on a scene that opens a door or sets an objective: progression is intact, and look for "cine rescues" lines in the log.
10. **T10** Close the console after an auto-pause: playback resumes.
11. **T11** Esc menu while paused: the menu works, closing it keeps the pause, and `gm cine play` resumes.
12. **T12** F7 panel buttons while paused: the commands still run (the pump works).
13. **T13** Stop on a level's last scene, which travels: no pause and no mute is left behind on the next map.
14. **T14** With U2SkipCutscenes installed: Space while paused does nothing; while it is skipping, GMCine stays out.

---

## 6. Files

- `unreal2_mods/U2GM/Classes/GMCine.uc`: the script side, new and not compiled yet.
- Matinee source: `Documents\Tools\u2_export\full_Engine\Classes\SceneManager.uc`, `MatSubAction.uc`, `SubAction*.uc`, and the rest (extracted from Engine.u).
- Decompiled natives: `Documents\U2_research\ghidra\decomp\Engine.dll_ASceneManager__{Tick,UpdateViewerFromPct,SetCurrentTime,RefreshSubActions,SetSceneStartTime}_*.c`, `Engine.dll_USubAction*__Update_*.c`, `Engine.dll_UMatSubAction__{Update,IsRunning}_*.c`, `Engine.dll_ULevel__{Tick,IsPaused}_*.c`, `Engine.dll_AActor__Tick_*.c`.
- U2 script used above: `full_U2/Classes/U2GameInfo.uc` (NotifyCutScene*, NotifyKilled disables scenes), `full_Engine/Classes/GameInfo.uc:319` (SetPause with a key plus PauseAudio), `full_U2/Classes/CodeMonkey.uc:40` (menu pause keys), `full_U2/Classes/U2PlayerController.uc:539` (Fire unpauses), `full_U2Dialog/Classes/DialogSession.uc` and `DialogNode.uc`.
