/* d3dtrace.c - a small Direct3D 8 call tracer for AdventNative (debugging only).

   Every IDirect3DDevice8 made by one d3d8.dll shares one method table, so we
   create a throwaway device, patch the table, and the game's own device goes
   through our functions from then on. We count what projectors need:
   texture stages set to projected texturing, draws made while such a stage is
   active, render-target textures (shadow bitmaps) and their formats. */
#include <windows.h>
#include <float.h>
#include <stdio.h>
#include <intrin.h>

void Note(const wchar_t* Fmt, ...);
static void StackScan(const wchar_t* Why);
static void SiteReport(void);
static int Readable(const void* P, SIZE_T N);
static HMODULE ModuleOf(const void* P);

typedef long HR;
#define VT(obj) (*(void***)(obj))

/* IDirect3D8 method slots */
enum { D3D_Release = 2, D3D_GetAdapterDisplayMode = 8, D3D_CheckDeviceFormat = 10, D3D_GetDeviceCaps = 13, D3D_CreateDevice = 15 };
/* IDirect3DDevice8 method slots */
enum { DEV_SetTransform = 37, DEV_SetVertexShader = 76, DEV_SetPixelShader2 = 88,
	DEV_Release = 2, DEV_Present = 15, DEV_CreateTexture = 20, DEV_SetRenderTarget = 31, DEV_SetRenderState = 50,
	DEV_SetTexture = 61, DEV_SetTextureStageState = 63, DEV_DrawPrimitive = 70, DEV_DrawIndexedPrimitive = 71,
	DEV_DrawPrimitiveUP = 72, DEV_DrawIndexedPrimitiveUP = 73, DEV_SetPixelShader = 91 };

#define TSS_TEXCOORDINDEX 11
#define TSS_TEXTURETRANSFORMFLAGS 24
#define TTFF_PROJECTED 256
#define TCI_CAMERASPACEPOSITION 0x20000
#define USAGE_RENDERTARGET 1
#define RS_ZBIAS 47
#define RS_ZFUNC 23
#define CMP_ALWAYS 8

typedef HR (__stdcall *Present_t)(void*, const void*, const void*, HWND, const void*);
typedef HR (__stdcall *CreateTexture_t)(void*, UINT, UINT, UINT, DWORD, DWORD, DWORD, void**);
typedef HR (__stdcall *SetRenderTarget_t)(void*, void*, void*);
typedef HR (__stdcall *SetRenderState_t)(void*, DWORD, DWORD);
typedef HR (__stdcall *SetTSS_t)(void*, DWORD, DWORD, DWORD);
typedef HR (__stdcall *DrawPrimitive_t)(void*, DWORD, UINT, UINT);
typedef HR (__stdcall *DrawIndexedPrimitive_t)(void*, DWORD, UINT, UINT, UINT, UINT);
typedef HR (__stdcall *DrawPrimitiveUP_t)(void*, DWORD, UINT, const void*, UINT);
typedef HR (__stdcall *DrawIndexedPrimitiveUP_t)(void*, DWORD, UINT, UINT, UINT, const void*, DWORD, const void*, UINT);

typedef HR (__stdcall *SetTexture_t)(void*, DWORD, void*);
typedef HR (__stdcall *SetTransform_t)(void*, DWORD, const float*);
typedef HR (__stdcall *SetShader_t)(void*, DWORD);
static SetTexture_t RealSetTexture;
static SetTransform_t RealSetTransform;
static SetShader_t RealSetVS, RealSetPS;
typedef HR (__stdcall *Clear_t)(void*, DWORD, const void*, DWORD, DWORD, float, DWORD);
static Clear_t RealClear;
static Present_t RealPresent;
static CreateTexture_t RealCreateTexture;
static SetRenderTarget_t RealSetRenderTarget;
static SetRenderState_t RealSetRenderState;
static SetTSS_t RealSetTSS;
static DrawPrimitive_t RealDP;
static DrawIndexedPrimitive_t RealDIP;
static DrawPrimitiveUP_t RealDPUP;
static DrawIndexedPrimitiveUP_t RealDIPUP;

static DWORD Transform[8], TexCoord[8];
static DWORD Tss[4][32];          /* stage states of the first 4 stages */
static DWORD Rs[256];             /* render states */
static void* Tex[4];
static DWORD VS, PS;
static float TexMatrix[4][16];
static int Details, OffDetails;
static void *CurRT, *BackRT;
static int SmallRT;
static DWORD RTW, RTH, RTFmt;
static long OffDraws, OffTargets;
static int SeqBinds, SeqActive, SeqLines;
/* frame dump: every call of one whole frame, render-target textures named by number */
#define MAXRT 64
static void *RtTex[MAXRT], *RtSurf[MAXRT];
static DWORD RtW[MAXRT], RtH[MAXRT];
static int RtCount;
static int DumpState, DumpLines;      /* 0 waiting, 1 armed (next Present starts), 2 dumping, 3 done */
static int RtOfSurf(void* S) { int i; for (i = 0; i < RtCount; i++) if (RtSurf[i] == S) return i; return -1; }
static int RtOfTex(void* T) { int i; if (!T) return -2; for (i = 0; i < RtCount; i++) if (RtTex[i] == T) return i; return -1; }
static int DumpAll;                /* ADVENT_DUMPALL=1: the dumped frame lists every draw, with texture sizes */
static int Dumping(void) { return DumpState == 2 && DumpLines < (DumpAll ? 6000 : 1500); }
static int Frames, Reports;
static DWORD LastTick;
static long Draws, ProjDraws, CamPosDraws, RTSwitches, ProjStageSets, ZBiasSets;
static int RTLogs;
static DWORD ZFunc = 4;            /* the engine's current depth test (LESSEQUAL by default) */
int D3DZAlways;
int D3DShadowAlpha = 0;  /* experiment, now done for real by shadowalpha.c */
static int ProjDebug;              /* ADVENT_D3DDEBUG: 1 projection draws in solid red, 2 the shadow texture itself, opaque */             /* experiment: draws into shadow bitmaps also write alpha (the shadow lives there) */                    /* experiment: projected draws always pass the depth test */

static int ProjectedActive(void)
{
	int i;
	for (i = 0; i < 8; i++)
		if (Transform[i] & TTFF_PROJECTED)
			return 1;
	return 0;
}

static int CamPosActive(void)
{
	int i;
	for (i = 0; i < 8; i++)
		if ((TexCoord[i] & 0xFFFF0000) == TCI_CAMERASPACEPOSITION)
			return 1;
	return 0;
}

static void OffDetail(void);

static long PlainRun, PlainPrims;
static void* PlainEsp;
static void FlushPlain(void)
{
	if (PlainRun && Dumping()) { DumpLines++; Note(L"d3dtrace: DUMP   ... %ld ordinary draws (%ld triangles), first at esp %p", PlainRun, PlainPrims, PlainEsp); }
	PlainRun = PlainPrims = 0;
}

static void DumpDraw(const wchar_t* Kind, UINT Prims)
{
	int i;
	if (!Dumping()) return;
	/* the scene has hundreds of plain draws: log only those touching render targets, projection or small targets */
	if (!DumpAll && !SmallRT && !ProjectedActive() && RtOfTex(Tex[0]) < 0 && RtOfTex(Tex[1]) < 0 && RtOfTex(Tex[2]) < 0 && RtOfTex(Tex[3]) < 0)
	{
		if (!PlainRun) PlainEsp = _AddressOfReturnAddress();
		PlainRun++; PlainPrims += Prims;
		return;
	}
	FlushPlain();
	DumpLines++;
	Note(L"d3dtrace: DUMP   esp %p", _AddressOfReturnAddress());
	Note(L"d3dtrace: DUMP   %ls %u prims: VS %lx PS %lx blend %lu %lu/%lu op %lu z %lu/%lu/%lu cull %lu cw %lx tf %08lx fog %lu atest %lu/%lu/%lu",
		Kind, Prims, VS, PS, Rs[27], Rs[19], Rs[20], Rs[171], Rs[7], Rs[14], Rs[23], Rs[22], Rs[168], Rs[60], Rs[28], Rs[15], Rs[25], Rs[24]);
	for (i = 0; i < 4; i++)
	{
		if (Tss[i][1] == 1 && !(DumpAll && PS)) break;      /* D3DTOP_DISABLE ends the cascade (a pixel shader ignores it) */
		if (DumpAll && PS && !Tex[i]) continue;
	{
		DWORD Td[8] = {0};
		typedef HR (__stdcall *GetType_t)(void*);
		typedef HR (__stdcall *GetLevelDesc_t)(void*, UINT, DWORD*);
		if (DumpAll && Tex[i] && Readable(Tex[i], 4) && ((GetType_t)VT(Tex[i])[10])(Tex[i]) == 3)
			((GetLevelDesc_t)VT(Tex[i])[14])(Tex[i], 0, Td);
		Note(L"d3dtrace: DUMP     stage %d tex %d(%p %lux%lu fmt %lu) color %lu(%lx,%lx) alpha %lu(%lx,%lx) tci %lx ttf %lx addr %lu/%lu",
			i, RtOfTex(Tex[i]), Tex[i], Td[6], Td[7], Td[0], Tss[i][1], Tss[i][2], Tss[i][3], Tss[i][4], Tss[i][5], Tss[i][6], Tss[i][11], Tss[i][24], Tss[i][13], Tss[i][14]);
	}
	}
}

static void Count(void)
{
	Draws++;
	if (SmallRT) { OffDraws++; OffDetail(); }
	if (ProjectedActive()) ProjDraws++;
	if (CamPosActive()) CamPosDraws++;
}

static HR __stdcall HookPresent(void* D, const void* A, const void* B, HWND W, const void* C)
{
	Frames++;
	BackRT = CurRT;
	FlushPlain();
	if (DumpState == 2) { DumpState = 3; Note(L"d3dtrace: DUMP end of frame (%d lines)", DumpLines); }
	if (DumpState == 1) { DumpState = 2; Note(L"d3dtrace: DUMP frame %d begins", Frames); }     /* whatever is bound when the frame is shown is the back buffer */
	if (Frames % 300 == 0)
	{
		DWORD Now = GetTickCount();
		DWORD Ms = LastTick ? Now - LastTick : 0;
		LastTick = Now;
		/* only frames with a 3D world in them (menus and movies draw a handful per frame) */
		if (Draws > 300 * 20 && (ProjDraws || DumpAll) && DumpState == 0 && Frames > (DumpAll ? 1500 : 3000)) DumpState = 1;
		if (ProjDebug == 4 && Draws > 300 * 20 && Reports < 12) SiteReport();
		if ((Draws > 300 * 20 || ProjDraws || ProjStageSets) && Reports < 400)
		{
			Reports++;
			Note(L"d3dtrace: last 300 frames (%.0f fps): %ld draws, %ld with a projected stage, %ld render-target switches, %ld shadow bitmaps bound, %ld draws into shadow bitmaps",
				Ms ? 300000.0 / Ms : 0.0, Draws, ProjDraws, RTSwitches, OffTargets, OffDraws);
		}
		Draws = ProjDraws = CamPosDraws = RTSwitches = ProjStageSets = ZBiasSets = OffDraws = OffTargets = 0;
	}
	return RealPresent(D, A, B, W, C);
}

static HR __stdcall HookCreateTexture(void* D, UINT W, UINT H, UINT Levels, DWORD Usage, DWORD Format, DWORD Pool, void** Tex)
{
	HR R = RealCreateTexture(D, W, H, Levels, Usage, Format, Pool, Tex);
	if ((Usage & USAGE_RENDERTARGET) && R == 0 && *Tex && RtCount < MAXRT)
	{
		/* IDirect3DTexture8::GetSurfaceLevel (slot 15) adds a reference; the pointer stays valid while the texture lives */
		typedef HR (__stdcall *GetLevel_t)(void*, UINT, void**);
		typedef ULONG (__stdcall *Rel_t)(void*);
		void* Surf = NULL;
		((GetLevel_t)VT(*Tex)[15])(*Tex, 0, &Surf);
		if (Surf) ((Rel_t)VT(Surf)[2])(Surf);
		RtTex[RtCount] = *Tex; RtSurf[RtCount] = Surf; RtW[RtCount] = W; RtH[RtCount] = H;
		Note(L"d3dtrace: render target texture #%d: %ux%u format %lu", RtCount, W, H, Format);
		RtCount++;
	}
	if ((Usage & USAGE_RENDERTARGET) && RTLogs < 20)
	{
		RTLogs++;
		Note(L"d3dtrace: CreateTexture render target %ux%u format %lu usage %lx -> %08lx", W, H, Format, Usage, (unsigned long)R);
	}
	return R;
}

static int WantWorldStack;
static BYTE* MainEsp;               /* stack depth of the main scene's colour clear */
static HR __stdcall HookClear(void* D, DWORD N, const void* R, DWORD Flags, DWORD Color, float Z, DWORD St)
{
	if ((Flags & 1) && !SmallRT) MainEsp = (BYTE*)_AddressOfReturnAddress();
	if (Flags == 2 && Details >= 2 && WantWorldStack == 0) { WantWorldStack = 1; StackScan(L"z clear before the world"); }
	FlushPlain();
	if (Dumping()) { DumpLines++; Note(L"d3dtrace: DUMP   clear flags %lx color %08lx z %.2f esp %p", Flags, Color, Z, _AddressOfReturnAddress()); }
	if (SeqActive && SeqLines < 60) { SeqLines++; Note(L"d3dtrace: SEQ clear flags %lx color %08lx z %.2f", Flags, Color, Z); }
	return RealClear(D, N, R, Flags, Color, Z, St);
}

static HR __stdcall HookSetRenderTarget(void* D, void* RT, void* Z)
{
	RTSwitches++;
	if (RT)
	{
		/* IDirect3DSurface8::GetDesc (slot 8): D3DSURFACE_DESC, Width at +24, Height at +28 */
		DWORD Desc[8] = {0};
		typedef HR (__stdcall *GetDesc_t)(void*, DWORD*);
		((GetDesc_t)(*(void***)RT)[8])(RT, Desc);
		CurRT = RT;
		FlushPlain();
		if (Dumping()) { DumpLines++; Note(L"d3dtrace: DUMP target %d (%lux%lu)", RtOfSurf(RT), Desc[6], Desc[7]); }
		SmallRT = Desc[6] && Desc[6] <= 512 && Desc[7] <= 512;
		if (SmallRT) { OffTargets++; RTW = Desc[6]; RTH = Desc[7]; RTFmt = Desc[0]; }
		/* the full sequence for a few shadow bitmaps, once frames have a 3D world in them */
		SeqActive = 0;
		if (SmallRT && Frames > 2000 && SeqBinds < 1) StackScan(L"shadow bitmap bound");
		if (SmallRT && Frames > 2000 && SeqBinds < 3) { SeqBinds++; SeqActive = 1; Note(L"d3dtrace: SEQ bind shadow bitmap %p (%lux%lu)", RT, RTW, RTH); }
	}
	return RealSetRenderTarget(D, RT, Z);
}

static HR __stdcall HookSetRenderState(void* D, DWORD State, DWORD Value)
{
	if (State == RS_ZBIAS && Value) ZBiasSets++;
	if (State == RS_ZFUNC) ZFunc = Value;
	if (State < 256) Rs[State] = Value;
	return RealSetRenderState(D, State, Value);
}

static HR __stdcall HookSetTexture(void* D, DWORD Stage, void* T) { if (Stage < 4) Tex[Stage] = T; return RealSetTexture(D, Stage, T); }
static HR __stdcall HookSetTransform(void* D, DWORD State, const float* M) { if (State >= 16 && State < 20 && M) memcpy(TexMatrix[State - 16], M, 64); return RealSetTransform(D, State, M); }
static HR __stdcall HookSetVS(void* D, DWORD H) { VS = H; return RealSetVS(D, H); }
static HR __stdcall HookSetPS(void* D, DWORD H) { PS = H; return RealSetPS(D, H); }

/* the state of the first draws into an off-screen target (the shadow bitmaps) */
static void OffDetail(void)
{
	if (SeqActive && SeqLines < 60)
	{
		int i;
		SeqLines++;
		Note(L"d3dtrace: SEQ draw: VS %08lx blend %lu %lu/%lu op %lu zen %lu zwr %lu cull %lu cw %lx tf %08lx light %lu dms %lu amb %08lx shade %lu alphatest %lu/%lu/%lu fog %lu clip %lx stencil %lu scissor %lu vertexblend %lu",
			VS, Rs[27], Rs[19], Rs[20], Rs[171], Rs[7], Rs[14], Rs[22], Rs[168], Rs[60], Rs[137], Rs[145], Rs[139], Rs[9], Rs[15], Rs[24], Rs[25], Rs[28], Rs[152], Rs[52], Rs[174], Rs[151]);
		for (i = 0; i < 4; i++)
			Note(L"d3dtrace: SEQ   stage %d tex %p color %lu(%lx,%lx) alpha %lu(%lx,%lx) tci %lx ttf %lx", i, Tex[i], Tss[i][1], Tss[i][2], Tss[i][3], Tss[i][4], Tss[i][5], Tss[i][6], Tss[i][11], Tss[i][24]);
	}
	if (OffDetails >= 6) return;
	OffDetails++;
	Note(L"d3dtrace: shadow-bitmap draw into %p (%lux%lu format %lu): blendop %lu VS %08lx PS %08lx alphablend %lu src %lu dst %lu zenable %lu cull %lu colorwrite %lx lighting %lu tfactor %08lx; stage0 tex %p colorop %lu arg1 %lx arg2 %lx alphaop %lu",
		CurRT, RTW, RTH, RTFmt, Rs[171], VS, PS, Rs[27], Rs[19], Rs[20], Rs[7], Rs[22], Rs[168], Rs[137], Rs[60], Tex[0], Tss[0][1], Tss[0][2], Tss[0][3], Tss[0][4]);
}

/* who asked for this draw: return addresses found on the stack that point into game modules */
static void StackScan(const wchar_t* Why)
{
	DWORD* Sp = (DWORD*)_AddressOfReturnAddress();
	wchar_t Line[2048];
	int n = 0, i, Len = 0;
	Len = swprintf(Line, 2048, L"d3dtrace: stack (%ls) esp %p:", Why, Sp);
	for (i = 0; i < 1500 && n < 14; i++)
	{
		DWORD V = Sp[i];
		HMODULE M;
		const BYTE* Code = (const BYTE*)V;
		if (!Readable(&Sp[i + 1], 4)) break;
		if (V < 0x10000 || !(M = ModuleOf((void*)V))) continue;
		/* a return address follows a call: E8 rel32 or FF /2 */
		if (!Readable(Code - 6, 6)) continue;
		if (Code[-5] != 0xE8 && !(Code[-6] == 0xFF && (Code[-5] & 0x38) == 0x10) && !(Code[-2] == 0xFF && (Code[-1] & 0x38) == 0x10) && !(Code[-3] == 0xFF && (Code[-2] & 0x38) == 0x10)) continue;
		{
			wchar_t Name[MAX_PATH];
			const wchar_t* Base;
			GetModuleFileNameW(M, Name, MAX_PATH);
			Base = wcsrchr(Name, 92) ? wcsrchr(Name, 92) + 1 : Name;
			if (_wcsicmp(Base, L"Engine.dll") && _wcsicmp(Base, L"Core.dll") && _wcsicmp(Base, L"advent.exe") && _wcsicmp(Base, L"D3DDrv.dll") && _wcsicmp(Base, L"WinDrv.dll") && _wcsicmp(Base, L"EonEngine.dll")) continue;
			if (!_wcsicmp(Base, L"AdventNative.dll") || !_wcsnicmp(Base, L"d3d", 3) || !_wcsicmp(Base, L"ntdll.dll") || !_wcsicmp(Base, L"kernel32.dll") || !_wcsicmp(Base, L"KERNELBASE.dll")) continue;
			Len += swprintf(Line + Len, 2048 - Len, L" %ls+%lx", Base, (unsigned long)(V - (DWORD)(ULONG_PTR)M));
			n++;
		}
	}
	Note(L"%ls", Line);
}

/* the full state of the first projected draws: what the GPU is actually told to do */
static void Detail(const wchar_t* Kind)
{
	int i;
	if (Details >= 2 || !ProjectedActive()) return;
	Details++;
	StackScan(Kind);
	Note(L"d3dtrace: projected %ls: VS %08lx PS %08lx alphablend %lu src %lu dst %lu zenable %lu zwrite %lu zfunc %lu cull %lu colorwrite %lx fog %lu",
		Kind, VS, PS, Rs[27], Rs[19], Rs[20], Rs[7], Rs[14], Rs[23], Rs[22], Rs[168], Rs[28]);
	for (i = 0; i < 4; i++)
		Note(L"d3dtrace:   stage %d tex %p colorop %lu arg1 %lx arg2 %lx alphaop %lu arg1 %lx arg2 %lx texcoord %lx transformflags %lx addr %lu/%lu  m[0]=%.3f m[5]=%.3f m[8]=%.3f m[9]=%.3f m[10]=%.3f m[11]=%.3f m[12]=%.3f m[13]=%.3f",
			i, Tex[i], Tss[i][1], Tss[i][2], Tss[i][3], Tss[i][4], Tss[i][5], Tss[i][6], Tss[i][11], Tss[i][24], Tss[i][13], Tss[i][14],
			TexMatrix[i][0], TexMatrix[i][5], TexMatrix[i][8], TexMatrix[i][9], TexMatrix[i][10], TexMatrix[i][11], TexMatrix[i][12], TexMatrix[i][13]);
}

static HR __stdcall HookSetTSS(void* D, DWORD Stage, DWORD Type, DWORD Value)
{
	if (Stage < 4 && Type < 32) Tss[Stage][Type] = Value;
	if (Stage < 8)
	{
		if (Type == TSS_TEXTURETRANSFORMFLAGS)
		{
			Transform[Stage] = Value;
			if (Value & TTFF_PROJECTED) ProjStageSets++;
		}
		else if (Type == TSS_TEXCOORDINDEX)
			TexCoord[Stage] = Value;
	}
	return RealSetTSS(D, Stage, Type, Value);
}

/* experiment: around a projected draw, let it always pass the depth test */
static int SkipNested(void)
{
	return ProjDebug == 3 && !SmallRT && MainEsp && (BYTE*)_AddressOfReturnAddress() < MainEsp - 0x1000;
}

static void ProjDebugDraw(void* D, int On)
{
	static DWORD Saved[6];
	if (!ProjDebug || !ProjectedActive() || SmallRT) return;
	if (On)
	{
		Saved[0] = Rs[27]; Saved[1] = Tss[0][1]; Saved[2] = Tss[0][2]; Saved[3] = Tss[0][3]; Saved[4] = Rs[60]; Saved[5] = Tss[0][4];
		RealSetRenderState(D, 27, 0);
		if (ProjDebug == 1) { RealSetRenderState(D, 60, 0xFFFF0000); RealSetTSS(D, 0, 1, 2); RealSetTSS(D, 0, 2, 3); }
		else { RealSetTSS(D, 0, 1, 2); RealSetTSS(D, 0, 2, 2); }
	}
	else
	{
		RealSetRenderState(D, 27, Saved[0]); RealSetRenderState(D, 60, Saved[4]);
		RealSetTSS(D, 0, 1, Saved[1]); RealSetTSS(D, 0, 2, Saved[2]); RealSetTSS(D, 0, 3, Saved[3]);
	}
}

static int ZBegin(void* D)
{
	if (D3DShadowAlpha && SmallRT && Rs[168] != 0xF) { RealSetRenderState(D, 168, 0xF); return 2; }
	if (!D3DZAlways || !ProjectedActive()) return 0;
	RealSetRenderState(D, RS_ZFUNC, CMP_ALWAYS);
	return 1;
}
static void ZEnd(void* D, int On) { if (On == 2) RealSetRenderState(D, 168, Rs[168]); else if (On) RealSetRenderState(D, RS_ZFUNC, ZFunc); }

static HR __stdcall HookDP(void* D, DWORD T, UINT S, UINT C) { HR R; int Z; Count(); DumpDraw(L"DP", C); Detail(L"HookDP"); Z = ZBegin(D); if (SkipNested()) return 0; ProjDebugDraw(D, 1); R = RealDP(D, T, S, C); ProjDebugDraw(D, 0); ZEnd(D, Z); return R; }
static HR __stdcall HookDIP(void* D, DWORD T, UINT Mn, UINT Nv, UINT Si, UINT Pc) { HR R; int Z; Count(); DumpDraw(L"DIP", Pc); Detail(L"HookDIP"); Z = ZBegin(D); if (SkipNested()) return 0; ProjDebugDraw(D, 1); R = RealDIP(D, T, Mn, Nv, Si, Pc); ProjDebugDraw(D, 0); ZEnd(D, Z); return R; }
static HR __stdcall HookDPUP(void* D, DWORD T, UINT C, const void* V, UINT St) { HR R; int Z; Count(); DumpDraw(L"DPUP", C); Detail(L"HookDPUP"); Z = ZBegin(D); if (SkipNested()) return 0; ProjDebugDraw(D, 1); R = RealDPUP(D, T, C, V, St); ProjDebugDraw(D, 0); ZEnd(D, Z); return R; }
static HR __stdcall HookDIPUP(void* D, DWORD T, UINT Mn, UINT Nv, UINT Pc, const void* I, DWORD F, const void* V, UINT St) { HR R; int Z; Count(); DumpDraw(L"DIPUP", Pc); Detail(L"HookDIPUP"); Z = ZBegin(D); if (SkipNested()) return 0; ProjDebugDraw(D, 1); R = RealDIPUP(D, T, Mn, Nv, Pc, I, F, V, St); ProjDebugDraw(D, 0); ZEnd(D, Z); return R; }

static void* Patch(void** Table, int Slot, void* To)
{
	void* Old = Table[Slot];
	DWORD Prot;
	VirtualProtect(&Table[Slot], sizeof(void*), PAGE_EXECUTE_READWRITE, &Prot);
	Table[Slot] = To;
	VirtualProtect(&Table[Slot], sizeof(void*), Prot, &Prot);
	return Old;
}

static int InModule(HMODULE M, const void* P)
{
	IMAGE_NT_HEADERS* Nt = (IMAGE_NT_HEADERS*)((BYTE*)M + ((IMAGE_DOS_HEADER*)M)->e_lfanew);
	return (BYTE*)P >= (BYTE*)M && (BYTE*)P < (BYTE*)M + Nt->OptionalHeader.SizeOfImage;
}

static int Readable(const void* P, SIZE_T N)
{
	MEMORY_BASIC_INFORMATION Mi;
	if (!P || !VirtualQuery(P, &Mi, sizeof(Mi)) || Mi.State != MEM_COMMIT || (Mi.Protect & (PAGE_NOACCESS | PAGE_GUARD)))
		return 0;
	return (BYTE*)P + N <= (BYTE*)Mi.BaseAddress + Mi.RegionSize;
}

static HMODULE ModuleOf(const void* P)
{
	HMODULE M = NULL;
	GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)P, &M);
	return M;
}

static const wchar_t* ModuleName(const void* P)
{
	static wchar_t Name[MAX_PATH];
	HMODULE M = ModuleOf(P);
	if (!M || !GetModuleFileNameW(M, Name, MAX_PATH)) return L"(no module)";
	return wcsrchr(Name, 92) ? wcsrchr(Name, 92) + 1 : Name;
}

/* walk Core's object list for the D3DDrv.D3DRenderDevice object, and find in it the
   pointer to an object whose methods are implemented where the reference device's are */
static void** DevHolder;            /* where the render device keeps its IDirect3DDevice8 */
static void* FindGameDevice(void** RefTable, void** D3DTable)
{
	typedef const wchar_t* (__fastcall *GetName_t)(void* This, void* Edx);
	typedef void* (__fastcall *GetClass_t)(void* This, void* Edx);
	typedef struct { void** Data; int Num, Max; } ObjArray;
	HMODULE Core = GetModuleHandleW(L"Core.dll");
	HMODULE Impl = ModuleOf(RefTable[DEV_Present]);
	ObjArray* Objs;
	GetName_t GetName;
	GetClass_t GetClass;
	int i, Off;

	if (!Core) return NULL;
	Objs = (ObjArray*)GetProcAddress(Core, "?GObjObjects@UObject@@1V?$TArray@PAVUObject@@@@A");
	GetName = (GetName_t)GetProcAddress(Core, "?GetName@UObject@@QBEPBGXZ");
	GetClass = (GetClass_t)GetProcAddress(Core, "?GetClass@UObject@@QBEPAVUClass@@XZ");
	if (!Objs || !GetName || !GetClass) { Note(L"d3dtrace: Core exports missing"); return NULL; }
	Note(L"d3dtrace: reference device: table %p in %ls, Present in %ls", RefTable, ModuleName(RefTable), ModuleName(RefTable[DEV_Present]));
	for (i = 0; i < Objs->Num; i++)
	{
		void* Obj = Objs->Data[i];
		void* Class;
		if (!Obj) continue;
		Class = GetClass(Obj, NULL);
		if (!Class || wcscmp(GetName(Class, NULL), L"D3DRenderDevice")) continue;
		for (Off = 0x30; Off <= 0x3000; Off += 4)
		{
			void* P;
			void** T;
			if (!Readable((BYTE*)Obj + Off, 4)) break;
			P = *(void**)((BYTE*)Obj + Off);
			if (!Readable(P, 4)) continue;
			T = *(void***)P;
			if (!Readable(T, (DEV_DrawIndexedPrimitiveUP + 1) * 4)) continue;
			/* the IDirect3D8 object has only 16 methods: never treat it as the device */
			if (T == D3DTable) continue;
			if (T == RefTable || (ModuleOf(T[DEV_Present]) == Impl && ModuleOf(T[DEV_DrawIndexedPrimitive]) == Impl && ModuleOf(T[DEV_SetTextureStageState]) == Impl))
			{
				Note(L"d3dtrace: game device at render device +%x: %p, table %p in %ls", Off, P, T, ModuleName(T));
				DevHolder = (void**)((BYTE*)Obj + Off);
				return P;
			}
		}
	}
	return NULL;
}

/* call-site counters inside Engine.dll: which renderers run in the sky pass and which in the main pass */
static const struct { DWORD Va; const wchar_t* Name; } Sites[] = {
	{ 0x10528F47, L"static mesh projectors A" }, { 0x1052BE27, L"static mesh projectors B" },
	{ 0x1052601F, L"adder 10519CE0" }, { 0x1044C08D, L"adder 1051A350 (1)" }, { 0x105032F3, L"adder 1051A350 (2)" },
	{ 0x1052B16E, L"terrain A" }, { 0x1052B23B, L"terrain B" },
	{ 0x1052B547, L"flush 1 item" }, { 0x1052BC44, L"flush 2 item" }, { 0x1052C04A, L"flush 3 item" },
	{ 0x10504229, L"scene render" },
};
#define NSITES (sizeof(Sites) / sizeof(Sites[0]))
static long SiteMain[NSITES], SiteSky[NSITES], AddMain[NSITES], AddSky[NSITES];
static DWORD SiteRet[NSITES], SiteList[NSITES], SiteEsp[NSITES];
#define GLIST ((DWORD*)(EngBase + (0x10955B78 - 0x10300000)))
static BYTE* EngBase;
static void __cdecl SiteHit(BYTE* Esp, int i);
static void __cdecl SitePre(int i, BYTE* Esp) { SiteList[i] = *GLIST; SiteEsp[i] = (DWORD)(ULONG_PTR)Esp; SiteHit(Esp, i); }
static void __cdecl SitePost(int i)
{
	if (*GLIST != SiteList[i])
	{
		if (MainEsp && (BYTE*)(ULONG_PTR)SiteEsp[i] < MainEsp - 0x1000) AddSky[i]++; else AddMain[i]++;
	}
}
static void __cdecl SiteHit(BYTE* Esp, int i)
{
	if (MainEsp && Esp < MainEsp - 0x1000) SiteSky[i]++; else SiteMain[i]++;
}
static void SiteReport(void)
{
	int i;
	for (i = 0; i < (int)NSITES; i++)
		if (SiteMain[i] || SiteSky[i])
			Note(L"d3dtrace: site %08lx %ls: main pass %ld, sky pass %ld, changed the projector list main %ld sky %ld (per 300 frames)", Sites[i].Va, Sites[i].Name, SiteMain[i], SiteSky[i], AddMain[i], AddSky[i]);
	memset(SiteMain, 0, sizeof(SiteMain)); memset(SiteSky, 0, sizeof(SiteSky)); memset(AddMain, 0, sizeof(AddMain)); memset(AddSky, 0, sizeof(AddSky));
}
static void PatchSites(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll");
	BYTE* Mem;
	int i;
	if (!Eng) return;
	EngBase = (BYTE*)Eng;
	Mem = (BYTE*)VirtualAlloc(NULL, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	for (i = 0; i < (int)NSITES; i++)
	{
		BYTE* Call = (BYTE*)Eng + (Sites[i].Va - 0x10300000);
		BYTE* Stub = Mem + i * 64;
		BYTE* Target;
		DWORD Prot;
		if (Call[0] != 0xE8) { Note(L"d3dtrace: site %08lx is not a call", Sites[i].Va); continue; }
		Target = Call + 5 + *(LONG*)(Call + 1);
		if (i < 7)
		{
			/* adders (not recursive): count, remember the list, make the call, see if the list changed
			   pushad; push esp; push i; call SitePre; add esp,8; popad; pop [Ret]; call Target;
			   pushad; push i; call SitePost; add esp,4; popad; push [Ret]; ret */
			BYTE* q = Stub;
			*q++ = 0x60; *q++ = 0x54; *q++ = 0x68; *(LONG*)q = i; q += 4;
			*q++ = 0xE8; *(LONG*)q = (LONG)((BYTE*)SitePre - (q + 4)); q += 4;
			*q++ = 0x83; *q++ = 0xC4; *q++ = 0x08; *q++ = 0x61;
			*q++ = 0x8F; *q++ = 0x05; *(DWORD**)q = &SiteRet[i]; q += 4;
			*q++ = 0xE8; *(LONG*)q = (LONG)(Target - (q + 4)); q += 4;
			*q++ = 0x60; *q++ = 0x68; *(LONG*)q = i; q += 4;
			*q++ = 0xE8; *(LONG*)q = (LONG)((BYTE*)SitePost - (q + 4)); q += 4;
			*q++ = 0x83; *q++ = 0xC4; *q++ = 0x04; *q++ = 0x61;
			*q++ = 0xFF; *q++ = 0x35; *(DWORD**)q = &SiteRet[i]; q += 4;
			*q++ = 0xC3;
			/* also count it like the others: SitePre counts nothing, so count here via SiteHit? (done in SitePre's caller below) */
		}
		else
		{
		/* pushad; push i; push esp; call SiteHit; add esp,8; popad; jmp Target */
		Stub[0] = 0x60;
		Stub[1] = 0x68; *(LONG*)(Stub + 2) = i;
		Stub[6] = 0x54;
		Stub[7] = 0xE8; *(LONG*)(Stub + 8) = (LONG)((BYTE*)SiteHit - (Stub + 12));
		Stub[12] = 0x83; Stub[13] = 0xC4; Stub[14] = 0x08;
		Stub[15] = 0x61;
		Stub[16] = 0xE9; *(LONG*)(Stub + 17) = (LONG)(Target - (Stub + 21));
		}
		VirtualProtect(Call, 5, PAGE_EXECUTE_READWRITE, &Prot);
		*(LONG*)(Call + 1) = (LONG)(Stub - (Call + 5));
		VirtualProtect(Call, 5, Prot, &Prot);
	}
	Note(L"d3dtrace: counting %d engine call sites", (int)NSITES);
}

static void HookTable(void** Table)
{
	RealPresent = (Present_t)Patch(Table, DEV_Present, HookPresent);
	RealCreateTexture = (CreateTexture_t)Patch(Table, DEV_CreateTexture, HookCreateTexture);
	RealSetRenderTarget = (SetRenderTarget_t)Patch(Table, DEV_SetRenderTarget, HookSetRenderTarget);
	RealSetRenderState = (SetRenderState_t)Patch(Table, DEV_SetRenderState, HookSetRenderState);
	RealSetTSS = (SetTSS_t)Patch(Table, DEV_SetTextureStageState, HookSetTSS);
	RealDP = (DrawPrimitive_t)Patch(Table, DEV_DrawPrimitive, HookDP);
	RealClear = (Clear_t)Patch(Table, 36, HookClear);
	RealSetTexture = (SetTexture_t)Patch(Table, DEV_SetTexture, HookSetTexture);
	RealSetTransform = (SetTransform_t)Patch(Table, DEV_SetTransform, HookSetTransform);
	RealSetVS = (SetShader_t)Patch(Table, DEV_SetVertexShader, HookSetVS);
	RealSetPS = (SetShader_t)Patch(Table, DEV_SetPixelShader2, HookSetPS);
	RealDIP = (DrawIndexedPrimitive_t)Patch(Table, DEV_DrawIndexedPrimitive, HookDIP);
	RealDPUP = (DrawPrimitiveUP_t)Patch(Table, DEV_DrawPrimitiveUP, HookDPUP);
	RealDIPUP = (DrawIndexedPrimitiveUP_t)Patch(Table, DEV_DrawIndexedPrimitiveUP, HookDIPUP);
}

/* The game's IDirect3DDevice8, found through its render device object (shadowalpha.c uses this too).
   The game makes a new device when its window changes size, so this always reads the current one. */
void* D3DGameDevice(void)
{
	typedef void* (__stdcall *Create8_t)(UINT);
	typedef HR (__stdcall *GetMode_t)(void*, UINT, void*);
	typedef ULONG (__stdcall *Release_t)(void*);
	typedef HR (__stdcall *CreateDevice_t)(void*, UINT, DWORD, HWND, DWORD, void*, void**);
	HMODULE Lib = GetModuleHandleW(L"d3d8.dll");
	Create8_t Create8;
	void *D3D, *Dev, *Ref = NULL;
	DWORD Pp[13];                 /* D3DPRESENT_PARAMETERS (Direct3D 8) */
	DWORD Mode[4];                /* Width, Height, RefreshRate, Format */
	HWND Win;
	HR R;
	unsigned int Fpu;

	if (DevHolder && Readable(DevHolder, 4) && *DevHolder && Readable(*DevHolder, 4)) return *DevHolder;
	if (!Lib) { Note(L"d3d: d3d8.dll not loaded"); return NULL; }
	Create8 = (Create8_t)GetProcAddress(Lib, "Direct3DCreate8");
	D3D = Create8 ? Create8(220) : NULL;
	if (!D3D) { Note(L"d3d: Direct3DCreate8 failed"); return NULL; }
	((GetMode_t)VT(D3D)[D3D_GetAdapterDisplayMode])(D3D, 0, Mode);

	/* a throwaway device, to learn where this system's device methods live */
	Win = CreateWindowExW(0, L"STATIC", L"d3dtrace", WS_POPUP, 0, 0, 8, 8, NULL, NULL, NULL, NULL);
	ZeroMemory(Pp, sizeof(Pp));
	Pp[0] = 8; Pp[1] = 8; Pp[2] = Mode[3]; Pp[3] = 1; Pp[5] = 1 /* discard */; Pp[6] = (DWORD)(ULONG_PTR)Win; Pp[7] = TRUE;
	/* FPU_PRESERVE: without it Direct3D drops the calling thread's x87 FPU to single
	   precision, and this runs on the game's thread. Unreal times its frames from the CPU's
	   cycle counter in doubles; in single precision those big counts lose their low digits,
	   the per-frame time steps come out wrong and the game plays in slow motion, choppy.
	   (That was AdventMod's "slow motion" bug.) The control word is put back as well. */
	Fpu = _controlfp(0, 0);
	R = ((CreateDevice_t)VT(D3D)[D3D_CreateDevice])(D3D, 0, 1, Win, 0x20 /* software vertex processing */ | 0x2 /* FPU preserve */, Pp, &Ref);
	_controlfp(Fpu, _MCW_PC | _MCW_RC | _MCW_EM);
	if (R != 0 || !Ref)
	{
		Note(L"d3d: CreateDevice failed %08lx", (unsigned long)R);
		((Release_t)VT(D3D)[D3D_Release])(D3D);
		DestroyWindow(Win);
		return NULL;
	}
	Dev = FindGameDevice(VT(Ref), VT(D3D));
	((Release_t)VT(Ref)[DEV_Release])(Ref);
	((Release_t)VT(D3D)[D3D_Release])(D3D);
	DestroyWindow(Win);
	if (!Dev) Note(L"d3d: game device not found");
	return Dev;
}

int D3DTraceStart(void)
{
	typedef void* (__stdcall *Create8_t)(UINT);
	typedef HR (__stdcall *GetMode_t)(void*, UINT, void*);
	typedef HR (__stdcall *CheckFormat_t)(void*, UINT, DWORD, DWORD, DWORD, DWORD, DWORD);
	typedef HR (__stdcall *GetCaps_t)(void*, UINT, DWORD, void*);
	typedef ULONG (__stdcall *Release_t)(void*);
	static int Started;
	HMODULE Lib = GetModuleHandleW(L"d3d8.dll");
	Create8_t Create8;
	void *D3D, *Dev = NULL, *Ref = NULL;
	DWORD Pp[13];                 /* D3DPRESENT_PARAMETERS (Direct3D 8) */
	HWND Win;
	HR R;
	typedef HR (__stdcall *CreateDevice_t)(void*, UINT, DWORD, HWND, DWORD, void*, void**);
	DWORD Mode[4];                /* Width, Height, RefreshRate, Format */
	BYTE Caps[512];
	void** Table;

	if (Started)
	{
		/* the game makes a new device when its window changes size: hook that one too */
		void* Now = DevHolder && Readable(DevHolder, 4) ? *DevHolder : NULL;
		if (Now && Readable(Now, 4) && VT(Now)[DEV_Present] != (void*)HookPresent)
		{
			Note(L"d3dtrace: the game has a new device %p: hooking it", Now);
			HookTable(VT(Now));
		}
		return 1;
	}
	{
		char E[16];
		if (GetEnvironmentVariableA("ADVENT_D3DDEBUG", E, sizeof(E))) ProjDebug = atoi(E);
		if (GetEnvironmentVariableA("ADVENT_SHADOWALPHA", E, sizeof(E))) D3DShadowAlpha = atoi(E);
		if (GetEnvironmentVariableA("ADVENT_DUMPALL", E, sizeof(E))) DumpAll = atoi(E);
		Note(L"d3dtrace: projection debug mode %d, shadow alpha write %d", ProjDebug, D3DShadowAlpha);
	}
	if (!Lib) { Note(L"d3dtrace: d3d8.dll not loaded"); return 0; }
	Create8 = (Create8_t)GetProcAddress(Lib, "Direct3DCreate8");
	D3D = Create8 ? Create8(220) : NULL;
	if (!D3D) { Note(L"d3dtrace: Direct3DCreate8 failed"); return 0; }

	/* what the card says about the features projectors and shadow bitmaps need */
	if (((GetCaps_t)VT(D3D)[D3D_GetDeviceCaps])(D3D, 0, 1, Caps) == 0)
		Note(L"d3dtrace: caps: TextureCaps %08lx (projected %d) MaxTextureBlendStages %lu MaxSimultaneousTextures %lu RasterCaps %08lx (zbias %d) PixelShader %08lx",
			*(DWORD*)(Caps + 0x3C), (*(DWORD*)(Caps + 0x3C) & 0x400) != 0, *(DWORD*)(Caps + 0x94), *(DWORD*)(Caps + 0x98),
			*(DWORD*)(Caps + 0x24), (*(DWORD*)(Caps + 0x24) & 0x4000) != 0, *(DWORD*)(Caps + 0xCC));
	Note(L"d3dtrace: caps: PrimitiveMiscCaps %08lx (blend operations %d) SrcBlendCaps %08lx DestBlendCaps %08lx",
		*(DWORD*)(Caps + 0x20), (*(DWORD*)(Caps + 0x20) & 0x800) != 0, *(DWORD*)(Caps + 0x2C), *(DWORD*)(Caps + 0x30));
	((GetMode_t)VT(D3D)[D3D_GetAdapterDisplayMode])(D3D, 0, Mode);
	Note(L"d3dtrace: render target formats on this card: L8 %s, A8R8G8B8 %s, X8R8G8B8 %s",
		((CheckFormat_t)VT(D3D)[D3D_CheckDeviceFormat])(D3D, 0, 1, Mode[3], USAGE_RENDERTARGET, 3, 50) == 0 ? L"yes" : L"NO",
		((CheckFormat_t)VT(D3D)[D3D_CheckDeviceFormat])(D3D, 0, 1, Mode[3], USAGE_RENDERTARGET, 3, 21) == 0 ? L"yes" : L"NO",
		((CheckFormat_t)VT(D3D)[D3D_CheckDeviceFormat])(D3D, 0, 1, Mode[3], USAGE_RENDERTARGET, 3, 22) == 0 ? L"yes" : L"NO");

	((Release_t)VT(D3D)[D3D_Release])(D3D);
	Dev = D3DGameDevice();
	if (!Dev) { Note(L"d3dtrace: game device not found"); return 0; }
	HookTable(VT(Dev));
	if (ProjDebug == 4) PatchSites();
	Started = 1;
	Note(L"d3dtrace: device methods hooked (table %p)", VT(Dev));
	return 1;
}
