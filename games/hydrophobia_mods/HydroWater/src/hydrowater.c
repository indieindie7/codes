/* HydroWater - see hydrowater.h. */
#include "hydrowater.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define EPS_H 1e-6f          /* below this a cell is dry */
#define MOM_CAP 1000.0f      /* the game's momentum cap, |hu| <= MOM_CAP h */

struct hw_sheet {
    int w, h, stride, rows, n;
    float dx, g, cfl;
    hw_opts o;
    float *hA, *huA, *hvA;   /* state buffers: in, half, out */
    float *hB, *huB, *hvB;
    float *hC, *huC, *hvC;
    float *u, *v, *c;        /* derived */
    float *B, *wall;         /* bed, per-cell wall */
    unsigned char *wallx, *wally;
    float *b, *bprev;        /* stage 1 planes */
    float *Beff;             /* B + bprev when displacement is on, else B */
    float *edge;             /* stage 8: 1 near a wet/dry edge */
    float smax, last_dt;
    /* stage 7 */
    float *foam, *air, *hprev, *impact, *ftmp, *atmp;
    float *spray; int nspray;
    hw_foam_params fp;
    unsigned rng;
};

static float *plane(const hw_sheet *s) { return (float *)calloc((size_t)s->n, sizeof(float)); }
#define AT(s, i, j) (((j) + 2) * (s)->stride + (i) + 2)

HW_API hw_sheet *hw_create(int w, int h, float dx, float g, float cfl)
{
    hw_sheet *s = (hw_sheet *)calloc(1, sizeof(hw_sheet));
    int i, j;
    s->w = w; s->h = h; s->stride = w + 4; s->rows = h + 4; s->n = s->stride * s->rows;
    s->dx = dx; s->g = g; s->cfl = cfl;
    s->o.alpha = 1.0f; s->o.c_adapt = 0.2f; s->o.edge_damp = 0.7f;
    s->hA = plane(s); s->huA = plane(s); s->hvA = plane(s);
    s->hB = plane(s); s->huB = plane(s); s->hvB = plane(s);
    s->hC = plane(s); s->huC = plane(s); s->hvC = plane(s);
    s->u = plane(s); s->v = plane(s); s->c = plane(s);
    s->B = plane(s); s->wall = plane(s); s->b = plane(s); s->bprev = plane(s); s->edge = plane(s); s->Beff = plane(s);
    s->foam = plane(s); s->air = plane(s); s->hprev = plane(s); s->impact = plane(s);
    s->ftmp = plane(s); s->atmp = plane(s);
    s->spray = (float *)calloc(HW_SPRAY_CAP * 8, sizeof(float));
    s->rng = 0x9e3779b9u;
    s->fp.foam_gain = 0.8f; s->fp.air_gain = 3.0f; s->fp.foam_life = 2.5f; s->fp.lace = 0.25f;
    s->fp.bubble_rise = 25.0f; s->fp.air_to_foam = 0.35f; s->fp.spread = 3.0f;
    s->fp.spray_rate = 30.0f; s->fp.spray_foam = 0.15f; s->fp.spray_drag = 0.5f; s->fp.spray_max = 4096;
    s->wallx = (unsigned char *)calloc((size_t)s->n, 1);
    s->wally = (unsigned char *)calloc((size_t)s->n, 1);
    /* the border is wall in both models so nothing leaves the sheet */
    for (j = -2; j < h + 2; j++)
        for (i = -2; i < w + 2; i++)
            if (i < 0 || j < 0 || i >= w || j >= h) {
                s->wall[AT(s, i, j)] = 1.0f;
                s->wallx[AT(s, i, j)] = 1; s->wally[AT(s, i, j)] = 1;
                if (i - 1 >= -2) s->wallx[AT(s, i - 1, j)] = 1;
                if (j - 1 >= -2) s->wally[AT(s, i, j - 1)] = 1;
            }
    return s;
}

HW_API void hw_destroy(hw_sheet *s)
{
    if (!s) return;
    free(s->hA); free(s->huA); free(s->hvA); free(s->hB); free(s->huB); free(s->hvB);
    free(s->hC); free(s->huC); free(s->hvC); free(s->u); free(s->v); free(s->c);
    free(s->B); free(s->wall); free(s->b); free(s->bprev); free(s->edge); free(s->Beff);
    free(s->foam); free(s->air); free(s->hprev); free(s->impact); free(s->ftmp); free(s->atmp); free(s->spray);
    free(s->wallx); free(s->wally); free(s);
}

HW_API void hw_set_opts(hw_sheet *s, const hw_opts *o)
{
    s->o = *o;
    if (s->o.alpha <= 0) s->o.alpha = 1.0f;
    if (s->o.c_adapt <= 0) s->o.c_adapt = 0.2f;
    if (s->o.edge_damp <= 0) s->o.edge_damp = 0.7f;
}
HW_API int hw_width(const hw_sheet *s) { return s->w; }
HW_API int hw_height(const hw_sheet *s) { return s->h; }
HW_API int hw_stride(const hw_sheet *s) { return s->stride; }
HW_API float *hw_depth(hw_sheet *s) { return s->hA; }
HW_API float *hw_hu(hw_sheet *s) { return s->huA; }
HW_API float *hw_hv(hw_sheet *s) { return s->hvA; }
HW_API float *hw_u(hw_sheet *s) { return s->u; }
HW_API float *hw_v(hw_sheet *s) { return s->v; }
HW_API float *hw_bed(hw_sheet *s) { return s->B; }
HW_API float *hw_wall(hw_sheet *s) { return s->wall; }
HW_API unsigned char *hw_wallx(hw_sheet *s) { return s->wallx; }
HW_API unsigned char *hw_wally(hw_sheet *s) { return s->wally; }
HW_API float *hw_body(hw_sheet *s) { return s->b; }
HW_API float hw_smax(const hw_sheet *s) { return s->smax; }

HW_API void hw_fill(hw_sheet *s, float eta)
{
    int i, j;
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j);
            if (s->wall[k] > 0) continue;
            s->hA[k] = eta > s->B[k] ? eta - s->B[k] : 0.0f;
            s->huA[k] = s->hvA[k] = 0.0f;
        }
}

HW_API void hw_wall_rect(hw_sheet *s, int i0, int j0, int i1, int j1)
{
    int i, j;
    for (j = j0; j < j1; j++)
        for (i = i0; i < i1; i++) {
            if (i < 0 || j < 0 || i >= s->w || j >= s->h) continue;
            s->wall[AT(s, i, j)] = 1.0f;
            s->hA[AT(s, i, j)] = s->huA[AT(s, i, j)] = s->hvA[AT(s, i, j)] = 0.0f;
            s->wallx[AT(s, i, j)] = 1; s->wallx[AT(s, i - 1, j)] = 1;
            s->wally[AT(s, i, j)] = 1; s->wally[AT(s, i, j - 1)] = 1;
        }
}

/* a wall segment blocks every cell face it crosses: walk the segment in small steps and flag
   the face between the cell before and after each crossing */
HW_API void hw_wall_segment(hw_sheet *s, float x0, float z0, float x1, float z1)
{
    float len = sqrtf((x1 - x0) * (x1 - x0) + (z1 - z0) * (z1 - z0));
    int steps = (int)(len / (0.1f * s->dx)) + 1, k;
    int pi = (int)floorf(x0 / s->dx), pj = (int)floorf(z0 / s->dx);
    for (k = 1; k <= steps; k++) {
        float t = (float)k / steps;
        float x = x0 + (x1 - x0) * t, z = z0 + (z1 - z0) * t;
        int ci = (int)floorf(x / s->dx), cj = (int)floorf(z / s->dx);
        while (ci != pi || cj != pj) {
            if (ci != pi) {
                int lo = ci < pi ? ci : pi;
                if (lo >= -2 && lo < s->w + 1 && pj >= -2 && pj < s->h + 2) s->wallx[AT(s, lo, pj)] = 1;
                pi += ci > pi ? 1 : -1;
            } else {
                int lo = cj < pj ? cj : pj;
                if (pi >= -2 && pi < s->w + 2 && lo >= -2 && lo < s->h + 1) s->wally[AT(s, pi, lo)] = 1;
                pj += cj > pj ? 1 : -1;
            }
        }
    }
}

/* ------------------------------------------------------------------ stage 1: bodies */

HW_API void hw_bodies_begin(hw_sheet *s) { memset(s->b, 0, (size_t)s->n * sizeof(float)); }

static float body_cell(hw_sheet *s, int i, int j, float cover, float ybottom, float ytop)
{
    int k;
    float eta, top, bot, sub, col;
    if (i < 0 || j < 0 || i >= s->w || j >= s->h) return 0.0f;
    k = AT(s, i, j);
    /* the column counts what bodies already pushed out of this cell (bprev): measuring against
       hA alone made a resting body displace, then see a short column, release it, and repeat */
    col = s->hA[k] + s->bprev[k];
    if (s->wall[k] > 0 || col <= EPS_H) return 0.0f;
    eta = s->Beff[k] + s->hA[k];
    top = ytop < eta ? ytop : eta;
    bot = ybottom > s->B[k] ? ybottom : s->B[k];
    sub = top - bot;
    if (sub <= 0) return 0.0f;
    if (sub > col) sub = col;
    s->b[k] += cover * sub;
    return cover * sub * s->dx * s->dx;
}

HW_API float hw_body_box(hw_sheet *s, float x0, float z0, float x1, float z1, float ybottom, float ytop)
{
    float vol = 0.0f;
    int i0 = (int)floorf(x0 / s->dx), i1 = (int)floorf(x1 / s->dx);
    int j0 = (int)floorf(z0 / s->dx), j1 = (int)floorf(z1 / s->dx), i, j;
    for (j = j0; j <= j1; j++)
        for (i = i0; i <= i1; i++) {
            float cx0 = i * s->dx, cx1 = cx0 + s->dx, cz0 = j * s->dx, cz1 = cz0 + s->dx;
            float ox = (x1 < cx1 ? x1 : cx1) - (x0 > cx0 ? x0 : cx0);
            float oz = (z1 < cz1 ? z1 : cz1) - (z0 > cz0 ? z0 : cz0);
            if (ox <= 0 || oz <= 0) continue;
            vol += body_cell(s, i, j, ox * oz / (s->dx * s->dx), ybottom, ytop);
        }
    return vol;
}

HW_API float hw_body_disc(hw_sheet *s, float x, float z, float r, float ybottom, float ytop)
{
    float vol = 0.0f;
    int i0 = (int)floorf((x - r) / s->dx), i1 = (int)floorf((x + r) / s->dx);
    int j0 = (int)floorf((z - r) / s->dx), j1 = (int)floorf((z + r) / s->dx), i, j;
    for (j = j0; j <= j1; j++)
        for (i = i0; i <= i1; i++) {
            /* 4x4 supersampled coverage of the disc */
            int a, c, in = 0;
            for (a = 0; a < 4; a++)
                for (c = 0; c < 4; c++) {
                    float px = (i + (a + 0.5f) / 4) * s->dx - x, pz = (j + (c + 0.5f) / 4) * s->dx - z;
                    if (px * px + pz * pz <= r * r) in++;
                }
            if (in) vol += body_cell(s, i, j, in / 16.0f, ybottom, ytop);
        }
    return vol;
}

static void apply_displacement(hw_sheet *s)
{
    int i, j;
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j), nb[4], m = 0, q;
            float d = s->o.alpha * (s->b[k] - s->bprev[k]);
            if (d == 0.0f || s->wall[k] > 0) continue;
            if (!s->wallx[AT(s, i - 1, j)]) nb[m++] = AT(s, i - 1, j);
            if (!s->wallx[k]) nb[m++] = AT(s, i + 1, j);
            if (!s->wally[AT(s, i, j - 1)]) nb[m++] = AT(s, i, j - 1);
            if (!s->wally[k]) nb[m++] = AT(s, i, j + 1);
            if (m == 0) continue;
            if (d > 0) {                        /* body entered: push water out */
                if (d > s->hA[k]) d = s->hA[k];
                s->hA[k] -= d;
                for (q = 0; q < m; q++) s->hA[nb[q]] += d / m;
            } else {                            /* body left: pull water back in */
                float take = -d / m;
                for (q = 0; q < m; q++) {
                    float t = take < s->hA[nb[q]] ? take : s->hA[nb[q]];
                    s->hA[nb[q]] -= t;
                    s->hA[k] += t;
                }
            }
        }
    memcpy(s->bprev, s->b, (size_t)s->n * sizeof(float));
    for (i = 0; i < s->n; i++) s->Beff[i] = s->B[i] + s->bprev[i];
}

/* ------------------------------------------------------------------ stage 2: stamp */

HW_API void hw_stamp(hw_sheet *s, float px, float pz, float x, float z, float r, float ybottom,
                     float vx, float vz, float dt)
{
    int nsub = 1, k;
    if (s->o.capped_stamp) {
        float sp = sqrtf(vx * vx + vz * vz);
        nsub = (int)floorf(sp * dt / s->dx + 0.5f);
        if (nsub < 1) nsub = 1;
    }
    for (k = 0; k < nsub; k++) {
        float t = (float)(k + 1) / nsub;
        float cx = px + (x - px) * t, cz = pz + (z - pz) * t;
        int i0 = (int)floorf((cx - r) / s->dx), i1 = (int)floorf((cx + r) / s->dx);
        int j0 = (int)floorf((cz - r) / s->dx), j1 = (int)floorf((cz + r) / s->dx), i, j;
        for (j = j0; j <= j1; j++)
            for (i = i0; i <= i1; i++) {
                float ex, ez, d2, wgt, hh, coeff;
                int c;
                if (i < 0 || j < 0 || i >= s->w || j >= s->h) continue;
                c = AT(s, i, j);
                hh = s->hA[c];
                if (s->wall[c] > 0 || hh <= EPS_H) continue;
                ex = (i + 0.5f) * s->dx - cx; ez = (j + 0.5f) * s->dx - cz;
                d2 = (ex * ex + ez * ez) / (r * r);
                if (d2 >= 1.0f) continue;
                wgt = 1.0f - d2;
                if (!s->o.capped_stamp) {
                    /* the game: overwrite the cell velocity with the body's, weighted */
                    s->u[c] = vx * wgt; s->v[c] = vz * wgt;
                } else {
                    float eta = s->B[c] + hh, depth = eta - ybottom;
                    if (depth <= 0) continue;           /* body above the water */
                    if (depth > hh) depth = hh;
                    coeff = expf(-depth / hh) * s->o.c_adapt * (depth / hh) * dt * wgt;
                    if (coeff > 1.0f) coeff = 1.0f;
                    s->u[c] += coeff * (vx - s->u[c]);
                    s->v[c] += coeff * (vz - s->v[c]);
                }
                s->huA[c] = hh * s->u[c]; s->hvA[c] = hh * s->v[c];
            }
    }
}

/* ------------------------------------------------------------------ stage 3: queries */

static int sample(const hw_sheet *s, const float *p, float x, float z, float *out)
{
    float fx = x / s->dx - 0.5f, fz = z / s->dx - 0.5f;
    int i = (int)floorf(fx), j = (int)floorf(fz);
    float tx = fx - i, tz = fz - j;
    if (i < -1 || j < -1 || i >= s->w || j >= s->h) return 0;
    *out = (1 - tx) * (1 - tz) * p[AT(s, i, j)] + tx * (1 - tz) * p[AT(s, i + 1, j)]
         + (1 - tx) * tz * p[AT(s, i, j + 1)] + tx * tz * p[AT(s, i + 1, j + 1)];
    return 1;
}

HW_API int hw_probe(const hw_sheet *s, float x, float z, float *eta, float *u, float *v,
                    float *deta_dx, float *deta_dz)
{
    /* eta from a surface plane built on the fly: for dry cells use the bed so the surface
       stays continuous at the shore */
    float e00, hh, uu, vv, ex0, ex1, ez0, ez1;
    int i, j;
    float fx = x / s->dx - 0.5f, fz = z / s->dx - 0.5f;
    i = (int)floorf(fx); j = (int)floorf(fz);
    if (i < -1 || j < -1 || i >= s->w || j >= s->h) return 0;
    {
        float tx = fx - i, tz = fz - j, w[4], e[4];
        int ks[4] = { AT(s, i, j), AT(s, i + 1, j), AT(s, i, j + 1), AT(s, i + 1, j + 1) }, q;
        w[0] = (1 - tx) * (1 - tz); w[1] = tx * (1 - tz); w[2] = (1 - tx) * tz; w[3] = tx * tz;
        e00 = 0;
        for (q = 0; q < 4; q++) { e[q] = s->Beff[ks[q]] + s->hA[ks[q]]; e00 += w[q] * e[q]; }
        ex0 = (1 - tz) * e[0] + tz * e[2]; ex1 = (1 - tz) * e[1] + tz * e[3];
        ez0 = (1 - tx) * e[0] + tx * e[1]; ez1 = (1 - tx) * e[2] + tx * e[3];
    }
    sample(s, s->hA, x, z, &hh);
    sample(s, s->u, x, z, &uu);
    sample(s, s->v, x, z, &vv);
    if (eta) *eta = e00;
    if (u) *u = hh > EPS_H ? uu : 0.0f;
    if (v) *v = hh > EPS_H ? vv : 0.0f;
    if (deta_dx) *deta_dx = (ex1 - ex0) / s->dx;
    if (deta_dz) *deta_dz = (ez1 - ez0) / s->dx;
    return 1;
}

HW_API float hw_body_force(const hw_sheet *s, const float *probes, int n, float V, float A_eff,
                           float rho, float dt_ramp, float c_d, float k_damp,
                           const float *body_vel, float *force)
{
    int q, sub_n = 0;
    float ratio;
    force[0] = force[1] = force[2] = 0.0f;
    for (q = 0; q < n; q++) {
        const float *p = probes + 6 * q;
        float eta, u, v, dex, dez, sub, ramp, vw[3], vr[3], sp;
        if (!hw_probe(s, p[0], p[2], &eta, &u, &v, &dex, &dez)) continue;
        sub = eta - p[1];
        if (sub <= 0) continue;
        sub_n++;
        ramp = dt_ramp > 0 ? sub / dt_ramp : 1.0f;
        if (ramp > 1) ramp = 1;
        force[1] += rho * s->g * (V / n) * ramp;
        vw[0] = u; vw[1] = u * dex + v * dez; vw[2] = v;   /* the water moves with its surface */
        vr[0] = p[3] - vw[0]; vr[1] = p[4] - vw[1]; vr[2] = p[5] - vw[2];
        sp = sqrtf(vr[0] * vr[0] + vr[1] * vr[1] + vr[2] * vr[2]);
        force[0] += -0.5f * rho * c_d * (A_eff / n) * sp * vr[0];
        force[1] += -0.5f * rho * c_d * (A_eff / n) * sp * vr[1];
        force[2] += -0.5f * rho * c_d * (A_eff / n) * sp * vr[2];
    }
    ratio = n ? (float)sub_n / n : 0.0f;
    force[0] += -k_damp * body_vel[0] * ratio;
    force[1] += -k_damp * body_vel[1] * ratio;
    force[2] += -k_damp * body_vel[2] * ratio;
    return ratio;
}

/* ------------------------------------------------------------------ the solver */

/* derive u, v, c from a state; returns max |u| + c + |v| */
static float prepare(hw_sheet *s, float *h, float *hu, float *hv, float dt_for_cap)
{
    int k;
    float smax = 0.0f;
    float vcap = (s->o.clamps && dt_for_cap > 0) ? 0.5f * s->dx / dt_for_cap : 0.0f;
    for (k = 0; k < s->n; k++) {
        float hh = h[k], cap;
        if (hh <= EPS_H || s->wall[k] > 0) {
            if (hh < 0) h[k] = 0.0f;
            hu[k] = hv[k] = 0.0f; s->u[k] = s->v[k] = 0.0f; s->c[k] = 0.0f;
            continue;
        }
        if (!s->o.clamps) {
            cap = MOM_CAP * hh;
            if (hu[k] > cap) hu[k] = cap; else if (hu[k] < -cap) hu[k] = -cap;
            if (hv[k] > cap) hv[k] = cap; else if (hv[k] < -cap) hv[k] = -cap;
        }
        s->u[k] = hu[k] / hh; s->v[k] = hv[k] / hh;
        if (vcap > 0) {
            if (s->u[k] > vcap) s->u[k] = vcap; else if (s->u[k] < -vcap) s->u[k] = -vcap;
            if (s->v[k] > vcap) s->v[k] = vcap; else if (s->v[k] < -vcap) s->v[k] = -vcap;
            if (s->o.edge_damp > 0 && s->edge[k] > 0) { s->u[k] *= s->o.edge_damp; s->v[k] *= s->o.edge_damp; }
            hu[k] = hh * s->u[k]; hv[k] = hh * s->v[k];
        }
        s->c[k] = sqrtf(s->g * hh);
        {
            float sp = fabsf(s->u[k]) + s->c[k] + fabsf(s->v[k]);
            if (sp > smax) smax = sp;
        }
    }
    return smax;
}

/* stage 8: cells within 2 of a wet/dry edge */
static void mark_edges(hw_sheet *s)
{
    int i, j;
    memset(s->edge, 0, (size_t)s->n * sizeof(float));
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j);
            if (s->hA[k] <= EPS_H && s->wall[k] == 0) {
                int a, c;
                for (a = -2; a <= 2; a++)
                    for (c = -2; c <= 2; c++) {
                        int ii = i + a, jj = j + c;
                        if (ii < 0 || jj < 0 || ii >= s->w || jj >= s->h) continue;
                        s->edge[AT(s, ii, jj)] = 1.0f;
                    }
            }
        }
}

/* fluxes from state (h, hu, hv, u, v, c) accumulated into (ho, huo, hvo) with coefficient a = dt/dx */
static float minmod(float a, float b)
{
    if (a > 0 && b > 0) return a < b ? a : b;
    if (a < 0 && b < 0) return a > b ? a : b;
    return 0.0f;
}

static void fluxes(hw_sheet *s, const float *h, const float *hu, const float *hv,
                   float *ho, float *huo, float *hvo, float a)
{
    const float g2 = 0.5f * s->g;
    int i, j, dir;
    (void)hu; (void)hv;
    for (dir = 0; dir < 2; dir++)
        for (j = -1; j < s->h + 1; j++)
            for (i = -1; i < s->w + 1; i++) {
                int L = AT(s, i, j), R = dir == 0 ? AT(s, i + 1, j) : AT(s, i, j + 1);
                int wallface;
                float hL = h[L], hR = h[R], bL = s->Beff[L], bR = s->Beff[R];
                float uL, uR, vL, vR, cL = s->c[L], cR = s->c[R];
                float hLs, hRs, us, cs, SL, SR, k, qL, qR, Fh, Fn, Ft, sL, sR, tmp;
                if (hL <= EPS_H && hR <= EPS_H) continue;
                if (s->o.face_walls) {
                    wallface = dir == 0 ? s->wallx[L] : s->wally[L];
                    /* dry-ledge rule: no flow up onto a dry step */
                    if (!wallface) {
                        if (hL <= 1e-4f * s->dx && bL > bR + hR) wallface = 1;
                        if (hR <= 1e-4f * s->dx && bR > bL + hL) wallface = 1;
                    }
                } else
                    wallface = (s->wall[L] > 0 || s->wall[R] > 0);
                if (dir == 0) { uL = s->u[L]; uR = s->u[R]; vL = s->v[L]; vR = s->v[R]; }
                else          { uL = s->v[L]; uR = s->v[R]; vL = s->u[L]; vR = s->u[R]; }
                if (wallface) {
                    /* reflecting: no mass or transverse flux, the cell feels its own pressure */
                    if (dir == 0) { huo[R] += a * g2 * hR * hR; huo[L] -= a * g2 * hL * hL; }
                    else          { hvo[R] += a * g2 * hR * hR; hvo[L] -= a * g2 * hL * hL; }
                    continue;
                }
                if (s->o.recon) {
                    /* stage 5: minmod-limited linear reconstruction of the surface eta = h + B
                       and of u, v on each side of the face (second order where the stencil is
                       wet and wall-free, first order elsewhere; exact for still water) */
                    int LL = dir == 0 ? AT(s, i - 1, j) : AT(s, i, j - 1);
                    int RR = dir == 0 ? AT(s, i + 2, j) : AT(s, i, j + 2);
                    int inL = dir == 0 ? i - 1 >= -2 : j - 1 >= -2;
                    int inR = dir == 0 ? i + 2 <= s->w + 1 : j + 2 <= s->h + 1;
                    float eL = hL + bL, eR = hR + bR, de = eR - eL;
                    if (hL > EPS_H && hR > EPS_H) {
                        if (inL && h[LL] > EPS_H && s->wall[LL] == 0) {
                            float uLL = dir == 0 ? s->u[LL] : s->v[LL], vLL = dir == 0 ? s->v[LL] : s->u[LL];
                            float sl = minmod(eL - (h[LL] + s->Beff[LL]), de), hn;
                            hn = eL + 0.5f * sl - bL; if (hn < 0) hn = 0; if (hn > 2.0f * hL) hn = 2.0f * hL;
                            uL += 0.5f * minmod(uL - uLL, uR - uL);
                            vL += 0.5f * minmod(vL - vLL, vR - vL);
                            hL = hn;
                        }
                        if (inR && h[RR] > EPS_H && s->wall[RR] == 0) {
                            float uRR = dir == 0 ? s->u[RR] : s->v[RR], vRR = dir == 0 ? s->v[RR] : s->u[RR];
                            float sl = minmod(de, (h[RR] + s->Beff[RR]) - eR), hn;
                            hn = eR - 0.5f * sl - bR; if (hn < 0) hn = 0; if (hn > 2.0f * hR) hn = 2.0f * hR;
                            uR -= 0.5f * minmod(uR - uL, uRR - uR);
                            vR -= 0.5f * minmod(vR - vL, vRR - vR);
                            hR = hn;
                        }
                        cL = sqrtf(s->g * hL); cR = sqrtf(s->g * hR);
                    }
                }
                tmp = bL - bR; hLs = hL + (tmp < 0 ? tmp : 0); if (hLs < 0) hLs = 0;
                tmp = bR - bL; hRs = hR + (tmp < 0 ? tmp : 0); if (hRs < 0) hRs = 0;
                us = 0.5f * (uL + uR) + (cL - cR);
                cs = 0.5f * (cL + cR) + 0.25f * (uL - uR);
                SL = uL - cL; if (us - fabsf(cs) < SL) SL = us - fabsf(cs); if (SL > 0) SL = 0;
                SR = uR + cR; if (us + fabsf(cs) > SR) SR = us + fabsf(cs); if (SR < 0) SR = 0;
                tmp = SR - SL; k = 1.0f / (tmp > 1e-10f ? tmp : 1e-10f);
                qL = hLs * uL; qR = hRs * uR;
                Fh = k * (qL * SR - qR * SL + (hRs - hLs) * SL * SR);
                Fn = k * ((uL * qL + g2 * hLs * hLs) * SR - (uR * qR + g2 * hRs * hRs) * SL + (qR - qL) * SL * SR);
                Ft = k * (vL * qL * SR - vR * qR * SL + (hRs * vR - hLs * vL) * SL * SR);
                sL = g2 * (hL * hL - hLs * hLs);
                sR = g2 * (hR * hR - hRs * hRs);
                ho[R] += a * Fh; ho[L] -= a * Fh;
                if (dir == 0) {
                    huo[R] += a * (Fn + sR); huo[L] -= a * (Fn + sL);
                    hvo[R] += a * Ft;        hvo[L] -= a * Ft;
                } else {
                    hvo[R] += a * (Fn + sR); hvo[L] -= a * (Fn + sL);
                    huo[R] += a * Ft;        huo[L] -= a * Ft;
                }
            }
}

/* --- stage 7: foam, entrained air and spray ---
 * Whitewater comes from where the flow loses energy: breaking crests (steep, rising, curved
 * down), bores and hydraulic jumps (fast flow running into slower water), water slamming into
 * walls, and bodies entering or leaving it. Those cells feed two planes: air, the bubbles mixed
 * into the column, which rise out at bubble_rise and turn into foam as they reach the top, and
 * foam, the white on the surface, which drifts with the flow, bunches up where the flow
 * converges (this draws the foam lines), spreads a little and thins out, thick foam first and
 * a lace that lingers. The strongest sources also throw spray drops that fly on gravity and
 * leave foam where they land. */
#define WET_FOAM 0.5f        /* below this depth a cell holds no foam */

static float smooth01(float a, float b, float x)
{
    float t = (x - a) / (b - a);
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    return t * t * (3 - 2 * t);
}

static float frand(hw_sheet *s)
{
    unsigned x = s->rng;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    s->rng = x;
    return (float)(x >> 8) * (1.0f / 16777216.0f);
}

/* open water: not wall, wet, and not under a body (its surface there is the body's underside) */
static int foam_cell(const hw_sheet *s, int k) { return s->wall[k] <= 0 && s->hA[k] >= WET_FOAM && s->bprev[k] <= 0; }

/* is the face between cell k (at i, j) and neighbour q (0 -x, 1 +x, 2 -z, 3 +z) open */
static int face_open(const hw_sheet *s, int i, int j, int q)
{
    switch (q) {
    case 0: return !s->wallx[AT(s, i - 1, j)];
    case 1: return !s->wallx[AT(s, i, j)];
    case 2: return !s->wally[AT(s, i, j - 1)];
    default: return !s->wally[AT(s, i, j)];
    }
}

/* bilinear sample of a plane that only reads wet, open cells */
static float sample_wet(const hw_sheet *s, const float *p, float x, float z)
{
    float fx = x / s->dx - 0.5f, fz = z / s->dx - 0.5f, sum = 0, wsum = 0;
    int i = (int)floorf(fx), j = (int)floorf(fz), q;
    float tx = fx - i, tz = fz - j;
    for (q = 0; q < 4; q++) {
        int ii = i + (q & 1), jj = j + (q >> 1), k;
        float w = ((q & 1) ? tx : 1 - tx) * ((q >> 1) ? tz : 1 - tz);
        if (ii < 0 || jj < 0 || ii >= s->w || jj >= s->h) continue;
        k = AT(s, ii, jj);
        if (!foam_cell(s, k)) continue;
        sum += w * p[k]; wsum += w;
    }
    return wsum > 1e-4f ? sum / wsum : 0.0f;
}

static void spray_spawn(hw_sheet *s, int i, int j, float strength, float dt, float nx, float nz)
{
    int k = AT(s, i, j);
    float c = sqrtf(s->g * s->hA[k]), expect = strength * s->fp.spray_rate * dt;
    float rise = (s->hA[k] - s->hprev[k]) / dt;
    int cap = s->fp.spray_max < HW_SPRAY_CAP ? s->fp.spray_max : HW_SPRAY_CAP;
    if (rise < 0) rise = 0;
    while (expect > 0 && s->nspray < cap) {
        float *p, up;
        if (expect < 1 && frand(s) > expect) break;
        expect -= 1;
        p = s->spray + 8 * s->nspray++;
        up = (0.3f + 0.7f * frand(s)) * (0.4f * c + rise);
        p[0] = (i + frand(s)) * s->dx;
        p[2] = (j + frand(s)) * s->dx;
        p[1] = s->Beff[k] + s->hA[k];
        p[3] = 0.86f * s->u[k] + 0.15f * c * (2 * frand(s) - 1);
        p[5] = 0.86f * s->v[k] + 0.15f * c * (2 * frand(s) - 1);
        if (nx != 0 || nz != 0) {   /* thrown back off the wall and up its face */
            float un = p[3] * nx + p[5] * nz;
            if (un > 0) { p[3] -= 1.6f * un * nx; p[5] -= 1.6f * un * nz; up += un; }
        }
        p[4] = up;
        p[6] = 0;
        p[7] = 0.5f + frand(s);
    }
}

static void spray_step(hw_sheet *s, float dt)
{
    int n = 0, m;
    float drag = expf(-s->fp.spray_drag * dt);
    for (m = 0; m < s->nspray; m++) {
        float *p = s->spray + m * 8;
        int i, j, k, dead = 0;
        p[4] -= s->g * dt;
        p[3] *= drag; p[4] *= drag; p[5] *= drag;
        p[0] += p[3] * dt; p[1] += p[4] * dt; p[2] += p[5] * dt;
        p[6] += dt;
        i = (int)floorf(p[0] / s->dx); j = (int)floorf(p[2] / s->dx);
        if (i < 0 || j < 0 || i >= s->w || j >= s->h || p[6] > 3.0f) dead = 1;
        else {
            k = AT(s, i, j);
            if (s->wall[k] > 0) dead = 1;
            else if (p[4] < 0 && p[1] <= s->Beff[k] + s->hA[k]) {   /* landed */
                dead = 1;
                if (s->hA[k] >= WET_FOAM) {
                    s->foam[k] += s->fp.spray_foam * p[7];
                    s->air[k] += 0.5f * s->fp.spray_foam * p[7];
                    if (s->foam[k] > 1) s->foam[k] = 1;
                    if (s->air[k] > 1) s->air[k] = 1;
                }
            }
        }
        if (!dead) { if (n != m) memcpy(s->spray + n * 8, p, 8 * sizeof(float)); n++; }
    }
    s->nspray = n;
}

static void foam_pass(hw_sheet *s, float dt)
{
    const hw_foam_params *fp = &s->fp;
    int i, j;
    float dx = s->dx, spread = fp->spread * dt;
    float *div = s->atmp;
    size_t bytes = (size_t)s->n * sizeof(float);
    if (spread > 1) spread = 1;
    spray_step(s, dt);
    /* sources, bubbles surfacing, decay */
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j), kn[4], q;
            float h = s->hA[k], eta, en[4], un[4], vn[4], c, gx, gz, slope, lap, rise, sp, fr;
            float brk, bore, rapid, slam = 0, impact, src, out, snx = 0, snz = 0, sprayk;
            div[k] = 0;
            if (!foam_cell(s, k)) { s->foam[k] = 0; s->air[k] = 0; continue; }
            kn[0] = AT(s, i - 1, j); kn[1] = AT(s, i + 1, j); kn[2] = AT(s, i, j - 1); kn[3] = AT(s, i, j + 1);
            eta = s->Beff[k] + h;
            c = sqrtf(s->g * h);
            for (q = 0; q < 4; q++) {
                int open = face_open(s, i, j, q) && s->wall[kn[q]] <= 0;
                int ok = open && s->hA[kn[q]] >= WET_FOAM;
                en[q] = ok ? s->Beff[kn[q]] + s->hA[kn[q]] : eta;
                un[q] = ok ? s->u[kn[q]] : s->u[k];
                vn[q] = ok ? s->v[kn[q]] : s->v[k];
                if (!open) {   /* water driven into this wall */
                    float nx = q == 0 ? -1.0f : q == 1 ? 1.0f : 0.0f;
                    float nz = q == 2 ? -1.0f : q == 3 ? 1.0f : 0.0f;
                    float sl = smooth01(0.1f, 0.6f, (s->u[k] * nx + s->v[k] * nz) / c);
                    if (sl > slam) { slam = sl; snx = nx; snz = nz; }
                }
            }
            gx = (en[1] - en[0]) / (2 * dx); gz = (en[3] - en[2]) / (2 * dx);
            slope = sqrtf(gx * gx + gz * gz);
            lap = (en[0] + en[1] + en[2] + en[3] - 4 * eta) / dx;   /* slope change across the cell */
            rise = (h - s->hprev[k]) / dt;
            div[k] = (un[1] - un[0] + vn[3] - vn[2]) / (2 * dx);
            sp = sqrtf(s->u[k] * s->u[k] + s->v[k] * s->v[k]);
            fr = sp / c;
            brk = smooth01(0.15f, 0.5f, slope) * smooth01(0.02f, 0.2f, rise / c) * smooth01(0.02f, 0.2f, -lap);
            bore = smooth01(0.6f, 1.2f, fr) * smooth01(0.05f, 0.5f, -div[k] * dx / (sp + c));
            rapid = smooth01(1.5f, 3.0f, fr);
            {   /* a body entering or leaving churns the water around its rim */
                float im = s->impact[k];
                for (q = 0; q < 4; q++) if (s->impact[kn[q]] > im) im = s->impact[kn[q]];
                impact = smooth01(0.05f, 0.5f, im / (dt * c));
            }
            src = brk + bore + 0.1f * rapid + slam + impact;
            if (src > 2) src = 2;
            s->air[k] += src * fp->air_gain * dt;
            s->foam[k] += src * fp->foam_gain * dt;
            /* bubbles reach the top and become foam */
            out = fp->bubble_rise * dt / (h > 1 ? h : 1);
            if (out > 1) out = 1;
            out *= s->air[k];
            s->air[k] -= out;
            s->foam[k] += out * fp->air_to_foam;
            /* thick foam collapses fast, the lace lingers */
            s->foam[k] *= expf(-dt * (fp->lace + s->foam[k]) / fp->foam_life);
            if (s->air[k] > 1) s->air[k] = 1;
            if (s->foam[k] > 1) s->foam[k] = 1;
            sprayk = brk + 1.5f * slam + 2 * impact + 0.5f * bore;
            if (sprayk > 0.05f)
                spray_spawn(s, i, j, sprayk, dt, slam > 0.3f ? snx : 0, slam > 0.3f ? snz : 0);
        }
    /* drift along (u, v) (semi-Lagrangian); surface foam also bunches up where the flow converges */
    memcpy(s->ftmp, s->foam, bytes);
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j);
            float sq;
            if (!foam_cell(s, k)) continue;
            sq = 1 - dt * div[k];
            if (sq < 0.5f) sq = 0.5f;
            if (sq > 1.5f) sq = 1.5f;
            sq *= sample_wet(s, s->ftmp, (i + 0.5f) * dx - s->u[k] * dt, (j + 0.5f) * dx - s->v[k] * dt);
            s->foam[k] = sq > 1 ? 1 : sq;
        }
    memcpy(s->ftmp, s->air, bytes);
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j);
            if (!foam_cell(s, k)) continue;
            s->air[k] = sample_wet(s, s->ftmp, (i + 0.5f) * dx - s->u[k] * dt, (j + 0.5f) * dx - s->v[k] * dt);
        }
    /* spread: f <- d f + (1 - d)/4 sum(open wet neighbours) */
    memcpy(s->ftmp, s->foam, bytes);
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) {
            int k = AT(s, i, j), kn[4], q;
            float sum = 0;
            if (!foam_cell(s, k)) continue;
            kn[0] = AT(s, i - 1, j); kn[1] = AT(s, i + 1, j); kn[2] = AT(s, i, j - 1); kn[3] = AT(s, i, j + 1);
            for (q = 0; q < 4; q++)
                sum += (face_open(s, i, j, q) && foam_cell(s, kn[q])) ? s->ftmp[kn[q]] : s->ftmp[k];
            s->foam[k] = (1 - spread) * s->ftmp[k] + spread * 0.25f * sum;
        }
}

HW_API float *hw_foam(hw_sheet *s) { return s->foam; }
HW_API float *hw_air(hw_sheet *s) { return s->air; }
HW_API const float *hw_spray(const hw_sheet *s, int *count) { if (count) *count = s->nspray; return s->spray; }
HW_API void hw_set_foam_params(hw_sheet *s, const hw_foam_params *p) { s->fp = *p; }
HW_API void hw_get_foam_params(const hw_sheet *s, hw_foam_params *p) { *p = s->fp; }

HW_API void hw_foam_add(hw_sheet *s, float x, float z, float r, float foam, float air)
{
    int i, j, i0 = (int)floorf((x - r) / s->dx), i1 = (int)floorf((x + r) / s->dx);
    int j0 = (int)floorf((z - r) / s->dx), j1 = (int)floorf((z + r) / s->dx);
    for (j = j0; j <= j1; j++)
        for (i = i0; i <= i1; i++) {
            int k;
            float ox = (i + 0.5f) * s->dx - x, oz = (j + 0.5f) * s->dx - z, w;
            if (i < 0 || j < 0 || i >= s->w || j >= s->h) continue;
            k = AT(s, i, j);
            if (!foam_cell(s, k)) continue;
            w = 1 - (ox * ox + oz * oz) / (r * r);
            if (w <= 0) continue;
            s->foam[k] += foam * w; if (s->foam[k] > 1) s->foam[k] = 1;
            s->air[k] += air * w; if (s->air[k] > 1) s->air[k] = 1;
        }
}

HW_API int hw_step(hw_sheet *s, float dt)
{
    int steps = 0;
    float remaining = dt;
    size_t bytes = (size_t)s->n * sizeof(float);
    if (s->o.foam) {
        int k;
        memcpy(s->hprev, s->hA, bytes);
        for (k = 0; k < s->n; k++) s->impact[k] = s->o.displacement ? fabsf(s->b[k] - s->bprev[k]) : 0.0f;
    }
    if (s->o.displacement) apply_displacement(s);
    else memcpy(s->Beff, s->B, bytes);
    if (s->o.clamps) mark_edges(s);
    while (remaining > 1e-7f && steps < 10000) {
        float smax = prepare(s, s->hA, s->huA, s->hvA, s->last_dt);
        float sub = smax > 1e-6f ? s->cfl * s->dx / smax : remaining;
        float a;
        if (sub > remaining) sub = remaining;
        s->smax = smax; s->last_dt = sub;
        a = sub / s->dx;
        /* half step: B = A + 0.5 dt F(A) */
        memcpy(s->hB, s->hA, bytes); memcpy(s->huB, s->huA, bytes); memcpy(s->hvB, s->hvA, bytes);
        fluxes(s, s->hA, s->huA, s->hvA, s->hB, s->huB, s->hvB, 0.5f * a);
        prepare(s, s->hB, s->huB, s->hvB, sub);
        /* full step: C = A + dt F(B) */
        memcpy(s->hC, s->hA, bytes); memcpy(s->huC, s->huA, bytes); memcpy(s->hvC, s->hvA, bytes);
        fluxes(s, s->hB, s->huB, s->hvB, s->hC, s->huC, s->hvC, a);
        { float *t;
          t = s->hA; s->hA = s->hC; s->hC = t;
          t = s->huA; s->huA = s->huC; s->huC = t;
          t = s->hvA; s->hvA = s->hvC; s->hvC = t; }
        remaining -= sub;
        steps++;
    }
    prepare(s, s->hA, s->huA, s->hvA, s->last_dt);   /* u, v, c valid for queries */
    if (s->o.foam && dt > 0) foam_pass(s, dt);
    return steps;
}

HW_API double hw_volume(const hw_sheet *s)
{
    double v = 0;
    int i, j;
    for (j = 0; j < s->h; j++)
        for (i = 0; i < s->w; i++) v += s->hA[AT(s, i, j)];
    return v * s->dx * s->dx;
}
