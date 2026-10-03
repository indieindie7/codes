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
//   hub spawn PKG.Class [yaw] [dist]  any actor, e.g. hub spawn U2Malcolm.MalcolmDummy
//   hub clean [fov]                   hide the HUD and your weapon (pictures)
//   hub dummy [MESH] [yaw] [dist]     a marine to look at, in front of you;
//                                     MESH = another model to wear, yaw =
//                                     degrees it is turned (180 = faces you)
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
	else if (Cmd == "DUMMY")                Dummy(Word(Args), NumOr(Word(Args), 180), NumOr(Word(Args), 160));
	else if (Cmd == "SPAWN")                SpawnActor(Word(Args), NumOr(Word(Args), 180), NumOr(Word(Args), 330));
	else if (Cmd == "CLEAN")                Clean(NumOr(Word(Args), 0));
	else if (Cmd == "SHADOWS")              Shadows(Caps(Word(Args)));
	else if (Cmd == "INFO")                 Info();
	else if (Cmd == "PROBE")                Probe();
	else if (Cmd == "BONES")                Bones();
	else if (Cmd == "BEND")                 Bend(Args);
	else if (Cmd == "AGENT")                Agent(Word(Args));
	else if (Cmd == "AGENTSET")             AgentSet(Word(Args), Word(Args), Caps(Word(Args)) == "LOCK");
	else if (Cmd == "AGENTDO")              AgentDo(Args);
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
	else if (Cmd == "ZONES")                Zones();
	else if (Cmd == "BEATS")                Beats();
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
	Say("hub zones - log the level's zones, doorways and scripted actors (for the zone map)");
	Say("hub beats - log the level's event wiring (who fires what, who reacts) for the beat graph");
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

// hub spawn PKG.Class [yaw] [dist] - any actor class in front of you, turned yaw degrees
function SpawnActor(string Path, float YawDeg, float Dist)
{
	local class<Actor> C;
	local Actor A;
	local rotator R;

	if (PC.Pawn == None)
		return;
	C = class<Actor>(DynamicLoadObject(Path, class'Class'));
	if (C == None)
	{
		Say("spawn: no class "$Path);
		return;
	}
	R.Yaw = PC.Rotation.Yaw + int(YawDeg * 65536.0 / 360.0);
	A = PC.Spawn(C,,, InFront(Dist, 0), R);
	if (A == None)
		Say("spawn: blocked");
	else
		Say("spawn: "$string(A));
}

// hub clean - no HUD and no weapon in view, for taking pictures
function Clean(float Zoom)
{
	if (PC.myHUD != None)
		PC.myHUD.bHideHUD = true;
	// third person with your own body hidden: nothing of you is drawn
	PC.ClientSetBehindView(true);
	PC.bGodMode = true;
	if (PC.Pawn != None)
		PC.Pawn.bHidden = true;
	PC.ConsoleCommand("ToggleHUD");
	if (Zoom > 0)
	{
		PC.DefaultFOV = Zoom;
		PC.DesiredFOV = Zoom;
		PC.FOVAngle = Zoom;
	}
	Say("clean: HUD, weapon and your body hidden");
}

function Dummy(string MeshPath, float YawDeg, float Dist)
{
	local Pawn P;
	local class<Pawn> C;
	local Mesh M;
	local rotator R;

	if (PC.Pawn == None)
		return;
	R.Yaw = PC.Rotation.Yaw + int(YawDeg * 65536.0 / 360.0);
	C = class<Pawn>(DynamicLoadObject("U2Pawns.U2MarineLight", class'Class'));
	if (C != None)
		P = PC.Spawn(C,,, InFront(Dist, 0), R);
	if (P == None)
	{
		Say("dummy: no room there");
		return;
	}
	if (MeshPath != "")
	{
		M = Mesh(DynamicLoadObject(MeshPath, class'Mesh'));
		if (M != None)
			P.Mesh = M;
		else
			Say("dummy: can't load "$MeshPath);
		// a model on show: no AI, so it keeps its place and facing
		if (P.Controller != None)
			P.Controller.Destroy();
	}
	Say("dummy: "$string(P)$" mesh "$string(P.Mesh));
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
					$" fade "$S.Fade$" share "$S.LightShare;
			}
			Say(Line);
			if (S.AssignedLight != None)
				Say("   "$Describe(S));
		}
		Say("light here: "$int(C.LastTotalLight)$" (lamps "$int(C.LastTotalLight - C.LastAmbient)$" + ambient "$int(C.LastAmbient)$"), set held "$C.bHeld);
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
			Say("  active: "$string(K.Owner)$" dist "$int(VSize(K.Owner.Location - PC.Pawn.Location))$" allowed "$K.Allowed);
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

// hub bend NODE pitch yaw roll [space] / hub bend off: rotate one bone every tick (HubBend).
// Node names with spaces use underscores: Merc_L_Forearm
function Bend(string Args)
{
	local HubBend B;
	local string N;
	local rotator R;
	local int i;

	foreach PC.AllActors(class'HubBend', B)
		B.Destroy();
	N = Word(Args);
	if (N == "" || Caps(N) == "OFF" || PC.Pawn == None)
	{
		Say("bend: off");
		return;
	}
	while (InStr(N, "_") >= 0)
	{
		i = InStr(N, "_");
		N = Left(N, i)$" "$Mid(N, i + 1);
	}
	R.Pitch = NumOr(Word(Args), 0) * 65536.0 / 360.0;
	R.Yaw = NumOr(Word(Args), 0) * 65536.0 / 360.0;
	R.Roll = NumOr(Word(Args), 0) * 65536.0 / 360.0;
	B = PC.Spawn(class'HubBend');
	B.Setup(PC.Pawn, N, R, byte(NumOr(Word(Args), 2)));
	Say("bend: "$N$" "$R);
}

// hub agent [me|near]: everything a mesh's Golem animation agent offers (its inputs with all their
// values and current value, its actions, its channels with what is bound on each) - the map
// for driving animation from script
function Agent(string Who)
{
	local Pawn P, Best;
	local float D, BestD;
	local int i, j, N;
	local string L;
	local name In;

	P = PC.Pawn;
	if (Caps(Who) == "NEAR")
	{
		BestD = 1000000;
		foreach PC.AllActors(class'Pawn', P)
			if (P != PC.Pawn && P.Mesh != None)
			{
				D = VSize(P.Location - PC.Pawn.Location);
				if (D < BestD) { BestD = D; Best = P; }
			}
		P = Best;
	}
	if (P == None)
	{
		Say("agent: no pawn");
		return;
	}
	Say("agent: "$P$" mesh "$P.Mesh$" inputs "$P.MeshAgentGetInputCount()$" actions "$P.MeshAgentGetActionCount()$" channels "$P.MeshAgentGetChannelCount());
	for (i = 0; i < P.MeshAgentGetInputCount(); i++)
	{
		In = P.MeshAgentGetInputName(i);
		N = P.MeshAgentGetInputValueCount(i);
		L = "agent input "$In$" = "$P.MeshAgentGetInputCurValue(In)$" of "$N$":";
		for (j = 0; j < N; j++)
			L = L$" "$P.MeshAgentGetInputValueName(i, j);
		Say(L);
	}
	L = "agent actions:";
	for (i = 0; i < P.MeshAgentGetActionCount(); i++)
	{
		L = L$" "$P.MeshAgentGetActionName(i);
		if (Len(L) > 900) { Say(L); L = "agent actions (more):"; }
	}
	Say(L);
	for (i = 0; i < P.MeshAgentGetChannelCount(); i++)
		Say("agent channel "$i$" "$P.MeshAgentGetChannelName(i)$" bound by "$P.MeshAgentGetChannelBoundAction(i)$" level "$P.MeshAgentGetChannelBoundLevel(i)$" script "$P.MeshAgentGetChannelScriptName(i));
}

// hub agentset INPUT VALUE [lock]: set an animation input on your character (lock keeps the game
// from changing it again; "hub agentset INPUT unlock" frees it)
function AgentSet(string In, string V, bool bLock)
{
	local Pawn P;
	local bool Ok;
	local int i, j;
	local name InName, VName;

	P = PC.Pawn;
	if (P == None || In == "")
		return;
	// names can't be made from strings here: find them among the agent's own
	for (i = 0; i < P.MeshAgentGetInputCount(); i++)
		if (string(P.MeshAgentGetInputName(i)) ~= In)
		{
			InName = P.MeshAgentGetInputName(i);
			for (j = 0; j < P.MeshAgentGetInputValueCount(i); j++)
				if (string(P.MeshAgentGetInputValueName(i, j)) ~= V)
					VName = P.MeshAgentGetInputValueName(i, j);
			break;
		}
	if (InName == '')
	{
		Say("agentset: no input "$In);
		return;
	}
	P.MeshAgentSetInputLock(InName, false);
	if (Caps(V) == "UNLOCK")
	{
		Say("agentset: "$InName$" unlocked");
		return;
	}
	if (VName == '')
	{
		Say("agentset: "$InName$" has no value "$V);
		return;
	}
	Ok = P.MeshAgentSetInputCurValue(InName, VName);
	if (bLock)
		P.MeshAgentSetInputLock(InName, true);
	Say("agentset: "$InName$" = "$VName$" ok "$Ok$" now "$P.MeshAgentGetInputCurValue(InName)$" locked "$bLock);
}

// hub agentdo TEXT: compile TEXT as a Golem action and run it on your character, e.g.
//   hub agentdo set AnimUpper { script "U_N_LG_AmbientLowered"; blend 0.2; }
function AgentDo(string Text)
{
	local int i;

	if (PC.Pawn == None)
		return;
	Say("agentdo: "$Text$" -> "$PC.Pawn.MeshAgentImmediateAction(Text));
	for (i = 0; i < PC.Pawn.MeshAgentGetChannelCount(); i++)
		if (PC.Pawn.MeshAgentGetChannelBoundLevel(i) > 0)
			Say("agentdo: channel "$PC.Pawn.MeshAgentGetChannelName(i)$" script "$PC.Pawn.MeshAgentGetChannelScriptName(i));
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
		$" fade "$H.GetFadeLength()$" player "$int(H.GetPlayerShadows())$" respectbaked "$H.GetRespectBaked()
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


// hub zones: the level as zones (rooms split by zone portals) for the zone map / level remixing.
// Logs "Zones:" lines: every navigation point with its zone, every path that crosses into another
// zone (a doorway), and per zone the actors that matter (enemies, triggers, movers, anything
// that fires an event). tools/python/U2Pilot/zonemap.py turns them into a report and a picture.
function Zones()
{
	local NavigationPoint N;
	local Actor A;
	local int i, Navs, Links;
	local ReachSpec R;
	local string Kind;
	local ZoneInfo Z;
	local PhysicsVolume V;

	foreach PC.AllActors(class'ZoneInfo', Z)
		Log("Zones: zoneinfo "$Z.Region.ZoneNumber$" "$Z.Name$" "$Z.ZoneTag$" "$int(Z.Location.X)$" "$int(Z.Location.Y)$" "$int(Z.Location.Z));
	for (N = PC.Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
	{
		Navs++;
		Log("Zones: nav "$N.Region.ZoneNumber$" "$int(N.Location.X)$" "$int(N.Location.Y)$" "$int(N.Location.Z)$" "$N.Class.Name$" "$N.Name);
		for (i = 0; i < N.PathList.Length; i++)
		{
			R = N.PathList[i];
			if (R != None && R.End != None)
				Log("Zones: edge "$N.Name$" "$R.End.Name$" "$R.Distance);
			if (R == None || R.End == None || R.End.Region.ZoneNumber == N.Region.ZoneNumber)
				continue;
			Links++;
			Log("Zones: link "$N.Region.ZoneNumber$" "$R.End.Region.ZoneNumber$" "$int((N.Location.X + R.End.Location.X) / 2)$" "$int((N.Location.Y + R.End.Location.Y) / 2)$" "$int((N.Location.Z + R.End.Location.Z) / 2));
		}
	}
	foreach PC.AllActors(class'Actor', A)
	{
		Kind = "";
		if (Pawn(A) != None && A != PC.Pawn)
			Kind = "pawn";
		else if (Mover(A) != None)
			Kind = "mover";
		else if (Triggers(A) != None)
			Kind = "trigger";
		else if (A.Event != '' && NavigationPoint(A) == None)
			Kind = "event";
		else if (PlayerStart(A) != None)
			Kind = "start";
		if (Kind != "")
			Log("Zones: actor "$Kind$" "$A.Region.ZoneNumber$" "$int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z)$" "$A.Class.Name$" tag="$A.Tag$" event="$A.Event);
	}
	// water: every water volume with its physics, every path point inside one, and how the player swims
	foreach PC.AllActors(class'PhysicsVolume', V)
		if (V.bWaterVolume)
			Log("Zones: water "$V.Name$" "$V.Region.ZoneNumber$" "$int(V.Location.X)$" "$int(V.Location.Y)$" "$int(V.Location.Z)$" friction="$V.FluidFriction$" gravity="$V.Gravity.Z$" terminal="$V.TerminalVelocity$" velocity="$V.ZoneVelocity$" pain="$V.bPainCausing$" tag="$V.Tag);
	for (N = PC.Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
		if (N.PhysicsVolume != None && N.PhysicsVolume.bWaterVolume)
			Log("Zones: wetnav "$N.Name$" "$N.PhysicsVolume.Name$" "$int(N.Location.X)$" "$int(N.Location.Y)$" "$int(N.Location.Z));
	if (PC.Pawn != None)
		Log("Zones: swim WaterSpeed="$PC.Pawn.WaterSpeed$" GroundSpeed="$PC.Pawn.GroundSpeed$" UnderWaterTime="$PC.Pawn.UnderWaterTime);
	if (PC.Pawn != None)
		Log("Zones: player "$PC.Pawn.Region.ZoneNumber$" "$int(PC.Pawn.Location.X)$" "$int(PC.Pawn.Location.Y)$" "$int(PC.Pawn.Location.Z));
	Log("Zones: map "$PC.Level.Outer.Name);
	Say("zones: "$Navs$" navigation points, "$Links$" zone-crossing paths (see the log)");
}


// hub beats: the level's event wiring, for the beat graph (story spine) of a level remix.
// Unreal levels are wired with names: an actor fires its Event, every actor whose Tag matches
// reacts. Logs "Beats:" lines for every actor that fires an event or receives one: class, zone,
// position, tag, event, plus what kind of thing it is (door, cutscene, sound, exit...).
// tools/python/U2Pilot/beatgraph.py draws the graph and finds the order along the path.
// events an actor fires besides its Event: dispatchers' lists, cutscene trigger sub-actions,
// spawners, stage triggers, door bumps, AI script chains
function ExtraEvents(Actor A, out array<name> E)
{
	local int i, k;
	local SceneManager S;

	E.Length = 0;
	if (Dispatcher(A) != None)
		for (i = 0; i < 8; i++)
			if (Dispatcher(A).OutEvents[i] != '') E[E.Length] = Dispatcher(A).OutEvents[i];
	if (RoundRobin(A) != None)
		for (i = 0; i < 16; i++)
			if (RoundRobin(A).OutEvents[i] != '') E[E.Length] = RoundRobin(A).OutEvents[i];
	if (StageTrigger(A) != None)
		for (i = 0; i < 8; i++)
		{
			if (StageTrigger(A).DispatcherTags[i] != '') E[E.Length] = StageTrigger(A).DispatcherTags[i];
			if (StageTrigger(A).WaterEvents[i] != '') E[E.Length] = StageTrigger(A).WaterEvents[i];
		}
	if (ActorFactory(A) != None)
	{
		if (ActorFactory(A).DepletedEvent != '') E[E.Length] = ActorFactory(A).DepletedEvent;
	}
	if (Mover(A) != None)
	{
		if (Mover(A).BumpEvent != '') E[E.Length] = Mover(A).BumpEvent;
		if (Mover(A).PlayerBumpEvent != '') E[E.Length] = Mover(A).PlayerBumpEvent;
	}
	if (AIScript(A) != None && AIScript(A).NextScriptTag != '')
		E[E.Length] = AIScript(A).NextScriptTag;
	S = SceneManager(A);
	if (S != None)
		Log("Beats: scene "$S.Name$" actions "$S.Actions.Length);
	if (S != None)
		for (i = 0; i < S.Actions.Length; i++)
			if (S.Actions[i] != None)
				for (k = 0; k < S.Actions[i].SubActions.Length; k++)
					if (SubActionTrigger(S.Actions[i].SubActions[k]) != None && SubActionTrigger(S.Actions[i].SubActions[k]).EventName != '')
						E[E.Length] = SubActionTrigger(S.Actions[i].SubActions[k]).EventName;
}

function Beats()
{
	local Actor A;
	local array<name> More;
	local int k, Logged;
	local bool bCustomTag;
	local string Kind, Extra;

	// one pass: every actor that fires something (Event or an event list) or carries its own tag
	// (anything else keeps its class name as tag and can't be a target). beatgraph.py links them.
	foreach PC.AllActors(class'Actor', A)
	{
		ExtraEvents(A, More);
		bCustomTag = A.Tag != '' && A.Tag != 'None' && string(A.Tag) != string(A.Class.Name);
		if (!bCustomTag && (A.Event == '' || A.Event == 'None') && More.Length == 0 && SceneManager(A) == None && Teleporter(A) == None)
			continue;
		Logged++;
		Kind = "other";
		Extra = "";
		if (Mover(A) != None)                Kind = "door";
		else if (SceneManager(A) != None)    Kind = "cutscene";
		else if (Teleporter(A) != None)      { Kind = "exit"; Extra = " url="$Teleporter(A).URL; }
		else if (AIScript(A) != None)        Kind = "aiscript";
		else if (Pawn(A) != None)            Kind = "pawn";
		else if (AmbientSound(A) != None)    Kind = "sound";
		else if (Counter(A) != None)         Kind = "counter";
		else if (ObjectivesTrigger(A) != None) Kind = "objective";
		else if (Light(A) != None)           Kind = "light";
		else if (Emitter(A) != None)         Kind = "effect";
		else if (Triggers(A) != None)        Kind = "trigger";
		else if (InStr(Caps(string(A.Class.Name)), "SOUND") >= 0) Kind = "sound";
		Log("Beats: "$Kind$" "$A.Region.ZoneNumber$" "$int(A.Location.X)$" "$int(A.Location.Y)$" "$int(A.Location.Z)$" "$A.Class.Name$" "$A.Name$" tag="$A.Tag$" event="$A.Event$Extra);
		for (k = 0; k < More.Length; k++)
			Log("Beats: fires "$A.Name$" "$More[k]);
	}
	Log("Beats: map "$PC.Level.Outer.Name);
	Say("beats: "$Logged$" wired actors (see the log)");
}

defaultproperties
{
}