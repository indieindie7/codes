Shader "Sprites/enemy" {
	Properties{
		_MainTex("Albedo (RGB)", 2D) = "white" {}
	//_alphaTex("ALPHA (A)", 2D) = "white" {}
	_RampTex("TAM (RGB)", 2D) = "white" {}

		_xc("Alpha Cutoff",Range(0.01,0.4)) = 2
		_pos("display name", Int) = 0
		//_Metallic("Metallic", Range(0,1)) = 0.0
	}
		SubShader{
		Tags{ "RenderType" = "Opaque" }
		LOD 200

		CGPROGRAM
		// Physically based Standard lighting model, and enable shadows on all light types
//#pragma fragment frag 
#pragma surface surf Standard fullforwardshadows alphatest:_Cutoff//  // vertex:vert fragment:frag
//#include "UnityCG.cginc"
//#pragma alphatest _Cutoff
//
//#pragma multi_compile _ PIXELSNAP_ON
//#pragma multi_compile _ ETC1_EXTERNAL_ALPHA

		// Use shader model 3.0 target, to get nicer looking lighting
//#pragma target 3.0

		sampler2D _MainTex;
		//sampler2D _alphaTex;
		sampler2D _RampTex;
	struct Input {
		float2 uv_MainTex;
	};
	half _xc;
	int _pos;

	// Add instancing support for this shader. You need to check 'Enable Instancing' on materials that use the shader.
	// See https://docs.unity3d.com/Manual/GPUInstancing.html for more information about instancing.
	// #pragma instancing_options assumeuniformscaling
	UNITY_INSTANCING_CBUFFER_START(Props)

		// put more per-instance properties here
		UNITY_INSTANCING_CBUFFER_END

		void surf(Input IN, inout SurfaceOutputStandard o) {
		//if (_pos > 0) {
			float xV = IN.uv_MainTex.x;
			float cellPixelWidth = 240 / 5;
			float cellPixelHeight = 192 / 4;
			float2 cellUVPercentage = float2(cellPixelWidth / 240,cellPixelHeight / 192);
			float posx = _pos % 5;
			float posy = _pos / 5;
			float xValue = 1- IN.uv_MainTex.x;
		
			xValue += cellUVPercentage.x * posx * 5;
			xValue *= cellUVPercentage.x;
			//xValue =  xValue;
			float yValue = IN.uv_MainTex.y;
			yValue += cellUVPercentage.y * posy * 4;
			yValue *= cellUVPercentage.y;
			yValue = 192 - yValue;
		float2	spriteUV = float2(xValue, yValue);

			half4 c = tex2D(_MainTex, spriteUV);
		//	half4 d = tex2D(_alphaTex, spriteUV); 
			o.Albedo = c.rgb;
			o.Alpha = c.a;// *_xc;
		
		o.Emission = c.rgb;
			//float cellPixelWidth = textureSize(_MainTex, 0).x / 4;
		//	float cellUVPercentage = cellPixelWidth / textureSize(_MainTex, 0).x;
		//}
		//else {
		//	// Albedo comes from a texture tinted by color
		//	fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
		//	o.Albedo = c.rgb;
		//	// Metallic and smoothness come from slider variables
			//o.Metallic = 1;// _Metallic;
			//o.Smoothness = 1;// _Glossiness;
		//	o.Alpha = c.a*(_xc);
		//}
	}
	ENDCG
	}
		FallBack "Diffuse"
}
