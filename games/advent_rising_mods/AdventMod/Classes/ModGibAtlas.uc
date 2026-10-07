//=============================================================================
// ModGibAtlas - settled gibs turned into flat snapshots on the floor (impostor cards), so a
// fight's mess stays on the floor without dozens of gib actors (the user's idea: a runtime
// "super texture", Rage-style, made from what is already on screen).
//
// One ScriptedTexture of Size x Size, cut into Tiles x Tiles tiles. When the gibs of one
// spot have all lain still for CardDelay seconds, a camera straight above them renders them
// and the blood around them into a free tile (ScriptedTexture.DrawPortal); a ModGibCard
// showing that tile is laid on the floor in their place and the gibs go. The engine only
// redraws a ScriptedTexture that something on screen uses, so the card waits on the floor
// at one unit across (drawn, too small to see) and grows to its size once its tile is taken. A tile in use again
// removes its old card (the oldest snapshot goes first).
// STATUS (2026-10-07): off by default. Proven: the atlas is redrawn while a waiting card is on
// screen (RenderTexture fires), DrawTile into it shows on the cards (CardDebug=1: red tiles), the
// tile mapping is right (TexScaler divides by its scale), cards replace the gibs. Not working:
// DrawPortal leaves the tile black, even with this actor moved to the camera first. Suspect the
// d3d8 layer (it swaps the scene's depth and render targets for the post chain; a second scene
// render into a 512 render target may hit that). Next: trace the layer during a capture.
//=============================================================================
class ModGibAtlas extends Info
	config(AdventMod);

var config bool bGibCards;
var config float CardDelay;        // seconds every gib of a spot has lain still before the snapshot
var config float CardReach;        // gibs within this of each other make one card
var config float CardLife;         // seconds a card stays
var config float CamHeight;        // how high above the gibs the snapshot camera wants to be
var config bool bCardLog;
var config int CardDebug;          // 1: tiles filled red instead of the camera's view (is the atlas shown at all?), 2: red then the view on top

var ScriptedTexture Atlas;
var int Size, Tiles, NextTile;
var ModGibCard Cards[16];

struct Shot
{
	var ModGibCard Card;
	var array<ModGib> Gibs;
	var vector Cam;
	var vector Floor;
	var int FOV;
	var int State;             // 0 waiting for the capture, 1 captured
	var float Age;
};
var array<Shot> Shots;
var ModGore Gore;
var float Look;

event PostBeginPlay()
{
	Super.PostBeginPlay();
	if (!bGibCards)
		return;
	Atlas = ScriptedTexture(Level.ObjectPool.AllocateObject(class'ScriptedTexture'));
	if (Atlas == None)
		return;
	Atlas.SetSize(Size, Size);
	Atlas.Client = self;
	if (bCardLog)
		class'ModSettings'.static.Note("gibcards: atlas " $ Atlas $ " " $ Size $ "x" $ Size);
}

event Destroyed()
{
	if (Atlas != None)
	{
		Atlas.Client = None;
		Level.ObjectPool.FreeObject(Atlas);
		Atlas = None;
	}
	Super.Destroyed();
}

// the camera's snapshot of every waiting shot, into its tile
event RenderTexture(ScriptedTexture Tex)
{
	local int i, X, Y, T;

	if (bCardLog)
		class'ModSettings'.static.Note("gibcards: atlas drawn (" $ Shots.Length $ " waiting)");

	for (i = 0; i < Shots.Length; i++)
	{
		if (Shots[i].State != 0 || Shots[i].Card == None)
			continue;
		T = Shots[i].Card.Tile;
		X = (T % Tiles) * (Size / Tiles);
		Y = (T / Tiles) * (Size / Tiles);
		if (CardDebug > 0)
			Tex.DrawTile(X, Y, Size / Tiles, Size / Tiles, 0, 0, 2, 2, Texture'Engine.WhiteSquareTexture', class'Canvas'.static.MakeColor(255, 0, 0));
		// the portal starts from the camera actor's zone: this actor goes to the camera first (left
		// where it spawned, it sat outside the level and every snapshot came out black)
		SetLocation(Shots[i].Cam);
		if (CardDebug != 1)
			Tex.DrawPortal(X, Y, Size / Tiles, Size / Tiles, self, Shots[i].Cam, rot(-16384,0,0), Shots[i].FOV, true);
		Shots[i].State = 1;
	}
}

// the material showing one tile, with the soft edge
function Material TileMaterial(ModGibCard C)
{
	local float K;

	// UE2's TexScaler divides the coordinates by its scale (a scale of 4 shows a quarter of
	// the texture: a card showed the whole atlas four times over with 0.25); offsets in texels
	K = Tiles;
	C.Scaler = TexScaler(Level.ObjectPool.AllocateObject(class'TexScaler'));
	C.Scaler.Material = Atlas;
	C.Scaler.UScale = K;
	C.Scaler.VScale = K;
	C.Scaler.UOffset = (C.Tile % Tiles) * (Size / Tiles);
	C.Scaler.VOffset = (C.Tile / Tiles) * (Size / Tiles);
	C.Comb = Combiner(Level.ObjectPool.AllocateObject(class'Combiner'));
	C.Comb.Material1 = C.Scaler;
	C.Comb.Material2 = C.Mask;
	C.Comb.CombineOperation = CO_Use_Color_From_Material1;
	C.Comb.AlphaOperation = AO_Use_Alpha_From_Material2;
	C.Final = FinalBlend(Level.ObjectPool.AllocateObject(class'FinalBlend'));
	C.Final.Material = C.Comb;
	C.Final.FrameBufferBlending = FB_AlphaBlend;
	C.Final.ZWrite = false;
	C.Final.ZTest = true;
	return C.Final;
}

function FreeCard(int T)
{
	local ModGibCard C;

	C = Cards[T];
	Cards[T] = None;
	if (C == None)
		return;
	if (C.Final != None) Level.ObjectPool.FreeObject(C.Final);
	if (C.Comb != None) Level.ObjectPool.FreeObject(C.Comb);
	if (C.Scaler != None) Level.ObjectPool.FreeObject(C.Scaler);
	if (!C.bDeleteMe)
		C.Destroy();
}

// a snapshot of the gibs around G, if they have all lain still long enough
function TryCard(ModGib G)
{
	local ModGib O;
	local array<ModGib> Group;
	local vector Mid, HitL, HitN;
	local float Ext, W, H;
	local int i, T, FOV;
	local Shot S;

	ForEach DynamicActors(class'ModGib', O)
		if (O.Class == class'ModGib' && !O.bCarding && VSize(O.Location - G.Location) < CardReach)
		{
			if (!O.bSettled || O.StillTime < 2)
				return;                         // something nearby still moving: later
			Group[Group.Length] = O;
			Mid += O.Location;
		}
	if (Group.Length == 0)
		return;
	Mid /= Group.Length;
	for (i = 0; i < Group.Length; i++)
		Ext = FMax(Ext, VSize((Group[i].Location - Mid) * vect(1,1,0)) + Group[i].Radius * 2);
	W = FClamp(Ext * 2 + 40, 80, 260);
	// the camera: up to CamHeight above, under any ceiling
	H = CamHeight;
	if (Trace(HitL, HitN, Mid + vect(0,0,1) * CamHeight, Mid, false) != None)
		H = VSize(HitL - Mid) - 10;
	if (H < 60)
		return;
	FOV = Clamp(int(2 * Atan(W, 2 * H) * 180 / Pi + 0.5), 10, 100);
	W = 2 * H * Tan(FOV * Pi / 360);            // the width that FOV covers exactly
	// the floor under them (the card's place)
	if (Trace(HitL, HitN, Mid - vect(0,0,200), Mid + vect(0,0,10), false) == None)
		return;
	T = NextTile;
	NextTile = (NextTile + 1) % (Tiles * Tiles);
	FreeCard(T);
	// the card waits on the floor at one unit across (still drawn, so the engine asks for the
	// atlas; under the floor it sat in solid space and was never drawn)
	S.Card = Spawn(class'ModGibCard',,, HitL + vect(0,0,1.5), rot(0,0,0));
	if (S.Card == None)
		return;
	S.Card.Tile = T;
	S.Card.Skins[0] = TileMaterial(S.Card);
	S.Card.SetDrawScale(1);
	S.Card.Width = W;
	S.Card.LifeSpan = CardLife;
	Cards[T] = S.Card;
	S.Gibs = Group;
	for (i = 0; i < Group.Length; i++)
		Group[i].bCarding = true;
	S.Cam = Mid + vect(0,0,1) * H;
	S.Floor = HitL;
	S.FOV = FOV;
	Shots[Shots.Length] = S;
	Atlas.Revision++;
	if (bCardLog)
		class'ModSettings'.static.Note("gibcards: " $ Group.Length $ " gibs at " $ Mid $ " -> tile " $ T $ ", " $ int(W) $ " wide, camera " $ int(H) $ " up, FOV " $ FOV);
}

event Tick(float DeltaTime)
{
	local int i, k;
	local ModGib G;

	if (!bGibCards || Atlas == None)
		return;
	for (i = Shots.Length - 1; i >= 0; i--)
	{
		Shots[i].Age += DeltaTime;
		if (Shots[i].Card == None || Shots[i].Card.bDeleteMe)
		{
			Shots.Remove(i, 1);
			continue;
		}
		if (Shots[i].State == 1)
		{
			// taken: the card comes up to the floor, the gibs go
			Shots[i].Card.SetDrawScale(Shots[i].Card.Width);
			for (k = 0; k < Shots[i].Gibs.Length; k++)
				if (Shots[i].Gibs[k] != None && !Shots[i].Gibs[k].bDeleteMe)
					Shots[i].Gibs[k].Destroy();
			Shots.Remove(i, 1);
		}
		else if (Shots[i].Age > 5)
		{
			// never captured (the card wasn't drawn: out of sight): try again from scratch
			for (k = 0; k < Shots[i].Gibs.Length; k++)
				if (Shots[i].Gibs[k] != None)
					Shots[i].Gibs[k].bCarding = false;
			FreeCard(Shots[i].Card.Tile);
			Shots.Remove(i, 1);
		}
		else
			Atlas.Revision++;
	}
	Look -= DeltaTime;
	if (Look > 0)
		return;
	Look = 1.0;
	ForEach DynamicActors(class'ModGib', G)
		if (G.Class == class'ModGib' && G.bSettled && !G.bCarding && G.StillTime > CardDelay)
		{
			TryCard(G);
			break;                              // one a second is plenty
		}
}

defaultproperties
{
     bGibCards=False
     CardDelay=6.000000
     CardReach=140.000000
     CardLife=600.000000
     CamHeight=260.000000
     Size=512
     Tiles=4
}
