/*
 * U2EdBridge.dll - remote control for Unreal II's UnrealEd.
 *
 * Injected into a running UnrealEd.exe (see u2edinject.c), it opens the named
 * pipe \\.\pipe\U2EdBridge-<editor process id>. Each line a client writes is run as an editor
 * command on the editor's main thread, exactly as if typed into UnrealEd's
 * command box. Everything logged while it runs comes back, followed by
 *     <<<U2ED rc=N>>>
 * (N = the command's return value, 1 = handled).
 *
 * Unreal II ships no engine headers, but its DLLs export their C++ symbols,
 * so everything is found by mangled name:
 *   Editor.dll  ?GEditor@@3PAVUEditorEngine@@A          the editor engine
 *               ??_7UEditorEngine@@6BFExec@@@            its FExec vtable (slot 0 = Exec)
 *   Core.dll    ?GLog@@3PAVFOutputDevice@@A / ?GWarn@@... log devices
 * Unreal II's FOutputDevice has a single virtual, Serialize(const TCHAR*, EName),
 * and TCHAR is UTF-16.
 *
 * Message boxes are answered automatically (logged into the reply), because a
 * modal box would stall the command. Yes/No questions get No by default, the
 * safe answer for "save changes?"-style prompts; "!answer yes" flips it.
 *
 * Commands starting with '!' are handled by the bridge itself:
 *   !ping                -> pong
 *   !answer yes|no       how to answer Yes/No message boxes
 *   !quit                terminate the editor (nothing is saved)
 *   !screenshot <path>   save the active viewport's back buffer as a 24-bit BMP
 *
 * !screenshot works by hooking d3d8.dll's Direct3DCreate8 import (same IAT-patch
 * technique as the message box hooks below) to catch the IDirect3DDevice8 the
 * editor creates, then patching that one instance's own CreateDevice slot so any
 * *later* device (e.g. after a Reset, or a freshly opened viewport) is caught
 * too. Capturing the frame itself is GetBackBuffer -> CreateImageSurface (system
 * memory) -> CopyRects -> LockRect, the standard D3D8 way to read back a render
 * target that mustn't be locked directly. If several devices exist (e.g. a mesh
 * browser preview pane), whichever was created or reset most recently wins;
 * there is no per-viewport selection.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <wchar.h>
#include <stdarg.h>
#include <string.h>

#define PIPE_NAME L"\\\\.\\pipe\\U2EdBridge-%lu"   /* %lu = the editor's process id */
#define WM_U2ED_EXEC (WM_APP + 0x55)
#define TC __attribute__((thiscall))

typedef int (TC *ExecFn)(void *self, const wchar_t *cmd, void *ar);
typedef void (TC *SerializeFn)(void *self, const wchar_t *v, int ev);

/* --- D3D8 screenshot support ---
 * COM vtable methods use __stdcall with an explicit "this" (unlike the C++
 * thiscall virtuals above), so these typedefs take self as a normal first
 * argument. Indices are from d3d8.h (IDirect3D8::CreateDevice = 15,
 * IDirect3DDevice8::GetBackBuffer/CreateImageSurface/CopyRects = 16/27/28,
 * IDirect3DSurface8::GetDesc/LockRect/UnlockRect = 8/9/10; Release on any
 * interface = 2). D3DFORMAT/D3DPOOL/etc. fields are all DWORD-sized enums, so
 * a plain DWORD is layout-compatible without pulling in real d3d8 headers. */
typedef void *(WINAPI *D3DCreate8Fn)(UINT sdkVersion);
typedef HRESULT (WINAPI *CreateDeviceFn)(void *self, UINT adapter, DWORD deviceType, HWND hFocus,
                                          DWORD behaviorFlags, void *presentParams, void **outDevice);
typedef HRESULT (WINAPI *GetBackBufferFn)(void *self, UINT which, DWORD type, void **outSurface);
typedef HRESULT (WINAPI *CreateImageSurfaceFn)(void *self, UINT w, UINT h, DWORD format, void **outSurface);
typedef HRESULT (WINAPI *CopyRectsFn)(void *self, void *src, const RECT *srcRects, UINT rectCount,
                                       void *dst, const POINT *dstPoints);
typedef HRESULT (WINAPI *SurfGetDescFn)(void *self, void *outDesc);
typedef HRESULT (WINAPI *SurfLockRectFn)(void *self, void *outLocked, const RECT *rect, DWORD flags);
typedef HRESULT (WINAPI *SurfUnlockRectFn)(void *self);
typedef ULONG (WINAPI *D3DReleaseFn)(void *self);

typedef struct { DWORD Format, Type, Usage, Pool, Size, MultiSampleType; UINT Width, Height; } D3DSurfaceDescMin;
typedef struct { LONG Pitch; void *pBits; } D3DLockedRectMin;

#define D3DCALL(obj, idx, Ty) (((Ty)((*(void ***)(obj))[idx])))
#define D3DFMT_A8R8G8B8 21
#define D3DFMT_X8R8G8B8 22
#define D3DFMT_R5G6B5   23

static void *g_device;             /* the most recently created/reset IDirect3DDevice8 */
static void *g_patchedD3DVtbl;     /* which IDirect3D8 vtable already has our CreateDevice hook */
static D3DCreate8Fn g_realD3DCreate8;
static CreateDeviceFn g_origCreateDevice;

/* GetProcAddress is hooked too: an IAT patch on Direct3DCreate8 only catches
   code that imports it by name at link time. If the renderer instead does
   GetProcAddress(hD3D8, "Direct3DCreate8") and calls through the returned
   pointer, that call never goes near any IAT slot we could have patched. */
typedef FARPROC (WINAPI *GetProcAddressFn)(HMODULE mod, LPCSTR name);
static GetProcAddressFn g_realGetProcAddress;

/* --- state shared between the pipe thread and the main thread --- */
static HWND g_main;              /* a window owned by the editor's main thread */
static DWORD g_mainThread;
static WNDPROC g_oldProc;
static HANDLE g_done;            /* signalled when the main thread ran a request */
static void *g_fexec;            /* GEditor's FExec subobject */
static volatile LONG g_capturing;
static int g_answerYes;

static wchar_t *g_req;           /* request being run */
static int g_rc;
static volatile LONG g_state;    /* 0 idle, 1 posted, 2 running on the main thread */
static char g_logPath[MAX_PATH];

/* U2EdBridge.log, next to the DLL */
static void BLog(const char *fmt, ...)
{
	char buf[1024];
	DWORD w;
	HANDLE f;
	va_list ap;
	SYSTEMTIME t;
	int n;
	GetLocalTime(&t);
	n = wsprintfA(buf, "[%02d:%02d:%02d] ", t.wHour, t.wMinute, t.wSecond);
	va_start(ap, fmt);
	n += wvsprintfA(buf + n, fmt, ap);
	va_end(ap);
	buf[n++] = '\r'; buf[n++] = '\n';
	f = CreateFileA(g_logPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, 0, NULL);
	if (f == INVALID_HANDLE_VALUE) return;
	WriteFile(f, buf, n, &w, NULL);
	CloseHandle(f);
}

/* capture buffer (UTF-16) */
static wchar_t *g_cap;
static size_t g_capLen, g_capMax;

static void CapAppend(const wchar_t *s, size_t n)
{
	if (g_capLen + n + 2 > g_capMax)
	{
		size_t m = g_capMax ? g_capMax * 2 : 65536;
		while (g_capLen + n + 2 > m) m *= 2;
		if (m > (8u << 20)) return;              /* 16 MB cap: drop the rest */
		wchar_t *p = g_cap ? (wchar_t *)HeapReAlloc(GetProcessHeap(), 0, g_cap, m * sizeof(wchar_t))
		                   : (wchar_t *)HeapAlloc(GetProcessHeap(), 0, m * sizeof(wchar_t));
		if (!p) return;
		g_cap = p; g_capMax = m;
	}
	memcpy(g_cap + g_capLen, s, n * sizeof(wchar_t));
	g_capLen += n;
}

static void CapLine(const wchar_t *s)
{
	if (!s) return;
	CapAppend(s, wcslen(s));
	CapAppend(L"\n", 1);
}

static int Capturing(void)
{
	return g_capturing && GetCurrentThreadId() == g_mainThread;
}

/* --- output devices: our own Ar, and taps on GLog / GWarn --- */

/* the device passed as Exec's Ar: a vtable pointer and nothing else */
static void TC ArSerialize(void *self, const wchar_t *v, int ev)
{
	(void)self; (void)ev;
	if (Capturing()) CapLine(v);
}
static void TC NopThis(void *self) { (void)self; }
static void *g_arVtbl[8] = { (void *)ArSerialize, (void *)NopThis, (void *)NopThis, (void *)NopThis,
                             (void *)NopThis, (void *)NopThis, (void *)NopThis, (void *)NopThis };
static struct { void **vtbl; char pad[60]; } g_ar = { g_arVtbl };

/* taps: the device keeps its own object and every other virtual; only slot 0
   (Serialize) is swapped for one that copies the text, then forwards it */
#define VT_COPY 64
typedef struct { void *obj; SerializeFn orig; void *vt[VT_COPY]; } Tap;
static Tap g_taps[2];

static void TC TapSerialize(void *self, const wchar_t *v, int ev)
{
	int i;
	if (Capturing()) CapLine(v);
	for (i = 0; i < 2; i++)
		if (g_taps[i].obj == self) { g_taps[i].orig(self, v, ev); return; }
}

static void InstallTap(Tap *t, void *obj)
{
	void **vtbl;
	DWORD old;
	if (!obj) return;
	vtbl = *(void ***)obj;
	memcpy(t->vt, vtbl, sizeof(t->vt));
	t->orig = (SerializeFn)vtbl[0];
	t->vt[0] = (void *)TapSerialize;
	t->obj = obj;
	VirtualProtect(obj, 4, PAGE_READWRITE, &old);
	*(void ***)obj = t->vt;
}

/* --- message boxes: answered instead of shown --- */

static int AutoAnswer(UINT type)
{
	switch (type & 0xF)
	{
	case MB_YESNO:
	case MB_YESNOCANCEL:     return g_answerYes ? IDYES : IDNO;
	case MB_OKCANCEL:        return g_answerYes ? IDOK : IDCANCEL;
	case MB_RETRYCANCEL:     return IDCANCEL;
	case MB_ABORTRETRYIGNORE:return IDIGNORE;
	default:                 return IDOK;
	}
}

static void LogBox(const wchar_t *cap, const wchar_t *text, int ans)
{
	wchar_t head[96];
	const wchar_t *a = ans == IDYES ? L"Yes" : ans == IDNO ? L"No" : ans == IDCANCEL ? L"Cancel"
	                 : ans == IDIGNORE ? L"Ignore" : L"OK";
	wsprintfW(head, L"[dialog -> %s] ", a);
	if (g_capturing)
	{
		CapAppend(head, wcslen(head));
		if (cap) { CapAppend(cap, wcslen(cap)); CapAppend(L": ", 2); }
		CapLine(text ? text : L"");
	}
	OutputDebugStringW(head);
}

static int WINAPI HookMessageBoxW(HWND h, LPCWSTR text, LPCWSTR cap, UINT type)
{
	int a = AutoAnswer(type);
	(void)h;
	LogBox(cap, text, a);
	return a;
}

static int WINAPI HookMessageBoxA(HWND h, LPCSTR text, LPCSTR cap, UINT type)
{
	wchar_t wt[2048], wc[256];
	int a = AutoAnswer(type);
	(void)h;
	wt[0] = wc[0] = 0;
	if (text) MultiByteToWideChar(CP_ACP, 0, text, -1, wt, 2048);
	if (cap)  MultiByteToWideChar(CP_ACP, 0, cap, -1, wc, 256);
	wt[2047] = wc[255] = 0;
	LogBox(wc, wt, a);
	return a;
}

/* point every loaded module's MessageBoxW/A import at our hooks; cheap, so it
   runs again before each command to catch DLLs loaded since */
static void PatchModule(HMODULE mod, void *realW, void *realA)
{
	BYTE *base = (BYTE *)mod;
	IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
	IMAGE_NT_HEADERS *nt;
	IMAGE_DATA_DIRECTORY *dir;
	IMAGE_IMPORT_DESCRIPTOR *imp;
	if (dos->e_magic != IMAGE_DOS_SIGNATURE) return;
	nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
	dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
	if (!dir->VirtualAddress) return;
	for (imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); imp->Name; imp++)
	{
		void **slot = (void **)(base + imp->FirstThunk);
		for (; *slot; slot++)
		{
			void *want = *slot == realW ? (void *)HookMessageBoxW
			           : *slot == realA ? (void *)HookMessageBoxA : NULL;
			if (want)
			{
				DWORD old;
				VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old);
				*slot = want;
				VirtualProtect(slot, sizeof(void *), old, &old);
			}
		}
	}
}

static void PatchMessageBoxes(void)
{
	HMODULE u32 = GetModuleHandleW(L"user32.dll");
	void *realW = (void *)GetProcAddress(u32, "MessageBoxW");
	void *realA = (void *)GetProcAddress(u32, "MessageBoxA");
	HMODULE self = NULL;
	MODULEENTRY32W me;
	HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
	GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
	                   (LPCWSTR)PatchMessageBoxes, &self);
	if (snap == INVALID_HANDLE_VALUE) return;
	me.dwSize = sizeof(me);
	if (Module32FirstW(snap, &me))
		do
			if (me.hModule != self && me.hModule != u32)
				PatchModule(me.hModule, realW, realA);
		while (Module32NextW(snap, &me));
	CloseHandle(snap);
}

/* --- D3D8 device capture: IAT-patch Direct3DCreate8, then patch the returned
   IDirect3D8 object's own CreateDevice slot (a class-wide vtable, so patching
   it once covers every device that class ever creates) --- */

static HRESULT WINAPI HookCreateDevice(void *self, UINT adapter, DWORD deviceType, HWND hFocus,
                                        DWORD behaviorFlags, void *presentParams, void **outDevice)
{
	HRESULT hr = g_origCreateDevice(self, adapter, deviceType, hFocus, behaviorFlags, presentParams, outDevice);
	if (SUCCEEDED(hr) && outDevice && *outDevice)
	{
		g_device = *outDevice;
		BLog("captured IDirect3DDevice8 %p", g_device);
	}
	return hr;
}

static void *WINAPI HookDirect3DCreate8(UINT sdkVersion)
{
	void *d3d = g_realD3DCreate8 ? g_realD3DCreate8(sdkVersion) : NULL;
	if (d3d && *(void ***)d3d != g_patchedD3DVtbl)
	{
		void **vtbl = *(void ***)d3d;
		DWORD old;
		g_origCreateDevice = (CreateDeviceFn)vtbl[15];
		VirtualProtect(vtbl, sizeof(void *) * 16, PAGE_READWRITE, &old);
		vtbl[15] = (void *)HookCreateDevice;
		VirtualProtect(vtbl, sizeof(void *) * 16, old, &old);
		g_patchedD3DVtbl = vtbl;
		BLog("patched IDirect3D8 CreateDevice at vtbl %p", (void *)vtbl);
	}
	return d3d;
}

/* mirrors PatchModule/PatchMessageBoxes below but for one import (Direct3DCreate8)
   in one module (d3d8.dll's own importers); kept separate rather than folded into
   the message-box patcher so that code stays untouched */
static void PatchD3DCreateInModule(HMODULE mod, HMODULE self, HMODULE d3d8)
{
	BYTE *base = (BYTE *)mod;
	IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
	IMAGE_NT_HEADERS *nt;
	IMAGE_DATA_DIRECTORY *dir;
	IMAGE_IMPORT_DESCRIPTOR *imp;
	if (mod == self || mod == d3d8 || dos->e_magic != IMAGE_DOS_SIGNATURE) return;
	nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
	dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
	if (!dir->VirtualAddress) return;
	for (imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); imp->Name; imp++)
	{
		void **slot = (void **)(base + imp->FirstThunk);
		for (; *slot; slot++)
			if (*slot == (void *)g_realD3DCreate8)
			{
				DWORD old;
				BLog("PatchD3DCreate: found Direct3DCreate8 import in module %p, patching", (void *)mod);
				VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old);
				*slot = (void *)HookDirect3DCreate8;
				VirtualProtect(slot, sizeof(void *), old, &old);
			}
	}
}

/* re-run before every command (like PatchMessageBoxes) to catch modules loaded
   since, and called once as early as possible from DllMain to win the race
   against the editor's own startup creating its first device */
static void PatchD3DCreate(void)
{
	HMODULE d3d8 = GetModuleHandleW(L"d3d8.dll");
	HMODULE self = NULL;
	MODULEENTRY32W me;
	HANDLE snap;
	static int everLogged;
	if (!d3d8) { if (!everLogged++) BLog("PatchD3DCreate: d3d8.dll not loaded yet"); return; }
	if (!g_realD3DCreate8)
		g_realD3DCreate8 = (D3DCreate8Fn)GetProcAddress(d3d8, "Direct3DCreate8");
	if (!g_realD3DCreate8) { if (!everLogged++) BLog("PatchD3DCreate: Direct3DCreate8 export not found"); return; }
	if (!everLogged++) BLog("PatchD3DCreate: d3d8.dll %p, Direct3DCreate8 %p, scanning modules", (void *)d3d8, (void *)g_realD3DCreate8);
	snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
	if (snap == INVALID_HANDLE_VALUE) return;
	GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
	                   (LPCWSTR)PatchD3DCreate, &self);
	me.dwSize = sizeof(me);
	if (Module32FirstW(snap, &me))
		do
			PatchD3DCreateInModule(me.hModule, self, d3d8);
		while (Module32NextW(snap, &me));
	CloseHandle(snap);
}

/* --- GetProcAddress("Direct3DCreate8") hook: covers dynamic resolution that
   the Direct3DCreate8 IAT patch above can't see --- */

static FARPROC WINAPI HookGetProcAddress(HMODULE mod, LPCSTR name)
{
	FARPROC real = g_realGetProcAddress(mod, name);
	if (real && (ULONG_PTR)name > 0xFFFF && !lstrcmpA(name, "Direct3DCreate8"))
	{
		if (!g_realD3DCreate8)
		{
			g_realD3DCreate8 = (D3DCreate8Fn)real;
			BLog("captured real Direct3DCreate8 %p via GetProcAddress", (void *)real);
		}
		return (FARPROC)HookDirect3DCreate8;
	}
	return real;
}

static void PatchGetProcAddressInModule(HMODULE mod, HMODULE self, HMODULE k32)
{
	BYTE *base = (BYTE *)mod;
	IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
	IMAGE_NT_HEADERS *nt;
	IMAGE_DATA_DIRECTORY *dir;
	IMAGE_IMPORT_DESCRIPTOR *imp;
	if (mod == self || mod == k32 || dos->e_magic != IMAGE_DOS_SIGNATURE) return;
	nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
	dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
	if (!dir->VirtualAddress) return;
	for (imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir->VirtualAddress); imp->Name; imp++)
	{
		void **slot = (void **)(base + imp->FirstThunk);
		for (; *slot; slot++)
			if (*slot == (void *)g_realGetProcAddress)
			{
				DWORD old;
				VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old);
				*slot = (void *)HookGetProcAddress;
				VirtualProtect(slot, sizeof(void *), old, &old);
			}
	}
}

/* like PatchD3DCreate: re-run before every command to catch modules loaded
   since, and called once as early as possible from DllMain */
static void PatchGetProcAddress(void)
{
	HMODULE k32 = GetModuleHandleW(L"kernel32.dll");
	HMODULE self = NULL;
	MODULEENTRY32W me;
	HANDLE snap;
	if (!g_realGetProcAddress)
		g_realGetProcAddress = (GetProcAddressFn)GetProcAddress(k32, "GetProcAddress");
	if (!g_realGetProcAddress) return;
	snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
	if (snap == INVALID_HANDLE_VALUE) return;
	GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
	                   (LPCWSTR)PatchGetProcAddress, &self);
	me.dwSize = sizeof(me);
	if (Module32FirstW(snap, &me))
		do
			PatchGetProcAddressInModule(me.hModule, self, k32);
		while (Module32NextW(snap, &me));
	CloseHandle(snap);
}

/* --- screenshot capture: GetBackBuffer -> CreateImageSurface (system memory,
   lockable) -> CopyRects -> LockRect, then a hand-rolled 24-bit BMP writer.
   D3DFMT_A8R8G8B8/X8R8G8B8 store bytes in memory as B,G,R,(A) on a little-endian
   machine, which is exactly a 24-bit BMP's pixel order once the 4th byte is
   dropped -- no color conversion needed for the common 32bpp case. */

static int WriteBMP(const wchar_t *path, void *bits, LONG pitch, UINT width, UINT height, DWORD format)
{
	HANDLE f;
	DWORD w, rowBytes, dataSize;
	BYTE fileHdr[14], infoHdr[40], *row, *src, *dst;
	UINT y, x;
	int bypp;

	if (format == D3DFMT_A8R8G8B8 || format == D3DFMT_X8R8G8B8) bypp = 4;
	else if (format == D3DFMT_R5G6B5) bypp = 2;
	else { CapLine(L"bridge: unsupported back buffer format for screenshot"); return 0; }

	rowBytes = (width * 3 + 3) & ~3u;
	dataSize = rowBytes * height;

	f = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
	if (f == INVALID_HANDLE_VALUE) { CapLine(L"bridge: could not create screenshot file"); return 0; }

	memset(fileHdr, 0, sizeof(fileHdr));
	fileHdr[0] = 'B'; fileHdr[1] = 'M';
	*(DWORD *)(fileHdr + 2) = 14 + 40 + dataSize;
	*(DWORD *)(fileHdr + 10) = 14 + 40;

	memset(infoHdr, 0, sizeof(infoHdr));
	*(DWORD *)(infoHdr + 0) = 40;
	*(LONG *)(infoHdr + 4) = (LONG)width;
	*(LONG *)(infoHdr + 8) = -(LONG)height;   /* negative height = top-down, matches D3D's memory layout */
	*(WORD *)(infoHdr + 12) = 1;
	*(WORD *)(infoHdr + 14) = 24;

	WriteFile(f, fileHdr, sizeof(fileHdr), &w, NULL);
	WriteFile(f, infoHdr, sizeof(infoHdr), &w, NULL);

	row = (BYTE *)HeapAlloc(GetProcessHeap(), 0, rowBytes);
	if (!row) { CloseHandle(f); return 0; }

	for (y = 0; y < height; y++)
	{
		src = (BYTE *)bits + (size_t)y * pitch;
		dst = row;
		memset(row, 0, rowBytes);
		if (bypp == 4)
			for (x = 0; x < width; x++) { dst[0] = src[0]; dst[1] = src[1]; dst[2] = src[2]; dst += 3; src += 4; }
		else
			for (x = 0; x < width; x++)
			{
				WORD p = *(WORD *)src;
				BYTE r5 = (BYTE)((p >> 11) & 0x1F), g6 = (BYTE)((p >> 5) & 0x3F), b5 = (BYTE)(p & 0x1F);
				dst[0] = (BYTE)((b5 * 527 + 23) >> 6);
				dst[1] = (BYTE)((g6 * 259 + 33) >> 6);
				dst[2] = (BYTE)((r5 * 527 + 23) >> 6);
				dst += 3; src += 2;
			}
		WriteFile(f, row, rowBytes, &w, NULL);
	}
	HeapFree(GetProcessHeap(), 0, row);
	CloseHandle(f);
	return 1;
}

static int DoScreenshot(const wchar_t *path)
{
	void *backbuf = NULL, *sysSurf = NULL;
	D3DSurfaceDescMin desc;
	D3DLockedRectMin lr;
	HRESULT hr;
	int ok = 0;

	if (!g_device) { CapLine(L"bridge: no D3D8 device captured yet (open or refresh a viewport, then retry)"); return 0; }

	hr = D3DCALL(g_device, 16, GetBackBufferFn)(g_device, 0, 0, &backbuf);
	if (FAILED(hr) || !backbuf) { CapLine(L"bridge: GetBackBuffer failed"); return 0; }

	memset(&desc, 0, sizeof(desc));
	D3DCALL(backbuf, 8, SurfGetDescFn)(backbuf, &desc);

	hr = D3DCALL(g_device, 27, CreateImageSurfaceFn)(g_device, desc.Width, desc.Height, desc.Format, &sysSurf);
	if (SUCCEEDED(hr) && sysSurf)
	{
		hr = D3DCALL(g_device, 28, CopyRectsFn)(g_device, backbuf, NULL, 0, sysSurf, NULL);
		if (SUCCEEDED(hr))
		{
			memset(&lr, 0, sizeof(lr));
			hr = D3DCALL(sysSurf, 9, SurfLockRectFn)(sysSurf, &lr, NULL, 0);
			if (SUCCEEDED(hr))
			{
				ok = WriteBMP(path, lr.pBits, lr.Pitch, desc.Width, desc.Height, desc.Format);
				D3DCALL(sysSurf, 10, SurfUnlockRectFn)(sysSurf);
			}
			else CapLine(L"bridge: LockRect failed");
		}
		else CapLine(L"bridge: CopyRects failed");
		D3DCALL(sysSurf, 2, D3DReleaseFn)(sysSurf);
	}
	else CapLine(L"bridge: CreateImageSurface failed");
	D3DCALL(backbuf, 2, D3DReleaseFn)(backbuf);
	if (ok) CapLine(L"screenshot saved");
	return ok;
}

/* --- running a request on the main thread --- */

static int RunBang(const wchar_t *cmd)
{
	if (!_wcsicmp(cmd, L"!ping")) { CapLine(L"pong"); return 1; }
	if (!_wcsnicmp(cmd, L"!answer ", 8))
	{
		g_answerYes = !_wcsicmp(cmd + 8, L"yes");
		CapLine(g_answerYes ? L"dialogs: Yes/OK" : L"dialogs: No/Cancel");
		return 1;
	}
	if (!_wcsicmp(cmd, L"!quit")) { BLog("quit requested"); TerminateProcess(GetCurrentProcess(), 0); return 1; }
	if (!_wcsnicmp(cmd, L"!screenshot ", 12)) return DoScreenshot(cmd + 12);
	CapLine(L"unknown bridge command (!ping, !answer yes|no, !quit, !screenshot <path>)");
	return 0;
}

static void RunRequest(void)
{
	/* the pipe thread may have given up on this request already */
	if (InterlockedCompareExchange(&g_state, 2, 1) != 1)
		return;
	PatchMessageBoxes();
	PatchGetProcAddress();
	PatchD3DCreate();
	g_capLen = 0;
	InterlockedExchange(&g_capturing, 1);
	if (g_req[0] == L'!')
		g_rc = RunBang(g_req);
	else
		g_rc = (*(ExecFn *)*(void **)g_fexec)(g_fexec, g_req, &g_ar);
	InterlockedExchange(&g_capturing, 0);
	InterlockedExchange(&g_state, 0);
	SetEvent(g_done);
}

static LRESULT CALLBACK SubProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
	if (m == WM_U2ED_EXEC)
	{
		RunRequest();
		return 0;
	}
	return CallWindowProcW(g_oldProc, h, m, w, l);
}

/* --- the editor's main window --- */

/* the biggest visible unowned top-level window of this process; during startup
   that is the splash screen, so BigWindow insists on at least 640x400 */
static BOOL CALLBACK FindMain(HWND h, LPARAM l)
{
	DWORD pid;
	RECT r, b;
	HWND *best = (HWND *)l;
	GetWindowThreadProcessId(h, &pid);
	if (pid != GetCurrentProcessId() || !IsWindowVisible(h) || GetWindow(h, GW_OWNER)) return TRUE;
	GetWindowRect(h, &r);
	if (!*best) { *best = h; return TRUE; }
	GetWindowRect(*best, &b);
	if ((r.right - r.left) * (r.bottom - r.top) > (b.right - b.left) * (b.bottom - b.top)) *best = h;
	return TRUE;
}

static HWND BigWindow(void)
{
	HWND h = NULL;
	RECT r;
	EnumWindows(FindMain, (LPARAM)&h);
	if (!h) return NULL;
	GetWindowRect(h, &r);
	return (r.right - r.left >= 640 && r.bottom - r.top >= 400) ? h : NULL;
}

/* (re)attach to the main window; runs before each request, so a replaced
   main window is picked up */
static int Attach(void)
{
	HWND h;
	char cls[128] = "", title[128] = "";
	if (g_main && IsWindow(g_main)) return 1;
	h = BigWindow();
	if (!h) return 0;
	g_main = h;
	g_mainThread = GetWindowThreadProcessId(h, NULL);
	g_oldProc = (WNDPROC)SetWindowLongPtrW(h, GWLP_WNDPROC, (LONG_PTR)SubProc);
	GetClassNameA(h, cls, sizeof(cls));
	GetWindowTextA(h, title, sizeof(title));
	BLog("attached to window %p class '%s' title '%s' thread %lu", (void *)h, cls, title, g_mainThread);
	return 1;
}

/* --- pipe server --- */

static int WriteAll(HANDLE p, const char *s, DWORD n)
{
	DWORD w;
	while (n)
	{
		if (!WriteFile(p, s, n, &w, NULL)) return 0;
		s += w; n -= w;
	}
	return 1;
}

static int SendReply(HANDLE p)
{
	char tail[64];
	int ok = 1;
	if (g_capLen)
	{
		int n = WideCharToMultiByte(CP_UTF8, 0, g_cap, (int)g_capLen, NULL, 0, NULL, NULL);
		char *u = (char *)HeapAlloc(GetProcessHeap(), 0, n + 1);
		if (u)
		{
			WideCharToMultiByte(CP_UTF8, 0, g_cap, (int)g_capLen, u, n, NULL, NULL);
			ok = WriteAll(p, u, n);
			HeapFree(GetProcessHeap(), 0, u);
		}
	}
	wsprintfA(tail, "<<<U2ED rc=%d>>>\n", g_rc);
	return ok && WriteAll(p, tail, lstrlenA(tail));
}

static void Fault(const wchar_t *msg)
{
	g_capLen = 0;
	CapLine(msg);
	g_rc = -1;
}

/* hand the request to the main thread; give up if it isn't picked up within
   15s (once running, a command may take as long as it needs) */
static void Dispatch(void)
{
	int waited;
	if (!Attach()) { Fault(L"bridge: no editor main window"); return; }
	ResetEvent(g_done);
	InterlockedExchange(&g_state, 1);
	PostMessageW(g_main, WM_U2ED_EXEC, 0, 0);
	for (waited = 0; ; waited += 250)
	{
		if (WaitForSingleObject(g_done, 250) == WAIT_OBJECT_0) return;
		if (waited >= 15000 && InterlockedCompareExchange(&g_state, 0, 1) == 1)
		{
			BLog("request not picked up by the main thread in 15s");
			g_main = NULL;   /* look for the window again next time */
			Fault(L"bridge: the editor did not pick up the command (busy, or a modal window is open)");
			return;
		}
	}
}

static void Serve(HANDLE p)
{
	static char line[65536];
	static wchar_t wline[65536];
	DWORD len = 0, got;
	for (;;)
	{
		char *nl;
		if (!ReadFile(p, line + len, sizeof(line) - 1 - len, &got, NULL) || !got) return;
		len += got;
		while ((nl = (char *)memchr(line, '\n', len)) != NULL)
		{
			int n = (int)(nl - line), k;
			if (n && line[n - 1] == '\r') n--;
			k = MultiByteToWideChar(CP_UTF8, 0, line, n, wline, 65535);
			wline[k] = 0;
			memmove(line, nl + 1, len - (nl + 1 - line));
			len -= (DWORD)(nl + 1 - line);
			if (!k) continue;
			g_req = wline;
			Dispatch();
			if (!SendReply(p)) return;
		}
		if (len >= sizeof(line) - 1) len = 0;   /* overlong line: drop it */
	}
}

/* --- startup --- */

static void *FindFExec(void *editor, void *fexecVtbl)
{
	/* the FExec subobject is the slot in GEditor holding that vtable */
	int i;
	for (i = 0; i < 0x4000 / 4; i++)
	{
		void **p = (void **)editor + i;
		if (IsBadReadPtr(p, 4)) return NULL;
		if (*p == fexecVtbl) return p;
	}
	return NULL;
}

/* --- the SET-on-ZoneInfo crash ---
   "SET Info ..." (or SET on ZoneInfo / LevelInfo / SkyZoneInfo) kills the editor with a general
   protection fault. UObject::GlobalSetProperty applies the value to EVERY object of the class, class
   default objects and objects outside the open map included, and calls PostEditChange on each;
   AZoneInfo::PostEditChange then reads this->XLevel to clear the level's render data without checking
   it for NULL, and those objects have no level. Read from Engine.dll with Ghidra (2026-10-05;
   Documents\U2_research\ghidra\SET_CRASH.md).
   Fix, in memory only: the function tests GIsEditor before that block; inside UnrealEd GIsEditor is
   always 1, so the test is replaced by a test of XLevel itself. Same length (15 bytes), same jump target.
     mov ecx,[&GIsEditor] / mov eax,[ecx] / add esp,10h / test eax,eax / je +73h
   becomes
     mov eax,[esi+0D4h]     / add esp,10h / test eax,eax / je +75h / nop / nop        */
static void PatchZoneInfoSet(void)
{
	HMODULE eng = GetModuleHandleW(L"Engine.dll");
	BYTE *fn, *p;
	DWORD old;
	static const BYTE want[15] = { 0x8B, 0x0D, 0, 0, 0, 0, 0x8B, 0x01, 0x83, 0xC4, 0x10, 0x85, 0xC0, 0x74, 0x73 };
	static const BYTE fix[15]  = { 0x8B, 0x86, 0xD4, 0x00, 0x00, 0x00, 0x83, 0xC4, 0x10, 0x85, 0xC0, 0x74, 0x75, 0x90, 0x90 };
	int i;
	if (!eng) { BLog("ZoneInfo patch: Engine.dll not loaded"); return; }
	fn = (BYTE *)GetProcAddress(eng, "?PostEditChange@AZoneInfo@@UAEXXZ");
	if (!fn) { BLog("ZoneInfo patch: AZoneInfo::PostEditChange export not found"); return; }
	p = fn + 0x69;
	for (i = 0; i < 15; i++)
		if (i != 2 && i != 3 && i != 4 && i != 5 && p[i] != want[i])
		{
			BLog("ZoneInfo patch: unexpected code at %p (byte %d is %02X), not patched", (void *)p, i, p[i]);
			return;
		}
	if (!VirtualProtect(p, 15, PAGE_EXECUTE_READWRITE, &old)) { BLog("ZoneInfo patch: VirtualProtect failed"); return; }
	memcpy(p, fix, 15);
	VirtualProtect(p, 15, old, &old);
	FlushInstructionCache(GetCurrentProcess(), p, 15);
	BLog("ZoneInfo patch: AZoneInfo::PostEditChange now skips objects with no level (SET Info is safe)");
}

static DWORD WINAPI Main(LPVOID unused)
{
	HMODULE ed = NULL, core = NULL;
	void ***pEditor = NULL, *fexecVtbl = NULL;
	void **pLog, **pWarn;
	wchar_t pipeName[64];
	int i;
	(void)unused;

	BLog("loaded into process %lu", GetCurrentProcessId());
	/* wait (up to 5 minutes) for the editor engine and its main window */
	for (i = 0; i < 3000; i++, Sleep(100))
	{
		if (!ed) ed = GetModuleHandleW(L"Editor.dll");
		if (!core) core = GetModuleHandleW(L"Core.dll");
		if (!ed || !core) continue;
		pEditor = (void ***)GetProcAddress(ed, "?GEditor@@3PAVUEditorEngine@@A");
		fexecVtbl = (void *)GetProcAddress(ed, "??_7UEditorEngine@@6BFExec@@@");
		if (!pEditor || !fexecVtbl) { BLog("Editor.dll exports not found"); return 1; }
		if (*pEditor && BigWindow()) break;
	}
	if (!pEditor || !*pEditor || !BigWindow()) { BLog("editor never became ready"); return 1; }
	Sleep(3000);   /* let the editor finish opening its browsers */

	g_fexec = FindFExec(*pEditor, fexecVtbl);
	if (!g_fexec) { BLog("FExec subobject not found"); return 1; }
	BLog("GEditor %p, FExec at +0x%x", (void *)*pEditor, (unsigned)((char *)g_fexec - (char *)*pEditor));
	PatchZoneInfoSet();

	pLog = (void **)GetProcAddress(core, "?GLog@@3PAVFOutputDevice@@A");
	pWarn = (void **)GetProcAddress(core, "?GWarn@@3PAVFFeedbackContext@@A");
	if (pLog) InstallTap(&g_taps[0], *pLog);
	if (pWarn && (!pLog || *pWarn != *pLog)) InstallTap(&g_taps[1], *pWarn);

	g_done = CreateEventW(NULL, TRUE, FALSE, NULL);
	if (!Attach()) { BLog("main window vanished"); return 1; }
	PatchMessageBoxes();

	/* one pipe per editor process, never shared: a crashed editor that lingers
	   can't squat on the name of a new one */
	wsprintfW(pipeName, PIPE_NAME, GetCurrentProcessId());
	BLog("listening on the pipe");
	for (;;)
	{
		HANDLE p = CreateNamedPipeW(pipeName, PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
			PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
			1, 1 << 16, 1 << 16, 0, NULL);
		if (p == INVALID_HANDLE_VALUE) { Sleep(1000); continue; }
		if (ConnectNamedPipe(p, NULL) || GetLastError() == ERROR_PIPE_CONNECTED)
			Serve(p);
		FlushFileBuffers(p);
		DisconnectNamedPipe(p);
		CloseHandle(p);
	}
	return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
	(void)reserved;
	if (reason == DLL_PROCESS_ATTACH)
	{
		HANDLE t;
		char *slash;
		DisableThreadLibraryCalls(inst);
		GetModuleFileNameA(inst, g_logPath, MAX_PATH);
		slash = strrchr(g_logPath, '\\');
		lstrcpyA(slash ? slash + 1 : g_logPath, "U2EdBridge.log");
		/* as early as possible: the editor's own (pre-existing) main thread keeps
		   running while this DllMain executes on the freshly injected thread, so
		   every millisecond before this hook is armed is a chance to miss the
		   editor's first Direct3DCreate8 call */
		PatchGetProcAddress();
		PatchD3DCreate();
		t = CreateThread(NULL, 0, Main, NULL, 0, NULL);
		if (t) CloseHandle(t);
	}
	return TRUE;
}
