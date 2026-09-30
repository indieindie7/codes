//=============================================================================
// SSMenuHelper - the Options > Shadows page's link to the add-on's settings.
// The menu scripts (UIScripts) bind each slider or checkbox to a Get<Name> /
// Set<Name> pair on a helper object; this one reads and writes the
// SSShadowController config values, saves them, and asks the running manager
// (if a level is loaded) to rebuild the shadows with the new values.
// Registered with the UI through PlugIn=U2SoftShadows.SSMenuHelper in
// Unreal2.ini's [UI.UIConsole] section.
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
function float GetStrength()            { return class'SSShadowController'.default.ShadowStrength; }
function SetStrength(float F)           { class'SSShadowController'.default.ShadowStrength = F; Apply(); }
function float GetFadeLength()          { return class'SSShadowController'.default.GradientScale; }
function SetFadeLength(float F)         { class'SSShadowController'.default.GradientScale = F; Apply(); }

// --- extras
function bool GetContact()              { return class'SSShadowController'.default.bContactShadow; }
function SetContact(bool B)             { class'SSShadowController'.default.bContactShadow = B; Apply(); }
function bool GetHardToSoft()           { return class'SSShadowController'.default.bHardToSoft; }
function SetHardToSoft(bool B)          { class'SSShadowController'.default.bHardToSoft = B; Apply(); }
function bool GetCapsules()             { return class'SSShadowController'.default.bCapsules; }
function SetCapsules(bool B)            { class'SSShadowController'.default.bCapsules = B; Apply(); }
function bool GetWeighted()             { return class'SSShadowController'.default.bWeightedPick; }
function SetWeighted(bool B)            { class'SSShadowController'.default.bWeightedPick = B; Apply(); }

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
