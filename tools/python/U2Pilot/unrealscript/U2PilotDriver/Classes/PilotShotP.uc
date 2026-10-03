//=============================================================================
// PilotShotP - asks the d3d8 fork (U2Shaders) for a screenshot of the frame as
// presented, after post-processing: bumping shotp= in U2Shaders.ini makes it save
// the next frame as System\ShotP#####.bmp. The game's own "shot" reads the frame
// before post runs in frames without a 2D draw (cutscenes).
//=============================================================================
class PilotShotP extends Object
	config(U2Shaders);

var config int shotp;

defaultproperties
{
}
