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
 *   !ping           -> pong
 *   !answer yes|no  how to answer Yes/No message boxes
 *   !quit           terminate the editor (nothing is saved)
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
	CapLine(L"unknown bridge command (!ping, !answer yes|no, !quit)");
	return 0;
}

static void RunRequest(void)
{
	/* the pipe thread may have given up on this request already */
	if (InterlockedCompareExchange(&g_state, 2, 1) != 1)
		return;
	PatchMessageBoxes();
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
		t = CreateThread(NULL, 0, Main, NULL, 0, NULL);
		if (t) CloseHandle(t);
	}
	return TRUE;
}
