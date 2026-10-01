// Liandri heavy armour: the see-through dome and core.
// Swirling plasma inside glass, a bright rim where the glass turns away from the
// eye, and the scene behind bent by the glass.
//
// noise(): value noise by Inigo Quilez, MIT License
//   Copyright (c) 2013 Inigo Quilez - https://www.shadertoy.com/view/lsf3WH

sampler2D Tex   : register(s0);   // the armour's own texture
sampler2D Scene : register(s1);   // the frame so far
float4    Info  : register(c0);   // time, normals valid, 1/width, 1/height
float4x4  Proj  : register(c4);

float hash(float2 p)
{
	p = 50.0 * frac(p * 0.3183099 + float2(0.71, 0.113));
	return frac(p.x * p.y * (p.x + p.y));
}

float noise(float2 p)
{
	float2 i = floor(p);
	float2 f = frac(p);
	float2 u = f * f * (3.0 - 2.0 * f);
	return lerp(lerp(hash(i), hash(i + float2(1, 0)), u.x),
	            lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), u.x), u.y);
}

float fbm(float2 p)
{
	float v = 0.5 * noise(p);
	p = p * 2.03 + 17.0;
	v += 0.25 * noise(p);
	p = p * 2.01 + 5.0;
	v += 0.125 * noise(p);
	return v / 0.875;
}

float4 main(float2 uv : TEXCOORD0, float3 normal : TEXCOORD1, float3 pos : TEXCOORD2) : COLOR
{
	float t = Info.x;
	float3 n = normalize(normal);
	float3 v = normalize(-pos);
	float facing = abs(dot(n, v));                 // 1 = glass faces the eye, 0 = edge-on
	float rim = pow(saturate(1.0 - facing), 2.5);

	// slow swirl: noise bent by more noise, anchored to the armour's own texture map
	float2 q = uv * 9.0;
	float warp = fbm(q + float2(0.0, t * 0.07));
	float swirl = fbm(q * 1.7 + warp * 2.2 + float2(t * 0.05, -t * 0.09));
	float wisps = smoothstep(0.35, 0.85, swirl);

	// where this pixel is on screen, then look through the glass a little sideways
	float4 clip = mul(Proj, float4(pos, 1.0));
	float2 screen = clip.xy / clip.w * float2(0.5, -0.5) + 0.5 + Info.zw * 0.5;
	float2 bend = n.xy * float2(1.0, -1.0) * (0.012 + 0.02 * rim) + (warp - 0.5) * 0.006;
	float3 behind = tex2D(Scene, screen + bend).rgb;

	float3 deep  = float3(0.20, 0.06, 0.42);
	float3 glow  = float3(0.95, 0.45, 0.95);
	float3 edge  = float3(0.45, 0.80, 1.00);
	float3 plasma = lerp(deep, glow, wisps);

	float fill = 0.30 + 0.45 * wisps;              // how much plasma hides what is behind
	float3 colour = behind * float3(0.80, 0.72, 0.95) * (1.0 - fill) + plasma * fill;
	colour += edge * rim * 0.9;
	return float4(colour, 1.0);
}
