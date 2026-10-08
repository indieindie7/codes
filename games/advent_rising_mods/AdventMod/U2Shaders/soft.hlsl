// soft.hlsl - soft particles (soft=1): what stage 0 of a sprite/beam draw did, then faded out
// where the scene behind it is near (no hard line where smoke meets the floor or a wall).
// Bound by the wrapper (U2Shaders::SoftBegin) for blended, unlit, depth-tested fixed-function
// draws that don't write depth; ps_2_a so the fixed-function fog still applies after it.

sampler2D Tex   : register(s0);   // the draw's own texture
sampler2D Depth : register(s7);   // the scene's depth (readable depth texture, point)
float4 ColOp : register(c0);      // stage 0 colour: op (0 arg1, 1 arg2, 2 multiply, 3 x2), arg1 is texture, arg2 is texture
float4 AlpOp : register(c1);      // the same for alpha
float4 Proj  : register(c2);      // the projection's _11, _22, _33, _43
float4 Soft  : register(c3);      // fade distance (world units), blending kind (0 alpha, 1 added, 2 multiply, 3 x2), debug

struct In
{
	float4 Diff : COLOR0;
	float2 UV   : TEXCOORD0;
	float3 Cam  : TEXCOORD7;      // camera-space position (stage 7 texgen)
};

float4 Combine(float4 op, float4 t, float4 d)
{
	float4 a = op.y > 0.5 ? t : d;
	float4 b = op.z > 0.5 ? t : d;
	if (op.x < 0.5) return a;
	if (op.x < 1.5) return b;
	if (op.x < 2.5) return a * b;
	return saturate(2 * a * b);
}

float4 main(In i) : COLOR
{
	float4 t = tex2D(Tex, i.UV);
	float4 c = float4(Combine(ColOp, t, i.Diff).rgb, Combine(AlpOp, t, i.Diff).a);

	// where this pixel lands on screen, and how far behind it the scene is
	float z = max(i.Cam.z, 0.001);
	float2 uv = float2(0.5 + 0.5 * Proj.x * i.Cam.x / z, 0.5 - 0.5 * Proj.y * i.Cam.y / z);
	float d = tex2D(Depth, uv).r;
	float scene = d >= 0.999999 ? 1e8 : Proj.w / (d - Proj.z);
	float fade = saturate((scene - i.Cam.z) / Soft.x);
	fade = fade * fade * (3 - 2 * fade);

	if (Soft.z > 0.5)
		return float4(0, fade, 1 - fade, c.a);
	if (Soft.y < 0.5)
		c.a *= fade;
	else if (Soft.y < 1.5)
		c *= fade;
	else if (Soft.y < 2.5)
		c.rgb = lerp(1, c.rgb, fade);
	else
		c.rgb = lerp(0.5, c.rgb, fade);
	return c;
}
