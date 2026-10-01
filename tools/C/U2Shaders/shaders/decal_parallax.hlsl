// Bullet holes (and other wall decals) that look sunken into the surface: parallax occlusion,
// as F.E.A.R.'s impact marks read as damage. No light direction needed: the depth shows by
// looking at the decal at an angle, and the inside of the hole darkens with depth.
//
// Use with decal=<hash> decal_parallax.hlsl: the draw keeps its own blending, so this returns
// what the texture itself would have (decals then still layer over each other).
//
// The decal's own texture doubles as its depth map (the fork has no second texture):
//   ALPHA_DECAL 1  alpha decals (the hole drawn over the wall): more opaque = deeper
//   ALPHA_DECAL 0  modulating decals (the wall multiplied by the texture, white = no change):
//                  darker = deeper
// For the other kind, copy this file, flip the setting and point that texture's rule at it.
//
// The surface's direction and the texture's axes come from screen-space derivatives of the
// position and texture coordinates, so the walls' vertices need no normals (level geometry
// often has none). Needs ddx/ddy: ps_2_a.

sampler2D Tex  : register(s0);   // the decal
float4    Info : register(c0);   // time, 1 = positions valid (fixed function), 1/width, 1/height
float4    Mode : register(c1);   // x: 1 = projected texture coordinates (projector decals)

#define ALPHA_DECAL 1
#define DEPTH 3.0                 // how deep the deepest part looks, in world units
#define STEPS 8                   // search steps into the surface
#define CAVITY 0.5                // how much darker the bottom of the hole is (0-1)

float DepthOf(float4 t)
{
	return ALPHA_DECAL ? t.a : 1 - dot(t.rgb, float3(0.30, 0.59, 0.11));
}

float4 main(float3 t0 : TEXCOORD0, float3 pos : TEXCOORD2) : COLOR
{
	float2 uv = Mode.x > 0.5 ? t0.xy / t0.z : t0.xy;

	// the surface's normal, and how the texture coordinates change per world unit along it
	float3 dpx = ddx(pos), dpy = ddy(pos);
	float2 dux = ddx(uv), duy = ddy(uv);
	float3 v = normalize(-pos);
	float3 n = normalize(cross(dpx, dpy));
	n = dot(n, v) < 0 ? -n : n;
	float3 px = cross(dpy, n), py = cross(n, dpx);
	float det = dot(px, dpx);
	float3 gu = (px * dux.x + py * duy.x) / det;     // gradient of u
	float3 gv = (px * dux.y + py * duy.y) / det;     // gradient of v

	// following the view ray down into the surface: the texture coordinates per unit of depth
	float2 perDepth = -float2(dot(v, gu), dot(v, gv)) / max(dot(v, n), 0.25);
	if (Info.y < 0.5)
		perDepth = 0;                               // no positions (vertex shader draw): flat

	// first step where the ray is below the surface the depth map describes, then the crossing
	// interpolated between that step and the one before (without it, steep views show steps)
	float gapPrev = DepthOf(tex2D(Tex, uv));        // depth map minus ray depth: > 0 = still above
	float found = step(gapPrev, 0);                 // flat outside the hole: the surface itself
	float2 hit = found > 0 ? uv : uv + perDepth * DEPTH;
	float hitDepth = found > 0 ? 0 : 1;
	float2 atPrev = uv;
	for (int i = 1; i <= STEPS; i++)
	{
		float layer = (float)i / STEPS;
		float2 at = uv + perDepth * (layer * DEPTH);
		float gap = DepthOf(tex2D(Tex, at)) - layer;
		float now = step(gap, 0) * (1 - found);
		float w = gapPrev / max(gapPrev - gap, 0.0001);
		hit = lerp(hit, lerp(atPrev, at, w), now);
		hitDepth = lerp(hitDepth, layer - (1 - w) / STEPS, now);
		found = max(found, now);
		gapPrev = gap;
		atPrev = at;
	}

	float4 decal = tex2D(Tex, hit);
	float shade = 1 - CAVITY * hitDepth;
	return ALPHA_DECAL ? float4(decal.rgb * shade, decal.a) : float4(decal.rgb * shade, 1);
}
