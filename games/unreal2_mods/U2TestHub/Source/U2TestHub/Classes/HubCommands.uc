//=============================================================================
// HubCommands - the "hub" console command. One word picks the station, the
// rest are its arguments:
//
//   hub help                          list the commands
//   hub view [on|off]                 third-person camera + god mode
//   hub lamp [bright] [angle] [dist]  bright test lamp in front of you:
//                                     brightness 0-255 (220), height angle in
//                                     degrees (45), distance (200)
//   hub lamp clear                    remove the test lamps
//   hub dummy                         a marine to look at, in front of you
//   hub shadows mod|stock|off         U2SoftShadows / the game's own / none
//   hub info                          your shadows: light, darkness, fade
//   hub probe                         log frame hitches (U2Hover.FrameProbe)
//   hub goto MAP                      open a level, e.g. hub goto M08A1
//
// Everything is also written to Unreal2.log (prefix "Hub:"), so scripted
// pilot runs can read the results.
//=============================================================================
class HubCommands extends Object;

var HubMutator HubMut;
var PlayerController PC;

// ---------------------------------------------------------------- helpers

function Say(coerce string S)
{
	Log("Hub: "$S);
	if (PC != None)
		PC.ClientMessage(S);
}

// first word of S (and S loses it)
function string Word(out string S)
{
	local string W;
	local int i;

	while (Left(S, 1) == " ")
		S = Mid(S, 1);
	i = InStr(S, " ");
	if (i < 0)
	{
		W = S;
		S = "";
	}
	else
	{
		W = Left(S, i);
		S = Mid(S, i + 1);
	}
	return W;
}

function float NumOr(string W, float Fallback)
{
	if (W == "")
		return Fallback;
	return float(W);
}

function vector InFront(float Dist, float UpAngle)
{
	local rotator R;
	local vector Dir;

	R.Yaw = PC.Rotation.Yaw;
	Dir = vector(R);
	return PC.Pawn.Location + Dir * (Dist * Cos(UpAngle * Pi / 180.0))
		+ vect(0,0,1) * (Dist * Sin(UpAngle * Pi / 180.0));
}

function SSShadowManager ShadowManager()
{
	local SSShadowManager M;
	foreach PC.DynamicActors(class'SSShadowManager', M)
		return M;
	return None;
}

// ---------------------------------------------------------------- command

exec function Hub(optional string Args)
{
	local string Cmd;

	if (PC == None || HubMut == None)
		return;
	Cmd = Caps(Word(Args));
	if (Cmd == "" || Cmd == "HELP")         Help();
	else if (Cmd == "VIEW")                 View(Caps(Word(Args)) != "OFF");
	else if (Cmd == "LAMP")                 Lamp(Args);
	else if (Cmd == "DUMMY")                Dummy();
	else if (Cmd == "SHADOWS")              Shadows(Caps(Word(Args)));
	else if (Cmd == "INFO")                 Info();
	else if (Cmd == "PROBE")                Probe();
	else if (Cmd == "BONES")                Bones();
	else if (Cmd == "LIGHTS")               Lights();
	else if (Cmd == "TRACER")               TracerTest();
	else if (Cmd == "LINE")                 LineTest();
	else if (Cmd == "TP")                   Teleport(Args);
	else if (Cmd == "FACE")                 Face(NumOr(Word(Args), 0));
	else if (Cmd == "MESH")                 MeshTest(Word(Args), NumOr(Word(Args), 1.0));
	else if (Cmd == "LOADMESH")             LoadMesh(Word(Args));
	else if (Cmd == "TPTO")                 TeleportTo(Word(Args), NumOr(Word(Args), 250));
	else if (Cmd == "KILL")                 Kill(NumOr(Word(Args), 400));
	else if (Cmd == "MENUTEST")             MenuTest(Word(Args));
	else if (Cmd == "GOTO")                 GotoLevel(Word(Args));
	else
		Say("hub: unknown command '"$Cmd$"' - try: hub help");
}

function Help()
{
	Say("hub view [on|off] - third person + god mode");
	Say("hub lamp [bright 0-255] [angle] [dist] - test lamp in front (220 45 200); hub lamp clear");
	Say("hub dummy - a marine to look at");
	Say("hub shadows mod|stock|off - soft shadows / game's own / none");
	Say("hub info - your shadows: light, darkness, fade");
	Say("hub probe - log frame hitches;  hub goto MAP - open a level");
	Say("hub bones - where the skeleton's bones are (capsule shadow research)");
}

function View(bool bOn)
{
	PC.ClientSetBehindView(bOn);
	PC.bGodMode = bOn;
	Say("view: third person + god mode "$bOn);
}

function Lamp(string Args)
{
	local string W;
	local float Bright, Angle, Dist;
	local TestLamp L;
	local int i;

	W = Word(Args);
	if (Caps(W) == "CLEAR")
	{
		for (i = 0; i < HubMut.Lamps.Length; i++)
			if (HubMut.Lamps[i] != None)
				HubMut.Lamps[i].Destroy();
		HubMut.Lamps.Length = 0;
		Say("lamps cleared");
		return;
	}
	if (PC.Pawn == None)
		return;
	Bright = FClamp(NumOr(W, 220), 0, 255);
	Angle = NumOr(Word(Args), 45);
	Dist = NumOr(Word(Args), 200);
	L = PC.Spawn(class'TestLamp',,, InFront(Dist, Angle));
	if (L == None)
	{
		Say("lamp: no room there");
		return;
	}
	L.LightBrightness = byte(Bright);
	HubMut.Lamps[HubMut.Lamps.Length] = L;
	Say("lamp "$HubMut.Lamps.Length$": brightness "$int(Bright)$", "$int(Angle)$" deg up, "$int(Dist)$" away");
}

function Dummy()
{
	local Pawn P;
	local class<Pawn> C;

	if (PC.Pawn == None)
		return;
	C = class<Pawn>(DynamicLoadObject("U2Pawns.U2MarineLight", class'Class'));
	if (C != None)
		P = PC.Spawn(C,,, InFront(160, 0));
	if (P == None)
		Say("dummy: no room there");
	else
		Say("dummy: "$string(P));
}

// mod: U2SoftShadows casts; stock: the game's own single shadow; off: none
function Shadows(string Mode)
{
	local SSShadowManager M;
	local Pawn P;
	local int i;

	M = ShadowManager();
	if (Mode != "MOD" && Mode != "STOCK" && Mode != "OFF")
	{
		Say("hub shadows mod|stock|off");
		return;
	}
	if (M == None && Mode == "MOD")
	{
		Say("shadows: U2SoftShadows isn't running");
		return;
	}
	if (M != None)
		M.SetSuspended(Mode != "MOD");
	// give back the shadow flag to whatever a previous "off" took it from
	for (i = 0; i < HubMut.ShadowOffPawns.Length; i++)
		if (HubMut.ShadowOffPawns[i] != None && !HubMut.ShadowOffPawns[i].bDeleteMe)
		{
			HubMut.ShadowOffPawns[i].bActorShadows = true;
			HubMut.ShadowOffPawns[i].ResetShadows();
		}
	HubMut.ShadowOffPawns.Length = 0;
	if (Mode == "OFF")
		foreach PC.DynamicActors(class'Pawn', P)
			if (P.Controller != None && P.Mesh != None && P.bActorShadows)
			{
				P.bActorShadows = false;
				P.ResetShadows();        // removes the game's own shadow too
				HubMut.ShadowOffPawns[HubMut.ShadowOffPawns.Length] = P;
			}
	Say("shadows: "$Mode);
}

// everything about a shadow projector that decides whether it draws
function string Describe(ShadowProjector S)
{
	local string L;
	local ShadowBitmapMaterial T;

	L = "dz "$int(S.Location.Z - PC.Pawn.Location.Z)$" pitch "$S.Rotation.Pitch$" fov "$S.FOV
		$" scale "$S.DrawScale$" trace "$S.MaxTraceDistance$" ldist "$int(S.LightDistance)
		$" grad "$S.bGradient$" hidden "$S.bHidden;
	T = S.ShadowTexture;
	if (T == None)
		return L$" (no texture)";
	return L$" | tex "$T.USize$" dark "$T.ShadowDarkness$" dirty "$T.Dirty$" invalid "$T.Invalid
		$" lfov "$T.LightFOV$" cull "$int(T.CullDistance)$" blob "$T.bBlobShadow
		$" origin "$int(VSize(T.FrustumOrigin - S.Location))$" actor "$(T.ShadowActor != None);
}

function Info()
{
	local SSShadowController C;
	local int i;
	local SSLightShadow S;
	local string Line;

	if (PC.Pawn == None)
		return;
	foreach PC.DynamicActors(class'SSShadowController', C)
	{
		if (C.Owner != PC.Pawn)
			continue;
		for (i = 0; i < C.Shadows.Length; i++)
		{
			S = C.Shadows[i];
			if (S == None)
				continue;
			Line = "shadow "$i$": ";
			if (S.AssignedLight == None)
				Line = Line$"no light";
			else
			{
				Line = Line$string(S.AssignedLight)$" bright "$S.AssignedLight.LightBrightness
					$" dist "$int(VSize(S.AssignedLight.Location - PC.Pawn.Location))
					$" fade "$S.Fade;
			}
			Say(Line);
			if (S.AssignedLight != None)
				Say("   "$Describe(S));
		}
		if (C.Contact != None)
			Say("contact shadow: shown "$C.Contact.bShown);
		if (C.Capsules.Length > 0 && C.Capsules[0] != None)
			Say("capsules: "$C.Capsules.Length$" shown "$C.Capsules[0].bShown$" first dz "$int(C.Capsules[0].Location.Z - PC.Pawn.Location.Z)$" scale "$C.Capsules[0].DrawScale$" tex "$string(C.Capsules[0].ProjTexture)$" chosen "$C.Chosen.Length);
		if (C.Sharp != None)
		{
			if (C.Sharp.AssignedLight == None)
				Say("sharp copy: no light");
			else
				Say("sharp copy of "$string(C.Sharp.AssignedLight)$": "$Describe(C.Sharp)$" blur "$C.Sharp.bBlurShadow);
		}
		if (PC.Pawn.ShadowA != None)
			Say("game's own shadow: "$Describe(ShadowProjector(PC.Pawn.ShadowA)));
		SunInfo(C);
		return;
	}
	if (PC.Pawn.ShadowA != None)
		Say("game's own shadow: "$Describe(ShadowProjector(PC.Pawn.ShadowA)));
	else
		Say("info: no shadows on you");
}

function SunInfo(SSShadowController C)
{
	local SSShadowController K;
	local int Total, Culled;
	local Actor Sun;
	local vector ToSun, HitLoc, HitNorm;
	local Actor Hit;
	local string L;

	foreach PC.DynamicActors(class'SSShadowController', K)
	{
		Total++;
		if (K.bCulled)
			Culled++;
		else if (K.Owner != None)
			Say("  active: "$string(K.Owner)$" dist "$int(VSize(K.Owner.Location - PC.Pawn.Location))$" allowed "$K.Allowed$" capsules "$K.Capsules.Length);
	}
	Say("characters with shadow controllers: "$Total$", culled "$Culled$", active "$(Total - Culled));

	Sun = C.Manager.SunLightActor;
	if (Sun == None)
	{
		Say("sun: none in this level");
		return;
	}
	ToSun = -vector(Sun.Rotation);
	Hit = PC.Trace(HitLoc, HitNorm, PC.Pawn.Location + ToSun * 16384, PC.Pawn.Location, false);
	L = "sun: "$string(Sun)$" pitch "$Sun.Rotation.Pitch$" bright "$Sun.LightBrightness$" clearance ";
	if (Hit == None)
		L = L$"open";
	else
		L = L$int(VSize(HitLoc - PC.Pawn.Location))$" ("$string(Hit)$")";
	Say(L$" -> casts "$C.SunVisible()$" (needs "$int(C.SunClearance)$")");
}

// does the engine give scripts the skeleton's bone positions? (needed for
// capsule shadows). Unreal II's Golem meshes have their own node API.
function Bones()
{
	local array<string> B;
	local int i, N, Node;
	local vector T, TL;
	local string L;

	if (PC.Pawn == None)
		return;
	Say("mesh nodes: "$PC.Pawn.MeshGetNodeCount());
	B[0] = "Merc Pelvis";   B[1] = "Merc Spine";     B[2] = "Merc Spine1";  B[3] = "Merc Spine2";
	B[4] = "Merc Neck";     B[5] = "Merc Head";      B[6] = "Merc L Thigh"; B[7] = "Merc R Thigh";
	B[8] = "Merc L Calf";   B[9] = "Merc R Calf";    B[10] = "Merc L Foot"; B[11] = "Merc R Foot";
	B[12] = "Merc L UpperArm"; B[13] = "Merc R UpperArm"; B[14] = "Merc L Forearm"; B[15] = "Merc R Forearm";
	B[16] = "Merc L Hand";  B[17] = "Merc R Hand";   B[18] = "head";        B[19] = "nosuchbone";
	for (i = 0; i < B.Length; i++)
	{
		Node = PC.Pawn.MeshGetNodeNamed(B[i]);
		L = "node "$B[i]$": handle "$Node;
		if (Node != 0)
		{
			T = PC.Pawn.MeshNodeGetTranslation(Node);
			TL = PC.Pawn.MeshNodeGetTranslation(Node, MESHNODEREL_Mesh);
			L = L$" world ("$int(T.X)$","$int(T.Y)$","$int(T.Z)$") mesh ("$int(TL.X)$","$int(TL.Y)$","$int(TL.Z)$")";
		}
		Say(L);
	}
	Say("pawn at ("$int(PC.Pawn.Location.X)$","$int(PC.Pawn.Location.Y)$","$int(PC.Pawn.Location.Z)$") height "$PC.Pawn.CollisionHeight);
}

// which lights each visible character's shadows are using
function Lights()
{
	local SSShadowController K;
	local int i;
	local string L;

	foreach PC.DynamicActors(class'SSShadowController', K)
	{
		if (K.bCulled || K.Owner == None)
			continue;
		L = "lights of "$string(K.Owner)$":";
		for (i = 0; i < K.Shadows.Length; i++)
			if (K.Shadows[i] != None && K.Shadows[i].TargetLight() != None)
				L = L$" "$string(K.Shadows[i].TargetLight());
		Say(L);
	}
}

// drive the options-page helper without the menu: hub menutest [maxshadows]
// sets Lights per Character through the same setter the menu uses (live
// rebuild + save), so the settings path behind the page can be checked
function MenuTest(string Arg)
{
	local SSMenuHelper H;

	H = new class'SSMenuHelper';
	Say("menu helper reads: enabled "$H.GetEnabled()$" maxshadows "$int(H.GetMaxShadows())$" strength "$int(H.GetStrength())
		$" fade "$H.GetFadeLength()$" contact "$H.GetContact()$" hardtosoft "$H.GetHardToSoft()$" capsules "$H.GetCapsules()
		$" cameracull "$H.GetCameraCull()$" near "$int(H.GetNearDistance())$" mid "$int(H.GetMidDistance()));
	if (Arg != "")
	{
		H.SetMaxShadows(float(Arg));
		Say("menu helper set maxshadows "$Arg$" -> now "$int(H.GetMaxShadows())$" (saved, shadows rebuilding)");
	}
}

// kill every enemy within Dist as if the player did it (the real death path:
// hit feedback, ragdoll, body rules) - for testing those without aiming
function Kill(float Dist)
{
	local Pawn P;
	local int N, k;

	if (PC.Pawn == None)
		return;
	foreach PC.DynamicActors(class'Pawn', P)
	{
		if (P == PC.Pawn || P.Health <= 0 || P.Controller == None || VSize(P.Location - PC.Pawn.Location) > Dist)
			continue;
		// modest hits until it drops: armour-proof, and never enough overkill to gib
		for (k = 0; k < 8 && P.Health > 0 && !P.bDeleteMe; k++)
			P.TakeDamage(P.Health + 10, PC.Pawn, P.Location, Normal(P.Location - PC.Pawn.Location) * 3000, class'DamageType');
		N++;
	}
	Say("kill: "$N$" within "$int(Dist));
}

// two AR_Tracer lines ahead of the player, scaled two ways, to learn the mesh's length
function TracerTest()
{
	local Actor T;
	local vector Start, Dir;
	local int i;

	if (PC.Pawn == None)
		return;
	Dir = vector(PC.GetViewRotation());
	Start = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.BaseEyeHeight + Dir * 60;
	for (i = 0; i < 2; i++)
	{
		T = PC.Spawn(class<Actor>(DynamicLoadObject("U2Weapons.AR_Tracer", class'Class')),,, Start + vect(0,0,1) * (-20 + 40 * i), PC.GetViewRotation());
		if (T == None)
			continue;
		if (i == 0)
		{
			T.SetDrawScale(1.0);
			T.SetDrawScale3D(vect(600,3,3));
		}
		else
		{
			T.SetDrawScale3D(vect(20000,2,2));           // default DrawScale 0.03 -> 600 units if the mesh is 1 unit long
		}
		T.LifeSpan = 30;
		T.SetPropertyText("FadeTime", "10");    // stays visible for the screenshot (normally 0.05 s)
		T.Trigger(None, None);
		Say("tracer "$i$": scale "$T.DrawScale$" x "$T.DrawScale3D.X);
	}
}

// the game's pulse-line tracer, drawn beside the player so it's seen side-on
function LineTest()
{
	local PulseLineGenerator T;
	local vector Fwd, Right, Start, End;
	local int i;

	if (PC.Pawn == None)
		return;
	Fwd = vector(PC.GetViewRotation());
	Right = Fwd cross vect(0,0,1);
	for (i = 0; i < 2; i++)
	{
		Start = PC.Pawn.Location + Right * (150 + 150 * i) + vect(0,0,1) * (20 + 30 * i);
		End = Start + Fwd * 900;
		T = PulseLineGenerator(class'ParticleGenerator'.static.CreateNew(PC.Pawn, PulseLineGenerator'AssaultFX.PulseLineGenerator1', Start));
		if (T == None)
		{
			Say("line: CreateNew failed");
			return;
		}
		if (T.Connections.Length != 1)
			T.Connections.Length = 1;
		T.Connections[0].StartActor = T;
		T.Connections[0].End = End;
		T.SetDrawType(DT_Custom);
		if (T.BeamTexture != None)
			T.BeamTexture.ResetModifiers();   // the beam material starts faded out (sniper rifle does this)
		T.TurnOn();                          // CreateNew leaves it off (bOn=False in a dump)
		if (i == 1)
			T.Trigger(PC.Pawn, PC.Pawn);
		T.LifeSpan = 8;
		Say("line "$i$": "$string(T)$" triggered "$(i == 1));
	}
}

// hub tp X Y Z - move the player there (testing progress-based scripting)
function Teleport(string Args)
{
	local vector V, HitLoc, HitNorm;

	if (PC.Pawn == None)
		return;
	V.X = float(Word(Args));
	V.Y = float(Word(Args));
	V.Z = float(Word(Args));
	// a Z of 0 (or none) means: find the ground from high up
	if (V.Z == 0)
	{
		if (PC.Trace(HitLoc, HitNorm, V + vect(0,0,-30000), V + vect(0,0,3800), false) != None)
			V = HitLoc + vect(0,0,1) * (PC.Pawn.CollisionHeight + 8);
	}
	if (PC.Pawn.SetLocation(V))
		Say("tp: now at ("$int(V.X)$","$int(V.Y)$","$int(V.Z)$")");
	else
		Say("tp: blocked at ("$int(V.X)$","$int(V.Y)$","$int(V.Z)$")");
}

// hub tpto NAME [dist] - stand DIST units from the actor whose name contains NAME
function TeleportTo(string NameBit, float Dist)
{
	local Actor A;
	local vector Spot;
	local rotator R;
	local int k;

	if (PC.Pawn == None)
		return;
	foreach PC.DynamicActors(class'Actor', A)
		if (InStr(Caps(string(A)), Caps(NameBit)) >= 0 && A != PC.Pawn)
		{
			// try eight directions around it at that distance, then closer
			for (k = 0; k < 16; k++)
			{
				R.Yaw = k * 8192;
				Spot = A.Location + vector(R) * Dist * (1.0 - 0.5 * (k / 8)) + vect(0,0,20);
				if (PC.Pawn.SetLocation(Spot))
				{
					Say("tpto "$string(A)$": at "$int(VSize(Spot - A.Location))$" units");
					return;
				}
			}
			Say("tpto "$string(A)$": blocked all round");
			return;
		}
	Say("tpto: no actor matching "$NameBit);
}

// hub mesh PKG.Group.Name [scale] - a static mesh 400 units ahead, for judging assets
function MeshTest(string Path, float Scale)
{
	local StaticMesh M;
	local HubMesh A;
	local vector Spot, HitLoc, HitNorm;

	if (PC.Pawn == None)
		return;
	M = StaticMesh(DynamicLoadObject(Path, class'StaticMesh'));
	if (M == None)
	{
		Say("mesh: can't load "$Path);
		return;
	}
	Spot = PC.Pawn.Location + vector(PC.Rotation) * 500;
	if (PC.Trace(HitLoc, HitNorm, Spot + vect(0,0,-3000), Spot + vect(0,0,500), false) != None)
		Spot = HitLoc;
	// StaticMeshActor is bStatic (can't be spawned): U2Decoration carries a mesh too
	A = HubMut.Spawn(class'HubMesh',,, Spot + vect(0,0,300));
	if (A == None)
	{
		Say("mesh: spawn blocked");
		return;
	}
	A.StaticMesh = M;
	A.SetDrawScale(Scale);
	A.SetDrawType(DT_StaticMesh);
	Say("mesh: "$Path$" x"$Scale$" at ("$int(Spot.X)$","$int(Spot.Y)$","$int(Spot.Z)$")");
}

// hub loadmesh PKG.Group.Name - does the engine find it? (asset survey)
function LoadMesh(string Path)
{
	if (DynamicLoadObject(Path, class'StaticMesh') != None)
		Log("Hub: loadmesh OK "$Path);
	else
		Log("Hub: loadmesh MISSING "$Path);
}

// hub face DEGREES - turn to a world yaw (0 = +X, 90 = +Y)
function Face(float Deg)
{
	local rotator R;
	R = PC.Rotation;
	R.Yaw = int(Deg * 65536.0 / 360.0);
	R.Pitch = -600;
	PC.SetRotation(R);
	if (PC.Pawn != None)
		PC.Pawn.SetRotation(R);
	PC.ClientSetRotation(R);
	Say("face "$int(Deg));
}

function Probe()
{
	local class<Actor> C;

	if (HubMut.Probe != None)
	{
		Say("probe already running (see Unreal2.log, FrameProbe:)");
		return;
	}
	C = class<Actor>(DynamicLoadObject("U2Hover.FrameProbe", class'Class'));
	if (C != None)
		HubMut.Probe = PC.Spawn(C);
	if (HubMut.Probe == None)
		Say("probe: U2Hover isn't installed");
	else
		Say("probe: logging frame hitches to Unreal2.log (FrameProbe:)");
}

function GotoLevel(string Map)
{
	if (Map == "")
	{
		Say("hub goto MAP  (e.g. M08A1, HoverTest)");
		return;
	}
	Say("goto "$Map);
	PC.ConsoleCommand("open "$Map);
}

defaultproperties
{
}
