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
 *     decal=1a2b3c4d decal_parallax.hlsl
 *                                 the same, but the draw keeps its own blending (no frame
 *                                 copy in s1): the shader returns what the texture would
 *                                 have, so overlapping decals still layer
 *     surface=1a2b3c4d world_parallax.hlsl
 *                                 a solid surface (wall, floor) drawn with parallax: the
 *                                 shader redoes the texture stages (texture x vertex colour
 *                                 x lightmap in s1, see SurfaceBegin); the lightmap and the
 *                                 texture's panning are left as they are. c2 = how the stages
 *                                 combine, c3 = the texture's brightness levels
 *     replace=1a2b3c4d my.dds     draw U2Shaders\my.dds wherever that texture is used, on any
 *                                 of stages 0-3 (lightmaps too); a DDS, 32-bit or DXT1/3/5,
 *                                 with its own mips (see Replacement)
 *     charlight=1                 light lit solid draws (characters, weapons) per pixel with
 *                                 char_light.hlsl: the game's own D3D lights, softer wrap,
 *                                 ambient lighter from above, rim (see CharBegin)
 *     lmcapture=1                 record the lightmapped geometry as it is drawn, for baking
 *                                 elsewhere: U2Shaders\capture\scene.obj + lightmaps.txt,
 *                                 lightmaps saved in U2Shaders\dump (see CaptureDraw)
 *     post=1                      bloom, sharpening and colour grading before the HUD
 *                                 (bloom=, grade=, colour=, sharpen=, postsplit=; see PostCheck)
 *     charprobe=1                 record how opaque on-screen draws (characters) are lit, in
 *                                 U2Shaders\dump\chars.txt, and whether scene depth can be
 *                                 read as a texture (U2Shaders.log; logging only, see ProbeDraw)
 *
 * What a shader gets:
 *     s0            the original texture, TEXCOORD0 = its (possibly panned) coordinates
 *     s1            a copy of the frame so far (for refraction)
 *     TEXCOORD1     camera-space normal      (only on fixed-function draws, see c0.y)
 *     TEXCOORD2     camera-space position
 *     COLOR0        the vertex lighting
 *     c0            (time in seconds, 1 if normals/positions are valid, 1/width, 1/height)
 *     c1.x          1 if TEXCOORD0 is projected (projector decals): divide .xy by .z
 *     c4..c7        the projection matrix (rows), to turn a position into a screen place
 *
 * While a shader draws, alpha blending is off: the shader has the frame behind it in s1
 * and returns the finished colour.
 */

#pragma once

#include <d3dcompiler.h>
#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <map>
#include <set>
#include <string>
#include <unordered_set>
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
	bool KeepBlend = false;    // decal=: the draw keeps its own blending, no frame copy
	bool Surface = false;      // surface=: solid draws only, see SurfaceBegin
	bool Refused = false;      // surface=: an unsupported stage setup was logged once
	float Levels[4] = {};      // surface=: the texture's brightness levels (see TextureLevels)
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
			else if (sscanf_s(Line, " shadowtint=%f %f %f", &ShadowTint[0], &ShadowTint[1], &ShadowTint[2]) == 3)
				;
			else if (sscanf_s(Line, " charprobe=%u", &Hash) == 1)
				CharProbe = Hash != 0;
			else if (sscanf_s(Line, " lmcapture=%u", &Hash) == 1)
				Capture = Hash != 0;
			else if (sscanf_s(Line, " charlight=%u", &Hash) == 1)
			{
				CharLight = Hash != 0;
				CharRule.File = "char_light.hlsl";
			}
			else if (sscanf_s(Line, " post=%u", &Hash) == 1)
			{
				Post = Hash != 0;
				PostBright.File = "post_bright.hlsl";
				PostBlur.File = "post_blur.hlsl";
				PostFinal.File = "post_final.hlsl";
			}
			else if (sscanf_s(Line, " posttrace=%u", &Hash) == 1)
				PostTrace = (int)Hash;
			else if (sscanf_s(Line, " postsplit=%u", &Hash) == 1)
				PostSplit = Hash != 0 ? 1.0f : 0.0f;
			else if (sscanf_s(Line, " bloom=%f %f", &PostBloom[0], &PostBloom[1]) == 2)
				;
			else if (sscanf_s(Line, " grade=%f %f %f %f", &PostGrade[0], &PostGrade[1], &PostGrade[2], &PostGrade[3]) == 4)
				;
			else if (sscanf_s(Line, " colour=%f %f %f", &PostBalance[0], &PostBalance[1], &PostBalance[2]) == 3)
				;
			else if (sscanf_s(Line, " sharpen=%f", &PostBalance[3]) == 1)
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
			else if (sscanf_s(Line, " decal=%x %255s", &Hash, Name, (unsigned)sizeof(Name)) == 2)
			{
				U2Rule R;
				R.Hash = Hash;
				R.File = Name;
				R.KeepBlend = true;
				Rules.push_back(R);
			}
			else if (sscanf_s(Line, " replace=%x %255s", &Hash, Name, (unsigned)sizeof(Name)) == 2)
				Replacements[Hash].File = Name;
			else if (sscanf_s(Line, " surface=%x %255s", &Hash, Name, (unsigned)sizeof(Name)) == 2)
			{
				U2Rule R;
				R.Hash = Hash;
				R.File = Name;
				R.Surface = true;
				Rules.push_back(R);
			}
		}
		fclose(F);
		Message("U2Shaders: log %d, %u rule(s), %u replacement(s), pcss %d (%g %g %g %g), shadow tint %g %g %g", (int)Log, (unsigned)Rules.size(), (unsigned)Replacements.size(), (int)Pcss,
			PcssParams[0], PcssParams[1], PcssParams[2], PcssParams[3], ShadowTint[0], ShadowTint[1], ShadowTint[2]);
		if (Log || CharProbe || Capture)
		{
			CreateDirectoryA((Dir + "U2Shaders").c_str(), nullptr);
			CreateDirectoryA((Dir + "U2Shaders\\dump").c_str(), nullptr);
		}
		if (Capture)
			CreateDirectoryA((Dir + "U2Shaders\\capture").c_str(), nullptr);
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

	void CopyScene(IDirect3DDevice9 *Dev, bool Force = false)
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
		if (SceneTex != nullptr && (Force || SceneFrame != Frame) && SUCCEEDED(SceneTex->GetSurfaceLevel(0, &Copy)))
		{
			Dev->StretchRect(Target, nullptr, Copy, nullptr, D3DTEXF_NONE);
			Copy->Release();
			SceneFrame = Frame;
		}
		Target->Release();
	}

	// Draws that render into something other than the back buffer (shadow maps are built this way)
	// called before every draw (despite the name: it is the per-draw hook)
	void LogTargetDraw(IDirect3DDevice9 *Dev, bool FixedFunction, bool HasTex0)
	{
		if (!Loaded)
			Load();
		PostCheck(Dev);
		if (CharProbe && !HasTex0 && Offscreen(Dev))
		{
			DWORD blend = 0, op0 = 0, arg1 = 0;
			Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend);
			Dev->GetTextureStageState(0, D3DTSS_COLOROP, &op0);
			Dev->GetTextureStageState(0, D3DTSS_COLORARG1, &arg1);
			if (!blend && op0 == D3DTOP_SELECTARG1 && (arg1 & 0xF) == D3DTA_TFACTOR)
				MapsThisFrame++;           // a shadow silhouette (same test as PcssBegin's map pass)
		}
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

	// Fills in a texture's cached hash the first time (0xFFFFFFFF: unreadable, don't try again)
	void Known(IDirect3DTexture9 *Tex, DWORD &Hash)
	{
		if (Hash != 0)
			return;
		U2TexInfo Info;
		Hash = this->Hash(Tex, Info, false);
		if (Hash == 0)
			Hash = 0xFFFFFFFF;
		else
			Seen[Hash] = Info;
	}

	// ---- replace=: our own texture in place of one of the game's -------------------------
	// The device swaps it in for each draw and back after (so the game still sees its own
	// texture when it asks), on stages 0-3. The rules keyed by hash still match the original.
	struct U2Replace
	{
		std::string File;
		IDirect3DTexture9 *Tex = nullptr;
		bool Tried = false;
	};
	std::map<DWORD, U2Replace> Replacements;

	IDirect3DTexture9 *Replacement(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, DWORD &Hash)
	{
		if (!Loaded)
			Load();
		if (Replacements.empty() || Tex == nullptr)
			return nullptr;
		Known(Tex, Hash);
		const auto It = Replacements.find(Hash);
		if (It == Replacements.end())
			return nullptr;
		U2Replace &R = It->second;
		if (!R.Tried)
		{
			R.Tried = true;
			R.Tex = LoadDDS(Dev, R.File);
			if (R.Tex != nullptr)
				Message("replace %08x: %s loaded", Hash, R.File.c_str());
		}
		return R.Tex;
	}

	// A DDS file as a managed texture (survives device resets): 32-bit (A8R8G8B8/X8R8G8B8) or
	// DXT1/3/5, all the mip levels the file has.
	IDirect3DTexture9 *LoadDDS(IDirect3DDevice9 *Dev, const std::string &File)
	{
		std::string Data;
		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + "U2Shaders\\" + File).c_str(), "rb") || F == nullptr)
		{
			Message("replace: %s not found", File.c_str());
			return nullptr;
		}
		char Buf[65536];
		size_t n;
		while ((n = fread(Buf, 1, sizeof(Buf), F)) > 0)
			Data.append(Buf, n);
		fclose(F);
		const DWORD *H = reinterpret_cast<const DWORD *>(Data.data());
		if (Data.size() < 128 || H[0] != 0x20534444 || H[1] != 124)
		{
			Message("replace: %s is not a DDS file", File.c_str());
			return nullptr;
		}
		const UINT Height = H[3], Width = H[4], Levels = (H[2] & 0x20000) && H[7] ? H[7] : 1;
		const DWORD PfFlags = H[20], FourCC = H[21], Bits = H[22], RMask = H[23], AMask = H[26];
		D3DFORMAT Fmt = D3DFMT_UNKNOWN;
		UINT BlockBytes = 0;          // DXT: bytes per 4x4 block; else 0
		if ((PfFlags & 0x4) && (FourCC == D3DFMT_DXT1 || FourCC == D3DFMT_DXT3 || FourCC == D3DFMT_DXT5))
		{
			Fmt = (D3DFORMAT)FourCC;
			BlockBytes = FourCC == D3DFMT_DXT1 ? 8 : 16;
		}
		else if ((PfFlags & 0x40) && Bits == 32 && RMask == 0xFF0000)
			Fmt = (PfFlags & 0x1) && AMask ? D3DFMT_A8R8G8B8 : D3DFMT_X8R8G8B8;
		if (Fmt == D3DFMT_UNKNOWN || Width == 0 || Height == 0)
		{
			Message("replace: %s: unsupported format (use 32-bit BGRA or DXT1/3/5)", File.c_str());
			return nullptr;
		}
		IDirect3DTexture9 *T = nullptr;
		if (FAILED(Dev->CreateTexture(Width, Height, Levels, 0, Fmt, D3DPOOL_MANAGED, &T, nullptr)))
		{
			Message("replace: %s: CreateTexture %ux%u failed", File.c_str(), Width, Height);
			return nullptr;
		}
		size_t At = 128;
		for (UINT L = 0; L < Levels; L++)
		{
			const UINT W = (std::max)(1u, Width >> L), Hh = (std::max)(1u, Height >> L);
			const UINT Rows = BlockBytes ? (std::max)(1u, (Hh + 3) / 4) : Hh;
			const UINT RowBytes = BlockBytes ? (std::max)(1u, (W + 3) / 4) * BlockBytes : W * 4;
			D3DLOCKED_RECT Lock;
			if (At + (size_t)Rows * RowBytes > Data.size() || FAILED(T->LockRect(L, &Lock, nullptr, 0)))
			{
				Message("replace: %s: file ends early (level %u)", File.c_str(), L);
				T->Release();
				return nullptr;
			}
			for (UINT y = 0; y < Rows; y++)
				memcpy(static_cast<BYTE *>(Lock.pBits) + y * Lock.Pitch, Data.data() + At + (size_t)y * RowBytes, RowBytes);
			T->UnlockRect(L);
			At += (size_t)Rows * RowBytes;
		}
		return T;
	}

	// Called before a draw. Hash = the stage 0 texture's hash (0: not yet known, read it from
	// Tex). Returns true if a shader was put in place; End() must then follow the draw.
	bool Begin(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, DWORD &Hash, bool FixedFunction)
	{
		if (!Loaded)
			Load();
		if (Tex == nullptr || (!Log && Rules.empty() && !CharProbe && !CharLight))
			return false;

		Known(Tex, Hash);
		if (Hash == 0xFFFFFFFF)
		{
			if (Log)
				LogUnreadableDraw(Dev, Tex);   // render targets (e.g. shadow maps): note how they're drawn
			return false;
		}
		if (CharProbe)
			ProbeDraw(Dev, Tex, Hash, FixedFunction);

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
			return CharLight ? CharBegin(Dev, FixedFunction) : false;
		if (Rule->Surface)
			return SurfaceBegin(Dev, *Rule, FixedFunction);
		// only the see-through parts: an atlas is often shared with solid ones
		DWORD Blending = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blending);
		if (!Blending)
			return false;
		IDirect3DPixelShader9 *PS = Compile(Dev, *Rule);
		if (PS == nullptr)
			return false;

		if (!Rule->KeepBlend)
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
		bool Projected = false;
		if (FixedFunction)
		{
			// raw texture coordinates on stage 0 (no panning): the shader animates itself.
			// Projector draws (decals) keep their transform: it is the projection itself,
			// and the shader divides by z (c1.x = 1), as pixel shaders ignore PROJECTED
			Dev->GetTextureStageState(0, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF[0]);
			Projected = (OldTTF[0] & D3DTTFF_PROJECTED) != 0;
			if (!Projected)
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
		Const[1][0] = Projected ? 1.0f : 0.0f;
		D3DMATRIX Proj;
		Dev->GetTransform(D3DTS_PROJECTION, &Proj);
		for (int r = 0; r < 4; r++)
			for (int c = 0; c < 4; c++)
				Const[4 + r][c] = Proj.m[r][c];
		Dev->SetPixelShaderConstantF(0, Const[0], 8);
		if (!Rule->KeepBlend)
		{
			Dev->SetTexture(1, SceneTex);
			Dev->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
		}
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
	// unit of gap, max radius; UV units). shadowtint=R G B goes to c5: how strongly the
	// projector darkens each channel (1 1 1 = the engine's grey; lower blue = bluer shadows).
	bool Pcss = false;
	U2Rule MapRule, ProjRule;
	float PcssParams[4] = { 0.05f, 0.004f, 0.0006f, 0.06f };
	float ShadowTint[4] = { 1, 1, 1, 1 };   // w = 1 tells pcss_proj.hlsl the tint is set
	float PcssDebug = 0;          // pcssdebug=1: colour the shadows by the measured gap
	int Mode = 0;                 // what End() undoes: 1 surface shader, 2 shadow map, 3 projector, 5 solid surface
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
		if (proj)
			Dev->SetPixelShaderConstantF(5, ShadowTint, 1);   // restored with c0-c7 in End()
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

	// surface=: a solid world surface drawn with parallax (world_parallax.hlsl). A pixel shader
	// replaces all the texture stages, so the shader redoes what they did; only the usual setups
	// are taken (stage 0: the texture, alone or times the vertex colour; stage 1: nothing, or a
	// second texture such as the lightmap times the result), as c2 = (vertex colour factor,
	// stage 1 factor; 0 = not used). Anything else is drawn as before and noted once in the log.
	// Stages 0 and 1 keep their own coordinates and transforms (panning, the lightmap's
	// mapping); stage 2's coordinates carry the camera-space position (TEXCOORD2).
	static float ModulateFactor(DWORD Op)
	{
		return Op == D3DTOP_MODULATE ? 1.0f : Op == D3DTOP_MODULATE2X ? 2.0f : Op == D3DTOP_MODULATE4X ? 4.0f : 0.0f;
	}
	static bool ArgsAre(DWORD A1, DWORD A2, DWORD X, DWORD Y)
	{
		return (A1 == X && A2 == Y) || (A1 == Y && A2 == X);   // no modifiers (complement, alpha replicate)
	}
	// The brightness a surface's texture mostly has (its median: taken as the surface itself) and
	// its darkest few percent (the bottom of its gaps), so world_parallax.hlsl needs no tuning per
	// texture. Read once from the top mip: 32-bit textures per pixel, DXT per block (the mean of
	// its two end colours). Other formats: false, and the shader uses its own settings.
	bool TextureLevels(IDirect3DTexture9 *Tex, float &Flat, float &Deep)
	{
		D3DSURFACE_DESC Desc;
		D3DLOCKED_RECT Lock;
		if (FAILED(Tex->GetLevelDesc(0, &Desc)))
			return false;
		const bool Dxt1 = Desc.Format == D3DFMT_DXT1;
		const bool Dxt = Dxt1 || Desc.Format == D3DFMT_DXT2 || Desc.Format == D3DFMT_DXT3 || Desc.Format == D3DFMT_DXT4 || Desc.Format == D3DFMT_DXT5;
		if (!(Desc.Format == D3DFMT_A8R8G8B8 || Desc.Format == D3DFMT_X8R8G8B8 || Dxt) || FAILED(Tex->LockRect(0, &Lock, nullptr, D3DLOCK_READONLY)))
			return false;
		unsigned Hist[256] = {}, Count = 0;
		auto Add = [&](unsigned r, unsigned g, unsigned b) { Hist[(r * 77 + g * 151 + b * 29) >> 8]++; Count++; };
		const BYTE *Bits = static_cast<const BYTE *>(Lock.pBits);
		if (Dxt)
		{
			const UINT Bw = (std::max)(1u, Desc.Width / 4), Bh = (std::max)(1u, Desc.Height / 4), Size = Dxt1 ? 8 : 16;
			for (UINT y = 0; y < Bh; y++)
				for (UINT x = 0; x < Bw; x++)
				{
					const BYTE *B = Bits + y * Lock.Pitch + x * Size + (Dxt1 ? 0 : 8);
					const unsigned c0 = B[0] | (B[1] << 8), c1 = B[2] | (B[3] << 8);
					Add((((c0 >> 11) & 31) + ((c1 >> 11) & 31)) * 255 / 62, (((c0 >> 5) & 63) + ((c1 >> 5) & 63)) * 255 / 126,
						((c0 & 31) + (c1 & 31)) * 255 / 62);
				}
		}
		else
			for (UINT y = 0; y < Desc.Height; y++)
				for (UINT x = 0; x < Desc.Width; x++)
				{
					const BYTE *P = Bits + y * Lock.Pitch + x * 4;
					Add(P[2], P[1], P[0]);
				}
		Tex->UnlockRect(0);
		if (Count == 0)
			return false;
		int DeepAt = -1, FlatAt = -1;
		for (unsigned i = 0, Sum = 0; i < 256; i++)
		{
			Sum += Hist[i];
			if (DeepAt < 0 && Sum * 100 >= Count * 4)
				DeepAt = i;
			if (FlatAt < 0 && Sum * 2 >= Count)
				FlatAt = i;
		}
		// a low-contrast texture gets little depth, not its small differences stretched to full depth
		Flat = (FlatAt + 0.5f) / 255;
		Deep = (std::min)((DeepAt + 0.5f) / 255, Flat - 0.15f);
		return true;
	}

	bool SurfaceBegin(IDirect3DDevice9 *Dev, U2Rule &R, bool FixedFunction)
	{
		DWORD Blending = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blending);
		if (Blending || !FixedFunction || Offscreen(Dev))
			return false;
		DWORD op[3] = {}, a1[3] = {}, a2[3] = {};
		for (DWORD st = 0; st < 3; st++)
		{
			Dev->GetTextureStageState(st, D3DTSS_COLOROP, &op[st]);
			Dev->GetTextureStageState(st, D3DTSS_COLORARG1, &a1[st]);
			Dev->GetTextureStageState(st, D3DTSS_COLORARG2, &a2[st]);
		}
		float Vert = -1, Second = -1;
		if (op[0] == D3DTOP_SELECTARG1 && a1[0] == D3DTA_TEXTURE)
			Vert = 0;
		else if (ModulateFactor(op[0]) > 0 && (ArgsAre(a1[0], a2[0], D3DTA_TEXTURE, D3DTA_DIFFUSE) || ArgsAre(a1[0], a2[0], D3DTA_TEXTURE, D3DTA_CURRENT)))
			Vert = ModulateFactor(op[0]);    // on stage 0, CURRENT is the vertex colour
		if (op[1] == D3DTOP_DISABLE)
			Second = 0;
		else if (ModulateFactor(op[1]) > 0 && ArgsAre(a1[1], a2[1], D3DTA_TEXTURE, D3DTA_CURRENT) && op[2] == D3DTOP_DISABLE)
			Second = ModulateFactor(op[1]);
		if (Vert < 0 || Second < 0)
		{
			if (!R.Refused)
				Message("surface %08x: stage setup not supported, drawn as before (st0 op %u %x %x | st1 op %u %x %x | st2 op %u)",
					R.Hash, op[0], a1[0], a2[0], op[1], a1[1], a2[1], op[2]);
			R.Refused = true;
			return false;
		}
		const bool First = !R.Tried;
		IDirect3DPixelShader9 *PS = Compile(Dev, R);
		if (PS == nullptr)
			return false;
		if (First)
		{
			IDirect3DTexture9 *Tex = nullptr;
			if (SUCCEEDED(Dev->GetTexture(0, reinterpret_cast<IDirect3DBaseTexture9 **>(&Tex))) && Tex != nullptr)
			{
				if (TextureLevels(Tex, R.Levels[0], R.Levels[1]))
				{
					R.Levels[3] = 1;
					Message("surface %08x: brightness levels %.2f (surface) %.2f (deepest)", R.Hash, R.Levels[0], R.Levels[1]);
				}
				else
					Message("surface %08x: texture format not read, using the shader's own levels", R.Hash);
				Tex->Release();
			}
		}

		Dev->GetPixelShader(&OldPS);
		Dev->GetPixelShaderConstantF(0, OldConst[0], 8);
		static const D3DMATRIX Identity = { 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 };
		Dev->GetTextureStageState(2, D3DTSS_TEXCOORDINDEX, &OldTCI[2]);
		Dev->GetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, &OldTTF[2]);
		Dev->GetTransform(D3DTS_TEXTURE2, &OldTexMat[2]);
		Dev->SetTextureStageState(2, D3DTSS_TEXCOORDINDEX, D3DTSS_TCI_CAMERASPACEPOSITION | 2);
		Dev->SetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_COUNT3);
		Dev->SetTransform(D3DTS_TEXTURE2, &Identity);

		float Const[4][4] = {};
		Const[0][0] = (GetTickCount() % 3600000) / 1000.0f;
		Const[0][1] = 1;
		Const[0][2] = SceneW ? 1.0f / SceneW : 0;
		Const[0][3] = SceneH ? 1.0f / SceneH : 0;
		Const[2][0] = Vert;
		Const[2][1] = Second;
		memcpy(Const[3], R.Levels, sizeof(R.Levels));
		Dev->SetPixelShaderConstantF(0, Const[0], 4);
		Dev->SetPixelShader(PS);
		Mode = 5;
		return true;
	}

	// charlight=1: a solid, fixed-function, lit draw (characters, weapons, pickups: the level
	// itself is lightmapped or vertex-coloured, unlit) gets its lighting per pixel from the same
	// D3D lights, in char_light.hlsl. Taken only when the shader can redo what the stages did:
	// stage 0 = texture x lit colour (x1/2/4), stage 1 off, material colours from the material
	// (not the vertices). Anything else is drawn as before and its setup logged once.
	// Constants: c2 (stage 0 factor, light count), c3 ambient + emissive, c4 world up in view
	// space, c8.. 4 per light (up to 4), in view space:
	//   position xyz, type (1 point, 2 spot, 3 directional) | direction xyz, cos(phi / 2)
	//   colour (light x material diffuse) rgb, range | attenuation 0, 1, 2, cos(theta / 2)
	// Stage 1 and 2 coordinates carry the camera-space normal and position (TEXCOORD1/2).
	bool CharBegin(IDirect3DDevice9 *Dev, bool FixedFunction)
	{
		DWORD Blending = 0, Lighting = 0, DiffSrc = 0, AmbSrc = 0, ColorVertex = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blending);
		Dev->GetRenderState(D3DRS_LIGHTING, &Lighting);
		if (Blending || !Lighting || !FixedFunction || Offscreen(Dev))
			return false;
		Dev->GetRenderState(D3DRS_COLORVERTEX, &ColorVertex);
		Dev->GetRenderState(D3DRS_DIFFUSEMATERIALSOURCE, &DiffSrc);
		Dev->GetRenderState(D3DRS_AMBIENTMATERIALSOURCE, &AmbSrc);
		DWORD op[2] = {}, a1 = 0, a2 = 0, Fvf = 0;
		Dev->GetTextureStageState(0, D3DTSS_COLOROP, &op[0]);
		Dev->GetTextureStageState(0, D3DTSS_COLORARG1, &a1);
		Dev->GetTextureStageState(0, D3DTSS_COLORARG2, &a2);
		Dev->GetTextureStageState(1, D3DTSS_COLOROP, &op[1]);
		Dev->GetFVF(&Fvf);
		const bool VertexColours = ColorVertex && (Fvf & D3DFVF_DIFFUSE) && (DiffSrc != D3DMCS_MATERIAL || AmbSrc != D3DMCS_MATERIAL);
		const float Factor = ModulateFactor(op[0]);
		if (Factor == 0 || !(ArgsAre(a1, a2, D3DTA_TEXTURE, D3DTA_DIFFUSE) || ArgsAre(a1, a2, D3DTA_TEXTURE, D3DTA_CURRENT))
			|| op[1] != D3DTOP_DISABLE || VertexColours)
		{
			char Key[160];
			sprintf_s(Key, "st0 op %u %x %x | st1 op %u | vertex colours as material %d", op[0], a1, a2, op[1], (int)VertexColours);
			if (!CharRefused[Key])
				Message("charlight: setup not supported, drawn as before (%s)", Key);
			CharRefused[Key] = true;
			return false;
		}
		IDirect3DPixelShader9 *PS = Compile(Dev, CharRule);
		if (PS == nullptr)
			return false;

		float C[24][4] = {};
		D3DMATERIAL9 M = {};
		Dev->GetMaterial(&M);
		D3DMATRIX V;
		Dev->GetTransform(D3DTS_VIEW, &V);
		auto Point = [&](const D3DVECTOR &p, float *out) {
			for (int c = 0; c < 3; c++)
				out[c] = p.x * V.m[0][c] + p.y * V.m[1][c] + p.z * V.m[2][c] + V.m[3][c];
		};
		auto Dir = [&](const D3DVECTOR &d, float *out) {
			for (int c = 0; c < 3; c++)
				out[c] = d.x * V.m[0][c] + d.y * V.m[1][c] + d.z * V.m[2][c];
			const float l = sqrtf(out[0] * out[0] + out[1] * out[1] + out[2] * out[2]);
			if (l > 0) for (int c = 0; c < 3; c++) out[c] /= l;
		};
		DWORD Amb = 0;
		Dev->GetRenderState(D3DRS_AMBIENT, &Amb);
		float AmbR = ((Amb >> 16) & 0xFF) / 255.0f, AmbG = ((Amb >> 8) & 0xFF) / 255.0f, AmbB = (Amb & 0xFF) / 255.0f;
		int Count = 0;
		for (DWORD i = 0; i < 8; i++)
		{
			BOOL On = FALSE;
			D3DLIGHT9 L = {};
			if (FAILED(Dev->GetLightEnable(i, &On)) || !On || FAILED(Dev->GetLight(i, &L)))
				continue;
			AmbR += L.Ambient.r; AmbG += L.Ambient.g; AmbB += L.Ambient.b;   // lights' ambient adds up, as in D3D
			if (Count == 4)
				continue;                  // more than 4: their ambient still counts, their light not
			float *P = C[8 + Count * 4];
			Point(L.Position, P);
			P[3] = (float)L.Type;
			Dir(L.Direction, C[9 + Count * 4]);
			C[9 + Count * 4][3] = cosf(L.Phi * 0.5f);
			C[10 + Count * 4][0] = L.Diffuse.r * M.Diffuse.r;
			C[10 + Count * 4][1] = L.Diffuse.g * M.Diffuse.g;
			C[10 + Count * 4][2] = L.Diffuse.b * M.Diffuse.b;
			C[10 + Count * 4][3] = L.Type == D3DLIGHT_DIRECTIONAL ? 1e30f : L.Range;
			C[11 + Count * 4][0] = L.Attenuation0;
			C[11 + Count * 4][1] = L.Attenuation1;
			C[11 + Count * 4][2] = L.Attenuation2;
			C[11 + Count * 4][3] = cosf(L.Theta * 0.5f);
			Count++;
		}
		C[0][0] = (GetTickCount() % 3600000) / 1000.0f;
		C[0][1] = 1;
		C[2][0] = Factor;
		C[2][1] = (float)Count;
		C[3][0] = AmbR * M.Ambient.r + M.Emissive.r;
		C[3][1] = AmbG * M.Ambient.g + M.Emissive.g;
		C[3][2] = AmbB * M.Ambient.b + M.Emissive.b;
		const D3DVECTOR Up = { 0, 0, 1 };      // Unreal's up (Z) in the world space the game draws in
		Dir(Up, C[4]);

		Dev->GetPixelShader(&OldPS);
		Dev->GetPixelShaderConstantF(0, OldCharConst[0], 24);
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
		Dev->SetPixelShaderConstantF(0, C[0], 24);
		Dev->SetPixelShader(PS);
		Mode = 6;
		return true;
	}

	void End(IDirect3DDevice9 *Dev)
	{
		if (Mode == 6)
		{
			Dev->SetPixelShader(OldPS);
			Dev->SetPixelShaderConstantF(0, OldCharConst[0], 24);
			for (DWORD s = 1; s <= 2; s++)
			{
				Dev->SetTextureStageState(s, D3DTSS_TEXCOORDINDEX, OldTCI[s]);
				Dev->SetTextureStageState(s, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF[s]);
				Dev->SetTransform((D3DTRANSFORMSTATETYPE)(D3DTS_TEXTURE0 + s), &OldTexMat[s]);
			}
			if (OldPS != nullptr) { OldPS->Release(); OldPS = nullptr; }
			Mode = 0;
			return;
		}
		if (Mode == 5)
		{
			Dev->SetPixelShader(OldPS);
			Dev->SetPixelShaderConstantF(0, OldConst[0], 8);
			Dev->SetTextureStageState(2, D3DTSS_TEXCOORDINDEX, OldTCI[2]);
			Dev->SetTextureStageState(2, D3DTSS_TEXTURETRANSFORMFLAGS, OldTTF[2]);
			Dev->SetTransform(D3DTS_TEXTURE2, &OldTexMat[2]);
			if (OldPS != nullptr) { OldPS->Release(); OldPS = nullptr; }
			Mode = 0;
			return;
		}
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

	// ---- post-processing (post=1) ----------------------------------------------------------
	// Bloom, sharpening and colour grading on the finished 3D frame, before the HUD is drawn
	// over it: run just before the first 2D draw (pre-transformed vertices or an orthographic
	// projection) into the back buffer of a frame that drew 3D, or at Present if no 2D came.
	// Frames with no 3D (menus) are left alone. Every device state touched is restored (a state
	// block, plus the render target and depth buffer, which state blocks don't cover).
	bool Post = false;
	float PostSplit = 0;                                 // postsplit=1: right half untouched
	float PostBloom[4] = { 0.75f, 0.5f, 0, 0 };          // threshold, intensity
	float PostGrade[4] = { 1.05f, 1.05f, 1.0f, 0.25f };  // saturation, contrast, exposure, vignette
	float PostBalance[4] = { 1, 1, 1, 0.25f };           // colour balance r g b, sharpen
	U2Rule PostBright, PostBlur, PostFinal;
	IDirect3DTexture9 *BloomA = nullptr, *BloomB = nullptr;
	UINT BloomW = 0, BloomH = 0;
	IDirect3DStateBlock9 *PostState = nullptr;
	IDirect3DDevice9 *LastDev = nullptr;
	bool Saw3D = false, PostDone = false;
	int PostTrace = 0;                                   // posttrace=N: log the draw order of N frames
	std::string PostTraceLine;

	void PostCheck(IDirect3DDevice9 *Dev)
	{
		if (!Post || PostDone)
			return;
		LastDev = Dev;
		if (Offscreen(Dev))
			return;
		DWORD fvf = 0;
		Dev->GetFVF(&fvf);
		IDirect3DVertexShader9 *VS = nullptr;
		Dev->GetVertexShader(&VS);
		const bool programmable = VS != nullptr;
		if (VS) VS->Release();
		D3DMATRIX P = {};
		Dev->GetTransform(D3DTS_PROJECTION, &P);
		const bool rhw = (fvf & D3DFVF_POSITION_MASK) == D3DFVF_XYZRHW;
		const bool ortho = !programmable && !rhw && P._34 == 0.0f && P._44 == 1.0f;
		// the HUD draws without depth testing; orthographic draws that still test depth are part
		// of the scene (in third person one came mid-frame: the post ran too early and covered
		// the rest of the frame with a half-drawn copy)
		DWORD zenable = 0, zwrite = 0, zfunc = 0, blend = 0;
		Dev->GetRenderState(D3DRS_ZENABLE, &zenable);
		Dev->GetRenderState(D3DRS_ZWRITEENABLE, &zwrite);
		Dev->GetRenderState(D3DRS_ZFUNC, &zfunc);
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend);
		if (PostTrace > 0)
		{
			char item[64];
			if (!rhw && !ortho)
				snprintf(item, sizeof(item), zenable ? "3 " : "h(w%lu b%lu p%.2f) ", zwrite, blend, P._43);
			else
			{
				D3DVIEWPORT9 vp = {};
				Dev->GetViewport(&vp);
				snprintf(item, sizeof(item), "%s(z%lu w%lu f%lu b%lu vp%lux%lu) ", rhw ? "R" : "O", zenable, zwrite, zfunc, blend, vp.Width, vp.Height);
			}
			if (PostTraceLine.size() < 3500) PostTraceLine += item;
		}
		if (!rhw && !ortho)
		{
			Saw3D = true;
			return;
		}
		if (PostTrace > 0)
			return;                           // tracing: just record the frame
		if (!Saw3D)
			return;
		static int told = 0;
		if (told++ < 6)
			Message("post: applied before a 2D draw (fvf %x, pre-transformed %d, orthographic %d)", (unsigned)fvf, (int)rhw, (int)ortho);
		RunPost(Dev);
	}

	struct U2QuadVertex { float x, y, z, rhw, u, v; };
	static void Quad(IDirect3DDevice9 *Dev, UINT W, UINT H)
	{
		// half-pixel offset: Direct3D 9 pixel centres sit on integer coordinates
		const float w = W - 0.5f, h = H - 0.5f;
		const U2QuadVertex q[4] = { { -0.5f, -0.5f, 0, 1, 0, 0 }, { w, -0.5f, 0, 1, 1, 0 }, { -0.5f, h, 0, 1, 0, 1 }, { w, h, 0, 1, 1, 1 } };
		Dev->SetFVF(D3DFVF_XYZRHW | D3DFVF_TEX1);
		Dev->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, q, sizeof(U2QuadVertex));
	}

	static void Target(IDirect3DDevice9 *Dev, IDirect3DTexture9 *T)
	{
		IDirect3DSurface9 *S = nullptr;
		if (SUCCEEDED(T->GetSurfaceLevel(0, &S)) && S)
		{
			Dev->SetRenderTarget(0, S);
			S->Release();
		}
	}

	void RunPost(IDirect3DDevice9 *Dev)
	{
		PostDone = true;
		IDirect3DPixelShader9 *Bright = Compile(Dev, PostBright), *Blur = Compile(Dev, PostBlur), *Final = Compile(Dev, PostFinal);
		if (Bright == nullptr || Blur == nullptr || Final == nullptr)
		{
			Message("post: a shader failed to compile, post-processing off");
			Post = false;
			return;
		}
		if (PostState == nullptr && FAILED(Dev->CreateStateBlock(D3DSBT_ALL, &PostState)))
		{
			PostState = nullptr;
			return;
		}
		PostState->Capture();
		IDirect3DSurface9 *OldRT = nullptr, *OldDS = nullptr;
		Dev->GetRenderTarget(0, &OldRT);
		Dev->GetDepthStencilSurface(&OldDS);
		// the game's vertex input, put back by hand: our quads are drawn with DrawPrimitiveUP,
		// which clears stream 0, and state blocks (at least through dgVoodoo) don't bring
		// streams back. Without this the HUD draw that follows used our full-screen quad:
		// the HUD texture sheet filled the screen (tested 2026-10-01 on the PC).
		IDirect3DVertexBuffer9 *OldVB[2] = {};
		UINT OldOffset[2] = {}, OldStride[2] = {};
		for (UINT s = 0; s < 2; s++)
			Dev->GetStreamSource(s, &OldVB[s], &OldOffset[s], &OldStride[s]);
		IDirect3DIndexBuffer9 *OldIB = nullptr;
		Dev->GetIndices(&OldIB);
		IDirect3DVertexDeclaration9 *OldDecl = nullptr;
		Dev->GetVertexDeclaration(&OldDecl);
		DWORD OldFVF = 0;
		Dev->GetFVF(&OldFVF);
		// textures, sampler states and shaders too: the state block doesn't restore them
		// either (the HUD's first draw came out with the bloom texture)
		IDirect3DBaseTexture9 *OldTex[4] = {};
		static const D3DSAMPLERSTATETYPE Samp[] = { D3DSAMP_ADDRESSU, D3DSAMP_ADDRESSV, D3DSAMP_MAGFILTER,
			D3DSAMP_MINFILTER, D3DSAMP_MIPFILTER, D3DSAMP_SRGBTEXTURE };
		static const D3DTEXTURESTAGESTATETYPE Stage[] = { D3DTSS_TEXCOORDINDEX, D3DTSS_TEXTURETRANSFORMFLAGS };
		DWORD OldSamp[2][6] = {}, OldStage[2][2] = {};
		for (DWORD t = 0; t < 4; t++)
			Dev->GetTexture(t, &OldTex[t]);
		for (DWORD t = 0; t < 2; t++)
		{
			for (int i = 0; i < 6; i++) Dev->GetSamplerState(t, Samp[i], &OldSamp[t][i]);
			for (int i = 0; i < 2; i++) Dev->GetTextureStageState(t, Stage[i], &OldStage[t][i]);
		}
		IDirect3DPixelShader9 *OldPS = nullptr;
		Dev->GetPixelShader(&OldPS);
		IDirect3DVertexShader9 *OldVS = nullptr;
		Dev->GetVertexShader(&OldVS);

		CopyScene(Dev, true);
		const UINT W = (std::max)(SceneW / 4, 1u), H = (std::max)(SceneH / 4, 1u);
		if (BloomA != nullptr && (BloomW != W || BloomH != H))
		{
			BloomA->Release(); BloomA = nullptr;
			if (BloomB) { BloomB->Release(); BloomB = nullptr; }
		}
		if (BloomA == nullptr)
		{
			BloomW = W; BloomH = H;
			if (FAILED(Dev->CreateTexture(W, H, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &BloomA, nullptr)))
				BloomA = nullptr;
			if (FAILED(Dev->CreateTexture(W, H, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &BloomB, nullptr)))
				BloomB = nullptr;
		}
		if (SceneTex != nullptr && BloomA != nullptr && BloomB != nullptr && OldRT != nullptr)
		{
			static const D3DRENDERSTATETYPE Off[] = { D3DRS_ZENABLE, D3DRS_ZWRITEENABLE, D3DRS_ALPHABLENDENABLE, D3DRS_ALPHATESTENABLE,
				D3DRS_FOGENABLE, D3DRS_STENCILENABLE, D3DRS_SCISSORTESTENABLE, D3DRS_LIGHTING, D3DRS_SRGBWRITEENABLE, D3DRS_CLIPPLANEENABLE };
			for (D3DRENDERSTATETYPE R : Off)
				Dev->SetRenderState(R, FALSE);
			Dev->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
			Dev->SetRenderState(D3DRS_COLORWRITEENABLE, 0xF);
			Dev->SetDepthStencilSurface(nullptr);
			Dev->SetVertexShader(nullptr);
			for (DWORD s = 0; s < 2; s++)
			{
				Dev->SetSamplerState(s, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
				Dev->SetSamplerState(s, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
				Dev->SetSamplerState(s, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
				Dev->SetSamplerState(s, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
				Dev->SetSamplerState(s, D3DSAMP_MIPFILTER, D3DTEXF_NONE);
				Dev->SetSamplerState(s, D3DSAMP_SRGBTEXTURE, FALSE);
				Dev->SetTextureStageState(s, D3DTSS_TEXCOORDINDEX, 0);
				Dev->SetTextureStageState(s, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
			}
			Dev->SetTexture(1, nullptr);

			// 1: the bright parts, quarter size
			float c[4][4] = {};
			c[0][0] = 1.0f / SceneW; c[0][1] = 1.0f / SceneH; c[0][2] = PostSplit;
			memcpy(c[1], PostBloom, sizeof(PostBloom));
			memcpy(c[2], PostGrade, sizeof(PostGrade));
			memcpy(c[3], PostBalance, sizeof(PostBalance));
			Target(Dev, BloomA);
			Dev->SetTexture(0, SceneTex);
			Dev->SetPixelShader(Bright);
			Dev->SetPixelShaderConstantF(0, c[0], 4);
			Quad(Dev, W, H);

			// 2: blurred, across then down, twice
			Dev->SetPixelShader(Blur);
			for (int round = 0; round < 2; round++)
			{
				const float across[4] = { 1.0f / W, 0, 0, 0 }, down[4] = { 0, 1.0f / H, 0, 0 };
				Target(Dev, BloomB);
				Dev->SetTexture(0, BloomA);
				Dev->SetPixelShaderConstantF(0, across, 1);
				Quad(Dev, W, H);
				Target(Dev, BloomA);
				Dev->SetTexture(0, BloomB);
				Dev->SetPixelShaderConstantF(0, down, 1);
				Quad(Dev, W, H);
			}

			// 3: the finished frame back into the game's own target
			Dev->SetRenderTarget(0, OldRT);
			Dev->SetTexture(0, SceneTex);
			Dev->SetTexture(1, BloomA);
			Dev->SetPixelShader(Final);
			Dev->SetPixelShaderConstantF(0, c[0], 4);
			Quad(Dev, SceneW, SceneH);
		}

		Dev->SetRenderTarget(0, OldRT);
		Dev->SetDepthStencilSurface(OldDS);
		PostState->Apply();               // after SetRenderTarget, which resets the viewport
		if (OldDecl)
			Dev->SetVertexDeclaration(OldDecl);
		else
			Dev->SetFVF(OldFVF);
		for (UINT s = 0; s < 2; s++)
		{
			Dev->SetStreamSource(s, OldVB[s], OldOffset[s], OldStride[s]);
			if (OldVB[s]) OldVB[s]->Release();
		}
		Dev->SetIndices(OldIB);
		if (OldIB) OldIB->Release();
		for (DWORD t = 0; t < 4; t++)
		{
			Dev->SetTexture(t, OldTex[t]);
			if (OldTex[t]) OldTex[t]->Release();
		}
		for (DWORD t = 0; t < 2; t++)
		{
			for (int i = 0; i < 6; i++) Dev->SetSamplerState(t, Samp[i], OldSamp[t][i]);
			for (int i = 0; i < 2; i++) Dev->SetTextureStageState(t, Stage[i], OldStage[t][i]);
		}
		Dev->SetPixelShader(OldPS);
		if (OldPS) OldPS->Release();
		Dev->SetVertexShader(OldVS);
		if (OldVS) OldVS->Release();
		if (OldDecl) OldDecl->Release();
		if (OldRT) OldRT->Release();
		if (OldDS) OldDS->Release();
	}

	void PostRelease()
	{
		if (BloomA) { BloomA->Release(); BloomA = nullptr; }
		if (BloomB) { BloomB->Release(); BloomB = nullptr; }
		if (PostState) { PostState->Release(); PostState = nullptr; }
	}

	// ---- character probe (charprobe=1) -----------------------------------------------------
	// Character skins are opaque, so the per-surface rules above never see them. Before any
	// character lighting or self-shadowing work, this records how each opaque on-screen draw is
	// lit (fixed-function lighting, lights, material, ambient, skinning) and whether shadow
	// silhouettes were drawn earlier in the same frame. Written to U2Shaders\dump\chars.txt;
	// each texture is also saved once as <hash>_<w>x<h>.dds so a character's skin can be found.
	bool CharProbe = false;
	bool CharLight = false;

	// ---- lmcapture=1: the lightmapped geometry, for baking elsewhere ---------------------------
	// Every draw with a texture on stage 1 that stage 1 multiplies in (a lightmap) is recorded as
	// world-space triangles with their stage 1 (lightmap) coordinates, worked out the way
	// fixed-function Direct3D does (texture coordinate set or camera-space position, then the
	// texture transform). Triangles are kept once each, however often they are drawn. Every few
	// seconds the lot is written to U2Shaders\capture\scene.obj (one object per lightmap,
	// "o lm_<hash>"; one material per stage 0 texture, "usemtl tex_<hash>"; vt = lightmap
	// coordinates in Direct3D's convention, v down; faces in the order Direct3D shows as their
	// front) and lightmaps.txt ("<hash> <width> <height> <stage 1 op> <triangles>"); each
	// lightmap is saved once in U2Shaders\dump. The buffers' contents come from copies the
	// device keeps while capturing (vertex buffers may not be readable).
	bool Capture = false;
	struct U2LightmapCapture
	{
		UINT W = 0, H = 0;
		DWORD Op = 0;
		std::vector<float> Verts;    // x y z u v, 3 per triangle
		std::vector<DWORD> Tex;      // stage 0 hash, 1 per triangle
	};
	std::map<DWORD, U2LightmapCapture> Captured;
	std::unordered_set<unsigned long long> CapturedTris;
	bool CaptureDirty = false;
	unsigned CaptureWritten = 0;

	struct U2VertexLayout
	{
		int Pos = -1;                // byte offset of the float3 position, -1 = none (or pre-transformed)
		int Tex[8];                  // byte offset of each texture coordinate set, -1 = none
		int TexComps[8];
		U2VertexLayout() { for (int i = 0; i < 8; i++) { Tex[i] = -1; TexComps[i] = 0; } }
	};

	static U2VertexLayout LayoutOf(IDirect3DDevice9 *Dev)
	{
		U2VertexLayout L;
		IDirect3DVertexDeclaration9 *Decl = nullptr;
		if (SUCCEEDED(Dev->GetVertexDeclaration(&Decl)) && Decl != nullptr)
		{
			D3DVERTEXELEMENT9 E[MAXD3DDECLLENGTH + 1];
			UINT N = MAXD3DDECLLENGTH + 1;
			if (SUCCEEDED(Decl->GetDeclaration(E, &N)))
				for (UINT i = 0; i < N && E[i].Stream != 0xFF; i++)
				{
					if (E[i].Stream != 0)
						continue;
					if (E[i].Usage == D3DDECLUSAGE_POSITION && E[i].UsageIndex == 0 && E[i].Type == D3DDECLTYPE_FLOAT3)
						L.Pos = E[i].Offset;
					else if (E[i].Usage == D3DDECLUSAGE_TEXCOORD && E[i].UsageIndex < 8 && E[i].Type <= D3DDECLTYPE_FLOAT4)
					{
						L.Tex[E[i].UsageIndex] = E[i].Offset;
						L.TexComps[E[i].UsageIndex] = E[i].Type + 1;   // FLOAT1..FLOAT4 are 0..3
					}
				}
			Decl->Release();
			return L;
		}
		DWORD Fvf = 0;
		Dev->GetFVF(&Fvf);
		if ((Fvf & D3DFVF_POSITION_MASK) != D3DFVF_XYZ)
			return L;                   // pre-transformed or blended: not captured
		int At = 12;
		L.Pos = 0;
		if (Fvf & D3DFVF_NORMAL) At += 12;
		if (Fvf & D3DFVF_PSIZE) At += 4;
		if (Fvf & D3DFVF_DIFFUSE) At += 4;
		if (Fvf & D3DFVF_SPECULAR) At += 4;
		const int Count = (Fvf & D3DFVF_TEXCOUNT_MASK) >> D3DFVF_TEXCOUNT_SHIFT;
		for (int i = 0; i < Count && i < 8; i++)
		{
			static const int Comps[4] = { 2, 3, 4, 1 };   // D3DFVF_TEXTUREFORMAT2/3/4/1
			L.Tex[i] = At;
			L.TexComps[i] = Comps[(Fvf >> (16 + i * 2)) & 3];
			At += L.TexComps[i] * 4;
		}
		return L;
	}

	void CaptureDraw(IDirect3DDevice9 *Dev, D3DPRIMITIVETYPE Type, UINT PrimCount, const BYTE *Verts, size_t VertBytes, UINT Stride,
		INT BaseVertex, const BYTE *Indices, size_t IndexBytes, bool Index32, UINT StartIndex,
		IDirect3DTexture9 *Tex0, DWORD *Hash0, IDirect3DTexture9 *Tex1, DWORD &Hash1)
	{
		if (!Capture || Tex1 == nullptr || Stride == 0 || Offscreen(Dev))
			return;
		if (Type != D3DPT_TRIANGLELIST && Type != D3DPT_TRIANGLESTRIP && Type != D3DPT_TRIANGLEFAN)
			return;
		DWORD Op1 = 0, Blend = 0, Cull = 0;
		Dev->GetTextureStageState(1, D3DTSS_COLOROP, &Op1);
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &Blend);
		Dev->GetRenderState(D3DRS_CULLMODE, &Cull);
		IDirect3DVertexShader9 *VS = nullptr;
		Dev->GetVertexShader(&VS);
		if (VS != nullptr) { VS->Release(); return; }
		if (ModulateFactor(Op1) == 0 || Blend)
			return;
		const U2VertexLayout L = LayoutOf(Dev);
		if (L.Pos < 0)
			return;
		Known(Tex1, Hash1);
		if (Hash1 == 0xFFFFFFFF)
			return;
		DWORD H0 = 0;
		if (Tex0 != nullptr && Hash0 != nullptr)
		{
			Known(Tex0, *Hash0);
			H0 = *Hash0;
		}

		DWORD Tci = 0, Ttf = 0;
		Dev->GetTextureStageState(1, D3DTSS_TEXCOORDINDEX, &Tci);
		Dev->GetTextureStageState(1, D3DTSS_TEXTURETRANSFORMFLAGS, &Ttf);
		const DWORD Gen = Tci & 0xFFFF0000, Set = Tci & 0xFFFF;
		if ((Gen != D3DTSS_TCI_PASSTHRU && Gen != D3DTSS_TCI_CAMERASPACEPOSITION) || (Gen == D3DTSS_TCI_PASSTHRU && (Set >= 8 || L.Tex[Set] < 0)))
			return;
		D3DMATRIX W, V, T;
		Dev->GetTransform(D3DTS_WORLD, &W);
		Dev->GetTransform(D3DTS_VIEW, &V);
		Dev->GetTransform(D3DTS_TEXTURE1, &T);
		auto Mul = [](const float *In, const D3DMATRIX &M, float *Out) {
			for (int c = 0; c < 4; c++)
				Out[c] = In[0] * M.m[0][c] + In[1] * M.m[1][c] + In[2] * M.m[2][c] + In[3] * M.m[3][c];
		};

		U2LightmapCapture &C = Captured[Hash1];
		if (C.W == 0)
		{
			D3DSURFACE_DESC D = {};
			Tex1->GetLevelDesc(0, &D);
			C.W = D.Width; C.H = D.Height; C.Op = Op1;
			U2TexInfo Dummy;
			this->Hash(Tex1, Dummy, true);       // the lightmap itself, for comparing with the bake
		}

		// one vertex: world position and lightmap coordinates; false if out of the data
		auto Vertex = [&](UINT Index, float *Out) -> bool {
			const long long At = ((long long)BaseVertex + Index) * Stride;
			if (At < 0 || (size_t)At + Stride > VertBytes)
				return false;
			const BYTE *P = Verts + At;
			const float *Pos = reinterpret_cast<const float *>(P + L.Pos);
			const float Obj[4] = { Pos[0], Pos[1], Pos[2], 1 };
			float World[4], In[4] = { 0, 0, 0, 0 }, Uv[4];
			Mul(Obj, W, World);
			if (Gen == D3DTSS_TCI_CAMERASPACEPOSITION)
			{
				Mul(World, V, In);
				In[3] = 1;
			}
			else
			{
				const float *Tc = reinterpret_cast<const float *>(P + L.Tex[Set]);
				const int N = L.TexComps[Set];
				for (int c = 0; c < N; c++)
					In[c] = Tc[c];
				if (N < 4)
					In[N] = 1;                   // Direct3D pads (u, v) to (u, v, 1, 0) for the transform
			}
			const DWORD Count = Ttf & 0xFF;
			if (Count != D3DTTFF_DISABLE)
			{
				Mul(In, T, Uv);
				if ((Ttf & D3DTTFF_PROJECTED) && Count >= 2 && Uv[Count - 1] != 0)
				{
					Uv[0] /= Uv[Count - 1];
					Uv[1] /= Uv[Count - 1];
				}
			}
			else
			{
				Uv[0] = In[0]; Uv[1] = In[1];
			}
			Out[0] = World[0]; Out[1] = World[1]; Out[2] = World[2]; Out[3] = Uv[0]; Out[4] = Uv[1];
			return true;
		};
		auto IndexAt = [&](UINT k, UINT &Out) -> bool {
			if (Indices == nullptr) { Out = k; return true; }
			const size_t At = ((size_t)StartIndex + k) * (Index32 ? 4 : 2);
			if (At + (Index32 ? 4 : 2) > IndexBytes)
				return false;
			Out = Index32 ? *reinterpret_cast<const DWORD *>(Indices + At) : *reinterpret_cast<const WORD *>(Indices + At);
			return true;
		};

		for (UINT t = 0; t < PrimCount; t++)
		{
			UINT k[3];
			if (Type == D3DPT_TRIANGLELIST) { k[0] = t * 3; k[1] = t * 3 + 1; k[2] = t * 3 + 2; }
			else if (Type == D3DPT_TRIANGLESTRIP) { k[0] = t + (t & 1); k[1] = t + 1 - (t & 1); k[2] = t + 2; }
			else { k[0] = 0; k[1] = t + 1; k[2] = t + 2; }
			if (Cull == D3DCULL_CW)
				std::swap(k[1], k[2]);           // front faces are counter-clockwise here
			float Tri[15];
			UINT I;
			bool Ok = true;
			for (int c = 0; c < 3 && Ok; c++)
				Ok = IndexAt(k[c], I) && Vertex(I, Tri + c * 5);
			if (!Ok)
				return;
			unsigned long long Key = 1469598103934665603ull ^ Hash1;
			for (int c = 0; c < 15; c++)
			{
				const long long Q = (long long)floor(Tri[c] * (c % 5 < 3 ? 8.0f : 4096.0f) + 0.5f);
				Key = (Key ^ (unsigned long long)Q) * 1099511628211ull;
			}
			if (!CapturedTris.insert(Key).second)
				continue;
			C.Verts.insert(C.Verts.end(), Tri, Tri + 15);
			C.Tex.push_back(H0);
			CaptureDirty = true;
		}
	}

	void WriteCapture()
	{
		CaptureDirty = false;
		FILE *F = nullptr;
		if (fopen_s(&F, (Dir + "U2Shaders\\capture\\scene.obj").c_str(), "w") || F == nullptr)
			return;
		fprintf(F, "# U2Shaders lmcapture: world-space triangles of lightmapped draws (game units)\n");
		fprintf(F, "# vt = lightmap coordinates, Direct3D convention (v down); faces in Direct3D front-face order\n");
		unsigned N = 0, Tris = 0;
		for (const auto &It : Captured)
		{
			const U2LightmapCapture &C = It.second;
			fprintf(F, "o lm_%08x\n", It.first);
			DWORD Last = 0xFFFFFFFF;
			for (size_t t = 0; t < C.Tex.size(); t++)
			{
				if (C.Tex[t] != Last)
				{
					fprintf(F, "usemtl tex_%08x\n", C.Tex[t]);
					Last = C.Tex[t];
				}
				const float *P = &C.Verts[t * 15];
				for (int c = 0; c < 3; c++)
					fprintf(F, "v %.4f %.4f %.4f\nvt %.6f %.6f\n", P[c * 5], P[c * 5 + 1], P[c * 5 + 2], P[c * 5 + 3], P[c * 5 + 4]);
				fprintf(F, "f %u/%u %u/%u %u/%u\n", N + 1, N + 1, N + 2, N + 2, N + 3, N + 3);
				N += 3;
				Tris++;
			}
		}
		fclose(F);
		if (fopen_s(&F, (Dir + "U2Shaders\\capture\\lightmaps.txt").c_str(), "w") || F == nullptr)
			return;
		fprintf(F, "# hash width height stage1_op triangles   (op: 4 modulate, 5 modulate x2, 6 modulate x4)\n");
		for (const auto &It : Captured)
			fprintf(F, "%08x %u %u %u %u\n", It.first, It.second.W, It.second.H, It.second.Op, (unsigned)It.second.Tex.size());
		fclose(F);
		if (CaptureWritten++ % 20 == 0)
			Message("lmcapture: %u lightmaps, %u triangles written to U2Shaders\\capture", (unsigned)Captured.size(), Tris);
	}

	U2Rule CharRule;
	std::map<std::string, bool> CharRefused;   // stage/material setups charlight= logged and left alone
	float OldCharConst[24][4] = {};
	unsigned MapsThisFrame = 0, ProbeFrames = 0, FramesWithMaps = 0;
	struct U2Probe { unsigned Draws = 0, AfterMaps = 0, FirstFrame = 0; std::string Sample; };
	std::map<std::string, U2Probe> Probes;
	std::map<DWORD, bool> ProbeDumped;

	// Screen-space contact shadows need the scene's depth as a texture, which Direct3D 9 only
	// offers through vendor formats. Asked once, then actually created: a wrapper (dgVoodoo)
	// may claim a format it can't make. Results go to U2Shaders.log.
	bool DepthChecked = false;
	void ProbeDepth(IDirect3DDevice9 *Dev)
	{
		DepthChecked = true;
		IDirect3D9 *D3D = nullptr;
		D3DDEVICE_CREATION_PARAMETERS CP = {};
		D3DDISPLAYMODE DM = {};
		if (FAILED(Dev->GetDirect3D(&D3D)) || D3D == nullptr || FAILED(Dev->GetCreationParameters(&CP)) || FAILED(Dev->GetDisplayMode(0, &DM)))
		{
			Message("depth probe: device queries failed");
			if (D3D) D3D->Release();
			return;
		}
		IDirect3DSurface9 *DS = nullptr;
		D3DSURFACE_DESC DD = {};
		if (SUCCEEDED(Dev->GetDepthStencilSurface(&DS)) && DS) { DS->GetDesc(&DD); DS->Release(); }
		Message("depth probe: scene depth format %u %ux%u multisample %u", (unsigned)DD.Format, DD.Width, DD.Height, (unsigned)DD.MultiSampleType);
		static const struct { const char *Name; D3DFORMAT Fmt; } Formats[] = {
			{ "INTZ", (D3DFORMAT)MAKEFOURCC('I', 'N', 'T', 'Z') },
			{ "DF24", (D3DFORMAT)MAKEFOURCC('D', 'F', '2', '4') },
			{ "DF16", (D3DFORMAT)MAKEFOURCC('D', 'F', '1', '6') },
			{ "RAWZ", (D3DFORMAT)MAKEFOURCC('R', 'A', 'W', 'Z') },
		};
		for (const auto &F : Formats)
		{
			HRESULT hr = D3D->CheckDeviceFormat(CP.AdapterOrdinal, CP.DeviceType, DM.Format, D3DUSAGE_DEPTHSTENCIL, D3DRTYPE_TEXTURE, F.Fmt);
			IDirect3DTexture9 *T = nullptr;
			HRESULT hc = Dev->CreateTexture(64, 64, 1, D3DUSAGE_DEPTHSTENCIL, F.Fmt, D3DPOOL_DEFAULT, &T, nullptr);
			Message("depth probe: %s reported %s, create %s", F.Name, SUCCEEDED(hr) ? "yes" : "no", SUCCEEDED(hc) && T ? "ok" : "failed");
			if (T) T->Release();
		}
		HRESULT hr = D3D->CheckDeviceFormat(CP.AdapterOrdinal, CP.DeviceType, DM.Format, D3DUSAGE_RENDERTARGET, D3DRTYPE_SURFACE, (D3DFORMAT)MAKEFOURCC('R', 'E', 'S', 'Z'));
		Message("depth probe: RESZ (copy a multisampled depth) reported %s", SUCCEEDED(hr) ? "yes" : "no");
		D3D->Release();
	}

	void ProbeDraw(IDirect3DDevice9 *Dev, IDirect3DTexture9 *Tex, DWORD TexHash, bool FixedFunction)
	{
		if (!DepthChecked)
			ProbeDepth(Dev);
		DWORD blend = 0;
		Dev->GetRenderState(D3DRS_ALPHABLENDENABLE, &blend);
		if (blend || Offscreen(Dev))
			return;
		DWORD fvf = 0, lighting = 0, ambient = 0, vblend = 0, ivb = 0, colorvertex = 0, diffsrc = 0, ambsrc = 0, spec = 0, tf = 0;
		Dev->GetFVF(&fvf);
		Dev->GetRenderState(D3DRS_LIGHTING, &lighting);
		Dev->GetRenderState(D3DRS_AMBIENT, &ambient);
		Dev->GetRenderState(D3DRS_VERTEXBLEND, &vblend);
		Dev->GetRenderState(D3DRS_INDEXEDVERTEXBLENDENABLE, &ivb);
		Dev->GetRenderState(D3DRS_COLORVERTEX, &colorvertex);
		Dev->GetRenderState(D3DRS_DIFFUSEMATERIALSOURCE, &diffsrc);
		Dev->GetRenderState(D3DRS_AMBIENTMATERIALSOURCE, &ambsrc);
		Dev->GetRenderState(D3DRS_SPECULARENABLE, &spec);
		Dev->GetRenderState(D3DRS_TEXTUREFACTOR, &tf);
		DWORD op[3] = {}, a1[3] = {}, a2[3] = {};
		for (DWORD st = 0; st < 3; st++)
		{
			Dev->GetTextureStageState(st, D3DTSS_COLOROP, &op[st]);
			Dev->GetTextureStageState(st, D3DTSS_COLORARG1, &a1[st]);
			Dev->GetTextureStageState(st, D3DTSS_COLORARG2, &a2[st]);
		}
		int lights = 0;
		std::string ls;
		for (DWORD i = 0; i < 8; i++)
		{
			BOOL on = FALSE;
			D3DLIGHT9 L = {};
			if (FAILED(Dev->GetLightEnable(i, &on)) || !on || FAILED(Dev->GetLight(i, &L)))
				continue;
			lights++;
			char b[160];
			sprintf_s(b, " | L%u type %u dif %.2f %.2f %.2f amb %.2f %.2f %.2f range %.0f att %.3f %.5f",
				i, (unsigned)L.Type, L.Diffuse.r, L.Diffuse.g, L.Diffuse.b, L.Ambient.r, L.Ambient.g, L.Ambient.b,
				L.Range, L.Attenuation1, L.Attenuation2);
			ls += b;
		}
		D3DMATERIAL9 M = {};
		Dev->GetMaterial(&M);

		char key[300];
		sprintf_s(key, "%08x %s fvf %x lighting %u vblend %u/%u colorvertex %u src dif %u amb %u spec %u lights %d | st0 %u %x %x | st1 %u %x %x | st2 %u %x %x",
			TexHash, FixedFunction ? "ff" : "vs", fvf, lighting, vblend, ivb, colorvertex, diffsrc, ambsrc, spec, lights,
			op[0], a1[0], a2[0], op[1], a1[1], a2[1], op[2], a1[2], a2[2]);
		char sample[200];
		sprintf_s(sample, "ambient %08x tfactor %08x mat dif %.2f %.2f %.2f amb %.2f %.2f %.2f emi %.2f %.2f %.2f",
			ambient, tf, M.Diffuse.r, M.Diffuse.g, M.Diffuse.b, M.Ambient.r, M.Ambient.g, M.Ambient.b, M.Emissive.r, M.Emissive.g, M.Emissive.b);

		U2Probe &P = Probes[key];
		if (P.Draws++ == 0)
			P.FirstFrame = Frame;
		if (MapsThisFrame > 0)
			P.AfterMaps++;
		P.Sample = std::string(sample) + ls;
		if (!ProbeDumped[TexHash])
		{
			ProbeDumped[TexHash] = true;
			U2TexInfo Dummy;
			this->Hash(Tex, Dummy, true);
		}
	}

	void OnPresent()
	{
		if (Post && Saw3D && !PostDone && LastDev != nullptr && !Offscreen(LastDev))
		{
			// no 2D draw this frame (no HUD): post-process the 3D frame now, in a scene of our own
			LastDev->BeginScene();
			RunPost(LastDev);
			LastDev->EndScene();
		}
		if (PostTrace > 0 && !PostTraceLine.empty())
		{
			static int frame = 0;
			if (++frame % 300 == 0)      // every 300th frame, so both views get sampled
			{
				Message("posttrace: %s", PostTraceLine.c_str());
				PostTrace--;
			}
		}
		PostTraceLine.clear();
		Saw3D = PostDone = false;
		Frame++;
		if (Capture && CaptureDirty && Frame % 300 == 0)
			WriteCapture();
		if (CharProbe)
		{
			ProbeFrames++;
			if (MapsThisFrame > 0)
				FramesWithMaps++;
			MapsThisFrame = 0;
		}
		if ((Log || CharProbe) && Frame - LogFrame >= 300)
		{
			LogFrame = Frame;
			WriteSeen();
		}
	}

	void WriteSeen()
	{
		FILE *F = nullptr;
		if (CharProbe && !fopen_s(&F, (Dir + "U2Shaders\\dump\\chars.txt").c_str(), "w") && F)
		{
			fprintf(F, "frames %u, with shadow silhouettes drawn %u\n", ProbeFrames, FramesWithMaps);
			fprintf(F, "draws  after-maps  first-frame  texture / state\n                                  last sample\n");
			for (const auto &It : Probes)
				fprintf(F, "%6u  %6u  %8u  %s\n      %s\n", It.second.Draws, It.second.AfterMaps, It.second.FirstFrame,
					It.first.c_str(), It.second.Sample.c_str());
			fclose(F);
			F = nullptr;
		}
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
		PostRelease();
		if (Log)
			WriteSeen();
	}

	void OnDestroy()
	{
		OnLost();
		for (U2Rule &R : Rules)
			if (R.PS != nullptr) { R.PS->Release(); R.PS = nullptr; R.Tried = false; }
		for (U2Rule *R : { &MapRule, &ProjRule, &PostBright, &PostBlur, &PostFinal })
			if (R->PS != nullptr) { R->PS->Release(); R->PS = nullptr; R->Tried = false; }
		LastDev = nullptr;
	}

private:
	bool WasFixedFunction = false;
};
