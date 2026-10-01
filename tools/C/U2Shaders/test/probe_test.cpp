// Smoke test for the U2Shaders d3d8.dll outside the game: a Direct3D 8 app that draws what the
// probes and the decal rule look for, then saves the frame. Run next to the d3d8.dll under test.
//   1. a shadow-silhouette-style draw into an offscreen target (untextured, TFACTOR, no blend)
//   2. an opaque, textured, fixed-function-lit wall (two D3D lights, material, ambient)
//   3. an alpha-blended bullet-hole decal on the wall (decal= rule -> decal_parallax.hlsl)
// Writes U2Shaders.ini itself (the decal's hash computed the way u2shaders.hpp does).
#include <windows.h>
#include <d3d8.h>
#include <cmath>
#include <cstdio>

struct V { float x, y, z, nx, ny, nz, u, v; };
static const DWORD FVF = D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_TEX1;
struct SV { float x, y, z, rhw; };

static D3DMATRIX Ident() { D3DMATRIX m = {}; m._11 = m._22 = m._33 = m._44 = 1; return m; }

static IDirect3DTexture8 *MakeTex(IDirect3DDevice8 *D, bool decal, DWORD *hashOut)
{
	IDirect3DTexture8 *T = nullptr;
	if (FAILED(D->CreateTexture(64, 64, 1, 0, D3DFMT_A8R8G8B8, D3DPOOL_MANAGED, &T)))
		return nullptr;
	D3DLOCKED_RECT L;
	T->LockRect(0, &L, nullptr, 0);
	for (int y = 0; y < 64; y++)
		for (int x = 0; x < 64; x++)
		{
			DWORD c;
			if (decal)
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
		DWORD H = 2166136261u ^ 64 ^ (64 << 12);
		const BYTE *P = (const BYTE *)L.pBits;
		UINT n = L.Pitch * 64; if (n > 16384) n = 16384;
		for (UINT i = 0; i < n; i++) H = (H ^ P[i]) * 16777619u;
		*hashOut = H ? H : 1;
	}
	T->UnlockRect(0);
	return T;
}

int main(int argc, char **argv)
{
	const bool useDecalRule = argc < 2 || strcmp(argv[1], "flat") != 0;
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

	DWORD decalHash = 0;
	IDirect3DTexture8 *Wall = MakeTex(D, false, nullptr), *Hole = MakeTex(D, true, &decalHash);
	FILE *F = fopen("U2Shaders.ini", "w");
	fprintf(F, "charprobe=1\n");
	if (useDecalRule) fprintf(F, "decal=%08lx decal_parallax.hlsl\n", decalHash);
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
		D->SetTexture(0, Wall);
		D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, wall, sizeof(V));

		D->SetRenderState(D3DRS_LIGHTING, FALSE);
		D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
		D->SetRenderState(D3DRS_ALPHABLENDENABLE, TRUE);
		D->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_SRCALPHA);
		D->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_INVSRCALPHA);
		D->SetRenderState(D3DRS_ZFUNC, D3DCMP_ALWAYS);
		D->SetTexture(0, Hole);
		D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, hole, sizeof(V));
		D->SetRenderState(D3DRS_ZFUNC, D3DCMP_LESSEQUAL);
		D->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
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
				FILE *B = fopen(useDecalRule ? "frame_parallax.bmp" : "frame_flat.bmp", "wb");
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
