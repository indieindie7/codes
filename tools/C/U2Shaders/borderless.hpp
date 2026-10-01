/**
 * Borderless window for Unreal II (U2Shaders fork).
 *
 * In windowed mode the game window loses its frame and covers its whole monitor,
 * like a fullscreen game but without the mode switch. Unreal II follows a window
 * resize by resizing its viewport, so the picture renders at the monitor's size.
 *
 * Done from a background thread with asynchronous window requests, checked every
 * two seconds (the game restyles its window on resolution changes): the game
 * rebuilds its renderer on a resize, which must not happen inside CreateDevice or
 * Present (that crashed the game in UD3DRenderDevice::Present).
 *
 * Experimental, off by default (it caused intermittent runtime aborts; dgVoodoo's
 * fake fullscreen is the working route): "borderless=1" in System\U2Shaders.ini
 * turns it on.
 */

#pragma once

#include <Windows.h>
#include <string>

namespace U2Borderless
{
	// shared state (function statics: the project builds as C++14, no inline variables)
	inline HWND &Window() { static HWND W = nullptr; return W; }
	inline int &Enabled() { static int E = -1; return E; }   // -1 = not read yet

	inline bool IsEnabled()
	{
		if (Enabled() >= 0)
			return Enabled() != 0;
		Enabled() = 0;
		char Path[MAX_PATH] = {};
		HMODULE Self = nullptr;
		GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
			reinterpret_cast<LPCSTR>(&IsEnabled), &Self);
		GetModuleFileNameA(Self, Path, MAX_PATH);
		std::string Ini(Path);
		Ini = Ini.substr(0, Ini.find_last_of("\\/") + 1) + "U2Shaders.ini";
		FILE *F = nullptr;
		if (!fopen_s(&F, Ini.c_str(), "r") && F)
		{
			char Line[256];
			while (fgets(Line, sizeof(Line), F))
				if (!_strnicmp(Line, "borderless=", 11))
					Enabled() = atoi(Line + 11);
			fclose(F);
		}
		return Enabled() != 0;
	}

	// strip the frame and cover the window's monitor (no-op when already so)
	inline void Apply(HWND W)
	{
		if (W == nullptr || !IsWindow(W) || IsIconic(W))
			return;                                 // gone, or minimised (alt-tab): leave it be
		MONITORINFO M = { sizeof(M) };
		if (!GetMonitorInfo(MonitorFromWindow(W, MONITOR_DEFAULTTONEAREST), &M))
			return;
		const RECT &R = M.rcMonitor;
		const LONG Style = GetWindowLong(W, GWL_STYLE);
		const LONG Want = (Style & ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME)) | WS_POPUP;
		const LONG Ex = GetWindowLong(W, GWL_EXSTYLE);
		const LONG WantEx = Ex & ~(WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_DLGMODALFRAME | WS_EX_STATICEDGE);
		RECT Now = {};
		GetWindowRect(W, &Now);
		if (Style == Want && Ex == WantEx && EqualRect(&Now, &R))
			return;
		SetWindowLong(W, GWL_STYLE, Want);
		SetWindowLong(W, GWL_EXSTYLE, WantEx);
		SetWindowPos(W, HWND_TOP, R.left, R.top, R.right - R.left, R.bottom - R.top,
			SWP_FRAMECHANGED | SWP_NOOWNERZORDER | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS);
	}

	inline DWORD WINAPI Watch(LPVOID)
	{
		Sleep(1500);                                // let the device settle first
		for (;;)
		{
			const HWND W = Window();
			if (W != nullptr && !IsWindow(W))
				return 0;                           // the game's window is gone
			Apply(W);
			Sleep(2000);
		}
	}

	// the device's window: remember it and start watching it (once)
	inline void Remember(HWND W)
	{
		if (W == nullptr || !IsEnabled())
			return;
		const bool First = Window() == nullptr;
		Window() = W;
		if (First)
		{
			const HANDLE T = CreateThread(nullptr, 0, Watch, nullptr, 0, nullptr);
			if (T)
				CloseHandle(T);
		}
	}
}
