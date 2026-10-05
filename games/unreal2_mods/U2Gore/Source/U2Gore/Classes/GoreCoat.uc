//=============================================================================
// Blood on a character. GoreManager gives a body one when blood lands on it (its own, or a
// spurt from someone next to it) and adds to it; the more blood, the heavier.
// Ported from AdventMod's ModBloodCoat.
//
// Each of the body's skins is swapped for a Combiner: its own texture times a blood texture
// (2x, so the blood texture's 50% grey leaves the skin as it is), over the same texture
// coordinates, so the stains sit where they are on each part of the body and move with it.
// While it wears a coat the body is drawn without its own Shader (its sheen).
//
// Only a body that lists its skins (Pawn.Skins) can wear one: script can't ask a mesh for
// its materials. Characters that use their mesh's own materials are left alone for now.
// The player's coat wears off with time; others keep theirs until the body is removed.
//=============================================================================
class GoreCoat extends Info;

var GoreManager Gore;
var Pawn Wearer;
var int Kind;              // whose blood: 1 red, 2 green
var float Amount;          // 0..2.5
var int Level;             // the blood texture in use (0, 1, 2)
var int Slots;
var Material OwnSkin[8];   // what the body wore
var Combiner Mix[8];

// the plain picture under a skin's material, if there is one
static function Material PlainOf(Material M)
{
	local int Depth;

	for (Depth = 0; Depth < 4 && M != None; Depth++)
	{
		if (Texture(M) != None)
			return M;
		if (Shader(M) != None)
			M = Shader(M).Diffuse;
		else if (FinalBlend(M) != None)
			M = FinalBlend(M).Material;
		else
			return None;
	}
	return None;
}

// false: this body can't wear one
function bool Wear(Pawn P, int BloodKind, float A)
{
	local Material Plain[8];
	local int i, Mixed;

	Slots = Min(P.Skins.Length, 8);
	if (Slots == 0)
		return false;
	for (i = 0; i < Slots; i++)
	{
		Plain[i] = PlainOf(P.Skins[i]);
		if (Plain[i] != None)
			Mixed++;
	}
	if (Mixed == 0)
		return false;
	Wearer = P;
	Kind = BloodKind;
	Amount = FMin(A, 2.5);
	for (i = 0; i < Slots; i++)
	{
		OwnSkin[i] = P.Skins[i];
		if (Plain[i] == None)
			continue;                     // a slot that can't be mixed stays as it is
		Mix[i] = new(None) class'Combiner';
		Mix[i].Material1 = Plain[i];
		Mix[i].CombineOperation = CO_Multiply;
		Mix[i].Modulate2X = true;
	}
	Level = -1;
	Update();
	for (i = 0; i < Slots; i++)
		if (Mix[i] != None)
			P.Skins[i] = Mix[i];
	return true;
}

function More(float A)
{
	Amount = FMin(Amount + A, 2.5);
	Update();
}

function Update()
{
	local int Want, i;

	if (Amount > 1.3)
		Want = 2;
	else if (Amount > 0.55)
		Want = 1;
	if (Want == Level)
		return;
	Level = Want;
	for (i = 0; i < Slots; i++)
		if (Mix[i] != None)
			Mix[i].Material2 = Gore.CoatMaterial(Kind, Level);
}

function TakeOff()
{
	local int i;

	if (Wearer != None && !Wearer.bDeleteMe)
		for (i = 0; i < Slots && i < Wearer.Skins.Length; i++)
			if (Mix[i] != None && Wearer.Skins[i] == Mix[i])
				Wearer.Skins[i] = OwnSkin[i];
	for (i = 0; i < 8; i++)
		Mix[i] = None;
}

event Tick(float DeltaTime)
{
	if (Wearer == None || Wearer.bDeleteMe || Gore == None)
	{
		Destroy();
		return;
	}
	if (Wearer.IsRealPlayer())
	{
		Amount -= DeltaTime / 45;          // the player's wears off
		if (Amount <= 0.05)
			Destroy();
		else
			Update();
	}
}

event Destroyed()
{
	TakeOff();
	Super.Destroyed();
}

defaultproperties
{
	RemoteRole=ROLE_None
}
