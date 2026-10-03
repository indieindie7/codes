// SMAA 1x for the U2Shaders post chain: the three passes of the reference SMAA.hlsl (Jimenez et al.,
// MIT, github.com/iryoku/smaa), which the fork puts in front of this file together with
//   #define SMAA_HLSL_3 1, #define SMAA_PRESET_HIGH 1, #define SMAA_PASS 1|2|3
//   float4 SmaaMetrics : register(c0);  #define SMAA_RT_METRICS SmaaMetrics   (1/w, 1/h, w, h)
// It runs on the game's frame copy before the final post pass, so grading, LUT and sharpening
// work on the anti-aliased image. Vertices: a clip-space quad (x y z, u v), shifted half a pixel
// here (Direct3D 9 pixel centres). Each pass binds its textures from s0, so the three passes
// fit in the samplers the post chain already saves and restores.

float4 SmaaPos(float4 p)
{
	return float4(p.x - SmaaMetrics.x, p.y + SmaaMetrics.y, p.z, 1);
}

#if SMAA_PASS == 1
// 1: edges, from luma (the game's frame is gamma-space 8-bit, as luma detection wants)
sampler2D colorTex : register(s0);

void EdgeVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0,
	out float4 o0 : TEXCOORD1, out float4 o1 : TEXCOORD2, out float4 o2 : TEXCOORD3)
{
	float4 o[3];
	SMAAEdgeDetectionVS(uv, o);
	op = SmaaPos(p); ouv = uv; o0 = o[0]; o1 = o[1]; o2 = o[2];
}

float4 EdgePS(float2 uv : TEXCOORD0, float4 o0 : TEXCOORD1, float4 o1 : TEXCOORD2, float4 o2 : TEXCOORD3) : COLOR
{
	float4 o[3] = { o0, o1, o2 };
	return float4(SMAALumaEdgeDetectionPS(uv, o, colorTex), 0, 0);
}

#elif SMAA_PASS == 2
// 2: blending weights, from the edges and the precomputed area and search textures
sampler2D edgesTex  : register(s0);
sampler2D areaTex   : register(s1);
sampler2D searchTex : register(s2);

void WeightVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0,
	out float2 pix : TEXCOORD1, out float4 o0 : TEXCOORD2, out float4 o1 : TEXCOORD3, out float4 o2 : TEXCOORD4)
{
	float4 o[3];
	SMAABlendingWeightCalculationVS(uv, pix, o);
	op = SmaaPos(p); ouv = uv; o0 = o[0]; o1 = o[1]; o2 = o[2];
}

float4 WeightPS(float2 uv : TEXCOORD0, float2 pix : TEXCOORD1, float4 o0 : TEXCOORD2, float4 o1 : TEXCOORD3,
	float4 o2 : TEXCOORD4) : COLOR
{
	float4 o[3] = { o0, o1, o2 };
	return SMAABlendingWeightCalculationPS(uv, pix, o, edgesTex, areaTex, searchTex, float4(0, 0, 0, 0));
}

#else
// 3: the frame blended along the edges
sampler2D colorTex : register(s0);
sampler2D blendTex : register(s1);

void BlendVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0,
	out float4 o : TEXCOORD1)
{
	SMAANeighborhoodBlendingVS(uv, o);
	op = SmaaPos(p); ouv = uv;
}

float4 BlendPS(float2 uv : TEXCOORD0, float4 o : TEXCOORD1) : COLOR
{
	return SMAANeighborhoodBlendingPS(uv, o, colorTex, blendTex);
}
#endif
