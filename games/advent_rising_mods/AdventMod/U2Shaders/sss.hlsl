// sss.hlsl - screen-space subsurface scattering for skin (sss=1): the lit frame blurred under
// the skin, once across and once down (a separable blur, the method of Jimenez et al.,
// "Separable Subsurface Scattering", CGF 2015; this kernel and code are our own). Compiled by
// the wrapper as vs_3_0 / ps_3_0.
//
// Which pixels are skin: the skin shader (char_skin.hlsl) writes a mask into a second render
// target while it draws (COLOR1); only masked pixels are blurred and only masked pixels feed
// the blur, so the skin doesn't bleed into the wall behind it or the armour beside it.
// The width is a distance on the skin (world units, sssfx's first value), so a face far away
// gets a narrower blur on screen than one close up. Each tap's weight drops with its depth
// difference ("follow the surface"), so the blur stops at the silhouette and at deep folds.
// The profile per colour: red light travels furthest in skin, blue least, so each colour has
// its own spread: a sharp centre plus a wide tail, the tail widest in red.
// sssfx=width strength falloff debug: width in world units (about 1.2 for a face at Advent's
// scale), strength 0-1 (how much of the blurred light replaces the sharp), falloff (how fast a
// depth step cuts the blur), debug 1 = the mask, 2 = the blur alone.

float4 Px   : register(c0);     // the frame's 1/w, 1/h, w, h
float4 Proj : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Dir  : register(c2);     // the pass's direction (1, 0) or (0, 1)
float4 Fx   : register(c3);     // width, strength, falloff, debug
sampler Scene : register(s0);   // the lit frame (or the first pass's result)
sampler Depth : register(s1);   // the scene's depth
sampler Mask  : register(s2);   // the skin mask (rgb)

void SssVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float ViewZ(float2 uv)
{
	float d = tex2Dlod(Depth, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 0 : Proj.w / (d - Proj.z);
}

#define TAPS 8                     // each side: 17 taps in all

// the per-colour profile at distance r (in units of the width): a narrow and a wide Gaussian;
// the wide one carries more weight and spreads further in red
float3 Profile(float r)
{
	float r2 = r * r;
	float3 nearW = float3(0.20, 0.45, 0.62), farW = float3(0.80, 0.55, 0.38);   // weights (sum 1 per colour)
	float3 nearV = float3(0.020, 0.012, 0.008), farV = float3(0.33, 0.12, 0.06); // variances
	return nearW * exp(-r2 / (2 * nearV)) / sqrt(nearV) + farW * exp(-r2 / (2 * farV)) / sqrt(farV);
}

float4 SssPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 c = tex2Dlod(Scene, float4(uv, 0, 0));
	float m = tex2Dlod(Mask, float4(uv, 0, 0)).g;
	if (Fx.w > 0.5 && Fx.w < 1.5)
		return float4(m, m, m, 1);
	if (m < 0.02)
		return c;
	float z = ViewZ(uv);
	if (z <= 0)
		return c;
	// the width on screen: world units -> pixels at this depth (the projection's x scale)
	float px = Fx.x * Proj.x * 0.5 * Px.z / z;
	px = min(px, 40);                                   // a face pressed to the lens: cap it
	float2 stepUv = Dir.xy * Px.xy * px / TAPS;
	float3 sum = c.rgb * Profile(0), wsum = Profile(0);
	for (int i = 1; i <= TAPS; i++)
	{
		float r = (float)i / TAPS;                       // 0..1 of the width
		float3 w = Profile(r * 1.6);
		for (int s = -1; s <= 1; s += 2)
		{
			float2 tuv = uv + stepUv * i * s;
			float3 tc = tex2Dlod(Scene, float4(tuv, 0, 0)).rgb;
			float tm = tex2Dlod(Mask, float4(tuv, 0, 0)).g;
			float tz = ViewZ(tuv);
			// follow the surface: a tap off the skin, or at another depth, counts less
			float follow = tm * saturate(1 - Fx.z * abs(tz - z) / max(Fx.x, 0.01));
			sum += tc * w * follow;
			wsum += w * follow;
		}
	}
	float3 blurred = sum / max(wsum, 0.0001);
	if (Fx.w > 1.5)
		return float4(blurred, c.a);
	return float4(lerp(c.rgb, blurred, saturate(Fx.y) * saturate(m)), c.a);
}
