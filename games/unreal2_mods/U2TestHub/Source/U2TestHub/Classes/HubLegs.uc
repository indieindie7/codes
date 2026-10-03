//=============================================================================
// HubLegs - "hub legs": foot-slide probe for your character. Every tick it
// tracks both feet relative to the pawn; while a foot is planted (lowest
// point of its cycle) its backward speed should equal the pawn's ground
// speed. Once a second it logs the pawn speed, the planted-foot speeds, the
// AnimAll clip/rate and the rate multiplier that would stop the sliding.
// "hub legs rate R" also compiles a one-off agent action that replays the
// current AnimAll clip at rate R (the live-rate test). "hub legs off" stops.
//=============================================================================
class HubLegs extends Info;

var Pawn Target;
var int FootL, FootR;
var vector PrevL, PrevR;
var bool bHavePrev;
var float LowL, LowR;          // lowest pawn-relative foot height seen (decays up)
var float SumL, SumR, CntL, CntR, SumBody, CntBody, Clock;
var float TryRate, Moving;
var byte Mode;                 // 0 probe only, 1 one-off agent action, 2 AnimRate each tick, 3 drive channel 0 ourselves
var float Mult;
var name Playing;
var array<name> CName;         // per-clip totals for the summary at the end
var array<float> CBody, CPlant, CRate, CCount;

function int FindNode(Pawn P, string Side)
{
	local int N;
	N = P.MeshGetNodeNamed("Merc "$Side$" Foot");
	if (N == 0) N = P.MeshGetNodeNamed("Bip01 "$Side$" Foot");
	if (N == 0) N = P.MeshGetNodeNamed("Marine "$Side$" Foot");
	return N;
}

function Setup(Pawn P, float R, optional byte M)
{
	Mode = M;
	Mult = R;
	Playing = '';
	Target = P;
	FootL = FindNode(P, "L");
	FootR = FindNode(P, "R");
	bHavePrev = false;
	LowL = 1000; LowR = 1000;
	if (Mode == 1) TryRate = R;
	Log("Hub: legs feet L "$FootL$" R "$FootR);
	Moving = 0;
}

function TryNow()
{
	local name Seq;
	local float Frame, Rate, Blend;
	local string Text;
	Target.GetAnimParams(0, Seq, Frame, Rate, Blend);
	Text = "set AnimAll { script \""$Target.MeshAgentGetChannelScriptName(0)$"\"; syncchannel AnimAll; rate "$TryRate$"; }";
	Log("Hub: legs before "$Seq$" frame "$Frame$" rate "$Rate$" -> "$Text$" = "$Target.MeshAgentImmediateAction(Text));
	Target.GetAnimParams(0, Seq, Frame, Rate, Blend);
	Log("Hub: legs after "$Seq$" frame "$Frame$" rate "$Rate);
}

// foot position in the pawn's yaw frame (X forward, Y right), relative to the pawn
function vector Local(int N)
{
	local rotator Yaw;
	Yaw.Yaw = Target.Rotation.Yaw;
	return (Target.MeshNodeGetTranslation(N, MESHNODEREL_World) - Target.Location) << Yaw;
}

// mode 3: the agent still picks the clip (its channel script name); we play it on channel 0 at Mult
function Drive()
{
	local name Want;
	Target.MeshAgentEnableChannel(0, false);
	Want = Target.MeshAgentGetChannelScriptName(0);
	if (Want == '')
		return;
	if (Want != Playing)
	{
		Target.LoopAnim(Want, Mult, 0.2, 0);
		Log("Hub: legs drive "$Want$" at "$Mult);
		Playing = Want;
	}
	else
		Target.LoopAnim(Want, Mult, 0.0, 0);
}

function AddClip(name Seq, float Body, float Plant, float Rate)
{
	local int i;
	for (i = 0; i < CName.Length; i++)
		if (CName[i] == Seq)
			break;
	if (i == CName.Length)
	{
		CName[i] = Seq; CBody[i] = 0; CPlant[i] = 0; CRate[i] = 0; CCount[i] = 0;
	}
	CBody[i] += Body; CPlant[i] += Plant; CRate[i] += Rate; CCount[i] += 1;
}

event Destroyed()
{
	local int i;
	for (i = 0; i < CName.Length; i++)
		if (CCount[i] >= 10)
			Log("Hub: legs clip "$CName[i]$" samples "$int(CCount[i])$" body "$CBody[i] / CCount[i]$" plant "$CPlant[i] / CCount[i]$" rate "$CRate[i] / CCount[i]
				$" -> stride speed per rate "$(CPlant[i] / CCount[i]) / FMax(CRate[i] / CCount[i], 0.01)$", rate for this body speed "$(CRate[i] / CCount[i]) * (CBody[i] / CCount[i]) / FMax(CPlant[i] / CCount[i], 1));
	if (Target != None && Mode == 3)
		Target.MeshAgentEnableChannel(0, true);
}

event Tick(float DeltaTime)
{
	local vector L, R, VL, VR, Flat;
	local float Body;
	local name Seq;
	local float Frame, Rate, Blend;

	if (Target == None || Target.Health <= 0 || FootL == 0 || FootR == 0 || DeltaTime <= 0)
		return;
	if (Mode == 2)
		Target.AnimRate = Mult;
	else if (Mode == 3)
		Drive();
	L = Local(FootL);
	R = Local(FootR);
	Flat = Target.Velocity;
	Flat.Z = 0;
	Body = VSize(Flat);
	LowL = FMin(LowL + 10 * DeltaTime, L.Z);
	LowR = FMin(LowR + 10 * DeltaTime, R.Z);
	Target.GetAnimParams(0, Seq, Frame, Rate, Blend);
	if (bHavePrev && Body > 20 && Left(string(Seq), 2) ~= "A_")
	{
		VL = (L - PrevL) / DeltaTime; VL.Z = 0;
		VR = (R - PrevR) / DeltaTime; VR.Z = 0;
		if (L.Z < LowL + 2) { SumL += VSize(VL); CntL += 1; }
		if (R.Z < LowR + 2) { SumR += VSize(VR); CntR += 1; }
		SumBody += Body; CntBody += 1;
		if (L.Z < LowL + 2) AddClip(Seq, Body, VSize(VL), Rate);
		if (R.Z < LowR + 2) AddClip(Seq, Body, VSize(VR), Rate);
	}
	PrevL = L; PrevR = R; bHavePrev = true;
	if (Body > 100) Moving += DeltaTime; else Moving = 0;
	if (TryRate > 0 && Moving > 1.5)   // replay at the trial rate once, after 1.5 s of steady movement
	{
		TryNow();
		TryRate = 0;
	}

	Clock += DeltaTime;
	if (Clock >= 1.0)
	{
		Clock = 0;
		if (CntBody > 0 && CntL + CntR > 0)
			Log("Hub: legs speed "$SumBody / CntBody$" plantL "$SumL / FMax(CntL, 1)$" ("$int(CntL)$") plantR "$SumR / FMax(CntR, 1)$" ("$int(CntR)$") clip "$Seq$" frame "$Frame$" rate "$Rate$" -> ideal x"$(SumBody / CntBody) / FMax((SumL + SumR) / (CntL + CntR), 1));
		else
			Log("Hub: legs still, clip "$Seq$" rate "$Rate);
		SumL = 0; SumR = 0; CntL = 0; CntR = 0; SumBody = 0; CntBody = 0;
	}
}
