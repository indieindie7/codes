// Shadow-map pass: the character drawn as a flat silhouette into its shadow map.
// Unreal II keeps the shadow in alpha (255 lit, lower = shadowed) and a constant grey in the
// colour, which then only scales the engine's own blur pass. The projector pass with
// contact hardening (pcss_proj.hlsl) reads this sharp map directly, so red is free to carry
// the silhouette's world height: frac(z / 256), one 8-bit step per unit, wrapping every 256
// units (only differences under that matter; a body is ~110 tall).

float4 Info : register(c0);    // y: debug mode
float4 TF   : register(c1);    // the draw's texture factor: what the engine would have written
float4 Zrow : register(c4);    // camera space (the light's view) -> world height

float4 main(float3 pos : TEXCOORD2) : COLOR    // pos: camera-space position in the light's view
{
	if (Info.y > 5.5)                            // debug 6: exactly what the engine writes
		return TF;
	return float4(frac(dot(float4(pos, 1), Zrow) / 256.0), TF.g, TF.b, TF.a);
}
