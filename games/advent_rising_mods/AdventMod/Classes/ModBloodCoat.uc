//=============================================================================
// ModBloodCoat - blood on a character. ModGore gives a body one when blood lands on it (its
// own, or a spurt from someone next to it) and adds to it; the more blood, the heavier.
//
// Each of the body's skins is swapped for a Combiner: its own texture times a blood texture
// (2x, so the blood texture's 50% grey leaves the skin as it is), over the same texture
// coordinates, so the stains sit where they are on each part of the body and move with it.
// (A projector riding on the body, the way the floor decals work, tinted the whole body one
// colour: on skinned meshes its texture coordinates come out as one point.) While it wears a
// coat the body is drawn without the game's own skin shader (its sheen).
//
// Which skins a body wears: its own Skins if it sets any, else its mesh's (ModSkins, a table:
// script can't ask a mesh). A body with neither is left alone. The player's coat wears off
// with time; others keep theirs until the body is removed or the game reuses the pawn.
//=============================================================================
class ModBloodCoat extends Info
	config(AdventMod);

var ModGore Gore;
var Pawn Wearer;
var int Kind;              // whose blood: 1 red, 2 purple
var float Amount;          // 0..2.5
var int Level;             // the blood texture in use (0, 1, 2)
var bool bWasDead;
var int Slots;
var Material OwnSkin[4];   // what the body wore
var Combiner Mix[4];
var bool bNoSkins;         // the body set no skins of its own (it gets none back)
// fresh blood runs: for DripTime after a hit the coat is the blood texture times drip
// streaks that a TexMatrix pans down the body, then the plain coat again
var TexMatrix Pan;
var Combiner DripMix;
var float DripT, DripPhase;
var config float DripTime, DripSpeed;

static function Material PlainOf(Material M)
{
	if (AdventShaderMaterial(M) != None)
		return AdventShaderMaterial(M).Diffuse;
	if (PSSkinShader(M) != None)
		return PSSkinShader(M).Diffuse;
	if (Texture(M) != None)
		return M;
	return None;
}

// false: this body can't wear one
function bool Wear(Pawn P, int BloodKind, float A)
{
	local Material Skin[4], Plain[4];
	local int i, Entry;

	if (P.Skins.Length > 0 && P.Skins[0] != None)
	{
		Slots = Min(P.Skins.Length, 4);
		for (i = 0; i < Slots; i++)
			Skin[i] = P.Skins[i];
	}
	else
	{
		Entry = class'ModSkins'.static.Find(P.Mesh);
		if (Entry < 0)
			return false;
		bNoSkins = true;
		for (i = 0; i < 4; i++)
		{
			if (class'ModSkins'.default.Meshes[Entry].Skin[i] == "")
				break;
			Skin[i] = Material(DynamicLoadObject(class'ModSkins'.default.Meshes[Entry].Skin[i], class'Material'));
			Slots = i + 1;
		}
	}
	for (i = 0; i < Slots; i++)
	{
		Plain[i] = PlainOf(Skin[i]);
		if (Plain[i] == None)
			return false;                 // a slot that can't be mixed: the body stays as it is
	}
	if (Slots == 0)
		return false;
	Wearer = P;
	Kind = BloodKind;
	Amount = FMin(A, 2.5);
	for (i = 0; i < Slots; i++)
	{
		OwnSkin[i] = Skin[i];
		Mix[i] = new(None) class'Combiner';
		Mix[i].Material1 = Plain[i];
		Mix[i].CombineOperation = CO_Multiply;
		Mix[i].Modulate2X = true;
	}
	Level = -1;
	Update();
	for (i = 0; i < Slots; i++)
		P.Skins[i] = Mix[i];
	return true;
}

function More(float A)
{
	Amount = FMin(Amount + A, 2.5);
	Update();
	if (A > 0.15)
		Drip();
}

function Drip()
{
	local int i;

	if (Gore == None || Gore.DripMaterial(Kind) == None || DripTime <= 0)
		return;
	if (Pan == None)
	{
		Pan = new(None) class'TexMatrix';
		Pan.Material = Gore.DripMaterial(Kind);
		DripMix = new(None) class'Combiner';
		DripMix.Material2 = Pan;
		DripMix.CombineOperation = CO_Multiply;
		DripMix.Modulate2X = true;
	}
	DripMix.Material1 = Gore.CoatMaterial(Kind, Max(Level, 0));
	for (i = 0; i < Slots; i++)
		if (Mix[i] != None)
			Mix[i].Material2 = DripMix;
	DripT = DripTime;
	SetTimer(0.04, true);
}

// the streaks pan down (texture V) while the drip lasts; then the plain coat comes back
event Timer()
{
	local int i;

	if (Pan == None)
	{
		SetTimer(0, false);
		return;
	}
	DripT -= 0.04;
	DripPhase += 0.04 * DripSpeed;
	if (DripPhase > 1)
		DripPhase -= 1;
	Pan.Matrix.WPlane.Y = -DripPhase;
	if (DripT <= 0)
	{
		for (i = 0; i < Slots; i++)
			if (Mix[i] != None)
				Mix[i].Material2 = Gore.CoatMaterial(Kind, Max(Level, 0));
		SetTimer(0, false);
	}
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
	if (DripMix != None)
		DripMix.Material1 = Gore.CoatMaterial(Kind, Level);
	for (i = 0; i < Slots; i++)
		if (Mix[i] != None && DripT <= 0)
			Mix[i].Material2 = Gore.CoatMaterial(Kind, Level);
}

function TakeOff()
{
	local int i;

	if (Wearer != None && !Wearer.bDeleteMe && Mix[0] != None && Wearer.Skins.Length > 0 && Wearer.Skins[0] == Mix[0])
	{
		if (bNoSkins)
			Wearer.Skins.Length = 0;
		else
			for (i = 0; i < Slots && i < Wearer.Skins.Length; i++)
				Wearer.Skins[i] = OwnSkin[i];
	}
	for (i = 0; i < 4; i++)
		Mix[i] = None;
}

event Tick(float DeltaTime)
{
	if (Wearer == None || Wearer.bDeleteMe || Gore == None)
	{
		Destroy();
		return;
	}
	// the game brought the pawn back to life (it reuses its dead): clean again
	if (Wearer.Health <= 0)
		bWasDead = true;
	else if (bWasDead)
	{
		Destroy();
		return;
	}
	if (Wearer.IsHumanControlled())
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
     DripTime=2.500000
     DripSpeed=0.350000
}
