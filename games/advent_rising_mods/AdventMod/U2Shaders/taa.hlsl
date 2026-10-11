// Temporal anti-aliasing (the fork's taa=; own code after the usual recipe: Karis, "High Quality
// Temporal Supersampling", SIGGRAPH 2014). The fork moves the projection by a different
// sub-pixel offset each frame (Halton 2,3, 8 places); this pass blends the frame into a history
// that follows the camera: each pixel's position is rebuilt from the depth, carried through last
// frame's camera to where it was then, and the history there is clamped to the colours around
// the pixel now, so what moved on its own (no per-object motion is known) can't leave a trail.

float4 Px    : register(c0);     // 1/w, 1/h, w, h
float4 Proj  : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Fx    : register(c2);     // new frame's share, jitter (pixels), sharpen, debug
float4x4 Back : register(c3);    // c3..c6: camera space now -> last frame's clip space (row vectors)
float4 Reset : register(c7);     // x = 1: no history this frame (first frame, camera cut)
sampler Scene : register(s0);
sampler Depth : register(s1);
sampler Hist  : register(s2);

void TaaVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float ViewZ(float2 uv)
{
	float d = tex2Dlod(Depth, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 1e6 : Proj.w / (d - Proj.z);
}

float3 Rgb(float2 uv)
{
	return tex2Dlod(Scene, float4(uv, 0, 0)).rgb;
}

float4 TaaPS(float2 uv : TEXCOORD0) : COLOR
{
	float3 c = Rgb(uv);
	// the colours around the pixel now: the box the history is held to
	float3 n0 = Rgb(uv + float2(Px.x, 0)), n1 = Rgb(uv - float2(Px.x, 0));
	float3 n2 = Rgb(uv + float2(0, Px.y)), n3 = Rgb(uv - float2(0, Px.y));
	float3 lo = min(c, min(min(n0, n1), min(n2, n3)));
	float3 hi = max(c, max(max(n0, n1), max(n2, n3)));
	float3 avg = (c + n0 + n1 + n2 + n3) * 0.2;
	float3 cur = c + (c - avg) * Fx.z;                       // a little sharpening against the blend's softness
	cur = clamp(cur, lo, hi);

	// the nearest depth of the cross, so edges of near things carry their own motion
	float z = min(ViewZ(uv), min(min(ViewZ(uv + float2(Px.x, 0)), ViewZ(uv - float2(Px.x, 0))),
		min(ViewZ(uv + float2(0, Px.y)), ViewZ(uv - float2(0, Px.y)))));
	float2 ndc = float2(uv.x * 2 - 1, 1 - uv.y * 2);
	float4 cam = float4(ndc.x * z / Proj.x, ndc.y * z / Proj.y, z, 1);
	float4 was = mul(cam, Back);
	float2 wasUv = float2(was.x / was.w * 0.5 + 0.5, 0.5 - was.y / was.w * 0.5);
	bool off = Reset.x > 0.5 || was.w <= 0 || any(wasUv < 0) || any(wasUv > 1);
	float3 h = tex2Dlod(Hist, float4(wasUv, 0, 0)).rgb;
	float3 hc = clamp(h, lo, hi);
	// debug: red where the history was thrown away (only there, as the output is the next history)
	if (off)
		return float4(Fx.w > 0.5 ? lerp(cur, float3(1, 0, 0), 0.6) : cur, 1);
	// more of the new frame where the camera moved far (the history there is blurred by resampling)
	float moved = length((uv - wasUv) * Px.zw);
	float share = lerp(Fx.x, 0.5, saturate(moved / 24));
	return float4(lerp(hc, cur, share), 1);
}
