// Shadow projector pass with contact hardening (percentage-closer soft shadows).
// Sharp where the body meets the ground, softer the farther the shadowing part is from it.
//
// Method after NVIDIA's PCSS (Fernando 2005) as implemented in UnityPCSS
// (https://github.com/TheMasonX/UnityPCSS, MIT License, Copyright (c) 2017 Lucas Norr):
// blocker search, penumbra from the receiver/blocker gap, filtering of the shadow map.
// Taps follow a golden-angle spiral instead of a Poisson table, to stay within the
// 32 constant registers of shader model 2.
//
// Unreal II specifics: the engine draws the silhouette into a sharp map (shadow in alpha:
// 1 lit, lower shadowed; pcss_map.hlsl adds the silhouette's world height in red), blurs it
// into a second map as 0.502 * alpha, and projects that. Here the sharp map comes in on
// sampler 3 and the blur is done per pixel, its radius set by how far above this ground the
// shadowing part is. Stages 1 and 2 of the original draw fade the result to neutral by
// their gradient textures' alpha; that is repeated here.

sampler2D Blurred : register(s0);   // the engine's blurred map (unused but for debugging)
sampler2D Fade1   : register(s1);
sampler2D Fade2   : register(s2);
sampler2D Sharp   : register(s3);
float4 Info  : register(c0);    // x: time, y: debug view (1: gap as colour, 2: raw values)
float4 TF    : register(c1);    // neutral colour (the draw's texture factor): no darkening
float4 P     : register(c2);    // search radius, min radius, radius per unit of gap, max radius (UV)
float4 Texel : register(c3);    // 1/width, 1/height of the shadow map
float4 Zrow  : register(c4);    // camera space -> world height
float4 Tint  : register(c5);    // how strongly each channel darkens (shadowtint=, 1 1 1 = grey)

#define SEARCH_TAPS 12
#define LIT 0.9                 // sharp-map alpha above this: no blocker

// tap i of n on the spiral (constant after unrolling), turned by the per-pixel rotation cs
float2 Tap(float i, float n, float2 cs)
{
	float r = sqrt((i + 0.5) / n);
	float a = i * 2.3999632;                            // golden angle
	float2 d = float2(cos(a), sin(a)) * r;
	return float2(d.x * cs.x - d.y * cs.y, d.x * cs.y + d.y * cs.x);
}

float4 main(float3 t0 : TEXCOORD0, float3 t1 : TEXCOORD1, float3 t2 : TEXCOORD2, float3 t3 : TEXCOORD3) : COLOR
{
	float2 uv = t0.xy / t0.z;
	float receiver = dot(float4(t3, 1), Zrow) / 256.0;  // this ground pixel's world height (code)
	float spin = frac(sin(dot(uv, float2(12.9898, 78.233))) * 43758.5453) * 6.2831853;
	float2 cs; sincos(spin, cs.y, cs.x);

	// 1) blocker search: silhouette pixels near this spot, and how far above this ground they are
	float gapSum = 0, blockers = 0;
	for (int i = 0; i < SEARCH_TAPS; i++)
	{
		float4 s = tex2D(Sharp, uv + Tap(i, SEARCH_TAPS, cs) * P.x);
		float hit = s.a < LIT;
		// signed, wrapped difference in -32..224 units: a part slightly below the ground
		// (measurement noise, slopes) counts as touching it
		float d = frac(s.r - receiver + 0.125) * 256.0 - 32.0;
		gapSum += hit * max(d, 0);
		blockers += hit;
	}
	float gap = gapSum / max(blockers, 1);

	// 2) penumbra: grows with the gap between the shadowing part and the ground
	float radius = clamp(P.y + gap * P.z, P.y, P.w);

	// 3) filter the silhouette at that radius, the engine's way: shade = 0.502 * alpha
	// (the search pattern twice: as is, and turned 90 degrees at 0.6 of the radius, so
	// both loops share their constants: shader model 2 has only 32 registers)
	float lit = 0;
	float2 cs2 = float2(-cs.y, cs.x);
	for (int j = 0; j < SEARCH_TAPS; j++)
	{
		lit += tex2D(Sharp, uv + Tap(j, SEARCH_TAPS, cs) * radius).a;
		lit += tex2D(Sharp, uv + Tap(j, SEARCH_TAPS, cs2) * (radius * 0.6)).a;
	}
	lit /= 2 * SEARCH_TAPS;
	// the shadow darkens each channel by its tint weight: 1 1 1 is the engine's grey, a lower
	// blue weight leaves more blue in the shadow (cool fill light). Tint.w is 1 only from a
	// d3d8.dll that sets c5; an older one leaves it 0, and the shadow stays grey
	float3 weight = Tint.w > 0.5 ? Tint.rgb : 1;
	float3 col = blockers > 0 ? 0.502 * saturate(1 - (1 - lit) * weight) : TF.rgb;

	// debug views (pcssdebug=N): 1 gap as colour (red touching .. blue 128 units up)
	if (Info.y > 0.5 && Info.y < 1.5 && blockers > 0)
		col = lerp(float3(1, 0, 0), float3(0, 0, 1), saturate(gap / 128.0)) * 0.5;
	// 2 raw values written as is: R = receiver code, G = height code at the centre, B = gap/256
	if (Info.y > 1.5 && Info.y < 2.5)
		return float4(frac(receiver), tex2D(Sharp, uv).r, gap / 256.0, 1);

	// the original draw's fades (stages 1 and 2: blend to neutral by the gradient alpha)
	col = lerp(TF.rgb, col, tex2D(Fade1, t1.xy).a);
	col = lerp(TF.rgb, col, tex2D(Fade2, t2.xy).a);
	return float4(col, 1);
}
