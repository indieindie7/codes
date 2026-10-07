// The crash level's alpha-blended sky layers (clouds over the backdrop) graded like
// sky_tone.hlsl. Use with decal=<hash> sky_layer.hlsl: the draw keeps its own blending, so
// this returns what the layer would have (texture x vertex colour), only graded.

sampler2D Tex  : register(s0);
float4    Info : register(c0);
float4    Mode : register(c1);   // x: 1 = projected coordinates (not for the sky)

#define LIFT     1.3
#define DESAT    0.55
#define TINT     float3(1.04, 1.00, 0.95)
#define KEEPBLUE 0.6

float4 main(float3 t0 : TEXCOORD0, float4 diffuse : COLOR0) : COLOR
{
	float2 uv = Mode.x > 0.5 ? t0.xy / t0.z : t0.xy;
	float4 t = tex2D(Tex, uv);
	float l = dot(t.rgb, float3(0.30, 0.59, 0.11));
	float blue = saturate((t.b - max(t.r, t.g)) * 4);
	float3 c = lerp(t.rgb, l.xxx, DESAT * (1 - KEEPBLUE * blue)) * lerp(TINT, 1, blue) * LIFT;
	c.g = lerp(c.g, min(c.g, (c.r + c.b) * 0.5 + 0.06), 0.7 * (1 - blue));
	return float4(saturate(c * diffuse.rgb), t.a * diffuse.a);
}
