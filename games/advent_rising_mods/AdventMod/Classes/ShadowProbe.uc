//=============================================================================
// ShadowProbe - step 1 of the soft-shadow port: what does this engine do?
// Spawned by ModMutator in a level when bShadowProbe is set. It logs the
// lights around the player and the player's stock shadow, then attaches a
// second ShadowProjector to the player aimed at the nearest real lamp, so a
// screenshot shows whether two shadows per character render at all.
//=============================================================================
class ShadowProbe extends Info;

var Pawn Target;
var ShadowProjector Extra;
var Projector Decal;
var Projector Mark;
var Actor Lamp;
var float LogTimer;
var int Reports;

function Note(string S)
{
	class'ModSettings'.static.Note("probe: " $ S);
}

function Start(Pawn P)
{
	local Actor A;
	local int n;
	local float d;

	local PlayerController PC;
	local Actor.SavedPCOptions O;

	Target = P;
	PC = PlayerController(P.Controller);
	if (PC != None)
	{
		Note("client Projectors " $ PC.ConsoleCommand("get WinDrv.WindowsClient Projectors") $ " BlobShadows " $ PC.ConsoleCommand("get WinDrv.WindowsClient BlobShadows") $ " Decals " $ PC.ConsoleCommand("get WinDrv.WindowsClient Decals") $ " NoDynamicLights " $ PC.ConsoleCommand("get WinDrv.WindowsClient NoDynamicLights"));
		PC.GetPCOptions(O);
		Note("saved PC options: Projectors " $ O.Projectors $ " Shadows " $ O.Shadows $ " Distortion " $ O.Distortion $ " DynamicLights " $ O.DynamicLights $ " size " $ O.Xsize $ "x" $ O.Ysize);
	}
	Note("pawn " $ P $ " (" $ P.Class $ ") mesh " $ P.Mesh $ " bActorShadows " $ P.bActorShadows $ " highdetail " $ P.bHighDetailShadow);
	if (P.Shadow != None)
		Note("stock shadow: dir " $ P.Shadow.LightDirection $ " dist " $ P.Shadow.LightDistance $ " blob " $ P.Shadow.bBlobShadow $ " root " $ P.Shadow.RootMotion $ " tex " $ P.Shadow.ShadowTexture $ " fov " $ P.Shadow.FOV $ " trace " $ P.Shadow.MaxTraceDistance);
	else
		Note("stock shadow: none");
	// every light within 2000 units, nearest first-ish (just listed)
	foreach P.RadiusActors(class'Actor', A, 2000)
	{
		if (Light(A) == None || A.LightType == LT_None)
			continue;
		d = VSize(A.Location - P.Location);
		n++;
		if (n <= 40)
			Note("light " $ A.Name $ " dist " $ int(d) $ " bright " $ A.LightBrightness $ " radius " $ A.LightRadius $ " (" $ int(25 * (A.LightRadius + 1)) $ " units) type " $ A.LightType $ " effect " $ A.LightEffect $ " hidden " $ A.bHidden);
		if (A.LightEffect != LE_Sunlight && d < 25 * (A.LightRadius + 1) && (Lamp == None || d < VSize(Lamp.Location - P.Location)))
			Lamp = A;
	}
	Note(n $ " lights within 2000; nearest reaching lamp: " $ Lamp);
	SpawnDecal(P);
	if (Lamp == None)
		return;
	Extra = Spawn(class'ShadowProjector', None, '', P.Location);
	if (Extra == None)
	{
		Note("could not spawn a second projector");
		return;
	}
	Extra.ShadowActor = P;
	Extra.CreateShadow();
	Extra.LightDirection = TestDirection();
	Extra.LightDistance = FClamp(VSize(P.Location - Lamp.Location), 200, 1000);
	Extra.MaxTraceDistance = 1000;
	Extra.bBlobShadow = false;
	Extra.RootMotion = true;
	Extra.UpdateInterval = 0;
	Extra.InitShadow();
	if (Extra.ShadowTexture != None)
		Extra.ShadowTexture.ShadowDarkness = 255;
	Note("second projector " $ Extra $ " aimed at " $ Lamp.Name $ ", texture " $ Extra.ShadowTexture $ " " $ Extra.ShadowTexture.USize $ "x" $ Extra.ShadowTexture.VSize);
}

// a plain projector (no shadow rendering involved) pointing straight down on the
// floor ahead of the player: tells apart "projectors don't draw" from "shadow textures don't draw"
function SpawnDecal(Pawn P)
{
	local vector Ahead, HitLoc, HitNorm;
	local Actor HitActor;
	local PlayerController PC;

	PC = PlayerController(P.Controller);
	Ahead = vect(1,0,0);
	if (PC != None)
		Ahead = Vector(PC.GetViewRotation());
	Ahead.Z = 0;
	Ahead = Normal(Ahead);
	// on the floor straight ahead: trace down from above that spot
	HitActor = Trace(HitLoc, HitNorm, P.Location + Ahead * 300 - vect(0,0,500), P.Location + Ahead * 300 + vect(0,0,100), false);
	if (HitActor == None)
		HitLoc = P.Location + Ahead * 300 - vect(0,0,80);
	Decal = Spawn(class'DynamicProjector', None, '', HitLoc + vect(0,0,200), rot(-16384,0,0));
	if (Decal == None)
	{
		Note("decal: could not spawn");
		return;
	}
	Decal.ProjTexture = Texture'Engine.DefaultTexture';
	Decal.FOV = 60;
	Decal.MaxTraceDistance = 600;
	Decal.bProjectBSP = true;
	Decal.bProjectStaticMesh = true;
	Decal.bProjectTerrain = true;
	Decal.bProjectActor = false;
	Decal.bGradient = false;
	Decal.SetDrawScale(2.0);
	Decal.AttachProjector();
	SpawnGameMark(HitLoc);
	Note("decal " $ Decal $ " at " $ Decal.Location $ " over floor hit " $ HitActor $ " at " $ HitLoc $ " texture " $ Decal.ProjTexture);
}

// the game's own bullet hit-mark projector, enlarged, on the same floor spot: if even
// this doesn't show, projector drawing itself is broken (engine/driver), not our setup
function SpawnGameMark(vector FloorLoc)
{
	local class<Projector> MarkClass;

	MarkClass = class<Projector>(DynamicLoadObject("EonEffects.hitMark", class'Class', true));
	if (MarkClass == None)
	{
		Note("hitmark: class not found");
		return;
	}
	Mark = Spawn(MarkClass, None, '', FloorLoc + vect(0,0,60) + vect(120,0,0), rot(-16384,0,0));
	if (Mark == None)
	{
		Note("hitmark: could not spawn");
		return;
	}
	Mark.SetDrawScale(8.0);
	Mark.MaxTraceDistance = 200;
	Mark.LifeSpan = 0;
	Mark.AttachProjector();
	Note("hitmark " $ Mark $ " at " $ Mark.Location $ " texture " $ Mark.ProjTexture);
}

// toward a light behind the player's camera, 30 degrees up: the shadow stretches
// forward across the floor, in plain view of the third-person camera
function vector TestDirection()
{
	local vector Back;
	local PlayerController PC;

	PC = PlayerController(Target.Controller);
	if (PC == None)
		return Normal(vect(1,1,3));
	Back = -Vector(PC.GetViewRotation());
	Back.Z = 0;
	Back = Normal(Back);
	return Normal(Back * 0.866 + vect(0,0,0.5));
}

event Tick(float DeltaTime)
{
	if (Target == None || Target.bDeleteMe)
	{
		Destroy();
		return;
	}
	if (Extra != None && Lamp != None)
	{
		Extra.LightDirection = TestDirection();
		if (Extra.ShadowTexture != None)
			Extra.ShadowTexture.LightDirection = Extra.LightDirection;
	}
	LogTimer += DeltaTime;
	if (LogTimer > 3.0 && Reports < 3)
	{
		LogTimer = 0;
		Reports++;
		if (Extra != None)
			Note("extra at " $ Extra.Location $ " rot " $ Extra.Rotation $ " pawn " $ Target.Location $ " darkness " $ Extra.ShadowTexture.ShadowDarkness $ " invalid " $ Extra.ShadowTexture.Invalid);
		if (Target.Shadow != None)
			Note("stock at " $ Target.Shadow.Location $ " rot " $ Target.Shadow.Rotation $ " darkness " $ Target.Shadow.ShadowTexture.ShadowDarkness);
	}
}

event Destroyed()
{
	if (Extra != None)
		Extra.Destroy();
	if (Decal != None)
		Decal.Destroy();
	if (Mark != None)
		Mark.Destroy();
	Super.Destroyed();
}

defaultproperties
{
}
