//=============================================================================
// ModArmourGrid - the test for "where the plates are" (ARMOUR.md): a grid of rays from the camera
// across the nearest enemy's body, each one classified by ModArmor (armour or flesh), logged as
// "armourgrid: ..." next to the native's "armour hit: ..." lines; with a damage, each ray is a
// real hit too (TakeDamage at the aim point, so sparks/blood and the factor show), then a
// screenshot. Spawned by ModArmor when [AdventMod.ModArmor] GridTest="cols rows damage delay"
// is set (the test harness writes it; it is empty in play). tools in the scratchpad draw the
// hit points over the ref-pose render and the screenshot.
//=============================================================================
class ModArmourGrid extends Info;

var ModArmor Armor;
var int Cols, Rows, Damage;
var float Delay;

event Tick(float DeltaTime)
{
	Delay -= DeltaTime;
	if (Delay > 0)
		return;
	Run();
	Destroy();
}

function PlayerController PC()
{
	local PlayerController C;

	ForEach DynamicActors(class'PlayerController', C)
		return C;
	return None;
}

function Run()
{
	local Pawn P, Best;
	local PlayerController C;
	local int i, j, n, Arm;
	local vector O, T, D, Right;
	local class<DamageType> Ty;

	C = PC();
	if (C == None || C.Pawn == None || Armor == None)
	{
		class'ModSettings'.static.Note("armourgrid: no player or no ModArmor");
		return;
	}
	ForEach DynamicActors(class'Pawn', P)
		if (P != C.Pawn && P.Health > 0 && !P.IsA('Vehicle') && (Best == None || VSize(P.Location - C.Pawn.Location) < VSize(Best.Location - C.Pawn.Location)))
			Best = P;
	if (Best == None)
	{
		class'ModSettings'.static.Note("armourgrid: no enemy near");
		return;
	}
	O = C.GetCameraPosition();
	class'ModSettings'.static.Note("armourcam: " $ O $ " " $ C.GetCameraRotation() $ " fov " $ C.FovAngle $ " target " $ Best $ " at " $ Best.Location $ " rot " $ Best.Rotation $ " r " $ Best.CollisionRadius $ " h " $ Best.CollisionHeight $ " mesh " $ Best.Mesh);
	Right = Normal((Best.Location - O) Cross vect(0,0,1));
	Ty = class<DamageType>(DynamicLoadObject("EonWeapons.dmgType_HumanPistolFire", class'Class'));
	for (j = 0; j < Rows; j++)
		for (i = 0; i < Cols; i++)
		{
			T = Best.Location + Right * Best.CollisionRadius * 1.2 * (2.0 * i / FMax(Cols - 1, 1) - 1.0) + vect(0,0,1) * Best.CollisionHeight * 1.05 * (2.0 * j / FMax(Rows - 1, 1) - 1.0);
			D = Normal(T - O);
			if (Armor.Probe(Best, O, D))
			{
				n++;
				if (Armor.LastClass == 2)
					Arm++;
			}
			class'ModSettings'.static.Note("armourgrid: " $ i $ " " $ j $ " class " $ Armor.LastClass $ " aim " $ T);
			if (Damage > 0 && Armor.LastClass > 0 && Ty != None)
				Best.TakeDamage(Damage, C.Pawn, T, D * 20000, Ty);
		}
	class'ModSettings'.static.Note("armourgrid: " $ n $ " of " $ Cols * Rows $ " rays met the body, " $ Arm $ " on armour (" $ Best $ ", health " $ Best.Health $ ")");
}

defaultproperties
{
     Cols=5
     Rows=8
     Delay=3.0
}
