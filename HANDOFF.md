# Handoff between Claude sessions

The cloud session can't message the PC session directly (cloud sessions can't send to other
sessions yet), so its replies go here. The PC session can still message the cloud session.
Newest first.

## 2026-10-02 (later), cloud session to "unreal modding" (PC)

- The user picked a different main fix for reaching the PC after reboots:
  `tools/remote-control/start-remote-control.ps1` runs `claude remote-control` in the repo at
  each login (Startup shortcut, installed by the user with `-Install`). Your `wake-chats.ps1`
  stays as the backup for waking the old chats. Nothing for you to do; just don't be surprised
  by a "<PC name> codes" session appearing.

## 2026-10-02, cloud session to "unreal modding" (PC)

- Done: `SESSION_NOTES.md` "PC access" now describes `wake-chats.ps1`. It replaces "resume
  each session by hand"; the user creates the Startup shortcut; the routes that don't work are
  listed; Chrome Remote Desktop and SSH stay as fallbacks; U2Pilot runs need the PC
  unattended. It's on branch `claude/pc-integration-notepad-6gp2ac` (commit `9df8fe2`), not on
  master yet: merge that branch too, or wait until the user merges it.
- Your merge plan for `tools/C/U2Shaders` is fine: my d3d8 source, your borderless patch
  0002 as an optional extra. Master (`6de76f6`) is otherwise the same as the branch.
- I won't touch `U2Wardrobe`, `U2UTWeapons`/`U2UTFlak` or `ssmenu_v2.py`, and I'll stay out
  of `tools/C/U2Shaders` until your merge is pushed.
- For the checklist: items 9-12 (`surface=`, `charlight=1`, the U2Blender round trip,
  `lmcapture=1`) need master's `tools/C/U2Shaders/d3d8-mingw.dll` installed as `d3d8.dll`.
  Please send me any "not supported" lines from `U2Shaders.log`, and the `lmcapture:` line
  (how many lightmaps were recorded); those decide what I change next.
