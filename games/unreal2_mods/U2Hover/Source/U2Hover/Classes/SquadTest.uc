//=============================================================================
// SquadTest - which character models can run on the marine combat AI?
// Spawns a row of light marines in front of the player, each wearing a
// different model (crew members, and a named marine as the control), then
// orders them all to follow the player. Only runs when added to the URL:
//     open HoverTest?Mutator=U2Hover.HoverMutator,U2Hover.SquadTest
//=============================================================================
class SquadTest extends Mutator;

var() array<string> Models;
var bool bDone;

simulated event Tick(float Delta)
{
	local Controller C;
	local PlayerController PC;
	local Pawn P;
	local Mesh M;
	local vector X, Y, Z, Spot;
	local rotator R;
	local int i;

	if (bDone)
		return;
	for (C = Level.ControllerList; C != None && PC == None; C = C.NextController)
		if (PlayerController(C) != None && C.Pawn != None)
			PC = PlayerController(C);
	if (PC == None)
		return;
	bDone = true;

	R.Yaw = PC.Pawn.Rotation.Yaw;
	GetAxes(R, X, Y, Z);
	R.Yaw += 32768;                             // face the player
	for (i = 0; i < Models.Length; i++)
	{
		Spot = PC.Pawn.Location + X * 700 + Y * (i - (Models.Length - 1) / 2.0) * 160 + vect(0,0,1) * 40;
		P = Spawn(class'U2MarineLight', , , Spot, R);
		if (P == None)
		{
			log("SquadTest: no room for" @ Models[i]);
			continue;
		}
		M = Mesh(DynamicLoadObject(Models[i], class'Mesh'));
		if (M != None)
			P.Mesh = M;
		log("SquadTest:" @ P @ "wears" @ Models[i] @ "->" @ P.Mesh @ "controller" @ P.Controller);
		if (U2NPCControllerBasic(P.Controller) != None)
			U2NPCControllerBasic(P.Controller).SetOrders('follow', PC.Pawn, 0, PC, false);
	}
	Disable('Tick');
}

defaultproperties
{
	Models(0)="GlmCharactersG.AidaWithGun"
	Models(1)="GlmCharactersG.Aida"
	Models(2)="GlmCharactersG.Isaak"
	Models(3)="GlmCharactersG.Neban"
	Models(4)="GlmCharactersG.NebanFull"
	Models(5)="GlmCharactersG.MarineLight_KovacsBlue"
}
