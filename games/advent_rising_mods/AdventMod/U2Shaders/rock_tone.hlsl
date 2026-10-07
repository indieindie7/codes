// Rock meshes graded toward real desert sandstone (Goblin Valley, Wadi Rum: the photos in
// design-refs/advent_crash_refs measure brightness 0.53-0.67 and saturation 0.13-0.40; the
// crash level's boulders draw at 0.17 and 0.65-0.72). Use with surface=<hash> rock_tone.hlsl
// on the rock textures: the shader redoes the texture stages (texture x vertex colour x
// lightmap, as the fork found them, c2) and grades the texture before the lighting, so the
// level's light and shadow on the rocks stay as they were.
//
// Also: a faint darkening of the texture's own dark parts (cracks read deeper) and a little
// local contrast, since a lifted, desaturated texture goes flat. ps_2_0 is enough.

sampler2D Tex     : register(s0);
sampler2D Second  : register(s1);   // stage 1's texture (usually the lightmap)
float4    Info    : register(c0);
float4    TFactor : register(c1);   // stage 1's constant colour when c2.z = 1
float4    Combine : register(c2);   // x: vertex colour factor, y: stage 1 factor (0 = not used)

#define LIFT       1.55             // brightness of the texture
#define DESAT      0.45             // 0 = the game's colour, 1 = grey
#define TINT       float3(1.05, 0.98, 0.92)   // warm sandstone, not orange
#define CRACKS     0.35             // how much darker the dark parts get
#define CONTRAST   0.25             // local contrast against a blurred read

float4 main(float2 uv : TEXCOORD0, float2 t1 : TEXCOORD1, float4 diffuse : COLOR0) : COLOR
{
	float4 t = tex2D(Tex, uv);
	float3 lum3 = float3(0.30, 0.59, 0.11);
	float l = dot(t.rgb, lum3);
	float blur = dot(tex2Dbias(Tex, float4(uv, 0, 3)).rgb, lum3);
	float3 c = lerp(t.rgb, l.xxx, DESAT) * TINT * LIFT;
	c *= 1 + CONTRAST * (l - blur) / max(blur, 0.05);          // stone grain
	c *= 1 - CRACKS * saturate((blur * 0.7 - l) / max(blur * 0.7, 0.02));   // cracks
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
