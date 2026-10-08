// atmos.hlsl - height fog and light shafts (atmos=1), compiled by the wrapper as
// vs_3_0/ps_3_0 with ATMOS_PASS set:
//   1 MaskPS   half size: the sky's bright parts, more the nearer the sun (what can shine)
//   2 RayPS    half size, three times: a blur along the line toward the sun, each pass
//              reaching 8x further (8 taps each: 512 steps' worth in 24 reads)
//   3 ApplyPS  full size: exponential height fog from the scene's depth (Inigo Quilez,
//              "better fog": the fog integrated along the view ray through air that thins
//              with height), tinted toward the sun's colour in the sun's direction, then
//              the shafts added (screen blend, so they never clip)
// The first-person weapon (drawn after a mid-frame depth clear) gets no fog; the sky gets the
// fog of a ray of atmosfog2's sky length, so the horizon hazes and straight up stays clear.

float4 Px : register(c0);       // the target's 1/w, 1/h, w, h
float4 Proj : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Small : register(c2);    // apply: the shafts' 1/w, 1/h, w, h
float4 Scr : register(c3);      // the frame's 1/w, 1/h, w, h
float4 Fog : register(c4);      // atmosfog= r g b density
float4 Fog2 : register(c5);     // atmosfog2= falloff (per unit of height), camera's height over the densest air, most fog, sky distance
float4 Shaft : register(c6);    // atmosshafts= strength, length (0..1 toward the sun), sky threshold, sun tint
float4 Sun : register(c7);      // the sun on screen (u, v), how visible (0..1), blur reach this pass
float4 SunCol : register(c8);   // its colour (brightest channel 1)
float4 SunDir : register(c9);   // toward it, camera space; w = 1 if there is a sun
float4 InvX : register(c10);    // camera -> world, row by row (translation in w)
float4 InvY : register(c11);
float4 InvZ : register(c12);
float4 Debug : register(c13);   // 1 fog amount, 2 shafts alone, 3 the mask

sampler S0 : register(s0);
sampler S1 : register(s1);
sampler S2 : register(s2);
sampler S3 : register(s3);

void AtmosVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float3 ViewPos(float2 uv, float z)
{
	return float3((2 * uv.x - 1) * z / Proj.x, (1 - 2 * uv.y) * z / Proj.y, z);
}

// view depth from the depth buffer (0 = sky / nothing)
float ViewZ(sampler s, float2 uv)
{
	float d = tex2Dlod(s, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 0 : Proj.w / (d - Proj.z);
}

// a pixel of the first-person weapon (drawn after the depth clear)
bool Weapon(float2 uv)
{
	float o = tex2Dlod(S3, float4(uv, 0, 0)).r;
	return o > 0 && o < 0.999999;
}

#if ATMOS_PASS == 1
// S0 = the scene's depth, S1 = the frame (linear), S2 = the weapon's depth (or none)
float4 MaskPS(float2 uv : TEXCOORD0) : COLOR
{
	float d = tex2Dlod(S0, float4(uv, 0, 0)).r;
	float o = tex2Dlod(S2, float4(uv, 0, 0)).r;
	if (d < 0.999999 || (o > 0 && o < 0.999999))
		return float4(0, 0, 0, 1);
	float3 c = tex2Dlod(S1, float4(uv, 0, 0)).rgb;
	float lum = dot(c, float3(0.299, 0.587, 0.114));
	float bright = saturate((lum - Shaft.z) / max(1 - Shaft.z, 0.01));
	float2 v = (uv - Sun.xy) * float2(Px.z / Px.w, 1);
	float near = saturate(1 - length(v) / 0.7);
	return float4(c * bright * near * near, 1);
}
#endif

#if ATMOS_PASS == 2
// S0 = the last pass (linear); Sun.w = this pass's reach (1/64, 1/8, 1 of the full length)
float4 RayPS(float2 uv : TEXCOORD0) : COLOR
{
	float2 step = (Sun.xy - uv) * Shaft.y * Sun.w / 8;
	float3 sum = 0;
	float wsum = 0;
	for (int j = 0; j < 8; j++)
	{
		float w = 1 - j * 0.07;
		sum += tex2Dlod(S0, float4(uv + step * j, 0, 0)).rgb * w;
		wsum += w;
	}
	return float4(sum / wsum, 1);
}
#endif

#if ATMOS_PASS == 3
// S0 = the scene's depth, S1 = the frame, S2 = the shafts (linear, or none), S3 = the weapon's depth
float4 ApplyPS(float2 uv : TEXCOORD0) : COLOR
{
	float3 c = tex2Dlod(S1, float4(uv, 0, 0)).rgb;
	float z = ViewZ(S0, uv);
	float amount = 0;
	if (!Weapon(uv))
	{
		// the view ray in the world
		float3 pc = ViewPos(uv, z > 0 ? z : 1);
		float3 dc = normalize(pc);
		float3 rd = float3(dot(dc, InvX.xyz), dot(dc, InvY.xyz), dot(dc, InvZ.xyz));
		float t = z > 0 ? length(pc) : Fog2.w;
		float h0 = Fog2.y;                           // the camera's height over the densest air: the fog
		                                             // follows the camera up and down (levels sit at any z),
		                                             // what lies below the camera is still thicker
		float a = Fog.w, b = max(Fog2.x, 1e-7);
		float start = a * exp(min(-h0 * b, 20));     // the density where the camera is
		float fog = abs(rd.z) > 1e-4 ? start * (1 - exp(min(-t * rd.z * b, 40))) / (b * rd.z) : start * t;
		amount = min(1 - exp(-max(fog, 0)), Fog2.z);
		// toward the sun the haze takes the sun's colour
		float toward = SunDir.w * pow(saturate(dot(dc, SunDir.xyz)), 6) * Shaft.w;
		float3 fc = lerp(Fog.rgb, SunCol.rgb * max(dot(Fog.rgb, float3(0.299, 0.587, 0.114)) * 1.5, 0.5), saturate(toward));
		c = lerp(c, fc, amount);
	}
	float3 s = tex2Dlod(S2, float4(uv, 0, 0)).rgb * SunCol.rgb * Shaft.x * Sun.z;
	if (Debug.x > 0.5)
	{
		if (Debug.x < 1.5) return float4(amount.xxx, 1);
		if (Debug.x < 2.5) return float4(s, 1);
		return float4(tex2Dlod(S2, float4(uv, 0, 0)).rgb, 1);
	}
	c = 1 - (1 - saturate(c)) * (1 - saturate(s));
	return float4(c, 1);
}
#endif
