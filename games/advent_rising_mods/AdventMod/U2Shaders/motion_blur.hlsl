// Camera motion blur (the fork's motionblur=; idea after UE4's PostProcessMotionBlur, own code).
// Each pixel's world position is rebuilt from the depth, carried through last frame's camera to
// where it was on screen then, and the frame is averaged along that line. Only the camera's own
// motion is known (no per-object velocity), so things that move with the camera, like the player
// in third person, are kept sharp by fading the blur out near the camera (nearfade).
// Samples whose depth is much nearer than the centre pixel's are left out, so a near edge
// doesn't smear over what is behind it.

float4 Px    : register(c0);     // 1/w, 1/h, w, h
float4 Proj  : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Fx    : register(c2);     // strength, near fade (world units), longest blur (pixels), debug
float4x4 Back : register(c3);    // c3..c6: camera space now -> last frame's clip space (row vectors)
sampler Scene : register(s0);
sampler Depth : register(s1);

#define SAMPLES 10

void BlurVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float ViewZ(float2 uv)
{
	float d = tex2Dlod(Depth, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 1e6 : Proj.w / (d - Proj.z);
}

float4 BlurPS(float2 uv : TEXCOORD0) : COLOR
{
	float z = ViewZ(uv);
	float2 ndc = float2(uv.x * 2 - 1, 1 - uv.y * 2);
	float4 cam = float4(ndc.x * z / Proj.x, ndc.y * z / Proj.y, z, 1);
	float4 was = mul(cam, Back);
	float2 wasUv = float2(was.x / was.w * 0.5 + 0.5, 0.5 - was.y / was.w * 0.5);
	float2 v = (uv - wasUv) * Fx.x;                          // screen units this frame moved
	v *= saturate((z - Fx.y) / max(Fx.y, 1));               // nothing near the camera
	float len = length(v * Px.zw);
	if (Fx.w > 0.5)                                         // debug: blur length as red/green, still = blue
		return float4(saturate(abs(v * Px.zw) / Fx.z), was.w <= 0 ? 1 : 0.3, 1);
	if (was.w <= 0 || len < 0.5)
		return tex2Dlod(Scene, float4(uv, 0, 0));
	v *= min(1, Fx.z / len);                                 // held to the longest blur
	float3 sum = 0;
	float wsum = 0;
	for (int i = 0; i < SAMPLES; i++)
	{
		float t = (i + 0.5) / SAMPLES - 0.5;                    // centred on the pixel
		float2 s = uv + v * t;
		float w = ViewZ(s) < z * 0.7 ? 0.0 : 1.0;               // nearer things stay out
		sum += tex2Dlod(Scene, float4(s, 0, 0)).rgb * w;
		wsum += w;
	}
	return float4(wsum > 0 ? sum / wsum : tex2Dlod(Scene, float4(uv, 0, 0)).rgb, 1);
}
