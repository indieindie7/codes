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
#define COBJMACROS
#include <d3d9.h>
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
    int borderless;     /* force the D3D9 device into a borderless window instead of exclusive fullscreen */
    int background;     /* keep the game running when its window is not in the foreground */
    int control;        /* poll HydroWater.cmd for test-pilot commands (shot ...) */
    int foam_dump;      /* write the first few foam-patched water shaders next to the DLL (debugging) */
    float foam_p[8];    /* foam_gain air_gain foam_life lace bubble_rise air_to_foam spread spray_rate; < 0 = library default */
} cfg = { MODE_HW, { 0, 0, 0, 1, 1.0f, 0.2f, 0.7f, 1, 1 }, 600, 4096, 1, 0, 0, 0, { -1, -1, -1, -1, -1, -1, -1, 0 } };
static const char *const FOAM_KEYS[8] = { "foam_gain", "air_gain", "foam_life", "lace", "bubble_rise", "air_to_foam", "spread", "spray_rate" };

static wchar_t g_dir[MAX_PATH];     /* folder of this DLL */
static volatile LONG g_presents;    /* IDirect3DDevice9::Present calls (control = 1) */

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
        else if (!_stricmp(k, "borderless")) cfg.borderless = atoi(v);
        else if (!_stricmp(k, "background")) cfg.background = atoi(v);
        else if (!_stricmp(k, "control")) cfg.control = atoi(v);
        else if (!_stricmp(k, "foam")) cfg.opts.foam = atoi(v);
        else if (!_stricmp(k, "foam_dump")) cfg.foam_dump = atoi(v);
        else {
            int n;
            for (n = 0; n < 8; n++) if (!_stricmp(k, FOAM_KEYS[n])) cfg.foam_p[n] = (float)atof(v);
        }
    }
    fclose(f);
    Log("config: mode=%d displacement=%d capped_stamp=%d face_walls=%d clamps=%d recon=%d alpha=%.2f c_adapt=%.2f edge_damp=%.2f log_every=%d max_cells=%d borderless=%d background=%d control=%d foam=%d",
        cfg.mode, cfg.opts.displacement, cfg.opts.capped_stamp, cfg.opts.face_walls, cfg.opts.clamps, cfg.opts.recon,
        cfg.opts.alpha, cfg.opts.c_adapt, cfg.opts.edge_damp, cfg.log_every, cfg.max_cells, cfg.borderless, cfg.background, cfg.control, cfg.opts.foam);
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
/* stage 7: foam and air of the last step as bytes (0..255), read by the mesh builder on a
   render worker thread. A new snapshot replaces the pointer in one store; old ones are never
   freed (sheets change size about never) so a reader can't be left holding freed memory. */
typedef struct foam_snap {
    int w, h;
    BYTE *foam, *air;   /* w*h each, cell (i,j) at j*w+i */
} foam_snap;

typedef struct bridge {
    uint32_t *S;        /* the game's sheet */
    int w, h;
    hw_sheet *hw;
    unsigned steps;
    foam_snap *volatile snap;
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
        if (cfg.opts.foam) {
            hw_foam_params fp;
            float *f = &fp.foam_gain;   /* the first seven floats, in FOAM_KEYS order */
            int n;
            foam_snap *sn = (foam_snap *)calloc(1, sizeof *sn + (size_t)w * h * 2);
            hw_get_foam_params(b->hw, &fp);
            for (n = 0; n < 7; n++) if (cfg.foam_p[n] >= 0.0f) f[n] = cfg.foam_p[n];
            if (cfg.foam_p[7] >= 0.0f) fp.spray_rate = cfg.foam_p[7];   /* drops aren't drawn in the game yet: 0 by default */
            hw_set_foam_params(b->hw, &fp);
            if (sn) { sn->w = w; sn->h = h; sn->foam = (BYTE *)(sn + 1); sn->air = sn->foam + (size_t)w * h; }
            b->snap = sn;
        }
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
    if (cfg.opts.foam && b->snap) {
        foam_snap *sn = b->snap;
        const float *pf = hw_foam(b->hw), *pa = hw_air(b->hw);
        int j;
        for (j = 0; j < h; j++)
            for (i = 0; i < w; i++) {
                float f = pf[(j + 2) * hs + i + 2], a = pa[(j + 2) * hs + i + 2];
                sn->foam[j * w + i] = (BYTE)(f <= 0.0f ? 0 : f >= 1.0f ? 255 : (int)(f * 255.0f + 0.5f));
                sn->air[j * w + i] = (BYTE)(a <= 0.0f ? 0 : a >= 1.0f ? 255 : (int)(a * 255.0f + 0.5f));
            }
    }

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
        Log("sheet %p: step %u dt %.4f volume %.1f smax %.1f (presents %ld)", (void *)S, b->steps, dt, hw_volume(b->hw), hw_smax(b->hw), g_presents);
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

/* ---------------------------------------------------------------- stage 7: foam into the water mesh
 * The sheet mesh is rebuilt by a render job, FUN_00bf0e20(job): job[0] the vertex buffer object,
 * job+0xc the sheet, job+0x10 the locked vertex pointer. It writes (w+1) x (h+1) vertices of 36
 * bytes, vertex j*(w+1)+i, colour dword at +32 = alpha << 24 | 0xffffff; the water shader reads
 * only the alpha (shallow fade). After a rebuild it unlocks through FUN_009b7f00 at 0xbf1448 with
 * the job in ESI; that call is pointed at MeshStub, which writes foam into red and air into green
 * (as 255 - value, so an untouched white vertex means none) and then jumps on to the unlock. The
 * shader patch below turns those channels into foam. Bytes are only written, never read: the
 * locked buffer can be write-combined memory. */
#define VA_MESH_UNLOCK_CALL 0xbf1448u          /* call FUN_009b7f00 after the vertices were written */
#define VA_UNLOCK           0x9b7f00u
void *g_unlock;                                /* asm name _g_unlock */
static int Readable(const void *p, size_t n);
static volatile LONG g_mesh_writes;

static bridge *Lookup(const uint32_t *S)
{
    bridge *b;
    AcquireSRWLockShared(&g_lock);
    for (b = g_bridges; b; b = b->next) if (b->S == S) break;
    ReleaseSRWLockShared(&g_lock);
    return b;
}

__attribute__((used, noinline)) void hw_mesh_foam(BYTE *job)
{
    uint32_t *S;
    BYTE *vb, *row;
    bridge *b;
    foam_snap *sn;
    int w, h, i, j, ci, cj;
    if (!job || !Readable(job, 0x14)) return;
    S = *(uint32_t **)(job + 0xc);
    vb = *(BYTE **)(job + 0x10);
    if (!S || !vb) return;
    b = Lookup(S);
    if (!b || !(sn = b->snap)) return;
    w = (int)S[1]; h = (int)S[3];
    if (w != sn->w || h != sn->h) return;
    for (j = 0; j <= h; j++) {
        cj = j < h ? j : h - 1;
        row = vb + (size_t)j * (w + 1) * 36;
        for (i = 0; i <= w; i++) {
            ci = i < w ? i : w - 1;
            row[i * 36 + 34] = (BYTE)(255 - sn->foam[cj * w + ci]);   /* R */
            row[i * 36 + 33] = (BYTE)(255 - sn->air[cj * w + ci]);    /* G */
        }
    }
    if (InterlockedIncrement(&g_mesh_writes) == 1) Log("foam: first water mesh coloured (sheet %p, %d x %d)", (void *)S, w, h);
}

__attribute__((naked, used)) static void MeshStub(void)
{
    __asm__ volatile(
        "pushal\n\t"
        "pushfl\n\t"
        "pushl %%esi\n\t"
        "call _hw_mesh_foam\n\t"
        "addl $4, %%esp\n\t"
        "popfl\n\t"
        "popal\n\t"
        "jmp *_g_unlock\n\t"
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

/* ---------------------------------------------------------------- stage 7: the foam shader
 * The game composes its shaders as HLSL text at run time and compiles them through its
 * D3DXCompileShader import. That import slot is pointed at CompileHook, which looks for the end
 * of the water's reflect/refract pixel code (FOAM_ANCHOR) and adds the foam after it: lace from
 * two octaves of value noise on the world position, coverage growing with the foam the mesh
 * carries in red, the foam lit from the scene behind it, and milky water where green says there
 * is air. If the patched text fails to compile, the original is compiled instead.
 * Compiled shaders are cached in shaderCacheDX.bin, which would keep the unpatched water; with
 * foam on, the exe's file name string is changed to shaderCacheHW.bin (same length) before the
 * cache is opened, so the game's own cache stays untouched and a second one is built. */
#define VA_SHADER_CACHE_NAME 0xeaf830u
static const char CACHE_NAME_GAME[] __attribute__((unused)) = "shaderCacheDX.bin";
static const char CACHE_NAME_HW[] __attribute__((unused))   = "shaderCacheHW.bin";   /* rename (same length) when FOAM_HLSL changes */
static const char FOAM_ANCHOR[] = "reflectionColour = vReflectionSample * fFresRefl.xxxx;";
static const char FOAM_DEFS[] =
    "\n#ifndef HW_VN\n"
    "#define HW_H(q) frac(sin(dot((q), float2(127.1f, 311.7f))) * 43758.5453f)\n"
    "#define HW_VN(p) lerp(lerp(HW_H(floor(p)), HW_H(floor(p) + float2(1.0f, 0.0f)), smoothstep(0.0f, 1.0f, frac(p).x)), "
    "lerp(HW_H(floor(p) + float2(0.0f, 1.0f)), HW_H(floor(p) + float2(1.0f, 1.0f)), smoothstep(0.0f, 1.0f, frac(p).x)), smoothstep(0.0f, 1.0f, frac(p).y))\n"
    "#endif\n";
static const char FOAM_HLSL[] =
    "{ /* HydroWater foam */\n"
    "  float hwF = saturate(1.0f - vertexColour.r);\n"
    "  float hwA = saturate(1.0f - vertexColour.g);\n"
    "  float2 hwP = vertexPosition.xy * (1.0f / 12.0f);\n"
    "  float hwN = 0.6f * HW_VN(hwP) + 0.4f * HW_VN(hwP * 0.45f + float2(17.0f, 5.0f));\n"
    "  float hwLace = lerp(1.0f - abs(hwN - 0.5f) * 2.0f, diffuseMapSample.x, 0.25f);\n"
    "  float hwCov = saturate((hwF * 1.25f - (1.0f - hwLace)) * (1.0f / 0.18f)) * saturate(hwF * 4.0f);\n"
    "  hwCov = max(hwCov, saturate((hwF - 0.8f) * 5.0f));\n"
    "  float hwLum = dot(vRefractionSample.rgb + vReflectionSample.rgb, float3(0.299f, 0.587f, 0.114f));\n"
    "  float3 hwFoam = lerp(float3(0.93f, 0.95f, 0.97f), vFogColour.rgb, 0.12f) * saturate(0.3f + 0.8f * hwLum);\n"
    "  float hwGrey = dot(refractionColour.rgb, float3(0.333f, 0.333f, 0.334f));\n"
    "  refractionColour.rgb = lerp(refractionColour.rgb, hwGrey * float3(0.8f, 1.0f, 1.0f) + 0.06f, hwA * 0.5f);\n"
    "  refractionColour.rgb = lerp(refractionColour.rgb, hwFoam, hwCov);\n"
    "  reflectionColour *= 1.0f - hwCov;\n"
    "  specularStrength *= 1.0f - hwCov;\n"
    "  diffuseMapSample.a = max(diffuseMapSample.a, hwCov);\n"
    "}\n";

typedef HRESULT (WINAPI *Compile_t)(const char *, UINT, const void *, void *, const char *, const char *, DWORD, void **, void **, void **);
static Compile_t g_orig_compile;
static volatile LONG g_foam_patched, g_foam_failed, g_foam_dumps;

static const char *FindN(const char *s, size_t n, const char *pat, size_t m)
{
    size_t i;
    if (m > n) return NULL;
    for (i = 0; i + m <= n; i++) if (s[i] == pat[0] && !memcmp(s + i, pat, m)) return s + i;
    return NULL;
}

/* src (len bytes, not necessarily terminated) with the foam inserted after every anchor, NULL
   when there is no anchor. The caller frees the result. */
__attribute__((used)) char *hw_foam_inject(const char *src, size_t len, size_t *outlen)
{
    size_t na = sizeof FOAM_ANCHOR - 1, nd = sizeof FOAM_DEFS - 1, nh = sizeof FOAM_HLSL - 1, k = 0, o = 0;
    const char *p = src, *q;
    char *out;
    while ((q = FindN(p, len - (size_t)(p - src), FOAM_ANCHOR, na)) != NULL) { k++; p = q + na; }
    if (!k) return NULL;
    out = (char *)malloc(len + k * (nd + nh) + 1);
    if (!out) return NULL;
    p = src;
    while ((q = FindN(p, len - (size_t)(p - src), FOAM_ANCHOR, na)) != NULL) {
        memcpy(out + o, p, (size_t)(q - p) + na); o += (size_t)(q - p) + na;
        memcpy(out + o, FOAM_DEFS, nd); o += nd;
        memcpy(out + o, FOAM_HLSL, nh); o += nh;
        p = q + na;
    }
    memcpy(out + o, p, len - (size_t)(p - src)); o += len - (size_t)(p - src);
    out[o] = 0;
    *outlen = o;
    return out;
}

static void ReleaseCom(void **pp)
{
    typedef ULONG (WINAPI *Rel_t)(void *);
    if (pp && *pp) { ((Rel_t)(*(void ***)*pp)[2])(*pp); *pp = NULL; }
}

static HRESULT WINAPI CompileHook(const char *src, UINT len, const void *defs, void *inc, const char *fn, const char *prof,
                                  DWORD flags, void **shader, void **errs, void **ctab)
{
    typedef void *(WINAPI *Ptr_t)(void *);
    size_t n = 0, srclen = len ? len : (src ? strlen(src) : 0);
    char *mod = (cfg.opts.foam && src) ? hw_foam_inject(src, srclen, &n) : NULL;
    HRESULT hr;
    if (mod) {
        void *e = NULL;
        LONG d;
        if (cfg.foam_dump && (d = InterlockedIncrement(&g_foam_dumps)) <= 4) {
            wchar_t path[MAX_PATH];
            FILE *f;
            _snwprintf(path, MAX_PATH, L"%ls\\HydroWater_shader%ld.hlsl", g_dir, d);
            if ((f = _wfopen(path, L"wb")) != NULL) { fwrite(mod, 1, n, f); fclose(f); }
        }
        hr = g_orig_compile(mod, (UINT)n, defs, inc, fn, prof, flags, shader, &e, ctab);
        if (hr >= 0) {
            free(mod);
            if (errs) *errs = e; else ReleaseCom(&e);
            if (InterlockedIncrement(&g_foam_patched) <= 3) Log("foam shader patched (%s %s)", fn ? fn : "?", prof ? prof : "?");
            return hr;
        }
        if (InterlockedIncrement(&g_foam_failed) <= 3) {
            const char *msg = e ? (const char *)((Ptr_t)(*(void ***)e)[3])(e) : NULL;   /* ID3DXBuffer::GetBufferPointer */
            Log("foam shader did not compile (%08lx, %s %s), the game's water is kept: %.600s", (unsigned long)hr,
                fn ? fn : "?", prof ? prof : "?", msg ? msg : "(no message)");
        }
        ReleaseCom(&e);
        if (shader) *shader = NULL;
        if (ctab) *ctab = NULL;
        free(mod);
    }
    return g_orig_compile(src, len, defs, inc, fn, prof, flags, shader, errs, ctab);
}

#ifdef HW_TEST
void hw_test_set_compile(void *fn) { g_orig_compile = (Compile_t)fn; }
void *hw_test_compile_hook(void) { return (void *)CompileHook; }
void hw_test_mesh_foam(BYTE *job) { hw_mesh_foam(job); }
int hw_test_foam_fill(const uint32_t *S, int foam, int air)
{
    bridge *b = Lookup(S);
    foam_snap *sn = b ? b->snap : NULL;
    if (!sn) return 0;
    memset(sn->foam, foam, (size_t)sn->w * sn->h);
    memset(sn->air, air, (size_t)sn->w * sn->h);
    sn->foam[0] = 255;                     /* cell (0,0) fully white */
    return 1;
}
#else
static BYTE *Exe(DWORD va) { return (BYTE *)GetModuleHandleW(NULL) + (va - IMAGE_BASE); }

static int PatchBytes(void *at, const void *bytes, size_t n)
{
    DWORD prot;
    if (!VirtualProtect(at, n, PAGE_EXECUTE_READWRITE, &prot)) return 0;
    memcpy(at, bytes, n);
    VirtualProtect(at, n, prot, &prot);
    FlushInstructionCache(GetCurrentProcess(), at, n);
    return 1;
}

/* the cache name, before the renderer opens the file: tried from the installer loop and again
   when the device is created */
static void PatchCacheName(void)
{
    static int done;
    char *s = (char *)Exe(VA_SHADER_CACHE_NAME);
    if (done || !cfg.opts.foam || !Readable(s, sizeof CACHE_NAME_GAME)) return;
    if (!memcmp(s, CACHE_NAME_HW, sizeof CACHE_NAME_HW)) { done = 1; return; }
    if (memcmp(s, CACHE_NAME_GAME, sizeof CACHE_NAME_GAME)) return;    /* not unpacked yet */
    if (PatchBytes(s, CACHE_NAME_HW, sizeof CACHE_NAME_HW)) { done = 1; Log("foam: shader cache is %s (the game's %s is left alone)", CACHE_NAME_HW, CACHE_NAME_GAME); }
}

/* the compile import: every slot in the exe image holding d3dx9_43!D3DXCompileShader */
static void HookCompile(void)
{
    static int done;
    HMODULE d3dx, exe = GetModuleHandleW(NULL);
    BYTE *fn, *base = (BYTE *)exe, *p, *end;
    IMAGE_NT_HEADERS *nt;
    MEMORY_BASIC_INFORMATION mbi;
    int hits = 0;
    if (done || !cfg.opts.foam) return;
    d3dx = GetModuleHandleW(L"d3dx9_43.dll");
    if (!d3dx || !(fn = (BYTE *)GetProcAddress(d3dx, "D3DXCompileShader"))) return;
    nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    end = base + nt->OptionalHeader.SizeOfImage;
    g_orig_compile = (Compile_t)fn;
    for (p = base; p < end && VirtualQuery(p, &mbi, sizeof mbi); p = (BYTE *)mbi.BaseAddress + mbi.RegionSize) {
        BYTE *q, *re = (BYTE *)mbi.BaseAddress + mbi.RegionSize;
        if (mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) continue;
        if (re > end) re = end;
        for (q = (BYTE *)mbi.BaseAddress; q + 4 <= re; q += 4)
            if (*(BYTE **)q == fn) {
                void *hook = (void *)CompileHook;
                if (PatchBytes(q, &hook, 4)) hits++;
            }
    }
    done = 1;
    if (hits) Log("foam: D3DXCompileShader import hooked (%d slot%s)", hits, hits == 1 ? "" : "s");
    else Log("foam: no D3DXCompileShader import slot found, the water shader is unchanged");
}

/* the mesh: call FUN_009b7f00 at 0xbf1448 retargeted to MeshStub */
static void HookMesh(void)
{
    static int done;
    BYTE *c = Exe(VA_MESH_UNLOCK_CALL);
    int32_t rel;
    if (done || !cfg.opts.foam || cfg.mode != MODE_HW || !Readable(c, 5) || c[0] != 0xE8) return;
    memcpy(&rel, c + 1, 4);
    done = 1;
    if (c + 5 + rel != Exe(VA_UNLOCK)) { Log("foam: unexpected code at the mesh unlock call, the mesh is not coloured"); return; }
    g_unlock = Exe(VA_UNLOCK);
    rel = (int32_t)((BYTE *)MeshStub - (c + 5));
    if (PatchBytes(c + 1, &rel, 4)) Log("foam: water mesh builder hooked at %p", (void *)c);
}
#endif

static void InstallFoam(void)
{
#ifndef HW_TEST
    PatchCacheName();
    HookCompile();
    HookMesh();
#endif
}

static void InstallWindowHooks(void);

static DWORD WINAPI Installer(LPVOID arg)
{
    int i, r;
    (void)arg;
    InstallWindowHooks();
    for (i = 0; i < 6000; i++) {           /* up to two minutes for the Steam stub to unpack */
#ifndef HW_TEST
        PatchCacheName();
#endif
        r = Install();
        if (r != 0) {
            InstallFoam();
            if (r > 0 && cfg.mode == MODE_OFF) Log("mode=off: the hook forwards every call to the game's solver");
            return 0;
        }
        Sleep(20);
    }
    Log("gave up: the solver's entry never showed the expected bytes (different exe build?)");
    return 0;
}

/* ---------------------------------------------------------------- borderless window / background
 * The game creates an exclusive-fullscreen Direct3D 9 device. IDirect3D9::CreateDevice (vtable
 * slot 16) and IDirect3DDevice9::Reset (slot 16) are patched in d3d9.dll's shared vtables: every
 * request with Windowed = FALSE is turned into a windowed device, and the game window is restyled
 * as a borderless popup the size of the back buffer, placed on its monitor. With background = 1
 * the window procedure is subclassed so the game never sees itself deactivated (it pauses
 * otherwise). No exe bytes are touched. */
typedef struct {
    UINT BackBufferWidth, BackBufferHeight, BackBufferFormat, BackBufferCount, MultiSampleType;
    DWORD MultiSampleQuality;
    UINT SwapEffect;
    HWND hDeviceWindow;
    BOOL Windowed, EnableAutoDepthStencil;
    UINT AutoDepthStencilFormat;
    DWORD Flags;
    UINT FullScreen_RefreshRateInHz, PresentationInterval;
} HW_D3DPP;
typedef HRESULT (WINAPI *CreateDevice_t)(void *, UINT, UINT, HWND, DWORD, HW_D3DPP *, void **);
typedef HRESULT (WINAPI *Reset_t)(void *, HW_D3DPP *);
typedef ULONG (WINAPI *Release_t)(void *);
typedef void *(WINAPI *Direct3DCreate9_t)(UINT);
static CreateDevice_t g_orig_create_device;
static Reset_t g_orig_reset;
static HWND g_game_wnd;
static WNDPROC g_orig_wndproc;

static LRESULT CALLBACK WndProcHook(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (cfg.background) {
        if (m == WM_ACTIVATEAPP && w == FALSE) return 0;
        if (m == WM_ACTIVATE && LOWORD(w) == WA_INACTIVE) return 0;
        if (m == WM_KILLFOCUS) return 0;
    }
    return CallWindowProcW(g_orig_wndproc, h, m, w, l);
}

static void AdoptWindow(HWND h)
{
    if (!h || h == g_game_wnd) return;
    g_game_wnd = h;
    if (cfg.background && !g_orig_wndproc) {
        g_orig_wndproc = (WNDPROC)SetWindowLongPtrW(h, GWLP_WNDPROC, (LONG_PTR)WndProcHook);
        Log("background: game window %p subclassed", (void *)h);
    }
}


/* With background = 1 the game must also believe it owns the foreground: user32's
 * GetForegroundWindow / GetActiveWindow / GetFocus are detoured at their hot-patchable
 * prologue (mov edi,edi; push ebp; mov ebp,esp) to answer with the game window. */
typedef HWND (WINAPI *HwndFn_t)(void);
static HwndFn_t g_orig_fg, g_orig_active, g_orig_focus;
static HWND WINAPI FgHook(void)     { return g_game_wnd ? g_game_wnd : g_orig_fg(); }
static HWND WINAPI ActiveHook(void) { return g_game_wnd ? g_game_wnd : g_orig_active(); }
static HWND WINAPI FocusHook(void)  { return g_game_wnd ? g_game_wnd : g_orig_focus(); }

/* Length of a relocatable prologue: the first >= 5 bytes must be instructions that run unchanged
 * from another address. Windows 10 user32 has these shapes; an existing jmp rel32 (another tool's
 * detour) is chained by relocating its target into the trampoline. */
static int PrologueLen(const BYTE *t)
{
    if (t[0] == 0x8B && t[1] == 0xFF && t[2] == 0x55 && t[3] == 0x8B && t[4] == 0xEC) return 5; /* mov edi,edi; push ebp; mov ebp,esp */
    if (t[0] == 0xFF && t[1] == 0x25) return 6;                                                  /* jmp [abs32] (forwarder) */
    if (t[0] == 0x6A && t[2] == 0xFF && t[3] == 0x15) return 8;                                  /* push imm8; call [abs32] */
    if (t[0] == 0xB8) return 5;                                                                  /* mov eax,imm32 (syscall stub) */
    if (t[0] == 0xE9) return 5;                                                                  /* jmp rel32 (someone else's detour, chained) */
    return 0;
}

static int HotPatch(const char *name, void *hook, HwndFn_t *orig)
{
    BYTE *t = (BYTE *)GetProcAddress(GetModuleHandleW(L"user32.dll"), name), *tr;
    DWORD prot;
    int32_t rel;
    int n = t ? PrologueLen(t) : 0;
    if (!n) {
        Log("background: %s has an unexpected prologue (%02x %02x %02x %02x %02x), not hooked", name,
            t ? t[0] : 0, t ? t[1] : 0, t ? t[2] : 0, t ? t[3] : 0, t ? t[4] : 0);
        return 0;
    }
    tr = (BYTE *)VirtualAlloc(NULL, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!tr) return 0;
    if (t[0] == 0xE9) {                     /* already detoured (e.g. an overlay): the trampoline jumps to that detour */
        memcpy(&rel, t + 1, 4);
        tr[0] = 0xE9;
        rel = (int32_t)((t + 5 + rel) - (tr + 5));
        memcpy(tr + 1, &rel, 4);
    } else {
        memcpy(tr, t, n);                   /* original prologue, then jump back behind it */
        tr[n] = 0xE9;
        rel = (int32_t)((t + n) - (tr + n + 5));
        memcpy(tr + n + 1, &rel, 4);
    }
    *orig = (HwndFn_t)tr;
    if (!VirtualProtect(t, n, PAGE_EXECUTE_READWRITE, &prot)) return 0;
    t[0] = 0xE9;
    rel = (int32_t)((BYTE *)hook - (t + 5));
    memcpy(t + 1, &rel, 4);
    VirtualProtect(t, n, prot, &prot);
    FlushInstructionCache(GetCurrentProcess(), t, n);
    Log("background: %s hooked (%d-byte prologue)", name, n);
    return 1;
}

static void InstallForegroundHooks(void)
{
    int n = 0;
    n += HotPatch("GetForegroundWindow", (void *)FgHook, &g_orig_fg);
    n += HotPatch("GetActiveWindow", (void *)ActiveHook, &g_orig_active);
    n += HotPatch("GetFocus", (void *)FocusHook, &g_orig_focus);
    Log("background: %d of 3 foreground queries answered with the game window", n);
}

static void MakeBorderless(HWND h, UINT w, UINT hgt)
{
    MONITORINFO mi;
    int x, y, mw, mh, iw = (int)w, ih = (int)hgt;
    LONG ex;
    mi.cbSize = sizeof mi;
    GetMonitorInfoW(MonitorFromWindow(h, MONITOR_DEFAULTTOPRIMARY), &mi);
    x = mi.rcMonitor.left; y = mi.rcMonitor.top;
    mw = mi.rcMonitor.right - x; mh = mi.rcMonitor.bottom - y;
    if (mw > iw) x += (mw - iw) / 2;
    if (mh > ih) y += (mh - ih) / 2;
    SetWindowLongW(h, GWL_STYLE, WS_POPUP | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS);
    ex = GetWindowLongW(h, GWL_EXSTYLE) & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_STATICEDGE);
    SetWindowLongW(h, GWL_EXSTYLE, ex);
    SetWindowPos(h, HWND_TOP, x, y, iw, ih, SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOACTIVATE);
    Log("borderless: window %p -> %dx%d at %d,%d", (void *)h, iw, ih, x, y);
}

static void ForceWindowed(HW_D3DPP *pp, HWND h)
{
    if (!pp || !cfg.borderless || pp->Windowed) return;
    pp->Windowed = TRUE;
    pp->FullScreen_RefreshRateInHz = 0;
    if (pp->PresentationInterval > 1 && pp->PresentationInterval != 0x80000000u) pp->PresentationInterval = 1;
    if (h) MakeBorderless(h, pp->BackBufferWidth, pp->BackBufferHeight);
}

static void PatchVtable(void *obj, int idx, void *hook, void **orig)
{
    void **vt = *(void ***)obj;
    DWORD old;
    if (vt[idx] == hook) return;
    if (!VirtualProtect(&vt[idx], sizeof(void *), PAGE_EXECUTE_READWRITE, &old)) { Log("vtable patch failed: %lu", GetLastError()); return; }
    *orig = vt[idx];
    vt[idx] = hook;
    VirtualProtect(&vt[idx], sizeof(void *), old, &old);
}

/* ---------------------------------------------------------------- control file (control = 1)
 * IDirect3DDevice9::Present (slot 17) is hooked as well. Every 250 ms it looks for
 * HydroWater.cmd next to the DLL, reads it, deletes it and runs its lines:
 *   shot <file.bmp>   dump the back buffer (works hidden, off-screen, any mode)
 * This is the test-pilot channel; it costs one file probe every quarter second. */
typedef HRESULT (WINAPI *Present_t)(IDirect3DDevice9 *, const RECT *, const RECT *, HWND, const RGNDATA *);
static Present_t g_orig_present;
static DWORD g_last_cmd_poll;

static void SaveBackbuffer(IDirect3DDevice9 *dev, const char *path)
{
    IDirect3DSurface9 *bb = NULL, *rt = NULL, *sys = NULL, *src;
    D3DSURFACE_DESC d;
    D3DLOCKED_RECT lr;
    HRESULT hr;
    FILE *f = NULL;
    hr = IDirect3DDevice9_GetBackBuffer(dev, 0, 0, D3DBACKBUFFER_TYPE_MONO, &bb);
    if (hr != D3D_OK) { Log("shot: GetBackBuffer failed %08lx", (unsigned long)hr); return; }
    IDirect3DSurface9_GetDesc(bb, &d);
    src = bb;
    if (d.MultiSampleType != D3DMULTISAMPLE_NONE) {
        hr = IDirect3DDevice9_CreateRenderTarget(dev, d.Width, d.Height, d.Format, D3DMULTISAMPLE_NONE, 0, FALSE, &rt, NULL);
        if (hr == D3D_OK) hr = IDirect3DDevice9_StretchRect(dev, bb, NULL, rt, NULL, D3DTEXF_NONE);
        if (hr != D3D_OK) { Log("shot: resolve failed %08lx", (unsigned long)hr); goto done; }
        src = rt;
    }
    hr = IDirect3DDevice9_CreateOffscreenPlainSurface(dev, d.Width, d.Height, d.Format, D3DPOOL_SYSTEMMEM, &sys, NULL);
    if (hr == D3D_OK) hr = IDirect3DDevice9_GetRenderTargetData(dev, src, sys);
    if (hr != D3D_OK) { Log("shot: GetRenderTargetData failed %08lx (format %d)", (unsigned long)hr, (int)d.Format); goto done; }
    if (d.Format != D3DFMT_X8R8G8B8 && d.Format != D3DFMT_A8R8G8B8) { Log("shot: back buffer format %d not handled", (int)d.Format); goto done; }
    hr = IDirect3DSurface9_LockRect(sys, &lr, NULL, D3DLOCK_READONLY);
    if (hr != D3D_OK) { Log("shot: LockRect failed %08lx", (unsigned long)hr); goto done; }
    f = fopen(path, "wb");
    if (f) {
        BITMAPFILEHEADER fh;
        BITMAPINFOHEADER ih;
        UINT y, x, stride = (d.Width * 3 + 3) & ~3u;
        BYTE *row = (BYTE *)calloc(stride, 1);
        memset(&fh, 0, sizeof fh); memset(&ih, 0, sizeof ih);
        fh.bfType = 0x4D42; fh.bfOffBits = sizeof fh + sizeof ih; fh.bfSize = fh.bfOffBits + stride * d.Height;
        ih.biSize = sizeof ih; ih.biWidth = (LONG)d.Width; ih.biHeight = (LONG)d.Height; ih.biPlanes = 1; ih.biBitCount = 24;
        fwrite(&fh, sizeof fh, 1, f); fwrite(&ih, sizeof ih, 1, f);
        for (y = d.Height; y-- > 0;) {
            const BYTE *p = (const BYTE *)lr.pBits + y * lr.Pitch;
            for (x = 0; x < d.Width; x++) { row[x * 3] = p[x * 4]; row[x * 3 + 1] = p[x * 4 + 1]; row[x * 3 + 2] = p[x * 4 + 2]; }
            fwrite(row, stride, 1, f);
        }
        free(row);
        fclose(f);
        Log("shot: %s (%ux%u, present #%ld)", path, d.Width, d.Height, g_presents);
    }
    else Log("shot: cannot write %s", path);
    IDirect3DSurface9_UnlockRect(sys);
done:
    if (sys) IDirect3DSurface9_Release(sys);
    if (rt) IDirect3DSurface9_Release(rt);
    if (bb) IDirect3DSurface9_Release(bb);
}

/* Level jumps for tests. The Lua handlers behind script_ChapterSelect (00be6060) and
 * script_LoadGame (00be5ab0) only write a few globals and switch the game's state machine;
 * the same writes are made here, on the render thread between frames (where the game's own
 * frame loop runs), so the game picks them up on its next update. Addresses are for the
 * Steam build (code version 0032) and are rebased on the exe's load address. */
#define g_exe_base ((BYTE *)GetModuleHandleW(NULL))
#define HG(a) ((volatile int *)(g_exe_base + ((a) - 0x400000)))
static void GameStateLog(const char *what)
{
    Log("control: %s state %d (0x%x), chapter %d/%d", what, *HG(0x01911380), *HG(0x01911380), *HG(0x01a880cc), *HG(0x01a880d0));
}
static void QuitToMenuIfPlaying(void)
{
    if (*HG(0x01911380) == 0x29) ((void (__cdecl *)(void))(g_exe_base + (0x00ce3030 - 0x400000)))();
}
static void ChapterSelect(int n)
{
    if (n <= 0) { Log("control: chapter %d ignored (chapters start at 1)", n); return; }
    *HG(0x0194070c) = 1;
    QuitToMenuIfPlaying();
    *HG(0x01a88080) = 1;
    *HG(0x01a0f184) = 1;
    *HG(0x01a72ffc) = 1;
    *HG(0x01911380) = 0x36;
    *HG(0x01a880cc) = n;
    *HG(0x01a880d0) = n;
    GameStateLog("chapter select ->");
}
static void ContinueGame(void)
{
    *HG(0x01a6c498) = 3;
    QuitToMenuIfPlaying();
    *HG(0x01911380) = 8;
    GameStateLog("load last checkpoint ->");
}

/* Mouse buttons for the menus. The game's window procedure takes only mouse movement from
 * Raw Input; buttons come in as WM_LBUTTONDOWN/UP and WM_RBUTTONDOWN/UP, which set a button
 * latch and call the UI's mouse callback with the client position. "click [r] [x y]" posts a
 * move, a press and (on the second following poll) a release to the game window. The position
 * is in client pixels and defaults to the centre. */
static UINT g_click_up;
static LPARAM g_click_pos;

static void InjectClick(const char *args)
{
    int right = args && (args[0] == 'r' || args[0] == 'R'), x = -1, y = -1;
    RECT rc;
    if (!g_game_wnd) { Log("control: click unavailable (no game window yet)"); return; }
    sscanf(args + (right ? 1 : 0), "%d %d", &x, &y);
    GetClientRect(g_game_wnd, &rc);
    if (x < 0 || y < 0) { x = rc.right / 2; y = rc.bottom / 2; }
    g_click_pos = MAKELPARAM(x, y);
    PostMessageW(g_game_wnd, WM_MOUSEMOVE, 0, g_click_pos);
    PostMessageW(g_game_wnd, right ? WM_RBUTTONDOWN : WM_LBUTTONDOWN, right ? MK_RBUTTON : MK_LBUTTON, g_click_pos);
    g_click_up = right ? WM_RBUTTONUP : WM_LBUTTONUP;
    Log("control: %s click at %d,%d", right ? "right" : "left", x, y);
}

static void ClickTick(void)           /* release on the second following control poll */
{
    static int armed;
    if (!g_click_up) { armed = 0; return; }
    if (!armed) { armed = 1; return; }
    PostMessageW(g_game_wnd, g_click_up, 0, g_click_pos);
    g_click_up = 0; armed = 0;
}

static void InjectKey(const char *args);
static void RunControlFile(IDirect3DDevice9 *dev)
{
    ClickTick();
    wchar_t path[MAX_PATH];
    char line[512];
    FILE *f;
    _snwprintf(path, MAX_PATH, L"%ls\\HydroWater.cmd", g_dir);
    f = _wfopen(path, L"r");
    if (!f) return;
    while (fgets(line, sizeof line, f)) {
        char *e = line + strlen(line);
        while (e > line && (e[-1] == '\n' || e[-1] == '\r' || e[-1] == ' ')) *--e = 0;
        if (!line[0]) continue;
        if (!_strnicmp(line, "shot ", 5)) SaveBackbuffer(dev, line + 5);
        else if (!_strnicmp(line, "chapter ", 8)) ChapterSelect(atoi(line + 8));
        else if (!_stricmp(line, "continue")) ContinueGame();
        else if (!_strnicmp(line, "key ", 4)) InjectKey(line + 4);
        else if (!_strnicmp(line, "click", 5)) InjectClick(line[5] ? line + 6 : "");
        else if (!_stricmp(line, "state")) GameStateLog("now");
        else Log("control: unknown command '%s'", line);
    }
    fclose(f);
    DeleteFileW(path);
}

/* After the intro the engine presents through the implicit swap chain
 * (IDirect3DSwapChain9::Present, slot 3), so that is hooked too. */
typedef HRESULT (WINAPI *SwapPresent_t)(IDirect3DSwapChain9 *, const RECT *, const RECT *, HWND, const RGNDATA *, DWORD);
static SwapPresent_t g_orig_swap_present;
static volatile LONG g_swap_presents;
static HRESULT WINAPI SwapPresentHook(IDirect3DSwapChain9 *self, const RECT *src, const RECT *dst, HWND wnd, const RGNDATA *dirty, DWORD flags)
{
    DWORD now = GetTickCount();
    IDirect3DDevice9 *dev = NULL;
    InterlockedIncrement(&g_swap_presents);
    InterlockedIncrement(&g_presents);
    if (now - g_last_cmd_poll >= 250 && IDirect3DSwapChain9_GetDevice(self, &dev) == D3D_OK) {
        g_last_cmd_poll = now;
        RunControlFile(dev);
        IDirect3DDevice9_Release(dev);
    }
    return g_orig_swap_present(self, src, dst, wnd, dirty, flags);
}

static HRESULT WINAPI PresentHook(IDirect3DDevice9 *self, const RECT *src, const RECT *dst, HWND wnd, const RGNDATA *dirty)
{
    DWORD now = GetTickCount();
    InterlockedIncrement(&g_presents);
    if (now - g_last_cmd_poll >= 250) { g_last_cmd_poll = now; RunControlFile(self); }
    return g_orig_present(self, src, dst, wnd, dirty);
}

static HRESULT WINAPI ResetHook(void *self, HW_D3DPP *pp)
{
    HRESULT hr;
    HWND h = g_game_wnd;
    if (pp && pp->hDeviceWindow) h = pp->hDeviceWindow;
    ForceWindowed(pp, h);
    hr = g_orig_reset(self, pp);
    Log("borderless: Reset -> %08lx", (unsigned long)hr);
    return hr;
}

static HRESULT WINAPI CreateDeviceHook(void *self, UINT adapter, UINT type, HWND focus, DWORD flags, HW_D3DPP *pp, void **dev)
{
    HRESULT hr;
    HWND h = focus;
    if (pp && pp->hDeviceWindow) h = pp->hDeviceWindow;
    if (pp) Log("D3D device requested: %ux%u windowed=%d interval=%08lx swap=%u", pp->BackBufferWidth, pp->BackBufferHeight,
                (int)pp->Windowed, (unsigned long)pp->PresentationInterval, pp->SwapEffect);
    AdoptWindow(h);
    ForceWindowed(pp, h);
    InstallFoam();
    hr = g_orig_create_device(self, adapter, type, focus, flags, pp, dev);
    if (hr == 0 && dev && *dev) {
        if (!g_orig_reset) PatchVtable(*dev, 16, (void *)ResetHook, (void **)&g_orig_reset);
        if (cfg.control && !g_orig_present) {
            PatchVtable(*dev, 17, (void *)PresentHook, (void **)&g_orig_present);
            Log("control: Present hooked (orig %p)", (void *)g_orig_present);
            {
                IDirect3DSwapChain9 *sc = NULL;
                if (IDirect3DDevice9_GetSwapChain((IDirect3DDevice9 *)*dev, 0, &sc) == D3D_OK && sc) {
                    PatchVtable(sc, 3, (void *)SwapPresentHook, (void **)&g_orig_swap_present);
                    Log("control: swap chain Present hooked (orig %p)", (void *)g_orig_swap_present);
                    IDirect3DSwapChain9_Release(sc);
                }
            }
        }
    }
    Log("CreateDevice -> %08lx", (unsigned long)hr);
    return hr;
}

static void InstallWindowHooks(void)
{
    HMODULE d3d;
    Direct3DCreate9_t create = NULL;
    Release_t release;
    void *d3d9 = NULL;
    if (!cfg.borderless && !cfg.background && !cfg.control && !cfg.opts.foam) return;
    d3d = LoadLibraryW(L"d3d9.dll");
    if (d3d) create = (Direct3DCreate9_t)GetProcAddress(d3d, "Direct3DCreate9");
    if (create) d3d9 = create(32);                   /* D3D_SDK_VERSION */
    if (cfg.background) InstallForegroundHooks();
    if (!d3d9) { Log("borderless: Direct3DCreate9 unavailable (%lu)", GetLastError()); return; }
    PatchVtable(d3d9, 16, (void *)CreateDeviceHook, (void **)&g_orig_create_device);
    release = (Release_t)(*(void ***)d3d9)[2];      /* release the probe object; the vtable is shared */
    release(d3d9);
    Log("borderless=%d background=%d: IDirect3D9::CreateDevice hooked (orig %p)", cfg.borderless, cfg.background, (void *)g_orig_create_device);
}

/* ---------------------------------------------------------------- dinput8 forwarding */
static HMODULE g_real;
static FARPROC g_real_create;

static FARPROC hw_resolve_real_dinput(void)
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

/* ---------------------------------------------------------------- DirectInput hooks (background / control)
 * The game reads keyboard and mouse through DirectInput 8. When this proxy hands out the real
 * IDirectInput8, its CreateDevice (slot 3) is patched; on each device, SetCooperativeLevel (13),
 * GetDeviceState (9) and GetDeviceData (10) are patched in the shared device vtable.
 *  - background = 1: devices are opened background/non-exclusive so they are never lost when the
 *    window is not in front (a lost keyboard made the game open its pause menu); real keys are
 *    hidden from the game while another window has the focus.
 *  - control = 1: "key <name|DIK hex> [ms]" in HydroWater.cmd presses a key for the game only. */
typedef HRESULT (WINAPI *DI8Create_t)(HINSTANCE, DWORD, const GUID *, void **, void *);
typedef HRESULT (WINAPI *DICreateDevice_t)(void *, const GUID *, void **, void *);
typedef HRESULT (WINAPI *DISetCoop_t)(void *, HWND, DWORD);
typedef HRESULT (WINAPI *DIGetState_t)(void *, DWORD, void *);
typedef HRESULT (WINAPI *DIGetData_t)(void *, DWORD, BYTE *, DWORD *, DWORD);
static DICreateDevice_t g_orig_di_create;
static DISetCoop_t g_orig_di_coop;
static DIGetState_t g_orig_di_state;
static DIGetData_t g_orig_di_data;
static void *g_kbd;                       /* the game's keyboard device */
static volatile LONG g_di_seen;           /* bit per method, for one-time logging */
static DWORD g_key_until[256];            /* tick until which an injected key is held (0 = up) */
static BYTE g_key_down[256];              /* injected key state already reported as down */
static DWORD g_di_seq = 0x40000000;

static const GUID HW_GUID_SysKeyboard = { 0x6F1D2B61, 0xD5A0, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 } };

static void DISeen(int bit, const char *what)
{
    if (!(InterlockedOr(&g_di_seen, 1 << bit) & (1 << bit))) Log("dinput: game uses %s", what);
}

static int GameHasFocus(void)
{
    HWND fg = g_orig_fg ? g_orig_fg() : GetForegroundWindow();
    return !g_game_wnd || fg == g_game_wnd;
}

static HRESULT WINAPI DISetCoopHook(void *self, HWND h, DWORD flags)
{
    DWORD f = flags;
    if (cfg.background) f = (flags & ~(0x1u | 0x4u)) | 0x2u | 0x8u;   /* EXCLUSIVE|FOREGROUND -> NONEXCLUSIVE|BACKGROUND */
    Log("dinput: SetCooperativeLevel(%p, %p, %lx -> %lx)%s", self, (void *)h, flags, f, self == g_kbd ? " keyboard" : "");
    return g_orig_di_coop(self, h, f);
}

static HRESULT WINAPI DIGetStateHook(void *self, DWORD cb, void *data)
{
    HRESULT hr = g_orig_di_state(self, cb, data);
    if (self != g_kbd || cb != 256 || !data) return hr;
    DISeen(0, "keyboard GetDeviceState");
    {
        BYTE *k = (BYTE *)data;
        DWORD now = GetTickCount();
        int i;
        if (hr != 0 || (cfg.background && !GameHasFocus())) { memset(k, 0, 256); hr = 0; }
        for (i = 0; i < 256; i++) if (g_key_until[i] && (LONG)(g_key_until[i] - now) > 0) k[i] = 0x80;
    }
    return hr;
}

static HRESULT WINAPI DIGetDataHook(void *self, DWORD cbo, BYTE *rgdod, DWORD *inout, DWORD flags)
{
    DWORD room = inout ? *inout : 0, n, now = GetTickCount();
    HRESULT hr = g_orig_di_data(self, cbo, rgdod, inout, flags);
    int i;
    if (self != g_kbd || !inout) return hr;
    DISeen(1, "keyboard GetDeviceData");
    if (hr < 0 || (cfg.background && !GameHasFocus())) { *inout = 0; hr = 0; }
    n = *inout;
    if (!rgdod || (flags & 1) || cbo < 16) return hr;                  /* DIGDD_PEEK or a size query: leave edges queued */
    for (i = 0; i < 256 && n < room; i++) {
        int want = g_key_until[i] && (LONG)(g_key_until[i] - now) > 0;
        if (want != g_key_down[i]) {
            BYTE *e = rgdod + n * cbo;
            memset(e, 0, cbo);
            ((DWORD *)e)[0] = (DWORD)i;                 /* dwOfs = DIK code */
            ((DWORD *)e)[1] = want ? 0x80 : 0;          /* dwData */
            ((DWORD *)e)[2] = now;                      /* dwTimeStamp */
            ((DWORD *)e)[3] = g_di_seq++;               /* dwSequence */
            g_key_down[i] = (BYTE)want;
            if (!want) g_key_until[i] = 0;
            n++;
        }
    }
    *inout = n;
    return hr;
}

static HRESULT WINAPI DICreateDeviceHook(void *self, const GUID *g, void **dev, void *outer)
{
    HRESULT hr = g_orig_di_create(self, g, dev, outer);
    if (hr == 0 && dev && *dev) {
        int kbd = g && !memcmp(g, &HW_GUID_SysKeyboard, sizeof(GUID));
        if (kbd) g_kbd = *dev;
        Log("dinput: CreateDevice %08lx-... -> %p%s", g ? g->Data1 : 0, *dev, kbd ? " (keyboard)" : "");
        if (!g_orig_di_coop) PatchVtable(*dev, 13, (void *)DISetCoopHook, (void **)&g_orig_di_coop);
        if (!g_orig_di_state) PatchVtable(*dev, 9, (void *)DIGetStateHook, (void **)&g_orig_di_state);
        if (!g_orig_di_data) PatchVtable(*dev, 10, (void *)DIGetDataHook, (void **)&g_orig_di_data);
    }
    return hr;
}

/* key names for the control file; anything else is read as a DIK hex code */
static int DikFromName(const char *s)
{
    static const struct { const char *n; int k; } T[] = {
        { "esc", 0x01 }, { "enter", 0x1C }, { "space", 0x39 }, { "tab", 0x0F }, { "backspace", 0x0E },
        { "w", 0x11 }, { "a", 0x1E }, { "s", 0x1F }, { "d", 0x20 }, { "e", 0x12 }, { "q", 0x10 }, { "f", 0x21 },
        { "r", 0x13 }, { "c", 0x2E }, { "lshift", 0x2A }, { "lctrl", 0x1D },
        { "up", 0xC8 }, { "down", 0xD0 }, { "left", 0xCB }, { "right", 0xCD } };
    int i;
    for (i = 0; i < (int)(sizeof T / sizeof T[0]); i++) if (!_stricmp(s, T[i].n)) return T[i].k;
    return (int)strtol(s, NULL, 16) & 0xFF;
}

static void InjectKey(const char *args)
{
    char name[32] = { 0 };
    int ms = 120, k;
    if (sscanf(args, "%31s %d", name, &ms) < 1) return;
    k = DikFromName(name);
    if (!k) { Log("control: key '%s' unknown", name); return; }
    if (ms < 30) ms = 30;
    g_key_until[k] = GetTickCount() + (DWORD)ms;
    if (!g_key_until[k]) g_key_until[k] = 1;
    Log("control: key %s (DIK %02x) for %d ms%s", name, k, ms, g_kbd ? "" : " (no keyboard device yet)");
}

static HRESULT WINAPI MyDirectInput8Create(HINSTANCE inst, DWORD ver, const GUID *riid, void **out, void *outer)
{
    DI8Create_t real = (DI8Create_t)hw_resolve_real_dinput();
    HRESULT hr = real ? real(inst, ver, riid, out, outer) : E_FAIL;
    if (hr == 0 && out && *out && (cfg.background || cfg.control) && !g_orig_di_create) {
        PatchVtable(*out, 3, (void *)DICreateDeviceHook, (void **)&g_orig_di_create);
        Log("dinput: IDirectInput8::CreateDevice hooked (background=%d control=%d)", cfg.background, cfg.control);
    }
    return hr;
}

__attribute__((used)) FARPROC hw_resolve_dinput(void)
{
    return hw_resolve_real_dinput() ? (FARPROC)MyDirectInput8Create : NULL;
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
