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
 */

#pragma once

#include <Windows.h>
#include <string>

namespace U2FakeFull
{
	// shared state (function statics: the project builds as C++14, no inline variables)
	inline int &Mode() { static int M = -1; return M; }              // -1 not read, 0 exclusive, 1 borderless
	inline WNDPROC &OldProc() { static WNDPROC P = nullptr; return P; }
	inline HWND &Hooked() { static HWND W = nullptr; return W; }
	inline bool &Quiet() { static bool Q = false; return Q; }

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
		FILE *F = nullptr;
		if (!fopen_s(&F, (Folder() + "U2Shaders.ini").c_str(), "r") && F)
		{
			char Line[256];
			while (fgets(Line, sizeof(Line), F))
				if (!_strnicmp(Line, "fullscreen=", 11))
					Mode() = _strnicmp(Line + 11, "exclusive", 9) != 0;
			fclose(F);
		}
		return Mode() != 0;
	}

	// while we restyle, the game doesn't see the window change size (it would rebuild its renderer)
	inline LRESULT CALLBACK Proc(HWND W, UINT Msg, WPARAM WP, LPARAM LP)
	{
		if (Quiet() && (Msg == WM_SIZE || Msg == WM_MOVE || Msg == WM_WINDOWPOSCHANGED || Msg == WM_WINDOWPOSCHANGING
			|| Msg == WM_STYLECHANGED || Msg == WM_STYLECHANGING || Msg == WM_NCCALCSIZE || Msg == WM_GETMINMAXINFO))
			return DefWindowProcW(W, Msg, WP, LP);
		return CallWindowProcW(OldProc(), W, Msg, WP, LP);
	}

	inline void Cover(HWND W)
	{
		if (W == nullptr || !IsWindow(W))
			return;
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

	// CreateDevice / Reset: a fullscreen request becomes a borderless window over the monitor
	inline void Adjust(D3DPRESENT_PARAMETERS &P, HWND Focus)
	{
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
