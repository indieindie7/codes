// char_pbr.hlsl - a character's (or weapon's) texture shaded as a physically based material
// (pbr=HASH map.dds): the game's own lights, per pixel, with a normal map, roughness and
// metalness from the rule's material map on s3:
//   r, g  the surface normal in the texture's own space (x, y; z is rebuilt)
//   b     roughness (0 mirror smooth .. 1 chalk)
//   a     metalness (0 cloth, skin, paint .. 1 bare metal)
// The diffuse part is char_light.hlsl's (wrapped diffuse, hemisphere ambient), so a material
// with a flat map looks as the character did; on top come a GGX highlight from each light and
// a sheen from the ambient light at grazing angles. Metals lose their diffuse colour and tint
// their highlights with it. Constants: see CharBegin in u2shaders.hpp (c5.y = 1: the map is
// there). The game's colours are gamma-space and are lit as they are, like the game does.

sampler2D Tex     : register(s0);
sampler2D Layer   : register(s1);   // Advent's skin shader: a second lit layer,
sampler2D LayerMask : register(s2); // its mask,
sampler2D Glow    : register(s3);   // and where the texture shows unlit (lights on a suit)
sampler2D Maps    : register(s4);
float4    GameC0  : register(c1);   // that shader's constants: the colour everything is times,
float4    GameC1  : register(c6);   // the mask's channel,
float4    GameC2  : register(c7);   // the glow's channel
float4    Setup   : register(c2);   // x: the texture's factor (1, 2, 4), y: number of lights (0-4),
                                    // z: highlight strength, w: normal map strength
float4    Ambient : register(c3);   // rgb: ambient x material ambient + emissive
float4    Up      : register(c4);   // xyz: world up, in view space
float4    Use     : register(c5);   // x: 1 = the texture is used, y: 1 = the material map is there,
                                    // z: 1 = drawn by Advent's skin shader (the layers above), w: debug view
float4    Lights[16] : register(c8);  // 4 per light (up to 4), see CharBegin

#define WRAP 0.5      // as char_light.hlsl
#define HEMI 0.4
#define SPEC Setup.z  // highlight strength (the rule's third value, 1 if left out)
#define BUMP Setup.w  // normal map strength (its fourth)

float4 main(float2 uv : TEXCOORD0, float2 uv1 : TEXCOORD1, float2 uv2 : TEXCOORD2, float2 uv3 : TEXCOORD3,
	float3 normal : TEXCOORD4, float3 pos : TEXCOORD5) : COLOR
{
	float3 ng = normalize(normal);
	float3 v = normalize(-pos);
	ng = dot(ng, v) < -0.2 ? -ng : ng;       // back faces of two-sided parts face the camera

	float4 m = Use.y > 0.5 ? tex2D(Maps, uv) : float4(0.5, 0.5, 0.5, 0);
	// the texture's axes on the surface, from how position and texture coordinates change
	// across the screen (no tangents in the game's vertices)
	float3 dp1 = ddx(pos), dp2 = ddy(pos);
	float2 du1 = ddx(uv), du2 = ddy(uv);
	float3 dp2perp = cross(dp2, ng), dp1perp = cross(ng, dp1);
	float3 T = dp2perp * du1.x + dp1perp * du2.x;
	float3 B = dp2perp * du1.y + dp1perp * du2.y;
	float scale = rsqrt(max(max(dot(T, T), dot(B, B)), 1e-12));
	float2 nxy = (m.rg * 2 - 1) * BUMP;
	float3 n = normalize(T * scale * nxy.x + B * scale * nxy.y + ng * sqrt(saturate(1 - dot(nxy, nxy))));

	float4 t = Use.x > 0.5 ? tex2D(Tex, uv) : float4(1, 1, 1, 1);
	float3 own = t.rgb;                       // the texture itself, for the unlit parts
	float glow = 0;
	if (Use.z > 0.5)
	{
		t.rgb = (t.rgb + tex2D(Layer, uv1).rgb * dot(tex2D(LayerMask, uv2).rgb, GameC1.rgb)) * GameC0.rgb;
		glow = saturate(dot(tex2D(Glow, uv3).rgb, GameC2.rgb));
	}
	float rough = clamp(m.b, 0.08, 1), metal = m.a;
	float a = rough * rough, a2 = a * a;
	float3 f0 = lerp(0.04, t.rgb, metal);
	float nv = saturate(dot(n, v));

	float3 direct = 0, shine = 0;
	for (int i = 0; i < 4; i++)
	{
		float4 P = Lights[i * 4], D = Lights[i * 4 + 1], C = Lights[i * 4 + 2], A = Lights[i * 4 + 3];
		float3 toL = P.w > 2.5 ? -D.xyz : P.xyz - pos;
		float d = length(toL);
		float3 l = toL / max(d, 0.0001);
		float att = P.w > 2.5 ? 1 : (d < C.w ? 1 / max(A.x + A.y * d + A.z * d * d, 0.0001) : 0);
		if (P.w > 1.5 && P.w < 2.5)
			att *= saturate((dot(-l, D.xyz) - D.w) / max(A.w - D.w, 0.0001));
		att *= i < Setup.y;
		float ndl = dot(n, l);
		float w = ndl * 0.5 + 0.5;
		direct += C.rgb * att * lerp(saturate(ndl), w * w, WRAP);
		// GGX, with the visibility term folded in (Karis' mobile form)
		float3 h = normalize(l + v);
		float nh = saturate(dot(n, h)), lh = saturate(dot(l, h));
		float dd = nh * nh * (a2 - 1) + 1;
		shine += C.rgb * att * saturate(ndl) * a2 / (4 * dd * dd * max(lh * lh, 0.1) * (rough + 0.5));
	}

	float sky = dot(n, Up.xyz) * 0.5 + 0.5;
	float3 ambient = Ambient.rgb * lerp(1 - HEMI, 1, sky);
	// what the ambient light adds at grazing angles, less on rough surfaces
	float3 fresnel = f0 + (max(1 - rough, f0) - f0) * pow(1 - nv, 5);
	float3 skyShine = Ambient.rgb * lerp(1 - HEMI, 1, dot(reflect(-v, n), Up.xyz) * 0.5 + 0.5);

	float3 diffuse = t.rgb * (1 - metal) * saturate(ambient + direct) * Setup.x;
	float3 spec = (f0 * shine + fresnel * skyShine * (1 - rough)) * SPEC * Setup.x;
	if (Use.w > 7.5) return float4(GameC1.rgb, 1);
	if (Use.w > 6.5) return float4(GameC0.rgb, 1);
	if (Use.w > 5.5) return float4(tex2D(LayerMask, uv2).rgb, 1);
	if (Use.w > 4.5) return float4(tex2D(Layer, uv1).rgb, 1);
	if (Use.w > 3.5) return float4(metal, metal, metal, 1);
	if (Use.w > 2.5) return float4(rough, rough, rough, 1);
	if (Use.w > 1.5) return float4(n * 0.5 + 0.5, 1);
	if (Use.w > 0.5) return float4(saturate(ambient + direct), 1);
	return float4(lerp(saturate(diffuse + spec), own, glow), t.a);
}
