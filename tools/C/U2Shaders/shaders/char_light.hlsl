// Characters (and every other lit solid draw: weapons, pickups) lit per pixel instead of per
// vertex, from the same D3D lights the game set, with the character tricks from Valve's
// "Shading in Valve's Source Engine" (SIGGRAPH 2006):
//   - wrapped ("half-Lambert") diffuse: the side away from a light falls off gradually
//     instead of going flat black at the terminator, so the body's shape still reads there
//   - hemisphere ambient: lighter from above than from below (a cheap ambient cube)
//   - a faint rim along the silhouette, in the colour of the light reaching it
// Used with charlight=1 (see CharBegin in u2shaders.hpp for the constants).

sampler2D Tex     : register(s0);
sampler2D Second  : register(s1);   // stage 1's texture, when stage 1 uses one
float4    Info    : register(c0);   // time, 1, -, -
float4    Setup   : register(c2);   // x: stage 0 factor (1, 2, 4), y: number of lights (0-4),
                                    // z: stage 1 (0 nothing, 1 x texture, 2 + alpha x texture), w: its factor
float4    Ambient : register(c3);   // rgb: ambient x material ambient + emissive
float4    Up      : register(c4);   // xyz: world up, in view space
float4    Use     : register(c5);   // x: 1 = stage 0 multiplies by its texture, 0 = lit colour alone
float4    Lights[16] : register(c8);  // 4 per light, see CharBegin

#define WRAP 0.5      // 0 = Lambert, as the game; 1 = full half-Lambert (Valve)
#define HEMI 0.4      // how much darker the ambient is from below (0 = flat ambient)
#define RIM 0.25      // rim strength (0 = off)

float4 main(float2 uv : TEXCOORD0, float2 uv1 : TEXCOORD1, float3 normal : TEXCOORD2, float3 pos : TEXCOORD3) : COLOR
{
	float3 n = normalize(normal);
	float3 v = normalize(-pos);
	n = dot(n, v) < -0.2 ? -n : n;           // back faces of two-sided parts face the camera

	float3 direct = 0, reach = 0;
	for (int i = 0; i < 4; i++)
	{
		float4 P = Lights[i * 4], D = Lights[i * 4 + 1], C = Lights[i * 4 + 2], A = Lights[i * 4 + 3];
		float3 toL = P.w > 2.5 ? -D.xyz : P.xyz - pos;
		float d = length(toL);
		float3 l = toL / max(d, 0.0001);
		float att = P.w > 2.5 ? 1 : (d < C.w ? 1 / max(A.x + A.y * d + A.z * d * d, 0.0001) : 0);
		if (P.w > 1.5 && P.w < 2.5)            // spot: full inside theta, none outside phi
			att *= saturate((dot(-l, D.xyz) - D.w) / max(A.w - D.w, 0.0001));
		att *= i < Setup.y;
		float ndl = dot(n, l);
		float h = ndl * 0.5 + 0.5;
		direct += C.rgb * att * lerp(saturate(ndl), h * h, WRAP);
		reach += C.rgb * att;
	}

	float sky = dot(n, Up.xyz) * 0.5 + 0.5;
	float3 ambient = Ambient.rgb * lerp(1 - HEMI, 1, sky);
	float rim = pow(1 - saturate(dot(n, v)), 3) * RIM;

	float3 lit = saturate(ambient + direct + reach * rim);   // the fixed-function clamp
	float4 t = Use.x > 0.5 ? tex2D(Tex, uv) : float4(1, 1, 1, 1);
	float4 c = float4(saturate(t.rgb * lit * Setup.x), t.a);

	// stage 1, as the game set it
	float4 t1 = tex2D(Second, uv1);
	if (Setup.z > 1.5)
		c.rgb = saturate(c.rgb + c.a * t1.rgb);              // MODULATEALPHA_ADDCOLOR
	else if (Setup.z > 0.5)
		c.rgb = saturate(c.rgb * t1.rgb * Setup.w);          // MODULATE (x2, x4)
	return c;
}
