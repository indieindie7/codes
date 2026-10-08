/*
 * bake_kernel.c - CPU ray tracer for U2Bake: BVH over world triangles, then per sample point
 * direct light (sun + point lights, shadow rays), sky visibility, and diffuse bounce.
 *
 *   zig cc -target x86_64-windows-gnu -O2 -shared -o bake_kernel.dll bake_kernel.c
 *
 * Called from bake.py through ctypes. Units are Unreal units; no engine code is involved.
 * Bounce: for each sample, RAYS cosine-weighted hemisphere rays; a ray that hits a surface q adds
 * albedo(q) * E_direct(q) (one bounce, next-event estimate at q; E_direct(q) = sun + lights with
 * shadow rays + sky * SKYHIT, no extra rays), a ray that escapes adds the sky colour.
 * With bounces=2 the hit point gathers BOUNCE2_RAYS more rays itself (slow; for reference bakes).
 */
#include <windows.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct { float x, y, z; } V3;
static V3 v3(float x, float y, float z) { V3 r = { x, y, z }; return r; }
static V3 add(V3 a, V3 b) { return v3(a.x + b.x, a.y + b.y, a.z + b.z); }
static V3 sub(V3 a, V3 b) { return v3(a.x - b.x, a.y - b.y, a.z - b.z); }
static V3 mul(V3 a, float s) { return v3(a.x * s, a.y * s, a.z * s); }
static V3 vmul(V3 a, V3 b) { return v3(a.x * b.x, a.y * b.y, a.z * b.z); }
static float dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static V3 cross(V3 a, V3 b) { return v3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static V3 norm(V3 a) { float l = sqrtf(dot(a, a)); return l > 1e-20f ? mul(a, 1.0f / l) : v3(0, 0, 1); }

/* ---- scene ---- */
typedef struct { V3 a, e1, e2, n; V3 alb; } Tri;
typedef struct { float lo[3], hi[3]; int left, first, count; } Node;   /* count>0: leaf */

static Tri *T; static int NT;
static Node *N; static int NN;
static int *TI;                                      /* triangle index order */

static float cen(int t, int ax)
{
	Tri *r = &T[t];
	float a = (&r->a.x)[ax], b = a + (&r->e1.x)[ax], c = a + (&r->e2.x)[ax];
	return (a + b + c) * (1.0f / 3.0f);
}

static void bounds(int first, int count, float *lo, float *hi)
{
	int i, k;
	for (k = 0; k < 3; k++) { lo[k] = 1e30f; hi[k] = -1e30f; }
	for (i = first; i < first + count; i++)
	{
		Tri *r = &T[TI[i]];
		for (k = 0; k < 3; k++)
		{
			float a = (&r->a.x)[k], b = a + (&r->e1.x)[k], c = a + (&r->e2.x)[k];
			float mn = fminf(a, fminf(b, c)), mx = fmaxf(a, fmaxf(b, c));
			if (mn < lo[k]) lo[k] = mn;
			if (mx > hi[k]) hi[k] = mx;
		}
	}
}

static int g_ax;
static int cmpc(const void *x, const void *y)
{
	float a = cen(*(const int *)x, g_ax), b = cen(*(const int *)y, g_ax);
	return a < b ? -1 : a > b;
}

/* median split on the longest axis, leaves of <= 4 triangles; right children stored in RIGHT */
static int *RIGHT;
static int build2(int first, int count)
{
	int me = NN++, k, ax = 0, half, l, r;
	float ext[3];
	bounds(first, count, N[me].lo, N[me].hi);
	if (count <= 4) { N[me].first = first; N[me].count = count; N[me].left = -1; RIGHT[me] = -1; return me; }
	for (k = 0; k < 3; k++) ext[k] = N[me].hi[k] - N[me].lo[k];
	if (ext[1] > ext[ax]) ax = 1;
	if (ext[2] > ext[ax]) ax = 2;
	g_ax = ax;
	qsort(TI + first, count, sizeof(int), cmpc);
	half = count / 2;
	l = build2(first, half);
	r = build2(first + half, count - half);
	N[me].count = 0; N[me].first = 0; N[me].left = l; RIGHT[me] = r;
	return me;
}

static int boxhit(const Node *n, V3 o, V3 inv, float tmax)
{
	float t0 = 0, t1 = tmax, a, b, tmp;
	int k;
	for (k = 0; k < 3; k++)
	{
		float oo = (&o.x)[k], ii = (&inv.x)[k];
		a = (n->lo[k] - oo) * ii; b = (n->hi[k] - oo) * ii;
		if (a > b) { tmp = a; a = b; b = tmp; }
		if (a > t0) t0 = a;
		if (b < t1) t1 = b;
		if (t0 > t1) return 0;
	}
	return 1;
}

/* closest hit (any=0) or any hit (any=1) within tmax; returns triangle or -1 */
static int trace(V3 o, V3 d, float tmax, int any, float *thit)
{
	int stack[128], sp = 0, best = -1, i;
	V3 inv = v3(1.0f / (fabsf(d.x) > 1e-12f ? d.x : 1e-12f), 1.0f / (fabsf(d.y) > 1e-12f ? d.y : 1e-12f),
	            1.0f / (fabsf(d.z) > 1e-12f ? d.z : 1e-12f));
	if (!NN) return -1;
	stack[sp++] = 0;
	while (sp)
	{
		int ni = stack[--sp];
		const Node *n = &N[ni];
		if (!boxhit(n, o, inv, tmax)) continue;
		if (n->left < 0)
		{
			for (i = n->first; i < n->first + n->count; i++)
			{
				const Tri *r = &T[TI[i]];
				V3 p = cross(d, r->e2), s, q;
				float det = dot(r->e1, p), id, u, v, t;
				if (fabsf(det) < 1e-12f) continue;
				id = 1.0f / det;
				s = sub(o, r->a);
				u = dot(s, p) * id;
				if (u < 0 || u > 1) continue;
				q = cross(s, r->e1);
				v = dot(d, q) * id;
				if (v < 0 || u + v > 1) continue;
				t = dot(r->e2, q) * id;
				if (t > 1e-3f && t < tmax)
				{
					tmax = t; best = TI[i];
					if (any) { *thit = t; return best; }
				}
			}
		}
		else if (sp < 126)
		{
			stack[sp++] = n->left;
			stack[sp++] = RIGHT[ni];
		}
	}
	*thit = tmax;
	return best;
}

/* ---- lighting ---- */
typedef struct { V3 p; float radius; V3 col; } Light;
static Light *L; static int NL;
static V3 SUNDIR, SUNCOL, SKY; static int HAVESUN;
static float EPS = 2.0f, SKYHIT = 0.5f, MAXDIST = 200000.0f;
static int RAYS = 64, BOUNCES = 1, B2RAYS = 8;

typedef struct { unsigned s; } Rng;
static float rnd(Rng *r) { r->s = r->s * 1664525u + 1013904223u; return (r->s >> 8) * (1.0f / 16777216.0f); }

static void basis(V3 n, V3 *t, V3 *b)
{
	V3 up = fabsf(n.z) < 0.9f ? v3(0, 0, 1) : v3(1, 0, 0);
	*t = norm(cross(up, n)); *b = cross(n, *t);
}

static V3 cosdir(V3 n, Rng *r)
{
	float u1 = rnd(r), u2 = rnd(r), rr = sqrtf(u1), ph = 6.2831853f * u2;
	V3 t, b;
	basis(n, &t, &b);
	return norm(add(add(mul(t, rr * cosf(ph)), mul(b, rr * sinf(ph))), mul(n, sqrtf(fmaxf(0.0f, 1 - u1)))));
}

/* sun + point lights at p with normal n, shadow rays */
static V3 direct(V3 p, V3 n)
{
	V3 e = v3(0, 0, 0), o = add(p, mul(n, EPS));
	float th;
	int i;
	if (HAVESUN)
	{
		V3 tosun = mul(SUNDIR, -1.0f);
		float c = dot(n, tosun);
		if (c > 0 && trace(o, tosun, MAXDIST, 1, &th) < 0) e = add(e, mul(SUNCOL, c));
	}
	for (i = 0; i < NL; i++)
	{
		V3 d = sub(L[i].p, o);
		float dist = sqrtf(dot(d, d)), c, f;
		if (dist >= L[i].radius || dist < 1e-3f) continue;
		d = mul(d, 1.0f / dist);
		c = dot(n, d);
		if (c <= 0) continue;
		f = 1.0f - dist / L[i].radius;            /* approximate UE2 falloff */
		f *= f;
		if (trace(o, d, dist - 1.0f, 1, &th) >= 0) continue;
		e = add(e, mul(L[i].col, c * f));
	}
	return e;
}

static V3 gather(V3 p, V3 n, int rays, int depth, Rng *rg, V3 *skyout)
{
	V3 acc = v3(0, 0, 0), sky = v3(0, 0, 0), o = add(p, mul(n, EPS));
	int k;
	for (k = 0; k < rays; k++)
	{
		V3 d = cosdir(n, rg);
		float th;
		int t = trace(o, d, MAXDIST, 0, &th);
		if (t < 0) { sky = add(sky, SKY); continue; }
		{
			const Tri *r = &T[t];
			V3 q = add(o, mul(d, th)), qn = r->n, eq;
			if (dot(qn, d) > 0) qn = mul(qn, -1.0f);        /* face the ray (two-sided) */
			eq = add(direct(q, qn), mul(SKY, SKYHIT));
			if (depth > 1)
			{
				V3 dummy;
				eq = add(eq, gather(q, qn, B2RAYS, depth - 1, rg, &dummy));
			}
			acc = add(acc, vmul(r->alb, eq));
		}
	}
	if (skyout) *skyout = mul(sky, 1.0f / rays);
	return mul(acc, 1.0f / rays);
}

/* ---- work split ---- */
static const float *SP, *SN; static float *RESULT; static int NS; static volatile LONG NEXT; static unsigned SEED;

static DWORD WINAPI worker(LPVOID unused)
{
	(void)unused;
	for (;;)
	{
		LONG i = InterlockedIncrement(&NEXT) - 1;
		V3 p, n, d, s, b;
		Rng rg;
		if (i >= NS) return 0;
		p = v3(SP[i * 3], SP[i * 3 + 1], SP[i * 3 + 2]);
		n = norm(v3(SN[i * 3], SN[i * 3 + 1], SN[i * 3 + 2]));
		rg.s = SEED ^ (unsigned)(i * 2654435761u);
		d = direct(p, n);
		b = BOUNCES > 0 ? gather(p, n, RAYS, BOUNCES, &rg, &s) : v3(0, 0, 0);
		if (BOUNCES <= 0) s = v3(0, 0, 0);
		RESULT[i * 9 + 0] = d.x; RESULT[i * 9 + 1] = d.y; RESULT[i * 9 + 2] = d.z;
		RESULT[i * 9 + 3] = s.x; RESULT[i * 9 + 4] = s.y; RESULT[i * 9 + 5] = s.z;
		RESULT[i * 9 + 6] = b.x; RESULT[i * 9 + 7] = b.y; RESULT[i * 9 + 8] = b.z;
	}
}

/* tri: 9 floats per triangle (a,b,c world); alb: 3 per triangle; outward normal = cross(b-a, c-a).
   lights: 7 per light (x,y,z, radius, r,g,b). sun: 7 (dir x,y,z = direction the light travels, r,g,b, on).
   opts: [eps, skyhit, far]. out: 9 per sample (direct rgb, sky rgb, bounce rgb). Returns 0 on success. */
__declspec(dllexport) int bake(int ntri, const float *tri, const float *alb,
                               int nsamp, const float *pos, const float *nrm,
                               int nlight, const float *lights, const float *sun, const float *sky,
                               int rays, int bounces, int bounce2rays, unsigned seed, const float *opts,
                               float *out, int nthreads)
{
	int i;
	HANDLE th[64];
	T = (Tri *)malloc(sizeof(Tri) * (ntri ? ntri : 1));
	TI = (int *)malloc(sizeof(int) * (ntri ? ntri : 1));
	N = (Node *)malloc(sizeof(Node) * (2 * ntri + 1));
	RIGHT = (int *)malloc(sizeof(int) * (2 * ntri + 1));
	L = (Light *)malloc(sizeof(Light) * (nlight ? nlight : 1));
	if (!T || !TI || !N || !RIGHT || !L) return 1;
	for (i = 0; i < ntri; i++)
	{
		V3 a = v3(tri[i * 9], tri[i * 9 + 1], tri[i * 9 + 2]), b = v3(tri[i * 9 + 3], tri[i * 9 + 4], tri[i * 9 + 5]),
		   c = v3(tri[i * 9 + 6], tri[i * 9 + 7], tri[i * 9 + 8]);
		T[i].a = a; T[i].e1 = sub(b, a); T[i].e2 = sub(c, a);
		T[i].n = norm(cross(T[i].e1, T[i].e2));
		T[i].alb = v3(alb[i * 3], alb[i * 3 + 1], alb[i * 3 + 2]);
		TI[i] = i;
	}
	NT = ntri; NN = 0;
	if (ntri) build2(0, ntri);
	for (i = 0; i < nlight; i++)
	{
		L[i].p = v3(lights[i * 7], lights[i * 7 + 1], lights[i * 7 + 2]);
		L[i].radius = lights[i * 7 + 3];
		L[i].col = v3(lights[i * 7 + 4], lights[i * 7 + 5], lights[i * 7 + 6]);
	}
	NL = nlight;
	SUNDIR = norm(v3(sun[0], sun[1], sun[2])); SUNCOL = v3(sun[3], sun[4], sun[5]); HAVESUN = sun[6] != 0;
	SKY = v3(sky[0], sky[1], sky[2]);
	EPS = opts[0]; SKYHIT = opts[1]; MAXDIST = opts[2];
	RAYS = rays > 0 ? rays : 1; BOUNCES = bounces; B2RAYS = bounce2rays > 0 ? bounce2rays : 1; SEED = seed;
	SP = pos; SN = nrm; RESULT = out; NS = nsamp; NEXT = 0;
	if (nthreads < 1) nthreads = 1;
	if (nthreads > 64) nthreads = 64;
	for (i = 0; i < nthreads; i++) th[i] = CreateThread(NULL, 0, worker, NULL, 0, NULL);
	WaitForMultipleObjects(nthreads, th, TRUE, INFINITE);
	for (i = 0; i < nthreads; i++) CloseHandle(th[i]);
	free(T); free(TI); free(N); free(RIGHT); free(L);
	return 0;
}
