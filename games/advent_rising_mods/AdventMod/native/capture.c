/* capture.c - screenshots of the finished frame, as it is presented.
   The engine's own "shot" command reads the frame before anything that a Direct3D
   layer draws over it (post-processing), so for testing those this copies the back
   buffer when the frame is presented and writes System\ShotP00000.bmp, ShotP00001.bmp ...
   (32-bit back buffers only).
   The same Present hook caps the frame rate (NativeCall "MaxFps:N", by default the
   monitor's refresh rate): uncapped, the GPU draws ~300 frames a second nobody sees. */
#include <windows.h>
#include <stdio.h>
#pragma comment(lib, "winmm.lib")

void Note(const wchar_t* Fmt, ...);
void* D3DGameDevice(void);    /* d3dtrace.c */

typedef long HR;
#define VT(obj) (*(void***)(obj))
enum { DEV_Present = 15, DEV_GetBackBuffer = 16, DEV_CreateImageSurface = 27, DEV_CopyRects = 28 };
enum { SURF_Release = 2, SURF_GetDesc = 8, SURF_LockRect = 9, SURF_UnlockRect = 10 };

typedef HR (__stdcall *Present_t)(void*, const void*, const void*, HWND, const void*);
static Present_t RealPresent;
static void** HookedTable;
static int Wanted, Count;
static double MinFrame;          /* seconds per frame at the cap, 0 = no cap */
static LARGE_INTEGER Freq, Last;

static void Save(void* Dev)
{
	typedef HR (__stdcall *GetBB_t)(void*, UINT, DWORD, void**);
	typedef HR (__stdcall *CreateImg_t)(void*, UINT, UINT, DWORD, void**);
	typedef HR (__stdcall *CopyRects_t)(void*, void*, const RECT*, UINT, void*, const POINT*);
	typedef HR (__stdcall *GetDesc_t)(void*, DWORD*);
	typedef HR (__stdcall *Lock_t)(void*, void*, const RECT*, DWORD);
	typedef HR (__stdcall *Unlock_t)(void*);
	typedef ULONG (__stdcall *Release_t)(void*);
	void *BB = NULL, *Img = NULL;
	DWORD Desc[8] = {0};          /* D3DSURFACE_DESC: Format at +0, Width +24, Height +28 */
	struct { INT Pitch; void* Bits; } Lk;
	wchar_t Path[MAX_PATH], *Slash;
	FILE* F;
	UINT y, W, H;
	BITMAPFILEHEADER Fh;
	BITMAPINFOHEADER Ih;
	HR R;

	if (((GetBB_t)VT(Dev)[DEV_GetBackBuffer])(Dev, 0, 0, &BB) != 0 || !BB) { Note(L"capture: no back buffer"); return; }
	((GetDesc_t)VT(BB)[SURF_GetDesc])(BB, Desc);
	W = Desc[6]; H = Desc[7];
	if (Desc[0] != 21 && Desc[0] != 22) { Note(L"capture: back buffer format %lu is not 32-bit", Desc[0]); ((Release_t)VT(BB)[SURF_Release])(BB); return; }
	R = ((CreateImg_t)VT(Dev)[DEV_CreateImageSurface])(Dev, W, H, Desc[0], &Img);
	if (R == 0 && Img) R = ((CopyRects_t)VT(Dev)[DEV_CopyRects])(Dev, BB, NULL, 0, Img, NULL);
	((Release_t)VT(BB)[SURF_Release])(BB);
	if (R != 0 || !Img) { Note(L"capture: copy failed %08lx", (unsigned long)R); if (Img) ((Release_t)VT(Img)[SURF_Release])(Img); return; }
	if (((Lock_t)VT(Img)[SURF_LockRect])(Img, &Lk, NULL, 0x10 /* read only */) != 0) { ((Release_t)VT(Img)[SURF_Release])(Img); Note(L"capture: lock failed"); return; }

	GetModuleFileNameW(NULL, Path, MAX_PATH);
	Slash = wcsrchr(Path, L'\\');
	swprintf(Slash + 1, MAX_PATH - (Slash + 1 - Path), L"ShotP%05d.bmp", Count++);
	F = _wfopen(Path, L"wb");
	if (F)
	{
		ZeroMemory(&Fh, sizeof(Fh)); ZeroMemory(&Ih, sizeof(Ih));
		Fh.bfType = 0x4D42;
		Fh.bfOffBits = sizeof(Fh) + sizeof(Ih);
		Fh.bfSize = Fh.bfOffBits + W * H * 4;
		Ih.biSize = sizeof(Ih); Ih.biWidth = W; Ih.biHeight = -(LONG)H; Ih.biPlanes = 1; Ih.biBitCount = 32;
		fwrite(&Fh, sizeof(Fh), 1, F);
		fwrite(&Ih, sizeof(Ih), 1, F);
		for (y = 0; y < H; y++)
			fwrite((BYTE*)Lk.Bits + y * Lk.Pitch, 4, W, F);
		fclose(F);
		Note(L"capture: %ls (%ux%u, as presented)", Slash + 1, W, H);
	}
	((Unlock_t)VT(Img)[SURF_UnlockRect])(Img);
	((Release_t)VT(Img)[SURF_Release])(Img);
}

/* wait until a whole frame's time has passed since the last present: sleep while more
   than 2 ms are left (the system timer is set to 1 ms), then spin the rest */
static void Pace(void)
{
	LARGE_INTEGER Now;
	double Left;
	if (MinFrame <= 0) return;
	for (;;)
	{
		QueryPerformanceCounter(&Now);
		Left = MinFrame - (double)(Now.QuadPart - Last.QuadPart) / Freq.QuadPart;
		if (Left <= 0) break;
		if (Left > 0.002) Sleep(1); else YieldProcessor();
	}
	/* a long frame (loading, a hitch) doesn't earn the next frames a burst */
	if ((double)(Now.QuadPart - Last.QuadPart) / Freq.QuadPart > 2 * MinFrame) Last = Now;
	else Last.QuadPart += (LONGLONG)(MinFrame * Freq.QuadPart);
}

static HR __stdcall HookPresent(void* D, const void* A, const void* B, HWND C, const void* E)
{
	if (Wanted) { Wanted = 0; Save(D); }
	Pace();
	return RealPresent(D, A, B, C, E);
}

static int HookDevice(void)
{
	void* Dev = D3DGameDevice();
	void** Table;
	DWORD Prot;
	if (!Dev) return 0;
	Table = VT(Dev);
	if (Table != HookedTable)
	{
		HookedTable = Table;
		RealPresent = (Present_t)Table[DEV_Present];
		VirtualProtect(&Table[DEV_Present], sizeof(void*), PAGE_EXECUTE_READWRITE, &Prot);
		Table[DEV_Present] = (void*)HookPresent;
		VirtualProtect(&Table[DEV_Present], sizeof(void*), Prot, &Prot);
	}
	return 1;
}

/* NativeCall("MaxFps:N"): at most N frames a second (0 = no cap, -1 = the monitor's refresh rate) */
int SetMaxFps(int Fps)
{
	DEVMODEW Mode;
	if (!HookDevice()) return 0;
	if (Fps < 0)
	{
		ZeroMemory(&Mode, sizeof(Mode));
		Mode.dmSize = sizeof(Mode);
		Fps = EnumDisplaySettingsW(NULL, ENUM_CURRENT_SETTINGS, &Mode) && Mode.dmDisplayFrequency > 1 ? (int)Mode.dmDisplayFrequency : 60;
		/* Windows reports 59.94 Hz (and 119.88, 143.86...) rounded down: a cap a frame under
		   the screen's rate would drop a frame every few seconds */
		if (Fps % 10 == 9 || Fps % 12 == 11) Fps++;
	}
	if (Fps > 0 && MinFrame <= 0)
	{
		timeBeginPeriod(1);
		QueryPerformanceFrequency(&Freq);
		QueryPerformanceCounter(&Last);
	}
	else if (Fps <= 0 && MinFrame > 0)
		timeEndPeriod(1);
	if ((Fps > 0 ? 1.0 / Fps : 0) != MinFrame)
		Note(L"frame cap: %d fps", Fps);
	MinFrame = Fps > 0 ? 1.0 / Fps : 0;
	return 1;
}

/* NativeCall("Capture"): the next presented frame goes to a ShotP file */
int CaptureNext(void)
{
	if (!HookDevice()) return 0;
	Wanted = 1;
	return 1;
}
