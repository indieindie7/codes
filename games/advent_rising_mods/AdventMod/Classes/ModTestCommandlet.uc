//=============================================================================
// ModTestCommandlet - "AdventUCC AdventMod.ModTest": checks that the engine
// loads AdventNative.dll by itself and that script can call into it.
//=============================================================================
class ModTestCommandlet extends Commandlet;

event int Main(string Parms)
{
	local bool bFirst, bSecond;

	bFirst = class'ModSettings'.static.NativeCall("Init");
	bSecond = class'ModSettings'.static.NativeCall("Init");
	Warn("AdventMod test: first call " $ bFirst $ ", second call " $ bSecond $ ", IsBorderless " $ class'ModSettings'.static.NativeCall("IsBorderless"));
	// distinct codes, so a run where this event never executed (0) can't pass
	if (bSecond && !bFirst)
		return 7;
	if (bSecond)
		return 8;
	return 3;
}

defaultproperties
{
}
