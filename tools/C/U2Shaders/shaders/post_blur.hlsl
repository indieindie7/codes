// Post pass 2: one direction of a separable 9-tap Gaussian blur, in 5 taps (bilinear filtering
// reads two texels per tap). Run across, then down, twice, on the quarter-size bright map.

sampler2D Src  : register(s0);
float4    Step : register(c0);   // one texel along the blur direction: (1/width, 0) or (0, 1/height)

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float3 c = tex2D(Src, uv).rgb * 0.2270270;
	c += (tex2D(Src, uv + Step.xy * 1.3846154).rgb + tex2D(Src, uv - Step.xy * 1.3846154).rgb) * 0.3162162;
	c += (tex2D(Src, uv + Step.xy * 3.2307692).rgb + tex2D(Src, uv - Step.xy * 3.2307692).rgb) * 0.0702703;
	return float4(c, 1);
}
