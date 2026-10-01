U2TestHub - console commands for testing mods in any Unreal II level
===================================================================

A developer tool: a "live game doc" you drive from the console (~ key).
Stations so far: lights and shadows. More (enemies, weapons, hover bike,
squad, level teleports) can be added the same way.

  hub help                          list the commands
  hub view [on|off]                 third-person camera + god mode
  hub lamp [bright] [angle] [dist]  bright test lamp in front of you
                                    (defaults 220, 45 degrees up, 200 away)
  hub lamp clear                    remove the test lamps
  hub dummy                         a marine to look at
  hub shadows mod|stock|off         U2SoftShadows / the game's own / none
  hub info                          your shadows: light, darkness, fade
  hub probe                         log frame hitches (needs U2Hover)
  hub goto MAP                      open a level, e.g. hub goto M08A1

Output goes on screen and to Unreal2.log ("Hub:" lines), so scripted U2Pilot
runs can use the same commands (step: console hub lamp 220 45 200).

INSTALL: add U2TestHub.HubMutator to the Mutator= line in User.ini's
[DefaultPlayer] section. It adds itself to the player's ExecManagers list
(the game's own hook for extra console commands), replacing nothing.
Needs U2SoftShadows for the shadow commands.
