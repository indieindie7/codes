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

var config bool bFirstPersonBody;      // see your own body in first person (BodyController + FirstPersonBody)
var config bool bMatchHeight;          // scale a new outfit to the height of the Dalton it replaces

// measured heights of every model, standing, at DrawScale 1: the head and left
// foot bones relative to the actor's drawn origin ("wardrobe measure" fills them)
var config array<string> CalMeshes;
var config array<float> CalHeads, CalFeet;
var array<string> MeasureList;         // "wardrobe measure" in progress: models still to measure
var int MeasureStep;
var Pawn MeasurePawn;
var Mesh MeasureOldMesh;
var PlayerController MeasurePC;

// a dressed character's original size, and whether its outfit has been fitted yet
struct Fit
{
	var Pawn P;
	var float Head, Foot;                // the original model's head and foot bone heights (world)
	var float Scale;                     // its DrawScale
	var vector PrePivot;
	var Mesh Orig;                       // the model it replaced
	var bool bFitted;
};
var array<Fit> Fits;

var Mesh Wanted;
var Pawn PhotoPawn;                    // "wardrobe photo": a model stood in front of the camera

event PostBeginPlay()
{
	Super.PostBeginPlay();
	LoadWanted();
	// own body in first person: the game spawns players from this class (before
	// anyone logs in, which comes after the mutators); only the game's usual
	// controller is replaced, never another mod's
	if (bFirstPersonBody && Level.Game != None && (Level.Game.PlayerControllerClass == None
		|| Level.Game.PlayerControllerClass == class'U2PlayerNetTestController')
		&& Level.Game.PlayerControllerClassName ~= "U2.U2PlayerNetTestController")
		Level.Game.PlayerControllerClass = class'BodyController';
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

	if (P == None || P.bDeleteMe || P == PhotoPawn)
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
	local int i;

	if (P == None)
		return;
	i = FitIndex(P);
	if (Wanted != None)
	{
		if (P.Mesh != Wanted)
		{
			// measure the model being replaced (only the game's own: an outfit
			// change keeps the first measurement)
			if (i < 0 && bMatchHeight)
			{
				i = Fits.Length;
				Fits.Length = i + 1;
				Fits[i].P = P;
				Fits[i].Scale = P.DrawScale;
				Fits[i].PrePivot = P.PrePivot;
				Fits[i].Orig = P.Mesh;
				if (!Measure(P, Fits[i].Head, Fits[i].Foot))
					Fits[i].Head = -1;
			}
			else if (i >= 0)
			{
				P.SetDrawScale(Fits[i].Scale);
				P.PrePivot = Fits[i].PrePivot;
			}
			if (i >= 0)
				Fits[i].bFitted = false;
			P.Mesh = Wanted;
			P.Skins.Length = 0;
			if (i >= 0 && FitMeasured(i))
				Fits[i].bFitted = true;
		}
		else if (i >= 0 && !Fits[i].bFitted)
			FitHeight(i);           // a tick later: the new model's bones are posed now
	}
	else if (P.Mesh != P.default.Mesh)
	{
		P.Mesh = P.default.Mesh;
		P.Skins = P.default.Skins;
		if (i >= 0)
		{
			P.SetDrawScale(Fits[i].Scale);
			P.PrePivot = Fits[i].PrePivot;
			Fits.Remove(i, 1);
		}
	}
}

function int FitIndex(Pawn P)
{
	local int i;

	for (i = Fits.Length - 1; i >= 0; i--)
		if (Fits[i].P == None || Fits[i].P.bDeleteMe)
			Fits.Remove(i, 1);
	for (i = 0; i < Fits.Length; i++)
		if (Fits[i].P == P)
			return i;
	return -1;
}

// head and foot bone heights of P's current model (world space)
function bool Measure(Pawn P, out float Head, out float Foot)
{
	local int H, F;

	H = P.MeshGetNodeNamed("Merc Head");
	F = P.MeshGetNodeNamed("Merc L Foot");
	if (H == 0 || F == 0)
		return false;
	Head = P.MeshNodeGetTranslation(H, MESHNODEREL_World).Z;
	Foot = P.MeshNodeGetTranslation(F, MESHNODEREL_World).Z;
	return Head - Foot > 10;
}

// the measured head and foot of model M (per unit of DrawScale), if known
function bool Measured(Mesh M, out float Head, out float Foot)
{
	local int i;
	local string S;

	S = string(M);
	for (i = 0; i < CalMeshes.Length; i++)
		if (CalMeshes[i] ~= S && i < CalHeads.Length && i < CalFeet.Length)
		{
			Head = CalHeads[i];
			Foot = CalFeet[i];
			return Head - Foot > 10;
		}
	return false;
}

// from the measurements: the new model exactly as tall as the Dalton it
// replaced (head to foot, standing), its feet where his were. Doesn't depend on
// the pose either is in at the moment (a cutscene can dress him mid-gesture).
function bool FitMeasured(int i)
{
	local Pawn P;
	local float H0, F0, H1, F1, S;

	P = Fits[i].P;
	if (!Measured(Fits[i].Orig, H0, F0) || !Measured(P.Mesh, H1, F1))
		return false;
	S = Fits[i].Scale * (H0 - F0) / (H1 - F1);
	P.SetDrawScale(S);
	P.PrePivot = Fits[i].PrePivot + vect(0,0,1) * (Fits[i].Scale * F0 - S * F1);
	Log("U2Wardrobe: fitted "$P.Name$" ("$Fits[i].Orig$" -> "$P.Mesh$") scale "$Fits[i].Scale$" -> "$S);
	return true;
}

// "wardrobe measure": put each model on the player in turn (seen from behind,
// so it is drawn and its bones posed), standing still, and record its height
function StartMeasure(PlayerController PC)
{
	local int i;

	if (PC.Pawn == None)
		return;
	MeasureList.Length = 0;
	MeasureList[0] = "GlmCharactersG.PlayerGame";
	MeasureList[1] = "GlmCharactersG.PlayerAtlantis";
	for (i = 1; i < Meshes.Length; i++)
		MeasureList[MeasureList.Length] = Meshes[i];
	MeasurePC = PC;
	MeasurePawn = PC.Pawn;
	MeasureOldMesh = PC.Pawn.Mesh;
	MeasureStep = 0;
	PC.ClientSetBehindView(true);
	PC.ClientMessage("wardrobe: measuring "$MeasureList.Length$" models, stand still");
}

function MeasureTick()
{
	local Pawn P;
	local int k, j;
	local float Head, Foot, S, Z;
	local Mesh M;

	P = MeasurePawn;
	if (P == None || P.bDeleteMe)
	{
		MeasureList.Length = 0;
		return;
	}
	k = MeasureStep / 3;              // 3 timer steps per model: put on, wait, measure
	if (k >= MeasureList.Length)
	{
		MeasureList.Length = 0;
		P.Mesh = MeasureOldMesh;
		Fits.Length = 0;
		SaveConfig();
		MeasurePC.ClientSetBehindView(false);
		MeasurePC.ClientMessage("wardrobe: measured, saved to U2Wardrobe.ini");
		return;
	}
	if (MeasureStep % 3 == 0)
	{
		M = Mesh(DynamicLoadObject(MeasureList[k], class'Mesh', true));
		if (M != None)
			P.Mesh = M;
	}
	else if (MeasureStep % 3 == 2 && string(P.Mesh) ~= MeasureList[k] && Measure(P, Head, Foot))
	{
		S = P.DrawScale;
		Z = P.Location.Z + P.PrePivot.Z;
		for (j = 0; j < CalMeshes.Length; j++)
			if (CalMeshes[j] ~= MeasureList[k])
				break;
		CalMeshes[j] = MeasureList[k];
		CalHeads[j] = (Head - Z) / S;
		CalFeet[j] = (Foot - Z) / S;
		Log("U2Wardrobe: measured "$MeasureList[k]$" head "$CalHeads[j]$" foot "$CalFeet[j]
			$" height "$(CalHeads[j] - CalFeet[j])$" (scale "$S$", collision "$P.CollisionHeight$")");
	}
	else if (MeasureStep % 3 == 2)
		Log("U2Wardrobe: can't measure "$MeasureList[k]);
	MeasureStep++;
}

// scale the outfit so its head stands where the replaced model's did, feet
// kept on the same spot: the cutscene cameras are framed for Dalton's head
// (on the Atlantis he is a taller stand-in than the player character)
function FitHeight(int i)
{
	local Pawn P;
	local float Head, Foot, R, NewFoot;

	Fits[i].bFitted = true;
	P = Fits[i].P;
	if (Fits[i].Head < 0 || !Measure(P, Head, Foot))
		return;
	R = FClamp((Fits[i].Head - Fits[i].Foot) / (Head - Foot), 0.8, 1.5);
	if (Abs(R - 1.0) < 0.03)
		return;
	// scaling is about the actor's origin: put the feet back where they were
	NewFoot = P.Location.Z + (Foot - P.Location.Z) * R;
	P.SetDrawScale(Fits[i].Scale * R);
	P.PrePivot = Fits[i].PrePivot + vect(0,0,1) * (Fits[i].Foot - NewFoot);
	Log("U2Wardrobe: fitted "$P.Name$" x"$R);
}

// "wardrobe photo N": stand outfit N (menu order) facing the camera, Dist units
// ahead, at Dalton's height, for the menu portraits (tools: make_portraits.py);
// "wardrobe photo off" removes it
function Photo(string Args, PlayerController PC)
{
	local int N;
	local float Dist, H0, F0, H1, F1, S;
	local rotator R;
	local vector Loc;
	local Mesh M;

	if (Args ~= "off" || Args == "")
	{
		if (PhotoPawn != None)
			PhotoPawn.Destroy();
		PhotoPawn = None;
		return;
	}
	N = int(Args);
	Dist = 160;
	if (InStr(Args, " ") > 0)
		Dist = float(Mid(Args, InStr(Args, " ") + 1));
	if (N < 0 || N >= Meshes.Length || PC.Pawn == None)
		return;
	M = Mesh(DynamicLoadObject(Meshes[N], class'Mesh', true));
	if (M == None)
		return;
	R.Yaw = PC.Rotation.Yaw;
	Loc = PC.Pawn.Location + vector(R) * Dist;
	R.Yaw += 32768;
	if (PhotoPawn == None || PhotoPawn.bDeleteMe)
		PhotoPawn = Spawn(PC.Pawn.Class,,, Loc, R);
	if (PhotoPawn == None)
	{
		PC.ClientMessage("wardrobe photo: no room there");
		return;
	}
	PhotoPawn.SetLocation(Loc);
	PhotoPawn.SetRotation(R);
	PhotoPawn.Mesh = M;
	if (N == 0)
		PhotoPawn.Skins = PhotoPawn.default.Skins;
	else
		PhotoPawn.Skins.Length = 0;
	// Dalton's height, feet on the ground (as FitMeasured, against his own model)
	S = PhotoPawn.default.DrawScale;
	PhotoPawn.SetDrawScale(S);
	PhotoPawn.PrePivot = PhotoPawn.default.PrePivot;
	if (N > 0 && Measured(Mesh(DynamicLoadObject(Meshes[0], class'Mesh', true)), H0, F0) && Measured(M, H1, F1))
	{
		PhotoPawn.SetDrawScale(S * (H0 - F0) / (H1 - F1));
		PhotoPawn.PrePivot.Z += S * F0 - PhotoPawn.DrawScale * F1;
	}
	Log("U2Wardrobe: photo "$Labels[N]$" scale "$PhotoPawn.DrawScale);
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
	bFirstPersonBody = bOn;
	SaveConfig();
	if (BodyController(PC) != None)
	{
		if (!bOn && BodyController(PC).Body != None)
			BodyController(PC).Body.Destroy();
		PC.ClientMessage("first-person body: "$bOn);
	}
	else
		PC.ClientMessage("first-person body: "$bOn$" (from the next level)");
}

function GiveBody(PlayerController PC)
{
	local BodyController B;

	B = BodyController(PC);
	if (B != None && (B.Body == None || B.Body.bDeleteMe))
		B.Body = Spawn(class'FirstPersonBody', PC);
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

	if (MeasureList.Length > 0)
	{
		MeasureTick();
		return;
	}
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
	bMatchHeight=True
	// measured with "wardrobe measure" (standing, DrawScale 1)
	CalMeshes(0)="GlmCharactersG.PlayerGame"
	CalHeads(0)=45.405
	CalFeet(0)=-47.150
	CalMeshes(1)="GlmCharactersG.PlayerAtlantis"
	CalHeads(1)=65.939
	CalFeet(1)=-59.668
	CalMeshes(2)="GlmMalcolmG.Malcolm"
	CalHeads(2)=44.314
	CalFeet(2)=-42.666
	CalMeshes(3)="GlmMercMaleAG.MercMaleA"
	CalHeads(3)=45.101
	CalFeet(3)=-42.347
	CalMeshes(4)="GlmMercFemaleAG.MercFemaleA"
	CalHeads(4)=42.299
	CalFeet(4)=-42.303
	CalMeshes(5)="GlmEgyptMaleAG.EgyptMaleA"
	CalHeads(5)=43.676
	CalFeet(5)=-42.028
	CalMeshes(6)="GlmNightMaleAG.NightMaleA"
	CalHeads(6)=42.410
	CalFeet(6)=-42.168
	CalMeshes(7)="GlmJuggMaleAG.JuggMaleA"
	CalHeads(7)=42.915
	CalFeet(7)=-37.867
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
