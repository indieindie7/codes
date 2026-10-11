// eye_adapt.hlsl - eye adaptation (eyeadapt=strength min max speed), compiled by the wrapper as
// vs_3_0/ps_3_0 into a 1x1 target each frame:
//   the frame's average brightness: the log average of a 24x14 grid (linear light, the middle
//   counting more, as where the player looks), and the exposure that would bring it to
//   eyekey, ^ strength and held to min..max; eased toward from last frame's value in log
//   space, so a dark room opens up after a moment and a bright doorway is toned down.
// r = the exposure post_final multiplies by, g = the average, b = the exposure wanted.

float4 Off : register(c0);      // unused (the 1x1 target needs no half-texel shift)
float4 Ad : register(c1);       // this frame's step toward the wanted (0..1), strength, min, max
float4 Ad2 : register(c2);      // eyekey (the average brightness aimed for), 1 = start fresh

sampler S0 : register(s0);      // the frame (linear filtered: each tap averages 2x2)
sampler S1 : register(s1);      // last frame's 1x1

void EyeVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.xyz, 1);
	ouv = uv;
}

float4 AdaptPS(float2 uv : TEXCOORD0) : COLOR
{
	float sum = 0, wsum = 0;
	for (int y = 0; y < 14; y++)
		for (int x = 0; x < 24; x++)
		{
			float2 suv = (float2(x, y) + 0.5) / float2(24, 14);
			float3 c = tex2Dlod(S0, float4(suv, 0, 0)).rgb;
			c *= c;                                     // gamma 2, as post_final
			float l = dot(c, float3(0.2126, 0.7152, 0.0722));
			float2 d = suv - 0.5;
			float w = 0.3 + saturate(1 - 2.5 * dot(d, d));
			sum += w * log2(l + 0.002);
			wsum += w;
		}
	float avg = exp2(sum / wsum);
	float want = clamp(pow(Ad2.x / avg, Ad.y), Ad.z, Ad.w);
	float prev = tex2Dlod(S1, float4(0.5, 0.5, 0, 0)).r;
	if (Ad2.y > 0.5 || !(prev > 0))
		prev = want;
	float e = exp2(lerp(log2(prev), log2(want), Ad.x));
	return float4(e, avg, want, 1);
}
