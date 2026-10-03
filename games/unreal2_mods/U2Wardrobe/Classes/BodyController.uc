//=============================================================================
// BodyController - the game's player controller, plus your own body in first
// person (WardrobeMutator makes the game use it when bFirstPersonBody is on).
//
// The engine never draws the "view actor" the camera belongs to; in first
// person that's your character. Here the game works out its camera exactly as
// always (the view target stays your character, so the first-person weapon and
// everything else that checks "viewing self" behave as before) and only the view
// actor handed to the renderer changes, to a hidden helper (FirstPersonBody), so
// your character is drawn - with its head and arms hidden and the camera moved
// to where its eyes are.
//
// The renderer also skips what the view actor owns, like the held weapon: with
// the helper as view actor the weapon would be drawn in the world as well as on
// top of the view, so it is hidden from the world while the body is shown (the
// first-person drawing on top doesn't depend on that).
//=============================================================================
class BodyController extends U2PlayerNetTestController;

var FirstPersonBody Body;
var Weapon HiddenWeapon;         // the weapon hidden from the world (to give back)
var bool bWeaponWasHidden;

function HideWeapon(Weapon W)
{
	if (W == HiddenWeapon)
		return;
	ShowWeapon();
	if (W == None)
		return;
	HiddenWeapon = W;
	bWeaponWasHidden = W.bHidden;
	W.bHidden = true;
}

function ShowWeapon()
{
	if (HiddenWeapon != None && !HiddenWeapon.bDeleteMe)
		HiddenWeapon.bHidden = bWeaponWasHidden;
	HiddenWeapon = None;
}

event PlayerCalcView(out Actor ViewActor, out vector CameraLocation, out rotator CameraRotation)
{
	local vector GameCamera;

	Super.PlayerCalcView(ViewActor, CameraLocation, CameraRotation);
	if (Body == None || Body.bDeleteMe)
	{
		ShowWeapon();
		WeaponKickOffset = vect(0,0,0);
		return;
	}
	if (ViewActor == Pawn && Pawn != None && !bBehindView && Pawn.Health > 0)
	{
		ViewActor = Body;
		GameCamera = CameraLocation;
		CameraLocation = Body.Show(Pawn, CameraLocation);
		HideWeapon(Pawn.Weapon);
		// the first-person weapon is placed from the game's eye point: move it with the camera
		// (U2Weapon.CalcDrawOffset adds WeaponKickOffset; the game's own kick code is disabled)
		// the first-person gun is placed from the pawn's eye height, not from WeaponKickOffset's
		// height (tested: a lowered camera saw the gun from below with or without the offset):
		// put the eye at the camera's height, and only the sideways part in the offset
		if (Body.bGunWithCamera)
		{
			WeaponKickOffset = CameraLocation - GameCamera;
			Pawn.EyeHeight += WeaponKickOffset.Z;
			WeaponKickOffset.Z = 0;
		}
		else
			WeaponKickOffset = vect(0,0,0);
		if (Body.bGunEyeHeight && Pawn.Weapon != None)
			WeaponKickOffset = vect(0,0,0);   // the camera is the eye point already
	}
	else
	{
		Body.Hide();
		ShowWeapon();
		WeaponKickOffset = vect(0,0,0);
	}
}

defaultproperties
{
}
