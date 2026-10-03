// Post pass 1: the frame shrunk to a quarter (4 bilinear taps cover each 4x4 block) and only
// what is brighter than the bloom threshold kept, with a soft knee so it fades in.

sampler2D Scene : register(s0);   // the finished 3D frame
float4    Texel : register(c0);   // 1/width, 1/height of the frame
float4    Bloom : register(c1);   // threshold, intensity

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float2 o = Texel.xy;
	float3 c = (tex2D(Scene, uv + float2(-o.x, -o.y)).rgb + tex2D(Scene, uv + float2(o.x, -o.y)).rgb
	          + tex2D(Scene, uv + float2(-o.x, o.y)).rgb + tex2D(Scene, uv + o).rgb) * 0.25;
	float peak = max(c.r, max(c.g, c.b));
	float keep = saturate((peak - Bloom.x) / max(1 - Bloom.x, 0.001));
	return float4(c * keep, 1);
}
