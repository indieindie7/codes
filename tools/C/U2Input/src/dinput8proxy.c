/*
 * U2Input - dinput8.dll proxy that lets a program drive Unreal II's mouse and
 * keyboard (menus included) without touching the real mouse or needing focus.
 *
 * Unreal II (WinDrv.dll) reads the mouse and keyboard through DirectInput 8;
 * its menu cursor follows DirectInput's relative movement and clicks come only
 * from DirectInput buttons, so window messages can move the cursor over a button
 * but never press it. Dropped into System\ next to Unreal2.exe, this DLL loads
 * the real dinput8.dll from the Windows folder, hands the game its devices, and
 * mixes in input sent over a named pipe:
 *
 *     \\.\pipe\U2Input-<pid>     one command per line, answered with "ok" / "error ..."
 *
 *     move DX DY        relative mouse movement (DirectInput units)
 *     down N / up N     mouse button N (0 left, 1 right, 2 middle) held / released
 *     click N           press, then release a few polls later
 *     key DIK down|up   a keyboard key by DirectInput scan code (DIK_*)
 *     tap DIK           press and release
 *     focus on|off      tell the game it has focus (needed while it runs in the background)
 *     cursor X Y        virtual cursor position in client pixels (with focus on): menus hover here
 *     vkey VK           press+release a key by Windows virtual-key code (the keyboard is read from
 *     vdown VK / vup VK   window messages, not DirectInput); e.g. vkey 117 = F6
 *     ping              "pong"; also reports which read path the game uses
 *     char CODE         type one character (WM_CHAR): console and menu text boxes
 *     nativeexec CMD    EXPERIMENTAL, crashes Unreal II: calls UGameEngine::Exec on the main thread.
 *                       Use typing instead (Tab, chars, Enter: u2ctl.py exec does that).
 *
 * Injected input also flows while the game window is in the background: if
 * the real device call fails only because the device isn't acquired, the
 * injected data is returned instead.
 *
 * Build (MSVC x86): see build.bat. Log: System\U2Input.log.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef DI_OK
#define DI_OK S_OK
#endif

typedef HRESULT (WINAPI *DI8CreateFn)(HINSTANCE, DWORD, REFIID, LPVOID *, void *);

static HMODULE g_real;
static DI8CreateFn g_realCreate;
static CRITICAL_SECTION g_lock;
static char g_logPath[MAX_PATH];

static const GUID GUID_SysMouse_ = {0x6F1D2B60, 0xD5A0, 0x11CF, {0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00}};
static const GUID GUID_SysKeyboard_ = {0x6F1D2B61, 0xD5A0, 0x11CF, {0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00}};

/* vtable slots */
enum { DI_CreateDevice = 3 };
enum { DEV_Acquire = 7, DEV_GetDeviceState = 9, DEV_GetDeviceData = 10 };

typedef HRESULT (WINAPI *CreateDeviceFn)(void *self, REFGUID guid, void **dev, void *outer);
typedef HRESULT (WINAPI *GetStateFn)(void *self, DWORD cb, void *data);
typedef HRESULT (WINAPI *GetDataFn)(void *self, DWORD cbObj, void *rgdod, DWORD *inout, DWORD flags);

static CreateDeviceFn g_realCreateDevice;
static GetStateFn g_realGetState;
static GetDataFn g_realGetData;
typedef HRESULT (WINAPI *AcquireFn)(void *self);
static AcquireFn g_realAcquire;

static void *g_mouse, *g_keyboard;
static int g_spoof;             /* "focus on": pretend the window is active and the mouse acquired */
static int g_mouseUsesData, g_keyUsesData, g_mouseUsesState, g_keyUsesState;

/* ---------------------------------------------------------------- injection state */
typedef struct { int dev; DWORD ofs; DWORD data; int delay; } Event;   /* dev 0 mouse, 1 keyboard */
#define MAXQ 256
static Event g_q[MAXQ];
static int g_qn;
static LONG g_dx, g_dy;              /* pending movement for the state path */
static BYTE g_buttons[8];            /* held mouse buttons (state path) */
static BYTE g_keys[256];             /* held keys (state path) */
static DWORD g_seq = 0x40000000;

static void Log(const char *fmt, ...)
{
	FILE *f;
	va_list a;
	if (!g_logPath[0] || fopen_s(&f, g_logPath, "a") || !f)
		return;
	va_start(a, fmt);
	vfprintf(f, fmt, a);
	va_end(a);
	fputc('\n', f);
	fclose(f);
}

static void Queue(int dev, DWORD ofs, DWORD data, int delay)
{
	if (g_qn < MAXQ)
	{
		g_q[g_qn].dev = dev; g_q[g_qn].ofs = ofs; g_q[g_qn].data = data; g_q[g_qn].delay = delay;
		g_qn++;
	}
}

/* state-path bookkeeping for queued button/key events, applied when they come due */
static void ApplyToState(const Event *e)
{
	if (e->dev == 0 && e->ofs >= 12 && e->ofs < 20)
		g_buttons[e->ofs - 12] = (BYTE)(e->data & 0x80);
	else if (e->dev == 1 && e->ofs < 256)
		g_keys[e->ofs] = (BYTE)(e->data & 0x80);
}

/* one poll of a device went by: count delays down; returns due events into out */
static int TakeDue(int dev, Event *out, int max)
{
	int i, n = 0, k = 0;
	for (i = 0; i < g_qn; i++)
	{
		Event e = g_q[i];
		if (e.dev == dev && e.delay <= 0 && n < max)
		{
			out[n++] = e;
			continue;
		}
		if (e.dev == dev && e.delay > 0)
			e.delay--;
		g_q[k++] = e;
	}
	g_qn = k;
	return n;
}

/* ---------------------------------------------------------------- device hooks */
static HRESULT WINAPI HookGetState(void *self, DWORD cb, void *data)
{
	int isMouse = self == g_mouse, isKey = self == g_keyboard;
	HRESULT hr = (g_spoof && (isMouse || isKey)) ? E_FAIL : g_realGetState(self, cb, data);   /* focus mode: injected only */
	Event due[32];
	int n, i, injected = 0;

	if (!isMouse && !isKey)
		return hr;
	EnterCriticalSection(&g_lock);
	if (isMouse) g_mouseUsesState = 1; else g_keyUsesState = 1;
	/* only feed this path when the game doesn't read the device through GetDeviceData */
	if ((isMouse && !g_mouseUsesData) || (isKey && !g_keyUsesData))
	{
		n = TakeDue(isMouse ? 0 : 1, due, 32);
		for (i = 0; i < n; i++)
			ApplyToState(&due[i]);
		if (FAILED(hr) && data && (g_spoof || n))
		{
			memset(data, 0, cb);
			hr = DI_OK;           /* not acquired (background): still hand over injected input */
		}
		if (SUCCEEDED(hr) && data)
		{
			if (isMouse && cb >= 16)
			{
				LONG *axes = (LONG *)data;
				BYTE *btn = (BYTE *)data + 12;
				axes[0] += g_dx; axes[1] += g_dy;
				injected = g_dx || g_dy;
				g_dx = g_dy = 0;
				for (i = 0; i < (int)(cb - 12) && i < 8; i++)
					btn[i] |= g_buttons[i];
			}
			else if (isKey && cb >= 256)
			{
				BYTE *k = (BYTE *)data;
				for (i = 0; i < 256; i++)
					k[i] |= g_keys[i];
			}
		}
	}
	LeaveCriticalSection(&g_lock);
	(void)injected;
	return hr;
}

static void RunPendingExec(void);   /* console commands queued by the pipe (below) */
static HRESULT WINAPI HookGetData(void *self, DWORD cbObj, void *rgdod, DWORD *inout, DWORD flags)
{
	DWORD cap = inout ? *inout : 0;
	HRESULT hr;
	RunPendingExec();
	if (g_spoof && (self == g_mouse || self == g_keyboard) && inout)
	{
		*inout = 0;               /* focus mode: only injected input, never the real device */
		hr = S_OK;
	}
	else
		hr = g_realGetData(self, cbObj, rgdod, inout, flags);
	int isMouse = self == g_mouse, isKey = self == g_keyboard;
	Event due[64];
	int n, i;
	DWORD got;

	if ((!isMouse && !isKey) || !rgdod || !inout || cbObj < 16 || (flags & 1 /* DIGDD_PEEK */))
		return hr;
	EnterCriticalSection(&g_lock);
	if (isMouse) g_mouseUsesData = 1; else g_keyUsesData = 1;
	{
		static DWORD calls, lastLog;
		calls++;
		if (GetTickCount() - lastLog > 2000)
		{
			Log("GetDeviceData(%s): %lu calls, last hr %08lx, real items %lu, cap %lu", isMouse ? "mouse" : "keyboard", calls, (unsigned long)hr, SUCCEEDED(hr) ? *inout : 0, cap);
			lastLog = GetTickCount();
		}
	}
	got = SUCCEEDED(hr) ? *inout : 0;
	if (got > cap) got = cap;
	/* pending movement becomes axis events */
	if (isMouse && (g_dx || g_dy))
	{
		if (g_dx) Queue(0, 0, (DWORD)g_dx, 0);
		if (g_dy) Queue(0, 4, (DWORD)g_dy, 0);
		g_dx = g_dy = 0;
	}
	n = TakeDue(isMouse ? 0 : 1, due, (int)((cap - got) < 64 ? (cap - got) : 64));
	for (i = 0; i < n; i++)
	{
		DWORD *rec = (DWORD *)((BYTE *)rgdod + (got + i) * cbObj);
		memset(rec, 0, cbObj);
		rec[0] = due[i].ofs;
		rec[1] = due[i].data;
		rec[2] = GetTickCount();
		rec[3] = g_seq++;
	}
	if (FAILED(hr) && g_spoof)
	{
		hr = S_OK;
		*inout = got;
	}
	if (n)
	{
		Log("  injected %d event(s), first ofs %lu data %lu, real hr %08lx", n, due[0].ofs, due[0].data, (unsigned long)hr);
		*inout = got + n;
		if (FAILED(hr))
			hr = DI_OK;
	}
	LeaveCriticalSection(&g_lock);
	return hr;
}

static HRESULT WINAPI HookAcquire(void *self)
{
	/* In focus mode the real device must stay unacquired: acquiring it for real
	   would hand the game the user's actual mouse (exclusive mode confines it). */
	if (g_spoof && (self == g_mouse || self == g_keyboard))
		return S_OK;
	return g_realAcquire(self);
}

static void PatchSlot(void **vtbl, int slot, void *fn, void **orig)
{
	DWORD old;
	if (vtbl[slot] == fn)
		return;
	if (!*orig)
		*orig = vtbl[slot];
	VirtualProtect(&vtbl[slot], sizeof(void *), PAGE_EXECUTE_READWRITE, &old);
	vtbl[slot] = fn;
	VirtualProtect(&vtbl[slot], sizeof(void *), old, &old);
}

static HRESULT WINAPI HookCreateDevice(void *self, REFGUID guid, void **dev, void *outer)
{
	HRESULT hr = g_realCreateDevice(self, guid, dev, outer);
	if (SUCCEEDED(hr) && dev && *dev)
	{
		void **vtbl = *(void ***)*dev;
		if (IsEqualGUID(guid, &GUID_SysMouse_)) { g_mouse = *dev; Log("mouse device %p", *dev); }
		else if (IsEqualGUID(guid, &GUID_SysKeyboard_)) { g_keyboard = *dev; Log("keyboard device %p", *dev); }
		else return hr;
		PatchSlot(vtbl, DEV_GetDeviceState, (void *)HookGetState, (void **)&g_realGetState);
		PatchSlot(vtbl, DEV_GetDeviceData, (void *)HookGetData, (void **)&g_realGetData);
		PatchSlot(vtbl, DEV_Acquire, (void *)HookAcquire, (void **)&g_realAcquire);
	}
	return hr;
}


/* ---------------------------------------------------------------- virtual focus + cursor
 * WinDrv only turns DirectInput into game input while its window has focus, and
 * positions the menu cursor from GetCursorPos. With "focus on" the game is told it
 * has focus and gets a virtual cursor ("cursor X Y", client pixels), and its own
 * SetCursorPos/ClipCursor calls are swallowed so the real mouse is never grabbed.
 */
static HWND g_hwnd;
static int g_hasCursor;
static POINT g_cursor;
typedef HWND (WINAPI *HwndFn)(void);
typedef BOOL (WINAPI *GetCursorPosFn)(LPPOINT);
typedef BOOL (WINAPI *SetCursorPosFn)(int, int);
typedef BOOL (WINAPI *ClipCursorFn)(const RECT *);
static HwndFn g_realGetFocus, g_realGetForeground;
static GetCursorPosFn g_realGetCursorPos;
static SetCursorPosFn g_realSetCursorPos;
static ClipCursorFn g_realClipCursor;

static HWND WINAPI HookGetFocus(void) { return g_spoof && g_hwnd ? g_hwnd : g_realGetFocus(); }
static HWND WINAPI HookGetForeground(void) { return g_spoof && g_hwnd ? g_hwnd : g_realGetForeground(); }

static BOOL WINAPI HookGetCursorPos(LPPOINT pt)
{
	if (g_spoof && g_hasCursor && g_hwnd && pt)
	{
		*pt = g_cursor;
		ClientToScreen(g_hwnd, pt);
		return TRUE;
	}
	return g_realGetCursorPos(pt);
}

static BOOL WINAPI HookSetCursorPos(int x, int y)
{
	if (g_spoof)
	{
		/* the game recentres the mouse for mouselook: follow it on the virtual cursor */
		POINT p = {x, y};
		if (g_hwnd && ScreenToClient(g_hwnd, &p)) { g_cursor = p; }
		return TRUE;
	}
	return g_realSetCursorPos(x, y);
}

static BOOL WINAPI HookClipCursor(const RECT *r) { return g_spoof ? TRUE : g_realClipCursor(r); }

/* point one import of module mod (e.g. WinDrv.dll) at fn */
static void PatchImport(HMODULE mod, const char *dll, const char *name, void *fn, void **orig)
{
	BYTE *base = (BYTE *)mod;
	IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
	IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
	IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
	IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress);
	for (; dir.VirtualAddress && imp->Name; imp++)
	{
		IMAGE_THUNK_DATA *names, *addrs;
		if (_stricmp((char *)(base + imp->Name), dll))
			continue;
		names = (IMAGE_THUNK_DATA *)(base + (imp->OriginalFirstThunk ? imp->OriginalFirstThunk : imp->FirstThunk));
		addrs = (IMAGE_THUNK_DATA *)(base + imp->FirstThunk);
		for (; names->u1.AddressOfData; names++, addrs++)
		{
			IMAGE_IMPORT_BY_NAME *ibn;
			DWORD old;
			if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal))
				continue;
			ibn = (IMAGE_IMPORT_BY_NAME *)(base + names->u1.AddressOfData);
			if (strcmp((char *)ibn->Name, name))
				continue;
			if (!*orig)
				*orig = (void *)addrs->u1.Function;
			VirtualProtect(&addrs->u1.Function, sizeof(void *), PAGE_READWRITE, &old);
			addrs->u1.Function = (DWORD_PTR)fn;
			VirtualProtect(&addrs->u1.Function, sizeof(void *), old, &old);
			Log("patched %s!%s", dll, name);
		}
	}
}

static void PatchWinDrv(void)
{
	HMODULE m = GetModuleHandleA("WinDrv.dll");
	static int done;
	if (!m || done)
		return;
	done = 1;
	PatchImport(m, "user32.dll", "GetFocus", (void *)HookGetFocus, (void **)&g_realGetFocus);
	PatchImport(m, "user32.dll", "GetForegroundWindow", (void *)HookGetForeground, (void **)&g_realGetForeground);
	PatchImport(m, "user32.dll", "GetCursorPos", (void *)HookGetCursorPos, (void **)&g_realGetCursorPos);
	PatchImport(m, "user32.dll", "SetCursorPos", (void *)HookSetCursorPos, (void **)&g_realSetCursorPos);
	PatchImport(m, "user32.dll", "ClipCursor", (void *)HookClipCursor, (void **)&g_realClipCursor);
}

static BOOL CALLBACK FindGameWindow(HWND h, LPARAM lp)
{
	DWORD pid;
	RECT r;
	GetWindowThreadProcessId(h, &pid);
	if (pid == GetCurrentProcessId() && IsWindowVisible(h) && GetClientRect(h, &r) && r.right > 200)
	{
		*(HWND *)lp = h;
		return FALSE;
	}
	return TRUE;
}

/* ---------------------------------------------------------------- pipe server */
/* ------------------------------------------------- console commands (exec) */
/* The game's console runs through UGameEngine::Exec. Unreal II doesn't export GEngine, so the engine
 * object is found once in the global object list (UObject::GObjObjects) by its class. Commands are
 * handed from the pipe thread to the game's main thread, which polls DirectInput (GetDeviceData)
 * hundreds of times a second: they run there, between frames, like console input. */
typedef void *(__cdecl *StaticClassFn)(void);
typedef int (__fastcall *ExecFn)(void *self, void *edx, const wchar_t *cmd, void *ar);
static void *g_engine;
static ExecFn g_exec;
static void **g_glog;
static wchar_t g_execCmd[512];
static volatile LONG g_execPending;
static int g_execResult;
static HANDLE g_execDone;
static int g_execSlot = -1;

/* a real UGameEngine has UGameEngine::Exec in its virtual table (other objects can hold the class
 * pointer at the same offset, e.g. properties that point to the class) */
/* follow "jmp rel32" stubs (an export or vtable entry can be one) to the code itself */
static void *Resolve(void *p)
{
	int hops;
	for (hops = 0; hops < 4 && p && !IsBadReadPtr(p, 5) && *(BYTE *)p == 0xE9; hops++)
		p = (BYTE *)p + 5 + *(LONG *)((BYTE *)p + 1);
	return p;
}

static int HasExec(void *o)
{
	void **vt;
	int k;
	void *want = Resolve((void *)g_exec);
	if (IsBadReadPtr(o, 4))
		return 0;
	vt = *(void ***)o;
	if (!vt || IsBadReadPtr(vt, 200 * sizeof(void *)))
		return 0;
	for (k = 0; k < 200; k++)
		if (vt[k] == (void *)g_exec || Resolve(vt[k]) == want)
		{
			g_execSlot = k;
			return 1;
		}
	return 0;
}

static int FindEngine(void)
{
	HMODULE eng = GetModuleHandleA("Engine.dll"), core = GetModuleHandleA("Core.dll");
	StaticClassFn sc;
	struct { void **Data; int Num, Max; } *objs;
	void *cls;
	int i, off;
	if (g_engine)
		return 1;
	if (!eng || !core)
		return 0;
	sc = (StaticClassFn)GetProcAddress(eng, "?StaticClass@UGameEngine@@SAPAVUClass@@XZ");
	g_exec = (ExecFn)GetProcAddress(eng, "?Exec@UGameEngine@@UAEHPBGAAVFOutputDevice@@@Z");
	g_glog = (void **)GetProcAddress(core, "?GLog@@3PAVFOutputDevice@@A");
	objs = (void *)GetProcAddress(core, "?GObjObjects@UObject@@0V?$TArray@PAVUObject@@@@A");
	if (!sc || !g_exec || !g_glog || !objs)
	{
		Log("exec: engine exports not found (StaticClass %p Exec %p GLog %p GObjObjects %p)", (void *)sc, (void *)g_exec, (void *)g_glog, (void *)objs);
		return 0;
	}
	cls = sc();
	/* UObject keeps its class a few pointers in (36 in UE2); try nearby offsets, log the one that matches */
	for (off = 36; off <= 48 && !g_engine; off += 4)
		for (i = 0; i < objs->Num; i++)
		{
			void *o = objs->Data[i];
			if (o && *(void **)((char *)o + off) == cls && HasExec(o))
			{
				g_engine = o;
				Log("exec: game engine object %p (class at offset %d, %d objects)", o, off, objs->Num);
				break;
			}
		}
	if (!g_engine)
	{
		Log("exec: no UGameEngine object found among %d objects; Exec export %p -> %p", objs->Num, (void *)g_exec, Resolve((void *)g_exec));
		for (i = 0; i < objs->Num; i++)
		{
			void *o = objs->Data[i];
			if (o && *(void **)((char *)o + 36) == cls)
				Log("exec: candidate %p (index %d), vtable %p, flags %08lx, outer %p", o, i, *(void **)o,
				    *(DWORD *)((char *)o + 28), *(void **)((char *)o + 24));
		}
	}
	else
		Log("exec: Exec is virtual slot %d", g_execSlot);
	return g_engine != NULL;
}

/* called on the game's main thread */
static void RunPendingExec(void)
{
	if (!g_execPending)
		return;
	g_execResult = FindEngine() ? g_exec(g_engine, NULL, g_execCmd, *g_glog) : -1;
	Log("exec: %ls -> %d", g_execCmd, g_execResult);
	InterlockedExchange(&g_execPending, 0);
	SetEvent(g_execDone);
}

/* called on the pipe thread: hand the command over and wait for it to run */
static void ExecCommand(const char *text, char *reply, int size)
{
	if (!g_execDone)
		g_execDone = CreateEventA(NULL, FALSE, FALSE, NULL);
	if (g_execPending)
	{
		strcpy_s(reply, size, "error: busy");
		return;
	}
	MultiByteToWideChar(CP_ACP, 0, text, -1, g_execCmd, (int)(sizeof(g_execCmd) / sizeof(g_execCmd[0])));
	ResetEvent(g_execDone);
	InterlockedExchange(&g_execPending, 1);
	if (WaitForSingleObject(g_execDone, 3000) != WAIT_OBJECT_0)
	{
		strcpy_s(reply, size, "error: the game didn't run it within 3 s (not polling input: loading or paused?)");
		return;
	}
	if (g_execResult < 0)
		strcpy_s(reply, size, "error: game engine not found (see U2Input.log)");
	else
		sprintf_s(reply, size, "ok %d", g_execResult);
}

static void Command(char *line, char *reply, int size)
{
	char cmd[16] = {0};
	long a = 0, b = 0;
	char word[16] = {0};
	int n = sscanf_s(line, "%15s %ld %ld", cmd, (unsigned)sizeof(cmd), &a, &b);

	if (n >= 1 && !strcmp(cmd, "nativeexec"))
	{
		const char *rest = line + 10;
		while (*rest == ' ') rest++;
		ExecCommand(rest, reply, size);
		return;
	}
	EnterCriticalSection(&g_lock);
	strcpy_s(reply, size, "ok");
	if (n >= 1 && !strcmp(cmd, "ping"))
		sprintf_s(reply, size, "pong mouse=%s keyboard=%s", g_mouse ? (g_mouseUsesData ? "data" : g_mouseUsesState ? "state" : "idle") : "none",
		          g_keyboard ? (g_keyUsesData ? "data" : g_keyUsesState ? "state" : "idle") : "none");
	else if (n >= 1 && !strcmp(cmd, "focus"))
	{
		char w[8] = {0};
		sscanf_s(line, "%*s %7s", w, (unsigned)sizeof(w));
		PatchWinDrv();
		if (!g_hwnd) EnumWindows(FindGameWindow, (LPARAM)&g_hwnd);
		g_spoof = strcmp(w, "off") != 0;
		if (g_spoof)
		{
			typedef HRESULT (WINAPI *UnacqFn)(void *);
			if (g_mouse) ((UnacqFn)(*(void ***)g_mouse)[8])(g_mouse);        /* Unacquire */
			if (g_keyboard) ((UnacqFn)(*(void ***)g_keyboard)[8])(g_keyboard);
		}
		if (g_spoof && g_hwnd)
		{
			PostMessageA(g_hwnd, WM_ACTIVATEAPP, TRUE, 0);
			PostMessageA(g_hwnd, WM_ACTIVATE, WA_ACTIVE, 0);
			PostMessageA(g_hwnd, WM_SETFOCUS, 0, 0);
		}
		sprintf_s(reply, size, "ok focus %s, window %p", g_spoof ? "on" : "off", (void *)g_hwnd);
	}
	else if (n == 3 && !strcmp(cmd, "cursor"))
	{
		g_cursor.x = a; g_cursor.y = b; g_hasCursor = 1;
		if (!g_hwnd) EnumWindows(FindGameWindow, (LPARAM)&g_hwnd);
		if (g_hwnd) PostMessageA(g_hwnd, WM_MOUSEMOVE, 0, MAKELPARAM(a, b));   /* makes WinDrv re-read GetCursorPos */
	}
	else if (n >= 2 && (!strcmp(cmd, "vkey") || !strcmp(cmd, "vdown") || !strcmp(cmd, "vup")))
	{
		/* keyboard: Unreal II reads it from window messages, not DirectInput */
		UINT sc = MapVirtualKeyA((UINT)a, 0 /* MAPVK_VK_TO_VSC */);
		if (!g_hwnd) EnumWindows(FindGameWindow, (LPARAM)&g_hwnd);
		if (cmd[1] != 'u') PostMessageA(g_hwnd, WM_KEYDOWN, (WPARAM)a, 1 | (sc << 16));
		if (cmd[1] != 'd') PostMessageA(g_hwnd, WM_KEYUP, (WPARAM)a, 1 | (sc << 16) | (1u << 30) | (1u << 31));
	}
	else if (n == 2 && !strcmp(cmd, "char") && a > 0 && a < 0x10000)
	{
		if (!g_hwnd) EnumWindows(FindGameWindow, (LPARAM)&g_hwnd);
		PostMessageW(g_hwnd, WM_CHAR, (WPARAM)a, 1);
	}
	else if (n == 3 && !strcmp(cmd, "move"))
		{ g_dx += a; g_dy += b; }
	else if (n == 2 && (!strcmp(cmd, "down") || !strcmp(cmd, "up")) && a >= 0 && a < 8)
		Queue(0, 12 + a, cmd[0] == 'd' ? 0x80 : 0, 0);
	else if (n == 2 && !strcmp(cmd, "click") && a >= 0 && a < 8)
		{ Queue(0, 12 + a, 0x80, 0); Queue(0, 12 + a, 0, 4); }
	else if (n == 2 && !strcmp(cmd, "tap") && a > 0 && a < 256)
		{ Queue(1, a, 0x80, 0); Queue(1, a, 0, 4); }
	else if (!strcmp(cmd, "key") && sscanf_s(line, "%15s %ld %15s", cmd, (unsigned)sizeof(cmd), &a, word, (unsigned)sizeof(word)) == 3 && a > 0 && a < 256)
		Queue(1, a, !strcmp(word, "down") ? 0x80 : 0, 0);
	else
		sprintf_s(reply, size, "error: unknown command");
	LeaveCriticalSection(&g_lock);
}

static DWORD WINAPI PipeThread(LPVOID p)
{
	char name[64], buf[512], line[256], reply[128];
	int len = 0;
	(void)p;
	sprintf_s(name, sizeof(name), "\\\\.\\pipe\\U2Input-%lu", GetCurrentProcessId());
	for (;;)
	{
		HANDLE h = CreateNamedPipeA(name, PIPE_ACCESS_DUPLEX, PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
		                            1, 4096, 4096, 0, NULL);
		DWORD got, wrote;
		if (h == INVALID_HANDLE_VALUE)
			return 1;
		if (!ConnectNamedPipe(h, NULL) && GetLastError() != ERROR_PIPE_CONNECTED)
		{
			CloseHandle(h);
			continue;
		}
		len = 0;
		while (ReadFile(h, buf, sizeof(buf), &got, NULL) && got)
		{
			DWORD i;
			for (i = 0; i < got; i++)
			{
				if (buf[i] == '\n' || len >= (int)sizeof(line) - 1)
				{
					line[len] = 0;
					if (len && line[len - 1] == '\r') line[len - 1] = 0;
					if (line[0])
					{
						Command(line, reply, sizeof(reply));
						strcat_s(reply, sizeof(reply), "\n");
						WriteFile(h, reply, (DWORD)strlen(reply), &wrote, NULL);
					}
					len = 0;
				}
				else
					line[len++] = buf[i];
			}
		}
		DisconnectNamedPipe(h);
		CloseHandle(h);
	}
}

/* ---------------------------------------------------------------- exports */
static BOOL LoadReal(void)
{
	char path[MAX_PATH];
	if (g_real)
		return TRUE;
	GetSystemDirectoryA(path, MAX_PATH);          /* SysWOW64 for this 32-bit process */
	strcat_s(path, MAX_PATH, "\\dinput8.dll");
	g_real = LoadLibraryA(path);
	g_realCreate = g_real ? (DI8CreateFn)GetProcAddress(g_real, "DirectInput8Create") : NULL;
	Log("real dinput8: %s (%s)", path, g_realCreate ? "ok" : "FAILED");
	return g_realCreate != NULL;
}

HRESULT WINAPI DirectInput8Create(HINSTANCE inst, DWORD ver, REFIID iid, LPVOID *out, void *outer)
{
	HRESULT hr;
	if (!LoadReal())
		return E_FAIL;
	hr = g_realCreate(inst, ver, iid, out, outer);
	if (SUCCEEDED(hr) && out && *out)
	{
		void **vtbl = *(void ***)*out;
		PatchSlot(vtbl, DI_CreateDevice, (void *)HookCreateDevice, (void **)&g_realCreateDevice);
		PatchWinDrv();
		Log("DirectInput8Create ok, pipe \\\\.\\pipe\\U2Input-%lu", GetCurrentProcessId());
	}
	return hr;
}

HRESULT WINAPI DllCanUnloadNow(void) { return S_FALSE; }

HRESULT WINAPI DllGetClassObject(REFCLSID c, REFIID i, LPVOID *o)
{
	typedef HRESULT (WINAPI *Fn)(REFCLSID, REFIID, LPVOID *);
	Fn f = LoadReal() ? (Fn)GetProcAddress(g_real, "DllGetClassObject") : NULL;
	return f ? f(c, i, o) : E_FAIL;
}

HRESULT WINAPI DllRegisterServer(void) { return E_NOTIMPL; }
HRESULT WINAPI DllUnregisterServer(void) { return E_NOTIMPL; }

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID r)
{
	(void)r;
	if (reason == DLL_PROCESS_ATTACH)
	{
		char *slash;
		DisableThreadLibraryCalls(inst);
		InitializeCriticalSection(&g_lock);
		GetModuleFileNameA(inst, g_logPath, MAX_PATH);
		slash = strrchr(g_logPath, '\\');
		if (slash) strcpy_s(slash + 1, MAX_PATH - (slash + 1 - g_logPath), "U2Input.log");
		DeleteFileA(g_logPath);
		Log("U2Input loaded into pid %lu", GetCurrentProcessId());
		CreateThread(NULL, 0, PipeThread, NULL, 0, NULL);
	}
	return TRUE;
}
