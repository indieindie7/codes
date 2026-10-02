# Remote Control at login

`start-remote-control.ps1` starts Claude Code's Remote Control server (`claude remote-control`)
in this repository whenever you log in to Windows. The PC is then reachable from the Claude app
(phone, or claude.ai/code) every morning, even after it shut down for the night, without
waking old chats.

## Install (once, on the PC)

1. In a terminal in the repo folder, run `claude remote-control` once by hand and accept every
   prompt it shows (trusting the folder, enabling Remote Control). Then close it. The login
   window starts minimized, so a first-time question there would wait unseen and the session
   would never come up.
2. In the repo folder:

       powershell -ExecutionPolicy Bypass -File tools\remote-control\start-remote-control.ps1 -Install

   This makes a shortcut in your Startup folder, *Claude Remote Control*, that runs the script
   minimized at login. `-Uninstall` removes it.

Close its window to stop it for the rest of that login.

## What it does

- Waits until the internet is reachable (up to 5 minutes), since it starts at login.
- Runs `claude remote-control --name "<computer name> codes"` in the repo folder. In the Claude
  app that shows up as a session you can type into, and you can start more from there.
- If it stops (network drop, update, crash), it starts it again: after 10 s, then waiting longer
  each time it stops quickly, up to 10 minutes.
- Writes what it does to `%LOCALAPPDATA%\claude-remote-control-startup.log`.

Options: `-PermissionMode acceptEdits` (or another mode) for the sessions it starts,
`-Name "..."`, `-Dir <folder>`.

## Two scripts, two jobs

- **This one makes sure the PC is reachable.** Each morning it creates a NEW session; it does
  not bring back the existing desktop-app chats. (`--continue` doesn't help: it only reattaches
  to a session from roughly the last 4 hours, and the PC is off overnight.) What carries over
  lives in the repo: `SESSION_NOTES.md` (state and checklist) and `HANDOFF.md` (messages between
  sessions).
- **`tools/wake-chats/wake-chats.ps1` (from the PC session) is the only way to revive the old
  chats** ("unreal modding", "advent rising modding", ...), by clicking through the app.

Leave the permission mode at its default, so the sessions it starts ask on the phone before
doing things.

Tested here only as far as possible without Windows: the script parses in PowerShell 7, and a
dry run with a stand-in `claude` showed the start, restart and back-off. The shortcut, the login
start and the real `claude remote-control` have not run yet.
