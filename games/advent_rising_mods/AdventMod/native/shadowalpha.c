/* shadowalpha.c - lets Advent Rising's shadow bitmaps keep their shadow.

   A character's shadow is drawn into a small (128x128) render target first: the
   target is cleared to grey and the character drawn over it, and the darkness goes
   into the alpha channel only. A blur pass and the projection onto the level then
   read that alpha. But the game masks alpha writes (D3DRS_COLORWRITEENABLE = 7,
   colour only) for the whole world part of every frame, to keep the screen's own
   alpha, and the shadow bitmaps are drawn inside that part. So the alpha stays
   empty and the projected shadow is a flat grey patch. Cards of the time that
   ignored the mask drew the shadow anyway, which is probably why the game's
   shadows were said to work only on one ATI card.

   The fix watches the device: while one of these small render targets is bound,
   alpha writes are on; when the game goes back to a full-size target, the mask the
   game asked for is put back. */
#include <windows.h>
#include <stdlib.h>

void Note(const wchar_t* Fmt, ...);
void* D3DGameDevice(void);    /* d3dtrace.c */

typedef long HR;
#define VT(obj) (*(void***)(obj))
enum { DEV_SetRenderTarget = 31, DEV_SetRenderState = 50 };
#define RS_COLORWRITEENABLE 168
#define RS_FOGENABLE 28
#define RS_CLIPPLANEENABLE 152
#define SHADOW_BITMAP_MAX 512 /* the shadow bitmaps are 128x128; the game's other targets are screen-sized */

typedef HR (__stdcall *SetRenderTarget_t)(void*, void*, void*);
typedef HR (__stdcall *SetRenderState_t)(void*, DWORD, DWORD);
static SetRenderTarget_t RealSetRenderTarget;
static SetRenderState_t RealSetRenderState;
static DWORD GameMask = 0xF;  /* what the game last asked for */
static DWORD GameFog;         /* the game's fog switch, likewise */
static DWORD GameClip;        /* and its user clip planes */
static int InShadow;          /* a shadow bitmap is bound */
static int Binds;
static int StageTest;           /* ADVENT_SHADOWTEST=1 */
static void** HookedTable;      /* the device method table we hooked */

static HR __stdcall HookSetRenderState(void* D, DWORD State, DWORD Value)
{
	if (State == RS_COLORWRITEENABLE)
	{
		GameMask = Value;
		if (InShadow) Value = 0xF;
	}
	/* no fog in a shadow bitmap: it's a flat silhouette, not a view of the level (outdoors,
	   fog applied to the silhouette pass under a replacement pixel shader emptied it) */
	if (State == RS_FOGENABLE)
	{
		GameFog = Value;
		if (InShadow) Value = 0;
	}
	if (State == RS_CLIPPLANEENABLE)
	{
		GameClip = Value;
		if (InShadow) Value = 0;
	}
	return RealSetRenderState(D, State, Value);
}

static HR __stdcall HookSetRenderTarget(void* D, void* RT, void* Z)
{
	if (RT)
	{
		/* IDirect3DSurface8::GetDesc (slot 8): D3DSURFACE_DESC, Width at +24, Height at +28 */
		typedef HR (__stdcall *GetDesc_t)(void*, DWORD*);
		DWORD Desc[8] = {0};
		int Small;
		((GetDesc_t)VT(RT)[8])(RT, Desc);
		Small = Desc[6] && Desc[6] <= SHADOW_BITMAP_MAX && Desc[7] <= SHADOW_BITMAP_MAX;
		if (Small && !InShadow && StageTest)
		{
			/* testing: clear texture-coordinate generation the terrain left on stages 2 and 3 */
			typedef HR (__stdcall *SetTSS_t)(void*, DWORD, DWORD, DWORD);
			SetTSS_t SetTSS = (SetTSS_t)VT(D)[63];
			SetTSS(D, 2, 11, 2); SetTSS(D, 2, 24, 0);
			SetTSS(D, 3, 11, 3); SetTSS(D, 3, 24, 0);
		}
		if (Small && !InShadow) { InShadow = 1; RealSetRenderState(D, RS_COLORWRITEENABLE, 0xF); RealSetRenderState(D, RS_FOGENABLE, 0); RealSetRenderState(D, RS_CLIPPLANEENABLE, 0); if (!Binds++) Note(L"shadowalpha: first shadow bitmap (%lux%lu): alpha writes on while it is drawn", Desc[6], Desc[7]); }
		else if (!Small && InShadow) { InShadow = 0; RealSetRenderState(D, RS_COLORWRITEENABLE, GameMask); RealSetRenderState(D, RS_FOGENABLE, GameFog); RealSetRenderState(D, RS_CLIPPLANEENABLE, GameClip); }
	}
	return RealSetRenderTarget(D, RT, Z);
}

static void* Patch(void** Table, int Slot, void* To)
{
	void* Old = Table[Slot];
	DWORD Prot;
	VirtualProtect(&Table[Slot], sizeof(void*), PAGE_EXECUTE_READWRITE, &Prot);
	Table[Slot] = To;
	VirtualProtect(&Table[Slot], sizeof(void*), Prot, &Prot);
	return Old;
}

/* Called at startup and again every half second: the game makes a new device when
   its window changes size, and a new device may come with a new method table. */
int ShadowAlphaApply(void)
{
	void* Dev;
	void** Table;
	char E[8];
	if (GetEnvironmentVariableA("ADVENT_SHADOWALPHA", E, sizeof(E)) && E[0] == '0') return 0;  /* testing: compare without it */
	if (GetEnvironmentVariableA("ADVENT_SHADOWTEST", E, sizeof(E))) StageTest = atoi(E);
	Dev = D3DGameDevice();
	if (!Dev) return 0;
	Table = VT(Dev);
	/* already hooked this device's table: another hook (the trace) may sit on top of ours now,
	   so don't go by what the slot holds, or the two hooks would end up calling each other */
	if (Table == HookedTable) return 1;
	HookedTable = Table;
	RealSetRenderTarget = (SetRenderTarget_t)Patch(Table, DEV_SetRenderTarget, HookSetRenderTarget);
	RealSetRenderState = (SetRenderState_t)Patch(Table, DEV_SetRenderState, HookSetRenderState);
	InShadow = 0;
	Note(L"shadowalpha: watching the device (%p) so shadow bitmaps keep their alpha", Dev);
	return 1;
}
