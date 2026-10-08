# Hooks for ModPlayerBlood (blood on the player's hands/weapon + lens drops)

Only one hook is needed: ModPlayerBlood finds ModGore by itself, reads the player's coat
(`Gore.CoatOf`) and ModScreenBlood's splats, and adds itself to the GameRules chain.

## Classes/ModMutator.uc

1. With the other `var`s at the top:

```unrealscript
var ModPlayerBlood PlayerBlood;
```

2. Right after the line that spawns ModGore (`Gore = Spawn(class'ModGore');`):

```unrealscript
	if (!class'ModSettings'.default.bGraphicsOnly && PlayerBlood == None && PC != None && Level.Game != None && !Level.Game.IsInFrontEnd)
		PlayerBlood = Spawn(class'ModPlayerBlood');
```

## Optional (README, owned by the other job)

- Hands: `hands=1`, `handsparams=radius pattern opacity gain` (U2Shaders.ini); `[AdventMod.ModPlayerBlood]`
  bHands, FadeSecs=150, DrySecs=45, ArmRadius, HandLength, WeaponRadius, KillReach.
- Lens: `lens=1` (needs `post=1`), `lensparams=strength reach life size`, `lensfx=refraction tint highlight opacity`;
  `[AdventMod.ModPlayerBlood]` bLens, bReplaceScreenBlood, LensNear. With lens=1 the lens replaces
  ModScreenBlood's HUD splats (they stay when the layer is off or older).
