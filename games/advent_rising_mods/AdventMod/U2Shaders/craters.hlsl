// SDF craters (the fork's craters=; own code, after Mike Turitzin's dynamic SDF talk).
// The mod sends each hole as a sphere (craters.hpp). A pixel of a surface inside a sphere's
// opening is in the hole: the view ray goes on to where it leaves that sphere (closed form, no
// march), and the inside is drawn there with the wall's own colour, lit by the inside's normal
// and darker with depth. A sphere only cuts the surface it was put on (the pixel's normal and
// plane must match the hole's), so characters and other walls in front stay whole.
// Nothing is written to the depth: fog and later passes see the flat wall.
// (10-11: a marched smooth union of all 16 holes compiled to 26 KB and took 6 s to build in the
// game, a freeze per device reset; one sphere per pixel builds in well under a second.)

float4 Px    : register(c0);     // 1/w, 1/h, w, h
float4 Proj  : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Fx    : register(c2);     // strength, debug, holes in use, soot ring strength
float4 Up    : register(c3);     // world up in camera space (xyz)
float4 HoleC[16] : register(c4); // per hole: centre in camera space, r
float4 HoleN[16] : register(c20); // per hole: normal in camera space, lift
sampler Scene : register(s0);
sampler Depth : register(s1);

#define HOLES 16

void CratersVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float ViewZ(float2 uv)
{
	float d = tex2Dlod(Depth, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 1e6 : Proj.w / (d - Proj.z);
}

float3 CamPos(float2 uv)
{
	float z = ViewZ(uv);
	float2 ndc = float2(uv.x * 2 - 1, 1 - uv.y * 2);
	return float3(ndc.x * z / Proj.x, ndc.y * z / Proj.y, z);
}

float2 ToUv(float3 p)
{
	float2 ndc = float2(p.x * Proj.x, p.y * Proj.y) / max(p.z, 1);
	return float2(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
}

float Shade(float3 nn, float3 v)
{
	return 0.45 + 0.35 * dot(nn, Up.xyz) + 0.35 * saturate(dot(nn, -v));
}

float4 CratersPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 base = tex2Dlod(Scene, float4(uv, 0, 0));
	float3 p = CamPos(uv);
	if (p.z > 5e5)
		return base;
	// the normal from the nearer neighbour on each axis (as ssr.hlsl)
	float3 r = CamPos(uv + float2(Px.x, 0)), l = CamPos(uv - float2(Px.x, 0));
	float3 d = CamPos(uv + float2(0, Px.y)), u = CamPos(uv - float2(0, Px.y));
	float3 dx = abs(r.z - p.z) < abs(l.z - p.z) ? r - p : p - l;
	float3 dy = abs(d.z - p.z) < abs(u.z - p.z) ? d - p : p - u;
	float3 n = normalize(cross(dy, dx));
	if (dot(n, p) > 0)
		n = -n;
	// the hole this pixel is in (the deepest-reaching one), or the soot ring just outside one;
	// fixed indices (unrolled): ps_3_0 turned a counted index into long compare chains
	float4 hc = 0;
	float best = 0, soot = 0;
	[unroll] for (int i = 0; i < HOLES; i++)
	{
		float4 c = HoleC[i], m = HoleN[i];
		bool cuts = i < Fx.z && dot(n, m.xyz) > 0.6 && abs(dot(p - c.xyz, m.xyz) + m.w) < 0.15 * c.w + 3;
		float dist = length(p - c.xyz);
		float into = cuts ? c.w - dist : -1;              // how far inside the opening
		if (into > best)
		{
			best = into;
			hc = c;
		}
		// a sooty, broken ring just outside the opening
		float open = sqrt(max(c.w * c.w - m.w * m.w, 1));
		float ring = 1 - saturate((dist - open) / (0.3 * open));
		soot = max(soot, cuts && into <= 0 ? ring : 0);
	}
	if (best <= 0)
	{
		if (soot <= 0)
			return base;
		return float4(base.rgb * (1 - Fx.w * soot * soot), base.a);
	}
	// on along the view ray to where it leaves the sphere (the far root; p is inside it)
	float3 v = normalize(p);
	float3 oc = p - hc.xyz;
	float b = dot(oc, v);
	float t = -b + sqrt(max(b * b - dot(oc, oc) + hc.w * hc.w, 0));
	float3 x = p + v * t;
	float3 nn = normalize(hc.xyz - x);                  // the inside's normal, into the hole
	float below = max(-dot(x - p, n), 0);               // depth under the surface
	// the wall's own colour, from the surface right above that point (a parallax-like shift)
	float2 suv = ToUv(x + n * below);
	if (any(suv < 0) || any(suv > 1))
		suv = uv;
	float3 rock = tex2Dlod(Scene, float4(suv, 0, 0)).rgb;
	float light = Shade(nn, v) / max(Shade(n, v), 0.2);
	float ao = exp(-1.6 * below / hc.w);
	float3 inside = rock * 0.8 * light * ao;
	if (Fx.y > 0.5)
		inside = lerp(inside, float3(1, 0.2, 0.1), 0.4);
	return float4(lerp(base.rgb, inside, Fx.x), base.a);
}
