//=============================================================================
// SSMenuHelper - the Options > Shadows page's link to the add-on's settings
// (the page replaces the game's own shadow options: the add-on draws every
// character shadow). The menu scripts (UIScripts) bind each slider or checkbox
// to a Get<Name> / Set<Name> pair on a helper object; this one reads and writes
// the SSShadowController config values, saves them, and asks the running
// manager (if a level is loaded) to rebuild the shadows with the new values.
// Registered in the menu script itself ([SSMenuHelper] RegisterObj).
//=============================================================================
class SSMenuHelper extends UIHelper;

function Apply()
{
	local SSShadowManager M;
	local PlayerController PC;

	class'SSShadowController'.static.StaticSaveConfig();
	PC = GetPlayerOwner();
	if (PC == None)
		return;
	foreach PC.DynamicActors(class'SSShadowManager', M)
		M.ApplySettings();
}

// --- on/off
function bool GetEnabled()              { return class'SSShadowController'.default.bEnabled; }
function SetEnabled(bool B)             { class'SSShadowController'.default.bEnabled = B; Apply(); }

// --- how many and how dark
function float GetMaxShadows()          { return class'SSShadowController'.default.MaxShadows; }
function SetMaxShadows(float F)         { class'SSShadowController'.default.MaxShadows = int(F); Apply(); }
function float GetPlayerShadows()       { return class'SSShadowController'.default.PlayerMaxShadows; }
function SetPlayerShadows(float F)      { class'SSShadowController'.default.PlayerMaxShadows = int(F); Apply(); }
function float GetStrength()            { return class'SSShadowController'.default.ShadowStrength; }
function SetStrength(float F)           { class'SSShadowController'.default.ShadowStrength = F; Apply(); }
function float GetFadeLength()          { return class'SSShadowController'.default.GradientScale; }
function SetFadeLength(float F)         { class'SSShadowController'.default.GradientScale = F; Apply(); }
function bool GetRespectBaked()         { return class'SSShadowController'.default.bRespectBaked; }
function SetRespectBaked(bool B)        { class'SSShadowController'.default.bRespectBaked = B; Apply(); }

// --- cost
function bool GetCameraCull()           { return class'SSShadowController'.default.bCameraCull; }
function SetCameraCull(bool B)          { class'SSShadowController'.default.bCameraCull = B; Apply(); }
function float GetNearDistance()        { return class'SSShadowController'.default.NearDistance; }
function SetNearDistance(float F)       { class'SSShadowController'.default.NearDistance = F; Apply(); }
function float GetMidDistance()         { return class'SSShadowController'.default.MidDistance; }
function SetMidDistance(float F)        { class'SSShadowController'.default.MidDistance = F; Apply(); }

defaultproperties
{
}
