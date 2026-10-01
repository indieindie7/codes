// Post pass 3: the frame finished before the HUD is drawn over it: sharpening, bloom, exposure,
// colour balance, saturation, contrast and a vignette. Settings come from U2Shaders.ini
// (bloom=, grade=, colour=, sharpen=); postsplit=1 leaves the right half untouched to compare.

sampler2D Scene    : register(s0);   // the finished 3D frame
sampler2D BloomMap : register(s1);   // the blurred bright parts (quarter size)
float4    Texel    : register(c0);   // 1/width, 1/height, 1 = compare split
float4    Bloom    : register(c1);   // threshold, intensity
float4    Grade    : register(c2);   // saturation, contrast, exposure, vignette
float4    Balance  : register(c3);   // colour balance r g b, sharpen

float4 main(float2 uv : TEXCOORD0) : COLOR
{
	float3 c = tex2D(Scene, uv).rgb;
	float3 original = c;

	// sharpen: push the pixel away from the average of its four neighbours
	float3 around = tex2D(Scene, uv + float2(Texel.x, 0)).rgb + tex2D(Scene, uv - float2(Texel.x, 0)).rgb
	              + tex2D(Scene, uv + float2(0, Texel.y)).rgb + tex2D(Scene, uv - float2(0, Texel.y)).rgb;
	c = saturate(c + (c - around * 0.25) * Balance.w);

	c += tex2D(BloomMap, uv).rgb * Bloom.y;
	c *= Grade.z * Balance.rgb;
	float luma = dot(c, float3(0.299, 0.587, 0.114));
	c = lerp(luma.xxx, c, Grade.x);
	c = (c - 0.5) * Grade.y + 0.5;
	float2 d = uv - 0.5;
	c *= 1 - Grade.w * dot(d, d) * 2;     // 0 at the centre, Grade.w darker in the corners

	c = (Texel.z > 0.5 && uv.x > 0.5) ? original : c;
	return float4(saturate(c), 1);
}
