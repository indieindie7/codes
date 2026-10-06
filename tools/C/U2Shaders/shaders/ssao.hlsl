// ssao.hlsl - screen-space ambient occlusion (ssao=1), compiled by the wrapper as
// ps_3_0/vs_3_0 with SSAO_PASS set:
//   1 GBufPS   the scene's depth -> view depth + normal (as gi.hlsl's), at the AO's size
//   2 AoPS     how much of the space around each point is filled: corners, wall feet,
//              contact under objects get darker. Scalable Ambient Obscurance (McGuire,
//              Mara, Luebke, HPG 2012): samples on a spiral in a disc whose size on screen
//              is a fixed distance in the world; each sample that rises above the surface
//              occludes, less the further it is
//   3 BlurPS   a depth-aware blur, once across and once down (no smearing over edges)
//   4 ApplyPS  the frame darkened by it, full size, upsampled by depth (joint bilateral);
//              the sky and a first-person weapon drawn after a depth clear are left alone
// ssaofx=strength radius intensity debug: strength 0-1 (how much of the darkening shows),
// radius in world units, intensity (how quickly it goes dark), debug 1 = the AO alone.

float4 Px : register(c0);       // the target's 1/w, 1/h, w, h
float4 Proj : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Step : register(c2);     // blur: one texel's step (x, y); apply: the AO's 1/w, 1/h, w, h
float4 Scr : register(c3);      // the frame's 1/w, 1/h, w, h
float4 Fx : register(c4);       // strength, radius, intensity, debug

sampler S0 : register(s0);
sampler S1 : register(s1);
sampler S2 : register(s2);
sampler S3 : register(s3);

void SsaoVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
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

float3 Normal(float4 g)
{
	return float3(g.y, g.z, -sqrt(saturate(1 - g.y * g.y - g.z * g.z)));
}

#if SSAO_PASS == 1
// S0 = the scene's depth, S1 = what was drawn after a mid-frame depth clear (or none)
float4 GBufPS(float2 uv : TEXCOORD0) : COLOR
{
	float z = ViewZ(S0, uv);
	float over = tex2Dlod(S1, float4(uv, 0, 0)).r;
	if (z <= 0 || (over > 0 && over < 0.999999))
		return float4(0, 0, 0, 0);
	float3 p = ViewPos(uv, z);
	// the normal from the nearer neighbour on each axis (so edges don't bend it)
	float2 dx = float2(Scr.x, 0), dy = float2(0, Scr.y);
	float zl = ViewZ(S0, uv - dx), zr = ViewZ(S0, uv + dx), zu = ViewZ(S0, uv - dy), zd = ViewZ(S0, uv + dy);
	float3 pl = ViewPos(uv - dx, zl), pr = ViewPos(uv + dx, zr), pu = ViewPos(uv - dy, zu), pd = ViewPos(uv + dy, zd);
	float el = abs(zl - z), er = abs(zr - z), eu = abs(zu - z), ed = abs(zd - z), same = 0.01 * z;
	float3 ax = (zl > 0 && zr > 0 && el < same && er < same) ? (pr - pl) * 0.5 : (el < er ? p - pl : pr - p);
	float3 ay = (zu > 0 && zd > 0 && eu < same && ed < same) ? (pd - pu) * 0.5 : (eu < ed ? p - pu : pd - p);
	float3 n = normalize(cross(ay, ax));
	if (n.z > 0)
		n = -n;                                     // towards the camera
	return float4(z, n.x, n.y, 1);
}
#endif

#if SSAO_PASS == 2
#define SAMPLES 16
#define TURNS 7.0
#define ANGLE_BIAS 0.2    // sine of the lowest rise that counts (about 12 degrees)
// S0 = the depth + normal buffer (point)
float4 AoPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 g = tex2Dlod(S0, float4(uv, 0, 0));
	if (g.w == 0)
		return float4(1, 0, 0, 1);
	float3 p = ViewPos(uv, g.x), n = Normal(g);
	float radius = Fx.y, r2 = radius * radius;
	// the disc's size on screen, in uv (each axis by its own projection scale)
	float2 disc = float2(Proj.x, Proj.y) * (0.5 * radius / g.x);
	if (disc.x * Px.z < 1.5)
		return float4(1, g.x, 0, 1);                // smaller than a texel: far away
	disc = min(disc, 0.15);                         // up close: no huge kernels
	// a different spiral turn per pixel (interleaved gradient noise), smoothed by the blur
	float2 pix = uv * Px.zw;
	float phi = 6.2831853 * frac(52.9829189 * frac(dot(pix, float2(0.06711056, 0.00583715))));
	float bias = 0.02 * radius + 0.002 * g.x;      // depth gets coarser with distance
	float sum = 0;
	for (int i = 0; i < SAMPLES; i++)
	{
		float a = (i + 0.5) / SAMPLES;
		float ang = a * TURNS * 6.2831853 + phi;
		float2 suv = uv + a * disc * float2(cos(ang), sin(ang));
		if (any(suv < 0) || any(suv > 1))
			continue;                               // off screen: unknown, not occluding
		float4 gs = tex2Dlod(S0, float4(suv, 0, 0));
		if (gs.w == 0)
			continue;
		float3 v = ViewPos(suv, gs.x) - p;
		float vv = dot(v, v), d = sqrt(vv);
		// SAO's falloff (1 - d^2/r^2)^3, times how steeply the sample rises over the surface
		// less an angle bias (surfaces seen at a grazing angle don't shade themselves through
		// the depth buffer's steps), times nearness in radii: independent of the world's units
		float f = saturate(1 - vv / r2);
		float rise = (dot(v, n) - bias) / max(d, 0.0001);
		sum += f * f * f * max(rise - ANGLE_BIAS, 0) * radius / (d + 0.15 * radius);
	}
	float ao = max(0, 1 - sum * Fx.z * 3.0 / SAMPLES);
	return float4(ao, g.x, 0, 1);
}
#endif

#if SSAO_PASS == 3
// S0 = the AO (r) with its depth (g), point; Step.xy = one texel along the blur
float4 BlurPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 c = tex2Dlod(S0, float4(uv, 0, 0));
	if (c.g <= 0)
		return c;
	float sum = c.r, wsum = 1;
	for (int i = -4; i <= 4; i++)
	{
		if (i == 0)
			continue;
		float4 s = tex2Dlod(S0, float4(uv + i * Step.xy, 0, 0));
		float w = exp(-i * i / 12.0) * (s.g > 0 ? 1 : 0) * saturate(1 - abs(s.g - c.g) / (0.04 * c.g));
		sum += s.r * w;
		wsum += w;
	}
	return float4(sum / wsum, c.g, 0, 1);
}
#endif

#if SSAO_PASS == 4
// S0 = the scene's depth (full size), S1 = the frame, S2 = the blurred AO (point), S3 = what
// was drawn after a mid-frame depth clear (or none). Step = the AO's 1/w, 1/h, w, h.
float4 ApplyPS(float2 uv : TEXCOORD0) : COLOR
{
	float4 col = tex2Dlod(S1, float4(uv, 0, 0));
	float z = ViewZ(S0, uv);
	float over = tex2Dlod(S3, float4(uv, 0, 0)).r;
	if (z <= 0 || (over > 0 && over < 0.999999))
		return Fx.w > 0.5 ? float4(1, 1, 1, 1) : col;
	// the four nearest AO texels, bilinear weights times how close their depth is to this pixel's
	float2 t = uv * Step.zw - 0.5;
	float2 f = frac(t);
	float2 base = (floor(t) + 0.5) * Step.xy;
	float ao = 0, wsum = 0.0001;
	for (int k = 0; k < 4; k++)
	{
		float2 o = float2(fmod(k, 2), floor(k / 2.0));
		float4 s = tex2Dlod(S2, float4(base + o * Step.xy, 0, 0));
		float wb = (o.x > 0 ? f.x : 1 - f.x) * (o.y > 0 ? f.y : 1 - f.y);
		float w = (wb + 0.001) * (s.g > 0 ? 1 : 0) / (0.001 + abs(s.g - z) / z);
		ao += s.r * w;
		wsum += w;
	}
	ao = wsum > 0.001 ? ao / wsum : 1;
	ao = lerp(1, ao, Fx.x);
	// ambient light is what gets occluded: let bright, directly lit pixels keep more of theirs
	float lum = dot(col.rgb, float3(0.299, 0.587, 0.114));
	ao = lerp(ao, 1, 0.5 * smoothstep(0.6, 1.0, lum));
	if (Fx.w > 0.5)
		return float4(ao, ao, ao, 1);
	return float4(col.rgb * ao, col.a);
}
#endif
