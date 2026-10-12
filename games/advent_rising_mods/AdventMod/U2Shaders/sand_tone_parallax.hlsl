// Rock meshes whose texture is already graded at load (texgrade=, e.g. 58fc527c on the crash
// level): rock_tone_parallax.hlsl with the grading off, so only the depth and self-shadow act.
// Otherwise as below.
//
// Rock meshes with depth and self-shadow: rock_tone.hlsl's sandstone grading (see there) on top
// of world_parallax.hlsl's parallax march and self-shadow toward surfacelight= (c8; see there).
// One surface= rule per texture, so the two live in one shader. Use with
// surface=<hash> rock_parallax.hlsl on the rock textures. Needs ddx/ddy: ps_2_a.
//
// A rock's dark parts are mostly cracks and crevices, so brightness as height suits it.

sampler2D Tex    : register(s0);   // the surface's texture
sampler2D Second : register(s1);   // stage 1's texture (usually the lightmap)
float4    Info    : register(c0);  // time, 1, 1/width, 1/height
float4    TFactor : register(c1);  // stage 1's constant colour when c2.z = 1
float4    Combine : register(c2);  // x: vertex colour factor, y: stage 1 factor (0 = not used)
float4    Levels  : register(c3);  // the texture's surface brightness, deepest brightness, 0, 1 = measured
float4    Light   : register(c8);  // xyz: towards the light, camera space; w: shadow strength (0 = off)

#define DEPTH 0.05                 // how deep the deepest part looks, as a fraction of the
                                   // texture's size on the wall (one repeat): 0.04 of a 512-unit
                                   // tile is 20 units; the same on any texture scale
#define STEPS 8                    // search steps into the surface
#define AUTO_LEVELS 1              // 1: the measured levels (c3), 0: the two below
#define FLAT_ABOVE 0.45            // brightness at or above this is the surface itself
#define DEEP_BELOW 0.12            // brightness at or below this is the deepest
#define HEIGHT_BLUR 1.0            // read the height from a smaller mip: smooths texture noise
#define CAVITY 0.3                 // how much darker the deepest parts are (0-1)
#define LIFT       1.0              // rock_tone grading: brightness of the texture
#define DESAT      0.0              // 0 = the game's colour, 1 = grey
#define TINT       float3(1, 1, 1)   // warm sandstone, not orange
#define CONTRAST   0.25             // local contrast against a blurred read
#define FADE_START 1500.0          // distance (world units) where the effect starts to fade
#define FADE_END 4000.0            // and where it is gone (far away it only shimmers)
#define SHADOW_STEPS 6             // steps from the hit towards the light (0 = no self-shadow)
#define SHADOW_SOFT 4.0            // how fast the shadow gets dark with depth under the height map

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

	// self-shadow: walk from the hit up towards the light; wherever the height map is above
	// the light ray, something raised blocks it. A surface facing away from the light gets
	// none (the lightmap already has it dark).
	float shade = 1;
	float strength = abs(Light.w);  // negative w = debug tint, same strength
#if SHADOW_STEPS > 0
	float3 l = Light.xyz;
	float ln = dot(l, n);
	if (strength > 0 && ln > 0.05 && hitDepth > 0.01)
	{
		float2 lightPer = float2(dot(l, gu), dot(l, gv)) / max(ln, 0.25) * (DEPTH * tile * fade);
		float blocked = 0;
		for (int j = 1; j <= SHADOW_STEPS; j++)
		{
			float k = (float)j / SHADOW_STEPS;
			float rayDepth = hitDepth * (1 - k);
			float under = rayDepth - DepthOf(hit + lightPer * hitDepth * k, levels);
			blocked = max(blocked, under * (1 - k * 0.5));
		}
		shade = 1 - strength * fade * saturate(blocked * SHADOW_SOFT);
	}
#endif

	// what the texture stages did, at the shifted place (each stage clamps, as they do)
	float4 t = tex2D(Tex, hit);
	float3 lum3 = float3(0.30, 0.59, 0.11);
	float l0 = dot(t.rgb, lum3);
	float blur = dot(tex2Dbias(Tex, float4(hit, 0, 3)).rgb, lum3);
	float3 c = lerp(t.rgb, l0.xxx, DESAT) * TINT * LIFT;
	c *= 1 + CONTRAST * (l0 - blur) / max(blur, 0.05);          // stone grain
	c *= (1 - CAVITY * hitDepth * fade) * shade;                // cracks: the depth now darkens them
	float a = t.a;
	if (Combine.x > 0)
	{
		c = saturate(c * diffuse.rgb * Combine.x);
		a *= diffuse.a;
	}
	if (Combine.y > 0)
		c = saturate(c * (Combine.z > 0 ? TFactor.rgb : tex2D(Second, t1).rgb) * Combine.y);
	// debug (surfacelight w < 0): the surface turns magenta so it can be found on screen, the
	// self-shadow shows green, and a surface facing away from the light shows blue
	if (Light.w < 0)
	{
		float lum = dot(c, float3(0.3, 0.59, 0.11)) + 0.15;
		c = (ln > 0.05 ? float3(1, 0.2, 1) : float3(0.2, 0.4, 1)) * lum;
		c = lerp(c, float3(0, 1, 0), saturate((1 - shade) * 3));
	}
	return float4(c, a);
}
