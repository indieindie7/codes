# HANDOFF fs2-ai (Frozen Synapse 2 AI bridge brains), 2026-11-04
## Index
1. State: what works, what is broken (L9-15)
2. Results: bound vs ambush2, 20 matches each (L16-25)
3. Paths, commits, commands (L26-34)
4. Key findings: order API (L35-42)
5. Left to try (L43-47)

## 1. State
- Bridge + brains work: our brain plans team 1 (units 1-4) before spSubmitTurn; stock Charon plans team 2 (units 5-8). Map test1.
- Every brain tried: 0 wins in all soaks. Best result is draws at the turn cap; kills below deaths.
- planAddOrder "WaitOrder" crashes Charon apply (3 of 3). Duck/EOS via planAddOrder are crash-safe.
- Game must start through Steam (FS2_STEAM=1, default) so playtime counts (user 11-04). Steam start ignores the DXVK 3060 filter env, so it may render on the 4070 Ti.
- No FrozenSynapse2.exe left running (closed 11-04); hoggate open.

## 2. Results (test1, 20 matches each, Steam launch)
| brain | kills | deaths | wins | Charon wins | cap draws |
|---|---|---|---|---|---|
| bound STEP 350 | 39 | 52 | 0 | 5 | 15 |
| ambush2 (select + addWaitOrder(1000), one run() per unit) | 35 | 59 | 0 | 6 | 14 |
- ambush2 = no gain, brain NOT kept (not in the tree). Difference is noise.
- Older small soaks: duckhunt 4 matches (kills 0/2/1/1, deaths 4/4/4/3), ambush Duck+EOS 3 matches (kills 3/1/0, deaths 2/4/4).
- A first ambush2 that batched all 4 units into ONE run() statement crashed the game in Charon apply (0 matches). One run() per unit did not crash.
- Raw logs (uncommitted): tools/bound20.jsonl, tools/ambush2.jsonl, tools/bound20-partial.jsonl (6 direct-launch matches). Console caps: C:\Users\john\AppData\Local\Temp\claude-cap\bound20s-080821.txt, ambush2s-084334.txt.

## 3. Paths, commits, commands
- Worktree: C:\Users\john\Documents\github\wt-fs2 ; tools in games/swat4_mods/tools (fs2brain.py, fs2soak.py, fs2bridge.py). Notes: games/swat4_mods/PORTS-HOOKS.md (FS2 sections).
- Game dir: C:\Program Files (x86)\Steam\steamapps\common\Frozen Synapse 2 ; bridge files smbridge/in.txt, out.txt there. Console log %APPDATA%\FrozenSynapse2\console.log (locked while running: retry opens).
- Commits on origin/master: 97800df, ffebeb0, 010c96e, 23560e5, 912f534, c2d68be (duckhunt), 9fa7181 (ambush + WaitOrder crash note), 157c8b2 (Duck+EOS soak), 3f230b9 (GUI add*Order note + 20-match results).
- Soak (background only, >2 min): from tools dir, `FS2_STEAM=1 py -3.13 -u -I fs2soak.py 20 out.jsonl --brain bound --map test1`. Brains: idle rush pairs focus bound hunt mass duckhunt ambush.
- Before a run: `py -3.13 -I ~/.claude/hooks/hoggate.py status`; Steam ActiveUser must be != 0 (reg HKCU\Software\Valve\Steam\ActiveProcess); one game at a time; kill FrozenSynapse2.exe when done (it holds the gate closed for other chats). A dead exe gives "timeout: game not polling": taskkill it first.
- Probe tool (not in repo): scratchpad probe.py, `py -3.13 -u -I probe.py 'stmt' ... [--submit]` loads test1, runs stmts, prints SMB out + console.log diff.
- Commit rule: git fetch; git rebase --autostash origin/master; git push origin HEAD:master; trailer Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>. Never bare git stash.

## 4. Key findings: order API
- The GUI's order functions are GLOBAL console functions that act on the GUI selection, not a unit id: addWaitOrder(ms) (GUI default 1000), addMoveAimOrder, addFocusAimOrder, addDuckOrder, addStandOrder, addProneOrder, addEOSOrder, addCOSOrder, addCancelMoveAimOrder, addSetSpeed, addEngageAndStopOrder, addReactivateOrder, addSuicideOrder, addRunAwayOrder.
- Selection helpers: cycleSelectedPlayer(), getSelectedPlayerId() (-1 at start), getSelectedPlayerTeam(), selectMyUnit() (0 args), getLastWPOnSelectedPlan(), unitIsSelected(id), toolboxSetOnlySelected, trySelectPlanElement. Also planAddOrderAtStart, planAddTimeHere, planSetTimeHere.
- Pattern that survived 20 matches: planNavigateTo(0,id,x,y) first, then `for(%k=0;%k<9&&getSelectedPlayerId()!=ID;%k++) cycleSelectedPlayer(); addWaitOrder(1000);` as its own run() per unit.
- Unverified: whether addWaitOrder really attached to the intended waypoint (no plan getter exists). addMoveAimOrder / MoveAimOrder2 args never decoded.
- `Plan` object is a Prefab named plan, not the editor; Plan.selectMyUnit etc. are unknown commands. planNavigateTo paths around walls; planAddWaypoint is a straight line.
- DSO decode via ident table was unreliable; abandoned (helper scripts in %TEMP%: dso.py, dsomod.py, dso2.py).

## 5. Left to try
- Aim lane: call addMoveAimOrder / addFocusAimOrder per unit (same select-then-add pattern); find their args by probing, then soak 20.
- Verify the hold really attaches (compare unit positions turn to turn with and without it).
- Brains differ little: draws dominate (15 of 20 hit the turn cap). Try a win-oriented plan (focus fire on one Charon unit, cover then push) instead of holds, measured over 20 matches per arm; 3 matches cannot separate noise.
- Port SwatMinds ideas that need no order types: formation spacing, staggered entry.
