//=============================================================================
// U2Gore - a short-lived spurt at the wound itself, distinct from the ground
// decal: oriented along the hit normal, meant to read as "damage just
// landed" feedback on every qualifying hit, not only on death.
//
// Extends 'Emitter' as a placeholder base - wire ParticleTemplate/whatever
// generator setup your Unreal2 SDK's particle emitters actually use (check
// an existing weapon-impact effect in your content for the real base class
// and template-assignment pattern before treating this as more than
// scaffolding).
//=============================================================================
class U2BloodSpurt extends Emitter;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	DrawScale *= 0.85 + FRand() * 0.3;
	LifeSpan = 1.0 + FRand() * 0.5; // brief - this is a hit reaction, not a decal
}

defaultproperties
{
	RemoteRole=ROLE_None
}
