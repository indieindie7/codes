// Floor reflections (the fork's ssr=; screen-space reflections, own code).
// The game draws no material data, so only what the depth says is kept: each pixel's position
// and normal are rebuilt from the depth, and only floors (normals near world up) reflect. The
// reflected ray is marched across the screen until it passes behind the depth, and the frame's
// colour there is blended in, stronger at grazing angles (Fresnel), faded at the screen's edges
// and with distance, as a reflection that leaves the screen has nothing to show.

float4 Px    : register(c0);     // 1/w, 1/h, w, h
float4 Proj  : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Fx    : register(c2);     // strength, longest ray (world units), thickness (world units), debug
float4 Up    : register(c3);     // world up in camera space (xyz)
sampler Scene : register(s0);
sampler Depth : register(s1);

#define STEPS 24

void SsrVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
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
	float2 ndc = float2(p.x * Proj.x, p.y * Proj.y) / p.z;
	return float2(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
}

float4 SsrPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 base = tex2Dlod(Scene, float4(uv, 0, 0));
	float3 p = CamPos(uv);
	if (p.z > 5e5)
		return base;
	// the normal from the nearer neighbour on each axis (keeps edges from bending it)
	float3 r = CamPos(uv + float2(Px.x, 0)), l = CamPos(uv - float2(Px.x, 0));
	float3 d = CamPos(uv + float2(0, Px.y)), u = CamPos(uv - float2(0, Px.y));
	float3 dx = abs(r.z - p.z) < abs(l.z - p.z) ? r - p : p - l;
	float3 dy = abs(d.z - p.z) < abs(u.z - p.z) ? d - p : p - u;
	float3 n = normalize(cross(dy, dx));
	if (dot(n, p) > 0)
		n = -n;
	float floorness = saturate((dot(n, Up.xyz) - 0.85) / 0.1);
	if (floorness <= 0)
		return Fx.w > 0.5 ? float4(base.rgb * 0.3, 1) : base;
	float3 v = normalize(p);
	float3 rd = reflect(v, n);
	if (rd.z < -0.2)                                         // toward the camera: nothing on screen to show
		return base;
	// busy textures (sand, grass, rock) are rough: only fairly plain floors reflect clearly
	float lb = dot(base.rgb, 0.333);
	float busy = 0;
	busy += abs(dot(tex2Dlod(Scene, float4(uv + float2(2 * Px.x, 0), 0, 0)).rgb, 0.333) - lb);
	busy += abs(dot(tex2Dlod(Scene, float4(uv - float2(2 * Px.x, 0), 0, 0)).rgb, 0.333) - lb);
	busy += abs(dot(tex2Dlod(Scene, float4(uv + float2(0, 2 * Px.y), 0, 0)).rgb, 0.333) - lb);
	busy += abs(dot(tex2Dlod(Scene, float4(uv - float2(0, 2 * Px.y), 0, 0)).rgb, 0.333) - lb);
	float plain = 1 - saturate((busy / (lb + 0.05) - 0.15) * 2.5);
	if (plain <= 0)
		return Fx.w > 0.5 ? float4(0, floorness * 0.3, 0.3, 1) : base;
	// per-pixel jitter on the steps, so the stepping shows as fine noise and not as rings
	float jit = frac(52.9829189 * frac(dot(uv * Px.zw, float2(0.06711056, 0.00583715))));
	float3 q = p + n * 2;
	float hit = 0;
	float2 huv = uv;
	float tPrev = 0;
	for (int i = 1; i <= STEPS; i++)
	{
		float k = (i - 1 + jit) / STEPS;
		float t = Fx.y * k * k + 4;                             // denser near the floor point
		float3 s = q + rd * t;
		if (s.z <= 1)
			break;
		float2 suv = ToUv(s);
		if (any(suv < 0) || any(suv > 1))
			break;
		float sz = ViewZ(suv);
		if (s.z > sz && s.z - sz < Fx.z + t * 0.05)
		{
			// halve back toward the last step that was in front, for a tighter edge
			float a = tPrev, b = t;
			for (int j = 0; j < 4; j++)
			{
				float m = (a + b) * 0.5;
				float3 sm = q + rd * m;
				if (sm.z > ViewZ(ToUv(sm))) b = m; else a = m;
			}
			huv = ToUv(q + rd * b);
			hit = 1 - k * k;
			break;
		}
		tPrev = t;
	}
	float2 edge = saturate(min(huv, 1 - huv) * 8);
	float fres = pow(1 - saturate(dot(-v, n)), 4);
	float w = hit * edge.x * edge.y * floorness * plain * Fx.x * (0.25 + 0.75 * fres);
	if (Fx.w > 0.5)
		return float4(w, floorness * 0.3, plain * 0.3, 1);
	float3 c = tex2Dlod(Scene, float4(huv, 0, 0)).rgb;
	return float4(lerp(base.rgb, c, saturate(w)), base.a);
}
