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
    float foam_p[10];   /* foam_gain air_gain foam_life lace bubble_rise air_to_foam spread spray_rate dye_gain dye_life; < 0 = library default */
    int foam_test;      /* 1 = paint moving foam bands instead of the simulated foam (to see the look) */
    float foam_strength; /* how strongly thin foam and air show: 0 = linear (the field as is), 2 = default */
    int foam_tex;       /* 1 = foam also from a world-space texture filled from every sheet, so unrebuilt sheets show it */
    float depth_colour; /* how strongly deep water is tinted (light lost to depth): 0 = off, 1 = default */
    float depth_scale;  /* depth (world units) at which the tint is about two thirds of full */
    float foam_streaks; /* how strongly foam is drawn as streaks along the flow: 0 = off, 1 = default */
    float streak_speed; /* flow speed (world units/s) at which streaks are about two thirds of full */
    float ripples;      /* strength of the ripples carried along by the flow: 0 = off, 1 = default */
    float dye;          /* how strongly the dye carried by the flow tints the water: 0 = off, 1 = default */
    float dye_colour[3]; /* its colour (murky silt by default) */
    float crest_glow;   /* light through the thin tops of waves (Sea of Thieves): 0 = off, 1 = default */
    float crest_height; /* how far (world units) a crest stands above its neighbours to glow about two thirds of full */
    float wake;         /* V wake behind Kate (Kelvin angle arms of foam): 0 = off, 1 = default */
    float wake_length;  /* length (world units) of each arm at full speed */
    float splotch;      /* big slow patches that break up wide thin foam: 0 = off, 1 = default */
    float foam_normals; /* foam lit as if raised (Crest's foam-gradient normals): 0 = off, 1 = default, at most 2 */
    float wet;          /* surfaces the water left stay darker and glossier, then dry: 0 = off, 1 = default, at most 1.5 */
    float wet_dry;      /* how fast (world units a second) the high-water mark sinks as things dry */
    float drench;       /* Kate just out of the water: wet skin sheen, soaked cloth, running water, drips */
    float drench_splash; /* how much of her the spray wets in patches when she runs through shallow water (0..1) */
    float drench_mask;  /* 1 = soak only where the game's own wetness mask (spec map .z) allows, 0 = everywhere, 2 = show the mask in red */
} cfg = { MODE_HW, { 0, 0, 0, 1, 1.0f, 0.2f, 0.7f, 1, 1 }, 600, 4096, 1, 0, 0, 0, { -1, -1, -1, -1, -1, -1, -1, 0, -1, -1 }, 0, 2.0f, 1, 1.0f, 150.0f, 1.0f, 120.0f, 1.0f, 1.0f, { 0.30f, 0.25f, 0.16f }, 1.0f, 3.0f, 1.0f, 160.0f, 1.0f, 1.0f, 1.0f, 1.5f, 1.0f, 1.0f, 1.0f };
static const char *const FOAM_KEYS[10] = { "foam_gain", "air_gain", "foam_life", "lace", "bubble_rise", "air_to_foam", "spread", "spray_rate", "dye_gain", "dye_life" };

static wchar_t g_dir[MAX_PATH];     /* folder of this DLL */
static volatile LONG g_presents;    /* frames seen by the EndScene hook */

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
        else if (!_stricmp(k, "foam_test")) cfg.foam_test = atoi(v);
        else if (!_stricmp(k, "foam_tex")) cfg.foam_tex = atoi(v);
        else if (!_stricmp(k, "foam_strength")) cfg.foam_strength = (float)atof(v);
        else if (!_stricmp(k, "depth_colour")) cfg.depth_colour = (float)atof(v);
        else if (!_stricmp(k, "depth_scale")) cfg.depth_scale = (float)atof(v);
        else if (!_stricmp(k, "foam_streaks")) cfg.foam_streaks = (float)atof(v);
        else if (!_stricmp(k, "streak_speed")) cfg.streak_speed = (float)atof(v);
        else if (!_stricmp(k, "ripples")) cfg.ripples = (float)atof(v);
        else if (!_stricmp(k, "dye")) cfg.dye = (float)atof(v);
        else if (!_stricmp(k, "crest_glow")) cfg.crest_glow = (float)atof(v);
        else if (!_stricmp(k, "crest_height")) cfg.crest_height = (float)atof(v);
        else if (!_stricmp(k, "wake")) cfg.wake = (float)atof(v);
        else if (!_stricmp(k, "wake_length")) cfg.wake_length = (float)atof(v);
        else if (!_stricmp(k, "splotch")) cfg.splotch = (float)atof(v);
        else if (!_stricmp(k, "foam_normals")) cfg.foam_normals = (float)atof(v);
        else if (!_stricmp(k, "wet")) cfg.wet = (float)atof(v);
        else if (!_stricmp(k, "wet_dry")) cfg.wet_dry = (float)atof(v);
        else if (!_stricmp(k, "drench")) cfg.drench = (float)atof(v);
        else if (!_stricmp(k, "drench_splash")) cfg.drench_splash = (float)atof(v);
        else if (!_stricmp(k, "drench_mask")) cfg.drench_mask = (float)atof(v);
        else if (!_stricmp(k, "dye_colour")) sscanf(v, "%f %f %f", &cfg.dye_colour[0], &cfg.dye_colour[1], &cfg.dye_colour[2]);
        else {
            int n;
            for (n = 0; n < 10; n++) if (!_stricmp(k, FOAM_KEYS[n])) cfg.foam_p[n] = (float)atof(v);
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
    BYTE *foam, *air, *depth;   /* w*h each, cell (i,j) at j*w+i; depth is the tint amount (depth_colour, depth_scale) */
    BYTE *flowu, *flowv;        /* w*h each: flow direction times streak amount, 128 + 127 x (-1..1) */
    BYTE *dye;                  /* w*h: the dye carried by the flow (world texture alpha only; the mesh has no free channel) */
    BYTE *crest;                /* w*h: crest glow, how far the surface stands above its neighbours (world texture only) */
    float *surf;                /* w*h: water surface height (bed + depth, the sheet's up axis), -1e30 where dry */
    float fmax;         /* largest shown foam since the last stats line (0..1, after foam_strength) */
    unsigned fcells;    /* cell-steps with shown foam above 0.1 since the last stats line */
    float ox, oy, dx;   /* world position of cell (0,0) and cell size, copied each step (the sheet may be freed on a level change) */
    volatile DWORD tick; /* GetTickCount of the last step that filled it */
} foam_snap;

/* Kate: the game keeps its CPlayerPawn (vtable 0xe910f4) in the global at 0x1a817a4 (326 code
 * references); pawn +0x2c/+0x30 is her position in the sheet plane, +0x34 her height. The game
 * stamps her only into some sheets, and her wake on the pool is drawn, not simulated. */
#define PLAYER_PTR   0x1a817a4u
#define PAWN_VTABLE  0xe910f4u

static const float *KatePos(void)
{
    const uint32_t *pawn;
    if (IsBadReadPtr((const void *)PLAYER_PTR, 4)) return NULL;
    pawn = *(const uint32_t *const *)PLAYER_PTR;
    if (!pawn || IsBadReadPtr(pawn, 0x40) || pawn[0] != PAWN_VTABLE) return NULL;
    return (const float *)((const BYTE *)pawn + 0x2c);
}

typedef struct bridge {
    uint32_t *S;        /* the game's sheet */
    int w, h;
    hw_sheet *hw;
    unsigned steps;
    float dm, du, dh;   /* largest outside change of momentum, velocity grid and depth since the last stats line */
    float kx, kz;       /* where Kate was at this sheet's last step */
    int kseen;
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
            foam_snap *sn = (foam_snap *)calloc(1, sizeof *sn + (size_t)w * h * (7 + sizeof(float)));
            hw_get_foam_params(b->hw, &fp);
            for (n = 0; n < 7; n++) if (cfg.foam_p[n] >= 0.0f) f[n] = cfg.foam_p[n];
            if (cfg.foam_p[7] >= 0.0f) fp.spray_rate = cfg.foam_p[7];   /* drops aren't drawn in the game yet: 0 by default */
            if (cfg.foam_p[8] >= 0.0f) fp.dye_gain = cfg.foam_p[8];
            if (cfg.foam_p[9] >= 0.0f) fp.dye_life = cfg.foam_p[9];
            hw_set_foam_params(b->hw, &fp);
            if (sn) { sn->w = w; sn->h = h; sn->surf = (float *)(sn + 1); sn->foam = (BYTE *)(sn->surf + (size_t)w * h); sn->air = sn->foam + (size_t)w * h; sn->depth = sn->air + (size_t)w * h; sn->flowu = sn->depth + (size_t)w * h; sn->flowv = sn->flowu + (size_t)w * h; sn->dye = sn->flowv + (size_t)w * h; sn->crest = sn->dye + (size_t)w * h; }
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

/* mesh hook diagnostics: rebuilds seen, no bridge/snap for the sheet, size mismatch, sheets coloured */
static volatile LONG g_mesh_calls, g_mesh_nobridge, g_mesh_badsize, g_mesh_sheets;
static const uint32_t *g_mesh_seen[256];
static volatile LONG g_shader_calls, g_shader_water_noanchor;
static volatile LONG g_foam_patched, g_foam_failed, g_foam_dumps, g_wet_patched;
static volatile LONG g_body_foam;   /* steps where a moving body added foam, since the last stats line */
static float g_body_vmax;           /* Kate's top speed over any sheet since the last stats line */
static float g_kate_h, g_kate_bed, g_kate_depth;   /* her height and the bed and depth under her at the last foam add */

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
        !S[0x14] || !S[0x15] || !S[0x19] || !(dt > 0.0f)) {
        static uint32_t *seen[32]; static volatile LONG nseen;
        int q, n = (int)nseen, known = 0;
        for (q = 0; q < n && q < 32; q++) if (seen[q] == S) known = 1;
        if (!known && n < 32) {
            seen[InterlockedIncrement(&nseen) - 1] = S;
            Log("sheet %p left to the game's solver: %d x %d, flat %u, buffer %u, origin %.0f %.0f", (void *)S, w, h, S[0x6b], S[0],
                *(const float *)&S[0x1f], *(const float *)&S[0x20]);
        }
        return CallOrig(S, dt);
    }

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
    /* the game stamped walking, swimming and falling bodies into its momentum since our last
       step: that change is a foam source (skipped on the first step, nothing to compare) */
    if (cfg.opts.foam && b->steps > 0) {
        const float *pu = hw_u(b->hw), *pv = hw_v(b->hw);
        int jj, ii;
        hw_foam_stir(b->hw, ghu, ghv, gs);
        for (jj = 2; jj < rows - 2; jj++)
            for (ii = 2; ii < cols - 2; ii++) {
                int e = jj * gs + ii, q = jj * hs + ii;
                float d = fabsf(ghu[e] - hhu[q]) + fabsf(ghv[e] - hhv[q]);
                if (d > b->dm) b->dm = d;
                d = fabsf(((const float *)S[0x14])[e] - pu[q]) + fabsf(((const float *)S[0x12])[e] - pv[q]);
                if (d > b->du) b->du = d;
                d = fabsf(gh[e] - hh[q]);
                if (d > b->dh) b->dh = d;
            }
    }
    CopyPlane(hh, hs, gh, gs, rows, cols);
    CopyPlane(hhu, hs, ghu, gs, rows, cols);
    CopyPlane(hhv, hs, ghv, gs, rows, cols);
    CopyPlane(hbed, hs, gbed, gs, rows, cols);
    for (r = 0; r < rows; r++)
        for (i = 0; i < cols; i++)   /* the 2-cell padding ring stays wall so nothing leaks off the sheet */
            hwall[r * hs + i] = (gwall[r * gs + i] != 0.0f || r < 2 || r >= rows - 2 || i < 2 || i >= cols - 2) ? 1.0f : 0.0f;

    /* bodies moving through the water churn foam around them: the game stamps them only into
       some sheets, and their wake on the pool is drawn, not simulated */
    if (cfg.opts.foam) {
        const float *kp = KatePos();
        float ox = *(const float *)&S[0x1f], oz = *(const float *)&S[0x20], dxs = *(const float *)&S[4], rad = 2.0f * dxs;
        if (!kp || kp[0] < ox - rad || kp[1] < oz - rad || kp[0] > ox + w * dxs + rad || kp[1] > oz + h * dxs + rad) b->kseen = 0;
        else {
            float x = kp[0], z = kp[1];
            int ci = (int)((x - ox) / dxs) + 2, cj = (int)((z - oz) / dxs) + 2;
            /* her height is negated against bed + depth (wading: -710 over bed 610, depth 110);
               on a grating more than 80 above the surface she makes no foam */
            int above = ci >= 2 && cj >= 2 && ci < w + 2 && cj < h + 2 && -kp[2] > gbed[cj * gs + ci] + gh[cj * gs + ci] + 80.0f;
            if (b->kseen && !above) {
                float vx = x - b->kx, vz = z - b->kz, v = sqrtf(vx * vx + vz * vz) / dt;
                if (v > g_body_vmax) g_body_vmax = v;
                if (v > 20.0f && v < 3000.0f) {   /* a jump in position is a respawn, not a wake */
                    float a = (v - 20.0f) / 250.0f;
                    if (a > 1.0f) a = 1.0f;
                    /* foam_add skips dry cells, so walking on a floor over the sheet adds nothing */
                    hw_foam_add(b->hw, x - ox, z - oz, rad, 3.0f * a * dt, 2.0f * a * dt);
                    hw_dye_add(b->hw, x - ox, z - oz, rad, 0.8f * a * dt);   /* silt kicked up by her feet */
                    /* a thinner trail a little behind, so the wake is a streak, not a disc */
                    hw_foam_add(b->hw, x - ox - vx * 0.5f, z - oz - vz * 0.5f, rad * 1.3f, 1.5f * a * dt, 0.5f * a * dt);
                    if (cfg.wake > 0.0f && cfg.wake_length > 0.0f) {
                        /* V wake: two arms trailing at the Kelvin angle (19.5 degrees each side of her
                           heading), longer the faster she goes, thinning toward the tips; each frame's
                           stamps stay where they land and fade, so the V follows her */
                        float bx = -vx / (v * dt), bz = -vz / (v * dt), len = cfg.wake_length * (0.4f + 0.6f * a);
                        float wg = cfg.wake > 1.0f ? 1.0f : cfg.wake;
                        int k, sd;
                        for (sd = -1; sd <= 1; sd += 2) {
                            float ax = 0.9428f * bx - sd * 0.3333f * bz, az = 0.9428f * bz + sd * 0.3333f * bx;
                            for (k = 1; k <= 5; k++) {
                                float d = len * k * 0.2f, t = 1.0f - 0.15f * k;
                                hw_foam_add(b->hw, x - ox + ax * d, z - oz + az * d, rad * (0.5f + 0.1f * k),
                                            1.2f * wg * a * t * dt, 0.3f * wg * a * t * dt);
                            }
                        }
                    }
                    g_body_foam++;
                    g_kate_h = kp[2];
                    if (ci >= 2 && cj >= 2 && ci < w + 2 && cj < h + 2) { g_kate_bed = gbed[cj * gs + ci]; g_kate_depth = gh[cj * gs + ci]; }
                }
            }
            b->kx = x; b->kz = z; b->kseen = 1;
        }
    }
    if (cfg.opts.displacement) hw_bodies_begin(b->hw);   /* no bodies registered yet (stage 1 hook pending) */
    hw_step(b->hw, dt);
    if (cfg.opts.foam && b->snap) {
        foam_snap *sn = b->snap;
        const float *pf = hw_foam(b->hw), *pa = hw_air(b->hw);
        /* thin foam is most of the field; a soft curve lifts it so the lace shows: 1 - exp(-k f),
           scaled to reach 1 at f = 1 */
        float k = 3.0f * cfg.foam_strength, kn = k > 0.01f ? 1.0f / (1.0f - expf(-k)) : 0.0f;
        float dk = cfg.depth_scale > 1.0f ? 1.0f / cfg.depth_scale : 0.0f, dc = cfg.depth_colour > 1.0f ? 1.0f : cfg.depth_colour;
        const float *pd = hw_depth(b->hw), *pu = hw_u(b->hw), *pv = hw_v(b->hw), *py = hw_dye(b->hw), *pb = hw_bed(b->hw);
        float ck = cfg.crest_glow > 0.0f && cfg.crest_height > 0.01f ? 1.0f / cfg.crest_height : 0.0f, cg = cfg.crest_glow > 1.0f ? 1.0f : cfg.crest_glow;
        float sk = cfg.streak_speed > 1.0f ? 1.0f / cfg.streak_speed : 0.0f, sc = cfg.foam_streaks > 1.0f ? 1.0f : cfg.foam_streaks;
        int j;
        for (j = 0; j < h; j++)
            for (i = 0; i < w; i++) {
                float f = pf[(j + 2) * hs + i + 2], a = pa[(j + 2) * hs + i + 2];
                if (cfg.foam_test) {   /* diagonal bands drifting across the sheet, thin to thick */
                    f = 0.5f + 0.5f * sinf((float)(i + j) * 0.5f - (float)b->steps * 0.05f);
                    f = f * f; a = f * 0.6f;
                }
                if (kn > 0.0f) {
                    f = f > 0.0f ? (1.0f - expf(-k * f)) * kn : 0.0f;
                    a = a > 0.0f ? (1.0f - expf(-k * a)) * kn : 0.0f;
                }
                if (f > sn->fmax) sn->fmax = f;
                if (f > 0.1f) sn->fcells++;
                sn->foam[j * w + i] = (BYTE)(f <= 0.0f ? 0 : f >= 1.0f ? 255 : (int)(f * 255.0f + 0.5f));
                sn->air[j * w + i] = (BYTE)(a <= 0.0f ? 0 : a >= 1.0f ? 255 : (int)(a * 255.0f + 0.5f));
                {   /* deep water: 1 - exp(-depth / depth_scale), times depth_colour */
                    float d = pd[(j + 2) * hs + i + 2];
                    d = d > 0.0f && dc > 0.0f ? dc * (1.0f - expf(-d * dk)) : 0.0f;
                    sn->depth[j * w + i] = (BYTE)(d >= 1.0f ? 255 : (int)(d * 255.0f + 0.5f));
                }
                {   /* flow direction for the foam streaks, scaled by 1 - exp(-speed / streak_speed) */
                    float u = pu[(j + 2) * hs + i + 2], v = pv[(j + 2) * hs + i + 2], sp = sqrtf(u * u + v * v), m = 0.0f;
                    if (sp > 1e-3f && sc > 0.0f && sk > 0.0f) m = sc * (1.0f - expf(-sp * sk)) / sp;
                    sn->flowu[j * w + i] = (BYTE)(128 + (int)(127.0f * u * m));
                    sn->flowv[j * w + i] = (BYTE)(128 + (int)(127.0f * v * m));
                }
                {   float y = py[(j + 2) * hs + i + 2];
                    sn->dye[j * w + i] = (BYTE)(y <= 0.0f ? 0 : y >= 1.0f ? 255 : (int)(y * 255.0f + 0.5f)); }
                {   int c = (j + 2) * hs + i + 2;
                    sn->surf[j * w + i] = pd[c] > 0.5f ? pd[c] + pb[c] : -1e30f; }
                {   /* crest glow: the surface above the mean of its wet neighbours, 1 - exp(-bump / crest_height) */
                    int c = (j + 2) * hs + i + 2, nb[4], q, nw = 0;
                    float e = 0.0f, g = 0.0f;
                    nb[0] = c - 1; nb[1] = c + 1; nb[2] = c - hs; nb[3] = c + hs;
                    if (ck > 0.0f && pd[c] > 1.0f) {
                        for (q = 0; q < 4; q++) if (pd[nb[q]] > 1.0f) { e += pd[nb[q]] + pb[nb[q]]; nw++; }
                        if (nw >= 3) { e = pd[c] + pb[c] - e / (float)nw; if (e > 0.0f) g = cg * (1.0f - expf(-e * ck)); }
                    }
                    sn->crest[j * w + i] = (BYTE)(g >= 1.0f ? 255 : (int)(g * 255.0f + 0.5f));
                }
            }
        sn->ox = *(const float *)&S[0x1f]; sn->oy = *(const float *)&S[0x20]; sn->dx = *(const float *)&S[4];
        sn->tick = GetTickCount();
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
    {
        Log("sheet %p: step %u dt %.4f volume %.1f smax %.1f (presents %ld) [+60 %x +f8 %x +6c %x]", (void *)S, b->steps, dt, hw_volume(b->hw), hw_smax(b->hw), g_presents, S[0x18], S[0x3e], S[0x1b]);
        if (b->snap) {
            Log("sheet %p: foam max %.2f, %.1f cells above 0.1 per step; outside change: momentum %.1f, velocity %.1f, depth %.2f", (void *)S, b->snap->fmax, b->snap->fcells / (float)cfg.log_every, b->dm, b->du, b->dh);
            b->dm = b->du = b->dh = 0.0f;
            b->snap->fmax = 0.0f; b->snap->fcells = 0;
        }
        {   /* the body table, once per stats round (the first sheet to log prints it) */
            static DWORD last;
            DWORD now = GetTickCount();
            if (now - last > 5000) {
                const float *kp = KatePos();
                last = now;
                if (kp) Log("kate: at %.0f %.0f height %.0f; %ld foam adds, top speed over water %.0f (last add: bed %.0f depth %.1f height %.0f)",
                            kp[0], kp[1], kp[2], g_body_foam, g_body_vmax, g_kate_bed, g_kate_depth, g_kate_h);
                else Log("kate: no player pawn");
                g_body_foam = 0; g_body_vmax = 0.0f;
            }
        }
        Log("mesh hook: %ld rebuilds, %ld no bridge, %ld size mismatch, %ld sheets coloured; shaders %ld compiled, %ld patched, %ld water-like without anchor",
            g_mesh_calls, g_mesh_nobridge, g_mesh_badsize, g_mesh_sheets, g_shader_calls, g_foam_patched, g_shader_water_noanchor);
    }
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
 * the job in ESI; that call is pointed at MeshStub, which writes foam into red, air into green and
 * depth into blue (as 255 - value, so an untouched white vertex means none) and then jumps on to the unlock. The
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
    InterlockedIncrement(&g_mesh_calls);
    b = Lookup(S);
    w = (int)S[1]; h = (int)S[3];
    if (!b || !(sn = b->snap)) {
        if (InterlockedIncrement(&g_mesh_nobridge) <= 3) Log("foam: mesh for sheet %p (%d x %d) has no bridge", (void *)S, w, h);
        return;
    }
    if (w != sn->w || h != sn->h) {
        if (InterlockedIncrement(&g_mesh_badsize) <= 3) Log("foam: mesh for sheet %p is %d x %d, snap %d x %d", (void *)S, w, h, sn->w, sn->h);
        return;
    }
    for (i = 0; i < 256 && g_mesh_seen[i] && g_mesh_seen[i] != S; i++) ;
    if (i < 256 && !g_mesh_seen[i]) {
        g_mesh_seen[i] = S;   /* render jobs may race; a duplicate entry only inflates the count */
        if (InterlockedIncrement(&g_mesh_sheets) <= 8) Log("foam: colouring sheet %p (%d x %d)", (void *)S, w, h);
    }
    for (j = 0; j <= h; j++) {
        cj = j < h ? j : h - 1;
        row = vb + (size_t)j * (w + 1) * 36;
        for (i = 0; i <= w; i++) {
            ci = i < w ? i : w - 1;
            row[i * 36 + 34] = (BYTE)(255 - sn->foam[cj * w + ci]);   /* R */
            row[i * 36 + 33] = (BYTE)(255 - sn->air[cj * w + ci]);    /* G */
            row[i * 36 + 32] = (BYTE)(255 - sn->depth[cj * w + ci]);  /* B */
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
 * of the water's reflect/refract pixel code (FOAM_ANCHOR) and adds the foam after it: a lace
 * web of value noise on the world position sets a threshold that the foam the mesh carries in
 * red pushes past, giving opaque bright foam with crisp edges over the water, lit from the
 * scene, and slightly lighter water where green says there is air. If the patched text fails to compile, the original is compiled instead.
 * Compiled shaders are cached in shaderCacheDX.bin, which would keep the unpatched water; with
 * foam on, the exe's file name string is changed to shaderCacheXY.bin (same length) before the
 * cache is opened, so the game's own cache stays untouched and a second one is built. XY is a hash
 * of every bit of HLSL the mod adds (and of the switches that decide what gets added), so a new
 * build or a changed ini never picks up shaders compiled from older text. */
#define VA_SHADER_CACHE_NAME 0xeaf830u
static const char CACHE_NAME_GAME[] __attribute__((unused)) = "shaderCacheDX.bin";
static char CACHE_NAME_HW[] = "shaderCacheHW.bin";   /* the two letters after "shaderCache" are set by PatchCacheName */
static const char FOAM_ANCHOR[] = "reflectionColour = vReflectionSample * fFresRefl.xxxx;";
static const char FOAM_DEFS[] =
    "\n#ifndef HW_VN\n"
    "#define HW_H(q) frac(sin(dot((q), float2(127.1f, 311.7f))) * 43758.5453f)\n"
    "#define HW_VN(p) lerp(lerp(HW_H(floor(p)), HW_H(floor(p) + float2(1.0f, 0.0f)), smoothstep(0.0f, 1.0f, frac(p).x)), "
    "lerp(HW_H(floor(p) + float2(0.0f, 1.0f)), HW_H(floor(p) + float2(1.0f, 1.0f)), smoothstep(0.0f, 1.0f, frac(p).x)), smoothstep(0.0f, 1.0f, frac(p).y))\n"
    "#endif\n";
static const char FOAM_HLSL[] =
    "{ /* HydroWater foam: foam toned to the scene laid over the water with crisp feathered edges (the threshold\n"
    "     idea of Crest, MIT), no grey tint on what is seen through it; aerated water a little lighter;\n"
    "     deep water (blue) loses red first, then green, and fills with the water colour; foam drawn as streaks along the flow; wave crests glow green-blue; foam lit as if raised */\n"
    "  float hwF = saturate(1.0f - vertexColour.r);\n"
    "  float hwD = saturate(1.0f - vertexColour.b);\n"
    "  float2 hwV = float2(0.0f, 0.0f);\n"
    "  float hwDy = 0.0f;\n"
    "  float hwCr = 0.0f;\n"
    "  float hwSp = 0.0f;\n"
    "  float hwFn = 0.0f;\n"
    "  float2 hwG = float2(0.0f, 0.0f);\n"
    "  float3 hwDyC = float3(0.0f, 0.0f, 0.0f);\n"
    "  float hwA = saturate(1.0f - vertexColour.g);\n"
    "  float2 hwP = vertexPosition.xy * (1.0f / 34.0f);\n"
    "  float hwN1 = HW_VN(hwP);\n"
    "  float hwS = saturate(length(hwV));\n"
    "  if (hwS > 0.05f) { /* streaks: the lace stretched 5x along four fixed axes, weighted toward the flow */\n"
    "    float2 hwDn = hwV / length(hwV);\n"
    "    float4 hwW = float4(hwDn.x, 0.7071f * (hwDn.x + hwDn.y), hwDn.y, 0.7071f * (hwDn.y - hwDn.x));\n"
    "    hwW *= hwW; hwW *= hwW; hwW /= dot(hwW, float4(1.0f, 1.0f, 1.0f, 1.0f));\n"
    "    float hwSt = hwW.x * HW_VN(float2(hwP.x * 0.2f, hwP.y * 1.4f))\n"
    "      + hwW.y * HW_VN(float2((hwP.x + hwP.y) * 0.1414f, (hwP.y - hwP.x) * 0.99f) + float2(31.0f, 7.0f))\n"
    "      + hwW.z * HW_VN(float2(hwP.y * 0.2f, hwP.x * 1.4f) + float2(3.0f, 41.0f))\n"
    "      + hwW.w * HW_VN(float2((hwP.y - hwP.x) * 0.1414f, (hwP.x + hwP.y) * 0.99f) + float2(57.0f, 13.0f));\n"
    "    hwN1 = lerp(hwN1, saturate((hwSt - 0.5f) * 1.25f + 0.5f), hwS);\n"
    "  }\n"
    "  float hwN2 = HW_VN(hwP * 2.7f + float2(17.0f, 5.0f));\n"
    "  float hwLace = saturate(0.65f * (1.0f - abs(hwN1 - 0.5f) * 2.0f) + 0.35f * hwN2);\n"
    "  if (hwSp > 0.0f) { /* splotch mask: big slow patches thin the lace so wide foam fields are not even;\n"
    "     thick foam (F above 0.6) is left whole */\n"
    "    float hwM = smoothstep(0.2f, 0.7f, HW_VN(hwP * 0.11f + float2(71.0f, 23.0f)));\n"
    "    hwF *= lerp(1.0f, 0.3f + 0.7f * hwM, hwSp * (1.0f - saturate((hwF - 0.6f) * 2.5f)));\n"
    "  }\n"
    "  /* coverage: foam where F is above the lace threshold, a soft band, holes kept even in thick foam;\n"
    "     opacity at most 0.88 so the water still shows through */\n"
    "  float hwTh = 1.0f - hwLace;\n"
    "  float hwCov = smoothstep(hwTh - 0.14f, hwTh + 0.14f, hwF * 0.97f) * saturate(hwF * 6.0f);\n"
    "  hwCov *= 0.55f + 0.33f * saturate(hwF);\n"
    "  float hwLum = dot(vRefractionSample.rgb + vReflectionSample.rgb, float3(0.299f, 0.587f, 0.114f));\n"
    "  float hwLit = clamp(0.45f + 0.9f * hwLum, 0.45f, 1.15f);\n"
    "  float3 hwTr = exp(-float3(2.0f, 0.85f, 0.65f) * hwD);\n"
    "  float3 hwDeep = lerp(float3(0.03f, 0.10f, 0.10f), vFogColour.rgb * 0.5f, 0.3f) * saturate(0.25f + 0.75f * hwLum);\n"
    "  refractionColour.rgb = refractionColour.rgb * hwTr + hwDeep * (1.0f - hwTr.g) * fFresRefr;\n"
    "  refractionColour.rgb = lerp(refractionColour.rgb, hwDyC * hwLit * fFresRefr, saturate(hwDy) * 0.8f);\n"
    "  /* crest glow: light through the thin top of a wave, a green-blue lift, more where the water is shallow */\n"
    "  refractionColour.rgb += float3(0.07f, 0.40f, 0.34f) * (hwCr * hwLit * fFresRefr * (0.55f + 0.45f * hwTr.g));\n"
    "  float3 hwFoam = lerp(float3(0.95f, 0.97f, 1.0f), vFogColour.rgb, 0.12f) * (hwLit * 0.5f) * (0.8f + 0.2f * hwN2);\n"
    "  if (hwFn > 0.0f) { /* foam normals (Crest, MIT): the foam stands up as a height, so its edges catch and lose light */\n"
    "    float2 hwPl = hwP * 2.7f + float2(17.0f, 5.0f);\n"
    "    float2 hwGl = float2(HW_VN(hwPl + float2(0.25f, 0.0f)) - hwN2, HW_VN(hwPl + float2(0.0f, 0.25f)) - hwN2) * (2.7f / (34.0f * 0.25f));\n"
    "    float2 hwSf = -(hwG * 10.0f + hwGl * 1.5f * hwCov) * hwFn;\n"
    "    float3 hwNf = normalize(float3(hwSf, 1.0f));\n"
    "    hwFoam *= clamp(dot(hwNf, float3(0.36f, 0.48f, 0.8f)) * 1.2f, 0.6f, 1.15f);\n"
    "    refractionColour.rgb *= 1.0f - 0.15f * saturate(length(hwG) * 10.0f * hwFn) * (1.0f - hwCov);\n"
    "  }\n"
    "  refractionColour.rgb = lerp(refractionColour.rgb, refractionColour.rgb * 0.8f + float3(0.06f, 0.11f, 0.11f) * hwLit, hwA * 0.5f);\n"
    "  refractionColour.rgb = lerp(refractionColour.rgb, hwFoam, hwCov);\n"
    "  reflectionColour *= 1.0f - 0.9f * hwCov;\n"
    "  specularStrength *= 1.0f - hwCov;\n"
    "  diffuseMapSample.a = max(diffuseMapSample.a, hwCov * 0.95f);\n"
    "}\n";

typedef HRESULT (WINAPI *Compile_t)(const char *, UINT, const void *, void *, const char *, const char *, DWORD, void **, void **, void **);
static Compile_t g_orig_compile;

static const char *FindN(const char *s, size_t n, const char *pat, size_t m)
{
    size_t i;
    if (m > n) return NULL;
    for (i = 0; i + m <= n; i++) if (s[i] == pat[0] && !memcmp(s + i, pat, m)) return s + i;
    return NULL;
}

/* src (len bytes, not necessarily terminated) with the foam inserted after every anchor, NULL
   when there is no anchor. The caller frees the result. */
/* foam_test 2: the shader draws world-space bands itself, ignoring the vertex colour, to tell a
   mesh that never gets our colours from a surface that doesn't use the patched shader */
static const char FOAM_F_LINE[] = "  float hwF = saturate(1.0f - vertexColour.r);\n";
static const char FOAM_F_TEST[] = "  float hwF = pow(0.5f + 0.5f * sin((vertexPosition.x + vertexPosition.y) * 0.02f), 2.0f);\n";
static const char FOAM_A_LINE[] = "  float hwA = saturate(1.0f - vertexColour.g);\n";
/* the world foam texture (see FoamTex below): sampler s15, mapping in c223 = (x0, y0, 1/width, 1/height) */
/* c222 = (seconds, ripple strength, crest glow on, splotch strength), c221 = (dye colour, dye strength),
   c220 = (foam normals strength, 0, 0, 0) */
static const char FOAM_TEX_GLOBALS[] = "sampler2D hwFoamTex : register(s15);\nfloat4 hwFoamXf : register(c223);\nfloat4 hwTime : register(c222);\nfloat4 hwDyeCol : register(c221);\nfloat4 hwFx : register(c220);\n";
static const char FOAM_TEX_LINE[] =
    "  float2 hwU = (vertexPosition.xy - hwFoamXf.xy) * hwFoamXf.zw;\n"
    "  float4 hwT = tex2Dlod(hwFoamTex, float4(hwU.x * 0.5f, hwU.y, 0.0f, 0.0f));\n"
    "  float4 hwFl = tex2Dlod(hwFoamTex, float4(0.5f + hwU.x * 0.5f, hwU.y, 0.0f, 0.0f));\n"
    "  hwV = hwFl.rg * 2.0f - 1.0f;\n"
    "  hwCr = saturate(hwFl.b * 2.0f - 1.0f) * hwTime.z;\n"
    "  hwSp = hwTime.w;\n"
    "  hwFn = hwFx.x;\n"
    "  if (hwFn > 0.0f) { /* foam normals: slope of the foam plane, world units, from texels 1.5 either side */\n"
    "    float hwE = 1.5f / 512.0f, hwUx = hwU.x * 0.5f;\n"
    "    float hwFr = tex2Dlod(hwFoamTex, float4(min(hwUx + 0.5f * hwE, 0.4995f), hwU.y, 0.0f, 0.0f)).r;\n"
    "    float hwFw = tex2Dlod(hwFoamTex, float4(max(hwUx - 0.5f * hwE, 0.0005f), hwU.y, 0.0f, 0.0f)).r;\n"
    "    float hwFu = tex2Dlod(hwFoamTex, float4(hwUx, hwU.y + hwE, 0.0f, 0.0f)).r;\n"
    "    float hwFd = tex2Dlod(hwFoamTex, float4(hwUx, hwU.y - hwE, 0.0f, 0.0f)).r;\n"
    "    hwG = float2(hwFr - hwFw, hwFu - hwFd) * (hwFoamXf.zw / (2.0f * hwE));\n"
    "  }\n"
    "  hwF = max(hwF, hwT.r);\n"
    "  hwA = max(hwA, hwT.g);\n"
    "  hwD = max(hwD, hwT.b);\n"
    "  hwDy = hwT.a * hwDyeCol.a;\n"
    "  hwDyC = hwDyeCol.rgb;\n"
    "  if (hwTime.y > 0.0f && dot(hwV, hwV) > 0.0025f) {\n"
    "    /* ripples carried along by the flow: three fixed waves whose pattern moves with (u, v), drawn twice\n"
    "       half a cycle apart and cross-faded so the pattern can reset without a jump (stage 11). The\n"
    "       reflection and refraction are already sampled here, so the slope shades them instead of bending them */\n"
    "    float2 hwRg = float2(0.0f, 0.0f);\n"
    "    float hwK, hwPh, hwRw;\n"
    "    float2 hwQ;\n"
    "    for (hwK = 0.0f; hwK < 1.0f; hwK += 0.5f) {\n"
    "      hwPh = frac(hwTime.x * 0.5f + hwK);\n"
    "      hwRw = 1.0f - abs(2.0f * hwPh - 1.0f);\n"
    "      hwQ = vertexPosition.xy - hwV * (240.0f * hwPh) + hwK * float2(37.0f, 91.0f);\n"
    "      hwRg += hwRw * (float2(0.8f, 0.6f) * cos(dot(hwQ, float2(0.8f, 0.6f)) * 0.2732f)\n"
    "        + float2(-0.5f, 0.866f) * cos(dot(hwQ, float2(-0.5f, 0.866f)) * 0.2027f + 1.7f)\n"
    "        + float2(0.96f, -0.28f) * cos(dot(hwQ, float2(0.96f, -0.28f)) * 0.3696f + 4.1f));\n"
    "    }\n"
    "    float hwSl = dot(hwRg, float2(0.6f, 0.8f)) * 0.45f * saturate(length(hwV)) * hwTime.y;\n"
    "    reflectionColour.rgb *= 1.0f + 0.35f * hwSl;\n"
    "    refractionColour.rgb *= 1.0f - 0.15f * hwSl;\n"
    "    specularStrength *= 1.0f + 0.5f * saturate(hwSl);\n"
    "  }\n";
/* wet surfaces: the deferred shaders that know their world position all end with this call; the mark
   the water left (s15 right half alpha, decoded with c219 = (lowest mark, mark range, up sign, strength))
   darkens the albedo and raises the gloss below it, fading over 25 units */
static const char WET_ANCHOR[] = "\tDS_WriteColour( wv, specularStrength";
static const char WET_NEED[] = "float4 vertexPosition = vIn.m_vVertexPosition;";
static const char WET_GLOBALS[] = "float4 hwWet : register(c219);\nfloat4 hwKate : register(c218);\nfloat4 hwKate2 : register(c217);\n";
static const char WET_HLSL[] =
    "  { /* HydroWater wet surfaces: darker and glossier below the high-water mark */\n"
    "    float2 hwWu = (vertexPosition.xy - hwFoamXf.xy) * hwFoamXf.zw;\n"
    "    if (hwWet.w > 0.0f && hwWu.x > 0.0f && hwWu.x < 1.0f && hwWu.y > 0.0f && hwWu.y < 1.0f) {\n"
    "      float hwWa = tex2Dlod(hwFoamTex, float4(0.5f + hwWu.x * 0.5f, hwWu.y, 0.0f, 0.0f)).a * 255.0f;\n"
    "      float hwWm = hwWet.x + (hwWa - 1.0f) * (1.0f / 254.0f) * hwWet.y;\n"
    "      float hwWt = hwWa > 0.5f ? saturate((hwWm - hwWet.z * vertexPosition.z) * (1.0f / 25.0f)) * hwWet.w : 0.0f;\n"
    "      diffuseMapSample.rgb *= 1.0f - 0.4f * hwWt;\n"
    "      specularStrength = lerp(specularStrength, saturate(specularStrength * 1.5f + 0.3f), hwWt);\n"
    "      specularPower *= 1.0f + 0.5f * hwWt;\n"
    "    }\n"
    "    if (hwKate.w > 0.0f) { /* drenched Kate: c218 = (x, y, world z of her wet line, freshness), c217 = (how much of her is soaked, world z of the splash top, splash density, drench_mask) */\n"
    "      float2 hwKd = vertexPosition.xy - hwKate.xy;\n"
    "      float hwKr = dot(hwKd, hwKd);\n"
    "      if (hwKr < 3600.0f) {\n"
    "        float hwRad = saturate(2.0f - hwKr * (1.0f / 1800.0f)) * hwKate.w;\n"
    "        float hwDz = vertexPosition.z - (hwKate.z + 3.0f * sin(hwKd.x * 0.35f + hwKd.y * 0.21f) + 2.0f * sin(hwKd.y * 0.53f - hwKd.x * 0.17f));\n" /* ragged line, not a level cut */
    "        float hwKw = saturate(hwDz * 0.1f) * hwRad;\n"
    "        float hwKc = saturate((hwDz + 14.0f) * (1.0f / 14.0f)) * hwRad;\n" /* cloth wicks a little above the line */
    "        float hwSf = saturate(-hwDz / max(hwKate.z - hwKate2.y, 1.0f));\n" /* splashes: 0 at the wet line, 1 at the top of the spray */
    "        float3 hwPc = floor(vertexPosition.xyz * (1.0f / 3.0f));\n"
    "        float hwPh = frac(sin(dot(hwPc, float3(127.1f, 311.7f, 74.7f))) * 43758.547f);\n"
    "        float3 hwPf = frac(vertexPosition.xyz * (1.0f / 3.0f)) - 0.5f;\n"
    "        float hwPs = (1.0f - smoothstep(0.25f, 0.45f, length(hwPf))) * step(hwPh + 0.001f, hwKate2.z * (1.0f - hwSf)) * step(hwDz, 0.0f) * hwRad;\n"
    "        hwKw = max(hwKw, 0.8f * hwPs);\n"
    "        hwKc = max(hwKc, hwPs);\n"
    "        float hwB = 1.0f;\n" /* the game's wetness mask: spec map .z, how wet the artists let this texel get */
    "#if defined(_SpecSamplersOn) && _SpecSamplersOn\n"
    "        if (g_bSpecularMapOn) hwB = HW_BETA;\n"
    "#endif\n"
    "        hwB = lerp(1.0f, hwB, saturate(hwKate2.w));\n"
    "        float3 hwC = diffuseMapSample.rgb;\n"
    "        float hwSk = (hwC.r > hwC.g && hwC.g > hwC.b) ? saturate(((hwC.r - hwC.b) / max(hwC.r, 0.01f) - 0.12f) * 6.0f) * saturate((0.65f - (hwC.r - hwC.b) / max(hwC.r, 0.01f)) * 6.0f) : 0.0f;\n"
    "        float hwL = dot(hwC, float3(0.3f, 0.59f, 0.11f));\n"
    "        float3 hwCl = lerp(hwL.xxx, hwC, 1.25f) * 0.7f;\n"
    "        diffuseMapSample.rgb = lerp(hwC, lerp(hwCl, hwC * 0.95f, hwSk), lerp(hwKc, hwKw, hwSk) * hwB);\n"
    "        specularStrength = lerp(specularStrength, lerp(saturate(specularStrength + 0.25f), saturate(specularStrength * 2.0f + 0.45f), hwSk), hwKw * lerp(0.4f, 1.0f, hwB));\n"
    "        specularPower *= 1.0f + hwKw * lerp(0.4f, 1.0f, hwB) * (0.5f + 2.5f * hwSk);\n"
    "        if (hwKate2.w > 1.5f) diffuseMapSample.rgb = lerp(diffuseMapSample.rgb, float3(1.0f, 0.0f, 0.0f), 0.8f * hwB * hwRad);\n" /* drench_mask 2: show the mask in red */
    "        float hwCol = floor(dot(vertexPosition.xy, float2(0.7071f, 0.7071f)) * 0.6f);\n"
    "        float hwH = frac(sin(hwCol * 12.9898f) * 43758.547f);\n"
    "        float hwS = frac(vertexPosition.z * 0.04f + hwTime.x * (0.5f + hwH) + hwH * 7.0f);\n"
    "        float hwRv = smoothstep(0.85f, 0.97f, hwS) * (1.0f - smoothstep(0.97f, 1.0f, hwS)) * step(hwH, 0.45f) * hwKw * hwKate.w;\n"
    "        specularStrength = saturate(specularStrength + 0.6f * hwRv);\n"
    "        diffuseMapSample.rgb *= 1.0f - 0.15f * hwRv;\n"
    "      }\n"
    "      if (hwKr < 6400.0f) { /* drips: round wet spots on flat ground around her */\n"
    "        float3 hwNg = normalize(cross(ddx(vertexPosition.xyz), ddy(vertexPosition.xyz)));\n"
    "        float2 hwG = vertexPosition.xy * (1.0f / 6.0f);\n"
    "        float2 hwGi = floor(hwG);\n"
    "        float hwR = frac(sin(dot(hwGi, float2(127.1f, 311.7f))) * 43758.547f);\n"
    "        float2 hwGc = hwGi + 0.25f + 0.5f * frac(hwR * float2(17.0f, 31.0f));\n"
    "        float hwDs = 1.0f - smoothstep(0.08f + 0.12f * hwR, 0.12f + 0.12f * hwR, length(hwG - hwGc));\n"
    "        float hwDw = hwDs * step(0.55f, hwR) * saturate(abs(hwNg.z) * 4.0f - 3.0f) * saturate(1.0f - hwKr * (1.0f / 6400.0f)) * hwKate.w * hwKate2.x;\n"
    "        diffuseMapSample.rgb *= 1.0f - 0.35f * hwDw;\n"
    "        specularStrength = lerp(specularStrength, saturate(specularStrength * 1.5f + 0.35f), hwDw);\n"
    "      }\n"
    "    }\n"
    "  }\n"
    ;

__attribute__((used)) char *hw_wet_inject(const char *src, size_t len, size_t *outlen)
{
    size_t na = sizeof WET_ANCHOR - 1, ng = sizeof FOAM_TEX_GLOBALS - 1, nw = sizeof WET_GLOBALS - 1, nh = sizeof WET_HLSL - 1, nb, o;
    const char *q = FindN(src, len, WET_ANCHOR, na), *beta;
    char *out;
    if (!q || FindN(q + na, len - (size_t)(q + na - src), WET_ANCHOR, na) || !FindN(src, len, WET_NEED, sizeof WET_NEED - 1)
        || FindN(src, len, "vReflectionSample", 17)) return NULL;
    beta = FindN(src, len, "float2 fBetaControl = ", 22) ? "#define HW_BETA fBetaControl.x\n" : "#define HW_BETA 1.0f\n";
    nb = strlen(beta);
    out = (char *)malloc(ng + nw + nb + len + nh + 1);
    if (!out) return NULL;
    memcpy(out, FOAM_TEX_GLOBALS, ng); memcpy(out + ng, WET_GLOBALS, nw); memcpy(out + ng + nw, beta, nb); o = ng + nw + nb;
    memcpy(out + o, src, (size_t)(q - src)); o += (size_t)(q - src);
    memcpy(out + o, WET_HLSL, nh); o += nh;
    memcpy(out + o, q, len - (size_t)(q - src)); o += len - (size_t)(q - src);
    out[o] = 0;
    *outlen = o;
    return out;
}

int g_inject_tex;   /* set by CompileHook for ps_3_0 shaders when the world foam texture is on */

/* FOAM_HLSL with line `at` replaced by `with` (or `with` appended after it when keep is set) */
static size_t SpliceLine(char *dst, const char *src, const char *at, const char *with, int keep)
{
    const char *f = strstr(src, at);
    size_t a, n;
    if (!f) { strcpy(dst, src); return strlen(dst); }
    a = (size_t)(f - src) + (keep ? strlen(at) : 0);
    memcpy(dst, src, a);
    strcpy(dst + a, with);
    strcat(dst, f + strlen(at));
    n = strlen(dst);
    return n;
}

__attribute__((used)) char *hw_foam_inject(const char *src, size_t len, size_t *outlen)
{
    static char v1[sizeof FOAM_HLSL + sizeof FOAM_F_TEST], v2[sizeof FOAM_HLSL + sizeof FOAM_F_TEST + sizeof FOAM_TEX_LINE];
    size_t na = sizeof FOAM_ANCHOR - 1, nd = sizeof FOAM_DEFS - 1, nh, ng, k = 0, o = 0;
    const char *p = src, *q, *hl = FOAM_HLSL;
    char *out;
    int tex = g_inject_tex;
    if (cfg.foam_test == 2) { SpliceLine(v1, hl, FOAM_F_LINE, FOAM_F_TEST, 0); hl = v1; }
    if (tex) { SpliceLine(v2, hl, FOAM_A_LINE, FOAM_TEX_LINE, 1); hl = v2; }
    nh = strlen(hl);
    ng = tex ? sizeof FOAM_TEX_GLOBALS - 1 : 0;
    while ((q = FindN(p, len - (size_t)(p - src), FOAM_ANCHOR, na)) != NULL) { k++; p = q + na; }
    if (!k) return NULL;
    out = (char *)malloc(ng + len + k * (nd + nh) + 1);
    if (!out) return NULL;
    memcpy(out, FOAM_TEX_GLOBALS, ng); o = ng;
    p = src;
    while ((q = FindN(p, len - (size_t)(p - src), FOAM_ANCHOR, na)) != NULL) {
        memcpy(out + o, p, (size_t)(q - p) + na); o += (size_t)(q - p) + na;
        memcpy(out + o, FOAM_DEFS, nd); o += nd;
        memcpy(out + o, hl, nh); o += nh;
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
    char *mod;
    int wet = 0;
    g_inject_tex = cfg.foam_tex && prof && !strcmp(prof, "ps_3_0");
    mod = (cfg.opts.foam && src) ? hw_foam_inject(src, srclen, &n) : NULL;
    if (!mod && g_inject_tex && cfg.opts.foam && cfg.wet > 0.0f && src && (mod = hw_wet_inject(src, srclen, &n)) != NULL) wet = 1;
    if (cfg.foam_dump >= 2 && src && prof && prof[0] == 'p') {   /* foam_dump 2: every pixel shader, to find splice anchors */
        static volatile LONG all;
        LONG d = InterlockedIncrement(&all);
        if (d <= 600) {
            wchar_t path[MAX_PATH];
            FILE *f;
            _snwprintf(path, MAX_PATH, L"%ls\\HydroWater_shaders", g_dir);
            CreateDirectoryW(path, NULL);
            _snwprintf(path, MAX_PATH, L"%ls\\HydroWater_shaders\\%03ld_%hs.hlsl", g_dir, d, prof);
            if ((f = _wfopen(path, L"wb")) != NULL) { fwrite(src, 1, srclen, f); fclose(f); }
        }
    }
    HRESULT hr;
    InterlockedIncrement(&g_shader_calls);
    if (!mod && src && FindN(src, srclen, "vReflectionSample", 17)) {
        LONG d = InterlockedIncrement(&g_shader_water_noanchor);
        if (d <= 4) Log("water-like shader without the foam anchor (%s %s)", fn ? fn : "?", prof ? prof : "?");
        if (cfg.foam_dump && d <= 4) {
            wchar_t path[MAX_PATH];
            FILE *f;
            _snwprintf(path, MAX_PATH, L"%ls\\HydroWater_noanchor%ld.hlsl", g_dir, d);
            if ((f = _wfopen(path, L"wb")) != NULL) { fwrite(src, 1, srclen, f); fclose(f); }
        }
    }
    if (mod) {
        void *e = NULL;
        LONG d;
        if (cfg.foam_dump && (d = InterlockedIncrement(&g_foam_dumps)) <= 4) {
            wchar_t path[MAX_PATH];
            FILE *f;
            _snwprintf(path, MAX_PATH, L"%ls\\HydroWater_shader%ld.hlsl", g_dir, d);
            if ((f = _wfopen(path, L"wb")) != NULL) { fwrite(mod, 1, n, f); fclose(f); }
        }
        if (wet && g_wet_patched < 2) Log("wet surfaces: compiling a deferred shader (%u bytes, flags %08lx)", (unsigned)n, (unsigned long)flags);
        hr = g_orig_compile(mod, (UINT)n, defs, inc, fn, prof, flags, shader, &e, ctab);
        if (hr >= 0) {
            free(mod);
            if (errs) *errs = e; else ReleaseCom(&e);
            if (wet) { if (InterlockedIncrement(&g_wet_patched) <= 2) Log("wet surfaces: deferred shader patched (%s %s)", fn ? fn : "?", prof ? prof : "?"); }
            else if (InterlockedIncrement(&g_foam_patched) <= 3) Log("foam shader patched (%s %s)", fn ? fn : "?", prof ? prof : "?");
            return hr;
        }
        if (InterlockedIncrement(&g_foam_failed) <= 3) {
            const char *msg = e ? (const char *)((Ptr_t)(*(void ***)e)[3])(e) : NULL;   /* ID3DXBuffer::GetBufferPointer */
            Log("%s shader did not compile (%08lx, %s %s), the game's shader is kept: %.600s", wet ? "wet" : "foam", (unsigned long)hr,
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
    memset(sn->depth, 32, (size_t)sn->w * sn->h);
    memset(sn->flowu, 128, (size_t)sn->w * sn->h * 2);
    memset(sn->crest, 0, (size_t)sn->w * sn->h);
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
    static const char abc[] = "ABCEFGHIJKLMNOPQRSTUVWYZ0123456789";   /* no D or X: never the game's own "DX" */
    const char *parts[] = { FOAM_DEFS, FOAM_HLSL, FOAM_TEX_GLOBALS, WET_GLOBALS, WET_HLSL };
    const char *name = CACHE_NAME_HW;
    unsigned h = 2166136261u, k;
    for (k = 0; k < sizeof parts / sizeof parts[0]; k++)
        for (const char *c = parts[k]; *c; c++) h = (h ^ (unsigned char)*c) * 16777619u;
    h = (h ^ (unsigned)(cfg.foam_test == 2) ^ (unsigned)(cfg.wet > 0.0f) << 1) * 16777619u;
    CACHE_NAME_HW[11] = abc[h % (sizeof abc - 1)];
    CACHE_NAME_HW[12] = abc[(h / (sizeof abc - 1)) % (sizeof abc - 1)];
    if (!memcmp(s, name, sizeof CACHE_NAME_HW)) { done = 1; return; }
    if (memcmp(s, CACHE_NAME_GAME, sizeof CACHE_NAME_GAME)) return;    /* not unpacked yet */
    if (PatchBytes(s, name, sizeof CACHE_NAME_HW)) { done = 1; Log("foam: shader cache is %s (the game's %s is left alone)", name, CACHE_NAME_GAME); }
}

/* every 4-byte slot in the exe image holding fn (import table entries) is pointed at hook */
static int PatchImportSlots(void *fn, void *hook)
{
    BYTE *base = (BYTE *)GetModuleHandleW(NULL), *p, *end;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    MEMORY_BASIC_INFORMATION mbi;
    int hits = 0;
    end = base + nt->OptionalHeader.SizeOfImage;
    for (p = base; p < end && VirtualQuery(p, &mbi, sizeof mbi); p = (BYTE *)mbi.BaseAddress + mbi.RegionSize) {
        BYTE *q, *re = (BYTE *)mbi.BaseAddress + mbi.RegionSize;
        if (mbi.State != MEM_COMMIT || (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))) continue;
        if (re > end) re = end;
        for (q = (BYTE *)mbi.BaseAddress; q + 4 <= re; q += 4)
            if (*(void **)q == fn && PatchBytes(q, &hook, 4)) hits++;
    }
    return hits;
}

/* the compile import: every slot in the exe image holding d3dx9_43!D3DXCompileShader */
static void HookCompile(void)
{
    static int done;
    HMODULE d3dx;
    BYTE *fn;
    int hits;
    if (done || !cfg.opts.foam) return;
    d3dx = GetModuleHandleW(L"d3dx9_43.dll");
    if (!d3dx || !(fn = (BYTE *)GetProcAddress(d3dx, "D3DXCompileShader"))) return;
    g_orig_compile = (Compile_t)fn;
    hits = PatchImportSlots(fn, (void *)CompileHook);
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
static void HookRawInput(void);

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
            HookRawInput();
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
 * IDirect3DDevice9::EndScene (slot 42) is hooked as well. Every 250 ms it looks for
 * HydroWater.cmd next to the DLL, reads it, deletes it and runs its lines:
 *   shot <file.bmp>   dump the back buffer (works hidden, off-screen, any mode)
 * This is the test-pilot channel; it costs one file probe every quarter second. */
typedef HRESULT (WINAPI *EndScene_t)(IDirect3DDevice9 *);
static EndScene_t g_orig_endscene;
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

/* Camera turns. The game takes mouse movement only from Raw Input: its window procedure calls
 * GetRawInputData on WM_INPUT. With control = 1 that import is redirected; "look dx dy [steps]"
 * posts `steps` WM_INPUT messages carrying a marker handle, and the hook answers those with a
 * relative mouse move of (dx/steps, dy/steps). Real raw input passes through unchanged. */
#define HW_LOOK_HANDLE ((HRAWINPUT)(UINT_PTR)0x4857C00Cu)
typedef UINT (WINAPI *GetRawInputData_t)(HRAWINPUT, UINT, LPVOID, PUINT, UINT);
static GetRawInputData_t g_orig_rawdata;
static volatile LONG g_look_sx, g_look_sy;

static UINT WINAPI RawDataHook(HRAWINPUT h, UINT cmd, LPVOID data, PUINT size, UINT hdr)
{
    RAWINPUT ri;
    UINT n;
    if (h != HW_LOOK_HANDLE) {
        /* In background mode the user's own mouse must not steer the game: zero real movement. */
        n = g_orig_rawdata(h, cmd, data, size, hdr);
        if (cfg.background && cmd == RID_INPUT && data && n != (UINT)-1 && n >= sizeof(RAWINPUTHEADER)
            && ((RAWINPUT *)data)->header.dwType == RIM_TYPEMOUSE) {
            ((RAWINPUT *)data)->data.mouse.lLastX = 0;
            ((RAWINPUT *)data)->data.mouse.lLastY = 0;
        }
        return n;
    }
    memset(&ri, 0, sizeof ri);
    ri.header.dwType = RIM_TYPEMOUSE;
    ri.header.dwSize = sizeof ri;
    ri.data.mouse.usFlags = MOUSE_MOVE_RELATIVE;
    ri.data.mouse.lLastX = g_look_sx;
    ri.data.mouse.lLastY = g_look_sy;
    n = cmd == RID_HEADER ? (UINT)sizeof ri.header : (UINT)sizeof ri;
    if (!size || hdr != sizeof(RAWINPUTHEADER)) return (UINT)-1;
    if (!data) { *size = n; return 0; }
    if (*size < n) { *size = n; return (UINT)-1; }
    memcpy(data, &ri, n);
    return n;
}

static void HookRawInput(void)
{
#ifndef HW_TEST
    void *fn = (void *)GetProcAddress(GetModuleHandleW(L"user32.dll"), "GetRawInputData");
    int hits;
    if (!cfg.control || g_orig_rawdata || !fn) return;
    g_orig_rawdata = (GetRawInputData_t)fn;
    hits = PatchImportSlots(fn, (void *)RawDataHook);
    Log("control: GetRawInputData import %s (%d slot%s)", hits ? "hooked" : "NOT found", hits, hits == 1 ? "" : "s");
#endif
}

static void InjectLook(const char *args)
{
    int dx = 0, dy = 0, steps = 10, i;
    if (sscanf(args, "%d %d %d", &dx, &dy, &steps) < 2) { Log("control: look needs dx dy [steps]"); return; }
    if (!g_game_wnd || !g_orig_rawdata) { Log("control: look unavailable (no window or raw input hook)"); return; }
    if (steps < 1) steps = 1;
    if (steps > 100) steps = 100;
    InterlockedExchange(&g_look_sx, dx / steps);
    InterlockedExchange(&g_look_sy, dy / steps);
    for (i = 0; i < steps; i++) PostMessageW(g_game_wnd, WM_INPUT, RIM_INPUT, (LPARAM)HW_LOOK_HANDLE);
    Log("control: look %d %d in %d steps", dx, dy, steps);
}

static void InjectKey(const char *args);
static float g_kate_wet;   /* defined with the wet surfaces below */

static void RunControlFile(IDirect3DDevice9 *dev)
{
    ClickTick();
    wchar_t path[MAX_PATH];
    char line[512];
    FILE *f;
    wchar_t work[MAX_PATH];
    _snwprintf(path, MAX_PATH, L"%ls\\HydroWater.cmd", g_dir);
    _snwprintf(work, MAX_PATH, L"%ls\\HydroWater.cmd.run", g_dir);
    /* Take the file by renaming it first. The rename fails while a writer still has it open,
     * so a half-written file is never read and deleted. */
    if (!MoveFileExW(path, work, MOVEFILE_REPLACE_EXISTING)) return;
    wcscpy(path, work);
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
        else if (!_strnicmp(line, "look ", 5)) InjectLook(line + 5);
        else if (!_strnicmp(line, "click", 5)) InjectClick(line[5] ? line + 6 : "");
        else if (!_stricmp(line, "state")) GameStateLog("now");
        else if (!_stricmp(line, "kate")) {
            const float *kp = KatePos();
            if (kp) Log("control: kate at %.0f %.0f height %.0f, wet %.0f", kp[0], kp[1], kp[2], g_kate_wet);
            else Log("control: kate: no player pawn");
        }
        else Log("control: unknown command '%s'", line);
    }
    fclose(f);
    DeleteFileW(path);
}

static void FoamTexUpdate(IDirect3DDevice9 *dev);

/* ---------------------------------------------------------------- world foam texture
 * The game rebuilds only the sheet meshes on its render list (in the Practice pool one sheet of
 * 80), so foam in vertex colours never reaches most water. Instead every sheet's foam and air are
 * written into one texture laid over the world (a texel per cell, covering all bridged sheets) at
 * each frame; the water shader reads it by world position (sampler s15, mapping in c223). The
 * texture is twice as wide: the right half holds the flow direction for the foam streaks. The
 * sheet origin is at S+0x7c/S+0x80 and cells are dx = S+0x10 apart (FUN_00bf0e20). */
#define FOAM_TEX_N 512
static IDirect3DTexture9 *g_foam_tex;
static IDirect3DDevice9 *g_foam_tex_dev;
static volatile LONG g_foam_tex_logged;

/* wet surfaces: per texel of the world texture, the highest water surface seen (the sheet's up axis),
 * sinking by wet_dry units a second so walls dry from the top and floors after the water has gone.
 * g_wet_lo is the last surface seen there; a mark 80 below it is dropped. Kate carries her own mark
 * (how far above her the water was) out of the water, so she stays wet and leaves a wet trail. */
static float *g_wet_m, *g_wet_lo;
static float g_wet_x0, g_wet_y0, g_wet_cell, g_wet_sink, g_kate_wet = -1e30f, g_kate_surf = -1e30f, g_kate_fresh, g_wet_dt, g_kate_spl = -1e30f, g_kate_spd;
static int g_kate_k = -1;   /* Kate's texel this frame, and (g_kate_surf) the highest water surface in it */
static DWORD g_wet_tick;

static void WetRemap(float x0, float y0, float cell)
{
    float *m, *lo;
    int i, j;
    if (g_wet_m && x0 == g_wet_x0 && y0 == g_wet_y0 && cell == g_wet_cell) return;
    m = (float *)malloc(sizeof(float) * FOAM_TEX_N * FOAM_TEX_N * 2);
    if (!m) return;
    lo = m + FOAM_TEX_N * FOAM_TEX_N;
    for (j = 0; j < FOAM_TEX_N; j++)
        for (i = 0; i < FOAM_TEX_N; i++) {   /* the old marks, nearest texel, so a change of the sheet set keeps them */
            int k = j * FOAM_TEX_N + i, oi, oj;
            m[k] = lo[k] = -1e30f;
            if (!g_wet_m || !(g_wet_cell > 0.0f)) continue;
            oi = (int)floorf((x0 + (i + 0.5f) * cell - g_wet_x0) / g_wet_cell);
            oj = (int)floorf((y0 + (j + 0.5f) * cell - g_wet_y0) / g_wet_cell);
            if (oi < 0 || oj < 0 || oi >= FOAM_TEX_N || oj >= FOAM_TEX_N) continue;
            m[k] = g_wet_m[oj * FOAM_TEX_N + oi]; lo[k] = g_wet_lo[oj * FOAM_TEX_N + oi];
        }
    free(g_wet_m);
    g_wet_m = m; g_wet_lo = lo; g_wet_x0 = x0; g_wet_y0 = y0; g_wet_cell = cell;
}

static void FoamTexUpdate(IDirect3DDevice9 *dev)
{
    float x0 = 1e30f, y0 = 1e30f, x1 = -1e30f, y1 = -1e30f, cell = 0.0f, inv, xf[4];
    D3DLOCKED_RECT lr;
    bridge *b;
    int i, j, n = 0;
    DWORD now = GetTickCount();
    if (!cfg.foam_tex || !cfg.opts.foam) return;
    if (g_foam_tex && g_foam_tex_dev != dev) { g_foam_tex = NULL; }   /* new device: the old texture went with it */
    if (!g_foam_tex) {
        if (IDirect3DDevice9_CreateTexture(dev, 2 * FOAM_TEX_N, FOAM_TEX_N, 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, &g_foam_tex, NULL) != D3D_OK) {
            g_foam_tex = NULL; return;
        }
        g_foam_tex_dev = dev;
        Log("foam: world foam texture %dx%d created (right half: flow)", 2 * FOAM_TEX_N, FOAM_TEX_N);
    }
    AcquireSRWLockShared(&g_lock);
    for (b = g_bridges; b; b = b->next) {
        float ox, oy, dx;
        if (!b->snap || now - b->snap->tick > 1000) continue;
        ox = b->snap->ox; oy = b->snap->oy; dx = b->snap->dx;
        if (!(dx > 0.0f) || !(ox == ox) || !(oy == oy)) continue;
        if (ox < x0) x0 = ox;
        if (oy < y0) y0 = oy;
        if (ox + dx * b->snap->w > x1) x1 = ox + dx * b->snap->w;
        if (oy + dx * b->snap->h > y1) y1 = oy + dx * b->snap->h;
        if (dx > cell) cell = dx;
        n++;
    }
    if (!n) { ReleaseSRWLockShared(&g_lock); return; }
    if ((x1 - x0) / FOAM_TEX_N > cell) cell = (x1 - x0) / FOAM_TEX_N;
    if ((y1 - y0) / FOAM_TEX_N > cell) cell = (y1 - y0) / FOAM_TEX_N;
    inv = 1.0f / cell;
    if (cfg.wet > 0.0f) {
        float dt = g_wet_tick ? (float)(now - g_wet_tick) * 0.001f : 0.0f, sink;
        int k;
        if (dt > 0.5f) dt = 0.5f;
        g_wet_tick = now;
        WetRemap(x0, y0, cell);
        sink = g_wet_sink = (cfg.wet_dry > 0.0f ? cfg.wet_dry : 0.0f) * dt;
        g_wet_dt = dt;
        {   const float *kp = KatePos();
            int ki = kp ? (int)((kp[0] - x0) * inv) : -1, kj = kp ? (int)((kp[1] - y0) * inv) : -1;
            g_kate_k = ki >= 1 && kj >= 1 && ki < FOAM_TEX_N - 1 && kj < FOAM_TEX_N - 1 ? kj * FOAM_TEX_N + ki : -1;
            g_kate_surf = -1e30f; }
        if (g_wet_m) for (k = 0; k < FOAM_TEX_N * FOAM_TEX_N; k++)
            if (g_wet_m[k] > -1e29f) { g_wet_m[k] -= sink; if (g_wet_m[k] < g_wet_lo[k] - 80.0f) g_wet_m[k] = -1e30f; }
    }
    if (IDirect3DTexture9_LockRect(g_foam_tex, 0, &lr, NULL, 0) == D3D_OK) {
        for (j = 0; j < FOAM_TEX_N; j++) {
            memset((BYTE *)lr.pBits + (size_t)j * lr.Pitch, 0, FOAM_TEX_N * 4);
            memset((BYTE *)lr.pBits + (size_t)j * lr.Pitch + FOAM_TEX_N * 4, 128, FOAM_TEX_N * 4);   /* no flow */
        }
        for (b = g_bridges; b; b = b->next) {
            const foam_snap *sn = b->snap;
            float ox, oy, dx;
            if (!sn || now - sn->tick > 1000) continue;
            ox = sn->ox; oy = sn->oy; dx = sn->dx;
            if (!(dx > 0.0f) || !(ox == ox) || !(oy == oy)) continue;
            for (j = 0; j < sn->h; j++) {
                int ty = (int)((oy + (j + 0.5f) * dx - y0) * inv);
                BYTE *row;
                if (ty < 0 || ty >= FOAM_TEX_N) continue;
                row = (BYTE *)lr.pBits + (size_t)ty * lr.Pitch;
                for (i = 0; i < sn->w; i++) {
                    int tx = (int)((ox + (i + 0.5f) * dx - x0) * inv);
                    BYTE f = sn->foam[j * sn->w + i], a = sn->air[j * sn->w + i], d = sn->depth[j * sn->w + i];
                    if (tx < 0 || tx >= FOAM_TEX_N) continue;
                    if (f > row[tx * 4 + 2]) row[tx * 4 + 2] = f;   /* R: foam */
                    if (a > row[tx * 4 + 1]) row[tx * 4 + 1] = a;   /* G: air */
                    if (sn->dye[j * sn->w + i] > row[tx * 4 + 3]) row[tx * 4 + 3] = sn->dye[j * sn->w + i];   /* A: dye */
                    if (d > row[tx * 4 + 0]) row[tx * 4 + 0] = d;   /* B: depth tint */
                    {   /* right half, R/G: flow; the stronger one wins where sheets overlap */
                        BYTE *fl = row + (FOAM_TEX_N + tx) * 4;
                        int nu = sn->flowu[j * sn->w + i] - 128, nv = sn->flowv[j * sn->w + i] - 128, ou = fl[2] - 128, ov = fl[1] - 128;
                        if (nu * nu + nv * nv > ou * ou + ov * ov) { fl[2] = (BYTE)(nu + 128); fl[1] = (BYTE)(nv + 128); }
                        if (128 + (sn->crest[j * sn->w + i] >> 1) > fl[0]) fl[0] = (BYTE)(128 + (sn->crest[j * sn->w + i] >> 1));   /* B: crest glow */
                    }
                    if (g_wet_m && cfg.wet > 0.0f && sn->surf[j * sn->w + i] > -1e29f) {   /* the high-water mark */
                        int k = ty * FOAM_TEX_N + tx;
                        float sf = sn->surf[j * sn->w + i];
                        if (sf > g_wet_m[k]) g_wet_m[k] = sf;
                        g_wet_lo[k] = sf;
                        if (k == g_kate_k && sf > g_kate_surf) g_kate_surf = sf;
                    }
                }
            }
        }
        if (g_wet_m && cfg.wet > 0.0f) {
            const float *kp = KatePos();
            float zlo = 1e30f, zhi = -1e30f, sc;
            int k;
            if (kp) {   /* Kate: how far above her the water reaches, carried out of the water and sinking like a mark */
                int ki = (int)((kp[0] - x0) * inv), kj = (int)((kp[1] - y0) * inv), di, dj;
                float kh = -kp[2];
                if (ki >= 1 && kj >= 1 && ki < FOAM_TEX_N - 1 && kj < FOAM_TEX_N - 1) {
                    if (g_kate_wet > -1e29f) g_kate_wet -= g_wet_sink;
                    if (g_kate_surf > -1e29f && g_kate_surf - kh > g_kate_wet) g_kate_wet = g_kate_surf - kh;   /* real water only, not her own trail */
                    if (g_kate_wet > 400.0f) g_kate_wet = 400.0f;
                    /* drench freshness: full while she stands in water, then fades over ~40 s */
                    if (g_kate_surf > -1e29f && g_kate_surf - kh > -140.0f) g_kate_fresh = 1.0f;   /* any water above her ankles; the wet line limits how much of her */
                    else if (g_kate_fresh > 0.0f) g_kate_fresh -= g_wet_dt * (1.0f / 40.0f);
                    if (g_kate_fresh < 0.0f) g_kate_fresh = 0.0f;
                    {   /* splashes: running through shallow water throws spray up her legs and body in patches;
                           g_kate_spl is the spray top above her (like g_kate_wet), g_kate_spd how many patches are wet */
                        static float px, py;
                        static int pv;
                        float d = g_kate_surf > -1e29f ? g_kate_surf - kh : -1e30f;
                        if (pv && g_wet_dt > 0.0f && d > -140.0f && d < 60.0f) {   /* wading, not swimming */
                            float vx = kp[0] - px, vy = kp[1] - py, v = sqrtf(vx * vx + vy * vy) / g_wet_dt;
                            if (v > 60.0f && v < 3000.0f) {   /* a jump in position is a respawn */
                                float a = (v - 60.0f) * (1.0f / 300.0f), top;
                                if (a > 1.0f) a = 1.0f;
                                top = d + 40.0f + 120.0f * a;
                                if (top > g_kate_spl) g_kate_spl = top;
                                g_kate_spd += a * g_wet_dt * 0.5f;
                                if (g_kate_spd > 1.0f) g_kate_spd = 1.0f;
                            }
                        }
                        px = kp[0]; py = kp[1]; pv = 1;
                        if (g_kate_spl > -1e29f) g_kate_spl -= g_wet_sink;
                        if (g_kate_spl > 400.0f) g_kate_spl = 400.0f;
                        if (g_kate_fresh <= 0.0f) { g_kate_spd = 0.0f; g_kate_spl = -1e30f; }
                    }
                    if (g_kate_wet > -150.0f)
                        for (dj = -1; dj <= 1; dj++)
                            for (di = -1; di <= 1; di++) {
                                int q = (kj + dj) * FOAM_TEX_N + ki + di;
                                if (kh + g_kate_wet > g_wet_m[q]) { g_wet_m[q] = kh + g_kate_wet; if (g_wet_lo[q] < -1e29f) g_wet_lo[q] = kh - 150.0f; }
                            }
                }
            }
            for (k = 0; k < FOAM_TEX_N * FOAM_TEX_N; k++)
                if (g_wet_m[k] > -1e29f) { if (g_wet_m[k] < zlo) zlo = g_wet_m[k]; if (g_wet_m[k] > zhi) zhi = g_wet_m[k]; }
            if (zhi < zlo) { zlo = 0.0f; zhi = 1.0f; }
            if (zhi - zlo < 1.0f) zhi = zlo + 1.0f;
            sc = 254.0f / (zhi - zlo);
            for (j = 0; j < FOAM_TEX_N; j++) {   /* right half alpha: 0 = never wet, 1..255 = the mark from zlo to zhi */
                BYTE *row = (BYTE *)lr.pBits + (size_t)j * lr.Pitch + FOAM_TEX_N * 4;
                const float *m = g_wet_m + (size_t)j * FOAM_TEX_N;
                for (i = 0; i < FOAM_TEX_N; i++) row[i * 4 + 3] = (BYTE)(m[i] > -1e29f ? 1 + (int)((m[i] - zlo) * sc + 0.5f) : 0);
            }
            xf[0] = zlo; xf[1] = zhi - zlo; xf[2] = -1.0f;   /* the world z axis points down the sheet's up axis */
            xf[3] = cfg.wet > 1.5f ? 1.5f : cfg.wet;
        } else { xf[0] = xf[1] = xf[2] = xf[3] = 0.0f; }
        IDirect3DTexture9_UnlockRect(g_foam_tex, 0);
        IDirect3DDevice9_SetPixelShaderConstantF(dev, 219, xf, 1);
        {   const float *kp = KatePos();
            float kc[4] = { 0.0f, 0.0f, 0.0f, 0.0f };
            if (kp && cfg.wet > 0.0f && cfg.drench > 0.0f && g_kate_wet > -150.0f && g_kate_fresh > 0.0f) {
                kc[0] = kp[0]; kc[1] = kp[1]; kc[2] = -(-kp[2] + g_kate_wet);   /* world z of her wet line (z points down) */
                kc[3] = g_kate_fresh * (cfg.drench > 1.5f ? 1.5f : cfg.drench);
            }
            IDirect3DDevice9_SetPixelShaderConstantF(dev, 218, kc, 1);
            kc[0] = kc[3] > 0.0f ? (g_kate_wet + 150.0f) * (1.0f / 250.0f) : 0.0f;   /* soaked share: 0 feet only, 1 to the chest; scales the drips */
            if (kc[0] > 1.0f) kc[0] = 1.0f;
            if (kc[3] > 0.0f && g_kate_spl > g_kate_wet && cfg.drench_splash > 0.0f) {
                kc[1] = -(-kp[2] + g_kate_spl);   /* world z of the spray top */
                kc[2] = g_kate_spd * (cfg.drench_splash > 1.0f ? 1.0f : cfg.drench_splash);
            } else { kc[1] = kc[2] = 0.0f; }
            kc[3] = cfg.drench_mask;
            IDirect3DDevice9_SetPixelShaderConstantF(dev, 217, kc, 1);
        }
    }
    ReleaseSRWLockShared(&g_lock);
    xf[0] = x0; xf[1] = y0; xf[2] = 1.0f / (cell * FOAM_TEX_N); xf[3] = xf[2];
    IDirect3DDevice9_SetTexture(dev, 15, (IDirect3DBaseTexture9 *)g_foam_tex);
    IDirect3DDevice9_SetSamplerState(dev, 15, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
    IDirect3DDevice9_SetSamplerState(dev, 15, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
    IDirect3DDevice9_SetSamplerState(dev, 15, D3DSAMP_MIPFILTER, D3DTEXF_NONE);
    IDirect3DDevice9_SetSamplerState(dev, 15, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
    IDirect3DDevice9_SetSamplerState(dev, 15, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
    IDirect3DDevice9_SetPixelShaderConstantF(dev, 223, xf, 1);
    xf[0] = (float)(GetTickCount() % 600000u) * 0.001f; xf[1] = cfg.ripples; xf[2] = cfg.crest_glow > 0.0f ? 1.0f : 0.0f; xf[3] = cfg.splotch > 1.0f ? 1.0f : cfg.splotch < 0.0f ? 0.0f : cfg.splotch;
    IDirect3DDevice9_SetPixelShaderConstantF(dev, 222, xf, 1);
    xf[0] = cfg.dye_colour[0]; xf[1] = cfg.dye_colour[1]; xf[2] = cfg.dye_colour[2]; xf[3] = cfg.dye;
    IDirect3DDevice9_SetPixelShaderConstantF(dev, 221, xf, 1);
    xf[0] = cfg.foam_normals > 2.0f ? 2.0f : cfg.foam_normals < 0.0f ? 0.0f : cfg.foam_normals; xf[1] = xf[2] = xf[3] = 0.0f;
    IDirect3DDevice9_SetPixelShaderConstantF(dev, 220, xf, 1);
    if (InterlockedIncrement(&g_foam_tex_logged) == 1 || g_foam_tex_logged % 2000 == 0)
        Log("foam: world texture over %d sheets, x %.0f..%.0f y %.0f..%.0f, texel %.1f", n, x0, x1, y0, y1, cell);
}

/* The per-frame work (foam texture, control file) runs in EndScene, at most once per 10 ms. It
 * used to hook Present on the device and the swap chain, but the Steam overlay hooks those too,
 * and now and then the two hooks called each other until the stack ran out (a startup crash in
 * about one launch in three). The overlay leaves EndScene alone. For the first 20 seconds the log
 * says once a second how many scenes ended and how many drew into the back buffer (in game
 * about 180 a second, none into the back buffer; the shots still come out whole). */
static HRESULT WINAPI EndSceneHook(IDirect3DDevice9 *self)
{
    static DWORD last, stat_tick, scenes, to_bb, logged;
    DWORD now = GetTickCount();
    IDirect3DSurface9 *rt = NULL, *bb = NULL;
    scenes++;
    if (logged < 20 && IDirect3DDevice9_GetRenderTarget(self, 0, &rt) == D3D_OK && rt) {
        if (IDirect3DDevice9_GetBackBuffer(self, 0, 0, D3DBACKBUFFER_TYPE_MONO, &bb) == D3D_OK && bb) {
            if (rt == bb) to_bb++;
            if (now - stat_tick >= 1000) {
                D3DSURFACE_DESC dr, db;
                IDirect3DSurface9_GetDesc(rt, &dr); IDirect3DSurface9_GetDesc(bb, &db);
                if (stat_tick) Log("endscene: %lu scenes/s, %lu into the back buffer; last rt %p %ux%u fmt %d ms %d, back buffer %p %ux%u fmt %d ms %d",
                                   scenes, to_bb, (void *)rt, dr.Width, dr.Height, (int)dr.Format, (int)dr.MultiSampleType,
                                   (void *)bb, db.Width, db.Height, (int)db.Format, (int)db.MultiSampleType), logged++;
                stat_tick = now; scenes = to_bb = 0;
            }
            IDirect3DSurface9_Release(bb);
        }
        IDirect3DSurface9_Release(rt);
    }
    if (now - last >= 10) {
        last = now;
        InterlockedIncrement(&g_presents);
        FoamTexUpdate(self);
        if (cfg.control && now - g_last_cmd_poll >= 250) { g_last_cmd_poll = now; RunControlFile(self); }
    }
    return g_orig_endscene(self);
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
    Log("modules: overlay %p d3d9 %p user32 %p", (void *)GetModuleHandleW(L"gameoverlayrenderer.dll"), (void *)GetModuleHandleW(L"d3d9.dll"), (void *)GetModuleHandleW(L"user32.dll"));
    if (pp) Log("D3D device requested: %ux%u windowed=%d interval=%08lx swap=%u", pp->BackBufferWidth, pp->BackBufferHeight,
                (int)pp->Windowed, (unsigned long)pp->PresentationInterval, pp->SwapEffect);
    AdoptWindow(h);
    ForceWindowed(pp, h);
    InstallFoam();
    hr = g_orig_create_device(self, adapter, type, focus, flags, pp, dev);
    if (hr == 0 && dev && *dev) {
        if (!g_orig_reset) PatchVtable(*dev, 16, (void *)ResetHook, (void **)&g_orig_reset);
        if ((cfg.control || (cfg.foam_tex && cfg.opts.foam)) && !g_orig_endscene) {
            PatchVtable(*dev, 42, (void *)EndSceneHook, (void **)&g_orig_endscene);
            Log("control: EndScene hooked (orig %p)", (void *)g_orig_endscene);
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

/* ---------------------------------------------------------------- crash log */
/* the first few access violations go to the log with the module and offset of the fault and of the
   return addresses found on the stack, so a crash report says where it happened */
static const char *ModOff(DWORD a, DWORD *off)
{
    static char name[4][64];
    static int r;
    HMODULE m = NULL;
    char path[MAX_PATH], *s, *n = name[r++ & 3];
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)(uintptr_t)a, &m) || !m) return NULL;
    if (!GetModuleFileNameA(m, path, sizeof path)) return NULL;
    s = strrchr(path, '\\');
    snprintf(n, 64, "%s", s ? s + 1 : path);
    *off = a - (DWORD)(uintptr_t)m;
    return n;
}

static HANDLE g_crashf = INVALID_HANDLE_VALUE;   /* HydroWater_crash.txt, opened at load so a crash needs no heap */

static LONG WINAPI CrashLog(EXCEPTION_POINTERS *ep)
{
    static volatile LONG seen;
    DWORD code = ep->ExceptionRecord->ExceptionCode, off = 0, *sp;
    const char *m;
    char line[1024];
    int i, n = 0, o;
    if ((code != EXCEPTION_ACCESS_VIOLATION && code != 0xC0000374u && code != EXCEPTION_STACK_OVERFLOW) || InterlockedIncrement(&seen) > 8) return EXCEPTION_CONTINUE_SEARCH;
#ifdef _M_IX86
    if (g_crashf != INVALID_HANDLE_VALUE) {   /* raw first, no heap, no locks: the module names below may hang */
        const CONTEXT *c = ep->ContextRecord;
        const DWORD *st = (const DWORD *)(uintptr_t)c->Esp;
        DWORD w;
        o = wsprintfA(line, "exc %08lx eip %08lx addr %08lx tid %lu eax %08lx ebx %08lx ecx %08lx edx %08lx esi %08lx edi %08lx ebp %08lx esp %08lx\r\n",
                      code, c->Eip, ep->ExceptionRecord->NumberParameters > 1 ? (DWORD)ep->ExceptionRecord->ExceptionInformation[1] : 0,
                      GetCurrentThreadId(), c->Eax, c->Ebx, c->Ecx, c->Edx, c->Esi, c->Edi, c->Ebp, c->Esp);
        WriteFile(g_crashf, line, (DWORD)o, &w, NULL);
        for (i = 0, o = 0; i < 64 && !IsBadReadPtr(st + i, 4); i++) o += wsprintfA(line + o, "%08lx%s", st[i], (i & 7) == 7 ? "\r\n" : " ");
        WriteFile(g_crashf, line, (DWORD)o, &w, NULL);
        WriteFile(g_crashf, "\r\n", 2, &w, NULL);
        if (code == EXCEPTION_STACK_OVERFLOW) {   /* which return addresses repeat down the whole stack: the recursion cycle */
            static DWORD key[4096], cnt[4096];
            const DWORD *top = (const DWORD *)(uintptr_t)__readfsdword(4), *q;
            for (q = st; q < top; q++) {
                DWORD v = *q, h;
                if (v < 0x00400000u || v >= 0x80000000u) continue;
                for (h = (v * 2654435761u) >> 20; key[h] && key[h] != v; h = (h + 1) & 4095) ;
                key[h] = v; cnt[h]++;
            }
            o = wsprintfA(line, "stack %08lx..%08lx, values seen 100+ times:\r\n", (DWORD)(uintptr_t)st, (DWORD)(uintptr_t)top);
            for (i = 0, n = 0; i < 4096 && n < 48; i++)
                if (cnt[i] >= 100) o += wsprintfA(line + o, "%08lx x%lu%s", key[i], cnt[i], (++n & 3) ? "  " : "\r\n");
            WriteFile(g_crashf, line, (DWORD)o, &w, NULL);
            WriteFile(g_crashf, "\r\n", 2, &w, NULL);
            n = 0;
        }
    }
#endif
    m = ModOff((DWORD)(uintptr_t)ep->ExceptionRecord->ExceptionAddress, &off);
    o = snprintf(line, sizeof line, "exception %08lx at %s+%lx (thread %lu), stack:", (unsigned long)code, m ? m : "?", (unsigned long)off, GetCurrentThreadId());
#ifdef _M_IX86
    sp = (DWORD *)(uintptr_t)ep->ContextRecord->Esp;
#else
    sp = NULL;
#endif
    for (i = 0; sp && i < 256 && n < 16 && o < (int)sizeof line - 80; i++) {
        DWORD v;
        if (IsBadReadPtr(sp + i, 4)) break;
        v = sp[i];
        if (v < 0x10000 || !(m = ModOff(v, &off)) || off < 0x1000) continue;
        o += snprintf(line + o, sizeof line - o, " %s+%lx", m, (unsigned long)off); n++;
    }
    Log("%s", line);
    return EXCEPTION_CONTINUE_SEARCH;
}

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
        {   wchar_t cp[MAX_PATH + 32]; char hd[160]; DWORD w; int k;
            _snwprintf(cp, MAX_PATH + 32, L"%ls\\HydroWater_crash.txt", g_dir);
            g_crashf = CreateFileW(cp, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
            k = wsprintfA(hd, "start pid %lu: exe %p ntdll %p kernelbase %p mod %p\r\n", GetCurrentProcessId(), (void *)GetModuleHandleW(NULL),
                          (void *)GetModuleHandleW(L"ntdll.dll"), (void *)GetModuleHandleW(L"kernelbase.dll"), (void *)inst);
            if (g_crashf != INVALID_HANDLE_VALUE) WriteFile(g_crashf, hd, (DWORD)k, &w, NULL); }
        AddVectoredExceptionHandler(0, CrashLog);
        CreateThread(NULL, 0, Installer, NULL, 0, NULL);
    }
    else if (reason == DLL_PROCESS_DETACH) {
        Log("unloading: %ld solver calls, %ld on HydroWater, %d sheets", g_calls, g_hw_calls, g_nbridges);
    }
    return TRUE;
}
