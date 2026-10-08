// sheen.hlsl - highlights and a grazing reflection added over a solid lightmapped surface
// (sheen=HASH sheen.hlsl [strength sharpness metal] in U2Shaders.ini). The wrapper draws the
// surface again with this, added on top (ONE/ONE, fog black so it fades with distance).
//   - Blinn highlights from the game's lights near the camera (the ones it lights characters
//     with), energy-normalized so a sharp highlight is small and bright;
//   - a Fresnel reflection of the "room": its brightness is the baked light at this spot
//     (the lightmap), brighter where the reflected ray looks up (ceiling lamps, sky), so
//     a floor shines toward the far end of a lit corridor and stays dark in dark corners;
//   - masked by the texture's own brightness (scuffs, seams and dirt shine less) and, for
//     metal, tinted by the texture's colour.

sampler2D Tex : register(s0);      // the surface's texture
sampler2D LightMap : register(s1); // its lightmap (when c16.x = 1)
float4 Info   : register(c0);      // time, 1, 1/w, 1/h
float4 Fx     : register(c2);      // sheenfx= strength, sharpness (Blinn exponent), Fresnel, mask contrast
float4 Env    : register(c3);      // sheenenv= the room's colour (r g b), multiplier
float4 Lights[8] : register(c8);   // 4 x (camera-space position or direction to it, range (0 = directional)), (colour, used)
float4 LmInfo : register(c16);     // 1 if a lightmap, its scale (x2 / x4)
float4 Up     : register(c17);     // the world's up in camera space
float4 Rule   : register(c18);     // this rule's strength, sharpness, metal (0 = the global ones / none)

struct In
{
	float4 Diff : COLOR0;
	float2 UV   : TEXCOORD0;
	float2 LmUV : TEXCOORD1;
	float3 N    : TEXCOORD4;       // camera-space normal
	float3 P    : TEXCOORD5;       // camera-space position
};

float4 main(In i) : COLOR
{
	float3 t = tex2D(Tex, i.UV).rgb;
	float3 light = LmInfo.x > 0.5 ? tex2D(LightMap, i.LmUV).rgb * LmInfo.y : i.Diff.rgb;
	float strength = Fx.x * (Rule.x > 0 ? Rule.x : 1);
	float sharp = Rule.y > 0 ? Rule.y : Fx.y;
	float metal = saturate(Rule.z);

	float3 n = normalize(i.N);
	float3 v = normalize(-i.P);
	if (dot(n, v) < 0)
		n = -n;                                    // two-sided geometry
	float nv = saturate(dot(n, v));

	// highlights from the game's lights
	float3 spec = 0;
	for (int k = 0; k < 4; k++)
	{
		float4 lp = Lights[2 * k], lc = Lights[2 * k + 1];
		if (lc.w < 0.5)
			continue;
		float3 l = lp.w > 0 ? lp.xyz - i.P : lp.xyz;
		float d = length(l);
		l /= max(d, 0.001);
		float att = lp.w > 0 ? saturate(1 - d / lp.w) : 1;
		att *= att;
		float nl = saturate(dot(n, l));
		float3 h = normalize(l + v);
		float3 col = lerp(dot(lc.rgb, float3(0.3, 0.59, 0.11)).xxx, lc.rgb, 0.5);   // the game's character lights are
		                                                                          // strongly coloured: half that on metal
		spec += col * pow(saturate(dot(n, h)), sharp) * (sharp + 8) / 25.1327 * nl * att;
	}

	// the room's reflection, as bright as the baked light here, brighter looking up
	float3 r = reflect(-v, n);
	float upness = saturate(0.5 + 0.5 * dot(r, Up.xyz));
	float fres = 0.04 + 0.96 * pow(1 - nv, 5);
	float3 room = Env.rgb * Env.w * light * (0.35 + 0.65 * upness * upness);
	float3 refl = room * fres * Fx.z;

	float lum = dot(t, float3(0.299, 0.587, 0.114));
	float mask = saturate(lerp(1, lum * 2.2, Fx.w));
	float3 tint = lerp(1, saturate(t * 2), metal);
	float3 c = (spec * (0.35 * light + 0.08) + refl) * tint * mask * strength;
	return float4(c, 1);
}
