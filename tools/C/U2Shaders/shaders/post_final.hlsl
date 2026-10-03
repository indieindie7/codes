// Final post pass (Unreal II; shared with AdventMod's, same constants). The frame arrives
// finished and before the HUD, already tonemapped by the game and 8-bit, so nothing here
// re-tonemaps the image as a whole:
//   1. bloom added in linear light, and only the result's highlights rolled off
//      (the shoulder of Khronos PBR Neutral, Apache-2.0), so the game's own look below the
//      shoulder is kept and bright lamps glow instead of clipping flat;
//   2. grade: exposure, colour balance, saturation, contrast (U2Shaders.ini grade=/colour=);
//   3. contrast-adaptive sharpening (AMD FidelityFX CAS, MIT; ported to ps_2): strong on soft
//      detail, gentle on edges that are already crisp, so no halos (sharpen= is its strength);
//   4. lens: a little chromatic aberration toward the screen's edges, and the vignette;
//   5. colour grading through a 3D LUT (lut= in U2Shaders.ini; see make_luts.py);
//   6. film grain (animated, stronger in the darks) and a triangular dither, last, so dark
//      gradients don't band.
// postfx=aberration grain dither shoulder (c4): 0 = that one off (shoulder 0 = 0.76).
// postsplit=1 leaves the right half untouched to compare.

sampler2D Scene    : register(s0);   // the finished 3D frame
sampler2D BloomMap : register(s1);   // the blurred bright parts (quarter size)
float4    Texel    : register(c0);   // 1/width, 1/height, 1 = compare split
float4    Bloom    : register(c1);   // threshold, intensity
float4    Grade    : register(c2);   // saturation, contrast, exposure, vignette
float4    Balance  : register(c3);   // colour balance r g b, sharpen (CAS strength 0..1)
float4    Fx       : register(c4);   // postfx=: aberration (screen widths), grain, dither (8-bit steps), shoulder
float4    LutInfo  : register(c5);   // N, 1/width, 1/height, 1 = a LUT is loaded
sampler2D Lut      : register(s2);   // N slices of NxN side by side: x = red, y = green, slice = blue

#define DESAT      0.15     // how much rolled-off highlights lose colour

float3 ToLinear(float3 c) { return c * c; }               // gamma 2 approximation: cheap, and
float3 ToGamma(float3 c)  { return sqrt(max(c, 0)); }     // exactly inverted below

// Khronos PBR Neutral's shoulder only (the toe would change the game's shadows)
float3 Shoulder(float3 c, float start)
{
	float peak = max(c.r, max(c.g, c.b));
	if (peak < start)
		return c;
	float d = 1 - start;
	float newPeak = 1 - d * d / (peak + d - start);
	c *= newPeak / peak;
	float g = 1 - 1 / (DESAT * (peak - newPeak) + 1);
	return lerp(c, newPeak.xxx, g);
}

// AMD FidelityFX CAS (MIT, Copyright (c) 2020 Advanced Micro Devices), 3x3, ps_2 form
float3 Cas(float2 uv, float sharpness)
{
	float2 o = Texel.xy;
	float3 a = tex2D(Scene, uv + float2(-o.x, -o.y)).rgb;
	float3 b = tex2D(Scene, uv + float2(0, -o.y)).rgb;
	float3 c = tex2D(Scene, uv + float2(o.x, -o.y)).rgb;
	float3 d = tex2D(Scene, uv + float2(-o.x, 0)).rgb;
	float3 e = tex2D(Scene, uv).rgb;
	float3 f = tex2D(Scene, uv + float2(o.x, 0)).rgb;
	float3 g = tex2D(Scene, uv + float2(-o.x, o.y)).rgb;
	float3 h = tex2D(Scene, uv + float2(0, o.y)).rgb;
	float3 i = tex2D(Scene, uv + o).rgb;
	float3 mn = min(min(min(d, e), min(f, b)), h);
	float3 mn2 = min(mn, min(min(a, c), min(g, i)));
	mn += mn2;
	float3 mx = max(max(max(d, e), max(f, b)), h);
	float3 mx2 = max(mx, max(max(a, c), max(g, i)));
	mx += mx2;
	float3 amp = sqrt(saturate(min(mn, 2 - mx) / max(mx, 0.0001)));
	float3 w = amp * (-1 / lerp(8.0, 5.0, sharpness));
	return saturate((b * w + d * w + f * w + h * w + e) / (1 + 4 * w));
}

// the colour through the LUT, blending the two blue slices around it
float3 Graded(float3 c)
{
	float n = LutInfo.x;
	float b = saturate(c.b) * (n - 1);
	float slice = floor(b);
	float2 uv = float2((slice * n + saturate(c.r) * (n - 1) + 0.5) * LutInfo.y, (saturate(c.g) * (n - 1) + 0.5) * LutInfo.z);
	float3 lo = tex2D(Lut, uv).rgb;
	float3 hi = tex2D(Lut, uv + float2(n * LutInfo.y, 0)).rgb;
	return lerp(lo, hi, b - slice);
}

// a value in -1..1 per pixel, triangular (two hashes), for the dither
float Tri(float2 p)
{
	float n1 = frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453);
	float n2 = frac(sin(dot(p, float2(39.3468, 11.135))) * 24634.6345);
	return n1 + n2 - 1;
}

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float3 original = tex2D(Scene, uv).rgb;
	float2 d = uv - 0.5;
	float edge = dot(d, d) * 2;                     // 0 at the centre, 1 in the corners

	// 3 first, on the game's own pixels: CAS (with chromatic aberration taken from the
	// neighbouring red/blue samples toward the edges)
	float3 c = Balance.w > 0 ? Cas(uv, saturate(Balance.w)) : original;
	float2 ca = d * Fx.x * edge * 4;
	c.r = lerp(c.r, tex2D(Scene, uv + ca).r, saturate(edge * 2));
	c.b = lerp(c.b, tex2D(Scene, uv - ca).b, saturate(edge * 2));

	// 1: bloom in linear light, then the highlights rolled off
	float3 lin = ToLinear(c) * Grade.z * Balance.rgb + ToLinear(tex2D(BloomMap, uv).rgb) * Bloom.y;
	c = ToGamma(Shoulder(lin, Fx.w > 0 ? Fx.w : 0.76));

	// 2: saturation and contrast (in gamma, where the game's look was made)
	float luma = dot(c, float3(0.299, 0.587, 0.114));
	c = lerp(luma.xxx, c, Grade.x);
	c = (c - 0.5) * Grade.y + 0.5;

	// 5: the LUT
	if (LutInfo.w > 0.5)
		c = Graded(c);

	// 4: vignette
	c *= 1 - Grade.w * edge;

	// 6: grain (moves every frame, mostly in the darks), then the dither
	float2 px = uv / Texel.xy;
	luma = dot(c, float3(0.299, 0.587, 0.114));
	c += Tri(px + frac(Texel.w * 7.13) * float2(1013, 719)) * Fx.y * (1 - 0.6 * luma);
	c += Tri(px) * (Fx.z / 255.0);

	c = (Texel.z > 0.5 && uv.x > 0.5) ? original : c;
	return float4(saturate(c), 1);
}
