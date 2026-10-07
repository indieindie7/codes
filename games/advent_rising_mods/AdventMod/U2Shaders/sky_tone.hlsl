// The crash level's sky graded from olive toward a real desert haze sky: pale warm grey at the
// horizon, a little blue left in the clear patches (the level's sky measures hue 49-74 at
// value 0.37-0.48; desert photos are 0.7-0.9 bright, near grey at the horizon). Use with
// surface=<hash> sky_tone.hlsl on the sky textures; like rock_tone.hlsl it redoes the texture
// stages (c2) and only grades the texture.

sampler2D Tex     : register(s0);
sampler2D Second  : register(s1);
float4    Info    : register(c0);
float4    TFactor : register(c1);   // stage 1's constant colour when c2.z = 1
float4    Combine : register(c2);

#define LIFT     1.35
#define DESAT    0.55
#define TINT     float3(1.04, 1.00, 0.95)
#define KEEPBLUE 0.6                // how much of a texel's blue (clear sky) survives the desaturation

float4 main(float2 uv : TEXCOORD0, float2 t1 : TEXCOORD1, float4 diffuse : COLOR0) : COLOR
{
	float4 t = tex2D(Tex, uv);
	float l = dot(t.rgb, float3(0.30, 0.59, 0.11));
	float blue = saturate((t.b - max(t.r, t.g)) * 4);            // clear patches
	float3 c = lerp(t.rgb, l.xxx, DESAT * (1 - KEEPBLUE * blue)) * lerp(TINT, 1, blue) * LIFT;
	// the olive cast: green above both red and blue is pulled back toward their mean
	c.g = lerp(c.g, min(c.g, (c.r + c.b) * 0.5 + 0.06), 0.7 * (1 - blue));
	float a = t.a;
	if (Combine.x > 0)
	{
		c = saturate(c * diffuse.rgb * Combine.x);
		a *= diffuse.a;
	}
	if (Combine.y > 0)
		c = saturate(c * (Combine.z > 0 ? TFactor.rgb : tex2D(Second, t1).rgb) * Combine.y);
	return float4(saturate(c), a);
}
