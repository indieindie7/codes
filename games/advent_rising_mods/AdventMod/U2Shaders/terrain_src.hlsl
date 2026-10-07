// Advent Rising terrain, in place of the engine's PS_Terrain3Layer / PS_Terrain4Layer
// (D3DDrv's ps.1.1/1.4: layers x weight map, x2 vertex lighting). make_terrain.py writes
// terrain3.hlsl and terrain4.hlsl from this file (LAYERS 3 or 4); the U2Shaders layer binds
// them with psreplace= when the game's terrain shader is set. Same inputs as the game's:
// weight map on t0 (RGB = layers 1-3, A = layer 4), the layers on t1.., baked light in v0.
// What it adds (research: research/terrain-beautify-papers-and-code.md):
//   1. height-aware blending (Mishkinis 2013): each layer's brightness is its height, so the
//      layer that is "higher" at a pixel wins where weights are close (sand settles in the
//      cracks of rock instead of a soft cross-fade);
//   2. anti-tiling (Inigo Quilez, "texture repetition" technique 3, CC BY-NC-SA): each layer is
//      read twice with offsets that change slowly over the world, blended, so the repeat
//      pattern disappears;
//   3. large-scale colour variation: a low-frequency world-space noise brightens/darkens
//      wide areas a little;
//   4. height fog (Inigo Quilez, "Better Fog"): thicker low down and far away;
// Inputs from the layer (psreplace): TEXCOORD5 = camera-space position, c1-c3 = inverse view
// rows (camera -> world, translation in .w), c4 = terrainfx= (blend depth, anti-tiling 0/1,
// variation, fog falloff), c5 = terrainfog= (r, g, b, density), c6 = terrainfog2= (fog base
// height in world units, most fog allowed 0..1). All 0 = that part off.

#ifndef LAYERS
#define LAYERS 3
#endif

sampler2D Weights : register(s0);
sampler2D Layer1  : register(s1);
sampler2D Layer2  : register(s2);
sampler2D Layer3  : register(s3);
#if LAYERS > 3
sampler2D Layer4  : register(s4);
#endif
float4 Info    : register(c0);   // seconds
float4 ViewX   : register(c1);   // inverse view, row by row
float4 ViewY   : register(c2);
float4 ViewZ   : register(c3);
float4 Fx      : register(c4);   // blend depth, anti-tiling, variation, fog falloff
float4 Fog     : register(c5);   // fog colour, density
float4 Fog2    : register(c6);   // fog base height, most fog
float4 Fx2     : register(c7);   // terrainfx2= relief strength, relief scale, slope rock, strata

struct In
{
	float4 Light : COLOR0;
	float2 W     : TEXCOORD0;
	float2 U1    : TEXCOORD1;
	float2 U2    : TEXCOORD2;
	float2 U3    : TEXCOORD3;
#if LAYERS > 3
	float2 U4    : TEXCOORD4;
#endif
	float3 Cam   : TEXCOORD5;   // camera-space position
};

float Hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }

// smooth value noise, 0..1
float Noise(float2 p)
{
	float2 i = floor(p), f = frac(p);
	f = f * f * (3 - 2 * f);
	return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), f.x), f.y);
}

// IQ technique 3: two reads at offsets picked by a slow noise value, blended so the seam
// between offsets is invisible; gradients from the plain coordinate keep the mip level right
float4 NoTile(sampler2D s, float2 uv, float k)
{
	float2 dx = ddx(uv), dy = ddy(uv);
	float l = k * 8;
	float i = floor(l), f = frac(l);
	float2 o1 = sin(float2(3, 7) * i);
	float2 o2 = sin(float2(3, 7) * (i + 1));
	float4 a = tex2Dgrad(s, uv + o1, dx, dy);
	float4 b = tex2Dgrad(s, uv + o2, dx, dy);
	float4 m = a - b;
	return lerp(a, b, smoothstep(0.2, 0.8, f - 0.1 * (m.r + m.g + m.b)));
}

float4 main(In I) : COLOR
{
	float3 world = float3(dot(ViewX, float4(I.Cam, 1)), dot(ViewY, float4(I.Cam, 1)), dot(ViewZ, float4(I.Cam, 1)));
	float k = Fx.y > 0 ? Noise(world.xy / 700.0) : 0;
	float4 w = tex2D(Weights, I.W);

	float4 t1 = Fx.y > 0 ? NoTile(Layer1, I.U1, k) : tex2D(Layer1, I.U1);
	float4 t2 = Fx.y > 0 ? NoTile(Layer2, I.U2, k) : tex2D(Layer2, I.U2);
	float4 t3 = tex2D(Layer3, I.U3);
#if LAYERS > 3
	float4 t4 = tex2D(Layer4, I.U4);
#endif

	float4 c;
	if (Fx.x > 0)
	{
		// 1: height blend; heights = brightness + weight, only what is within Fx.x of the top counts
		float3 lum = float3(0.3, 0.59, 0.11);
		float h1 = dot(t1.rgb, lum) + w.r, h2 = dot(t2.rgb, lum) + w.g, h3 = dot(t3.rgb, lum) + w.b;
		float top = max(h1, max(h2, h3));
#if LAYERS > 3
		float h4 = dot(t4.rgb, lum) + w.a;
		top = max(top, h4);
#endif
		top -= Fx.x;
		float b1 = max(h1 - top, 0) * (w.r > 0.004), b2 = max(h2 - top, 0) * (w.g > 0.004), b3 = max(h3 - top, 0) * (w.b > 0.004);
		float sum = b1 + b2 + b3;
		c = t1 * b1 + t2 * b2 + t3 * b3;
#if LAYERS > 3
		float b4 = max(h4 - top, 0) * (w.a > 0.004);
		sum += b4;
		c += t4 * b4;
#endif
		// keep the overall weight the game gave (weights may not add up to 1 where extra
		// layers are added on top in later passes)
		float total = w.r + w.g + w.b;
#if LAYERS > 3
		total += w.a;
#endif
		c *= total / max(sum, 0.0001);
	}
	else
	{
		c = t1 * w.r + t2 * w.g + t3 * w.b;
#if LAYERS > 3
		c += t4 * w.a;
#endif
	}

	// 3: wide colour variation (very low frequency, about +-Fx.z)
	if (Fx.z > 0)
		c.rgb *= 1 + Fx.z * (Noise(world.xy / 3000.0) * 2 - 1);

	// 5: the ground's shape, which the flat vertex lighting hides (terrainfx2=):
	//    x relief: the first layer's own brightness read as a height map from a coarse mip (bumps
	//      metres wide, not texels), lit by a fixed low sun, so hollows darken and brows catch light;
	//    y relief scale: the sample spread in texture units x 0.001 (4 = wide, soft bumps);
	//    z slope rock: steep ground (from the screen-space slope of the world position) turns to
	//      darker, greyer bare rock with scree at its foot instead of the same grass or dust;
	//    w strata: faint horizontal rock bands (world height) on that steep ground, canyon-style
	if (Fx2.x > 0 || Fx2.z > 0)
	{
		float3 n = normalize(cross(ddx(world), ddy(world)));
		n = n.z < 0 ? -n : n;
		float3 lum3 = float3(0.3, 0.59, 0.11);
		if (Fx2.x > 0)
		{
			// two spreads: a wide one from a very coarse mip (the swells, metres across) and a
			// narrow one (stones and ruts); one spread alone read as fine gravel everywhere
			float e = max(Fx2.y, 0.5) * 0.001;
			float4 uc = float4(I.U1, 0, 4.5), uf = float4(I.U1, 0, 2.0);
			float ec = e * 6;
			float hx = 0.7 * (dot(tex2Dbias(Layer1, uc + float4(ec, 0, 0, 0)).rgb, lum3) - dot(tex2Dbias(Layer1, uc - float4(ec, 0, 0, 0)).rgb, lum3))
			         + 0.3 * (dot(tex2Dbias(Layer1, uf + float4(e, 0, 0, 0)).rgb, lum3) - dot(tex2Dbias(Layer1, uf - float4(e, 0, 0, 0)).rgb, lum3));
			float hy = 0.7 * (dot(tex2Dbias(Layer1, uc + float4(0, ec, 0, 0)).rgb, lum3) - dot(tex2Dbias(Layer1, uc - float4(0, ec, 0, 0)).rgb, lum3))
			         + 0.3 * (dot(tex2Dbias(Layer1, uf + float4(0, e, 0, 0)).rgb, lum3) - dot(tex2Dbias(Layer1, uf - float4(0, e, 0, 0)).rgb, lum3));
			float3 nt = normalize(float3(-hx * Fx2.x * 5, -hy * Fx2.x * 5, 1));
			float3 L = normalize(float3(-0.55, -0.4, 0.73));
			c.rgb *= saturate(1 + (dot(nt, L) - L.z) * 1.6);
		}
		if (Fx2.z > 0)
		{
			float steep = saturate((1 - n.z - 0.22) / 0.28) * Fx2.z;   // 0 under ~26 deg, full over ~44
			float l = dot(c.rgb, lum3);
			float3 rock = lerp(c.rgb, l * float3(0.66, 0.62, 0.56), 0.75);
			if (Fx2.w > 0)
			{
				float band = 0.5 + 0.5 * sin(world.z / 26.0 + 2.5 * Noise(world.xy / 300.0));
				rock *= 1 + Fx2.w * 0.35 * (band - 0.5);
			}
			// scree: a lighter, dustier band where the steep face meets gentler ground
			float foot = saturate((n.z - 0.6) / 0.15) * saturate((0.85 - n.z) / 0.1);
			rock = lerp(rock, c.rgb * 1.08, foot * 0.5);
			c.rgb = lerp(c.rgb, rock, steep);
		}
	}

	c *= I.Light * 2;   // the game's lighting, as before

	// 4: height fog along the view ray (IQ "Better Fog"), world z up
	if (Fog.w > 0)
	{
		float3 eye = float3(ViewX.w, ViewY.w, ViewZ.w);
		float3 ray = world - eye;
		float dist = length(ray);
		float rz = ray.z / max(dist, 1);
		float b = max(Fx.w, 0.00001);
		float h = clamp(eye.z - Fog2.x, -2000, 20000);   // camera height above the fog base
		float rzs = abs(rz) > 0.0001 ? rz : 0.0001;
		float amount = Fog.w / b * exp(-h * b) * (1 - exp(-dist * rzs * b)) / rzs;
		c.rgb = lerp(c.rgb, Fog.rgb, min(saturate(amount), Fog2.y > 0 ? Fog2.y : 1));
	}
	return c;
}
