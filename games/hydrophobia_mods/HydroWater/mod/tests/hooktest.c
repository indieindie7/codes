/* hooktest.exe: exercises the detour, trampoline and the xmm0 return thunks against a fake
   solver with the game's prologue bytes and return convention, and the sheet bridge against a
   fake sheet laid out like the game's. 32-bit, built by tests\build.ps1. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

extern BYTE *hw_test_target;
void hw_test_setup(const wchar_t *dir, int mode);
int hw_test_install(void);
void hw_test_mode(int mode);

/* the fake game solver: same prologue as FUN_00d5c9d0, counts calls in sheet[0x90],
   returns dt * 0.5 in xmm0 */
const float half = 0.5f;   /* non-static: referenced from asm as _half */
__attribute__((naked)) static void FakeSolver(void)
{
    __asm__ volatile(
        ".byte 0x55, 0x8b, 0xec, 0x83, 0xe4, 0xf0\n\t"   /* push ebp; mov ebp,esp; and esp,-16, the game's encoding */
        "movl 8(%%ebp), %%eax\n\t"
        "incl 0x240(%%eax)\n\t"
        "movss 12(%%ebp), %%xmm0\n\t"
        "mulss _half, %%xmm0\n\t"
        "movl %%ebp, %%esp\n\t"
        "popl %%ebp\n\t"
        "ret\n\t"
        ::: "memory");
}

/* call a (sheet, dt) solver that returns in xmm0 */
__attribute__((naked)) static float CallXmm(void *fn, uint32_t *S, float dt)
{
    __asm__ volatile(
        "pushl 12(%%esp)\n\t"
        "pushl 12(%%esp)\n\t"
        "call *12(%%esp)\n\t"
        "addl $8, %%esp\n\t"
        "subl $4, %%esp\n\t"
        "movss %%xmm0, (%%esp)\n\t"
        "flds (%%esp)\n\t"
        "addl $4, %%esp\n\t"
        "ret\n\t"
        ::: "memory");
}

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL: " __VA_ARGS__); printf("\n"); } else { printf("ok: " __VA_ARGS__); printf("\n"); } } while (0)

static float *Plane(int n) { return (float *)calloc((size_t)n, sizeof(float)); }

int main(void)
{
    uint32_t S[0x100];
    int w = 10, h = 8, stride, rows, n, r, i, idx;
    float *planes[0x20];
    float ret, vol0, vol1;
    wchar_t dir[MAX_PATH];

    GetCurrentDirectoryW(MAX_PATH, dir);
    hw_test_setup(dir, 1);
    hw_test_target = (BYTE *)FakeSolver;
    CHECK(hw_test_install() == 1, "hook installed on the fake solver");
    CHECK(hw_test_target[0] == 0xE9, "entry now starts with a jmp");

    memset(S, 0, sizeof S);
    /* passthrough: the trampoline must run the original and hand back its xmm0 */
    ret = CallXmm(hw_test_target, S, 0.04f);
    CHECK(fabsf(ret - 0.02f) < 1e-7f, "passthrough returns the original's xmm0 (%.4f)", ret);
    CHECK(S[0x90] == 1, "passthrough ran the original (counter %u)", S[0x90]);

    /* the fake sheet, laid out like the game's */
    stride = ((w + 3) / 4) * 4 + 4 + 4;  /* [2] = padded + 4, row stride = [2] + 4 */
    S[1] = (uint32_t)w; S[2] = (uint32_t)(stride - 4); S[3] = (uint32_t)h;
    *(float *)&S[4] = 20.0f; *(float *)&S[7] = 1.0f / 20.0f; *(float *)&S[8] = 0.5f; *(float *)&S[9] = 980.0f;
    S[0x17] = 2; S[0x6b] = 0; *(float *)&S[0x60] = 0.1f; *(float *)&S[0xb1] = 0.0f; *(float *)&S[0xb2] = 0.0f;
    rows = h + 4; n = rows * stride;
    for (i = 10; i <= 0x1d; i++) { planes[i] = Plane(n); S[i] = (uint32_t)(uintptr_t)planes[i]; }
    idx = 0; S[0] = (uint32_t)idx;
    vol0 = 0;
    for (r = 2; r < rows - 2; r++)
        for (i = 2; i < stride - 2 && i < w + 2; i++) {
            float d = 30.0f + ((r == 5 && i == 6) ? 10.0f : 0.0f);
            planes[10][r * stride + i] = d; vol0 += d;
        }
    for (r = 0; r < rows; r++) { planes[0x19][r * stride + 2] = 1.0f / 20.0f; } /* a wall column */

    hw_test_mode(2);
    ret = CallXmm(hw_test_target, S, 0.04f);
    CHECK(fabsf(ret - 0.04f) < 1e-7f, "hw mode consumed the whole dt (%.4f)", ret);
    CHECK(S[0] == 1, "buffer index flipped (%u)", S[0]);
    CHECK(S[0x43] == 1, "two-stage step counter incremented (%u)", S[0x43]);
    CHECK(fabsf(*(float *)&S[0x24] - 0.04f) < 1e-7f, "last dt stored");
    CHECK(S[0x90] == 1, "the original was not called in hw mode (counter %u)", S[0x90]);
    vol1 = 0;
    for (r = 2; r < rows - 2; r++)
        for (i = 2; i < w + 2; i++) vol1 += planes[11][r * stride + i];
    CHECK(fabsf(vol1 - vol0) < 1e-2f * vol0 / 100.0f, "volume conserved into the other buffer (%.3f -> %.3f)", vol0, vol1);
    CHECK(planes[11][5 * stride + 6] < 40.0f && planes[11][5 * stride + 6] > 30.0f, "the bump started to spread (%.3f)", planes[11][5 * stride + 6]);
    CHECK(planes[0x13][5 * stride + 6] > 170.0f, "wave-speed plane written (%.1f)", planes[0x13][5 * stride + 6]);
    CHECK(planes[0x14][5 * stride + 7] > 0.0f, "u plane shows flow away from the bump (%.3f)", planes[0x14][5 * stride + 7]);
    CHECK(planes[0x1c][5 * stride + 7] != 0.0f, "flow accumulator advanced");

    /* a second step reads from the flipped buffer */
    ret = CallXmm(hw_test_target, S, 0.04f);
    CHECK(S[0] == 0 && S[0x43] == 2, "second step flipped back");

    /* flat sheets go to the original */
    S[0x6b] = 1;
    ret = CallXmm(hw_test_target, S, 0.04f);
    CHECK(S[0x90] == 2 && fabsf(ret - 0.02f) < 1e-7f, "flat sheet forwarded to the original");

    printf("%s (%d failures)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
