/* AdventUCC - the missing "ucc" for Advent Rising.
   usage: adventucc <commandlet> [parameters]     e.g.  adventucc batchexport EonGame.u class uc C:\out
   Starts advent.exe suspended, loads AdventUCCHook.dll into it and lets the
   game's own launcher initialise the engine; the hook then runs the commandlet.
   ADVENT_SYSTEM = the game's System folder. ADVENTUCC_TIMEOUT = seconds (default 300). */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static int Remote(HANDLE Proc, LPTHREAD_START_ROUTINE Fn, void* Arg, DWORD* Result)
{
	HANDLE T = CreateRemoteThread(Proc, NULL, 0, Fn, Arg, 0, NULL);
	if (!T) return 0;
	WaitForSingleObject(T, 30000);
	GetExitCodeThread(T, Result);
	CloseHandle(T);
	return 1;
}

/* The Steam copy's advent.exe is wrapped: without what Steam gives a game it
   launches (app id, Steam's folder on the path) it stops at "Failed to find Steam". */
static void SteamEnvironment(void)
{
	static wchar_t Steam[1024], Path[32768], New[34000];
	DWORD Size = sizeof(Steam);
	SetEnvironmentVariableW(L"SteamAppId", L"3800");
	SetEnvironmentVariableW(L"SteamGameId", L"3800");
	if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Valve\\Steam", L"SteamPath", RRF_RT_REG_SZ, NULL, Steam, &Size) == ERROR_SUCCESS
		&& GetEnvironmentVariableW(L"PATH", Path, 32768))
	{
		swprintf(New, 34000, L"%ls;%ls", Steam, Path);
		SetEnvironmentVariableW(L"PATH", New);
	}
}

int wmain(int argc, wchar_t** argv)
{
	static wchar_t Sys[1024], Exe[1200], Here[1024], Dll[1200], Work[1200], OutFile[1300], Running[1200], Cmd[4096], Line[4096], Buf[4096];
	int HadRunning;
	STARTUPINFOW Si = { sizeof(Si) };
	PROCESS_INFORMATION Pi;
	HMODULE Local;
	void* Mem;
	DWORD RemoteBase = 0, Ok = 0, Code = 1, Timeout = 300, Wait;
	wchar_t* Slash;
	FILE* F;
	int i;

	if (argc < 2) { wprintf(L"usage: adventucc <commandlet> [parameters]\n"); return 1; }
	if (!GetEnvironmentVariableW(L"ADVENT_SYSTEM", Sys, 1024))
		wcscpy(Sys, L"H:\\SteamLibrary\\steamapps\\common\\Advent Rising\\System");
	if (GetEnvironmentVariableW(L"ADVENTUCC_TIMEOUT", Buf, 64)) Timeout = _wtoi(Buf);
	swprintf(Exe, 1200, L"%ls\\advent.exe", Sys);
	GetModuleFileNameW(NULL, Here, 1024);
	Slash = wcsrchr(Here, 92); if (Slash) *Slash = 0;
	swprintf(Dll, 1200, L"%ls\\AdventUCCHook.dll", Here);
	swprintf(Work, 1200, L"%ls\\work", Here);
	CreateDirectoryW(Work, NULL);
	swprintf(OutFile, 1300, L"%ls\\output.txt", Work);
	DeleteFileW(OutFile);

	Cmd[0] = 0;
	for (i = 1; i < argc; i++) { if (i > 1) wcscat(Cmd, L" "); wcscat(Cmd, argv[i]); }
	SetEnvironmentVariableW(L"ADVENTUCC_CMD", Cmd);
	SetEnvironmentVariableW(L"ADVENTUCC_OUT", OutFile);
	SteamEnvironment();
	/* our own ini/log so the player's settings are never touched; the game only
	   reads an ini that exists, so start them as copies of its defaults */
	swprintf(Buf, 4096, L"%ls\\default.ini", Sys); swprintf(Line, 4096, L"%ls\\AdventUCC.ini", Work); CopyFileW(Buf, Line, TRUE);
	swprintf(Buf, 4096, L"%ls\\defuser.ini", Sys); swprintf(Line, 4096, L"%ls\\AdventUCCUser.ini", Work); CopyFileW(Buf, Line, TRUE);
	/* the engine's "still running" marker: we stop the process ourselves, so remove ours afterwards */
	swprintf(Running, 1200, L"%ls\\Running.ini", Sys);
	HadRunning = GetFileAttributesW(Running) != INVALID_FILE_ATTRIBUTES;
	swprintf(Line, 4096, L"\"%ls\" INI=%ls\\AdventUCC.ini USERINI=%ls\\AdventUCCUser.ini LOG=%ls\\AdventUCC.log", Exe, Work, Work, Work);

	if (!CreateProcessW(Exe, Line, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, Sys, &Si, &Pi))
	{ wprintf(L"could not start %ls (%d)\n", Exe, GetLastError()); return 1; }

	Mem = VirtualAllocEx(Pi.hProcess, NULL, sizeof(Dll), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
	Local = LoadLibraryExW(Dll, NULL, DONT_RESOLVE_DLL_REFERENCES);
	if (!Mem || !Local || !WriteProcessMemory(Pi.hProcess, Mem, Dll, sizeof(Dll), NULL)
		|| !Remote(Pi.hProcess, (LPTHREAD_START_ROUTINE)LoadLibraryW, Mem, &RemoteBase) || !RemoteBase
		|| !Remote(Pi.hProcess, (LPTHREAD_START_ROUTINE)((BYTE*)RemoteBase + ((BYTE*)GetProcAddress(Local, "_Init@4") - (BYTE*)Local)), NULL, &Ok) || !Ok)
	{
		wprintf(L"could not load the hook into the game (%d)\n", GetLastError());
		TerminateProcess(Pi.hProcess, 1);
		Code = 1;
	}
	else
	{
		ResumeThread(Pi.hThread);
		Wait = WaitForSingleObject(Pi.hProcess, Timeout * 1000);
		if (Wait == WAIT_TIMEOUT) { wprintf(L"timed out after %d s (a dialog may be open) - stopping the game process\n", Timeout); TerminateProcess(Pi.hProcess, 99); Code = 99; }
		else GetExitCodeProcess(Pi.hProcess, &Code);
	}
	if (!HadRunning) DeleteFileW(Running);
	F = _wfopen(OutFile, L"r, ccs=UTF-8");
	if (F) { while (fgetws(Buf, 4096, F)) fputws(Buf, stdout); fclose(F); }
	wprintf(L"exit code %d\n", Code);
	return (int)Code;
}
