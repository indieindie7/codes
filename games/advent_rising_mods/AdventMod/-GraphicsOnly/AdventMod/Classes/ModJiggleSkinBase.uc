//=============================================================================
// ModJiggleSkinBase - the hook for the filled Seeker skin (JIGGLE.md phase B). In the repo Skin is None.
// build.ps1 -JiggleSkin patches the GAME-FOLDER copy of this file (never the repo) with the #exec TEXTURE
// IMPORT of seeker_infantry_filled.tga and Skin=Texture'AdventMod.Skins.SeekerSkinJ', so that build's
// AdventMod.u carries the texture and ModJiggle (class'ModJiggleSkinBase'.default.Skin) can wear it.
// Compile-time on purpose: a run-time load by name of anything inside AdventMod (a class, a texture)
// answers nothing in this engine.
//=============================================================================
class ModJiggleSkinBase extends Object;

var Texture Skin;

defaultproperties
{
}
