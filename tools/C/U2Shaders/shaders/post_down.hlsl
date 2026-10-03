// Mip-chain bloom, going down: one level of the bright map shrunk to half its size with the
// 13-tap filter from Jimenez, "Next Generation Post Processing in Call of Duty: Advanced
// Warfare" (SIGGRAPH 2014): five overlapping 2x2 boxes (bilinear taps), the centre one weighted
// 0.5 and the four corner ones 0.125, so small bright spots don't flicker as the view moves.

sampler2D Src   : register(s0);   // the level above (twice this size)
float4    Texel : register(c0);   // 1/width, 1/height of that level

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float2 o = Texel.xy;
	float3 a = tex2D(Src, uv + o * float2(-2, -2)).rgb;
	float3 b = tex2D(Src, uv + o * float2( 0, -2)).rgb;
	float3 c = tex2D(Src, uv + o * float2( 2, -2)).rgb;
	float3 d = tex2D(Src, uv + o * float2(-1, -1)).rgb;
	float3 e = tex2D(Src, uv + o * float2( 1, -1)).rgb;
	float3 f = tex2D(Src, uv + o * float2(-2,  0)).rgb;
	float3 g = tex2D(Src, uv).rgb;
	float3 h = tex2D(Src, uv + o * float2( 2,  0)).rgb;
	float3 i = tex2D(Src, uv + o * float2(-1,  1)).rgb;
	float3 j = tex2D(Src, uv + o * float2( 1,  1)).rgb;
	float3 k = tex2D(Src, uv + o * float2(-2,  2)).rgb;
	float3 l = tex2D(Src, uv + o * float2( 0,  2)).rgb;
	float3 m = tex2D(Src, uv + o * float2( 2,  2)).rgb;
	float3 r = (d + e + i + j) * 0.125
	         + (a + b + f + g) * 0.03125 + (b + c + g + h) * 0.03125
	         + (f + g + k + l) * 0.03125 + (g + h + l + m) * 0.03125;
	return float4(r, 1);
}
