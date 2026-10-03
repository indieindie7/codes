// Mip-chain bloom, going up: the smaller (wider) level enlarged with a 3x3 tent filter and mixed
// into this level's own shrunk bright map (Jimenez 2014; the mix by "scatter" as in Unity's
// URP bloom). Repeated from the smallest level up to half size, it adds tight glow around a
// light and a wide soft haze at once.

sampler2D Lower : register(s0);   // the next smaller level, already built up
sampler2D Here  : register(s1);   // this level's shrunk bright map
float4    Texel : register(c0);   // 1/width, 1/height of the smaller level
float4    Mix   : register(c1);   // x = scatter: 0 only this level, 1 only the wider glow

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float2 o = Texel.xy;
	float3 t = tex2D(Lower, uv).rgb * 4
	         + (tex2D(Lower, uv + float2(-o.x, 0)).rgb + tex2D(Lower, uv + float2(o.x, 0)).rgb
	          + tex2D(Lower, uv + float2(0, -o.y)).rgb + tex2D(Lower, uv + float2(0, o.y)).rgb) * 2
	         + tex2D(Lower, uv - o).rgb + tex2D(Lower, uv + o).rgb
	         + tex2D(Lower, uv + float2(-o.x, o.y)).rgb + tex2D(Lower, uv + float2(o.x, -o.y)).rgb;
	t /= 16;
	return float4(lerp(tex2D(Here, uv).rgb, t, Mix.x), 1);
}
