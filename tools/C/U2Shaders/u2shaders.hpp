/**
 * U2Shaders - replace the fixed-function look of chosen surfaces with HLSL pixel shaders.
 *
 * A surface is chosen by the texture bound to stage 0 when it is drawn (a hash of the top
 * mip level). Settings come from U2Shaders.ini next to the game executable:
 *
 *     log=1                       list alpha-blended textures in U2Shaders.log and
 *                                 save each one to U2Shaders\dump\<hash>_<w>x<h>.dds
 *     tint=1a2b3c4d               draw everything using that texture in flat magenta
 *     shader=1a2b3c4d core.hlsl   draw it with U2Shaders\core.hlsl (entry "main", ps_2_a)
 *
 * What a shader gets:
 *     s0            the original texture, TEXCOORD0 = its (possibly panned) coordinates
 *     s1            a copy of the frame so far (for refraction)
 *     TEXCOORD1     camera-space normal      (only on fixed-function draws, see c0.y)
 *     TEXCOORD2     camera-space position
 *     COLOR0        the vertex lighting
 *     c0            (time in seconds, 1 if normals/positions are valid, 1/width, 1/height)
 *     c4..c7        the projection matrix (rows), to turn a position into a screen place
 *
 * While a shader draws, alpha blending is off: the shader has the frame behind it in s1
 * and returns the finished colour.
 */

#pragma once

#include <d3dcompiler.h>
#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#pragma comment(lib, "d3dcompiler.lib")

struct U2TexInfo
{
	UINT W = 0, H = 0;
	D3DFORMAT Fmt = D3DFMT_UNKNOWN;
	unsigned Draws = 0;
};

struct U2Rule
{
	DWORD Hash = 0;
	std::string File;          // empty = the built-in tint
	IDirect3DPixelShader9 *PS = nullptr;
	bool Tried = false;
};

class U2Shaders
{
public:
	bool Loaded = false, Log = false;
	std::string Dir;           // "<exe dir>\"
	std::map<DWORD, U2TexInfo> Seen;
	std::vector<U2Rule> Rules;
	unsigned Frame = 0, SceneFrame = ~0u, LogFrame = 0;

	IDirect3DTexture9 *SceneTex = nullptr;
	UINT SceneW = 0, SceneH = 0;
	D3DFORMAT SceneFmt = D3DFMT_UNKNOWN;

	// state put back after a shader draw
	IDirect3DPixelShader9 *OldPS = nullptr;
	IDirect3DBaseTexture9 *OldTex1 = nullptr;
	DWORD OldTCI[3] = {}, OldTTF[3] = {}, OldBlend = 0, OldSamp1[5] = {};
	D3DMATRIX OldTexMat[3] = {};
	float OldConst[8][4] = {};

	void Message(const char *Format, ...)
	{
		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + "U2Shaders.log").c_str(), "a") || F == nullptr)
			return;
		va_list Args;
		va_start(Args, Format);
		vfprintf(F, Format, Args);
		va_end(Args);
		fputc('\n', F);
		fclose(F);
	}

	void Load()
	{
		Loaded = true;

		char Path[MAX_PATH] = {};
		GetModuleFileNameA(nullptr, Path, MAX_PATH);
		Dir = Path;
		Dir.erase(Dir.find_last_of("\\/") + 1);
		DeleteFileA((Dir + "U2Shaders.log").c_str());

		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + "U2Shaders.ini").c_str(), "r") || F == nullptr)
			return;
		char Line[512];
		while (fgets(Line, sizeof(Line), F))
		{
			char Name[256] = {};
			unsigned Hash = 0;
			if (sscanf_s(Line, " log=%u", &Hash) == 1)
				Log = Hash != 0;
			else if (sscanf_s(Line, " pcss=%u", &Hash) == 1)
			{
				Pcss = Hash != 0;
				MapRule.File = "pcss_map.hlsl";
				ProjRule.File = "pcss_proj.hlsl";
			}
			else if (sscanf_s(Line, " pcssparams=%f %f %f %f", &PcssParams[0], &PcssParams[1], &PcssParams[2], &PcssParams[3]) == 4)
				;
			else if (sscanf_s(Line, " pcssdebug=%f", &PcssDebug) == 1)
				;
			else if (sscanf_s(Line, " tint=%x", &Hash) == 1)
			{
				U2Rule R;
				R.Hash = Hash;
				Rules.push_back(R);
			}
			else if (sscanf_s(Line, " shader=%x %255s", &Hash, Name, (unsigned)sizeof(Name)) == 2)
			{
				U2Rule R;
				R.Hash = Hash;
				R.File = Name;
				Rules.push_back(R);
			}
		}
		fclose(F);
		Message("U2Shaders: log %d, %u rule(s), pcss %d (%g %g %g %g)", (int)Log, (unsigned)Rules.size(), (int)Pcss,
			PcssParams[0], PcssParams[1], PcssParams[2], PcssParams[3]);
		if (Log)
		{
			CreateDirectoryA((Dir + "U2Shaders").c_str(), nullptr);
			CreateDirectoryA((Dir + "U2Shaders\\dump").c_str(), nullptr);
		}
	}

	static UINT LevelBytes(const D3DSURFACE_DESC &Desc, INT Pitch)
	{
		switch (Desc.Format)
		{
		case D3DFMT_DXT1:
			return (std::max)(1u, Desc.Width / 4) * (std::max)(1u, Desc.Height / 4) * 8;
		case D3DFMT_DXT2: case D3DFMT_DXT3: case D3DFMT_DXT4: case D3DFMT_DXT5:
			return (std::max)(1u, Desc.Width / 4) * (std::max)(1u, Desc.Height / 4) * 16;
		default:
			return (UINT)Pitch * Desc.Height;
		}
	}

	// hash of the top mip (0 = could not be read); with Dump, also saved as a .dds
	DWORD Hash(IDirect3DTexture9 *Tex, U2TexInfo &Info, bool Dump)
	{
		D3DSURFACE_DESC Desc;
		D3DLOCKED_RECT Lock;
		if (FAILED(Tex->GetLevelDesc(0, &Desc)) || FAILED(Tex->LockRect(0, &Lock, nullptr, D3DLOCK_READONLY)))
			return 0;
		const UINT Bytes = LevelBytes(Desc, Lock.Pitch);
		DWORD H = 2166136261u ^ Desc.Width ^ (Desc.Height << 12);
		const BYTE *P = static_cast<const BYTE *>(Lock.pBits);
		for (UINT i = 0, n = (std::min)(Bytes, 16384u); i < n; i++)
			H = (H ^ P[i]) * 16777619u;
		if (H == 0)
			H = 1;
		Info.W = Desc.Width; Info.H = Desc.Height; Info.Fmt = Desc.Format;
		if (Dump)
			SaveDDS(H, Desc, P, Bytes, Lock.Pitch);
		Tex->UnlockRect(0);
		return H;
	}

	void SaveDDS(DWORD H, const D3DSURFACE_DESC &Desc, const BYTE *Bits, UINT Bytes, INT Pitch)
	{
		DWORD Header[32] = {};
		Header[0] = 0x20534444;            // "DDS "
		Header[1] = 124;
		Header[2] = 0x1007;                // caps | height | width | pixelformat
		Header[3] = Desc.Height;
		Header[4] = Desc.Width;
		Header[19] = 32;                   // pixel format size
		const bool Compressed = Desc.Format == D3DFMT_DXT1 || (Desc.Format >= D3DFMT_DXT2 && Desc.Format <= D3DFMT_DXT5 && (Desc.Format & 0xFF) == 'D');
		if (Compressed)
		{
			Header[2] |= 0x80000;          // linear size
			Header[5] = Bytes;
			Header[20] = 0x4;              // fourcc
			Header[21] = Desc.Format;
		}
		else if (Desc.Format == D3DFMT_A8R8G8B8 || Desc.Format == D3DFMT_X8R8G8B8)
		{
			Header[2] |= 0x8;              // pitch
			Header[5] = Pitch;
			Header[20] = Desc.Format == D3DFMT_A8R8G8B8 ? 0x41 : 0x40;
			Header[22] = 32;
			Header[23] = 0xFF0000; Header[24] = 0xFF00; Header[25] = 0xFF;
			Header[26] = Desc.Format == D3DFMT_A8R8G8B8 ? 0xFF000000 : 0;
		}
		else
			return;
		Header[27] = 0x1000;               // texture

		char Name[64];
		sprintf_s(Name, "U2Shaders\\dump\\%08x_%ux%u.dds", H, Desc.Width, Desc.Height);
		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + Name).c_str(), "wb") || F == nullptr)
			return;
		fwrite(Header, 4, 32, F);
		fwrite(Bits, 1, Bytes, F);
		fclose(F);
	}

	IDirect3DPixelShader9 *Compile(IDirect3DDevice9 *Dev, U2Rule &R)
	{
		if (R.Tried)
			return R.PS;
		R.Tried = true;

		static const char TintSource[] = "float4 main() : COLOR { return float4(1, 0, 1, 1); }";
		std::string Source = TintSource;
		if (!R.File.empty())
		{
			FILE *F = nullptr;
			if (fopen_s(&F, (Dir + "U2Shaders\\" + R.File).c_str(), "rb") || F == nullptr)
			{
				Message("shader %s: file not found", R.File.c_str());
				return nullptr;
			}
			Source.clear();
			char Buf[4096];
			size_t n;
			while ((n = fread(Buf, 1, sizeof(Buf), F)) > 0)
				Source.append(Buf, n);
			fclose(F);
		}

		ID3DBlob *Code = nullptr, *Errors = nullptr;
		HRESULT hr = D3DCompile(Source.data(), Source.size(), R.File.c_str(), nullptr, nullptr, "main", "ps_2_a", 0, 0, &Code, &Errors);
		if (FAILED(hr))
		{
			// too big for ps_2_a (22 temporaries): ps_2_b has 32, still usable with fixed-function vertices
			if (Errors != nullptr) { Errors->Release(); Errors = nullptr; }
			hr = D3DCompile(Source.data(), Source.size(), R.File.c_str(), nullptr, nullptr, "main", "ps_2_b", 0, 0, &Code, &Errors);
		}
		if (Errors != nullptr)
		{
			Message("shader %s: %s", R.File.c_str(), (const char *)Errors->GetBufferPointer());
			Errors->Release();
		}
		if (FAILED(hr) || Code == nullptr)
			return nullptr;
		if (FAILED(Dev->CreatePixelShader(static_cast<const DWORD *>(Code->GetBufferPointer()), &R.PS)))
			Message("shader %s: CreatePixelShader failed", R.File.c_str());
		else
			Message("shader %s: ready for texture %08x", R.File.empty() ? "(tint)" : R.File.c_str(), R.Hash);
		Code->Release();
		return R.PS;
	}

	void CopyScene(IDirect3DDevice9 *Dev)
	{
		IDirect3DSurface9 *Target = nullptr, *Copy = nullptr;
		if (FAILED(Dev->GetRenderTarget(0, &Target)) || Target == nullptr)
			return;
		D3DSURFACE_DESC Desc;
		Target->GetDesc(&Desc);
		if (SceneTex != nullptr && (SceneW != Desc.Width || SceneH != Desc.Height || SceneFmt != Desc.Format))
		{
			SceneTex->Release();
			SceneTex = nullptr;
		}
		if (SceneTex == nullptr)
		{
			SceneW = Desc.Width; SceneH = Desc.Height; SceneFmt = Desc.Format;
			if (FAILED(Dev->CreateTexture(SceneW, SceneH, 1, D3DUSAGE_RENDERTARGET, SceneFmt, D3DPOOL_DEFAULT, &SceneTex, nullptr)))
			{
				SceneTex = nullptr;
				Message("scene copy: CreateTexture %ux%u failed", SceneW, SceneH);
			}
		}
		if (SceneTex != nullptr && SceneFrame != Frame && SUCCEEDED(SceneTex->GetSurfaceLevel(0, &Copy)))
		{
			Dev->StretchRect(Target, nullptr, Copy, nullptr, D3DTEXF_NONE);
			Copy->Release();
			SceneFrame = Frame;
		}
		Target->Release();
	}

	// Draws that render into something other than the back buffer (shadow maps are built this way)
	void LogTargetDraw(IDirect3DDevice9 *Dev, bool FixedFunction, bool HasTex0)
	{
		if (!Loaded)
			Load();
		if (!Log)
			return;
		IDirect3DSurface9 *T = nullptr, *BB = nullptr;
		if (FAILED(Dev->GetRenderTarget(0, &T)) || T == nullptr)
			return;
		D3DSURFACE_DESC D = {}, B = {};
		T->GetDesc(&D);
		if (SUCCEEDED(Dev->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &BB)) && BB) { BB->GetDesc(&B); BB->Release(); }
		T->Release();
		if (D.Width == B.Width && D.Height == B.Height)
			return;
		DWORD rs[4] = {}, ts[6] = {}, tf = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &rs[0]);
		Dev->GetRenderState(D3DRS_SRCBLEND, &rs[1]);
		Dev->GetRenderState(D3DRS_DESTBLEND, &rs[2]);
		Dev->GetRenderState(D3DRS_ZENABLE, &rs[3]);
		Dev->GetRenderState(D3DRS_TEXTUREFACTOR, &tf);
		Dev->GetTextureStageState(0, D3DTSS_COLOROP, &ts[0]);
		Dev->GetTextureStageState(0, D3DTSS_COLORARG1, &ts[1]);
		Dev->GetTextureStageState(0, D3DTSS_COLORARG2, &ts[2]);
		Dev->GetTextureStageState(0, D3DTSS_TEXCOORDINDEX, &ts[3]);
		Dev->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &ts[4]);
		DWORD fvf = 0;
		Dev->GetFVF(&fvf);
		char key[300];
		sprintf_s(key, "INTO %ux%u | %s fvf %x tex0 %d | blend %u src %u dst %u z %u tfactor %08x | st0 op %u a1 %u a2 %u tci %x ttf %x",
			D.Width, D.Height, FixedFunction ? "ff" : "vs", fvf, (int)HasTex0, rs[0], rs[1], rs[2], rs[3], tf, ts[0], ts[1], ts[2], ts[3], ts[4]);
		DrawKinds[key]++;
	}

	// Called before a draw. Hash = the stage 0 texture's hash (0: not yet known, read it from
	// Tex). Returns true if a shader was put in place; End() must then follow the draw.
	bool Begin(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, DWORD &Hash, bool FixedFunction)
	{
		if (!Loaded)
			Load();
		if (Tex == nullptr || (!Log && Rules.empty()))
			return false;

		if (Hash == 0)
		{
			U2TexInfo Info;
			Hash = this->Hash(Tex, Info, false);
			if (Hash == 0)
				Hash = 0xFFFFFFFF;         // unreadable: don't try again
			else
				Seen[Hash] = Info;
		}
		if (Hash == 0xFFFFFFFF)
		{
			if (Log)
				LogUnreadableDraw(Dev, Tex);   // render targets (e.g. shadow maps): note how they're drawn
			return false;
		}

		if (Log)
		{
			DWORD Blend = 0;
			Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blend);
			if (Blend)
			{
				U2TexInfo &Info = Seen[Hash];
				if (Info.Draws++ == 0)
				{
					U2TexInfo Dummy;
					this->Hash(Tex, Dummy, true);
				}
			}
		}

		U2Rule *Rule = nullptr;
		for (U2Rule &R : Rules)
			if (R.Hash == Hash)
				Rule = &R;
		if (Rule == nullptr)
			return false;
		// only the see-through parts: an atlas is often shared with solid ones
		DWORD Blending = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blending);
		if (!Blending)
			return false;
		IDirect3DPixelShader9 *PS = Compile(Dev, *Rule);
		if (PS == nullptr)
			return false;

		CopyScene(Dev);

		Dev->GetPixelShader(&OldPS);
		Dev->GetTexture(1, &OldTex1);
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &OldBlend);
		Dev->GetPixelShaderConstantF(0, OldConst[0], 8);
		static const D3DSAMPLERSTATETYPE Samp[5] = { D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_MAGFILTER, D3DSAMP_MINFILTER, D3DSAMP_MIPFILTER };
		static const DWORD SampValue[5] = { D3DTADDRESS_CLAMP, D3DTADDRESS_CLAMP, D3DTEXF_LINEAR, D3DTEXF_LINEAR, D3DTEXF_NONE };
		for (int i = 0; i < 5; i++)
		{
			Dev->GetSamplerState(1, Samp[i], &OldSamp1[i]);
			Dev->SetSamplerState(1, Samp[i], SampValue[i]);
		}
		if (FixedFunction)
		{
			// raw texture coordinates on stage 0 (no panning): the shader animates itself
			Dev->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF[0]);
			Dev->SetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
			static const D3DMATRIX Identity = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
			for (DWORD s = 1; s <= 2; s++)
			{
				Dev->GetTextureStageState(s, D3DTSS_TEXCOORDINDEX, &OldTCI[s]);
				Dev->GetTextureStageState(s, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF[s]);
				Dev->GetTransform((D3DTRANSFORMSTATETYPE)(D3DTS_TEXTURE0 + s), &OldTexMat[s]);
				Dev->SetTextureStageState(s, D3DTSS_TEXCOORDINDEX, (s == 1 ? D3DTSS_TCI_CAMERASPACENORMAL : D3DTSS_TCI_CAMERASPACEPOSITION) | s);
				Dev->SetTextureStageState(s, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_COUNT3);
				Dev->SetTransform((D3DTRANSFORMSTATETYPE)(D3DTS_TEXTURE0 + s), &Identity);
			}
		}

		float Const[8][4] = {};
		Const[0][0] = (GetTickCount() % 3600000) / 1000.0f;
		Const[0][1] = FixedFunction ? 1.0f : 0.0f;
		Const[0][2] = SceneW ? 1.0f / SceneW : 0;
		Const[0][3] = SceneH ? 1.0f / SceneH : 0;
		D3DMATRIX Proj;
		Dev->GetTransform(D3DTS_PROJECTION, &Proj);
		for (int r = 0; r < 4; r++)
			for (int c = 0; c < 4; c++)
				Const[4 + r][c] = Proj.m[r][c];
		Dev->SetPixelShaderConstantF(0, Const[0], 8);
		Dev->SetTexture(1, SceneTex);
		Dev->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
		Dev->SetPixelShader(PS);
		WasFixedFunction = FixedFunction;
		Mode = 1;
		return true;
	}

	// ---- contact-hardening shadows (PCSS) --------------------------------------------------
	// Unreal II builds each dynamic shadow by drawing the character as a flat silhouette
	// (colour = texture factor) into a small render target, then projects that target onto
	// the ground (stage 0 projected, DESTCOLOR*SRCCOLOR, stages 1-2 fade to the neutral
	// texture factor by their gradient textures' alpha). With "pcss=1":
	//   shadow-map pass: pcss_map.hlsl keeps the colour and writes the distance from the light
	//                    into the target's otherwise unused alpha
	//   projector pass:  pcss_proj.hlsl searches for blockers, sizes the blur by the gap
	//                    between them and the ground, filters, and applies the two fades
	// The engine's own shadow blur must be off (WinDrv BlurShadows=False): it would mix the
	// stored distances. pcssparams=A B C D goes to c2 (search radius, min radius, radius per
	// unit of gap, max radius; UV units).
	bool Pcss = false;
	U2Rule MapRule, ProjRule;
	float PcssParams[4] = { 0.05f, 0.004f, 0.0006f, 0.06f };
	float PcssDebug = 0;          // pcssdebug=1: colour the shadows by the measured gap
	int Mode = 0;                 // what End() undoes: 1 surface shader, 2 shadow map, 3 projector
	DWORD OldCWE = 0;
	std::map<void *, D3DMATRIX> MapViews;   // shadow-map surface -> the light's view it was drawn with
	IDirect3DSurface9 *MapTarget = nullptr; // the shadow map drawn last (compared only, not referenced)
	std::map<void *, IDirect3DTexture9 *> BlurSource;   // blurred shadow surface (B) -> our snapshot of its sharp map (A)
	bool MapDirty = false;                  // a silhouette was drawn since the last snapshot
	void *CopiedFor = nullptr;              // the B the last snapshot was taken for
	IDirect3DBaseTexture9 *OldTex3 = nullptr;
	DWORD OldSamp3[5] = {};

	void DumpRaw(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, const char *What, UINT Size)
	{
		D3DSURFACE_DESC D = {};
		Tex->GetLevelDesc(0, &D);
		IDirect3DSurface9 *RT = nullptr, *Sys = nullptr;
		if (SUCCEEDED(Tex->GetSurfaceLevel(0, &RT)) &&
			SUCCEEDED(Dev->CreateOffscreenPlainSurface(D.Width, D.Height, D.Format, D3DPOOL_SYSTEMMEM, &Sys, nullptr)) &&
			SUCCEEDED(Dev->GetRenderTargetData(RT, Sys)))
		{
			D3DLOCKED_RECT L;
			if (SUCCEEDED(Sys->LockRect(&L, nullptr, D3DLOCK_READONLY)))
			{
				char name[64];
				sprintf_s(name, "U2Shaders\\dump\\pcss_%s_%u.raw", What, Size);
				FILE *F = nullptr;
				if (!fopen_s(&F, (Dir + name).c_str(), "wb") && F)
				{
					for (UINT y = 0; y < D.Height; y++)
						fwrite((const BYTE *)L.pBits + y * L.Pitch, 4, D.Width, F);
					fclose(F);
				}
				Sys->UnlockRect();
			}
		}
		else
			Message("pcss dump of %s %u failed\n", What, Size);
		if (Sys) Sys->Release();
		if (RT) RT->Release();
	}

	void ClearBlurSources() { for (auto &It : BlurSource) if (It.second) It.second->Release(); BlurSource.clear(); }
	DWORD OldTCI3 = 0, OldTTF3 = 0, OldSrc = 0, OldDst = 0;
	bool RawDebug = false;
	D3DMATRIX OldTexMat3 = {};

	static D3DMATRIX Mul(const D3DMATRIX &A, const D3DMATRIX &B)
	{
		D3DMATRIX R = {};
		for (int r = 0; r < 4; r++)
			for (int c = 0; c < 4; c++)
				for (int k = 0; k < 4; k++)
					R.m[r][c] += A.m[r][k] * B.m[k][c];
		return R;
	}

	// inverse of a view matrix (rotation + translation, row-vector convention)
	static D3DMATRIX InvView(const D3DMATRIX &V)
	{
		D3DMATRIX R = {};
		for (int r = 0; r < 3; r++)
			for (int c = 0; c < 3; c++)
				R.m[r][c] = V.m[c][r];
		for (int c = 0; c < 3; c++)
			R.m[3][c] = -(V.m[3][0] * R.m[0][c] + V.m[3][1] * R.m[1][c] + V.m[3][2] * R.m[2][c]);
		R.m[3][3] = 1;
		return R;
	}

	// the game draws a shadow into a render surface and copies it into the projector's texture
	void OnCopy(IDirect3DSurface9 *From, IDirect3DSurface9 *To)
	{
		auto It = MapViews.find(From);
		if (It != MapViews.end())
		{
			MapViews[To] = It->second;
			static std::map<UINT, bool> told;
			D3DSURFACE_DESC A = {}, B = {};
			From->GetDesc(&A); To->GetDesc(&B);
			if (!told[A.Width])
			{
				told[A.Width] = true;
				Message("pcss copy %ux%u fmt %u -> %ux%u fmt %u usage %x pool %u\n", A.Width, A.Height, (unsigned)A.Format, B.Width, B.Height, (unsigned)B.Format, (unsigned)B.Usage, (unsigned)B.Pool);
			}
		}
	}

	bool Offscreen(IDirect3DDevice9 *Dev)
	{
		IDirect3DSurface9 *T = nullptr, *BB = nullptr;
		D3DSURFACE_DESC D = {}, B = {};
		if (FAILED(Dev->GetRenderTarget(0, &T)) || T == nullptr)
			return false;
		T->GetDesc(&D);
		T->Release();
		if (SUCCEEDED(Dev->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &BB)) && BB) { BB->GetDesc(&B); BB->Release(); }
		return D.Width != B.Width || D.Height != B.Height;
	}

	bool PcssBegin(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, bool FixedFunction)
	{
		if (!Loaded)
			Load();
		if (!Pcss)
			return false;
		DWORD blend = 0, src = 0, op0 = 0, arg1 = 0, ttf0 = 0, tf = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend);
		Dev->GetRenderState(D3DRS_SRCBLEND, &src);
		Dev->GetTextureStageState(0, D3DTSS_COLOROP, &op0);
		Dev->GetTextureStageState(0, D3DTSS_COLORARG1, &arg1);
		Dev->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &ttf0);
		Dev->GetRenderState(D3DRS_TEXTUREFACTOR, &tf);
		const float tfc[4] = { ((tf >> 16) & 255) / 255.0f, ((tf >> 8) & 255) / 255.0f, (tf & 255) / 255.0f, (tf >> 24) / 255.0f };

		if (PcssDebug > 4.5 && Offscreen(Dev))
		{
			// every distinct state set drawn into an offscreen target, once
			static std::map<std::string, bool> told;
			DWORD aop = 0, aa1 = 0, cwe = 0, zen = 0, dst = 0, op1 = 0, fvf = 0;
			Dev->GetTextureStageState(0, D3DTSS_ALPHAOP, &aop);
			Dev->GetTextureStageState(0, D3DTSS_ALPHAARG1, &aa1);
			Dev->GetTextureStageState(1, D3DTSS_COLOROP, &op1);
			Dev->GetRenderState(D3DRS_COLORWRITEENABLE, &cwe);
			Dev->GetRenderState(D3DRS_ZENABLE, &zen);
			Dev->GetRenderState(D3DRS_DESTBLEND, &dst);
			Dev->GetFVF(&fvf);
			IDirect3DSurface9 *T = nullptr; D3DSURFACE_DESC D = {};
			if (SUCCEEDED(Dev->GetRenderTarget(0, &T)) && T) { T->GetDesc(&D); T->Release(); }
			char k[300];
			sprintf_s(k, "rt %u tex %d ff %d blend %u %u/%u cop %u a1 %x aop %u aa1 %x st1 %u cwe %x z %u fvf %x tf %08x",
				D.Width, Tex != nullptr, FixedFunction, blend, src, dst, op0, arg1, aop, aa1, op1, cwe, zen, fvf, tf);
			if (!told[k]) { told[k] = true; Message("offscreen draw: %s\n", k); }
		}
		bool map = Tex == nullptr && !blend && op0 == D3DTOP_SELECTARG1 && (arg1 & 0xF) == D3DTA_TFACTOR && Offscreen(Dev);
		if (map)
		{
			IDirect3DSurface9 *T = nullptr;
			if (SUCCEEDED(Dev->GetRenderTarget(0, &T)) && T) { MapTarget = T; T->Release(); }
			MapDirty = true;
		}
		else if (Tex != nullptr && blend && src == D3DBLEND_SRCALPHA && MapTarget != nullptr)
		{
			// the engine blurs the silhouette map (A) into a second target (B) with additive
			// textured passes; the projector then samples B. A is a scratch target shared by
			// every shadow, B is kept per shadow (and only redrawn when needed). So take a
			// snapshot of A for this B now, which the projector pass reads instead of B.
			IDirect3DSurface9 *T = nullptr, *S0 = nullptr;
			if (SUCCEEDED(Dev->GetRenderTarget(0, &T)) && T && SUCCEEDED(Tex->GetSurfaceLevel(0, &S0)) && S0)
			{
				if (S0 == MapTarget && T != MapTarget && (MapDirty || CopiedFor != T))
				{
					D3DSURFACE_DESC D = {};
					S0->GetDesc(&D);
					IDirect3DTexture9 *&Snap = BlurSource[T];
					if (Snap != nullptr)
					{
						D3DSURFACE_DESC SD = {};
						Snap->GetLevelDesc(0, &SD);
						if (SD.Width != D.Width || SD.Height != D.Height || SD.Format != D.Format) { Snap->Release(); Snap = nullptr; }
					}
					if (Snap == nullptr && FAILED(Dev->CreateTexture(D.Width, D.Height, 1, D3DUSAGE_RENDERTARGET, D.Format, D3DPOOL_DEFAULT, &Snap, nullptr)))
						Snap = nullptr;
					IDirect3DSurface9 *Dst = nullptr;
					if (Snap != nullptr && SUCCEEDED(Snap->GetSurfaceLevel(0, &Dst)) && Dst)
					{
						Dev->StretchRect(S0, nullptr, Dst, nullptr, D3DTEXF_NONE);
						Dst->Release();
					}
					MapDirty = false;
					CopiedFor = T;
				}
			}
			if (S0) S0->Release();
			if (T) T->Release();
			return false;
		}
		bool proj = Tex != nullptr && blend && src == D3DBLEND_DESTCOLOR && (ttf0 & D3DTTFF_PROJECTED);
		if ((!map && !proj) || !FixedFunction)
			return false;
		IDirect3DPixelShader9 *PS = Compile(Dev, map ? MapRule : ProjRule);
		if (PS == nullptr)
			return false;
		{
			// once per pass kind and size: the formats involved (alpha must survive to the projector)
			static std::map<UINT, bool> told;
			D3DSURFACE_DESC D = {};
			IDirect3DSurface9 *T = nullptr;
			if (map && SUCCEEDED(Dev->GetRenderTarget(0, &T)) && T) { T->GetDesc(&D); T->Release(); }
			if (proj) Tex->GetLevelDesc(0, &D);
			UINT key = (map ? 0x10000 : 0x20000) + D.Width;
			if (!told[key])
			{
				told[key] = true;
				Message("pcss %s %ux%u format %u usage %x\n", map ? "map target" : "projector texture", D.Width, D.Height, (unsigned)D.Format, (unsigned)D.Usage);
			}
		}

		Dev->GetPixelShader(&OldPS);
		Dev->GetPixelShaderConstantF(0, OldConst[0], 8);
		float c[4][4] = {};
		c[0][0] = (GetTickCount() % 3600000) / 1000.0f;
		c[0][1] = PcssDebug;
		memcpy(c[1], tfc, sizeof(tfc));
		memcpy(c[2], PcssParams, sizeof(PcssParams));
		IDirect3DTexture9 *Sharp = nullptr;
		if (proj)
		{
			// the sharp silhouette map this blurred shadow was made from (see the blur passes above)
			IDirect3DSurface9 *S0 = nullptr;
			if (SUCCEEDED(Tex->GetSurfaceLevel(0, &S0)) && S0)
			{
				auto It = BlurSource.find(S0);
				if (It != BlurSource.end())
					Sharp = It->second;
				S0->Release();
			}
			if (Sharp == nullptr)
			{
				static int told = 0;
				if (told++ < 4)
					Message("pcss: projector without a known sharp map, left stock\n");
				return false;
			}
		}
		if (proj && PcssDebug > 2.5)
		{
			// debug: both maps, raw BGRA, once per size
			static std::map<UINT, bool> dumped;
			D3DSURFACE_DESC D = {};
			Tex->GetLevelDesc(0, &D);
			if (!dumped[D.Width] && Frame > 300)
			{
				dumped[D.Width] = true;
				DumpRaw(Dev, Tex, "blurred", D.Width);
				DumpRaw(Dev, Sharp, "sharp", D.Width);
			}
		}
		if (proj)
		{
			// the sharp map on sampler 3
			static const D3DSAMPLERSTATETYPE Samp[5] = { D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_MAGFILTER, D3DSAMP_MINFILTER, D3DSAMP_MIPFILTER };
			static const DWORD Want[5] = { D3DTADDRESS_CLAMP, D3DTADDRESS_CLAMP, D3DTEXF_LINEAR, D3DTEXF_LINEAR, D3DTEXF_NONE };
			Dev->GetTexture(3, &OldTex3);
			for (int i = 0; i < 5; i++)
			{
				Dev->GetSamplerState(3, Samp[i], &OldSamp3[i]);
				Dev->SetSamplerState(3, Samp[i], Want[i]);
			}
			Dev->SetTexture(3, Sharp);
		}
		if (proj)
		{
			D3DSURFACE_DESC D = {};
			Tex->GetLevelDesc(0, &D);
			c[3][0] = D.Width ? 1.0f / D.Width : 0;
			c[3][1] = D.Height ? 1.0f / D.Height : 0;
		}
		// c4: camera space -> world height (z), from the inverse of the current view. In the
		// shadow-map pass the view is the light's, in the projector pass the player's: both
		// passes then measure world height, and their difference is how far the shadowing
		// part is above the ground it shadows.
		float zrow[4] = { 0, 0, 0, 0 };
		{
			D3DMATRIX V;
			Dev->GetTransform(D3DTS_VIEW, &V);
			D3DMATRIX Inv = InvView(V);
			zrow[0] = Inv.m[0][2]; zrow[1] = Inv.m[1][2]; zrow[2] = Inv.m[2][2]; zrow[3] = Inv.m[3][2];
			c[0][2] = 1.0f;
		}
		Dev->SetPixelShaderConstantF(0, c[0], 4);
		Dev->SetPixelShaderConstantF(4, zrow, 1);
		if (!map)
		{
			// camera-space position on TEXCOORD3 for the receiver depth
			static const D3DMATRIX Identity = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
			Dev->GetTextureStageState(3, D3DTSS_TEXCOORDINDEX, &OldTCI3);
			Dev->GetTextureStageState(3, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF3);
			Dev->GetTransform(D3DTS_TEXTURE3, &OldTexMat3);
			Dev->SetTextureStageState(3, D3DTSS_TEXCOORDINDEX, D3DTSS_TCI_CAMERASPACEPOSITION | 3);
			Dev->SetTextureStageState(3, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_COUNT3);
			Dev->SetTransform(D3DTS_TEXTURE3, &Identity);
		}
		if (map)
		{
			// the silhouette's camera-space position (the light's view) on TEXCOORD2
			static const D3DMATRIX Identity = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
			Dev->GetTextureStageState(2, D3DTSS_TEXCOORDINDEX, &OldTCI[2]);
			Dev->GetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF[2]);
			Dev->GetTransform(D3DTS_TEXTURE2, &OldTexMat[2]);
			Dev->SetTextureStageState(2, D3DTSS_TEXCOORDINDEX, D3DTSS_TCI_CAMERASPACEPOSITION | 2);
			Dev->SetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_COUNT3);
			Dev->SetTransform(D3DTS_TEXTURE2, &Identity);
			Dev->GetRenderState(D3DRS_COLORWRITEENABLE, &OldCWE);
			Dev->SetRenderState(D3DRS_COLORWRITEENABLE, 0xF);
		}
		if (proj && PcssDebug > 1.5 && PcssDebug < 2.5)
		{
			// raw-value debug view: write the shader output as is (no multiply with the ground)
			Dev->GetRenderState(D3DRS_SRCBLEND, &OldSrc);
			Dev->GetRenderState(D3DRS_DESTBLEND, &OldDst);
			Dev->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_ONE);
			Dev->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_ZERO);
			RawDebug = true;
		}
		Dev->SetPixelShader(PS);
		Mode = map ? 2 : 3;
		return true;
	}

	void End(IDirect3DDevice9 *Dev)
	{
		if (Mode == 4)
		{
			Dev->SetRenderState(D3DRS_COLORWRITEENABLE, OldCWE);
			Mode = 0;
			return;
		}
		if (Mode == 2 || Mode == 3)
		{
			Dev->SetPixelShader(OldPS);
			Dev->SetPixelShaderConstantF(0, OldConst[0], 8);
			if (RawDebug)
			{
				Dev->SetRenderState(D3DRS_SRCBLEND, OldSrc);
				Dev->SetRenderState(D3DRS_DESTBLEND, OldDst);
				RawDebug = false;
			}
			if (Mode == 3)
			{
				static const D3DSAMPLERSTATETYPE Samp[5] = { D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_MAGFILTER, D3DSAMP_MINFILTER, D3DSAMP_MIPFILTER };
				Dev->SetTexture(3, OldTex3);
				for (int i = 0; i < 5; i++)
					Dev->SetSamplerState(3, Samp[i], OldSamp3[i]);
				if (OldTex3 != nullptr) { OldTex3->Release(); OldTex3 = nullptr; }
				Dev->SetTextureStageState(3, D3DTSS_TEXCOORDINDEX, OldTCI3);
				Dev->SetTextureStageState(3, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF3);
				Dev->SetTransform(D3DTS_TEXTURE3, &OldTexMat3);
			}
			if (Mode == 2)
			{
				Dev->SetTextureStageState(2, D3DTSS_TEXCOORDINDEX, OldTCI[2]);
				Dev->SetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF[2]);
				Dev->SetTransform(D3DTS_TEXTURE2, &OldTexMat[2]);
				Dev->SetRenderState(D3DRS_COLORWRITEENABLE, OldCWE);
			}
			if (OldPS != nullptr) { OldPS->Release(); OldPS = nullptr; }
			Mode = 0;
			return;
		}
		Mode = 0;
		static const D3DSAMPLERSTATETYPE Samp[5] = { D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_MAGFILTER, D3DSAMP_MINFILTER, D3DSAMP_MIPFILTER };
		Dev->SetPixelShader(OldPS);
		Dev->SetRenderState(D3DRS_ALPHABLENDENABLE, OldBlend);
		Dev->SetTexture(1, OldTex1);
		Dev->SetPixelShaderConstantF(0, OldConst[0], 8);
		for (int i = 0; i < 5; i++)
			Dev->SetSamplerState(1, Samp[i], OldSamp1[i]);
		if (WasFixedFunction)
			Dev->SetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF[0]);
		if (WasFixedFunction)
			for (DWORD s = 1; s <= 2; s++)
			{
				Dev->SetTextureStageState(s, D3DTSS_TEXCOORDINDEX, OldTCI[s]);
				Dev->SetTextureStageState(s, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF[s]);
				Dev->SetTransform((D3DTRANSFORMSTATETYPE)(D3DTS_TEXTURE0 + s), &OldTexMat[s]);
			}
		if (OldPS != nullptr) { OldPS->Release(); OldPS = nullptr; }
		if (OldTex1 != nullptr) { OldTex1->Release(); OldTex1 = nullptr; }
	}

	// Draws whose stage 0 texture can't be read (render targets such as the dynamic shadow
	// maps) can't be picked by hash: list their render states instead, to find a signature.
	std::map<std::string, unsigned> DrawKinds;
	void LogUnreadableDraw(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex)
	{
		D3DSURFACE_DESC Desc = {};
		Tex->GetLevelDesc(0, &Desc);
		DWORD rs[6] = {}, ts[10] = {};
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &rs[0]);
		Dev->GetRenderState(D3DRS_SRCBLEND, &rs[1]);
		Dev->GetRenderState(D3DRS_DESTBLEND, &rs[2]);
		Dev->GetRenderState(D3DRS_ZWRITEENABLE, &rs[3]);
		Dev->GetRenderState(D3DRS_ALPHATESTENABLE, &rs[4]);
		Dev->GetTextureStageState(0, D3DTSS_TEXCOORDINDEX, &ts[0]);
		Dev->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &ts[1]);
		Dev->GetTextureStageState(0, D3DTSS_COLOROP, &ts[2]);
		Dev->GetTextureStageState(1, D3DTSS_COLOROP, &ts[3]);
		Dev->GetTextureStageState(1, D3DTSS_TEXCOORDINDEX, &ts[4]);
		Dev->GetTextureStageState(1, D3DTSS_TEXTURETRANSFORMFLAGS, &ts[5]);
		Dev->GetTextureStageState(2, D3DTSS_COLOROP, &ts[6]);
		IDirect3DBaseTexture9 *t1 = nullptr;
		Dev->GetTexture(1, &t1);
		D3DSURFACE_DESC D1 = {};
		if (t1 != nullptr && t1->GetType() == D3DRTYPE_TEXTURE)
			static_cast<IDirect3DTexture9 *>(t1)->GetLevelDesc(0, &D1);
		if (t1 != nullptr) t1->Release();
		char key[400];
		sprintf_s(key, "tex0 %ux%u fmt %u usage %x | blend %u src %u dst %u zwrite %u atest %u | "
			"st0 tci %x ttf %x op %u | st1 op %u tci %x ttf %x tex %ux%u | st2 op %u",
			Desc.Width, Desc.Height, (unsigned)Desc.Format, (unsigned)Desc.Usage, rs[0], rs[1], rs[2], rs[3], rs[4],
			ts[0], ts[1], ts[2], ts[3], ts[4], ts[5], D1.Width, D1.Height, ts[6]);
		DrawKinds[key]++;

		// projector draws: the full stage setup, and one copy of each shadow-map size
		if (rs[1] == D3DBLEND_DESTCOLOR && (ts[1] & D3DTTFF_PROJECTED))
		{
			char k2[400];
			DWORD a[3][6] = {};
			for (DWORD st = 0; st < 3; st++)
			{
				Dev->GetTextureStageState(st, D3DTSS_COLORARG1, &a[st][0]);
				Dev->GetTextureStageState(st, D3DTSS_COLORARG2, &a[st][1]);
				Dev->GetTextureStageState(st, D3DTSS_ALPHAOP, &a[st][2]);
				Dev->GetTextureStageState(st, D3DTSS_ALPHAARG1, &a[st][3]);
				Dev->GetTextureStageState(st, D3DTSS_ALPHAARG2, &a[st][4]);
				Dev->GetTextureStageState(st, D3DTSS_COLOROP, &a[st][5]);
			}
			DWORD tf = 0;
			Dev->GetRenderState(D3DRS_TEXTUREFACTOR, &tf);
			sprintf_s(k2, "PROJECTOR stages (cop a1 a2 / aop a1 a2): 0: %u %x %x / %u %x %x | 1: %u %x %x / %u %x %x | 2: %u %x %x / %u %x %x | tfactor %08x",
				a[0][5], a[0][0], a[0][1], a[0][2], a[0][3], a[0][4], a[1][5], a[1][0], a[1][1], a[1][2], a[1][3], a[1][4],
				a[2][5], a[2][0], a[2][1], a[2][2], a[2][3], a[2][4], tf);
			DrawKinds[k2]++;
			static std::map<UINT, bool> dumped;
			if (!dumped[Desc.Width] && Frame > 200)
			{
				dumped[Desc.Width] = true;
				IDirect3DSurface9 *RT = nullptr, *Sys = nullptr;
				if (SUCCEEDED(Tex->GetSurfaceLevel(0, &RT)) &&
					SUCCEEDED(Dev->CreateOffscreenPlainSurface(Desc.Width, Desc.Height, Desc.Format, D3DPOOL_SYSTEMMEM, &Sys, nullptr)) &&
					SUCCEEDED(Dev->GetRenderTargetData(RT, Sys)))
				{
					D3DLOCKED_RECT L;
					if (SUCCEEDED(Sys->LockRect(&L, nullptr, D3DLOCK_READONLY)))
					{
						D3DSURFACE_DESC D2 = Desc;
						D2.Format = D3DFMT_A8R8G8B8;
						SaveDDS(0x5400 + Desc.Width, D2, (const BYTE *)L.pBits, L.Pitch * Desc.Height, L.Pitch);
						Sys->UnlockRect();
					}
				}
				if (Sys) Sys->Release();
				if (RT) RT->Release();
			}
		}
	}

	void OnPresent()
	{
		Frame++;
		if (Log && Frame - LogFrame >= 300)
		{
			LogFrame = Frame;
			WriteSeen();
		}
	}

	void WriteSeen()
	{
		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + "U2Shaders\\dump\\seen.txt").c_str(), "w") || F == nullptr)
			return;
		for (const auto &It : Seen)
			if (It.second.Draws)
				fprintf(F, "%08x %ux%u fmt %u draws %u\n", It.first, It.second.W, It.second.H, (unsigned)It.second.Fmt, It.second.Draws);
		fclose(F);
		if (fopen_s(&F, (Dir + "U2Shaders\\dump\\draws.txt").c_str(), "w") || F == nullptr)
			return;
		for (const auto &It : DrawKinds)
			fprintf(F, "%8u  %s\n", It.second, It.first.c_str());
		fclose(F);
	}

	// Before the device is reset or destroyed: default-pool objects must go
	void OnLost()
	{
		MapViews.clear();
		MapTarget = nullptr;
		ClearBlurSources();
		MapDirty = false;
		CopiedFor = nullptr;
		if (SceneTex != nullptr) { SceneTex->Release(); SceneTex = nullptr; }
		if (Log)
			WriteSeen();
	}

	void OnDestroy()
	{
		OnLost();
		for (U2Rule &R : Rules)
			if (R.PS != nullptr) { R.PS->Release(); R.PS = nullptr; R.Tried = false; }
		for (U2Rule *R : { &MapRule, &ProjRule })
			if (R->PS != nullptr) { R->PS->Release(); R->PS = nullptr; R->Tried = false; }
	}

private:
	bool WasFixedFunction = false;
};
