//=============================================================================
// DestructProbe - can a map's placed props be replaced at runtime? Destruction
// in the style of Black (props that chip, crack and break) needs three things the
// engine may or may not allow on a level's StaticMeshActors, which are bStatic:
//   1. hiding the original and switching its collision off
//   2. a spawned, non-static copy with the same mesh that blocks like the original
//   3. Karma debris made from that mesh that falls and comes to rest
// Spawn it in front of the player (U2Pilot: spawn U2Destruct.DestructProbe 300).
// It picks the nearest solid prop, turns the view to it and runs one stage every
// two seconds, logging "DestructProbe: ..." lines to Unreal2.log.
//=============================================================================
class DestructProbe extends Actor;

var StaticMeshActor Target;
var PlayerController PC;
var DestructPiece Piece;
var Actor Debris;
var vector DebrisStart;
var int Stage;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	foreach DynamicActors(class'PlayerController', PC)
		break;
	Target = FindTarget();
	if (Target == None)
	{
		Log("DestructProbe: no StaticMeshActor with a mesh within 1500 units");
		Destroy();
		return;
	}
	Log("DestructProbe: target "$Target$" mesh "$Target.StaticMesh$" at "$Target.Location
		$" scale "$Target.DrawScale$" "$Target.DrawScale3D$" bStatic "$Target.bStatic
		$" collide "$Target.bCollideActors$" block "$Target.bBlockActors$"/"$Target.bBlockPlayers
		$" worldgeo "$Target.GetPropertyText("bWorldGeometry")$" hidden "$Target.bHidden
		$" skins "$Target.GetPropertyText("Skins"));
	FaceTarget();
	Log("DestructProbe: stage 1 original blocks a trace: "$BlockedBy());
	SetTimer(2.0, true);
}

// the nearest prop with a mesh, preferring solid ones (cover is what destruction is for)
function StaticMeshActor FindTarget()
{
	local StaticMeshActor S, Best, BestAny;
	local float D, BestD, BestAnyD;

	BestD = 1500;
	BestAnyD = 1500;
	foreach AllActors(class'StaticMeshActor', S)
	{
		if (S.StaticMesh == None)
			continue;
		D = VSize(S.Location - Location);
		if (D < BestAnyD) { BestAnyD = D; BestAny = S; }
		if (S.bBlockActors && D < BestD) { BestD = D; Best = S; }
	}
	if (Best != None)
		return Best;
	return BestAny;
}

function FaceTarget()
{
	local rotator R;

	if (PC == None || PC.Pawn == None)
		return;
	R = rotator(Target.Location - (PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight));
	PC.SetRotation(R);
	PC.Pawn.SetRotation(R);
	PC.ClientSetRotation(R);
}

// what a trace from the player's eyes through the prop's middle hits first
function string BlockedBy()
{
	local vector Start, End, HitLoc, HitNorm;
	local Actor Hit;

	if (PC == None || PC.Pawn == None)
		return "no player";
	Start = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	End = Target.Location + vect(0,0,32);
	End += Normal(End - Start) * 200;
	Hit = PC.Pawn.Trace(HitLoc, HitNorm, End, Start, true);
	if (Hit == None)
		return "nothing";
	return string(Hit)$" at "$int(VSize(HitLoc - Start))$" units";
}

event Timer()
{
	local class<Actor> KClass;

	Stage++;
	if (Target == None || Target.bDeleteMe)
	{
		Log("DestructProbe: target gone at stage "$Stage);
		Destroy();
		return;
	}
	switch (Stage)
	{
	case 1:
		// stage 2: hide the original and turn its collision off
		Target.bHidden = true;
		Target.SetCollision(false, false, false);
		Log("DestructProbe: stage 2 after hide+SetCollision(off): hidden "$Target.bHidden
			$" collide "$Target.bCollideActors$" block "$Target.bBlockActors$" trace hits: "$BlockedBy());
		break;
	case 2:
		// stage 3: a movable copy in its place, solid
		Piece = Spawn(class'DestructPiece',,, Target.Location, Target.Rotation);
		if (Piece == None)
		{
			Log("DestructProbe: stage 3 copy spawn FAILED (blocked?)");
			break;
		}
		Piece.Copy(Target);
		Log("DestructProbe: stage 3 copy "$Piece$" mesh "$Piece.StaticMesh$" at "$Piece.Location
			$" collide "$Piece.bCollideActors$" block "$Piece.bBlockActors$" trace hits: "$BlockedBy());
		break;
	case 3:
		// stage 4: Karma debris from the same mesh, half size, dropped from above
		KClass = class<Actor>(DynamicLoadObject("Engine.KActor", class'Class'));
		if (KClass == None)
		{
			Log("DestructProbe: stage 4 no Engine.KActor class");
			break;
		}
		DebrisStart = Target.Location + vect(0,0,160);
		Debris = Spawn(KClass,,, DebrisStart, Target.Rotation);
		if (Debris == None)
		{
			Log("DestructProbe: stage 4 KActor spawn FAILED");
			break;
		}
		// the mesh changes after spawning, so restart the KActor's own physics (Karma,
		// named through its default rather than PHYS_Karma, which this build may lack)
		Debris.StaticMesh = Target.StaticMesh;
		Debris.SetDrawType(DT_StaticMesh);
		Debris.SetDrawScale(Target.DrawScale * 0.5);
		Debris.SetPhysics(PHYS_None);
		Debris.SetPhysics(KClass.default.Physics);
		Log("DestructProbe: stage 4 debris "$Debris$" physics "$Debris.GetPropertyText("Physics")
			$" KParams "$Debris.GetPropertyText("KParams")$" at "$Debris.Location);
		break;
	case 4:
		break;
	case 5:
		if (Debris != None)
			Log("DestructProbe: stage 4 result after 4 s: physics "$Debris.GetPropertyText("Physics")$" dropped "
				$int(DebrisStart.Z - Debris.Location.Z)$" units (about 160 = landed on the floor,"
				$" 0 = never moved, far more = fell through)");
		Log("DestructProbe: done");
		SetTimer(0, false);
		break;
	}
}

defaultproperties
{
	bHidden=True
	bCollideActors=False
	bCollideWorld=False
	RemoteRole=ROLE_None
}
