/**
 * Borderless fullscreen without dgVoodoo (U2Shaders fork).
 *
 * When the game asks for a fullscreen device, it gets a windowed one instead and its window becomes a
 * frameless popup covering the monitor: it looks like fullscreen, with no display-mode switch, so
 * alt-tab is instant and other windows can sit on a second monitor. The game keeps its own resolution
 * (the back buffer); Present stretches it to the monitor.
 *
 * The window is restyled right there, inside CreateDevice / Reset, on the game's own thread, before the
 * device exists, and the size / move messages that causes are kept from the game (an earlier attempt
 * resized the window later from another thread, and the game rebuilt its renderer mid-frame and
 * aborted). "fullscreen=exclusive" in System\U2Shaders.ini keeps the game's real fullscreen.
 * A d3d9.dll wrapper next to the game (dgVoodoo) makes its own fake fullscreen: then this stays
 * off ("fullscreen=borderless" forces it on anyway).
 */

#pragma once

#include <Windows.h>
#include <algorithm>
#include <string>

namespace U2FakeFull
{
	// shared state (function statics: the project builds as C++14, no inline variables)
	inline int &Mode() { static int M = -1; return M; }              // -1 not read, 0 exclusive, 1 borderless
	inline WNDPROC &OldProc() { static WNDPROC P = nullptr; return P; }
	inline HWND &Hooked() { static HWND W = nullptr; return W; }
	inline bool &Quiet() { static bool Q = false; return Q; }
	// the game must see its window's new size (switching from windowed, it kept its old size and
	// re-set the resolution until it crashed); fullscreenquiet=1 hides the messages again (test)
	inline std::string Folder();
	inline bool QuietOn()
	{
		static int On = -1;
		if (On < 0)
		{
			On = 0;
			FILE *F = nullptr;
			if (!fopen_s(&F, (Folder() + "U2Shaders.ini").c_str(), "r") && F)
			{
				char Line[256];
				while (fgets(Line, sizeof(Line), F))
					if (!_strnicmp(Line, "fullscreenquiet=1", 17))
						On = 1;
				fclose(F);
			}
		}
		return On != 0;
	}

	inline std::string Folder()
	{
		char Path[MAX_PATH] = {};
		HMODULE Self = nullptr;
		GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
			reinterpret_cast<LPCSTR>(&Folder), &Self);
		GetModuleFileNameA(Self, Path, MAX_PATH);
		std::string S(Path);
		return S.substr(0, S.find_last_of("\\/") + 1);
	}

	inline std::string &Pending() { static std::string S; return S; }   // for U2Shaders' log, which starts after us

	inline void Note(const char *Text)
	{
		Pending() += Text;
		Pending() += '\n';
		FILE *F = nullptr;
		if (!fopen_s(&F, (Folder() + "U2Shaders.log").c_str(), "a") && F)
		{
			fprintf(F, "%s\n", Text);
			fclose(F);
		}
	}

	inline bool Borderless()
	{
		if (Mode() >= 0)
			return Mode() != 0;
		Mode() = 1;
		bool Forced = false;
		FILE *F = nullptr;
		if (!fopen_s(&F, (Folder() + "U2Shaders.ini").c_str(), "r") && F)
		{
			char Line[256];
			while (fgets(Line, sizeof(Line), F))
				if (!_strnicmp(Line, "fullscreen=", 11))
				{
					Mode() = _strnicmp(Line + 11, "exclusive", 9) != 0;
					Forced = _strnicmp(Line + 11, "borderless", 10) == 0;
				}
			fclose(F);
		}
		// a d3d9.dll next to the game (dgVoodoo or another wrapper) makes its own fake fullscreen
		// and resizes the window after us; the game then sees its fullscreen window change and
		// drops back to windowed (black screen). Leave fullscreen to it unless fullscreen=borderless.
		char D9[MAX_PATH] = {};
		const HMODULE M = GetModuleHandleA("d3d9.dll");
		if (Mode() != 0 && !Forced && M != nullptr && GetModuleFileNameA(M, D9, MAX_PATH))
		{
			std::string Path(D9);
			Path = Path.substr(0, Path.find_last_of("\\/") + 1);
			if (_stricmp(Path.c_str(), Folder().c_str()) == 0)
			{
				Mode() = 0;
				Note("fullscreen: a d3d9.dll wrapper in the game folder (dgVoodoo?) handles fullscreen; borderless left to it");
			}
		}
		return Mode() != 0;
	}

	// while we restyle, the game doesn't see the window change size (it would rebuild its renderer)
	inline LRESULT CALLBACK Proc(HWND W, UINT Msg, WPARAM WP, LPARAM LP)
	{
		if (Quiet() && QuietOn() && (Msg == WM_SIZE || Msg == WM_MOVE || Msg == WM_WINDOWPOSCHANGED || Msg == WM_WINDOWPOSCHANGING
			|| Msg == WM_STYLECHANGED || Msg == WM_STYLECHANGING || Msg == WM_NCCALCSIZE || Msg == WM_GETMINMAXINFO))
			return DefWindowProcW(W, Msg, WP, LP);
		return CallWindowProcW(OldProc(), W, Msg, WP, LP);
	}

	inline bool &Covered() { static bool C = false; return C; }
	inline LONG &SavedStyle() { static LONG S = 0; return S; }
	inline LONG &SavedEx() { static LONG S = 0; return S; }

	inline void Cover(HWND W)
	{
		if (W == nullptr || !IsWindow(W))
			return;
		if (!Covered())
		{
			SavedStyle() = GetWindowLong(W, GWL_STYLE);
			SavedEx() = GetWindowLong(W, GWL_EXSTYLE);
		}
		Covered() = true;
		if (Hooked() != W)
		{
			OldProc() = reinterpret_cast<WNDPROC>(SetWindowLongPtrW(W, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(&Proc)));
			Hooked() = W;
		}
		MONITORINFO M = { sizeof(M) };
		if (!GetMonitorInfo(MonitorFromWindow(W, MONITOR_DEFAULTTOPRIMARY), &M))
			return;
		const RECT &R = M.rcMonitor;
		const LONG Style = (GetWindowLong(W, GWL_STYLE) & ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX
			| WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME)) | WS_POPUP | WS_VISIBLE;
		const LONG Ex = GetWindowLong(W, GWL_EXSTYLE) & ~(WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_DLGMODALFRAME
			| WS_EX_STATICEDGE | WS_EX_TOPMOST);
		Quiet() = true;
		SetWindowLong(W, GWL_STYLE, Style);
		SetWindowLong(W, GWL_EXSTYLE, Ex);
		SetWindowPos(W, HWND_TOP, R.left, R.top, R.right - R.left, R.bottom - R.top, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
		Quiet() = false;
	}

	// back to windowed after we covered the monitor: a framed window with the requested client
	// size, centred. Left covering it, the game kept seeing the wrong window size and re-set its
	// resolution in a loop until it crashed (ResourceList in UD3DRenderDevice::Flush).
	inline void Uncover(HWND W, UINT CW, UINT CH)
	{
		Covered() = false;
		if (W == nullptr || !IsWindow(W))
			return;
		LONG Style = SavedStyle(), Ex = SavedEx();
		if (!(Style & WS_CAPTION))      // it started fullscreen: the game's usual windowed frame
		{
			Style = (Style & ~WS_POPUP) | WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_VISIBLE;
			Ex = Ex | WS_EX_WINDOWEDGE;
		}
		RECT R = { 0, 0, (LONG)CW, (LONG)CH };
		AdjustWindowRectEx(&R, Style, FALSE, Ex);
		MONITORINFO M = { sizeof(M) };
		GetMonitorInfo(MonitorFromWindow(W, MONITOR_DEFAULTTOPRIMARY), &M);
		const LONG w = R.right - R.left, h = R.bottom - R.top;
		const LONG x = M.rcWork.left + ((M.rcWork.right - M.rcWork.left) - w) / 2, y = M.rcWork.top + ((M.rcWork.bottom - M.rcWork.top) - h) / 2;
		Quiet() = true;
		SetWindowLong(W, GWL_STYLE, Style);
		SetWindowLong(W, GWL_EXSTYLE, Ex);
		SetWindowPos(W, HWND_NOTOPMOST, (std::max)(x, M.rcWork.left), (std::max)(y, M.rcWork.top), w, h, SWP_FRAMECHANGED | SWP_SHOWWINDOW);
		Quiet() = false;
		char Text[128];
		sprintf_s(Text, "fullscreen: back to a %ux%u window", CW, CH);
		Note(Text);
	}

	// CreateDevice / Reset: a fullscreen request becomes a borderless window over the monitor
	inline void Adjust(D3DPRESENT_PARAMETERS &P, HWND Focus)
	{
		if (P.Windowed && Covered())
			Uncover(P.hDeviceWindow ? P.hDeviceWindow : Focus, P.BackBufferWidth, P.BackBufferHeight);
		if (P.Windowed || !Borderless())
			return;
		const HWND W = P.hDeviceWindow ? P.hDeviceWindow : Focus;
		P.Windowed = TRUE;
		P.FullScreen_RefreshRateInHz = 0;
		if (P.PresentationInterval == D3DPRESENT_INTERVAL_DEFAULT)
			P.PresentationInterval = D3DPRESENT_INTERVAL_ONE;     // fullscreen default = vsync; keep it
		Cover(W);
		char Text[160];
		sprintf_s(Text, "fullscreen: borderless window over the monitor (game resolution %ux%u, vsync %d)",
			P.BackBufferWidth, P.BackBufferHeight, P.PresentationInterval != D3DPRESENT_INTERVAL_IMMEDIATE);
		Note(Text);
	}
}
