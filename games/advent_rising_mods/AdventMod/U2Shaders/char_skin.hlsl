// char_skin.hlsl - skin, flesh and alien hide: pbr=HASH none 1 1 char_skin.hlsl (the map is
// optional: "none" = flat). Same inputs as char_pbr.hlsl (see CharBegin in u2shaders.hpp); a
// skin diffuse instead of the plain wrapped one. Valve's lightwarp skin recipe as maths in
// place of a painted ramp, close to pre-integrated skin (Penner 2011) without its lookup:
//   - per-colour wrap: red wraps furthest past the terminator, blue least, so the shadow edge
//     goes warm and soft (light that entered the skin comes out further on);
//   - a warm band just around the terminator;
//   - the diffuse sees a normal pulled toward the surface's own (skin hides small bumps in
//     diffuse light; they stay in the highlight);
//   - a soft rim from the ambient light at grazing angles, stronger facing up, and a broad
//     low highlight (skin oil).
// Kept small for ps_2_a: 32 constants, 16 of them the lights.

sampler2D Tex       : register(s0);
sampler2D Layer     : register(s1);   // Advent's skin shader: a second lit layer,
sampler2D LayerMask : register(s2);   // its mask,
sampler2D Glow      : register(s3);   // and where the texture shows unlit
sampler2D Maps      : register(s4);
float4    GameC0    : register(c1);
float4    GameC1    : register(c6);
float4    GameC2    : register(c7);
float4    Setup     : register(c2);   // x: the texture's factor, y: lights (0-4), z: highlight, w: bump
float4    Ambient   : register(c3);
float4    Up        : register(c4);
float4    Use       : register(c5);   // x: texture used, y: map there, z: Advent skin layers / stage 1
float4    Lights[16] : register(c8);

static const float3 SKINWRAP = float3(0.75, 0.42, 0.32);

float4 main(float2 uv : TEXCOORD0, float2 uv1 : TEXCOORD1, float2 uv2 : TEXCOORD2, float2 uv3 : TEXCOORD3,
	float3 normal : TEXCOORD4, float3 pos : TEXCOORD5) : COLOR
{
	float3 ng = normalize(normal);
	float3 v = normalize(-pos);
	ng = dot(ng, v) < -0.2 ? -ng : ng;

	// the normal map (if any), along the texture's axes from screen derivatives
	float2 nxy = Use.y > 0.5 ? (tex2D(Maps, uv).rg * 2 - 1) * Setup.w : 0;
	float3 dp1 = ddx(pos), dp2 = ddy(pos);
	float2 du1 = ddx(uv), du2 = ddy(uv);
	float3 T = cross(dp2, ng) * du1.x + cross(ng, dp1) * du2.x;
	float3 B = cross(dp2, ng) * du1.y + cross(ng, dp1) * du2.y;
	float scale = rsqrt(max(max(dot(T, T), dot(B, B)), 1e-12));
	float3 n = normalize((T * nxy.x + B * nxy.y) * scale + ng);
	float3 ns = normalize(n + ng * 1.5);

	float4 t = Use.x > 0.5 ? tex2D(Tex, uv) : 1;
	float3 own = t.rgb;
	float glow = 0;
	if (Use.z > 1.5)
		t.rgb *= tex2D(Layer, uv1).rgb * GameC0.w;
	else if (Use.z > 0.5)
	{
		t.rgb = (t.rgb + tex2D(Layer, uv1).rgb * dot(tex2D(LayerMask, uv2).rgb, GameC1.rgb)) * GameC0.rgb;
		glow = saturate(dot(tex2D(Glow, uv3).rgb, GameC2.rgb));
	}

	float3 direct = 0;
	float shine = 0;
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
		float ndl = dot(ns, l);
		float3 w3 = saturate((ndl + SKINWRAP) / (1 + SKINWRAP));
		direct += C.rgb * att * (w3 * w3 + (SKINWRAP - 0.3) * 0.36 * saturate(1 - abs(ndl) * 2.5));
		float nh = saturate(dot(n, normalize(l + v)));
		shine += dot(C.rgb, 0.33) * att * pow(nh, 24) * saturate(dot(n, l));
	}

	float nv = saturate(dot(n, v));
	float sky = dot(n, Up.xyz) * 0.5 + 0.5;
	float3 ambient = Ambient.rgb * (0.6 + 0.4 * sky);
	float3 rim = Ambient.rgb * 0.55 * pow(1 - nv, 4) * sky;
	float3 c = t.rgb * saturate(ambient + direct + rim) * Setup.x + shine * 0.12 * Setup.z * Setup.x;
	return float4(lerp(saturate(c), own, glow), t.a);
}
