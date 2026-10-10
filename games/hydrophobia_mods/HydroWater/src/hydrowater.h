/* HydroWater - a shallow-water sheet solver in the shape of Hydrophobia's.
 *
 * The baseline (hw_opts all zero) is the scheme read out of HydroPC.exe (see
 * games/hydrophobia-water-tech.md): explicit finite volume on a grid of dx-unit cells with a
 * two-cell border, per cell depth h, momentum hu/hv, bed B; hydrostatic reconstruction
 * (Audusse 2004), Toro two-rarefaction wave speeds, HLL flux, g/2 (h^2 - h*^2) source,
 * reflecting walls, momentum capped at 1000 h, dt = min(remaining, cfl dx / max(|u|+c+|v|)),
 * midpoint (two-stage) time step.
 *
 * The options switch on the upgrade plan's stages (games/hydrophobia-water-upgrade.md):
 *   displacement  (1) bodies displace volume through the b plane
 *   capped_stamp  (2) velocity stamps blend with a stability cap and sweep fast bodies
 *   (3) smooth buoyancy is hw_body_force(), a query, so it has no switch
 *   face_walls    (4a) walls on faces, plus the automatic dry-ledge rule
 *   clamps        (8) velocity cap 0.5 dx/dt, edge damping, no 1000 h cap
 *   foam          (7) foam, entrained air and spray drops read from the field (render-only)
 *
 * Plain C99, no dependencies. Built as a DLL for the Python harness (tests/harness.py) and
 * meant to become the drop-in for the game's step function later (same per-cell state).
 */
#ifndef HYDROWATER_H
#define HYDROWATER_H

#ifdef _WIN32
#define HW_API __declspec(dllexport)
#else
#define HW_API
#endif

typedef struct hw_opts {
    int displacement;   /* stage 1 */
    int capped_stamp;   /* stage 2 */
    int face_walls;     /* stage 4a: wallX/wallY face masks and the dry-ledge rule */
    int clamps;         /* stage 8 */
    float alpha;        /* stage 1 wave amplitude scale, 0.5..1 (default 1) */
    float c_adapt;      /* stage 2 adaptation rate (default 0.2) */
    float edge_damp;    /* stage 8 velocity scale within 2 cells of a wet/dry edge (default 0.7) */
    int recon;          /* stage 5: minmod-limited linear reconstruction of eta, u, v at faces */
    int foam;           /* stage 7: foam, air and spray planes (never feed back into the flow) */
} hw_opts;

/* stage 7 tuning; hw_create sets the defaults shown */
typedef struct hw_foam_params {
    float foam_gain;    /* foam added per second at full source strength (0.8) */
    float air_gain;     /* entrained air added per second at full source strength (3) */
    float foam_life;    /* seconds for thick foam to thin out (2.5) */
    float lace;         /* decay floor: thin foam lasts foam_life / lace (0.25) */
    float bubble_rise;  /* bubble rise speed, units/s; deep water holds its air longer (25) */
    float air_to_foam;  /* share of surfacing air that turns into foam (0.35) */
    float spread;       /* foam diffusion rate per second (3) */
    float spray_rate;   /* spray drops per cell per second at full strength (30) */
    float spray_foam;   /* foam left where a drop lands (0.15) */
    float spray_drag;   /* air drag on drops, per second (0.5) */
    int spray_max;      /* drop limit, at most HW_SPRAY_CAP (4096) */
} hw_foam_params;

#define HW_SPRAY_CAP 8192

typedef struct hw_sheet hw_sheet;

/* w x h interior cells of size dx, gravity g (units/s^2), CFL number (the game uses 0.5) */
HW_API hw_sheet *hw_create(int w, int h, float dx, float g, float cfl);
HW_API void hw_destroy(hw_sheet *s);
HW_API void hw_set_opts(hw_sheet *s, const hw_opts *o);
HW_API int hw_width(const hw_sheet *s);
HW_API int hw_height(const hw_sheet *s);
HW_API int hw_stride(const hw_sheet *s);   /* row stride of every plane (w + 4) */

/* planes, (h + 4) rows of stride floats; cell (i, j) of the interior is at (j + 2) * stride + i + 2 */
HW_API float *hw_depth(hw_sheet *s);       /* current h */
HW_API float *hw_hu(hw_sheet *s);
HW_API float *hw_hv(hw_sheet *s);
HW_API float *hw_u(hw_sheet *s);           /* derived velocity (valid after a step) */
HW_API float *hw_v(hw_sheet *s);
HW_API float *hw_bed(hw_sheet *s);         /* B */
HW_API float *hw_wall(hw_sheet *s);        /* per-cell wall flag (1 = wall), the game's model */
HW_API unsigned char *hw_wallx(hw_sheet *s); /* face (i,j)-(i+1,j) is a wall */
HW_API unsigned char *hw_wally(hw_sheet *s); /* face (i,j)-(i,j+1) is a wall */
HW_API float *hw_body(hw_sheet *s);        /* b: water column replaced by bodies this frame */

/* fill the interior to surface level eta (h = max(0, eta - B)) */
HW_API void hw_fill(hw_sheet *s, float eta);
/* mark a rectangle of cells [i0,i1) x [j0,j1) as wall cells (both models) */
HW_API void hw_wall_rect(hw_sheet *s, int i0, int j0, int i1, int j1);
/* rasterise a line segment (world units) into the face masks, Bresenham on cell edges */
HW_API void hw_wall_segment(hw_sheet *s, float x0, float z0, float x1, float z1);

/* --- stage 1: bodies ---
 * call hw_bodies_begin once per frame, then hw_body_box / hw_body_capsule for every body in
 * the sheet, then hw_step; the step applies the displacement difference against the previous
 * frame and keeps this frame's b as b_prev */
HW_API void hw_bodies_begin(hw_sheet *s);
/* both return the water volume the body displaces (units^3): rho g times that is its buoyancy,
 * exact for the rasterised shape and continuous in the body's height, Thuerey's per-column force */
HW_API float hw_body_box(hw_sheet *s, float x0, float z0, float x1, float z1, float ybottom, float ytop);
HW_API float hw_body_disc(hw_sheet *s, float x, float z, float r, float ybottom, float ytop);

/* --- stage 2: velocity stamp ---
 * a body of radius r moved from (px,pz) to (x,z) this frame, its bottom at ybottom, with
 * horizontal velocity (vx, vz). Baseline: overwrite u,v within r weighted 1 - d^2/r^2 (the game). */
HW_API void hw_stamp(hw_sheet *s, float px, float pz, float x, float z, float r, float ybottom,
                     float vx, float vz, float dt);

/* --- stage 3: queries for buoyancy ---
 * surface height and water velocity at a world point (bilinear over cell centres);
 * returns 0 if the point is outside the sheet */
HW_API int hw_probe(const hw_sheet *s, float x, float z, float *eta, float *u, float *v,
                    float *deta_dx, float *deta_dz);
/* force on a body sampled at n probe points (x, y, z, vx, vy, vz per point), each carrying
 * volume V / n and area A_eff / n. rho water density, dt_ramp the buoyancy ramp distance,
 * c_d drag coefficient, k_damp extra damping while submerged (per second, times body velocity
 * times submerged ratio). Writes force (3) and returns the submerged probe ratio. */
HW_API float hw_body_force(const hw_sheet *s, const float *probes, int n, float V, float A_eff,
                           float rho, float dt_ramp, float c_d, float k_damp,
                           const float *body_vel, float *force);

/* --- stage 7: foam, air and spray (hw_opts.foam) ---
 * updated once per hw_step from the frame's flow; all three are for the renderer only.
 * foam: surface coverage 0..1 (white). air: bubbles in the column 0..1 (pale, milky water).
 * spray: count drops of 8 floats (x, y, z, vx, vy, vz, age s, size 0.5..1.5); y is height. */
HW_API float *hw_foam(hw_sheet *s);
HW_API float *hw_air(hw_sheet *s);
HW_API const float *hw_spray(const hw_sheet *s, int *count);
HW_API void hw_set_foam_params(hw_sheet *s, const hw_foam_params *p);
HW_API void hw_get_foam_params(const hw_sheet *s, hw_foam_params *p);
/* splash event (bullet, explosion, a body falling in): add foam and air within radius r */
HW_API void hw_foam_add(hw_sheet *s, float x, float z, float r, float foam, float air);

/* advance by dt seconds (sub-stepped by CFL); returns the number of sub-steps */
HW_API int hw_step(hw_sheet *s, float dt);
/* total water volume (sum of h dx^2) over the interior */
HW_API double hw_volume(const hw_sheet *s);
/* largest |u| + c + |v| seen in the last sub-step */
HW_API float hw_smax(const hw_sheet *s);

#endif
