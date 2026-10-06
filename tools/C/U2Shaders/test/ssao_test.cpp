// ssao_test: a plain Direct3D 8 room through the built d3d8.dll, for ssao=1 (post-processing).
// A floor, a back wall, a left wall and a box on the floor, flat vertex colours (no lighting,
// so without SSAO the corners don't show at all), then a HUD box drawn the way Unreal II
// starts its HUD (orthographic, no depth test), which is where the post chain runs.
//   ssao_test off | on | debug     writes U2Shaders.ini and saves frame_ssao_<mode>.bmp
// Built and run by run_ssao.sh.
#include <windows.h>
#include <d3d8.h>
#include <cmath>
#include <cstdio>
#include <cstring>

struct CV { float x, y, z; DWORD c; };
static const DWORD FVF = D3DFVF_XYZ | D3DFVF_DIFFUSE;

static D3DMATRIX Ident()
{
	D3DMATRIX m = {};
	m._11 = m._22 = m._33 = m._44 = 1;
	return m;
}

// a quad from four corners (strip order: a b c d = top-left, top-right, bottom-left, bottom-right)
static void Quad(IDirect3DDevice8 *D, float ax, float ay, float az, float bx, float by, float bz,
	float cx, float cy, float cz, float dx, float dy, float dz, DWORD col)
{
	CV q[4] = { { ax, ay, az, col }, { bx, by, bz, col }, { cx, cy, cz, col }, { dx, dy, dz, col } };
	D->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, q, sizeof(CV));
}

static void Box(IDirect3DDevice8 *D, float x0, float y0, float z0, float x1, float y1, float z1, DWORD top, DWORD side, DWORD front)
{
	Quad(D, x0, y1, z1, x1, y1, z1, x0, y1, z0, x1, y1, z0, top);       // top
	Quad(D, x0, y1, z0, x1, y1, z0, x0, y0, z0, x1, y0, z0, front);     // front (faces the camera)
	Quad(D, x0, y1, z1, x0, y1, z0, x0, y0, z1, x0, y0, z0, side);      // left
	Quad(D, x1, y1, z0, x1, y1, z1, x1, y0, z0, x1, y0, z1, side);      // right
}

int main(int argc, char **argv)
{
	const char *mode = argc >= 2 ? argv[1] : "on";
	FILE *F = fopen("U2Shaders.ini", "w");
	fprintf(F, "post=1\nsmaa=0\nbloom=1.0 0.0\n");
	if (strcmp(mode, "off") != 0)
		fprintf(F, "ssao=1\nssaofx=0.9 40 1.0 %d\n", strcmp(mode, "debug") == 0 ? 1 : 0);
	fclose(F);

	const UINT Wd = 640, Ht = 480;
	WNDCLASSA wc = {}; wc.lpfnWndProc = DefWindowProcA; wc.hInstance = GetModuleHandle(nullptr); wc.lpszClassName = "ssao";
	RegisterClassA(&wc);
	HWND hw = CreateWindowA("ssao", "ssao", WS_OVERLAPPEDWINDOW, 0, 0, Wd, Ht, nullptr, nullptr, wc.hInstance, nullptr);
	IDirect3D8 *D3D = Direct3DCreate8(D3D_SDK_VERSION);
	if (!D3D) { printf("Direct3DCreate8 failed\n"); return 1; }
	D3DDISPLAYMODE dm; D3D->GetAdapterDisplayMode(0, &dm);
	D3DPRESENT_PARAMETERS pp = {};
	pp.Windowed = TRUE; pp.SwapEffect = D3DSWAPEFFECT_COPY; pp.BackBufferFormat = dm.Format;
	pp.BackBufferWidth = Wd; pp.BackBufferHeight = Ht;
	pp.EnableAutoDepthStencil = TRUE; pp.AutoDepthStencilFormat = D3DFMT_D24S8;
	IDirect3DDevice8 *D = nullptr;
	HRESULT hr = D3D->CreateDevice(0, D3DDEVTYPE_HAL, hw, D3DCREATE_SOFTWARE_VERTEXPROCESSING, &pp, &D);
	if (FAILED(hr)) { printf("CreateDevice failed %08lx\n", hr); return 1; }
	IDirect3DSurface8 *BB = nullptr;
	D->GetRenderTarget(&BB);

	// camera at the origin looking down +Z, a little above the floor
	D3DMATRIX W = Ident(), Vw = Ident(), Pr = {};
	Vw._42 = -10;                                   // eye at y = 10
	float zn = 4, zf = 4000, fy = 1 / std::tan(0.55f);
	Pr._11 = fy * Ht / Wd; Pr._22 = fy; Pr._33 = zf / (zf - zn); Pr._34 = 1; Pr._43 = -zn * zf / (zf - zn);

	for (int frame = 0; frame < 90; frame++)
	{
		D->Clear(0, nullptr, D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER, 0xFF203040, 1.0f, 0);
		D->BeginScene();
		D->SetTransform(D3DTS_WORLD, &W); D->SetTransform(D3DTS_VIEW, &Vw); D->SetTransform(D3DTS_PROJECTION, &Pr);
		D->SetRenderState(D3DRS_LIGHTING, FALSE);
		D->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
		D->SetRenderState(D3DRS_ZENABLE, TRUE);
		D->SetRenderState(D3DRS_ZWRITEENABLE, TRUE);
		D->SetTexture(0, nullptr);
		D->SetTextureStageState(0, D3DTSS_COLOROP, D3DTOP_SELECTARG1);
		D->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_DIFFUSE);
		D->SetVertexShader(FVF);
		// floor (y = -40), back wall (z = 260), left wall (x = -110), right wall (x = 150)
		Quad(D, -110, -40, 260, 150, -40, 260, -110, -40, 20, 150, -40, 20, 0xFFA8A49C);
		Quad(D, -110, 120, 260, 150, 120, 260, -110, -40, 260, 150, -40, 260, 0xFFC0C0C8);
		Quad(D, -110, 120, 20, -110, 120, 260, -110, -40, 20, -110, -40, 260, 0xFFB8B8C0);
		Quad(D, 150, 120, 260, 150, 120, 20, 150, -40, 260, 150, -40, 20, 0xFFB8B8C0);
		// a crate on the floor against nothing, and a low step along the back wall
		Box(D, -20, -40, 140, 30, 10, 190, 0xFFC8B090, 0xFFC8B090, 0xFFC8B090);
		Box(D, -110, -40, 230, 150, -28, 260, 0xFFB0ACA4, 0xFFB0ACA4, 0xFFB0ACA4);

		// the HUD: orthographic, no depth test (post-processing runs here)
		D3DMATRIX Ortho = Ident();
		Ortho._11 = 2.0f / Wd; Ortho._22 = -2.0f / Ht; Ortho._41 = -1; Ortho._42 = 1;
		D->SetTransform(D3DTS_PROJECTION, &Ortho);
		D->SetTransform(D3DTS_VIEW, &W);
		D->SetRenderState(D3DRS_ZENABLE, FALSE);
		Quad(D, 10, 440, 0.5f, 130, 440, 0.5f, 10, 470, 0.5f, 130, 470, 0.5f, 0xFF30C030);
		D->SetRenderState(D3DRS_ZENABLE, TRUE);
		D->EndScene();

		if (frame == 89)
		{
			D3DSURFACE_DESC bd; BB->GetDesc(&bd);
			IDirect3DSurface8 *Sys = nullptr;
			D->CreateImageSurface(bd.Width, bd.Height, bd.Format, &Sys);
			D->CopyRects(BB, nullptr, 0, Sys, nullptr);
			D3DLOCKED_RECT LR;
			if (Sys && SUCCEEDED(Sys->LockRect(&LR, nullptr, D3DLOCK_READONLY)))
			{
				char name[64];
				snprintf(name, sizeof(name), "frame_ssao_%s.bmp", mode);
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
				printf("saved %s\n", name);
			}
			if (Sys) Sys->Release();
		}
		D->Present(nullptr, nullptr, nullptr, nullptr);
	}
	BB->Release();
	D->Release(); D3D->Release();
	return 0;
}
