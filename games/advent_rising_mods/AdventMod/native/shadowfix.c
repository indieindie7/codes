/* shadowfix.c - makes Advent Rising's character shadows (projectors) visible.

   Engine.dll renders a level scene with one function (at 10529590 in the stock DLL).
   Projectors waiting to be drawn sit in a global list (10955B78). The function saves
   that list on entry and empties it, and at the end it should give the caller its
   list back. But it gives the list back first and then runs its last "draw the
   waiting projectors" step. The sky is rendered by a nested call of the same
   function, so the sky pass draws the main pass's waiting shadows, with the sky's
   camera and before the level is drawn over them, and the main pass finds the list
   empty. Every shadow and decal of the frame is lost this way whenever a sky is
   visible, which is nearly always.

   The fix moves the hand-back to after that last step:
     1052BC77  mov edx,[esp+9Ch] / mov [List],edx     -> no-ops (13 bytes)
     1052C05C  mov [List],edi    (empties the list)   -> jmp to a stub that puts the
                                                          caller's list back instead */
#include <windows.h>

void Note(const wchar_t* Fmt, ...);

#define ENGINE_BASE 0x10300000
#define VA(Eng, A) ((BYTE*)(Eng) + ((A) - ENGINE_BASE))

static int Applied;

static int Same(const BYTE* P, const BYTE* Want, int N)
{
	return memcmp(P, Want, N) == 0;
}

static void Write(BYTE* P, const BYTE* Bytes, int N)
{
	DWORD Prot;
	VirtualProtect(P, N, PAGE_EXECUTE_READWRITE, &Prot);
	memcpy(P, Bytes, N);
	VirtualProtect(P, N, Prot, &Prot);
	FlushInstructionCache(GetCurrentProcess(), P, N);
}

int ShadowFixApply(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll");
	BYTE *Restore, *Clear, *Stub;
	DWORD List;
	BYTE WantRestore[13] = { 0x8B, 0x94, 0x24, 0x9C, 0x00, 0x00, 0x00, 0x89, 0x15, 0, 0, 0, 0 };
	BYTE WantClear[6] = { 0x89, 0x3D, 0, 0, 0, 0 };
	BYTE Nops[13];
	BYTE Jump[6];
	BYTE* q;

	if (Applied) return 1;
	if (!Eng) { Note(L"shadowfix: Engine.dll not loaded"); return 0; }
	/* the list's address as it is in this process (the DLL may have been relocated) */
	List = (DWORD)(ULONG_PTR)VA(Eng, 0x10955B78);
	*(DWORD*)(WantRestore + 9) = List;
	*(DWORD*)(WantClear + 2) = List;
	Restore = VA(Eng, 0x1052BC77);
	Clear = VA(Eng, 0x1052C05C);
	if (!Same(Restore, WantRestore, 13) || !Same(Clear, WantClear, 6))
	{
		Note(L"shadowfix: Engine.dll is not the version this fix knows; nothing changed");
		return 0;
	}

	/* the stub: push eax; mov eax,[esp+4+9Ch]; mov [List],eax; pop eax; jmp back */
	Stub = (BYTE*)VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	if (!Stub) return 0;
	q = Stub;
	*q++ = 0x50;
	*q++ = 0x8B; *q++ = 0x84; *q++ = 0x24; *(DWORD*)q = 0x9C + 4; q += 4;
	*q++ = 0xA3; *(DWORD*)q = List; q += 4;
	*q++ = 0x58;
	*q++ = 0xE9; *(LONG*)q = (LONG)((Clear + 6) - (q + 4)); q += 4;

	memset(Nops, 0x90, sizeof(Nops));
	Jump[0] = 0xE9; *(LONG*)(Jump + 1) = (LONG)(Stub - (Clear + 5)); Jump[5] = 0x90;
	Write(Restore, Nops, 13);
	Write(Clear, Jump, 6);
	Applied = 1;
	Note(L"shadowfix: the sky pass no longer draws the level's waiting projectors");
	return 1;
}
