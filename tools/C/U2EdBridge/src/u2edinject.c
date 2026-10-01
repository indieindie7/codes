/*
 * u2edinject.exe <pid> <dll>              - load a DLL into a running 32-bit process.
 * u2edinject.exe launch <exe> <dll> <cwd> - launch <exe> suspended in <cwd>,
 *   inject <dll>, then resume it. Prints the new process id on success.
 *
 * The launch mode exists because a post-hoc injection (open the process by
 * pid once it has a window, then LoadLibraryW into it) can lose the race
 * against whatever the target does at startup before any window appears --
 * e.g. UnrealEd creates its D3D8 device in the same synchronous init that
 * creates its main window, so by the time a pid-based injector's target
 * process is even visible, that race is usually already lost. Launching
 * CREATE_SUSPENDED and injecting before ResumeThread guarantees our DLL's
 * DllMain (and whatever hooks it installs) runs before the target's own
 * main thread executes a single instruction.
 *
 * Built as a 32-bit program, so LoadLibraryW's address here is the same as in
 * the target (kernel32 sits at the same base in every process of a session).
 * Exit code 0 = loaded (or launched+injected, for "launch").
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

/* inject <dllPath> into an already-open <proc> (any state: running or
   CREATE_SUSPENDED); returns the loaded module's base address (nonzero) on
   success, matching LoadLibraryW's own remote-thread exit code */
static DWORD InjectInto(HANDLE proc, const wchar_t *dllPath)
{
	wchar_t full[MAX_PATH];
	SIZE_T size;
	void *mem;
	HANDLE th;
	LPTHREAD_START_ROUTINE load;
	DWORD code = 0;

	if (!GetFullPathNameW(dllPath, MAX_PATH, full, NULL) || GetFileAttributesW(full) == INVALID_FILE_ATTRIBUTES)
	{ fwprintf(stderr, L"dll not found: %ls\n", dllPath); return 0; }

	size = (wcslen(full) + 1) * sizeof(wchar_t);
	mem = VirtualAllocEx(proc, NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
	if (!mem || !WriteProcessMemory(proc, mem, full, size, NULL))
	{ fwprintf(stderr, L"writing the path failed: %lu\n", GetLastError()); return 0; }

	load = (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
	th = CreateRemoteThread(proc, NULL, 0, load, mem, 0, NULL);
	if (!th)
	{
		fwprintf(stderr, L"CreateRemoteThread failed: %lu\n", GetLastError());
		VirtualFreeEx(proc, mem, 0, MEM_RELEASE);
		return 0;
	}
	WaitForSingleObject(th, 30000);
	GetExitCodeThread(th, &code);   /* the DLL's base address, 0 on failure */
	CloseHandle(th);
	VirtualFreeEx(proc, mem, 0, MEM_RELEASE);
	return code;
}

static int ByPid(wchar_t **argv)
{
	DWORD pid, code;
	HANDLE proc;

	pid = (DWORD)_wtoi(argv[1]);
	proc = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION |
	                   PROCESS_VM_WRITE | PROCESS_VM_READ, FALSE, pid);
	if (!proc) { fwprintf(stderr, L"OpenProcess(%lu) failed: %lu\n", pid, GetLastError()); return 1; }
	code = InjectInto(proc, argv[2]);
	CloseHandle(proc);
	if (!code) { fwprintf(stderr, L"LoadLibraryW failed inside the process\n"); return 1; }
	wprintf(L"loaded %ls into %lu\n", argv[2], pid);
	return 0;
}

static int Launch(int argc, wchar_t **argv)
{
	wchar_t *exe, *dll, *cwd;
	STARTUPINFOW si;
	PROCESS_INFORMATION pi;
	DWORD code;

	if (argc != 5) { fwprintf(stderr, L"usage: u2edinject launch <exe> <dll> <cwd>\n"); return 2; }
	exe = argv[2]; dll = argv[3]; cwd = argv[4];

	memset(&si, 0, sizeof(si));
	si.cb = sizeof(si);
	memset(&pi, 0, sizeof(pi));
	if (!CreateProcessW(exe, NULL, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, cwd, &si, &pi))
	{ fwprintf(stderr, L"CreateProcess failed: %lu\n", GetLastError()); return 1; }

	code = InjectInto(pi.hProcess, dll);
	if (!code)
	{
		fwprintf(stderr, L"LoadLibraryW failed inside the suspended process\n");
		TerminateProcess(pi.hProcess, 1);
		CloseHandle(pi.hThread);
		CloseHandle(pi.hProcess);
		return 1;
	}
	ResumeThread(pi.hThread);
	CloseHandle(pi.hThread);
	CloseHandle(pi.hProcess);
	wprintf(L"%lu\n", pi.dwProcessId);
	return 0;
}

int wmain(int argc, wchar_t **argv)
{
	if (argc >= 2 && !wcscmp(argv[1], L"launch")) return Launch(argc, argv);
	if (argc != 3)
	{
		fwprintf(stderr, L"usage: u2edinject <pid> <dll>\n       u2edinject launch <exe> <dll> <cwd>\n");
		return 2;
	}
	return ByPid(argv);
}
