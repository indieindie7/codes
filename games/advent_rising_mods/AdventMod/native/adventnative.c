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
int CaptureNext(int Mask);  /* capture.c */
int SetMaxFps(int Fps);     /* capture.c */
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
/* Sets "Key=Value" in System\U2Shaders.ini (the U2Shaders d3d8.dll layer's settings; it
   picks the file up again while the game runs), replacing the key's line or adding one.
   Value NULL removes the line. 0 when the file isn't there. */
static int SetU2(const char* Key, const char* Value)
{
	wchar_t Path[MAX_PATH], *Slash;
	char Buf[8192], Out[8400];
	FILE* F;
	size_t Len, o = 0, K = strlen(Key);
	char* Line;
	int Found = 0;

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
		if (!_strnicmp(Line, Key, K) && Line[K] == '=')
		{
			if (Value && !Found) o += sprintf(Out + o, "%s=%s\r\n", Key, Value);
			Found = 1;
		}
		else o += sprintf(Out + o, "%s\r\n", Line);
		if (o > sizeof(Out) - 600) break;
	}
	if (!Found && Value) o += sprintf(Out + o, "%s=%s\r\n", Key, Value);
	F = _wfopen(Path, L"wb");
	if (!F) return 0;
	fwrite(Out, 1, o, F);
	fclose(F);
	return 1;
}

static int SetPcss(int On)
{
	static int Last = -1;
	if (On == Last) return 1;
	if (!SetU2("pcss", On ? "1" : "0")) return 0;
	Last = On;
	Note(L"contact-hardening shadows %ls", On ? L"on (indoors)" : L"off (outdoors: the plain sun shadow)");
	return 1;
}

/* NativeCall("Blood:<command>"): a live blood pool command for the d3d8 layer (its blood.hpp;
   the export U2BloodCommand), e.g. "pool 0 120 0.02 0" or "stamp 0 0.5 0.5 1.2 0 0.08". */
typedef int (__cdecl *U2BloodCommand_t)(const char*);
static int BloodCommand(const wchar_t* Arg)
{
	static U2BloodCommand_t Fn;
	static int Tried;
	char Cmd[256];
	if (!Tried)
	{
		HMODULE D3D = GetModuleHandleW(L"d3d8.dll");
		Tried = 1;
		if (D3D) Fn = (U2BloodCommand_t)GetProcAddress(D3D, "U2BloodCommand");
		Note(L"blood: the d3d8 layer's live pools are %ls", Fn ? L"available" : L"not in this d3d8.dll (pools stay baked)");
	}
	if (!Fn) return 0;
	WideCharToMultiByte(CP_ACP, 0, Arg, -1, Cmd, sizeof(Cmd), 0, 0);
	Cmd[sizeof(Cmd) - 1] = 0;
	return Fn(Cmd);
}

/* NativeCall("U2Set:key=value"): one U2Shaders.ini setting ("U2Set:key=" removes the line) */
static int U2SetCommand(const wchar_t* Arg)
{
	char A[512], *Eq;
	WideCharToMultiByte(CP_ACP, 0, Arg, -1, A, sizeof(A), NULL, NULL);
	Eq = strchr(A, '=');
	if (!Eq || Eq == A) return 0;
	*Eq = 0;
	Note(L"U2Shaders.ini: %ls", Arg);
	return SetU2(A, Eq[1] ? Eq + 1 : NULL);
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


/* NativeCall("LiveReq:WORD"): live sessions (tools/live_reload.py). True, once, when System\AdventLive.req
   holds that word (save, reload, forget, quit): the request is then deleted. A fixed set of
   words the mod's ModLive asks about: nothing in the file is ever run as a command. */
static int LiveRequest(const wchar_t* Word)
{
	wchar_t Path[MAX_PATH], Line[64] = L"";
	FILE* F;
	int n;
	GetModuleFileNameW(NULL, Path, MAX_PATH);
	if (wcsrchr(Path, 92)) wcscpy_s(wcsrchr(Path, 92) + 1, MAX_PATH - (wcsrchr(Path, 92) + 1 - Path), L"AdventLive.req");   /* after the last backslash */
	if (_wfopen_s(&F, Path, L"r") || !F) return 0;
	fgetws(Line, 64, F);
	fclose(F);
	for (n = (int)wcslen(Line); n > 0 && (Line[n - 1] == L'\n' || Line[n - 1] == L'\r' || Line[n - 1] == L' '); n--) Line[n - 1] = 0;
	if (_wcsicmp(Line, Word)) return 0;
	DeleteFileW(Path);
	Note(L"live: request '%ls'", Word);
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
	if (!_wcsnicmp(Cmd, L"LiveReq:", 8)) return LiveRequest(Cmd + 8);
	if (!_wcsicmp(Cmd, L"TestCrashThread")) { Note(L"testing: a thread calling address 0 on purpose"); CreateThread(0, 0, (LPTHREAD_START_ROUTINE)0, 0, 0, 0); return 1; }
	if (!_wcsicmp(Cmd, L"TestCrash")) { void (*Nowhere)(void) = 0; Note(L"testing: calling address 0 on purpose"); Nowhere(); return 1; }
	if (!_wcsicmp(Cmd, L"BorderlessOn")) return SetBorderless(1);
	if (!_wcsicmp(Cmd, L"BorderlessOff")) return SetBorderless(0);
	if (!_wcsicmp(Cmd, L"IsBorderless")) return Borderless;
	if (!_wcsicmp(Cmd, L"D3DTrace")) return D3DTraceStart();
	if (!_wcsicmp(Cmd, L"ShadowFix")) return ShadowFixApply();
	if (!_wcsicmp(Cmd, L"ShadowAlpha")) return ShadowAlphaApply();
	if (!_wcsicmp(Cmd, L"Capture")) return CaptureNext(-1);
	if (!_wcsicmp(Cmd, L"CaptureMask")) return CaptureNext(1);   /* the frame and a character mask (U2Shaders layer) */
	if (!_wcsnicmp(Cmd, L"MaxFps:", 7)) return SetMaxFps(_wtoi(Cmd + 7));
	if (!_wcsicmp(Cmd, L"D3DZAlways")) { D3DZAlways = 1; Note(L"d3dtrace: projected draws now always pass the depth test"); return 1; }
	if (!_wcsnicmp(Cmd, L"Pcss:", 5)) return SetPcss(Cmd[5] == L'1');
	if (!_wcsnicmp(Cmd, L"U2Set:", 6)) return U2SetCommand(Cmd + 6);
	if (!_wcsnicmp(Cmd, L"Blood:", 6)) return BloodCommand(Cmd + 6);
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


/* a crash the game's own handler doesn't catch (the ones that end in the Windows "stopped
   working" record): what and where, to AdventNative.log, and a minidump next to it
   (AdventCrash.dmp, readable in WinDbg / Visual Studio). The filter then lets Windows carry on
   as before. */
typedef BOOL (WINAPI *MiniDumpWriteDump_t)(HANDLE, DWORD, HANDLE, int, void*, void*, void*);
static LPTOP_LEVEL_EXCEPTION_FILTER PrevFilter;

static void Where(wchar_t* Out, size_t N, void* At)
{
	HMODULE M = 0;
	wchar_t Path[MAX_PATH], *Base;
	if (At && GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)At, &M) && M)
	{
		GetModuleFileNameW(M, Path, MAX_PATH);
		Base = wcsrchr(Path, L'\\'); Base = Base ? Base + 1 : Path;
		swprintf(Out, N, L"%ls+%08X", Base, (unsigned)((char*)At - (char*)M));
	}
	else
		swprintf(Out, N, L"%08X", (unsigned)(size_t)At);
}

static LONG WINAPI CrashFilter(EXCEPTION_POINTERS* E)
{
	wchar_t W[160];
	EXCEPTION_RECORD* R = E->ExceptionRecord;
	CONTEXT* C = E->ContextRecord;
	int i;
	Where(W, 160, R->ExceptionAddress);
	Note(L"crash: exception %08X at %ls (eip %08X)", R->ExceptionCode, W, (unsigned)C->Eip);
	if (R->ExceptionCode == EXCEPTION_ACCESS_VIOLATION && R->NumberParameters >= 2)
		Note(L"crash: %ls address %08X", R->ExceptionInformation[0] == 8 ? L"executing" : R->ExceptionInformation[0] ? L"writing" : L"reading", (unsigned)R->ExceptionInformation[1]);
	/* the callers: the frame chain, then the top of the stack (for a jump to nowhere the
	   return address is the first thing there) */
	{
		DWORD* Fp = (DWORD*)C->Ebp;
		for (i = 0; i < 16 && Fp && !IsBadReadPtr(Fp, 8); i++)
		{
			Where(W, 160, (void*)Fp[1]);
			Note(L"crash: frame %d from %ls", i, W);
			if ((DWORD*)Fp[0] <= Fp) break;
			Fp = (DWORD*)Fp[0];
		}
		{
			DWORD* Sp = (DWORD*)C->Esp;
			wchar_t Line[600] = L"";
			for (i = 0; i < 24 && !IsBadReadPtr(Sp + i, 4); i++)
			{
				HMODULE M = 0;
				if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)Sp[i], &M) && M)
				{
					Where(W, 160, (void*)Sp[i]);
					if (wcslen(Line) + wcslen(W) + 12 < 600) swprintf(Line + wcslen(Line), 600 - wcslen(Line), L"[%d]%ls ", i, W);
				}
			}
			Note(L"crash: code addresses on the stack: %ls", Line);
		}
	}
	{
		HMODULE Dbg = LoadLibraryW(L"dbghelp.dll");
		MiniDumpWriteDump_t Write = Dbg ? (MiniDumpWriteDump_t)GetProcAddress(Dbg, "MiniDumpWriteDump") : 0;
		HANDLE F = Write ? CreateFileW(L"AdventCrash.dmp", GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0) : INVALID_HANDLE_VALUE;
		if (F != INVALID_HANDLE_VALUE)
		{
			struct { DWORD ThreadId; EXCEPTION_POINTERS* E; BOOL Client; } Info = { GetCurrentThreadId(), E, FALSE };
			BOOL Ok = Write(GetCurrentProcess(), GetCurrentProcessId(), F, 0x0040 /* MiniDumpWithIndirectlyReferencedMemory: the stacks and what they point at (with data segments the file was 330 MB) */, &Info, 0, 0);
			CloseHandle(F);
			Note(L"crash: minidump %ls (System\\AdventCrash.dmp)", Ok ? L"written" : L"failed");
		}
	}
	return PrevFilter ? PrevFilter(E) : EXCEPTION_CONTINUE_SEARCH;
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
			PrevFilter = SetUnhandledExceptionFilter(CrashFilter);
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
