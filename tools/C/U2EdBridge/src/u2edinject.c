/*
 * u2edinject.exe <pid> <dll path> - load a DLL into a running 32-bit process.
 *
 * Built as a 32-bit program, so LoadLibraryW's address here is the same as in
 * UnrealEd (kernel32 sits at the same base in every process of a session).
 * Exit code 0 = loaded.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

int wmain(int argc, wchar_t **argv)
{
	DWORD pid, code = 0;
	HANDLE proc, th;
	wchar_t full[MAX_PATH];
	SIZE_T size;
	void *mem;
	LPTHREAD_START_ROUTINE load;

	if (argc != 3) { fwprintf(stderr, L"usage: u2edinject <pid> <dll>\n"); return 2; }
	pid = (DWORD)_wtoi(argv[1]);
	if (!GetFullPathNameW(argv[2], MAX_PATH, full, NULL) || GetFileAttributesW(full) == INVALID_FILE_ATTRIBUTES)
	{ fwprintf(stderr, L"dll not found: %ls\n", argv[2]); return 2; }

	proc = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION |
	                   PROCESS_VM_WRITE | PROCESS_VM_READ, FALSE, pid);
	if (!proc) { fwprintf(stderr, L"OpenProcess(%lu) failed: %lu\n", pid, GetLastError()); return 1; }

	size = (wcslen(full) + 1) * sizeof(wchar_t);
	mem = VirtualAllocEx(proc, NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
	if (!mem || !WriteProcessMemory(proc, mem, full, size, NULL))
	{ fwprintf(stderr, L"writing the path failed: %lu\n", GetLastError()); return 1; }

	load = (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
	th = CreateRemoteThread(proc, NULL, 0, load, mem, 0, NULL);
	if (!th) { fwprintf(stderr, L"CreateRemoteThread failed: %lu\n", GetLastError()); return 1; }
	WaitForSingleObject(th, 30000);
	GetExitCodeThread(th, &code);   /* the DLL's base address, 0 on failure */
	CloseHandle(th);
	VirtualFreeEx(proc, mem, 0, MEM_RELEASE);
	CloseHandle(proc);
	if (!code) { fwprintf(stderr, L"LoadLibraryW failed inside the process\n"); return 1; }
	wprintf(L"loaded %ls into %lu\n", full, pid);
	return 0;
}
