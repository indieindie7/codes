// Walls and floors with depth: parallax occlusion on a solid world surface, so mortar lines,
// panel seams and grates look recessed when seen at an angle. Same method as
// decal_parallax.hlsl, without its light direction or a separate height map.
//
// Use with surface=<hash> world_parallax.hlsl. The shader replaces the texture stages, so it
// redoes what they did (the fork passes which setup it found in c2): the texture, times the
// vertex colour, times the lightmap. The lightmap is not shifted, only the texture.
//
// The texture's own brightness stands in for height: dark = recessed. That suits textures
// whose dark parts are gaps (bricks, tiles, panels, grates) and looks wrong on ones whose
// dark parts are just colour (painted signs, dirt): leave those without a rule. The fork
// measures each texture once (c3): its typical brightness counts as the surface itself, its
// darkest few percent as the bottom, so most of a texture stays flat and only its gaps sink
// (a fully bumpy surface swims). FLAT_ABOVE / DEEP_BELOW are used when it could not measure
// (an unusual texture format), or always with AUTO_LEVELS 0.
//
// For a different texture, copy this file, adjust the settings and point that texture's
// rule at the copy. Needs ddx/ddy: ps_2_a.

sampler2D Tex    : register(s0);   // the surface's texture
sampler2D Second : register(s1);   // stage 1's texture (usually the lightmap)
float4    Info    : register(c0);  // time, 1, 1/width, 1/height
float4    Combine : register(c2);  // x: vertex colour factor, y: stage 1 factor (0 = not used)
float4    Levels  : register(c3);  // the texture's surface brightness, deepest brightness, 0, 1 = measured

#define DEPTH 0.04                 // how deep the deepest part looks, as a fraction of the
                                   // texture's size on the wall (one repeat): 0.04 of a 512-unit
                                   // tile is 20 units; the same on any texture scale
#define STEPS 8                    // search steps into the surface
#define AUTO_LEVELS 1              // 1: the measured levels (c3), 0: the two below
#define FLAT_ABOVE 0.45            // brightness at or above this is the surface itself
#define DEEP_BELOW 0.12            // brightness at or below this is the deepest
#define HEIGHT_BLUR 1.0            // read the height from a smaller mip: smooths texture noise
#define CAVITY 0.3                 // how much darker the deepest parts are (0-1)
#define FADE_START 1500.0          // distance (world units) where the effect starts to fade
#define FADE_END 4000.0            // and where it is gone (far away it only shimmers)

float DepthOf(float2 uv, float2 levels)
{
	float l = dot(tex2Dbias(Tex, float4(uv, 0, HEIGHT_BLUR)).rgb, float3(0.30, 0.59, 0.11));
	return saturate((levels.x - l) / (levels.x - levels.y));
}

float4 main(float2 uv : TEXCOORD0, float2 t1 : TEXCOORD1, float3 pos : TEXCOORD2,
            float4 diffuse : COLOR0) : COLOR
{
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

	float2 levels = AUTO_LEVELS && Levels.w > 0.5 ? Levels.xy : float2(FLAT_ABOVE, DEEP_BELOW);
	float fade = saturate((FADE_END - length(pos)) / (FADE_END - FADE_START));
	float tile = 2 / max(length(gu) + length(gv), 0.000001);   // world units per texture repeat
	float2 perDepth = -float2(dot(v, gu), dot(v, gv)) / max(dot(v, n), 0.25) * (DEPTH * tile * fade);

	// first step where the view ray is below the height map, the crossing interpolated
	// between that step and the one before
	float gapPrev = DepthOf(uv, levels);
	float found = step(gapPrev, 0);
	float2 hit = found > 0 ? uv : uv + perDepth;
	float hitDepth = found > 0 ? 0 : 1;
	float2 atPrev = uv;
	for (int i = 1; i <= STEPS; i++)
	{
		float layer = (float)i / STEPS;
		float2 at = uv + perDepth * layer;
		float gap = DepthOf(at, levels) - layer;
		float now = step(gap, 0) * (1 - found);
		float w = gapPrev / max(gapPrev - gap, 0.0001);
		hit = lerp(hit, lerp(atPrev, at, w), now);
		hitDepth = lerp(hitDepth, layer - (1 - w) / STEPS, now);
		found = max(found, now);
		gapPrev = gap;
		atPrev = at;
	}

	// what the texture stages did, at the shifted place (each stage clamps, as they do)
	float4 t = tex2D(Tex, hit);
	float3 c = t.rgb * (1 - CAVITY * hitDepth * fade);
	float a = t.a;
	if (Combine.x > 0)
	{
		c = saturate(c * diffuse.rgb * Combine.x);
		a *= diffuse.a;
	}
	if (Combine.y > 0)
		c = saturate(c * tex2D(Second, t1).rgb * Combine.y);
	return float4(c, a);
}
