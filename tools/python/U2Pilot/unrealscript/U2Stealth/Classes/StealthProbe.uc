//=============================================================================
// Development probe: logs the perception values the engine uses for stealth
// (enemy sight/hearing, player visibility/noise) so tuning starts from the
// game's real numbers. Add with Mutator=U2Stealth.StealthProbe.
//=============================================================================
class StealthProbe extends Mutator;

var array<class> Seen;
var int Ticks;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	Log("StealthProbe: footsteps MakeNoiseVolumeMultiplier="$class'MoveTextureHelperGeneric'.default.MakeNoiseVolumeMultiplier
		$" RunningSoundSpeed="$class'MoveTextureHelperGeneric'.default.RunningSoundSpeed
		$" WalkVolumeMultiplier="$class'MoveTextureHelperGeneric'.default.WalkVolumeMultiplier
		$" BaseVolume="$class'MoveTextureHelperGeneric'.default.BaseVolume);
	SetTimer(1.0, true);
}

function bool Known(class C)
{
	local int i;

	for (i = 0; i < Seen.Length; i++)
		if (Seen[i] == C)
			return true;
	Seen[Seen.Length] = C;
	return false;
}

event Timer()
{
	local Pawn P;

	Ticks++;
	foreach DynamicActors(class'Pawn', P)
	{
		if (P.bDeleteMe || P.Controller == None)
			continue;
		if (PlayerController(P.Controller) != None)
		{
			if (!Known(P.Class))
				Log("StealthProbe: PLAYER "$P.Class$" Visibility="$P.Visibility$" SeenRadius="$P.SeenRadius
					$" SeenRadiusNoFOV="$P.SeenRadiusNoFOV$" SoundDampening="$P.SoundDampening
					$" GroundSpeed="$P.GroundSpeed$" WalkingPct="$P.WalkingPct);
			Log("StealthProbe: t="$Ticks$" speed="$int(VSize(P.Velocity))$" stance="$P.GetStance()$" walking="$P.bIsWalking);
		}
		else if (!Known(P.Class))
			Log("StealthProbe: NPC "$P.Class$" (ctrl "$P.Controller.Class$") SightRadius="$P.SightRadius
				$" PeripheralVision="$P.PeripheralVision$" SeeOtherOdds="$P.SeeOtherOdds
				$" HearingThreshold="$P.HearingThreshold$" Alertness="$P.Alertness
				$" LOS/Zone/Adj/Muffled/Corner="$P.bLOSHearing$"/"$P.bSameZoneHearing$"/"$P.bAdjacentZoneHearing
				$"/"$P.bMuffledHearing$"/"$P.bAroundCornerHearing);
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
}
