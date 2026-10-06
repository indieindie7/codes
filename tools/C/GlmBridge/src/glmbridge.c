/* GlmBridge - drive Unreal II's Golem Studio (GlmEd.exe + GlmLib.dll) from a pipe.
 *
 * Loaded into GlmEd.exe (bin\u2edinject.exe from U2EdBridge does the injection). Listens on
 * \\.\pipe\GlmBridge-<pid>; each line is a Golem command, run on the editor's main thread
 * through GlmLib's own command layer and answered with everything Golem logged meanwhile
 * plus "<<<GLM rc=N>>>".
 *
 * How Golem takes commands (read from GlmLib.dll with Ghidra, 2026-10-05):
 *   - every editor window has a GLM::WWindow object in GWL_USERDATA (WWindow::StaticWindowGetObject);
 *     WWindow is a GLM::RObject.
 *   - GLM::RObject::ExecuteCommand(CDatString &result, const char *line) splits the line into words
 *     (quotes, ` = quote), finds the first word with RClass::GetCommandNamed up the class chain,
 *     checks the parameter count and calls it; menus run their items through the same table.
 *   - GLM::LOG_AddTarget(ILogTarget *) registers a log sink: vtable slot 0 is called on add, slot 2
 *     gets every formatted log line (LOG_Logf, LOG_DevLogf ...).
 *
 * Protocol: "<command words>" runs on the main window's object; "@<hwnd hex> <command>" runs on
 * that window's object. Bridge commands start with '!': !ping, !quit, !windows (every window of the
 * process with its object class), !commands [hwnd] (the command table of that object's class chain),
 * !answer yes|no (how Yes/No message boxes are answered; default No), !log (the last log lines).
 *
 * Build: zig cc -target x86-windows-gnu -O2 -shared -o bin/GlmBridge.dll src/glmbridge.c -luser32 -lkernel32
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define PIPE_NAME L"\\\\.\\pipe\\GlmBridge-%lu"
#define WM_GLM_EXEC (WM_APP + 0x56)
#define TC __attribute__((thiscall))

typedef struct { void *s; unsigned len, cap; unsigned flag; } CDatString;     /* 16 bytes, as ExecuteCommandf builds it */
typedef int (TC *ExecuteCommandFn)(void *self, CDatString *out, const char *line);
typedef void *(TC *GetCommandNamedFn)(void *rclass, const char *name);
typedef unsigned long (TC *GetCommandCountFn)(void *rclass);
typedef void *(TC *GetCommandIndexedFn)(void *rclass, unsigned long i);
typedef void *(TC *GetSuperFn)(void *rclass);
typedef char *(TC *GetNameFn)(void *rclass);
typedef void *(__cdecl *StaticWindowGetObjectFn)(void *hwnd);
typedef unsigned long (__cdecl *LogAddTargetFn)(void *target);
typedef void *(TC *GetClassFn)(void *self);

static ExecuteCommandFn pExecuteCommand;
static GetCommandNamedFn pGetCommandNamed;
static GetCommandCountFn pGetCommandCount;
static GetCommandIndexedFn pGetCommandIndexed;
static GetSuperFn pGetSuper;
static GetNameFn pGetName;
static StaticWindowGetObjectFn pWindowGetObject;
static LogAddTargetFn pLogAddTarget;
typedef void *(__cdecl *GetWorkspaceFn)(void);
typedef const char *(TC *ItemGetNameFn)(void *item);
typedef int (__cdecl *WindowCommandfFn)(void *self, const char *fmt, ...);   /* virtual, varargs: this on the stack */
static WindowCommandfFn pWindowCommandf;
static GetWorkspaceFn pGetWorkspace;
static ItemGetNameFn pItemGetName;
static HMODULE g_glm;
static BYTE *g_glmLo, *g_glmHi;

/* --- our log --- */
static void BLog(const char *fmt, ...)
{
	static HANDLE f = INVALID_HANDLE_VALUE;
	char buf[2048];
	DWORD w;
	va_list ap;
	int n;
	if (f == INVALID_HANDLE_VALUE)
	{
		wchar_t path[MAX_PATH];
		GetModuleFileNameW(NULL, path, MAX_PATH);
		lstrcatW(path, L".glmbridge.log");
		f = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, 0, NULL);
	}
	va_start(ap, fmt);
	n = wvsprintfA(buf, fmt, ap);
	va_end(ap);
	buf[n++] = '\r'; buf[n++] = '\n';
	if (f != INVALID_HANDLE_VALUE) WriteFile(f, buf, n, &w, NULL);
}

/* --- capture of Golem's log lines while a command runs --- */
static char g_cap[1 << 16];
static volatile LONG g_capLen, g_capturing;
static char g_recent[64][256];
static int g_recentN;
static CRITICAL_SECTION g_capLock;

static void CapLine(const char *s)
{
	int n = lstrlenA(s);
	EnterCriticalSection(&g_capLock);
	lstrcpynA(g_recent[g_recentN++ % 64], s, 256);
	if (g_capturing && (size_t)g_capLen + n + 1 < sizeof(g_cap))
	{
		memcpy(g_cap + g_capLen, s, n);
		g_cap[g_capLen + n] = '\n';
		g_capLen += n + 1;
	}
	LeaveCriticalSection(&g_capLock);
}

/* ILogTarget: a vtable of thiscall methods; slot 0 runs on registration, slot 2 receives lines */
static void TC TargetNop(void *self) { (void)self; }
static void TC TargetWrite(void *self, const char *line) { (void)self; if (line) CapLine(line); }
static void *g_logVtbl[8] = { (void *)TargetNop, (void *)TargetNop, (void *)TargetWrite, (void *)TargetNop,
                              (void *)TargetNop, (void *)TargetNop, (void *)TargetNop, (void *)TargetNop };
static void *g_logObj[1];

/* --- message boxes: answered without a hand --- */
static volatile LONG g_answerYes;
typedef int (WINAPI *MessageBoxWFn)(HWND, LPCWSTR, LPCWSTR, UINT);
typedef int (WINAPI *MessageBoxAFn)(HWND, LPCSTR, LPCSTR, UINT);
static MessageBoxWFn g_realMsgW;
static MessageBoxAFn g_realMsgA;

static int AutoAnswer(UINT type)
{
	switch (type & 0xF)
	{
	case MB_OK: case MB_OKCANCEL: return IDOK;
	case MB_YESNO: case MB_YESNOCANCEL: return g_answerYes ? IDYES : IDNO;
	case MB_RETRYCANCEL: return IDCANCEL;
	case MB_ABORTRETRYIGNORE: return IDIGNORE;
	}
	return IDOK;
}
static int WINAPI HookMessageBoxW(HWND h, LPCWSTR text, LPCWSTR cap, UINT type)
{
	char line[1024];
	int ans = AutoAnswer(type);
	(void)h;
	wsprintfA(line, "[dialog -> %s] %ls: %ls", ans == IDYES ? "Yes" : ans == IDNO ? "No" : "OK", cap ? cap : L"", text ? text : L"");
	CapLine(line);
	return ans;
}
static int WINAPI HookMessageBoxA(HWND h, LPCSTR text, LPCSTR cap, UINT type)
{
	char line[1024];
	int ans = AutoAnswer(type);
	(void)h;
	wsprintfA(line, "[dialog -> %s] %s: %s", ans == IDYES ? "Yes" : ans == IDNO ? "No" : "OK", cap ? cap : "", text ? text : "");
	CapLine(line);
	return ans;
}
static void PatchImports(HMODULE mod, void *realW, void *realA)
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
		void **slot;
		if (lstrcmpiA((char *)(base + imp->Name), "user32.dll")) continue;
		for (slot = (void **)(base + imp->FirstThunk); *slot; slot++)
		{
			void *want = *slot == realW ? (void *)HookMessageBoxW : *slot == realA ? (void *)HookMessageBoxA : NULL;
			DWORD old;
			if (!want) continue;
			VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old);
			*slot = want;
			VirtualProtect(slot, sizeof(void *), old, &old);
		}
	}
}
static void PatchMessageBoxes(void)
{
	HMODULE u32 = GetModuleHandleW(L"user32.dll");
	g_realMsgW = (MessageBoxWFn)GetProcAddress(u32, "MessageBoxW");
	g_realMsgA = (MessageBoxAFn)GetProcAddress(u32, "MessageBoxA");
	PatchImports(GetModuleHandleW(NULL), (void *)g_realMsgW, (void *)g_realMsgA);
	if (g_glm) PatchImports(g_glm, (void *)g_realMsgW, (void *)g_realMsgA);
}

/* --- Golem objects --- */
static int InGlm(void *p) { return (BYTE *)p >= g_glmLo && (BYTE *)p < g_glmHi; }

/* the GLM object behind a window, or NULL when the window isn't one of Golem's */
static void *ObjectOf(HWND h)
{
	void *obj, *vt;
	char cls[64];
	if (!h || !IsWindow(h)) return NULL;
	/* Golem keeps a WWindow in GWL_USERDATA of its own windows and of the standard controls it wraps;
	   anything else there is checked for looking like a GLM object before it is touched */
	(void)cls;
	obj = pWindowGetObject(h);
	if (!obj || IsBadReadPtr(obj, 8)) return NULL;
	vt = *(void **)obj;
	if (!InGlm(vt) || IsBadReadPtr(vt, 16) || !InGlm(((void **)vt)[3])) return NULL;
	return obj;
}
static void *ClassOf(void *obj)
{
	GetClassFn getClass = (GetClassFn)(*(void ***)obj)[3];   /* RObject vtable slot 3 = GetClass */
	void *c;
	if (!InGlm((void *)getClass)) return NULL;
	c = getClass(obj);
	if (!c || IsBadReadPtr(c, 0x40)) return NULL;
	return c;
}
static const char *ClassName(void *rclass)
{
	char *n = rclass ? pGetName(rclass) : NULL;
	return n && !IsBadReadPtr(n, 1) ? n : "?";
}

/* --- requests --- */
static HWND g_main;
static WNDPROC g_oldProc;
static HANDLE g_done;
static volatile LONG g_state;
static const char *g_req;
static int g_rc;

static HWND g_enumBest;
static BOOL CALLBACK FindMain(HWND h, LPARAM l)
{
	DWORD pid;
	RECT r, b;
	(void)l;
	GetWindowThreadProcessId(h, &pid);
	if (pid != GetCurrentProcessId() || !IsWindowVisible(h) || GetWindow(h, GW_OWNER)) return TRUE;
	GetWindowRect(h, &r);
	if (!g_enumBest) { g_enumBest = h; return TRUE; }
	GetWindowRect(g_enumBest, &b);
	if ((r.right - r.left) * (r.bottom - r.top) > (b.right - b.left) * (b.bottom - b.top)) g_enumBest = h;
	return TRUE;
}
static HWND BigWindow(void)
{
	RECT r;
	g_enumBest = NULL;
	EnumWindows(FindMain, 0);
	if (!g_enumBest) return NULL;
	GetWindowRect(g_enumBest, &r);
	return (r.right - r.left >= 500 && r.bottom - r.top >= 300) ? g_enumBest : NULL;
}

static void ListWindow(HWND h, int depth)
{
	char cls[64], title[128], line[512];
	void *obj = ObjectOf(h);
	cls[0] = title[0] = 0;
	GetClassNameA(h, cls, sizeof(cls));
	if (GetWindowThreadProcessId(h, NULL) == GetCurrentThreadId())
		GetWindowTextA(h, title, sizeof(title));   /* another thread's window could deadlock us */
	title[60] = 0;
	wsprintfA(line, "%s%08X %s '%s'%s%s", depth ? "  " : "", (unsigned)(ULONG_PTR)h, cls, title,
	          obj ? "  object " : "", obj ? ClassName(ClassOf(obj)) : "");   /* (wsprintf has no '*' width) */
	CapLine(line);
}
static BOOL CALLBACK ListChild(HWND h, LPARAM depth) { ListWindow(h, (int)depth); return TRUE; }
static BOOL CALLBACK ListTop(HWND h, LPARAM l)
{
	DWORD pid;
	(void)l;
	GetWindowThreadProcessId(h, &pid);
	if (pid != GetCurrentProcessId()) return TRUE;
	ListWindow(h, 0);
	EnumChildWindows(h, ListChild, 1);
	return TRUE;
}

static void ListCommands(void *obj)
{
	void *c;
	char line[512];
	for (c = ClassOf(obj); c; c = pGetSuper(c))
	{
		unsigned long i, n = pGetCommandCount(c);
		wsprintfA(line, "class %s: %lu commands", ClassName(c), n);
		CapLine(line);
		for (i = 0; i < n; i++)
		{
			BYTE *cmd = (BYTE *)pGetCommandIndexed(c, i);     /* SRefCmd: +0 name, +0x24 parameter count */
			const char *name = cmd && !IsBadReadPtr(cmd, 0x30) ? *(const char **)cmd : NULL;
			wsprintfA(line, "  %s (%d params)", name ? name : "?", cmd ? *(int *)(cmd + 0x24) : -1);
			CapLine(line);
		}
	}
}

/* every GLM class with its command table: GlmLib exports one static "sClass" pointer per class
   (?sClass@<Class>@GLM@@...), so the export table is a complete class list */
static void ListClasses(int onlyWithCommands)
{
	BYTE *base = (BYTE *)g_glm;
	IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
	IMAGE_DATA_DIRECTORY *dir = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
	IMAGE_EXPORT_DIRECTORY *ex = (IMAGE_EXPORT_DIRECTORY *)(base + dir->VirtualAddress);
	DWORD *names = (DWORD *)(base + ex->AddressOfNames), *funcs = (DWORD *)(base + ex->AddressOfFunctions);
	WORD *ords = (WORD *)(base + ex->AddressOfNameOrdinals);
	DWORD i;
	int classes = 0, withCmds = 0;
	char line[512];
	for (i = 0; i < ex->NumberOfNames; i++)
	{
		const char *nm = (const char *)(base + names[i]);
		void **slot;
		void *c;
		unsigned long k, n;
		if (strncmp(nm, "?sClass@", 8)) continue;
		slot = (void **)(base + funcs[ords[i]]);
		if (IsBadReadPtr(slot, 4)) continue;
		c = *slot;
		classes++;
		if (!c || IsBadReadPtr(c, 0x40)) { if (!onlyWithCommands) { wsprintfA(line, "%s: class not created yet", nm + 8); CapLine(line); } continue; }
		n = pGetCommandCount(c);
		if (onlyWithCommands && !n) continue;
		withCmds += n > 0;
		wsprintfA(line, "class %s (%s): %lu commands", ClassName(c), pGetSuper(c) ? ClassName(pGetSuper(c)) : "-", n);
		CapLine(line);
		for (k = 0; k < n; k++)
		{
			BYTE *cmd = (BYTE *)pGetCommandIndexed(c, k);
			const char *name = cmd && !IsBadReadPtr(cmd, 0x30) ? *(const char **)cmd : NULL;
			wsprintfA(line, "  %s (%d params)", name && !IsBadReadPtr(name, 1) ? name : "?", cmd ? *(int *)(cmd + 0x24) : -1);
			CapLine(line);
		}
	}
	wsprintfA(line, "%d classes exported, %d with commands", classes, withCmds);
	CapLine(line);
}

/* --- the workspace tree (RGemTreeItem, layout read from GemItemFindChildNamed / GemItemSetParent):
   +0x24 = head of the child list; list nodes are {next, prev, item}, the head's item is NULL --- */
static void *FirstChild(void *item, void **node)
{
	void **head = (void **)((BYTE *)item + 0x24);
	void **n = (void **)head[0];
	if (!n || IsBadReadPtr(n, 12) || !n[2]) return NULL;
	*node = n;
	return n[2];
}
static void *NextChild(void **node)
{
	void **n = (void **)((void **)*node)[0];
	if (!n || IsBadReadPtr(n, 12) || !n[2]) return NULL;
	*node = n;
	return n[2];
}
static const char *ItemName(void *item)
{
	const char *n = item && !IsBadReadPtr(item, 0x40) ? pItemGetName(item) : NULL;
	return n && !IsBadReadPtr(n, 1) ? n : "?";
}
static void PrintTree(void *item, int depth, int maxDepth, char *path)
{
	void *node, *child;
	char line[1024];
	size_t len = lstrlenA(path);
	wsprintfA(line, "%s  [%s]", path[0] ? path : "/", ClassName(ClassOf(item)));
	CapLine(line);
	if (depth >= maxDepth) return;
	for (child = FirstChild(item, &node); child; child = NextChild(&node))
	{
		if (len + lstrlenA(ItemName(child)) + 2 > 900) continue;
		lstrcatA(path, "/");
		lstrcatA(path, ItemName(child));
		PrintTree(child, depth + 1, maxDepth, path);
		path[len] = 0;
	}
}
/* "/Folder/File.gem/Object" -> the item; "/" = the workspace */
static void *ItemAt(const char *path, const char **rest)
{
	void *item = pGetWorkspace ? pGetWorkspace() : NULL;
	const char *p = path;
	if (!item) return NULL;
	while (*p == '/')
	{
		const char *e;
		char name[256];
		void *node, *child, *hit = NULL;
		size_t n;
		p++;
		for (e = p; *e && *e != '/' && *e != ' '; e++) ;
		n = e - p;
		if (!n) break;
		if (n > 255) n = 255;
		memcpy(name, p, n); name[n] = 0;
		for (child = FirstChild(item, &node); child; child = NextChild(&node))
			if (!lstrcmpiA(ItemName(child), name)) { hit = child; break; }
		if (!hit) { *rest = NULL; return NULL; }
		item = hit;
		p = e;
	}
	while (*p == ' ') p++;
	*rest = p;
	return item;
}

static int RunBang(const char *req)
{
	if (!_strnicmp(req, "!tree", 5))
	{
		char path[1024] = "";
		void *ws = pGetWorkspace ? pGetWorkspace() : NULL;
		int depth = req[5] == ' ' ? atoi(req + 6) : 3;
		if (!ws) { CapLine("bridge: no workspace"); return 0; }
		PrintTree(ws, 0, depth > 0 ? depth : 3, path);
		return 1;
	}
	if (!lstrcmpiA(req, "!classes")) { ListClasses(1); return 1; }
	if (!lstrcmpiA(req, "!classes all")) { ListClasses(0); return 1; }
	if (!lstrcmpiA(req, "!ping")) { CapLine("pong"); return 1; }
	if (!lstrcmpiA(req, "!quit"))
	{
		/* "Are you sure you want to exit?" must get Yes, or Golem stays and its settings never save */
		InterlockedExchange(&g_answerYes, 1);
		PostMessageW(g_main, WM_CLOSE, 0, 0);
		CapLine("closing");
		return 1;
	}
	if (!lstrcmpiA(req, "!answer yes")) { InterlockedExchange(&g_answerYes, 1); CapLine("yes"); return 1; }
	if (!lstrcmpiA(req, "!answer no")) { InterlockedExchange(&g_answerYes, 0); CapLine("no"); return 1; }
	if (!lstrcmpiA(req, "!windows")) { EnumWindows(ListTop, 0); return 1; }
	if (!lstrcmpiA(req, "!log"))
	{
		int i, from = g_recentN > 64 ? g_recentN - 64 : 0;
		for (i = from; i < g_recentN; i++) CapLine(g_recent[i % 64]);
		return 1;
	}
	if (!_strnicmp(req, "!commands", 9))
	{
		HWND h = g_main;
		void *obj;
		if (req[9] == ' ') h = (HWND)(ULONG_PTR)strtoul(req + 10, NULL, 16);
		obj = ObjectOf(h);
		if (!obj) { CapLine("bridge: that window has no Golem object"); return 0; }
		ListCommands(obj);
		return 1;
	}
	CapLine("bridge: unknown ! command");
	return 0;
}

static void RunRequest(void)
{
	const char *req = g_req;
	HWND target = g_main;
	void *obj;
	CDatString out = { 0, 0, 0, 1 };
	InterlockedExchange(&g_capLen, 0);
	InterlockedExchange(&g_capturing, 1);
	if (req[0] == '!')
		g_rc = RunBang(req);
	else
	{
		obj = NULL;
		if (!_strnicmp(req, "win:", 4))
		{
			/* a WINDOW command: what the menus run (WClass command handlers up the window's class chain) */
			req += 4;
			while (*req == ' ') req++;
			obj = ObjectOf(target);
			if (!obj) { CapLine("bridge: no Golem object behind the main window"); g_rc = 0; goto done; }
			g_rc = pWindowCommandf(obj, "%s", req);
			goto done;
		}
		if (req[0] == '/')
		{
			const char *rest;
			obj = ItemAt(req, &rest);
			if (!obj) { CapLine("bridge: no such tree item"); g_rc = 0; goto done; }
			if (!_strnicmp(rest, "!commands", 9)) { ListCommands(obj); g_rc = 1; goto done; }
			req = rest;
		}
		else
		{
			if (req[0] == '@')
			{
				target = (HWND)(ULONG_PTR)strtoul(req + 1, (char **)&req, 16);
				while (*req == ' ') req++;
			}
			obj = ObjectOf(target);
		}
		if (!obj) { CapLine("bridge: no Golem object behind the target window"); g_rc = 0; }
		else
		{
			g_rc = pExecuteCommand(obj, &out, req);
			if (out.s && !IsBadReadPtr(out.s, 1) && *(char *)out.s) CapLine((const char *)out.s);
			/* out.s is a small CRT buffer owned by the string; left to the process (no exported destructor) */
		}
	}
done:
	InterlockedExchange(&g_capturing, 0);
	InterlockedExchange(&g_state, 0);
	SetEvent(g_done);
}

static LRESULT CALLBACK SubProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
	if (m == WM_GLM_EXEC) { RunRequest(); return 0; }
	return CallWindowProcW(g_oldProc, h, m, w, l);
}

static int Attach(void)
{
	HWND h;
	char cls[128] = "", title[128] = "";
	if (g_main && IsWindow(g_main)) return 1;
	h = BigWindow();
	if (!h) return 0;
	g_main = h;
	g_oldProc = (WNDPROC)SetWindowLongPtrW(h, GWLP_WNDPROC, (LONG_PTR)SubProc);
	GetClassNameA(h, cls, sizeof(cls));
	GetWindowTextA(h, title, sizeof(title));
	BLog("attached to window %p class '%s' title '%s', object %s", (void *)h, cls, title,
	     ObjectOf(h) ? ClassName(ClassOf(ObjectOf(h))) : "(none)");
	return 1;
}

static void Fault(const char *msg) { InterlockedExchange(&g_capLen, 0); CapLine(msg); g_rc = -1; }

static void Dispatch(void)
{
	int waited;
	if (!Attach()) { Fault("bridge: no Golem main window"); return; }
	ResetEvent(g_done);
	InterlockedExchange(&g_state, 1);
	PostMessageW(g_main, WM_GLM_EXEC, 0, 0);
	for (waited = 0; ; waited += 250)
	{
		if (WaitForSingleObject(g_done, 250) == WAIT_OBJECT_0) return;
		if (waited >= 15000 && InterlockedCompareExchange(&g_state, 0, 1) == 1)
		{
			g_main = NULL;
			Fault("bridge: Golem did not pick up the command (busy, or a modal window is open)");
			return;
		}
	}
}

static int WriteAll(HANDLE p, const char *s, DWORD n)
{
	DWORD w;
	while (n) { if (!WriteFile(p, s, n, &w, NULL)) return 0; s += w; n -= w; }
	return 1;
}
static void Serve(HANDLE p)
{
	static char line[65536];
	DWORD len = 0, got;
	for (;;)
	{
		char *nl;
		if (!ReadFile(p, line + len, sizeof(line) - 1 - len, &got, NULL) || !got) return;
		len += got;
		while ((nl = (char *)memchr(line, '\n', len)) != NULL)
		{
			static char req[65536];
			char tail[64];
			int n = (int)(nl - line);
			if (n && line[n - 1] == '\r') n--;
			memcpy(req, line, n); req[n] = 0;
			memmove(line, nl + 1, len - (nl + 1 - line));
			len -= (DWORD)(nl + 1 - line);
			if (!n) continue;
			g_req = req;
			Dispatch();
			if (g_capLen && !WriteAll(p, g_cap, g_capLen)) return;
			wsprintfA(tail, "<<<GLM rc=%d>>>\n", g_rc);
			if (!WriteAll(p, tail, lstrlenA(tail))) return;
		}
		if (len >= sizeof(line) - 1) len = 0;
	}
}

static DWORD WINAPI Main(LPVOID unused)
{
	wchar_t pipeName[64];
	int i;
	(void)unused;
	InitializeCriticalSection(&g_capLock);
	BLog("loaded into process %lu", GetCurrentProcessId());
	for (i = 0; i < 3000; i++, Sleep(100))
	{
		if (!g_glm) g_glm = GetModuleHandleW(L"GlmLib.dll");
		if (g_glm && BigWindow()) break;
	}
	if (!g_glm) { BLog("GlmLib.dll never loaded"); return 1; }
	{
		IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)g_glm;
		IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)((BYTE *)g_glm + dos->e_lfanew);
		g_glmLo = (BYTE *)g_glm;
		g_glmHi = g_glmLo + nt->OptionalHeader.SizeOfImage;
	}
	pExecuteCommand = (ExecuteCommandFn)GetProcAddress(g_glm, "?ExecuteCommand@RObject@GLM@@QAE_NAAVCDatString@2@PBD@Z");
	pGetCommandNamed = (GetCommandNamedFn)GetProcAddress(g_glm, "?GetCommandNamed@RClass@GLM@@QAEPAUSRefCmd@12@PBD@Z");
	pGetCommandCount = (GetCommandCountFn)GetProcAddress(g_glm, "?GetCommandCount@RClass@GLM@@QAEKXZ");
	pGetCommandIndexed = (GetCommandIndexedFn)GetProcAddress(g_glm, "?GetCommandIndexed@RClass@GLM@@QAEPAUSRefCmd@12@K@Z");
	pGetSuper = (GetSuperFn)GetProcAddress(g_glm, "?GetSuper@RClass@GLM@@QAEPAV12@XZ");
	pGetName = (GetNameFn)GetProcAddress(g_glm, "?GetName@RClass@GLM@@QAEPADXZ");
	pWindowGetObject = (StaticWindowGetObjectFn)GetProcAddress(g_glm, "?StaticWindowGetObject@WWindow@GLM@@SAPAV12@PAX@Z");
	pLogAddTarget = (LogAddTargetFn)GetProcAddress(g_glm, "?LOG_AddTarget@GLM@@YAKPAVILogTarget@1@@Z");
	pGetWorkspace = (GetWorkspaceFn)GetProcAddress(g_glm, "?ED_GetWorkspace@GLM@@YAPAVRGemWorkspaceFolder@1@XZ");
	pWindowCommandf = (WindowCommandfFn)GetProcAddress(g_glm, "?WindowCommandf@WWindow@GLM@@UAA_NPADZZ");
	pItemGetName = (ItemGetNameFn)GetProcAddress(g_glm, "?GemItemGetName@RGemTreeItem@GLM@@UAEPBDXZ");
	if (!pExecuteCommand || !pGetCommandNamed || !pGetCommandCount || !pGetCommandIndexed || !pGetSuper || !pGetName
	    || !pWindowGetObject || !pLogAddTarget || !pGetWorkspace || !pItemGetName || !pWindowCommandf)
	{ BLog("GlmLib.dll exports not found"); return 1; }
	Sleep(2000);
	g_logObj[0] = (void *)g_logVtbl;
	BLog("log target slot %lu", pLogAddTarget(g_logObj));
	g_done = CreateEventW(NULL, TRUE, FALSE, NULL);
	if (!Attach()) { BLog("main window vanished"); return 1; }
	PatchMessageBoxes();
	wsprintfW(pipeName, PIPE_NAME, GetCurrentProcessId());
	BLog("listening on the pipe");
	for (;;)
	{
		HANDLE p = CreateNamedPipeW(pipeName, PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
			PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS, 1, 1 << 16, 1 << 16, 0, NULL);
		if (p == INVALID_HANDLE_VALUE) { Sleep(1000); continue; }
		if (ConnectNamedPipe(p, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) Serve(p);
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
		DisableThreadLibraryCalls(inst);
		CloseHandle(CreateThread(NULL, 0, Main, NULL, 0, NULL));
	}
	return TRUE;
}
