// Wet blood: the shine a liquid film has, added over Advent's blood decals.
//
// Use with gloss=<hash> blood_gloss.hlsl: after the game draws the decal (which multiplies the
// floor: it can darken and redden, never shine), the fork draws the same geometry again with
// this shader and ADDS what it returns. So this returns light only: sharp highlights from the
// game's lights and a sheen of the surroundings at grazing angles (Fresnel), both where there
// is blood, and most where it is thickest.
//
// How much blood a pixel holds comes from how far the decal darkens the floor below its neutral
// brightness (c1.z: mid-grey for the decals' "multiply x2"). The thickness also tilts the
// surface a little where it changes (the edge of a pool rounds off like a drop's), which puts a
// rim of light along pool edges.
//
// Drying: the fork ages each decal (c1.w: 1 fresh .. 0 dry, glossdry= sets the times). The
// shine fades with it, and a dry decal darkens what is under it (the pass blends ONE /
// SRCALPHA: the colour returned is added, the alpha multiplies the floor), so old blood goes
// from wet red to a dull brown-black; c16.x is how dark.
//
// Constants (the fork's GlossBegin): c0 time, 1, 1/w, 1/h; c1 x projected coordinates, y blend
// kind, z neutral brightness, w wetness; c2 glossfx= strength, sharpness, light gain, sheen gain; c3
// glossenv= the surroundings' colour and a multiplier; c8..c15 four lights in camera space
// (position or direction toward it, range (0 = directional); colour, 1 if used).

sampler2D Tex : register(s0);
float4 Info   : register(c0);
float4 Mode   : register(c1);
float4 Fx     : register(c2);
float4 Env    : register(c3);
float4 Light[8] : register(c8);
float4 Dry    : register(c16);

#define EDGE 6.0          // how strongly a change of thickness tilts the surface

float Amount(float2 uv)
{
	float4 t = tex2D(Tex, uv);
	float lum = dot(t.rgb, float3(0.30, 0.59, 0.11));
	return Mode.y < 0.5 ? t.a : saturate((Mode.z - lum) / (Mode.z * 0.85));
}

float4 main(float3 t0 : TEXCOORD0, float3 pos : TEXCOORD2) : COLOR
{
	float2 uv = Mode.x > 0.5 ? t0.xy / t0.z : t0.xy;
	float a = Amount(uv);
	if (a < 0.02)
		return float4(0, 0, 0, 1);              // nothing added, the floor kept as it is

	// the surface (flat: from the position's screen derivatives) and the view
	float3 dpx = ddx(pos), dpy = ddy(pos);
	float3 v = normalize(-pos);
	float3 n = normalize(cross(dpx, dpy));
	n = dot(n, v) < 0 ? -n : n;

	// the liquid's own shape: tilted away from where it gets thicker (screen-space gradient)
	float da = ddx(a), db = ddy(a);
	float3 gx = dpx - n * dot(dpx, n), gy = dpy - n * dot(dpy, n);
	float3 slope = (gx * da / max(dot(gx, gx), 1e-4) + gy * db / max(dot(gy, gy), 1e-4));
	n = normalize(n - slope * EDGE);

	// highlights from the game's lights
	float3 spec = 0;
	for (int i = 0; i < 4; i++)
	{
		float4 lp = Light[i * 2], lc = Light[i * 2 + 1];
		float3 toL = lp.w > 0 ? lp.xyz - pos : lp.xyz;
		float d = length(toL);
		float3 l = toL / max(d, 1e-3);
		float att = lp.w > 0 ? saturate(1 - d / lp.w) : 1;
		att *= att;
		float3 h = normalize(l + v);
		float s = pow(saturate(dot(n, h)), Fx.y) * saturate(dot(n, l) * 4);
		spec += lc.rgb * (s * att * lc.w);
	}

	// the surroundings, reflected at grazing angles (a liquid's Fresnel: ~2% head on)
	float f = 0.02 + 0.98 * pow(1 - saturate(dot(n, v)), 5);
	float3 sheen = Env.rgb * (Env.a * f);

	// thin smears dull fast; the shine comes with thickness, and goes as the decal dries
	float wet = a * a * (3 - 2 * a) * Mode.w;
	float dried = a * (1 - Mode.w);
	float3 brown = float3(0.010, 0.006, 0.0) * dried;      // dried blood is browner, not only darker
	return float4((spec * Fx.z + sheen * Fx.w) * (wet * Fx.x) + brown, 1 - dried * Dry.x);
}
