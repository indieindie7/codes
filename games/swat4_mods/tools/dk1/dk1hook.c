/* Door Kickers 1 gym hook: dbghelp.dll proxy (the exe imports only MiniDumpWriteDump from it).

   Install: copy bin\dbghelp.dll next to DoorKickers.exe. Undo: delete it.
   On load it IAT-patches the exe's PeekMessageW/GetMessageW, so our code runs on the game's main
   thread once per frame, between frames (no game update in flight). Each frame it checks the file
   bridge <game>\dk1bridge\in.txt; first line "seq N", then one command per line. It answers in
   out.txt: "seq N", the results, "END". Commands:
     humans                       one line per Human: id team type state x y
     path <id> <x> <y> [...]      Human::DeletePath, then Human::AddToPath per point
     cmd <type> <entity> <v1x> <v1y> <v2x> <v2y> <i1> <i2>   Game::Server_ProcessCommand(sClientCommand)
     restart                      Game::RestartMap
   RVAs and layouts come from DoorKickers.pdb (tools/dk1/dk1sym.py; list in PORTS-HOOKS.md). */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define RVA_GAME_INSTANCE   0x3caa08
#define RVA_GET_HUMANS      0x159020  /* List<Human*>* Game::GetMapHumansList() */
#define RVA_PROCESS_COMMAND 0x169340  /* void Game::Server_ProcessCommand(sClientCommand*) */
#define RVA_RESTART_MAP     0x1541d0  /* void Game::RestartMap() */
#define RVA_SET_STATE       0x14bb90  /* void Game::SetState(eState) */
#define RVA_FINISH_DEPLOY   0x16afd0  /* void Game::Client_FinishDeploy() */
#define RVA_PAUSE           0x1605e0  /* void Game::Server_Pause(int) */
#define RVA_RESUME          0x160650  /* void Game::Server_Resume(int) */
#define RVA_PAUSE_TOGGLE    0x160540  /* void Game::Server_PauseToggle(int) */
#define RVA_GENERATE_PATH   0x1620d0  /* static Waypoints* Game::GeneratePath(..., Vector2 from, Vector2 to) */
#define RVA_SET_AI_PATH     0x0a6be0  /* void Human::SetAIPath(Waypoints*) */
#define RVA_DELETE_PATH     0x09f770  /* void Human::DeletePath() */
#define RVA_ADD_TO_PATH     0x0a1520  /* Vector2 Human::AddToPath(...): hidden ret ptr, bool, x, y (call order at 0x16a0f6) */

typedef struct { float x, y; } V2;
typedef struct { int type; unsigned entity; V2 v1, v2; int i1, i2; } sClientCommand;
typedef struct { int size; void **list; int count; char user; } List;

/* thiscall via fastcall: ecx = this, edx = unused */
typedef List *(__fastcall *GetHumans_t)(void *game, void *edx);
typedef void (__fastcall *ProcessCommand_t)(void *game, void *edx, sClientCommand *c);
typedef void (__fastcall *Void_t)(void *self, void *edx);
typedef void *(__stdcall *GeneratePath_t)(int cls, V2 from, V2 to);
typedef void (__fastcall *SetAIPath_t)(void *human, void *edx, void *wp);
typedef void (__fastcall *SetState_t)(void *game, void *edx, int state);
typedef void (__fastcall *DoorOpen_t)(void *door, void *edx, int how, float a, float b);
typedef BYTE (__fastcall *TraceLOS_t)(void *coll, void *edx, unsigned mask, unsigned shooter, unsigned target, int *out, int x0, int y0, int x1, int y1);
typedef int *(__fastcall *ToColl_t)(void *game, void *edx, int *ret, float x, float y);
typedef V2 *(__fastcall *AddToPath_t)(void *human, void *edx, V2 *ret, int flag, float x, float y);

static BYTE *g_base;
static char g_in[MAX_PATH], g_out[MAX_PATH], g_tmp[MAX_PATH];
static BOOL (WINAPI *real_Peek)(LPMSG, HWND, UINT, UINT, UINT);
static BOOL (WINAPI *real_Get)(LPMSG, HWND, UINT, UINT);
static HMODULE g_real_dbghelp;

#define F(rva) ((void *)(g_base + (rva)))

static char g_last[200], g_crash[MAX_PATH];  /* last bridge line, crash log path */
static LONG CALLBACK veh(EXCEPTION_POINTERS *e)
{
    /* first-chance log of access violations etc. to dk1bridge\crash.txt: code, eip (+RVA), fault address,
       last bridge command, game state/time, a stack scan for code addresses */
    static int n;
    DWORD c = e->ExceptionRecord->ExceptionCode;
    if ((c == 0xC0000005 || c == 0xC000001D || c == 0xC0000094 || c == 0xC00000FD || c == 0xC0000374) && n < 40) {
        FILE *f = fopen(g_crash, "a");
        DWORD *sp = (DWORD *)e->ContextRecord->Esp;
        BYTE *gm = *(BYTE **)(g_base + RVA_GAME_INSTANCE);
        int i, k = 0;
        n++;
        if (f) {
            fprintf(f, "%lu EXC %08lx eip %08lx rva %lx addr %08lx rw %lu | last '%s' | state %d time %u map %d/%d\n", GetTickCount(), c,
                    (DWORD)e->ExceptionRecord->ExceptionAddress, (DWORD)e->ExceptionRecord->ExceptionAddress - (DWORD)g_base,
                    e->ExceptionRecord->NumberParameters > 1 ? (DWORD)e->ExceptionRecord->ExceptionInformation[1] : 0,
                    e->ExceptionRecord->NumberParameters > 0 ? (DWORD)e->ExceptionRecord->ExceptionInformation[0] : 0, g_last,
                    gm ? *(int *)(gm + 4) : -1, gm ? *(unsigned *)(gm + 0xc) : 0, gm ? *(int *)(gm + 0xc4) : -1, gm ? *(int *)(gm + 0xc8) : -1);
            fprintf(f, "   stack rvas:");
            __try {
                for (i = 0; i < 400 && k < 14; i++)
                    if (sp[i] > (DWORD)g_base && sp[i] < (DWORD)g_base + 0x400000) { fprintf(f, " %lx", sp[i] - (DWORD)g_base); k++; }
            } __except (EXCEPTION_EXECUTE_HANDLER) {}
            fprintf(f, "\n");
            fclose(f);
        }
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

static void *game(void) { return *(void **)F(RVA_GAME_INSTANCE); }

static void run_line(char *line, FILE *out)
{
    char *tok = strtok(line, " \t\r\n");
    void *g = game();
    if (!tok) return;
    if (!g) { fprintf(out, "ERR no game\n"); return; }
    if (!strcmp(tok, "humans")) {
        /* GetMapHumansList = &maps[cur]->humans (game+0xcc -> +0x20 array, +0x2c index); outside a
           mission that list is stale, and an unchecked count hung the game (AppHang 10-24) */
        List *l;
        int i;
        if (!*(void **)((BYTE *)g + 0xcc)) { fprintf(out, "ERR no map\n"); return; }
        l = ((GetHumans_t)F(RVA_GET_HUMANS))(g, 0);
        if (!l || !l->list || l->count < 0 || l->count > 1024) { fprintf(out, "ERR bad list\n"); return; }
        for (i = 0; i < l->count; i++) {
            BYTE *h = (BYTE *)l->list[i];
            if (!h || *(int *)(h + 0x18) != 2) continue;
            fprintf(out, "%u %d %d %d %.2f %.2f %d\n", *(unsigned *)(h + 0x94), *(int *)(h + 0x90),
                    *(int *)(h + 0xa8), *(int *)(h + 0xfc), *(float *)(h + 0x1c), *(float *)(h + 0x20),
                    ((List *)(h + 0x15c))->count);  /* m_waypoints count */
        }
    } else if (!strcmp(tok, "path")) {
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);  /* Entity::g_entityPool[8192] */
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL;
        char *sx, *sy;
        V2 r;
        if (!h || *(int *)(h + 0x18) != 2) { fprintf(out, "ERR not a human %u\n", id); return; }
        ((Void_t)F(RVA_DELETE_PATH))(h, 0);
        while ((sx = strtok(NULL, " \t\r\n")) && (sy = strtok(NULL, " \t\r\n")))
            ((AddToPath_t)F(RVA_ADD_TO_PATH))(h, 0, &r, 0, (float)atof(sx), (float)atof(sy));
        fprintf(out, "OK path %u\n", id);
    } else if (!strcmp(tok, "goto")) {
        /* pathfinding move, as Editor::OnAssignPathToSelection / AI patrols do:
           Waypoints* GeneratePath(human+0xa0, from, to) (static stdcall, ret 0x14), Human::SetAIPath(wp).
           (AddToPath only draws a straight segment and stops at the first wall.) */
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL;
        V2 to;
        void *wp;
        if (!h || *(int *)(h + 0x18) != 2) { fprintf(out, "ERR not a human %u\n", id); return; }
        to.x = (float)atof(strtok(NULL, " \t\r\n"));
        to.y = (float)atof(strtok(NULL, " \t\r\n"));
        ((Void_t)F(RVA_DELETE_PATH))(h, 0);
        wp = ((GeneratePath_t)F(RVA_GENERATE_PATH))(*(int *)(h + 0xa0), *(V2 *)(h + 0x1c), to);
        if (!wp) { fprintf(out, "ERR no path %u\n", id); return; }
        ((SetAIPath_t)F(RVA_SET_AI_PATH))(h, 0, wp);
        fprintf(out, "OK goto %u\n", id);
    } else if (!strcmp(tok, "move")) {
        /* player-style order: CREATE_PATH (cmd 6, v2 = start) then ADD_TO_PATH (cmd 10, v1 = point) for every
           point of GeneratePath (Waypoints: m_vPoints list +0x20, data +0x24, count +0x28, sPoint 12 bytes,
           origin +4), then clear m_bSelected (0x11c) = mouse-up, else UpdateWaypointsMove holds at the last point.
           A straight ADD_TO_PATH is clipped at the first wall, hence the pathfinder points. */
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL, *wp, *pts;
        sClientCommand c;
        V2 to;
        int i, n;
        if (!h || *(int *)(h + 0x18) != 2) { fprintf(out, "ERR not a human %u\n", id); return; }
        to.x = (float)atof(strtok(NULL, " \t\r\n"));
        to.y = (float)atof(strtok(NULL, " \t\r\n"));
        wp = ((GeneratePath_t)F(RVA_GENERATE_PATH))(*(int *)(h + 0xa0), *(V2 *)(h + 0x1c), to);
        if (!wp) { fprintf(out, "ERR no path %u\n", id); return; }
        pts = *(BYTE **)(wp + 0x24);
        n = *(int *)(wp + 0x28);
        memset(&c, 0, sizeof c);
        c.type = 6; c.entity = id; c.v1 = c.v2 = *(V2 *)(h + 0x1c);
        ((ProcessCommand_t)F(RVA_PROCESS_COMMAND))(g, 0, &c);
        for (i = 0; i < n && i < 256; i++) {
            c.type = 10; c.v1 = *(V2 *)(pts + 12 * i + 4);
            ((ProcessCommand_t)F(RVA_PROCESS_COMMAND))(g, 0, &c);
        }
        h[0x11c] = 0;
        fprintf(out, "OK move %u pts %d\n", id, n);
    } else if (!strcmp(tok, "cmd")) {
        sClientCommand c;
        memset(&c, 0, sizeof c);
        c.type = atoi(strtok(NULL, " \t\r\n"));
        c.entity = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        c.v1.x = (float)atof(strtok(NULL, " \t\r\n")); c.v1.y = (float)atof(strtok(NULL, " \t\r\n"));
        c.v2.x = (float)atof(strtok(NULL, " \t\r\n")); c.v2.y = (float)atof(strtok(NULL, " \t\r\n"));
        c.i1 = atoi(strtok(NULL, " \t\r\n")); c.i2 = atoi(strtok(NULL, " \t\r\n"));
        ((ProcessCommand_t)F(RVA_PROCESS_COMMAND))(g, 0, &c);
        fprintf(out, "OK cmd %d\n", c.type);
    } else if (!strcmp(tok, "state")) {
        /* Game::m_state (eState: 5 MAIN_MENU, 6 GAME_LOADING .. 9 DEPLOY, 10 RUNNING, 12 ENDED),
           m_mapListIndex, m_mapIndex, m_pMap */
        BYTE *b = (BYTE *)g;
        fprintf(out, "%d %d %d %p time %u speed %.2f pause %x\n", *(int *)(b + 4), *(int *)(b + 0xc4), *(int *)(b + 0xc8),
                *(void **)(b + 0xcc), *(unsigned *)(b + 0xc), *(float *)(b + 0x14), *(unsigned *)(b + 0x18));
    } else if (!strcmp(tok, "toggle")) {
        int who = atoi(strtok(NULL, " \t\r\n"));
        ((SetState_t)F(RVA_PAUSE_TOGGLE))(g, 0, who);
        fprintf(out, "OK toggle %d pause %x\n", who, *(unsigned *)((BYTE *)g + 0x18));
    } else if (!strcmp(tok, "resume") || !strcmp(tok, "pause")) {
        /* Server_Resume/Server_Pause(int who): bitmask Game+0x18 |= flags[who] (table at VA 0x7af8b8) */
        int who = atoi(strtok(NULL, " \t\r\n"));
        ((SetState_t)F(tok[0] == 'r' ? RVA_RESUME : RVA_PAUSE))(g, 0, who);
        fprintf(out, "OK %s %d pause %x\n", tok, who, *(unsigned *)((BYTE *)g + 0x18));
    } else if (!strcmp(tok, "load")) {
        /* UpdateGameLoading calls LoadMap(m_mapListIndex, m_mapIndex): set them, enter GAME_LOADING */
        BYTE *b = (BYTE *)g;
        *(int *)(b + 0xc4) = atoi(strtok(NULL, " \t\r\n"));  /* eMapList: 0 SINGLE 1 RANDOM 2 KILLHOUSE 3 CAMPAIGN */
        *(int *)(b + 0xc8) = atoi(strtok(NULL, " \t\r\n"));
        ((SetState_t)F(RVA_SET_STATE))(g, 0, 6);
        fprintf(out, "OK load\n");
    } else if (!strcmp(tok, "setstate")) {
        ((SetState_t)F(RVA_SET_STATE))(g, 0, atoi(strtok(NULL, " \t\r\n")));
        fprintf(out, "OK setstate\n");
    } else if (!strcmp(tok, "dbg")) {
        /* movement gate of Human::UpdateWaypointsMove: stops if (flags 0x2b8 >> 5 | byte 0x29c) & 1 or
           (flags & 9) == 1; uses the last m_waypoints segment (data +0x160, count +0x164) if seg+0x10 == 0 and
           seg+0x28 (points) != 0; while selected (0x11c) only moves when seg+0xc (cursor) < points-1 */
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL, *seg = NULL;
        int n;
        if (!h || *(int *)(h + 0x18) != 2) { fprintf(out, "ERR not a human %u\n", id); return; }
        n = *(int *)(h + 0x164);
        if (n > 0 && n < 64) seg = (*(BYTE ***)(h + 0x160))[n - 1];
        fprintf(out, "sel %d flags %x b29c %d awps %d segs %d", h[0x11c], *(unsigned *)(h + 0x2b8), h[0x29c],
                *(int *)(h + 0x19c), n);
        if (seg) fprintf(out, " seg b10 %d cur %d pts %d", seg[0x10], *(int *)(seg + 0xc), *(int *)(seg + 0x28));
        fprintf(out, "\n");
    } else if (!strcmp(tok, "maps")) {
        /* map list counts: Game::GetMapList(i) = g_pGame+0x74+i*0x10, List {cap, data, count} */
        BYTE *g = *(BYTE **)F(0x3caa0c);
        int i;
        for (i = 0; i < 4; i++) fprintf(out, "list %d count %d\n", i, *(int *)(g + 0x74 + i * 0x10 + 8));
    } else if (!strcmp(tok, "cgrid")) {
        /* collision grid = the game's own wall/door/prop map (Game+0x120 Collision: +0 w, +4 h, +8 uint32 cells).
           A cell blocks line of sight when (v & 0x10) (Collision::TraceLineOfSight is called with mask 0x10);
           0x80000000 = border/default, treated as blocked. Header "G w h mapW mapH", then h rows of w chars:
           '#' blocked, '.' open. Map point -> cell: see `c2g`. */
        BYTE *c = *(BYTE **)((BYTE *)g + 0x120), *mp = *(BYTE **)((BYTE *)g + 0xcc), *m;
        int w, hh, x, y;
        unsigned *d;
        if (!c || !mp) { fprintf(out, "ERR no collision\n"); return; }
        m = (*(BYTE ***)(mp + 0x20))[*(int *)(mp + 0x2c)];
        w = *(int *)c; hh = *(int *)(c + 4); d = *(unsigned **)(c + 8);
        if (w <= 0 || hh <= 0 || w > 4096 || hh > 4096 || !d) { fprintf(out, "ERR bad grid %d %d\n", w, hh); return; }
        fprintf(out, "G %d %d %d %d\n", w, hh, *(int *)(m + 4), *(int *)(m + 8));
        for (y = 0; y < hh; y++) {
            for (x = 0; x < w; x++) { unsigned v = d[y * w + x]; fputc(v == 0x80000000u || (v & 0x10) ? '#' : '.', out); }
            fputc('\n', out);
        }
    } else if (!strcmp(tok, "chist")) {
        /* histogram of collision cell values: low 16 bits (flags) x has-entity-id (high 16 bits != 0) */
        BYTE *c = *(BYTE **)((BYTE *)g + 0x120);
        int w, hh, i, k, nb = 0;
        unsigned *d, key[64], cnt[64];
        if (!c) { fprintf(out, "ERR no collision\n"); return; }
        w = *(int *)c; hh = *(int *)(c + 4); d = *(unsigned **)(c + 8);
        for (i = 0; i < w * hh; i++) {
            unsigned v = d[i], kk = v == 0x80000000u ? 0xffffffffu : ((v & 0xffff) | ((v >> 16) ? 0x10000u : 0));
            for (k = 0; k < nb && key[k] != kk; k++);
            if (k == nb) { if (nb == 64) continue; key[nb] = kk; cnt[nb++] = 0; }
            cnt[k]++;
        }
        for (k = 0; k < nb; k++) fprintf(out, "%08x %u\n", key[k], cnt[k]);
    } else if (!strcmp(tok, "c2g")) {
        /* Game::ConvertMapToCollisionCoords(x, y) */
        float x = (float)atof(strtok(NULL, " \t\r\n")), y = (float)atof(strtok(NULL, " \t\r\n"));
        int r[2];
        ((ToColl_t)F(0x161480))(g, 0, r, x, y);
        fprintf(out, "%d %d\n", r[0], r[1]);
    } else if (!strcmp(tok, "los")) {
        /* los x1 y1 x2 y2 (map coords): the game's Collision::TraceLineOfSight with mask 0x10 -> "1|0 hitx hity" (1 = clear) */
        float v[4];
        int i, a[2], b[2], hit[2] = {-1, -1};
        BYTE r;
        BYTE *c = *(BYTE **)((BYTE *)g + 0x120);
        for (i = 0; i < 4; i++) v[i] = (float)atof(strtok(NULL, " \t\r\n"));
        if (!c) { fprintf(out, "ERR no collision\n"); return; }
        ((ToColl_t)F(0x161480))(g, 0, a, v[0], v[1]);
        ((ToColl_t)F(0x161480))(g, 0, b, v[2], v[3]);
        r = ((TraceLOS_t)F(0x4f010))(c, 0, 0x10, 0x7ffe0000u, 0x7fff0000u, hit, a[0], a[1], b[0], b[1]);
        fprintf(out, "%d %d %d\n", r ? 1 : 0, hit[0], hit[1]);
    } else if (!strcmp(tok, "opendoors")) {
        /* opendoors: Door::Open(how 0, 0, 0) on every closed Door in the entity pool. A trooper whose route crosses a closed
           door stops dead (Human +0x29c bit 0 set) until somebody opens it; the gym brains do not issue door actions. */
        void **pool = (void **)F(0x3c0c70);
        void *v1 = F(0x3accc8), *v2 = F(0x3accd0);
        int i, n = 0, t = 0;
        for (i = 0; i < 8192; i++) {
            BYTE *e = (BYTE *)pool[i];
            if (!e || (*(void **)e != v1 && *(void **)e != v2)) continue;
            t++;
            if (e[0xa4] & 1) continue;
            ((DoorOpen_t)F(0x91b20))(e, 0, 0, 0.0f, 0.0f);
            n++;
        }
        fprintf(out, "OK doors %d opened %d\n", t, n);
    } else if (!strcmp(tok, "route")) {
        /* route id x y: the pathfinder's points (GeneratePath -> Waypoints list +0x24 data / +0x28 count, sPoint 12 B,
           origin +4), nobody moves. `path` is manual drawing (DeletePath + AddToPath per given point): it never had any. */
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL, *wp, *pts;
        V2 to;
        int i, n;
        if (!h || *(int *)(h + 0x18) != 2) { fprintf(out, "ERR not a human %u\n", id); return; }
        to.x = (float)atof(strtok(NULL, " \t\r\n"));
        to.y = (float)atof(strtok(NULL, " \t\r\n"));
        wp = ((GeneratePath_t)F(RVA_GENERATE_PATH))(*(int *)(h + 0xa0), *(V2 *)(h + 0x1c), to);
        if (!wp) { fprintf(out, "ERR no path %u\n", id); return; }
        pts = *(BYTE **)(wp + 0x24);
        n = *(int *)(wp + 0x28);
        if (n < 0 || n > 512 || (n && !pts)) { fprintf(out, "ERR bad route %d\n", n); return; }
        fprintf(out, "R %d", n);
        for (i = 0; i < n; i++) fprintf(out, " %.0f %.0f", *(float *)(pts + 12 * i + 4), *(float *)(pts + 12 * i + 8));
        fputc('\n', out);
    } else if (!strcmp(tok, "poke")) {
        /* poke id off byte: one byte of a human (debug) */
        unsigned id = (unsigned)atoi(strtok(NULL, " \t\r\n"));
        void **pool = (void **)F(0x3c0c70);
        BYTE *h = id < 8192 ? (BYTE *)pool[id] : NULL;
        int off = (int)strtol(strtok(NULL, " \t\r\n"), NULL, 0);
        if (!h || *(int *)(h + 0x18) != 2 || off < 0 || off >= 0x400) { fprintf(out, "ERR poke\n"); return; }
        h[off] = (BYTE)atoi(strtok(NULL, " \t\r\n"));
        fprintf(out, "OK poke\n");
    } else if (!strcmp(tok, "deploy")) {
        /* maps with a deploy screen stop in eState 9 DEPLOY with troopers at their default entry points:
           Game::Client_FinishDeploy() = the GO button */
        ((Void_t)F(RVA_FINISH_DEPLOY))(g, 0);
        fprintf(out, "OK deploy state %d\n", *(int *)((BYTE *)g + 4));
    } else if (!strcmp(tok, "deploygo")) {
        /* the GO button itself: DeployScreen::OnDeployGO (game+0x28 = DeployScreen) */
        BYTE *ds = *(BYTE **)((BYTE *)g + 0x28);
        if (!ds) { fprintf(out, "ERR no deployscreen\n"); return; }
        ((Void_t)F(0x88c20))(ds, 0);
        fprintf(out, "OK deploygo state %d ds %d\n", *(int *)((BYTE *)g + 4), *(int *)(ds + 4));
    } else if (!strcmp(tok, "dslots")) {
        /* DeployScreen (game+0x28) slots: array +0xc, count +0x10, 0x14 bytes each; GetDeployedHumans
           takes slot+4 (object, its +0x70 == Entity::s_playerTeam) when slot+8 != 0 */
        BYTE *ds = *(BYTE **)((BYTE *)g + 0x28);
        int i, n;
        if (!ds) { fprintf(out, "ERR no deployscreen\n"); return; }
        n = *(int *)(ds + 0x10);
        fprintf(out, "ds state %d n %d playerTeam %d\n", *(int *)(ds + 4), n, *(int *)F(0x3c0c6c));  /* Entity::s_playerTeam */
        for (i = 0; i < n && i < 64; i++) {
            int *s = (int *)(*(BYTE **)(ds + 0xc) + i * 0x14);
            BYTE *o = (BYTE *)s[1];
            fprintf(out, "%d: %x %p %x %x %x obj70 %d\n", i, s[0], o, s[2], s[3], s[4], o ? *(int *)(o + 0x70) : -1);
        }
    } else if (!strcmp(tok, "restart")) {
        ((Void_t)F(RVA_RESTART_MAP))(g, 0);
        fprintf(out, "OK restart\n");
    } else {
        fprintf(out, "ERR unknown %s\n", tok);
    }
}

static void poll_bridge(void)
{
    static DWORD last;
    char line[1024], seq[64] = "seq ?\n";
    FILE *in, *out;
    if (GetTickCount() - last < 50) return;
    last = GetTickCount();
    if (GetFileAttributesA(g_in) == INVALID_FILE_ATTRIBUTES) return;
    in = fopen(g_in, "r");
    if (!in) return;
    out = fopen(g_tmp, "w");
    if (!out) { fclose(in); return; }
    if (fgets(seq, sizeof seq, in)) fputs(seq, out);
    while (fgets(line, sizeof line, in)) {
        strncpy(g_last, line, sizeof g_last - 1); g_last[sizeof g_last - 1] = 0;
        { char *nl = strpbrk(g_last, "\r\n"); if (nl) *nl = 0; }
        __try { run_line(line, out); }
        __except (EXCEPTION_EXECUTE_HANDLER) { fprintf(out, "ERR exception %08lx\n", GetExceptionCode()); }
    }
    fputs("END\n", out);
    fclose(in);
    fclose(out);
    DeleteFileA(g_in);
    MoveFileExA(g_tmp, g_out, MOVEFILE_REPLACE_EXISTING);
}

static BOOL WINAPI hook_Peek(LPMSG m, HWND w, UINT a, UINT b, UINT r) { poll_bridge(); return real_Peek(m, w, a, b, r); }
static BOOL WINAPI hook_Get(LPMSG m, HWND w, UINT a, UINT b) { poll_bridge(); return real_Get(m, w, a, b); }

/* Bot mode (10-29): the gym runs DK1 while the user types elsewhere, and the game stole focus on launch and on
   every mission load. When focusguard's bot marker for doorkickers.exe is live (dk1gym.py mark_bot()), the game's
   own focus calls become no-ops and its windows never activate. A DK1 the user starts later plays normally. */
static int g_bot;
static BOOL (WINAPI *real_Show)(HWND, int);
static BOOL (WINAPI *real_Pos)(HWND, HWND, int, int, int, int, UINT);
static HDWP (WINAPI *real_Defer)(HDWP, HWND, HWND, int, int, int, int, UINT);
static HWND (WINAPI *real_CreateA)(DWORD, LPCSTR, LPCSTR, DWORD, int, int, int, int, HWND, HMENU, HINSTANCE, LPVOID);
static HWND (WINAPI *real_CreateW)(DWORD, LPCWSTR, LPCWSTR, DWORD, int, int, int, int, HWND, HMENU, HINSTANCE, LPVOID);

static BOOL WINAPI hook_Fg(HWND w) { return TRUE; }
static HWND WINAPI hook_Focus(HWND w) { return GetFocus(); }
static BOOL WINAPI hook_Show(HWND w, int c)
{
    if (c == SW_SHOWNORMAL || c == SW_SHOW || c == SW_SHOWMAXIMIZED || c == SW_RESTORE || c == SW_SHOWDEFAULT)
        c = SW_SHOWNOACTIVATE;
    return real_Show(w, c);
}
static BOOL WINAPI hook_Pos(HWND w, HWND a, int x, int y, int cx, int cy, UINT f) { return real_Pos(w, a, x, y, cx, cy, f | SWP_NOACTIVATE); }
static HDWP WINAPI hook_Defer(HDWP d, HWND w, HWND a, int x, int y, int cx, int cy, UINT f) { return real_Defer(d, w, a, x, y, cx, cy, f | SWP_NOACTIVATE); }
static HWND WINAPI hook_CreateA(DWORD ex, LPCSTR c, LPCSTR n, DWORD st, int x, int y, int w, int h, HWND p, HMENU m, HINSTANCE i, LPVOID l)
{
    /* WS_VISIBLE at creation still activated the window (10-29): create hidden, then show without activating */
    HWND r;
    if (p) return real_CreateA(ex, c, n, st, x, y, w, h, p, m, i, l);
    r = real_CreateA(ex | WS_EX_NOACTIVATE, c, n, st & ~WS_VISIBLE, x, y, w, h, p, m, i, l);
    if (r && (st & WS_VISIBLE)) real_Show(r, SW_SHOWNOACTIVATE);
    return r;
}
static HWND WINAPI hook_CreateW(DWORD ex, LPCWSTR c, LPCWSTR n, DWORD st, int x, int y, int w, int h, HWND p, HMENU m, HINSTANCE i, LPVOID l)
{
    HWND r;
    if (p) return real_CreateW(ex, c, n, st, x, y, w, h, p, m, i, l);
    r = real_CreateW(ex | WS_EX_NOACTIVATE, c, n, st & ~WS_VISIBLE, x, y, w, h, p, m, i, l);
    if (r && (st & WS_VISIBLE)) real_Show(r, SW_SHOWNOACTIVATE);
    return r;
}

static int bot_marker(void)
{
    char path[MAX_PATH], buf[64] = {0};
    FILE *f;
    if (!GetEnvironmentVariableA("USERPROFILE", path, MAX_PATH)) return 0;
    strcat(path, "\\Documents\\Tools\\focusguard\\botlaunch\\doorkickers.exe");
    if (!(f = fopen(path, "r"))) return 0;
    fread(buf, 1, sizeof buf - 1, f);
    fclose(f);
    return atof(buf) > (double)time(NULL);
}

static void patch_iat(void)
{
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)g_base;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(g_base + dos->e_lfanew);
    IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(g_base +
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    FARPROC peek = GetProcAddress(GetModuleHandleA("user32"), "PeekMessageW");
    FARPROC get = GetProcAddress(GetModuleHandleA("user32"), "GetMessageW");
    HMODULE u = GetModuleHandleA("user32");
    FARPROC fg = GetProcAddress(u, "SetForegroundWindow"), show = GetProcAddress(u, "ShowWindow"),
            pos = GetProcAddress(u, "SetWindowPos"), defer = GetProcAddress(u, "DeferWindowPos"),
            ca = GetProcAddress(u, "CreateWindowExA"), focus = GetProcAddress(u, "SetFocus"), cw = GetProcAddress(u, "CreateWindowExW");
    real_Show = (void *)show;
    for (; imp->Name; imp++) {
        IMAGE_THUNK_DATA *t = (IMAGE_THUNK_DATA *)(g_base + imp->FirstThunk);
        for (; t->u1.Function; t++) {
            void *p = NULL;
            DWORD old;
            if ((FARPROC)t->u1.Function == peek) { real_Peek = (void *)peek; p = hook_Peek; }
            else if ((FARPROC)t->u1.Function == get) { real_Get = (void *)get; p = hook_Get; }
            else if (g_bot && (FARPROC)t->u1.Function == fg) p = hook_Fg;
            else if (g_bot && (FARPROC)t->u1.Function == focus) p = hook_Focus;
            else if (g_bot && (FARPROC)t->u1.Function == show) { real_Show = (void *)show; p = hook_Show; }
            else if (g_bot && (FARPROC)t->u1.Function == pos) { real_Pos = (void *)pos; p = hook_Pos; }
            else if (g_bot && (FARPROC)t->u1.Function == defer) { real_Defer = (void *)defer; p = hook_Defer; }
            else if (g_bot && (FARPROC)t->u1.Function == ca) { real_CreateA = (void *)ca; p = hook_CreateA; }
            else if (g_bot && (FARPROC)t->u1.Function == cw) { real_CreateW = (void *)cw; p = hook_CreateW; }
            if (!p) continue;
            VirtualProtect(&t->u1.Function, 4, PAGE_READWRITE, &old);
            t->u1.Function = (DWORD)(DWORD_PTR)p;
            VirtualProtect(&t->u1.Function, 4, old, &old);
        }
    }
}

/* the one export the exe imports; forwarded to the system dbghelp */
BOOL WINAPI MiniDumpWriteDump(HANDLE p, DWORD pid, HANDLE f, int type, void *e, void *u, void *c)
{
    typedef BOOL (WINAPI *fn_t)(HANDLE, DWORD, HANDLE, int, void *, void *, void *);
    if (!g_real_dbghelp) {
        char path[MAX_PATH];
        GetSystemDirectoryA(path, MAX_PATH);  /* SysWOW64 for this 32-bit process */
        strcat(path, "\\dbghelp.dll");
        g_real_dbghelp = LoadLibraryA(path);
    }
    return g_real_dbghelp ? ((fn_t)GetProcAddress(g_real_dbghelp, "MiniDumpWriteDump"))(p, pid, f, type, e, u, c) : FALSE;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD why, LPVOID r)
{
    if (why == DLL_PROCESS_ATTACH) {
        char dir[MAX_PATH], *s;
        DisableThreadLibraryCalls(inst);
        g_base = (BYTE *)GetModuleHandleA(NULL);
        GetModuleFileNameA(NULL, dir, MAX_PATH);
        if ((s = strrchr(dir, '\\'))) *s = 0;
        strcat(dir, "\\dk1bridge");
        CreateDirectoryA(dir, NULL);
        sprintf(g_in, "%s\\in.txt", dir);
        sprintf(g_out, "%s\\out.txt", dir);
        sprintf(g_tmp, "%s\\out.tmp", dir);
        sprintf(g_crash, "%s\\crash.txt", dir);
        AddVectoredExceptionHandler(1, veh);
        g_bot = bot_marker();
        patch_iat();
    }
    return TRUE;
}
