//=============================================================================
// ModPanel - a translucent panel behind an options page (title, rows, Reset), so the
// game's dark labels stay readable over whatever is behind the menu.
// Pages call class'ModPanel'.static.AddTo(self) at the end of
// SetupInitalPositions (the rows' positions are known then).
//=============================================================================
class ModPanel extends Object
	config(AdventMod);

var config bool bPanel;       // draw it at all
var config color PanelColor;  // A = how solid (0-255)

static function AddTo(MenuPauseOptionsBase Page)
{
	local GUIImage Panel;
	local float Top, Bottom;

	if (!default.bPanel || Page.NumOptions < 1)
		return;
	// from above the page's title (and "Back") to below the last row, or the Reset button
	Top = Page.TitleLabel.WinTop - 0.035;
	Bottom = Page.LinePositions[Page.NumOptions - 1] + 0.055;
	if (!Page.bNoResetButton)
		Bottom = Page.ResetButton.WinTop + 0.0825;
	Panel = new(None) class'GUIImage';
	Panel.Image = Texture'Engine.WhiteSquareTexture';
	Panel.ImageStyle = ISTY_Stretched;
	Panel.ImageRenderStyle = MSTY_Alpha;
	Panel.ImageColor = default.PanelColor;
	Panel.WinLeft = 0.03;
	Panel.WinWidth = 0.81;
	Panel.WinTop = Top;
	Panel.WinHeight = Bottom - Top;
	// lower than every other component's weight: drawn first, under the rows
	Panel.RenderWeight = 0.0;
	Page.AppendComponent(Panel);
}

defaultproperties
{
     bPanel=True
     PanelColor=(R=255,G=255,B=255,A=120)
}
