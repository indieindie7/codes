// Smoke test for the U2Shaders d3d8.dll outside the game: a Direct3D 8 app that draws what the
// probes and the decal rule look for, then saves the frame. Run next to the d3d8.dll under test.
//   1. a shadow-silhouette-style draw into an offscreen target (untextured, TFACTOR, no blend)
//   2. an opaque, textured, fixed-function-lit wall (two D3D lights, material, ambient)
//   3. an alpha-blended bullet-hole decal on the wall (decal= rule -> decal_parallax.hlsl)
// Modes "wall" / "wallflat": instead, a brick wall drawn the way level geometry is (texture x
// vertex colour on stage 0, a lightmap times 2 on stage 1), with and without the surface= rule.
// Modes "sphere" / "spherelit": a textured, D3D-lit sphere seen through an Unreal-style view
// (world X forward, Z up), without and with charlight=1 (per-pixel character lighting).
// Mode "wallcap": the wall with lmcapture=1 (writes U2Shaders\capture\scene.obj). Mode
// "wallbaked": the wall with its lightmap replaced by U2Shaders\baked\<hash>.dds, if a bake made one.
// Mode "wallgi": the wall with its lightmap swapped (replace=) for a DDS this program writes
// (warm light from the left, blue bounce from the right), as a Blender bake would be.
// Writes U2Shaders.ini itself (the decal's hash computed the way u2shaders.hpp does).
#include <windows.h>
#include <d3d8.h>
#include <cmath>
#include <cstdio>
#include <vector>

struct V { float x, y, z, nx, ny, nz, u, v; };
static const DWORD FVF = D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_TEX1;
struct SV { float x, y, z, rhw; };

static D3DMATRIX Ident() { D3DMATRIX m = {}; m._11 = m._22 = m._33 = m._44 = 1; return m; }

enum Kind { CHECKER, DECAL, BRICK, LIGHTMAP };
static IDirect3DTexture8 *MakeTex(IDirect3DDevice8 *D, Kind kind, DWORD *hashOut)
{
	IDirect3DTexture8 *T = nullptr;
	// bricks with a full mip chain, like game textures (the parallax reads a smaller mip for height)
	if (FAILED(D->CreateTexture(64, 64, kind == BRICK ? 0 : 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, &T)))
		return nullptr;
	D3DLOCKED_RECT L;
	T->LockRect(0, &L, nullptr, 0);
	for (int y = 0; y < 64; y++)
		for (int x = 0; x < 64; x++)
		{
			DWORD c;
			if (kind == BRICK)
			{
				// 32x16 bricks, every other row offset, 2-texel dark mortar; a little noise on the faces
				int row = y / 16, bx = (x + (row & 1) * 16) % 32, by = y % 16;
				bool mortar = bx < 2 || by < 2;
				int n = ((x * 73 + y * 151) % 17) - 8;
				c = mortar ? 0xFF282420 : 0xFF000000 | ((150 + n) << 16) | ((80 + n) << 8) | (60 + n);
			}
			else if (kind == LIGHTMAP)
			{
				// bright towards the top left, darker to the bottom right (x2 on stage 1: 0x80 = unchanged)
				int l = 0x40 + (127 - x - y) * 0x50 / 127;
				c = 0xFF000000 | (l << 16) | (l << 8) | l;
			}
			else if (kind == DECAL)
			{
				float r = std::hypot((x + 0.5f) / 64 - 0.5f, (y + 0.5f) / 64 - 0.5f);
				float a = std::pow(std::fmax(0.f, 1 - r / 0.32f), 0.6f);
				int ring = (std::sin(r * 90) > 0) ? 150 : 60;
				c = ((DWORD)(a * 255) << 24) | (ring << 16) | (ring * 8 / 9 << 8) | (ring * 7 / 9);
			}
			else
				c = 0xFF000000 | (((x / 8 + y / 8) & 1) ? 0xB0B0B0 : 0x909090);
			((DWORD *)((BYTE *)L.pBits + y * L.Pitch))[x] = c;
		}
	if (hashOut)
	{
		// same as U2Shaders::Hash: FNV-1a over the top mip's first 16 KB, seeded by its size
		// (computed before the mips below are written: only the top level counts)
		DWORD H = 2166136261u ^ 64 ^ (64 << 12);
		const BYTE *P = (const BYTE *)L.pBits;
		UINT n = L.Pitch * 64; if (n > 16384) n = 16384;
		for (UINT i = 0; i < n; i++) H = (H ^ P[i]) * 16777619u;
		*hashOut = H ? H : 1;
	}
	T->UnlockRect(0);
	for (UINT lv = 1; lv < T->GetLevelCount(); lv++)
	{
		// box-filter each mip from the one above
		D3DLOCKED_RECT A, B;
		T->LockRect(lv - 1, &A, nullptr, D3DLOCK_READONLY);
		T->LockRect(lv, &B, nullptr, 0);
		const int w = 64 >> lv;
		for (int y = 0; y < w; y++)
			for (int x = 0; x < w; x++)
			{
				DWORD out = 0;
				for (int ch = 0; ch < 32; ch += 8)
				{
					DWORD sum = 0;
					for (int k = 0; k < 4; k++)
						sum += (((DWORD *)((BYTE *)A.pBits + (y * 2 + k / 2) * A.Pitch))[x * 2 + k % 2] >> ch) & 0xFF;
					out |= (sum / 4) << ch;
				}
				((DWORD *)((BYTE *)B.pBits + y * B.Pitch))[x] = out;
			}
		T->UnlockRect(lv);
		T->UnlockRect(lv - 1);
	}
	return T;
}

// a 64x64 32-bit DDS with a full mip chain: warm on the left fading to a blue bounce on the right
static void WriteBakedDDS(const char *name)
{
	DWORD H[32] = {};
	H[0] = 0x20534444; H[1] = 124; H[2] = 0x1007 | 0x8 | 0x20000; H[3] = 64; H[4] = 64; H[5] = 256; H[7] = 7;
	H[19] = 32; H[20] = 0x40; H[22] = 32; H[23] = 0xFF0000; H[24] = 0xFF00; H[25] = 0xFF; H[27] = 0x1000 | 0x400000 | 0x8;
	FILE *F = fopen(name, "wb");
	fwrite(H, 4, 32, F);
	for (int lv = 0, w = 64; lv < 7; lv++, w /= 2)
		for (int y = 0; y < w; y++)
			for (int x = 0; x < w; x++)
			{
				float t = (x + 0.5f) / w;
				int r = (int)(0xC0 * (1 - t) + 0x30 * t), g = (int)(0xA0 * (1 - t) + 0x50 * t), b = (int)(0x60 * (1 - t) + 0xA0 * t);
				DWORD c = 0xFF000000 | (r << 16) | (g << 8) | b;
				fwrite(&c, 4, 1, F);
			}
	fclose(F);
}

int main(int argc, char **argv)
{
	// modes: (none) decal rule on | flat: no rules | post: post=1 with postsplit, a bright
	// light panel in 3D and a HUD box + crosshair in 2D drawn after it
	const bool postMode = argc >= 2 && strcmp(argv[1], "post") == 0;
	const bool wallMode = argc >= 2 && strncmp(argv[1], "wall", 4) == 0;
	const bool sphereMode = argc >= 2 && strncmp(argv[1], "sphere", 6) == 0;
	const bool charLight = sphereMode && strcmp(argv[1], "spherelit") == 0;
	const bool giMode = wallMode && strcmp(argv[1], "wallgi") == 0;
	const bool capMode = wallMode && strcmp(argv[1], "wallcap") == 0;
	const bool bakedMode = wallMode && strcmp(argv[1], "wallbaked") == 0;
	const bool useWallRule = wallMode && (strcmp(argv[1], "wall") == 0 || giMode);
	const bool useDecalRule = argc < 2 || (strcmp(argv[1], "flat") != 0 && !postMode && !wallMode && !sphereMode);
	WNDCLASSA wc = {}; wc.lpfnWndProc = DefWindowProcA; wc.hInstance = GetModuleHandle(nullptr); wc.lpszClassName = "u2t";
	RegisterClassA(&wc);
	HWND hw = CreateWindowA("u2t", "u2t", WS_OVERLAPPEDWINDOW, 0, 0, 320, 240, nullptr, nullptr, wc.hInstance, nullptr);
	IDirect3D8 *D3D = Direct3DCreate8(D3D_SDK_VERSION);
	if (!D3D) { printf("Direct3DCreate8 failed\n"); return 1; }
	D3DDISPLAYMODE dm; D3D->GetAdapterDisplayMode(0, &dm);
	D3DPRESENT_PARAMETERS pp = {};
	pp.Windowed = TRUE; pp.SwapEffect = D3DSWAPEFFECT_COPY; pp.BackBufferFormat = dm.Format;
	pp.BackBufferWidth = 320; pp.BackBufferHeight = 240;
	pp.EnableAutoDepthStencil = TRUE; pp.AutoDepthStencilFormat = D3DFMT_D16;
	IDirect3DDevice8 *D = nullptr;
	HRESULT hr = D3D->CreateDevice(0, D3DDEVTYPE_HAL, hw, D3DCREATE_SOFTWARE_VERTEXPROCESSING, &pp, &D);
	if (FAILED(hr)) { printf("CreateDevice failed %08lx\n", hr); return 1; }

	DWORD decalHash = 0, brickHash = 0, lightHash = 0;
	IDirect3DTexture8 *Wall = MakeTex(D, CHECKER, nullptr), *Hole = MakeTex(D, DECAL, &decalHash);
	IDirect3DTexture8 *Brick = MakeTex(D, BRICK, &brickHash), *Light = MakeTex(D, LIGHTMAP, &lightHash);
	FILE *F = fopen("U2Shaders.ini", "w");
	fprintf(F, "charprobe=1\n");
	if (useDecalRule) fprintf(F, "decal=%08lx decal_parallax.hlsl\n", decalHash);
	if (postMode) fprintf(F, "post=1\npostsplit=1\nbloom=0.7 1.0\n");
	if (charLight) fprintf(F, "charlight=1\n");
	if (useWallRule) fprintf(F, "surface=%08lx world_parallax.hlsl\n", brickHash);
	if (capMode) fprintf(F, "lmcapture=1\n");
	if (bakedMode) fprintf(F, "replace=%08lx baked\\%08lx.dds\n", lightHash, lightHash);
	if (giMode)
	{
		WriteBakedDDS("U2Shaders\\baked_test.dds");
		fprintf(F, "replace=%08lx baked_test.dds\n", lightHash);
	}
	fclose(F);
	printf("decal hash %08lx, rule %s\n", decalHash, useDecalRule ? "on" : "off");

	IDirect3DTexture8 *RT = nullptr; IDirect3DSurface8 *RTS = nullptr, *BB = nullptr, *ZS = nullptr;
	D->CreateTexture(128, 128, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT, &RT);
	RT->GetSurfaceLevel(0, &RTS);
	D->GetRenderTarget(&BB); D->GetDepthStencilSurface(&ZS);

	// a wall tilted 60 degrees away to the right, 60 units ahead
	const float c = std::cos(1.05f), s = std::sin(1.05f);
	auto P = [&](float a, float b, float off, float u, float v) {
		V r = { a * c, b, 60 + a * s - off, -s, 0, c, u, v };
		return r;
	};
	V wall[4] = { P(-40, 30, 0, 0, 0), P(40, 30, 0, 5, 0), P(-40, -30, 0, 0, 4), P(40, -30, 0, 5, 4) };
	V hole[4] = { P(-8, 8, 0.05f, 0, 0), P(8, 8, 0.05f, 1, 0), P(-8, -8, 0.05f, 0, 1), P(8, -8, 0.05f, 1, 1) };
	SV sil[4] = { { 20, 20, 0.5f, 1 }, { 100, 20, 0.5f, 1 }, { 20, 100, 0.5f, 1 }, { 100, 100, 0.5f, 1 } };

	D3DMATRIX W = Ident(), Vw = Ident(), Pr = {};
	float zn = 1, zf = 1000, fy = 1 / std::tan(0.6f);
	Pr._11 = fy * 240 / 320; Pr._22 = fy; Pr._33 = zf / (zf - zn); Pr._34 = 1; Pr._43 = -zn * zf / (zf - zn);
	D->SetTransform(D3DTS_WORLD, &W); D->SetTransform(D3DTS_VIEW, &Vw); D->SetTransform(D3DTS_PROJECTION, &Pr);

	D3DLIGHT8 L0 = {}; L0.Type = D3DLIGHT_DIRECTIONAL; L0.Diffuse = { 0.9f, 0.85f, 0.8f, 1 }; L0.Direction = { -0.5f, -0.3f, 1 };
	D3DLIGHT8 L1 = {}; L1.Type = D3DLIGHT_POINT; L1.Diffuse = { 0.3f, 0.3f, 0.5f, 1 }; L1.Ambient = { 0.1f, 0.1f, 0.1f, 1 };
	L1.Position = { 10, 10, 40 }; L1.Range = 200; L1.Attenuation0 = 1;
	D3DMATERIAL8 M = {}; M.Diffuse = { 1, 1, 1, 1 }; M.Ambient = { 1, 1, 1, 1 };

	// the sphere: Unreal-style world (X forward, Y right, Z up), radius 18, 45 units ahead
	std::vector<V> sphere;
	{
		const int SEG = 32, RING = 16;
		auto At = [](int i, int j) {
			const float lon = i * 6.2831853f / SEG, lat = j * 3.1415927f / RING - 1.5707963f;
			const float nx = std::cos(lat) * std::cos(lon), ny = std::cos(lat) * std::sin(lon), nz = std::sin(lat);
			V v = { 45 + 18 * nx, 18 * ny, 18 * nz, nx, ny, nz, i * 4.0f / SEG, j * 2.0f / RING };
			return v;
		};
		for (int j = 0; j < RING; j++)
			for (int i = 0; i < SEG; i++)
			{
				V a = At(i, j), b = At(i + 1, j), c = At(i, j + 1), d = At(i + 1, j + 1);
				sphere.insert(sphere.end(), { a, c, b, b, c, d });
			}
	}
	// Unreal's view: world Y -> screen right, Z -> up, X -> into the screen (a rotation)
	D3DMATRIX UView = {};
	UView._13 = 1; UView._21 = 1; UView._32 = 1; UView._44 = 1;
	D3DLIGHT8 S0 = {}; S0.Type = D3DLIGHT_DIRECTIONAL; S0.Diffuse = { 0.95f, 0.85f, 0.7f, 1 }; S0.Direction = { 0.6f, 0.6f, -0.7f };
	D3DLIGHT8 S1 = {}; S1.Type = D3DLIGHT_POINT; S1.Diffuse = { 0.2f, 0.35f, 0.8f, 1 };
	S1.Position = { 30, -40, -10 }; S1.Range = 300; S1.Attenuation0 = 1;

	for (int frame = 0; frame < 320; frame++)
	{
		// 1. silhouette into the offscreen target
		D->SetRenderTarget(RTS, nullptr);
		D->BeginScene();
		D->Clear(0, nullptr, D3DCLEAR_TARGET, 0xFFFFFFFF, 1, 0);
		D->SetTexture(0, nullptr);
		D->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
		D->SetRenderState(D3DRS_LIGHTING, FALSE);
		D->SetRenderState(D3DRS_TEXTUREFACTOR, 0x80808080);
		D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
		D->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TFACTOR);
		D->SetVertexShader(D3DFVF_XYZRHW);
		D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, sil, sizeof(SV));
		D->EndScene();

		// 2. the lit wall, 3. the decal
		D->SetRenderTarget(BB, ZS);
		D->BeginScene();
		D->Clear(0, nullptr, D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER, 0xFF202830, 1, 0);
		D->SetRenderState(D3DRS_LIGHTING, TRUE);
		D->SetRenderState(D3DRS_AMBIENT, 0x00303030);
		D->SetLight(0, &L0); D->LightEnable(0, TRUE);
		D->SetLight(1, &L1); D->LightEnable(1, TRUE);
		D->SetMaterial(&M);
		D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_MODULATE);
		D->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TEXTURE);
		D->SetTextureStageState(0, D3DTSS_COLORARG2, D3DTA_DIFFUSE);
		D->SetTextureStageState(0, D3DTSS_ALPHAOP, D3DTOP_SELECTARG1);
		D->SetTextureStageState(0, D3DTSS_ALPHAARG1, D3DTA_TEXTURE);
		D->SetVertexShader(FVF);
		if (sphereMode)
		{
			D->SetTransform(D3DTS_VIEW, &UView);
			D->SetLight(0, &S0); D->SetLight(1, &S1);
			D->SetTexture(0, Wall);
			D->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
			D->DrawPrimitiveUP(D3DPT_TRIANGLELIST, (UINT)sphere.size() / 3, sphere.data(), sizeof(V));
			D->SetRenderState(D3DRS_CULLMODE, D3DCULL_CCW);
			D->SetTransform(D3DTS_VIEW, &Vw);
		}
		else if (wallMode)
		{
			// level geometry: texture x vertex lighting, then the lightmap x2 (same coordinates, scaled down)
			D3DMATRIX lm = Ident(); lm._11 = 0.2f; lm._22 = 0.25f;
			D->SetTransform(D3DTS_TEXTURE1, &lm);
			D->SetTextureStageState(1, D3DTSS_TEXCOORDINDEX, 0);
			D->SetTextureStageState(1, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_COUNT2);
			D->SetTextureStageState(1, D3DTSS_COLOROP, D3DTOP_MODULATE2X);
			D->SetTextureStageState(1, D3DTSS_COLORARG1, D3DTA_TEXTURE);
			D->SetTextureStageState(1, D3DTSS_COLORARG2, D3DTA_CURRENT);
			D->SetTextureStageState(0, D3DTSS_MIPFILTER, D3DTEXF_LINEAR);
			D->SetTextureStageState(0, D3DTSS_MINFILTER, D3DTEXF_LINEAR);
			D->SetTextureStageState(0, D3DTSS_MAGFILTER, D3DTEXF_LINEAR);
			D->SetTexture(0, Brick);
			D->SetTexture(1, Light);
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, wall, sizeof(V));
			D->SetTexture(1, nullptr);
			D->SetTextureStageState(1, D3DTSS_COLOROP, D3DTOP_DISABLE);
			D->SetTextureStageState(1, D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
		}
		else
		{
			D->SetTexture(0, Wall);
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, wall, sizeof(V));
		}

		D->SetRenderState(D3DRS_LIGHTING, FALSE);
		D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
		D->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE);
		D->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_SRCALPHA);
		D->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
		D->SetRenderState(D3DRS_ZFUNC, D3DCMP_ALWAYS);
		D->SetTexture(0, Hole);
		if (!wallMode && !sphereMode)
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, hole, sizeof(V));
		D->SetRenderState(D3DRS_ZFUNC, D3DCMP_LESSEQUAL);
		D->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);

		if (postMode)
		{
			// a bright light panel in the 3D scene (should bloom), straddling the screen's middle
			V lamp[4] = { P(-6, 22, 0.1f, 0, 0), P(6, 22, 0.1f, 1, 0), P(-6, 16, 0.1f, 0, 1), P(6, 16, 0.1f, 1, 1) };
			D->SetTexture(0, nullptr);
			D->SetRenderState(D3DRS_TEXTUREFACTOR, 0xFFFFFFFF);
			D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
			D->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TFACTOR);
			D->SetVertexShader(FVF);
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, lamp, sizeof(V));
			// the HUD after it, pre-transformed: a box at the bottom left and a crosshair (must stay sharp)
			SV box[4] = { { 10, 200, 0, 1 }, { 110, 200, 0, 1 }, { 10, 230, 0, 1 }, { 110, 230, 0, 1 } };
			SV cross1[4] = { { 150, 119, 0, 1 }, { 170, 119, 0, 1 }, { 150, 121, 0, 1 }, { 170, 121, 0, 1 } };
			SV cross2[4] = { { 159, 110, 0, 1 }, { 161, 110, 0, 1 }, { 159, 130, 0, 1 }, { 161, 130, 0, 1 } };
			D->SetRenderState(D3DRS_ZENABLE, FALSE);
			D->SetVertexShader(D3DFVF_XYZRHW);
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, box, sizeof(SV));
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, cross1, sizeof(SV));
			D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, cross2, sizeof(SV));
			D->SetRenderState(D3DRS_ZENABLE, TRUE);
		}
		D->EndScene();

		if (frame == 319)
		{
			// save the back buffer as a BMP (read back through a lockable copy)
			D3DSURFACE_DESC bd; BB->GetDesc(&bd);
			IDirect3DSurface8 *Sys = nullptr;
			D->CreateImageSurface(bd.Width, bd.Height, bd.Format, &Sys);
			D->CopyRects(BB, nullptr, 0, Sys, nullptr);
			D3DLOCKED_RECT LR;
			if (Sys && SUCCEEDED(Sys->LockRect(&LR, nullptr, D3DLOCK_READONLY)))
			{
				const char *name = sphereMode ? (charLight ? "frame_spherelit.bmp" : "frame_sphere.bmp") : postMode ? "frame_post.bmp" : wallMode ? (giMode ? "frame_wallgi.bmp" : bakedMode ? "frame_wallbaked.bmp" : capMode ? "frame_wallcap.bmp" : useWallRule ? "frame_wall.bmp" : "frame_wallflat.bmp")
					: useDecalRule ? "frame_parallax.bmp" : "frame_flat.bmp";
				FILE *B = fopen(name, "wb");
				BITMAPFILEHEADER fh = {}; BITMAPINFOHEADER ih = {};
				fh.bfType = 0x4D42; fh.bfOffBits = sizeof(fh) + sizeof(ih);
				fh.bfSize = fh.bfOffBits + bd.Width * bd.Height * 4;
				ih.biSize = sizeof(ih); ih.biWidth = bd.Width; ih.biHeight = -(LONG)bd.Height;
				ih.biPlanes = 1; ih.biBitCount = 32;
				fwrite(&fh, sizeof(fh), 1, B); fwrite(&ih, sizeof(ih), 1, B);
				for (UINT y = 0; y < bd.Height; y++)
					fwrite((BYTE *)LR.pBits + y * LR.Pitch, 4, bd.Width, B);
				fclose(B);
				Sys->UnlockRect();
				printf("saved frame (format %u)\n", (unsigned)bd.Format);
			}
			if (Sys) Sys->Release();
		}
		D->Present(nullptr, nullptr, nullptr, nullptr);
	}
	printf("done\n");
	D->Release(); D3D->Release();
	return 0;
}
