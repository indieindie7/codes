/* HydroWater mod for Hydrophobia: Prophecy (HydroPC.exe, 32-bit).
 *
 * Built as dinput8.dll: the game imports DirectInput8Create from dinput8.dll, so a copy of this
 * DLL in the game folder is loaded by the exe itself (no exe patch, no launcher). It forwards
 * DirectInput8Create to the system dinput8.dll and, once the Steam stub has decrypted the code
 * (the bytes at the solver's entry become what we expect), detours the water solver
 * FUN_00d5c9d0(sheet, dt) onto HydroWater (../src/hydrowater.c): the game's sheet planes are
 * copied into an hw_sheet, stepped with the upgrade options from HydroWater.ini, and copied
 * back in the layout the game expects (result in the other depth buffer, buffer index flipped,
 * u/v/c planes, flow accumulators, step counters, consumed dt returned in xmm0).
 *
 * Sheet layout read out of the exe (dword indices into the sheet struct; see
 * games/REVERSE-ENGINEERING.md and the mod README):
 *   [0] current buffer (0/1)      [1] width w        [2] padded width, row stride = [2]+4
 *   [3] height h                  [4] cell size dx   [7] 1/dx    [8] CFL   [9] g
 *   [10],[11] depth buffers       [0xd],[0xe] hu     [0xf],[0x10] hv
 *   [0x12] v  [0x13] c = sqrt(g h)  [0x14] u  [0x15] bed  [0x19] wall (1/dx on wall cells)
 *   [0x1c],[0x1d] flow accumulators (+= vel * [0x60] * dt + [0xb1]/[0xb2] * dt)
 *   [0x17] stages (2)  [0x24] last dt  [0x3e] dirty  [0x42],[0x43] step counters  [0x6b] flat
 * Planes: (h+4) rows of ([2]+4) floats, interior cell (i,j) at row j+2, column i+2.
 *
 * GPL. Our own code, no game data.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include "../../src/hydrowater.h"

/* ---------------------------------------------------------------- addresses */
#define IMAGE_BASE      0x400000u
#define VA_STEP         0xd5c9d0u              /* FUN_00d5c9d0(uint *sheet, float dt) */
static const BYTE STEP_PROLOGUE[6] = { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF0 }; /* push ebp; mov ebp,esp; and esp,-16 */

/* ---------------------------------------------------------------- config */
enum { MODE_OFF = 0, MODE_PASSTHROUGH = 1, MODE_HW = 2 };
static struct {
    int mode;
    hw_opts opts;
    int log_every;      /* log sheet stats every N steps (0 = never) */
    int max_cells;      /* sheets larger than this stay on the game's solver */
} cfg = { MODE_HW, { 0, 0, 0, 1, 1.0f, 0.2f, 0.7f }, 600, 4096 };

static wchar_t g_dir[MAX_PATH];     /* folder of this DLL */

/* ---------------------------------------------------------------- logging */
static CRITICAL_SECTION g_logcs;
static void Log(const char *fmt, ...)
{
    wchar_t path[MAX_PATH];
    FILE *f;
    va_list ap;
    SYSTEMTIME t;
    _snwprintf(path, MAX_PATH, L"%ls\\HydroWater.log", g_dir);
    EnterCriticalSection(&g_logcs);
    f = _wfopen(path, L"a");
    if (f) {
        GetLocalTime(&t);
        fprintf(f, "%02d:%02d:%02d.%03d ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
        va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
        fputc('\n', f);
        fclose(f);
    }
    LeaveCriticalSection(&g_logcs);
}

static void ReadIni(void)
{
    wchar_t path[MAX_PATH];
    FILE *f;
    char line[256];
    _snwprintf(path, MAX_PATH, L"%ls\\HydroWater.ini", g_dir);
    f = _wfopen(path, L"r");
    if (!f) { Log("HydroWater.ini not found, defaults in use"); return; }
    while (fgets(line, sizeof line, f)) {
        char *k = line, *v, *e;
        while (*k == ' ' || *k == '\t') k++;
        if (*k == ';' || *k == '#' || *k == '[' || *k == '\n' || *k == '\r' || !*k) continue;
        v = strchr(k, '=');
        if (!v) continue;
        *v++ = 0;
        for (e = k + strlen(k); e > k && (e[-1] == ' ' || e[-1] == '\t'); e--) e[-1] = 0;
        while (*v == ' ' || *v == '\t') v++;
        for (e = v + strlen(v); e > v && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\n' || e[-1] == '\r'); e--) e[-1] = 0;
        if (!_stricmp(k, "mode")) {
            if (!_stricmp(v, "off")) cfg.mode = MODE_OFF;
            else if (!_stricmp(v, "passthrough")) cfg.mode = MODE_PASSTHROUGH;
            else cfg.mode = MODE_HW;
        }
        else if (!_stricmp(k, "displacement")) cfg.opts.displacement = atoi(v);
        else if (!_stricmp(k, "capped_stamp")) cfg.opts.capped_stamp = atoi(v);
        else if (!_stricmp(k, "face_walls")) cfg.opts.face_walls = atoi(v);
        else if (!_stricmp(k, "clamps")) cfg.opts.clamps = atoi(v);
        else if (!_stricmp(k, "recon")) cfg.opts.recon = atoi(v);
        else if (!_stricmp(k, "alpha")) cfg.opts.alpha = (float)atof(v);
        else if (!_stricmp(k, "c_adapt")) cfg.opts.c_adapt = (float)atof(v);
        else if (!_stricmp(k, "edge_damp")) cfg.opts.edge_damp = (float)atof(v);
        else if (!_stricmp(k, "log_every")) cfg.log_every = atoi(v);
        else if (!_stricmp(k, "max_cells")) cfg.max_cells = atoi(v);
    }
    fclose(f);
    Log("config: mode=%d displacement=%d capped_stamp=%d face_walls=%d clamps=%d recon=%d alpha=%.2f c_adapt=%.2f edge_damp=%.2f log_every=%d max_cells=%d",
        cfg.mode, cfg.opts.displacement, cfg.opts.capped_stamp, cfg.opts.face_walls, cfg.opts.clamps, cfg.opts.recon,
        cfg.opts.alpha, cfg.opts.c_adapt, cfg.opts.edge_damp, cfg.log_every, cfg.max_cells);
}

/* ---------------------------------------------------------------- the original, via trampoline */
void *g_tramp;   /* the solver's first 6 bytes + jmp back; asm name _g_tramp */

/* float orig_step(uint32_t *sheet, float dt): the game's solver returns the consumed dt in
   xmm0 (whole-program-optimised convention), so a C call cannot read it; this thunk moves it
   onto the x87 stack where a cdecl float return lives. */
__attribute__((naked)) static float CallOrig(uint32_t *sheet, float dt)
{
    __asm__ volatile(
        "pushl 8(%%esp)\n\t"
        "pushl 8(%%esp)\n\t"
        "call *_g_tramp\n\t"
        "addl $8, %%esp\n\t"
        "subl $4, %%esp\n\t"
        "movss %%xmm0, (%%esp)\n\t"
        "flds (%%esp)\n\t"
        "addl $4, %%esp\n\t"
        "ret\n\t"
        ::: "memory");
}

/* ---------------------------------------------------------------- sheet bridge */
typedef struct bridge {
    uint32_t *S;        /* the game's sheet */
    int w, h;
    hw_sheet *hw;
    unsigned steps;
    struct bridge *next;
} bridge;

static SRWLOCK g_lock = SRWLOCK_INIT;
static bridge *g_bridges;
static int g_nbridges;
static volatile LONG g_calls, g_hw_calls;

static bridge *Find(uint32_t *S, int w, int h)
{
    bridge *b;
    AcquireSRWLockShared(&g_lock);
    for (b = g_bridges; b; b = b->next) if (b->S == S) break;
    ReleaseSRWLockShared(&g_lock);
    if (b && b->hw && b->w == w && b->h == h) return b;
    AcquireSRWLockExclusive(&g_lock);
    if (!b) {
        for (b = g_bridges; b; b = b->next) if (b->S == S) break;
        if (!b) { b = (bridge *)calloc(1, sizeof *b); b->S = S; b->next = g_bridges; g_bridges = b; g_nbridges++; }
    }
    if (b->hw && (b->w != w || b->h != h)) { hw_destroy(b->hw); b->hw = NULL; }
    if (!b->hw) {
        b->w = w; b->h = h; b->steps = 0;
        b->hw = hw_create(w, h, *(float *)&S[4], *(float *)&S[9], *(float *)&S[8]);
        hw_set_opts(b->hw, &cfg.opts);
        Log("sheet %p: %d x %d cells (stride %u), dx %.1f g %.1f cfl %.2f, now on HydroWater (%d sheets)",
            (void *)S, w, h, S[2] + 4, *(float *)&S[4], *(float *)&S[9], *(float *)&S[8], g_nbridges);
    }
    ReleaseSRWLockExclusive(&g_lock);
    return b;
}

static void CopyPlane(float *dst, int dstride, const float *src, int sstride, int rows, int cols)
{
    int r;
    for (r = 0; r < rows; r++) memcpy(dst + r * dstride, src + r * sstride, (size_t)cols * sizeof(float));
}

/* the detour target: same contract as FUN_00d5c9d0, returns the consumed dt */
__attribute__((used, noinline)) float hw_hook_step(uint32_t *S, float dt)
{
    int w, h, gs, rows, cols, hs, r, i;
    const float *gh, *ghu, *ghv, *gbed, *gwall;
    float *oh, *ohu, *ohv, *gu, *gv, *gc, *gfx, *gfy;
    float *hh, *hhu, *hhv, *hu, *hv, *hbed, *hwall;
    float g, kflow, driftx, drifty;
    bridge *b;
    unsigned idx;

    InterlockedIncrement(&g_calls);
    if (cfg.mode != MODE_HW) return CallOrig(S, dt);
    w = (int)S[1]; h = (int)S[3];
    if (S[0x6b] != 0 || w <= 0 || h <= 0 || w * h > cfg.max_cells || S[0] > 1 ||
        !S[10] || !S[11] || !S[0xd] || !S[0xe] || !S[0xf] || !S[0x10] || !S[0x12] || !S[0x13] ||
        !S[0x14] || !S[0x15] || !S[0x19] || !(dt > 0.0f))
        return CallOrig(S, dt);

    b = Find(S, w, h);
    idx = S[0];
    gs = (int)S[2] + 4; rows = h + 4; cols = w + 4;
    gh = (const float *)S[10 + idx]; ghu = (const float *)S[0xd + idx]; ghv = (const float *)S[0xf + idx];
    gbed = (const float *)S[0x15]; gwall = (const float *)S[0x19];
    oh = (float *)S[10 + (idx ^ 1)]; ohu = (float *)S[0xd + (idx ^ 1)]; ohv = (float *)S[0xf + (idx ^ 1)];
    gu = (float *)S[0x14]; gv = (float *)S[0x12]; gc = (float *)S[0x13];
    gfx = (float *)S[0x1c]; gfy = (float *)S[0x1d];

    hs = hw_stride(b->hw);
    hh = hw_depth(b->hw); hhu = hw_hu(b->hw); hhv = hw_hv(b->hw);
    hbed = hw_bed(b->hw); hwall = hw_wall(b->hw);
    CopyPlane(hh, hs, gh, gs, rows, cols);
    CopyPlane(hhu, hs, ghu, gs, rows, cols);
    CopyPlane(hhv, hs, ghv, gs, rows, cols);
    CopyPlane(hbed, hs, gbed, gs, rows, cols);
    for (r = 0; r < rows; r++)
        for (i = 0; i < cols; i++)   /* the 2-cell padding ring stays wall so nothing leaks off the sheet */
            hwall[r * hs + i] = (gwall[r * gs + i] != 0.0f || r < 2 || r >= rows - 2 || i < 2 || i >= cols - 2) ? 1.0f : 0.0f;

    if (cfg.opts.displacement) hw_bodies_begin(b->hw);   /* no bodies registered yet (stage 1 hook pending) */
    hw_step(b->hw, dt);

    hh = hw_depth(b->hw); hhu = hw_hu(b->hw); hhv = hw_hv(b->hw);
    hu = hw_u(b->hw); hv = hw_v(b->hw);
    g = *(float *)&S[9];
    kflow = *(float *)&S[0x60]; driftx = *(float *)&S[0xb1]; drifty = *(float *)&S[0xb2];
    CopyPlane(oh, gs, hh, hs, rows, cols);
    CopyPlane(ohu, gs, hhu, hs, rows, cols);
    CopyPlane(ohv, gs, hhv, hs, rows, cols);
    CopyPlane(gu, gs, hu, hs, rows, cols);
    CopyPlane(gv, gs, hv, hs, rows, cols);
    for (r = 0; r < rows; r++)
        for (i = 0; i < cols; i++) {
            float d = hh[r * hs + i];
            gc[r * gs + i] = d > 0.0f ? sqrtf(g * d) : 0.0f;
        }
    if (gfx && gfy)
        for (r = 2; r < rows - 2; r++)
            for (i = 2; i < cols - 2; i++) {
                gfx[r * gs + i] += hu[r * hs + i] * kflow * dt + driftx * dt;
                gfy[r * gs + i] += hv[r * hs + i] * kflow * dt + drifty * dt;
            }

    S[0] = idx ^ 1;
    *(float *)&S[0x24] = dt;
    if (S[0x17] == 1) S[0x42]++; else S[0x43]++;
    InterlockedIncrement(&g_hw_calls);
    b->steps++;
    if (cfg.log_every > 0 && b->steps % (unsigned)cfg.log_every == 0)
        Log("sheet %p: step %u dt %.4f volume %.1f smax %.1f", (void *)S, b->steps, dt, hw_volume(b->hw), hw_smax(b->hw));
    return dt;
}

/* what the patched solver entry jumps to: cdecl in, consumed dt out in xmm0 */
__attribute__((naked)) static void HookEntry(void)
{
    __asm__ volatile(
        "pushl 8(%%esp)\n\t"
        "pushl 8(%%esp)\n\t"
        "call _hw_hook_step\n\t"
        "addl $8, %%esp\n\t"
        "subl $4, %%esp\n\t"
        "fstps (%%esp)\n\t"
        "movss (%%esp), %%xmm0\n\t"
        "addl $4, %%esp\n\t"
        "ret\n\t"
        ::: "memory");
}

/* ---------------------------------------------------------------- the detour */
#ifdef HW_TEST
BYTE *hw_test_target;                      /* tests/hooktest.c points this at a fake solver */
static BYTE *Target(void) { return hw_test_target; }
#else
static BYTE *Target(void)
{
    HMODULE exe = GetModuleHandleW(NULL);
    return (BYTE *)exe + (VA_STEP - IMAGE_BASE);
}
#endif

static int Readable(const void *p, size_t n)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery(p, &mbi, sizeof mbi)) return 0;
    if (mbi.State != MEM_COMMIT) return 0;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return 0;
    return (const BYTE *)p + n <= (const BYTE *)mbi.BaseAddress + mbi.RegionSize;
}

static int Install(void)
{
    BYTE *t = Target();
    BYTE *tr;
    DWORD prot;
    int32_t rel;
    if (!Readable(t, 6) || memcmp(t, STEP_PROLOGUE, 6) != 0) return 0;
    tr = (BYTE *)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!tr) { Log("VirtualAlloc for the trampoline failed: %lu", GetLastError()); return -1; }
    memcpy(tr, STEP_PROLOGUE, 6);
    tr[6] = 0xE9;
    rel = (int32_t)((t + 6) - (tr + 11));
    memcpy(tr + 7, &rel, 4);
    g_tramp = tr;
    if (!VirtualProtect(t, 6, PAGE_EXECUTE_READWRITE, &prot)) { Log("VirtualProtect failed: %lu", GetLastError()); return -1; }
    t[0] = 0xE9;
    rel = (int32_t)((BYTE *)HookEntry - (t + 5));
    memcpy(t + 1, &rel, 4);
    t[5] = 0x90;
    VirtualProtect(t, 6, prot, &prot);
    FlushInstructionCache(GetCurrentProcess(), t, 6);
    Log("solver hooked at %p (trampoline %p, hook %p)", (void *)t, (void *)tr, (void *)HookEntry);
    return 1;
}

static DWORD WINAPI Installer(LPVOID arg)
{
    int i, r;
    (void)arg;
    for (i = 0; i < 6000; i++) {           /* up to two minutes for the Steam stub to unpack */
        r = Install();
        if (r != 0) {
            if (r > 0 && cfg.mode == MODE_OFF) Log("mode=off: the hook forwards every call to the game's solver");
            return 0;
        }
        Sleep(20);
    }
    Log("gave up: the solver's entry never showed the expected bytes (different exe build?)");
    return 0;
}

/* ---------------------------------------------------------------- dinput8 forwarding */
static HMODULE g_real;
static FARPROC g_real_create;

__attribute__((used)) FARPROC hw_resolve_dinput(void)
{
    wchar_t path[MAX_PATH];
    if (!g_real_create) {
        UINT n = GetSystemDirectoryW(path, MAX_PATH);
        _snwprintf(path + n, MAX_PATH - n, L"\\dinput8.dll");
        g_real = LoadLibraryW(path);
        if (g_real) g_real_create = GetProcAddress(g_real, "DirectInput8Create");
        if (!g_real_create) Log("the system dinput8.dll could not be loaded (%lu)", GetLastError());
    }
    return g_real_create;
}

/* exported as DirectInput8Create; the stack is handed through untouched, so the stdcall
   contract (5 args, callee cleans) is the real function's business */
__attribute__((naked)) __declspec(dllexport) void DirectInput8Create(void)
{
    __asm__ volatile(
        "pushal\n\t"
        "call _hw_resolve_dinput\n\t"
        "movl %%eax, 28(%%esp)\n\t"   /* the saved eax slot: popal restores it as the target */
        "popal\n\t"
        "jmp *%%eax\n\t"
        ::: "memory");
}

#ifdef HW_TEST
void hw_test_setup(const wchar_t *dir, int mode)
{
    InitializeCriticalSection(&g_logcs);
    wcsncpy(g_dir, dir, MAX_PATH - 1);
    cfg.mode = mode;
}
int hw_test_install(void) { return Install(); }
void hw_test_mode(int mode) { cfg.mode = mode; }
#endif

/* ---------------------------------------------------------------- entry */
BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        wchar_t *p;
        DisableThreadLibraryCalls(inst);
        InitializeCriticalSection(&g_logcs);
        GetModuleFileNameW(inst, g_dir, MAX_PATH);
        p = wcsrchr(g_dir, L'\\');
        if (p) *p = 0;
        Log("HydroWater mod loaded into %ls (exe base %p)", g_dir, (void *)GetModuleHandleW(NULL));
        ReadIni();
        CreateThread(NULL, 0, Installer, NULL, 0, NULL);
    }
    else if (reason == DLL_PROCESS_DETACH) {
        Log("unloading: %ld solver calls, %ld on HydroWater, %d sheets", g_calls, g_hw_calls, g_nbridges);
    }
    return TRUE;
}
