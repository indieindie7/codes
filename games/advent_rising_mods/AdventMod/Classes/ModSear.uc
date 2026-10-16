//=============================================================================
// ModSear - where a plasma bolt hit a body (PLASMA-AND-PENETRATION.md): a small glow
// riding the nearest bone that cools as the wall burns do (ModGore.Burns: white-hot,
// orange, ember), dimming over Life seconds, then gone. Drawn added (STY_Translucent),
// so the cooling frames fade into the skin by themselves.
//=============================================================================
class ModSear extends Actor;

var Material Frames[3];
var float Life, Age, Size0;

function Start(Material F0, Material F1, Material F2, float Size, float L)
{
	Frames[0] = F0;
	Frames[1] = F1;
	Frames[2] = F2;
	Texture = F0;
	Size0 = Size;
	SetDrawScale(Size);
	Life = L;
	Age = 0;
}

event Tick(float DeltaTime)
{
	local int f;

	Age += DeltaTime;
	if (Age >= Life)
	{
		Destroy();
		return;
	}
	f = Min(int(3 * Age / Life), 2);
	if (Texture != Frames[f])
		Texture = Frames[f];
	ScaleGlow = 1.6 * (1 - Age / Life);
	SetDrawScale(Size0 * (1 - 0.4 * Age / Life));
}

defaultproperties
{
     DrawType=DT_Sprite
     Style=STY_Translucent
     bUnlit=True
     bHidden=False
     Physics=PHYS_None
     bCollideActors=False
     bCollideWorld=False
     bBlockActors=False
     bBlockPlayers=False
     bShadowCast=False
     bAcceptsProjectors=False
     RemoteRole=ROLE_None
     DrawScale=0.08
     Life=3.0
}
