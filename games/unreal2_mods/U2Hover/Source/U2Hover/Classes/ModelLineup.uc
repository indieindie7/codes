//=============================================================================
// ModelLineup - a look at character models in game: two rows of friendly
// marines, each wearing one model - FrontModels in front of the player,
// BackModels behind. They're given no orders, so they mostly stand still.
// Only runs when added to the URL:
//     open HoverTest?Mutator=U2Hover.ModelLineup
//=============================================================================
class ModelLineup extends Mutator;

var() array<string> FrontModels, BackModels;
var bool bDone;

function SpawnRow(Pawn Viewer, array<string> Models, float Side)
{
	local vector X, Y, Z, Spot;
	local rotator R;
	local Pawn P;
	local Mesh M;
	local int i;

	R.Yaw = Viewer.Rotation.Yaw;
	GetAxes(R, X, Y, Z);
	R.Yaw += 32768 * int(Side > 0);        // face the player
	for (i = 0; i < Models.Length; i++)
	{
		Spot = Viewer.Location + X * 520 * Side + Y * (i - (Models.Length - 1) / 2.0) * 130 * Side + vect(0,0,1) * 30;
		P = Spawn(class'U2MarineLight', , , Spot, R);
		if (P == None)
		{
			log("ModelLineup: no room for" @ Models[i]);
			continue;
		}
		M = Mesh(DynamicLoadObject(Models[i], class'Mesh'));
		if (M != None)
			P.Mesh = M;
		log("ModelLineup:" @ i @ Models[i] @ "->" @ P.Mesh);
	}
}

simulated event Tick(float Delta)
{
	local Controller C;

	if (bDone)
		return;
	for (C = Level.ControllerList; C != None; C = C.NextController)
		if (PlayerController(C) != None && C.Pawn != None)
		{
			bDone = true;
			SpawnRow(C.Pawn, FrontModels, 1);
			SpawnRow(C.Pawn, BackModels, -1);
			Disable('Tick');
			return;
		}
}

defaultproperties
{
	FrontModels(0)="GlmCharactersG.Izarian"
	FrontModels(1)="GlmCharactersG.Izarian_NoArmor"
	FrontModels(2)="GlmCharactersG.Izarian_Bald"
	FrontModels(3)="GlmCharactersG.Izarian_Armor01"
	FrontModels(4)="GlmCharactersG.Izarian_ArmorFull"
	FrontModels(5)="GlmCharactersG.Izarian_ArmorFullWithRifle"
	BackModels(0)="GlmCharactersG.FrankSkaarjJogger"
	BackModels(1)="GlmCharactersG.FrankMarineStumpy"
	BackModels(2)="GlmCharactersG.FrankMarineFilth"
	BackModels(3)="GlmCharactersG.FrankMarineSwill"
	BackModels(4)="GlmCharactersG.FrankGimp"
}
