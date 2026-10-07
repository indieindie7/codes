//=============================================================================
// AutoBrain - what the autoplayer wants, a few times a second:
//   * explore: the nearest navigation point it hasn't been to that the
//     engine can find a path to (Controller.FindPathToActor, the bots' own
//     path network), walked waypoint by waypoint; FindRandomDest when all are
//     visited;
//   * fight back: any pawn whose AI has the player as its enemy and is in
//     sight gets looked at and fired on until it's dead or gone;
//   * get unstuck: barely moved in 2 s -> jump, strafe a moment, press Use
//     (doors, lifts, switches); stuck three times on one goal -> give it up.
// AutoInput turns these wants into key presses each frame (Keys). Every
// decision is logged ("AutoPlay: ...") so a run can be read back as a report.
//=============================================================================
class AutoBrain extends Info;

var bool bOn;
var PlayerController PC;

var NavigationPoint Goal;
var Actor Next;
var vector GoalPoint;          // "autoplay goto": a point instead of a navigation point
var bool bGoPoint;
var array<NavigationPoint> Visited;
var Pawn Target;

// what AutoInput presses
var float Fwd, Strafe;
var rotator Want;
var bool bWantFire, bWantJump, bWantUse;
var float UseTime, StrafeTime;

// bookkeeping
var float ThinkWait, StuckWait, ReportWait;
var vector LastSpot;
var int Stuck, Reached, Fights, GiveUps;
var float StartTime;

function Command(string Args)
{
	local string W;

	W = Caps(Args);
	if (W == "ON")
	{
		bOn = true;
		StartTime = Level.TimeSeconds;
		Say("on");
	}
	else if (W == "OFF")
	{
		bOn = false;
		Release();
		Say("off");
	}
	else if (W == "EXPLORE")
	{
		Visited.Length = 0;
		Goal = None;
		bGoPoint = false;
		Say("exploring again");
	}
	else if (Left(W, 4) == "GOTO")
	{
		GoalPoint.X = float(Word(Args, 1));
		GoalPoint.Y = float(Word(Args, 2));
		GoalPoint.Z = float(Word(Args, 3));
		bGoPoint = true;
		Goal = None;
		Say("going to "$GoalPoint);
	}
	else
		Report();
}

function string Word(string S, int n)
{
	local int i;

	for (i = 0; i < n; i++)
	{
		if (InStr(S, " ") < 0)
			return "";
		S = Mid(S, InStr(S, " ") + 1);
	}
	if (InStr(S, " ") >= 0)
		S = Left(S, InStr(S, " "));
	return S;
}

function Say(coerce string S)
{
	Log("AutoPlay: "$S);
	if (PC != None)
		PC.ClientMessage("[autoplay] "$S);
}

function Report()
{
	local string Where;

	if (PC != None && PC.Pawn != None)
		Where = int(PC.Pawn.Location.X)$" "$int(PC.Pawn.Location.Y)$" "$int(PC.Pawn.Location.Z)$" health "$PC.Pawn.Health;
	else
		Where = "no pawn";
	Say("status: "$Where$", goal "$Goal$", visited "$Visited.Length$", reached "$Reached$", stuck "$Stuck
		$", gave up "$GiveUps$", fights "$Fights$", "$int(Level.TimeSeconds - StartTime)$" s");
}

// let go of every key
function Release()
{
	Fwd = 0;
	Strafe = 0;
	bWantFire = false;
	bWantJump = false;
	if (PC != None)
	{
		if (PC.bFire != 0)
			PC.bFire = 0;
		if (bWantUse)
			PC.Unuse();
	}
	bWantUse = false;
}

function bool CanAct()
{
	return bOn && PC != None && PC.Pawn != None && PC.Pawn.Health > 0 && Level.Pauser == None
		&& !PC.bInterpolating && !PC.Pawn.bInterpolating;
}

function bool IsVisited(NavigationPoint N)
{
	local int i;

	for (i = 0; i < Visited.Length; i++)
		if (Visited[i] == N)
			return true;
	return false;
}

function MarkVisited(NavigationPoint N)
{
	if (N != None && !IsVisited(N))
		Visited[Visited.Length] = N;
}

// the nearest unvisited navigation point a path leads to
function PickGoal()
{
	local NavigationPoint N, Best;
	local float D, BestD;
	local Actor Ret;
	local byte R;
	local int Tries;

	for (Tries = 0; Tries < 6; Tries++)
	{
		Best = None;
		BestD = 1000000000.0;
		for (N = Level.NavigationPointList; N != None; N = N.nextNavigationPoint)
		{
			if (IsVisited(N))
				continue;
			D = VSize(N.Location - PC.Pawn.Location);
			if (D > 150 && D < BestD)
			{
				BestD = D;
				Best = N;
			}
		}
		if (Best == None)
		{
			// everything seen: wander
			Best = PC.FindRandomDest();
			if (Best == None)
				return;
			Goal = Best;
			Say("all "$Visited.Length$" places visited; wandering to "$Goal);
			return;
		}
		R = PC.FindPathToActor(Best, Ret);
		if (R != 0)
		{
			Goal = Best;
			Log("AutoPlay: goal "$Goal$" "$int(BestD)$" away");
			return;
		}
		MarkVisited(Best);            // no path: skip it
	}
}

// the next waypoint toward the goal
function FindNext()
{
	local Actor Ret;
	local vector V;
	local byte R;

	Next = None;
	if (bGoPoint)
	{
		R = PC.FindPathToPoint(GoalPoint, V);
		if (R == 3 || R == 0)
			Next = None;        // straight at it (direct, or nothing better)
		else if (PC.RouteCache[0] != None)
			Next = PC.RouteCache[0];
		return;
	}
	if (Goal == None)
		return;
	R = PC.FindPathToActor(Goal, Ret);
	if (R == 3)
		Next = Goal;
	else if (Ret != None)
		Next = Ret;
	else
		Next = Goal;
}

function Pawn FindTarget()
{
	local Pawn P, Best;
	local float D, BestD;

	BestD = 5000;
	foreach DynamicActors(class'Pawn', P)
	{
		if (P == PC.Pawn || P.Health <= 0 || P.Controller == None || P.Controller.ControllerEnemy != PC.Pawn)
			continue;
		D = VSize(P.Location - PC.Pawn.Location);
		if (D < BestD && PC.LineOfSightTo(P))
		{
			BestD = D;
			Best = P;
		}
	}
	return Best;
}

event Tick(float DeltaTime)
{
	local vector Aim, Dest;
	local float Yaw;

	if (!CanAct())
		return;
	ReportWait -= DeltaTime;
	if (ReportWait <= 0)
	{
		ReportWait = 15;
		Report();
	}
	if (StrafeTime > 0)
		StrafeTime -= DeltaTime;
	if (bWantUse)
	{
		UseTime -= DeltaTime;
		if (UseTime <= 0)
		{
			PC.Unuse();
			bWantUse = false;
		}
	}
	ThinkWait -= DeltaTime;
	if (ThinkWait > 0)
		return;
	ThinkWait = 0.2;

	// a fight comes first
	Target = FindTarget();
	if (Target != None)
	{
		if (!bWantFire)
		{
			Fights++;
			Say("fighting "$Target);
		}
		Aim = Target.Location - (PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight);
		Want = rotator(Aim);
		bWantFire = true;
		Fwd = 0;
		if (StrafeTime <= 0)
		{
			Strafe = (FRand() - 0.5) * 2;
			StrafeTime = 0.8;
		}
		return;
	}
	bWantFire = false;

	// the goal: reached? a new one?
	if (bGoPoint)
	{
		if (VSize(GoalPoint - PC.Pawn.Location) < 200)
		{
			Say("reached the point "$GoalPoint);
			bGoPoint = false;
		}
	}
	else
	{
		if (Goal != None && VSize(Goal.Location - PC.Pawn.Location) < 160)
		{
			MarkVisited(Goal);
			Reached++;
			Goal = None;
		}
		if (Goal == None)
			PickGoal();
	}
	FindNext();
	if (bGoPoint && Next == None)
		Dest = GoalPoint;
	else if (Next != None)
		Dest = Next.Location;
	else
	{
		Fwd = 0;
		return;
	}
	// mark waypoints passed on the way as visited too
	if (NavigationPoint(Next) != None && VSize(Next.Location - PC.Pawn.Location) < 160)
		MarkVisited(NavigationPoint(Next));

	Aim = Dest - PC.Pawn.Location;
	Want = rotator(Aim);
	Want.Pitch = 0;
	Yaw = Abs(((Want.Yaw - PC.Rotation.Yaw) & 65535) - 32768);      // 32768 = facing it
	if (Yaw > 32768 - 8000)
		Fwd = 1;
	else
		Fwd = 0.25;
	if (StrafeTime <= 0)
		Strafe = 0;

	// stuck?
	StuckWait -= 0.2;
	if (StuckWait <= 0)
	{
		StuckWait = 2;
		if (VSize(PC.Pawn.Location - LastSpot) < 60 && Fwd > 0)
		{
			Stuck++;
			bWantJump = true;
			Strafe = (FRand() - 0.5) * 2;
			StrafeTime = 0.9;
			if (!bWantUse)
			{
				PC.Use();
				bWantUse = true;
				UseTime = 0.4;
			}
			if (Stuck % 3 == 0 && Goal != None)
			{
				Say("stuck going for "$Goal$" at "$int(PC.Pawn.Location.X)$" "$int(PC.Pawn.Location.Y)$" "$int(PC.Pawn.Location.Z)$": giving it up");
				MarkVisited(Goal);
				GiveUps++;
				Goal = None;
			}
		}
		LastSpot = PC.Pawn.Location;
	}
}

// AutoInput, each frame before the engine reads the axes
function Keys(float DeltaTime)
{
	local rotator R;
	local int DY, DP;

	if (!CanAct())
		return;
	PC.aForward = 24000 * Fwd;
	PC.aStrafe = 24000 * Strafe;
	if (bWantJump)
	{
		PC.bPressedJump = true;
		bWantJump = false;
	}
	if (bWantFire && PC.bFire == 0)
	{
		PC.bFire = 1;
		PC.Fire();
	}
	else if (!bWantFire && PC.bFire != 0)
		PC.bFire = 0;
	// turn toward Want, quickly but not instantly (it reads as a player, not a snap)
	R = PC.Rotation;
	DY = ((Want.Yaw - R.Yaw + 32768) & 65535) - 32768;
	DP = ((Want.Pitch - R.Pitch + 32768) & 65535) - 32768;
	R.Yaw += DY * FMin(1, DeltaTime * 8);
	R.Pitch += DP * FMin(1, DeltaTime * 8);
	R.Roll = 0;
	PC.SetRotation(R);
}

defaultproperties
{
	RemoteRole=ROLE_None
}
