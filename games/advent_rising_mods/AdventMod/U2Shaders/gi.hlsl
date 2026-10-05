// gi.hlsl - screen-space global illumination by radiance cascades (gi=1), compiled by the
// wrapper as ps_3_0/vs_3_0 with GI_PASS set:
//   1 GBufPS     depth -> view depth + normal, half size
//   2 CascadePS  one cascade: for each probe and direction, what the screen shows along
//                that direction over the cascade's stretch of pixels, merged with the next
//                (farther, finer in angle) cascade
//   3 GatherPS   the nearest cascade gathered per pixel
//   4 CachePS    the world cache brought up to date from this frame
//   5 ResolvePS  the gathered light smoothed along surfaces: bounce light added, corners darkened
//
// The world cache (gicache=1) is what the screen can't give: a coarse grid of cells around
// the camera (64 x 64 x 32, slices side by side in one texture) that remembers the light
// seen on the surfaces in each cell over the last frames. A cell on screen takes the
// frame's colour where the depth buffer says a surface is in it, empties where it is seen
// to be air, and keeps what it had while hidden or off screen. The farthest cascade ends
// its directions in the cache, so light from behind the camera or behind a pillar still
// arrives, for as long as the cache remembers it.
//
// Radiance cascades (Sannikov, Path of Exile 2): light from near needs many probes but few
// directions, light from far few probes but many directions. Cascade c has probes every
// 2^(c+1) of its texels and 4^(c+1) directions, and covers a stretch 4x as long as the
// one before. Each cascade is one texture (the frame's size over gires): k x k tiles
// (k = 2^(c+1)), one per direction, each a small picture of the screen's probes, so the
// probes of a direction interpolate with plain bilinear filtering.
//
// What one direction stores (here: a horizon version, as there is only the screen to trace):
// rgb = light arriving from it, summed over bands of elevation over the surface, each band
// lit by the nearest thing that rises into it; a = the highest elevation reached (its sine).
// Merging adds the farther cascade's light for the part of the sky still open above that.

float4 Px : register(c0);       // the target's 1/w, 1/h, w, h
float4 Proj : register(c1);     // the scene projection's _11, _22, _33, _43
float4 Casc : register(c2);     // tiles per axis k, stretch start (pixels), stretch length, 1 = merge the next cascade
                                // (the resolve: 0, 0, the cascade texture's w, h)
float4 Scr : register(c3);      // the frame's 1/w, 1/h, w, h
float4 Fx : register(c4);       // bounce strength, corner darkening, reach (world units), debug view
float4 Mat0 : register(c5);     // a matrix's columns (row vectors: x' = dot(float4(p, 1), Mat0)): the
float4 Mat1 : register(c6);     // camera's inverse view in the cascade and resolve passes, its view in
float4 Mat2 : register(c7);     // the cache pass
float4 Grid : register(c8);     // the cache's lowest corner (world), its cell size
float4 GridOld : register(c9);  // last frame's corner, 1 = the cache is on

static const float3 GridN = float3(64, 64, 32);
static const float2 GridTiles = float2(8, 4);

float3 Xform(float3 p)
{
	float4 q = float4(p, 1);
	return float3(dot(q, Mat0), dot(q, Mat1), dot(q, Mat2));
}

float3 Rotate(float3 v)
{
	return float3(dot(v, Mat0.xyz), dot(v, Mat1.xyz), dot(v, Mat2.xyz));
}

// the cache at a world position (s = its sampler), between the two nearest slices
float4 CacheAt(sampler s, float3 world, float3 corner)
{
	float3 g = (world - corner) / Grid.w;
	if (any(g < 0.5) || any(g > GridN - 0.5))
		return 0;
	float2 inTile = clamp(g.xy / GridN.xy, 0.5 / GridN.xy, 1 - 0.5 / GridN.xy);
	float z = g.z - 0.5, z0 = floor(z);
	float2 t0 = float2(fmod(z0, GridTiles.x), floor(z0 / GridTiles.x));
	float2 t1 = float2(fmod(z0 + 1, GridTiles.x), floor((z0 + 1) / GridTiles.x));
	return lerp(tex2Dlod(s, float4((t0 + inTile) / GridTiles, 0, 0)), tex2Dlod(s, float4((t1 + inTile) / GridTiles, 0, 0)), z - z0);
}

sampler S0 : register(s0);
sampler S1 : register(s1);
sampler S2 : register(s2);

void GiVS(float4 p : POSITION, float2 uv : TEXCOORD0, out float4 op : POSITION, out float2 ouv : TEXCOORD0)
{
	op = float4(p.x - Px.x, p.y + Px.y, p.z, 1);
	ouv = uv;
}

float3 ViewPos(float2 uv, float z)
{
	return float3((2 * uv.x - 1) * z / Proj.x, (1 - 2 * uv.y) * z / Proj.y, z);
}

#if GI_PASS == 1
// S0 = the scene's depth buffer
float ViewZ(float2 uv)
{
	float d = tex2Dlod(S0, float4(uv, 0, 0)).r;
	return d >= 0.999999 ? 0 : Proj.w / (d - Proj.z);
}

float4 GBufPS(float2 uv : TEXCOORD0) : COLOR
{
	float z = ViewZ(uv);
	// S1 (when set): the depth of what the game drew after clearing the world's (a first-person
	// weapon, in its own projection). What it covers is left alone.
	float over = tex2Dlod(S1, float4(uv, 0, 0)).r;
	if (z <= 0 || (over > 0 && over < 0.999999))
		return float4(0, 0, 0, 0);                  // sky
	float3 p = ViewPos(uv, z);
	// the normal from the nearer neighbour on each axis (so edges don't bend it)
	float2 dx = float2(Scr.x, 0), dy = float2(0, Scr.y);
	float zl = ViewZ(uv - dx), zr = ViewZ(uv + dx), zu = ViewZ(uv - dy), zd = ViewZ(uv + dy);
	// both neighbours where the surface carries on (steadier: far depth comes in coarse steps)
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

float3 Normal(float4 g)
{
	return float3(g.y, g.z, -sqrt(saturate(1 - g.y * g.y - g.z * g.z)));
}

#if GI_PASS == 2
// S0 = depth + normal, S1 = the frame, S2 = the next cascade (the farthest: the world cache)
float4 CascadePS(float2 uv : TEXCOORD0) : COLOR
{
	float k = Casc.x, n = k * k;
	float2 tile = floor(uv * k);
	float dirIndex = tile.y * k + tile.x;
	// the probe's place on the screen, kept half a texel inside its tile
	float2 tileSize = Px.zw / k;
	float2 puv = clamp(frac(uv * k), 0.5 / tileSize, 1 - 0.5 / tileSize);
	float4 g = tex2Dlod(S0, float4(puv, 0, 0));
	if (g.a < 0.5)
		return float4(0, 0, 0, 0);
	float3 p0 = ViewPos(puv, g.x), n0 = Normal(g);
	float angle = 6.2831853 * (dirIndex + 0.5) / n;
	float2 dir = float2(cos(angle), sin(angle)) * Scr.xy;

	// each probe steps along its directions from its own offset: the steps' regular
	// pattern (stripes and hatching on slopes and round things) becomes fine grain, which
	// the resolve smooths away
	float2 probe = floor(frac(uv * k) * tileSize);
	float jitter = frac(52.9829189 * frac(dot(probe, float2(0.06711056, 0.00583715))));
	float h = 0;
	float3 light = 0;
	for (int i = 0; i < 8; i++)
	{
		float t = Casc.y + Casc.z * (i + jitter) / 8;
		float2 suv = puv + dir * t;
		if (suv.x < 0 || suv.x > 1 || suv.y < 0 || suv.y > 1)
			break;
		float4 gs = tex2Dlod(S0, float4(suv, 0, 0));
		if (gs.a < 0.5)
			continue;
		float3 v = ViewPos(suv, gs.x) - p0;
		float dist = length(v);
		// how high it stands over the surface; things beyond the reach fade out (on a
		// screen, something far in front of the surface would else pass for a wall next to it)
		// (a little under the horizon doesn't count: sloped surfaces would else shade
		// themselves in stripes, from the depth buffer's steps)
		float s = saturate((dot(v, n0) / max(dist, 0.001) - 0.1) / 0.9);
		float near = saturate(1 - dist * dist / (Fx.z * Fx.z));
		s = lerp(h, s, near);
		if (s > h)
		{
			// the frame is gamma-space: light adds up in linear
			light += pow(max(tex2Dlod(S1, float4(suv, 0, 0)).rgb, 0), 2.2) * (s * s - h * h);
			h = s;
		}
	}
	if (Casc.w > 0.5)
	{
		// the four finer directions of the next cascade that this one spans
		float ku = k * 2;
		float2 tileSizeU = Px.zw / ku;
		float2 puvU = clamp(puv, 0.5 / tileSizeU, 1 - 0.5 / tileSizeU);
		float4 up = 0;
		for (int j = 0; j < 4; j++)
		{
			float iu = dirIndex * 4 + j;
			float ty = floor((iu + 0.5) / ku);
			float tx = iu - ty * ku;
			up += tex2Dlod(S2, float4((float2(tx, ty) + puvU) / ku, 0, 0));
		}
		up *= 0.25;
		// the farther light fills what is still open above this stretch's horizon
		light += up.rgb * (1 - h * h);
		h = max(h, up.a);
	}
	else if (GridOld.w > 0.5)
	{
		// the farthest cascade: what is still open ends in the world cache, a few steps out
		// along the middle of the open part of this direction's slice of the sky
		float3 d3 = float3(cos(angle), -sin(angle), 0);
		float3 tangent = normalize(d3 - n0 * dot(d3, n0));
		float sinE = 0.5 * (h + 1), cosE = sqrt(1 - sinE * sinE);
		float3 dirW = Rotate(tangent * cosE + n0 * sinE);
		float3 p0W = Xform(p0);
		float3 far = 0;
		float cover = 0;
		for (int m = 0; m < 5; m++)
		{
			float4 cell = CacheAt(S2, p0W + dirW * Grid.w * (1.5 + 1.75 * m * (1 + 0.5 * m)), Grid.xyz);
			far += (1 - cover) * cell.rgb;
			cover += (1 - cover) * cell.a;
		}
		light += far * (1 - h * h);
	}
	return float4(light, h);
}
#endif

#if GI_PASS == 3
// S2 = the nearest cascade (2 x 2 directions): gathered per pixel, rgb the light, a the
// part of the sky closed off
float4 GatherPS(float2 uv : TEXCOORD0) : COLOR
{
	float2 tileSize = Casc.zw * 0.5;                // the cascade texture's size, 2 tiles per axis
	float2 puv = clamp(uv, 0.5 / tileSize, 1 - 0.5 / tileSize);
	float4 sum = 0;
	float closed = 0;
	for (int j = 0; j < 4; j++)
	{
		float2 t = float2(j % 2, j / 2);
		float4 r = tex2Dlod(S2, float4((t + puv) * 0.5, 0, 0));
		sum += r;
		closed += r.a * r.a;
	}
	return float4(sum.rgb * 0.25, closed * 0.25);
}
#endif

#if GI_PASS == 5
// S0 = depth + normal, S1 = the frame, S2 = the gathered light (debug view 5: the world cache)
float4 ResolvePS(float2 uv : TEXCOORD0) : COLOR
{
	float4 c = tex2D(S1, uv);
	float4 g = tex2Dlod(S0, float4(uv, 0, 0));
	if (g.a < 0.5)
		return c;
	if (Fx.w > 4.5)
	{
		// 5: the world cache where this pixel's surface is
		float4 cell = CacheAt(S2, Xform(ViewPos(uv, g.x)), Grid.xyz);
		return float4(pow(max(cell.rgb, 0), 1 / 2.2), 1);
	}
	// the gathered light smoothed over the pixels around that lie on the same surface (the
	// cascades' probes are jittered: this turns their grain into an even result, and keeps
	// it from spreading over edges)
	float3 n = Normal(g);
	float4 sum = 0;
	float wsum = 0;
	for (int y = -2; y <= 2; y++)
		for (int x = -2; x <= 2; x++)
		{
			float2 o = uv + float2(x, y) * 2 * Scr.xy;
			float4 gs = tex2Dlod(S0, float4(o, 0, 0));
			float w = gs.a * saturate(1 - abs(gs.x - g.x) / (0.03 * g.x)) * pow(saturate(dot(Normal(gs), n)), 8) + 0.0001;
			sum += tex2Dlod(S2, float4(o, 0, 0)) * w;
			wsum += w;
		}
	sum /= wsum;
	float3 light = sum.rgb;
	float shade = 1 - Fx.y * sum.a;
	// the surface's own colour, guessed from the lit frame: its hue, not its brightness
	float3 hue = c.rgb / (max(c.r, max(c.g, c.b)) + 0.08);
	if (Fx.w > 3.5)
		return float4(frac(g.x / 500), 0, 0, 1);    // 4: depth, in bands of 500 units
	if (Fx.w > 2.5)
		return float4(n * 0.5 + 0.5, 1);            // 3: normals
	if (Fx.w > 1.5)
		return float4(shade, shade, shade, 1);      // 2: the corner darkening alone
	if (Fx.w > 0.5)
		return float4(pow(max(light, 0), 1 / 2.2), 1);      // 1: the gathered light alone
	float3 lit = pow(max(c.rgb, 0), 2.2) * shade + pow(max(hue, 0), 2.2) * light * Fx.x;
	return float4(pow(max(lit, 0), 1 / 2.2), c.a);
}
#endif

#if GI_PASS == 4
// S0 = depth + normal, S1 = the frame, S2 = the cache as it was
float4 CachePS(float2 uv : TEXCOORD0) : COLOR
{
	// this texel's cell, and where its middle is in the world
	float2 t = uv * GridTiles;
	float2 tile = floor(t);
	float3 cellIndex = float3(floor(frac(t) * GridN.xy), tile.y * GridTiles.x + tile.x);
	float3 world = Grid.xyz + (cellIndex + 0.5) * Grid.w;
	// what it remembered (the grid may have stepped since)
	float3 go = (world - GridOld.xyz) / Grid.w;
	float4 old = 0;
	if (all(go > 0) && all(go < GridN))
	{
		float3 ci = floor(go);
		old = tex2Dlod(S2, float4((float2(fmod(ci.z, GridTiles.x), floor(ci.z / GridTiles.x)) + (ci.xy + 0.5) / GridN.xy) / GridTiles, 0, 0));
	}
	float3 v = Xform(world);
	if (v.z > 4)
	{
		float2 suv = float2(0.5 + 0.5 * v.x * Proj.x / v.z, 0.5 - 0.5 * v.y * Proj.y / v.z);
		if (suv.x > 0 && suv.x < 1 && suv.y > 0 && suv.y < 1)
		{
			float4 g = tex2Dlod(S0, float4(suv, 0, 0));
			float dz = g.a < 0.5 ? -1e6 : v.z - g.x;
			if (abs(dz) < Grid.w * 0.75)
				return lerp(old, float4(pow(max(tex2Dlod(S1, float4(suv, 0, 0)).rgb, 0), 2.2), 1), 0.12);
			if (dz < 0)
				return old * 0.85;              // seen to be air
		}
	}
	return old * 0.999;                         // hidden or off screen: remembered
}
#endif
