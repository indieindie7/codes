// Solus (UE4, x64, D3D11) FPS graph: winmm.dll proxy.
// Hooks IDXGISwapChain::Present (shared vtable, found via a throwaway device) and draws
// an fps readout + scrolling frame-time bars top-right with ID3D11DeviceContext1::ClearView
// (solid rects, touches no pipeline state).
// F10 = toggle graph. solus_fps.ini next to the dll: graph=1 log=1 key=121 (VK code).
// Log: solus_fps.log next to the dll, one line per second: fps avg, worst ms.
#include <windows.h>
#include <d3d11_1.h>
#include <dxgi.h>
#include <stdio.h>
#include <stdarg.h>
#include "winmm_exports.h"

static char g_dir[MAX_PATH], g_log[MAX_PATH];
static int g_show = 1, g_dolog = 1, g_key = VK_F10;
static void logf(const char* f, ...) {
    if (!g_log[0]) return;
    FILE* fp = fopen(g_log, "a");
    if (!fp) return;
    va_list a; va_start(a, f); vfprintf(fp, f, a); va_end(a);
    fputc('\n', fp); fclose(fp);
}

enum { N = 240, BARW = 2, GH = 96, MARGIN = 10 };
static float g_ms[N]; static int g_head;
static LARGE_INTEGER g_freq, g_last;
static double g_acc_ms, g_worst; static int g_acc_n; static float g_fps, g_avgms;
static bool g_keydown, g_first = true;

// 3x5 font: digits 0-9, '.', 15 bits each, row-major, bit 14 = top-left
static const unsigned short FONT[11] = {
    0x7B6F, 0x2C97, 0x73E7, 0x73CF, 0x5BC9, 0x79CF, 0x79EF, 0x7249, 0x7BEF, 0x7BCF, 0x0002 };

static void rect(ID3D11DeviceContext1* c, ID3D11RenderTargetView* v, int x, int y, int w, int h, const float* col) {
    if (w <= 0 || h <= 0) return;
    D3D11_RECT r = { x, y, x + w, y + h };
    c->ClearView(v, col, &r, 1);
}
static int text(ID3D11DeviceContext1* c, ID3D11RenderTargetView* v, int x, int y, int s, const char* t, const float* col) {
    static const float blk[4] = { 0, 0, 0, 1 };
    for (int pass = 0; pass < 2; pass++) {
        int cx = x;
        for (const char* p = t; *p; p++) {
            int g = (*p >= '0' && *p <= '9') ? *p - '0' : (*p == '.' ? 10 : -1);
            if (g >= 0) for (int i = 0; i < 15; i++) if (FONT[g] & (1 << (14 - i))) {
                int px = cx + (i % 3) * s, py = y + (i / 3) * s;
                if (pass == 0) rect(c, v, px + s / 2, py + s / 2, s, s, blk);   // shadow
                else rect(c, v, px, py, s, s, col);
            }
            cx += 4 * s;
        }
        if (pass == 1) return cx;
    }
    return x;
}

static void draw(IDXGISwapChain* sc) {
    ID3D11Device* dev = nullptr; ID3D11DeviceContext* ctx = nullptr; ID3D11DeviceContext1* c1 = nullptr;
    ID3D11Texture2D* bb = nullptr; ID3D11RenderTargetView* rtv = nullptr;
    if (SUCCEEDED(sc->GetDevice(__uuidof(ID3D11Device), (void**)&dev))) {
        dev->GetImmediateContext(&ctx);
        if (ctx && SUCCEEDED(ctx->QueryInterface(__uuidof(ID3D11DeviceContext1), (void**)&c1)) &&
            SUCCEEDED(sc->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&bb)) &&
            SUCCEEDED(dev->CreateRenderTargetView(bb, nullptr, &rtv))) {
            D3D11_TEXTURE2D_DESC td; bb->GetDesc(&td);
            if (g_first) { g_first = false; logf("first draw: backbuffer %ux%u fmt %d", td.Width, td.Height, td.Format); }
            static const float green[4] = { 0.1f, 0.9f, 0.2f, 1 }, yellow[4] = { 1, 0.85f, 0.1f, 1 },
                red[4] = { 1, 0.15f, 0.1f, 1 }, white[4] = { 1, 1, 1, 1 }, grey[4] = { 0.55f, 0.55f, 0.55f, 1 };
            int gw = N * BARW, x0 = (int)td.Width - gw - MARGIN, y0 = MARGIN + 22, base = y0 + GH;
            if (x0 > 0 && base < (int)td.Height) {
                for (int i = 0; i < N; i++) {
                    float ms = g_ms[(g_head + i) % N];
                    if (ms <= 0) continue;
                    int h = (int)(ms * GH / 33.33f); if (h < 1) h = 1; if (h > GH) h = GH;
                    rect(c1, rtv, x0 + i * BARW, base - h, BARW, h, ms <= 16.7f ? green : ms <= 33.4f ? yellow : red);
                }
                rect(c1, rtv, x0, base - GH / 2, gw, 1, grey);   // 16.7 ms line
                rect(c1, rtv, x0, base, gw, 1, grey);
                char b[32];
                sprintf(b, "%d", (int)(g_fps + 0.5f));
                text(c1, rtv, x0, MARGIN, 3, b, g_fps >= 59 ? green : g_fps >= 29 ? yellow : red);
                sprintf(b, "%.1f", g_avgms);
                text(c1, rtv, x0 + 70, MARGIN, 3, b, white);
            }
        } else if (g_first) { g_first = false; logf("first draw FAILED (ctx1=%p bb=%p rtv=%p)", c1, bb, rtv); }
    }
    if (rtv) rtv->Release(); if (bb) bb->Release(); if (c1) c1->Release(); if (ctx) ctx->Release(); if (dev) dev->Release();
}

typedef HRESULT (STDMETHODCALLTYPE* Present_t)(IDXGISwapChain*, UINT, UINT);
static Present_t o_Present, g_real;   // o_Present = whatever was in the vtable; g_real = dxgi's own Present (from the dll file)
static __declspec(thread) int t_depth;
static bool g_reent_logged;

// Steam overlay re-hooks the same vtable slot and can end up calling us as "its original" while
// our original is the overlay: endless recursion. Real Present comes from dxgi.dll on disk.
static Present_t real_from_disk(void** slot) {
    HMODULE m = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)slot, &m) || !m) return nullptr;
    wchar_t path[MAX_PATH]; if (!GetModuleFileNameW(m, path, MAX_PATH)) return nullptr;
    BYTE* base = (BYTE*)m;
    IMAGE_NT_HEADERS64* nt = (IMAGE_NT_HEADERS64*)(base + ((IMAGE_DOS_HEADER*)base)->e_lfanew);
    DWORD rva = (DWORD)((BYTE*)slot - base), off = 0;
    IMAGE_SECTION_HEADER* sh = IMAGE_FIRST_SECTION(nt);
    for (int i = 0; i < nt->FileHeader.NumberOfSections; i++)
        if (rva >= sh[i].VirtualAddress && rva + 8 <= sh[i].VirtualAddress + sh[i].SizeOfRawData) off = rva - sh[i].VirtualAddress + sh[i].PointerToRawData;
    if (!off) return nullptr;
    HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
    if (f == INVALID_HANDLE_VALUE) return nullptr;
    BYTE hdr[0x1000]; DWORD n = 0; ULONGLONG val = 0, disk_base = 0;
    bool ok = ReadFile(f, hdr, sizeof(hdr), &n, nullptr) && n == sizeof(hdr);
    if (ok) { IMAGE_NT_HEADERS64* dn = (IMAGE_NT_HEADERS64*)(hdr + ((IMAGE_DOS_HEADER*)hdr)->e_lfanew); disk_base = dn->OptionalHeader.ImageBase; }
    ok = ok && SetFilePointer(f, off, nullptr, FILE_BEGIN) != INVALID_SET_FILE_POINTER && ReadFile(f, &val, 8, &n, nullptr) && n == 8;
    CloseHandle(f);
    if (!ok || val < disk_base || val - disk_base >= nt->OptionalHeader.SizeOfImage) return nullptr;
    // Steam overlay inline-hooks the start of Present and calls back through the vtable (= us).
    // Build our own entry past its jump: first 14 bytes from the dll file (position independent
    // for this dxgi build, checked below), then an absolute jump to real+14.
    static const BYTE want[14] = { 0x48,0x89,0x5c,0x24,0x10, 0x48,0x89,0x74,0x24,0x18, 0x55, 0x57, 0x41,0x56 };
    DWORD frva = (DWORD)(val - disk_base), foff = 0; BYTE pro[14] = {};
    for (int i = 0; i < nt->FileHeader.NumberOfSections; i++)
        if (frva >= sh[i].VirtualAddress && frva + 14 <= sh[i].VirtualAddress + sh[i].SizeOfRawData) foff = frva - sh[i].VirtualAddress + sh[i].PointerToRawData;
    f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
    ok = foff && f != INVALID_HANDLE_VALUE && SetFilePointer(f, foff, nullptr, FILE_BEGIN) != INVALID_SET_FILE_POINTER && ReadFile(f, pro, 14, &n, nullptr) && n == 14;
    if (f != INVALID_HANDLE_VALUE) CloseHandle(f);
    if (!ok || memcmp(pro, want, 14)) { logf("dxgi Present prologue differs from the known one: graph disabled"); return nullptr; }
    BYTE* t = (BYTE*)VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!t) return nullptr;
    memcpy(t, pro, 14); t[14] = 0xFF; t[15] = 0x25; *(DWORD*)(t + 16) = 0;
    *(ULONGLONG*)(t + 20) = (ULONGLONG)(base + frva + 14);
    BYTE* live = base + frva;
    logf("live Present starts %02x %02x %02x %02x %02x (disk 48 89 5c 24 10)", live[0], live[1], live[2], live[3], live[4]);
    logf("dxgi %ls slot rva %lx -> real Present rva %llx (vtable now %p)", path, rva, val - disk_base, *slot);
    return (Present_t)t;
}

static HRESULT STDMETHODCALLTYPE h_Present(IDXGISwapChain* sc, UINT sync, UINT flags) {
    if (t_depth > 0) {   // re-entered through another hook's chain: go straight to dxgi
        if (!g_reent_logged) { g_reent_logged = true; logf("re-entry (overlay chain) -> real Present"); }
        return g_real(sc, sync, flags);
    }
    struct Depth { Depth() { t_depth++; } ~Depth() { t_depth--; } } guard;
    if (!(flags & DXGI_PRESENT_TEST)) {
        LARGE_INTEGER now; QueryPerformanceCounter(&now);
        if (g_last.QuadPart) {
            double ms = (now.QuadPart - g_last.QuadPart) * 1000.0 / g_freq.QuadPart;
            g_ms[g_head] = (float)ms; g_head = (g_head + 1) % N;
            g_acc_ms += ms; g_acc_n++; if (ms > g_worst) g_worst = ms;
            if (g_acc_ms >= 1000.0) {
                g_avgms = (float)(g_acc_ms / g_acc_n); g_fps = 1000.0f / g_avgms;
                if (g_dolog) logf("fps %.1f avg %.2f ms worst %.2f ms", g_fps, g_avgms, g_worst);
                g_acc_ms = 0; g_acc_n = 0; g_worst = 0;
            }
        }
        g_last = now;
        bool down = (GetAsyncKeyState(g_key) & 0x8000) != 0;
        if (down && !g_keydown) {
            DXGI_SWAP_CHAIN_DESC d;
            if (SUCCEEDED(sc->GetDesc(&d)) && GetForegroundWindow() == d.OutputWindow) g_show = !g_show;
        }
        g_keydown = down;
        if (g_show) draw(sc);
    }
    return o_Present(sc, sync, flags);
}

static LRESULT CALLBACK dummy_proc(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProcA(h, m, w, l); }

static DWORD WINAPI installer(LPVOID) {
    WNDCLASSA wc = {}; wc.lpfnWndProc = dummy_proc; wc.hInstance = GetModuleHandleA(nullptr); wc.lpszClassName = "SolusFpsDummy";
    RegisterClassA(&wc);
    HWND w = CreateWindowExA(WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE, wc.lpszClassName, "d", WS_POPUP, 0, 0, 64, 64, nullptr, nullptr, wc.hInstance, nullptr);
    DXGI_SWAP_CHAIN_DESC d = {};
    d.BufferCount = 1; d.BufferDesc.Width = 64; d.BufferDesc.Height = 64; d.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    d.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT; d.OutputWindow = w; d.SampleDesc.Count = 1; d.Windowed = TRUE;
    IDXGISwapChain* sc = nullptr; ID3D11Device* dev = nullptr; ID3D11DeviceContext* ctx = nullptr;
    HRESULT hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &d, &sc, &dev, nullptr, &ctx);
    if (FAILED(hr)) hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &d, &sc, &dev, nullptr, &ctx);
    if (SUCCEEDED(hr) && sc) {
        void** vt = *(void***)sc;
        g_real = real_from_disk(&vt[8]);
        if (g_real) {
            DWORD old; VirtualProtect(&vt[8], sizeof(void*), PAGE_READWRITE, &old);
            o_Present = (Present_t)vt[8]; vt[8] = (void*)h_Present;
            VirtualProtect(&vt[8], sizeof(void*), old, &old);
            logf("Present hooked (vtable %p, previous %p, real %p)", vt, o_Present, g_real);
        } else logf("real Present not resolved: graph disabled, no hook");
        sc->Release(); ctx->Release(); dev->Release();
    } else logf("dummy device failed %08lx", hr);
    DestroyWindow(w);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD why, LPVOID) {
    if (why == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        HMODULE pin; GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_PIN | GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, (LPCSTR)&DllMain, &pin);
        GetModuleFileNameA(inst, g_dir, MAX_PATH);
        char* s = strrchr(g_dir, '\\'); if (s) s[1] = 0;
        char ini[MAX_PATH]; sprintf(ini, "%ssolus_fps.ini", g_dir);
        g_show = GetPrivateProfileIntA("fps", "graph", 1, ini);
        g_dolog = GetPrivateProfileIntA("fps", "log", 1, ini);
        g_key = GetPrivateProfileIntA("fps", "key", VK_F10, ini);
        sprintf(g_log, "%ssolus_fps.log", g_dir);
        DeleteFileA(g_log);
        QueryPerformanceFrequency(&g_freq);
        logf("attach pid %lu graph=%d log=%d key=%d", GetCurrentProcessId(), g_show, g_dolog, g_key);
        CloseHandle(CreateThread(nullptr, 0, installer, nullptr, 0, nullptr));
    }
    return TRUE;
}
