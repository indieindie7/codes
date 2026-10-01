/* AdventUCC hook: loaded into advent.exe before it runs. Waits until the
   game's own launcher has initialised the engine (appInit: memory, files,
   config, log), then runs a commandlet from Editor.dll instead of the game. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

typedef void* (__cdecl *StaticLoadClass_t)(void* Base, void* Outer, const wchar_t* Name, const wchar_t* File, DWORD Flags, void* Sandbox);
typedef void* (__cdecl *StaticConstructObject_t)(void* Class, void* Outer, int Name, DWORD Flags, void* Template, void* Error, void* A, int B, void* C);
typedef void* (__cdecl *Getter_t)(void);
typedef void (__fastcall *Serialize_t)(void* This, void* Edx, const wchar_t* V, int Event);
typedef void (__fastcall *VoidMethod_t)(void* This, void* Edx);
typedef int  (__fastcall *Main_t)(void* This, void* Edx, const wchar_t* Parms);

#define VT_INITEXECUTION 13
#define VT_MAIN 25
#define LOAD_NOWARN 0x2

static HMODULE Core;
static StaticLoadClass_t RealSLC;
static FILE* Out;
static int Started;
static void* WarnVtbl[96];
static Serialize_t RealWarnSerialize;

static void Say(const wchar_t* Fmt, ...)
{
	va_list A;
	if (!Out) return;
	va_start(A, Fmt);
	vfwprintf(Out, Fmt, A);
	va_end(A);
	fputwc(10, Out);
	fflush(Out);
}

static void* Sym(const char* Name)
{
	void* P = (void*)GetProcAddress(Core, Name);
	if (!P) Say(L"[AdventUCC] missing export %hs", Name);
	return P;
}

static void SetInt(const char* Name, int V)
{
	int* P = (int*)Sym(Name);
	if (P) *P = V;
}

/* everything the commandlet prints goes through GWarn->Serialize */
/* Core's exports are jump thunks: point one at our function, return the real one */
static void* Redirect(const char* Name, void* To)
{
	BYTE* Thunk = (BYTE*)Sym(Name);
	void* Real;
	DWORD Old;
	if (!Thunk || Thunk[0] != 0xE9) { Say(L"[AdventUCC] unexpected entry for %hs", Name); return NULL; }
	Real = Thunk + 5 + *(LONG*)(Thunk + 1);
	if (!VirtualProtect(Thunk, 5, PAGE_EXECUTE_READWRITE, &Old)) return NULL;
	*(LONG*)(Thunk + 1) = (LONG)((BYTE*)To - (Thunk + 5));
	VirtualProtect(Thunk, 5, Old, &Old);
	FlushInstructionCache(GetCurrentProcess(), Thunk, 5);
	return Real;
}

/* The engine's class exporter passes a null object when a class has an empty
   exported object reference in its defaults, and crashes. Skip those. */
typedef void (__cdecl *ExportToOutputDevice_t)(void* Object, void* Exporter, void* Out, const wchar_t* FileType, int Indent);
static ExportToOutputDevice_t RealExportToOutputDevice;
static int SkippedExports, Failed;

static void __cdecl HookExportToOutputDevice(void* Object, void* Exporter, void* OutDev, const wchar_t* FileType, int Indent)
{
	if (!Object) { SkippedExports++; return; }
	RealExportToOutputDevice(Object, Exporter, OutDev, FileType, Indent);
}

#define NAME_WARNING 788
#define NAME_ERROR 789
typedef void* (__fastcall *GetContext_t)(void* This, void* Edx, void* Result);
typedef void (__fastcall *SetContext_t)(void* This, void* Edx, void* Supplier);
static SetContext_t RealSetContext;
static void* Context;

static void __fastcall WarnSetContext(void* This, void* Edx, void* Supplier)
{
	Context = Supplier;
	RealSetContext(This, Edx, Supplier);
}

static void __fastcall WarnSerialize(void* This, void* Edx, const wchar_t* V, int Event)
{
	struct { wchar_t* Data; int Num, Max; } Where = { NULL, 0, 0 };
	/* the compiler tells the feedback device which file/line it is on; the game's device ignores it */
	if (Context && (Event == NAME_ERROR || Event == NAME_WARNING))
		((GetContext_t)(*(void***)Context)[0])(Context, NULL, &Where);
	if (Where.Data && Where.Num > 1) Say(L"%ls : %ls", Where.Data, V ? V : L"");
	else Say(L"%ls", V ? V : L"");
	if (V && wcsstr(V, L"aborted due to errors")) Failed = 1;
	RealWarnSerialize(This, Edx, V, Event);
}

/* ADVENTUCC_LOG=1: also print the engine log (script Log/Warn lines end up there) */
static void* LogVtbl[32];
static Serialize_t RealLogSerialize;

static void __fastcall LogSerialize(void* This, void* Edx, const wchar_t* V, int Event)
{
	Say(L"Log: %ls", V ? V : L"");
	RealLogSerialize(This, Edx, V, Event);
}

static void TapLog(void)
{
	void*** PLog = (void***)Sym("?GLog@@3PAVFOutputDevice@@A");
	void** Obj;
	if (!PLog || !*PLog || !GetEnvironmentVariableW(L"ADVENTUCC_LOG", NULL, 0)) return;
	Obj = (void**)*PLog;
	memcpy(LogVtbl, *Obj, sizeof(LogVtbl));
	RealLogSerialize = (Serialize_t)LogVtbl[0];
	LogVtbl[0] = (void*)LogSerialize;
	*Obj = LogVtbl;
}

static void TapWarn(void)
{
	void*** PWarn = (void***)Sym("?GWarn@@3PAVFFeedbackContext@@A");
	void** Obj;
	if (!PWarn || !*PWarn) return;
	Obj = (void**)*PWarn;
	memcpy(WarnVtbl, *Obj, sizeof(WarnVtbl));
	RealWarnSerialize = (Serialize_t)WarnVtbl[0];
	WarnVtbl[0] = (void*)WarnSerialize;
	RealSetContext = (SetContext_t)WarnVtbl[6];
	WarnVtbl[6] = (void*)WarnSetContext;
	*Obj = WarnVtbl;
}

static int RunCommandlet(void)
{
	static wchar_t Cmd[4096], Full[512];
	wchar_t *Name = Cmd, *Parms;
	void *Base, *Class = NULL, *Obj, **Vt, **PErr;
	int IsMake, Ret;

	if (!GetEnvironmentVariableW(L"ADVENTUCC_CMD", Cmd, 4096)) { Say(L"[AdventUCC] no command"); return 2; }
	Parms = wcschr(Cmd, 32);
	if (Parms) *Parms++ = 0; else Parms = L"";
	IsMake = !_wcsicmp(Name, L"make");

	SetInt("?GIsUCC@@3HA", 1); SetInt("?GIsEditor@@3HA", 1); SetInt("?GIsScriptable@@3HA", 1);
	SetInt("?GIsClient@@3HA", 1); SetInt("?GIsServer@@3HA", 1); SetInt("?GLazyLoad@@3HA", 1);
	TapWarn();
	TapLog();
	RealExportToOutputDevice = (ExportToOutputDevice_t)Redirect("?ExportToOutputDevice@UExporter@@SAXPAVUObject@@PAV1@AAVFOutputDevice@@PBGH@Z", HookExportToOutputDevice);

	Base = ((Getter_t)Sym("?StaticClass@UCommandlet@@SAPAVUClass@@XZ"))();
	if (wcschr(Name, 46))
		Class = RealSLC(Base, NULL, Name, NULL, LOAD_NOWARN, NULL);
	if (!Class) { swprintf(Full, 512, L"Editor.%lsCommandlet", Name); Class = RealSLC(Base, NULL, Full, NULL, LOAD_NOWARN, NULL); }
	if (!Class) { swprintf(Full, 512, L"Editor.%ls", Name); Class = RealSLC(Base, NULL, Full, NULL, LOAD_NOWARN, NULL); }
	if (!Class) { Say(L"[AdventUCC] commandlet %ls not found", Name); return 3; }
	if (IsMake) { SetInt("?GIsClient@@3HA", 0); SetInt("?GIsServer@@3HA", 0); }

	PErr = (void**)Sym("?GError@@3PAVFOutputDeviceError@@A");
	Obj = ((StaticConstructObject_t)Sym("?StaticConstructObject@UObject@@SAPAV1@PAVUClass@@PAV1@VFName@@K1PAVFOutputDevice@@1H1@Z"))
		(Class, ((Getter_t)Sym("?GetTransientPackage@UObject@@SAPAVUPackage@@XZ"))(), 0, 0, NULL, PErr ? *PErr : NULL, NULL, 0, NULL);
	if (!Obj) { Say(L"[AdventUCC] could not create the commandlet"); return 4; }
	Vt = *(void***)Obj;
	((VoidMethod_t)Vt[VT_INITEXECUTION])(Obj, NULL);
	Say(L"[AdventUCC] running %ls %ls", Name, Parms);
	Ret = ((Main_t)Vt[VT_MAIN])(Obj, NULL, Parms);
	if (SkippedExports) Say(L"[AdventUCC] skipped %d empty object exports", SkippedExports);
	if (Failed && !Ret) Ret = 1;
	Say(L"[AdventUCC] finished, result %d", Ret);
	return Ret;
}

static int Report(EXCEPTION_POINTERS* E)
{
	Say(L"[AdventUCC] exception %08X at %p", E->ExceptionRecord->ExceptionCode, E->ExceptionRecord->ExceptionAddress);
	return EXCEPTION_EXECUTE_HANDLER;
}

static int Guarded(void)
{
	int Ret = 1;
	__try { Ret = RunCommandlet(); }
	__except (Report(GetExceptionInformation())) { Ret = 10; }
	return Ret;
}

static void* __cdecl HookSLC(void* Base, void* Outer, const wchar_t* Name, const wchar_t* File, DWORD Flags, void* Sandbox)
{
	/* the launcher's first class load after appInit is the game engine */
	if (!Started && Name && wcsstr(Name, L"Engine"))
	{
		int Ret;
		Started = 1;
		Say(L"[AdventUCC] engine initialised (%ls), taking over", Name);
		Ret = Guarded();
		if (Out) fclose(Out);
		TerminateProcess(GetCurrentProcess(), Ret);
	}
	return RealSLC(Base, Outer, Name, File, Flags, Sandbox);
}

/* called by the launcher in a remote thread, before the game's main thread runs */
__declspec(dllexport) DWORD WINAPI Init(LPVOID Unused)
{
	static wchar_t Path[1024];

	if (GetEnvironmentVariableW(L"ADVENTUCC_OUT", Path, 1024))
		Out = _wfopen(Path, L"w, ccs=UTF-8");
	Core = LoadLibraryW(L"Core.dll");
	if (!Core) { Say(L"[AdventUCC] Core.dll not loaded (%d)", GetLastError()); return 0; }
	RealSLC = (StaticLoadClass_t)Redirect("?StaticLoadClass@UObject@@SAPAVUClass@@PAV2@PAV1@PBG2KPAVUPackageMap@@@Z", HookSLC);
	if (!RealSLC) return 0;
	Say(L"[AdventUCC] hook ready");
	return 1;
}

BOOL WINAPI DllMain(HINSTANCE H, DWORD Reason, LPVOID R) { return TRUE; }
