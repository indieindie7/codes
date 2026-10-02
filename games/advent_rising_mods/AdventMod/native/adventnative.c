/* AdventNative.dll - native helpers for AdventMod (Advent Rising).

   UnrealScript can't change the window, and a script package can only have
   native functions through a full native class. Instead the engine loads this
   DLL by itself: a DynamicLoadObject("AdventNative.X") finds no AdventNative.u
   and falls back to the package's DLL. Once loaded we redirect Core.dll's
   UObject::StaticLoadObject export, and every later
   DynamicLoadObject("AdventNative.<Command>", class'Class', true) is a call
   into HandleCommand: it returns the class (script sees non-None = true) or
   NULL (None = false). */
#include <windows.h>
#include <wchar.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

int D3DTraceStart(void);   /* d3dtrace.c */
int ShadowFixApply(void);  /* shadowfix.c */
int ShadowAlphaApply(void); /* shadowalpha.c */
extern int D3DZAlways;

__declspec(dllexport) wchar_t GPackage[] = L"AdventNative";

typedef void* (__cdecl *StaticLoadObject_t)(void* Class, void* Outer, const wchar_t* Name, const wchar_t* File, DWORD Flags, void* Sandbox);
static StaticLoadObject_t RealSLO;

/* AdventNative.log, next to the game's own log */
void Note(const wchar_t* Fmt, ...)
{
	static wchar_t Line[1024];
	char Utf8[2048];
	va_list A;
	HANDLE F;
	DWORD N;
	va_start(A, Fmt);
	_vsnwprintf(Line, 1020, Fmt, A);
	va_end(A);
	Line[1020] = 0;
	wcscat(Line, L"\r\n");
	F = CreateFileW(L"AdventNative.log", FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
	if (F == INVALID_HANDLE_VALUE) return;
	N = WideCharToMultiByte(CP_UTF8, 0, Line, -1, Utf8, sizeof(Utf8), NULL, NULL);
	if (N > 1) WriteFile(F, Utf8, N - 1, &N, NULL);
	CloseHandle(F);
}

/* ------------------------------------------------------------ borderless */

static HWND GameWindow;
/* The contact-hardening shadow layer (the U2Shaders d3d8.dll, when installed) reads
   "pcss=" from System\U2Shaders.ini. Rewrites that line only when the value changes;
   the layer picks the file up again while the game runs. 0 when the layer isn't there. */
static int SetPcss(int On)
{
	static int Last = -1;
	wchar_t Path[MAX_PATH], *Slash;
	char Buf[8192], Out[8400];
	FILE* F;
	size_t Len, o = 0;
	char* Line;
	int Found = 0;

	if (On == Last) return 1;
	GetModuleFileNameW(NULL, Path, MAX_PATH);
	Slash = wcsrchr(Path, L'\\');
	if (!Slash) return 0;
	wcscpy(Slash + 1, L"U2Shaders.ini");
	F = _wfopen(Path, L"rb");
	if (!F) return 0;
	Len = fread(Buf, 1, sizeof(Buf) - 1, F);
	fclose(F);
	Buf[Len] = 0;
	for (Line = strtok(Buf, "\r\n"); Line; Line = strtok(NULL, "\r\n"))
	{
		if (!_strnicmp(Line, "pcss=", 5)) { o += sprintf(Out + o, "pcss=%d\r\n", On); Found = 1; }
		else o += sprintf(Out + o, "%s\r\n", Line);
		if (o > sizeof(Out) - 600) break;
	}
	if (!Found) o += sprintf(Out + o, "pcss=%d\r\n", On);
	F = _wfopen(Path, L"wb");
	if (!F) return 0;
	fwrite(Out, 1, o, F);
	fclose(F);
	Last = On;
	Note(L"contact-hardening shadows %ls", On ? L"on (indoors)" : L"off (outdoors: the plain sun shadow)");
	return 1;
}

static int Borderless;
static LONG SavedStyle, SavedExStyle;
static RECT SavedRect;

static BOOL CALLBACK FindWindowProc(HWND H, LPARAM L)
{
	DWORD Pid;
	RECT R;
	GetWindowThreadProcessId(H, &Pid);
	if (Pid != GetCurrentProcessId() || !IsWindowVisible(H) || GetWindow(H, GW_OWNER)) return TRUE;
	GetWindowRect(H, &R);
	if (R.right - R.left < 320) return TRUE;
	GameWindow = H;
	return FALSE;
}

static int SetBorderless(int On)
{
	MONITORINFO Mi = { sizeof(Mi) };
	if (!GameWindow || !IsWindow(GameWindow)) { GameWindow = NULL; EnumWindows(FindWindowProc, 0); }
	if (!GameWindow) { Note(L"borderless: no game window found"); return 0; }
	if (On && !Borderless)
	{
		SavedStyle = GetWindowLongW(GameWindow, GWL_STYLE);
		SavedExStyle = GetWindowLongW(GameWindow, GWL_EXSTYLE);
		GetWindowRect(GameWindow, &SavedRect);
		GetMonitorInfoW(MonitorFromWindow(GameWindow, MONITOR_DEFAULTTONEAREST), &Mi);
		SetWindowLongW(GameWindow, GWL_STYLE, (SavedStyle & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)) | WS_POPUP);
		SetWindowLongW(GameWindow, GWL_EXSTYLE, SavedExStyle & ~(WS_EX_DLGMODALFRAME | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE | WS_EX_WINDOWEDGE));
		SetWindowPos(GameWindow, HWND_TOP, Mi.rcMonitor.left, Mi.rcMonitor.top, Mi.rcMonitor.right - Mi.rcMonitor.left, Mi.rcMonitor.bottom - Mi.rcMonitor.top, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
		Borderless = 1;
		Note(L"borderless on: %dx%d at %d,%d", Mi.rcMonitor.right - Mi.rcMonitor.left, Mi.rcMonitor.bottom - Mi.rcMonitor.top, Mi.rcMonitor.left, Mi.rcMonitor.top);
	}
	else if (!On && Borderless)
	{
		SetWindowLongW(GameWindow, GWL_STYLE, SavedStyle);
		SetWindowLongW(GameWindow, GWL_EXSTYLE, SavedExStyle);
		/* a window that was already screen-sized (the game remembers its last size) would
		   come back larger than the screen: give it a normal centred window instead */
		GetMonitorInfoW(MonitorFromWindow(GameWindow, MONITOR_DEFAULTTONEAREST), &Mi);
		if (SavedRect.right - SavedRect.left >= Mi.rcMonitor.right - Mi.rcMonitor.left)
		{
			int W = (Mi.rcWork.right - Mi.rcWork.left) * 5 / 6, Ht = (Mi.rcWork.bottom - Mi.rcWork.top) * 5 / 6;
			SavedRect.left = Mi.rcWork.left + (Mi.rcWork.right - Mi.rcWork.left - W) / 2;
			SavedRect.top = Mi.rcWork.top + (Mi.rcWork.bottom - Mi.rcWork.top - Ht) / 2;
			SavedRect.right = SavedRect.left + W;
			SavedRect.bottom = SavedRect.top + Ht;
		}
		SetWindowPos(GameWindow, HWND_NOTOPMOST, SavedRect.left, SavedRect.top, SavedRect.right - SavedRect.left, SavedRect.bottom - SavedRect.top, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
		Borderless = 0;
		Note(L"borderless off");
	}
	return 1;
}

/* ------------------------------------------------------------ commands */

static int HandleCommand(const wchar_t* Cmd)
{
	if (!_wcsicmp(Cmd, L"Init"))
	{
		/* which Direct3D 8 the game got: the system's, or a wrapper in the game folder */
		wchar_t Path[MAX_PATH] = L"(not loaded)";
		HMODULE D3D = GetModuleHandleW(L"d3d8.dll");
		if (D3D) GetModuleFileNameW(D3D, Path, MAX_PATH);
		Note(L"d3d8: %ls", Path);
		return 1;
	}
	if (!_wcsnicmp(Cmd, L"Note:", 5)) { Note(L"%ls", Cmd + 5); return 1; }
	if (!_wcsicmp(Cmd, L"BorderlessOn")) return SetBorderless(1);
	if (!_wcsicmp(Cmd, L"BorderlessOff")) return SetBorderless(0);
	if (!_wcsicmp(Cmd, L"IsBorderless")) return Borderless;
	if (!_wcsicmp(Cmd, L"D3DTrace")) return D3DTraceStart();
	if (!_wcsicmp(Cmd, L"ShadowFix")) return ShadowFixApply();
	if (!_wcsicmp(Cmd, L"ShadowAlpha")) return ShadowAlphaApply();
	if (!_wcsicmp(Cmd, L"D3DZAlways")) { D3DZAlways = 1; Note(L"d3dtrace: projected draws now always pass the depth test"); return 1; }
	if (!_wcsnicmp(Cmd, L"Pcss:", 5)) return SetPcss(Cmd[5] == L'1');
	if (!_wcsnicmp(Cmd, L"Fits:", 5))
	{
		/* does WxH fit on the screen the game is on? */
		MONITORINFO Mi = { sizeof(Mi) };
		int W = 0, Ht = 0;
		if (swscanf(Cmd + 5, L"%dx%d", &W, &Ht) != 2) return 0;
		if (!GameWindow || !IsWindow(GameWindow)) { GameWindow = NULL; EnumWindows(FindWindowProc, 0); }
		if (!GetMonitorInfoW(MonitorFromWindow(GameWindow, MONITOR_DEFAULTTOPRIMARY), &Mi)) return 0;
		return W <= Mi.rcMonitor.right - Mi.rcMonitor.left && Ht <= Mi.rcMonitor.bottom - Mi.rcMonitor.top;
	}
	return 0;
}

/* One of the mod's own classes failed to load quietly: ask again with LOAD_Throw
   and note the engine's reason (it throws the message as a const TCHAR*). */
static int NoteThrown(EXCEPTION_POINTERS* E)
{
	if (E->ExceptionRecord->ExceptionCode == 0xE06D7363 && E->ExceptionRecord->NumberParameters >= 2 && E->ExceptionRecord->ExceptionInformation[1])
		Note(L"load failed: %ls", *(const wchar_t**)E->ExceptionRecord->ExceptionInformation[1]);
	else
		Note(L"load failed: exception %08X", E->ExceptionRecord->ExceptionCode);
	return EXCEPTION_EXECUTE_HANDLER;
}

static void WhyNot(void* Class, void* Outer, const wchar_t* Name, const wchar_t* File, void* Sandbox)
{
	__try { if (!RealSLO(Class, Outer, Name, File, 0x8 | 0x2, Sandbox)) Note(L"load failed without a reason: %ls", Name); }
	__except (NoteThrown(GetExceptionInformation())) { }
}

static void* __cdecl HookSLO(void* Class, void* Outer, const wchar_t* Name, const wchar_t* File, DWORD Flags, void* Sandbox)
{
	void* Result;

	if (Name && !Outer && !_wcsnicmp(Name, L"AdventNative.", 13))
		return HandleCommand(Name + 13) ? Class : NULL;
	Result = RealSLO(Class, Outer, Name, File, Flags, Sandbox);
	if (!Result && Name && !_wcsnicmp(Name, L"AdventMod.", 10))
		WhyNot(Class, Outer, Name, File, Sandbox);
	return Result;
}

/* Core's exports are jump thunks: point one at our function, keep the real one */
static void* Redirect(HMODULE Core, const char* Name, void* To)
{
	BYTE* Thunk = (BYTE*)GetProcAddress(Core, Name);
	void* Real;
	DWORD Old;
	if (!Thunk || Thunk[0] != 0xE9) return NULL;
	Real = Thunk + 5 + *(LONG*)(Thunk + 1);
	if (!VirtualProtect(Thunk, 5, PAGE_EXECUTE_READWRITE, &Old)) return NULL;
	*(LONG*)(Thunk + 1) = (LONG)((BYTE*)To - (Thunk + 5));
	VirtualProtect(Thunk, 5, Old, &Old);
	FlushInstructionCache(GetCurrentProcess(), Thunk, 5);
	return Real;
}

BOOL WINAPI DllMain(HINSTANCE H, DWORD Reason, LPVOID R)
{
	if (Reason == DLL_PROCESS_ATTACH)
	{
		HMODULE Core = GetModuleHandleW(L"Core.dll");
		DisableThreadLibraryCalls(H);
		if (Core && !RealSLO)
		{
			HMODULE Pin;
			RealSLO = (StaticLoadObject_t)Redirect(Core, "?StaticLoadObject@UObject@@SAPAV1@PAVUClass@@PAV1@PBG2KPAVUPackageMap@@@Z", HookSLO);
			/* the hook points into this DLL: never unload it */
			GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN | GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, (LPCWSTR)HookSLO, &Pin);
			DeleteFileW(L"AdventNative.log");
			Note(L"AdventNative loaded, hook %ls", RealSLO ? L"ready" : L"FAILED");
			{
				/* which Direct3D 8 the game got: the system's, or a wrapper in the game folder */
				wchar_t Path[MAX_PATH] = L"(not loaded yet)";
				HMODULE D3D = GetModuleHandleW(L"d3d8.dll");
				if (D3D) GetModuleFileNameW(D3D, Path, MAX_PATH);
				Note(L"d3d8: %ls", Path);
			}
		}
	}
	return TRUE;
}
