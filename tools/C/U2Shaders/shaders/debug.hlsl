sampler2D Scene : register(s1);
float4    Info  : register(c0);
float4x4  Proj  : register(c4);
float4 main(float2 uv : TEXCOORD0, float3 normal : TEXCOORD1, float3 pos : TEXCOORD2) : COLOR
{
	// red: fixed-function flag; green: depth in 500 units; blue: normal z
	return float4(Info.y, saturate(pos.z / 500.0), normal.z * 0.5 + 0.5, 1);
}
