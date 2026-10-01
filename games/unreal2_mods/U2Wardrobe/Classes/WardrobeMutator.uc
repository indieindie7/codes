//=============================================================================
// U2Wardrobe - dress Dalton in any character model. Press F6 for the menu,
// or use the console:
//     wardrobe wear NAME     put on an outfit (names as in the menu)
//     wardrobe next / prev   cycle through them
//     wardrobe view          third person on/off, to see yourself
//     wardrobe list          print the outfits
// The choice is saved in System\U2Wardrobe.ini and put on again in every level.
//
// Outfits are Golem meshes: the game's own characters, and anything imported
// with tools\python\U2Golem (UT2004 characters share the marines' animations).
// The menu (UIScripts\Wardrobe.ui) is generated from the same list by
// make_wardrobe_ui.py.
//=============================================================================
class WardrobeMutator extends Mutator config(U2Wardrobe);

var config string Outfit;                 // label of the outfit worn ("" = the game's own Dalton)
var config array<string> Labels;          // what the menu shows
var config array<string> Meshes;          // Golem mesh for each label, e.g. GlmMalcolmG.Malcolm

var config bool bFirstPersonBody;      // see your own body in first person (FirstPersonBody)

var Mesh Wanted;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	LoadWanted();
	SetTimer(0.25, true);     // cutscene stand-ins are spawned mid-level
}

function int Find(string L)
{
	local int i;
	for (i = 0; i < Labels.Length; i++)
		if (Caps(Labels[i]) == Caps(L))
			return i;
	return -1;
}

function LoadWanted()
{
	local int i;
	Wanted = None;
	i = Find(Outfit);
	// the first outfit is the game's own Dalton: nothing to put on (his armour on
	// missions, off-duty clothes on the Atlantis, as the game picks)
	if (i > 0)
		Wanted = Mesh(DynamicLoadObject(Meshes[i], class'Mesh', true));
	if (i > 0 && Wanted == None)
		Log("U2Wardrobe: can't load "$Meshes[i]$" for "$Labels[i]);
}

// Dalton as the player, or as the stand-in the game uses in its cutscenes
// (CutscenePlayer and its subclasses, or any character wearing one of his models)
function bool IsDalton(Pawn P, PlayerController PC)
{
	local string M;

	if (P == None || P.bDeleteMe)
		return false;
	if (PC != None && P == PC.Pawn)
		return true;
	if (P.IsA('CutscenePlayer'))
		return true;
	M = string(P.default.Mesh);
	return M == "GlmCharactersG.PlayerGame" || M == "GlmCharactersG.PlayerAtlantis";
}

// put the outfit on (the game's skins for Dalton are dropped: they'd paint his
// textures over the new model), or give the game's own Dalton back
function Dress(Pawn P)
{
	if (P == None)
		return;
	if (Wanted != None)
	{
		if (P.Mesh != Wanted)
		{
			P.Mesh = Wanted;
			P.Skins.Length = 0;
		}
	}
	else if (P.Mesh != P.default.Mesh)
	{
		P.Mesh = P.default.Mesh;
		P.Skins = P.default.Skins;
	}
}

function DressAll(PlayerController PC)
{
	local Pawn P;

	foreach DynamicActors(class'Pawn', P)
		if (IsDalton(P, PC))
			Dress(P);
}

function Wear(string L, PlayerController PC)
{
	local int i;
	i = Find(L);
	if (i < 0)
	{
		PC.ClientMessage("wardrobe: no outfit called "$L);
		return;
	}
	Outfit = Labels[i];
	SaveConfig();
	LoadWanted();
	if (Wanted == None && i > 0)
	{
		PC.ClientMessage("wardrobe: "$Labels[i]$" isn't installed ("$Meshes[i]$")");
		return;
	}
	DressAll(PC);
	PC.ClientMessage("Dalton is now wearing: "$Outfit);
	Log("U2Wardrobe: wearing "$Outfit$" ("$Meshes[i]$")");
}

function Step(int Dir, PlayerController PC)
{
	local int i;
	i = Find(Outfit);
	if (i < 0)
		i = 0;
	else
		i = (i + Dir + Labels.Length) % Labels.Length;
	Wear(Labels[i], PC);
}

function SetBody(bool bOn, PlayerController PC)
{
	local FirstPersonBody B;

	bFirstPersonBody = bOn;
	SaveConfig();
	if (!bOn)
		foreach DynamicActors(class'FirstPersonBody', B)
			B.Destroy();
	PC.ClientMessage("first-person body: "$bOn);
}

function GiveBody(PlayerController PC)
{
	local FirstPersonBody B;

	foreach DynamicActors(class'FirstPersonBody', B)
		if (B.PC == PC)
			return;
	B = Spawn(class'FirstPersonBody', PC);     // owned by the controller: ticks after it (no aim lag)
	if (B != None)
		B.Start(PC);
}

function List(PlayerController PC)
{
	local int i;
	for (i = 0; i < Labels.Length; i++)
		PC.ClientMessage(Labels[i]$" = "$Meshes[i]);
}

// players come and go (level start, respawn): give each the command and the outfit
event Timer()
{
	local Controller C;
	local PlayerController PC;
	local WardrobeCommands W;
	local int i;
	local bool bHas;

	for (C = Level.ControllerList; C != None; C = C.NextController)
	{
		PC = PlayerController(C);
		if (PC == None)
			continue;
		bHas = false;
		for (i = 0; i < PC.ExecManagers.Length; i++)
			if (WardrobeCommands(PC.ExecManagers[i]) != None)
				bHas = true;
		if (!bHas)
		{
			W = new(PC) class'WardrobeCommands';
			W.WM = Self;
			W.PC = PC;
			PC.ExecManagers[PC.ExecManagers.Length] = W;
		}
		DressAll(PC);
		if (bFirstPersonBody)
			GiveBody(PC);
	}
}

defaultproperties
{
	RemoteRole=ROLE_None
	bFirstPersonBody=True
	// OUTFITS-BEGIN (generated by make_wardrobe_ui.py)
	Labels(0)="Dalton"
	Meshes(0)="GlmCharactersG.PlayerGame"
	Labels(1)="Malcolm (UT2004)"
	Meshes(1)="GlmMalcolmG.Malcolm"
	Labels(2)="Merc (UT2004)"
	Meshes(2)="GlmMercMaleAG.MercMaleA"
	Labels(3)="Merc woman (UT2004)"
	Meshes(3)="GlmMercFemaleAG.MercFemaleA"
	Labels(4)="Egyptian (UT2004)"
	Meshes(4)="GlmEgyptMaleAG.EgyptMaleA"
	Labels(5)="Necris (UT2004)"
	Meshes(5)="GlmNightMaleAG.NightMaleA"
	Labels(6)="Juggernaut (UT2004)"
	Meshes(6)="GlmJuggMaleAG.JuggMaleA"
	// OUTFITS-END
}
