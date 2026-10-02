//=============================================================================
// DestructProbe - can a map's placed props be replaced at runtime? Destruction
// in the style of Black (props that chip, crack and break) needs three things the
// engine may or may not allow on a level's StaticMeshActors, which are bStatic:
//   1. hiding the original and switching its collision off
//   2. a spawned, non-static copy with the same mesh that blocks like the original
//   3. debris made from that mesh that falls, bounces and comes to rest
//      (not Karma: rigid-body Karma is switched off in Unreal II, "physKarma: This physics
//      type is obsolete in U2 829"; DestructDebris uses PHYS_Falling and bounces itself)
// Spawn it in front of the player (U2Pilot: spawn U2Destruct.DestructProbe 300).
// It picks the nearest solid prop, turns the view to it and runs one stage every
// two seconds, logging "DestructProbe: ..." lines to Unreal2.log.
//=============================================================================
class DestructProbe extends Actor;

var StaticMeshActor Target;
var PlayerController PC;
var DestructPiece Piece;
var DestructDebris Debris;
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

// the nearest prop with a mesh, preferring solid ones near the player's eye height (cover is
// what destruction is for; a roof or canopy far above makes a poor test)
function StaticMeshActor FindTarget()
{
	local StaticMeshActor S, Best, BestAny;
	local float D, BestD, BestAnyD, EyeZ;

	BestD = 1500;
	BestAnyD = 1500;
	EyeZ = Location.Z;
	if (PC != None && PC.Pawn != None)
		EyeZ = PC.Pawn.Location.Z + PC.Pawn.EyeHeight;
	foreach AllActors(class'StaticMeshActor', S)
	{
		if (S.StaticMesh == None)
			continue;
		D = VSize(S.Location - Location);
		if (D < BestAnyD) { BestAnyD = D; BestAny = S; }
		if (S.bBlockActors && Abs(S.Location.Z - EyeZ) < 150 && D < BestD) { BestD = D; Best = S; }
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

// what traces from the player's eyes towards the prop hit first: nine rays aimed across the
// prop (its collision cylinder: middle, sides, top and bottom), each continuing 200 units
// past it. A single ray through the origin can miss a prop whose origin is in empty space.
// "prop" = the target (or its copy), "world" = level geometry, else the actor hit.
function string BlockedBy()
{
	local vector Start, Aim, Side, End, HitLoc, HitNorm;
	local Actor Hit;
	local int i, OnProp, OnWorld, OnOther, Missed;
	local float R, H;
	local string First;

	if (PC == None || PC.Pawn == None)
		return "no player";
	Start = PC.Pawn.Location + vect(0,0,1) * PC.Pawn.EyeHeight;
	R = FMax(Target.CollisionRadius, 16) * 0.5;
	H = FMax(Target.CollisionHeight, 16) * 0.5;
	Side = Normal((Target.Location - Start) cross vect(0,0,1));
	for (i = 0; i < 9; i++)
	{
		Aim = Target.Location + Side * R * ((i % 3) - 1) + vect(0,0,1) * H * ((i / 3) - 1);
		End = Aim + Normal(Aim - Start) * 200;
		Hit = PC.Pawn.Trace(HitLoc, HitNorm, End, Start, true);
		if (Hit == None)
			Missed++;
		else if (Hit == Target || (Piece != None && Hit == Piece))
			OnProp++;
		else if (Hit == Level || Hit.IsA('LevelInfo'))
			OnWorld++;
		else
			OnOther++;
		if (Hit != None && First == "")
			First = " (first hit: "$Hit$" at "$int(VSize(HitLoc - Start))$" units)";
	}
	return "of 9 rays: prop "$OnProp$", world "$OnWorld$", other "$OnOther$", nothing "$Missed$First;
}

event Timer()
{
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
		// stage 4: debris from the same mesh, a quarter size, thrown up and sideways from
		// above the prop: it should fall, bounce and come to rest on the floor
		DebrisStart = Target.Location + vect(0,0,160);
		Debris = Spawn(class'DestructDebris',,, DebrisStart, Target.Rotation);
		if (Debris == None)
		{
			Log("DestructProbe: stage 4 debris spawn FAILED");
			break;
		}
		Debris.Launch(Target.StaticMesh, Target.DrawScale * 0.25, VRand() * 150 + vect(0,0,200));
		Log("DestructProbe: stage 4 debris "$Debris$" physics "$Debris.GetPropertyText("Physics")$" at "$Debris.Location);
		break;
	case 4:
		break;
	case 5:
		if (Debris != None)
			Log("DestructProbe: stage 4 result after 4 s: physics "$Debris.GetPropertyText("Physics")$" bounces "$Debris.Bounces
				$" dropped "$int(DebrisStart.Z - Debris.Location.Z)$" units (about 160 = landed on the floor,"
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
