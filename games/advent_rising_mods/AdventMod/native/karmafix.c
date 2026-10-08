/* karmafix.c - frozen ragdolls stay where they lie (research/karma-internals.md).

   KFreezeRagdoll (Engine.dll 1040B4C0, also what the engine runs on the oldest ragdoll once
   MaxRagdolls are down) tears the ragdoll's physics down and sets the body PHYS_Falling, but
   leaves bCollideWorld off from when it went limp: the body falls out of the world. Setting
   PHYS_None instead keeps it lying in its last pose, which is what a frozen corpse should do.
     1040B559  6A 02  push 2 (PHYS_Falling)  ->  6A 00  push 0 (PHYS_None)
   right before the virtual setPhysics call (mov ecx,esi / call [eax+11Ch]). The bytes are
   checked first; on any other Engine.dll nothing is changed. */
#include <windows.h>

void Note(const wchar_t* Fmt, ...);

#define ENGINE_BASE 0x10300000
#define VA(Eng, A) ((BYTE*)(Eng) + ((A) - ENGINE_BASE))

static int Applied;

int KarmaFixApply(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll");
	static const BYTE Want[10] = { 0x6A, 0x02, 0x8B, 0xCE, 0xFF, 0x90, 0x1C, 0x01, 0x00, 0x00 };
	BYTE* P;
	DWORD Prot;

	if (Applied) return 1;
	if (!Eng) { Note(L"karmafix: Engine.dll not loaded"); return 0; }
	P = VA(Eng, 0x1040B559);
	if (memcmp(P, Want, sizeof(Want)) != 0)
	{
		Note(L"karmafix: KFreezeRagdoll isn't the expected code (%02x %02x ...): left alone", P[0], P[1]);
		return 0;
	}
	VirtualProtect(P + 1, 1, PAGE_EXECUTE_READWRITE, &Prot);
	P[1] = 0x00;                    /* PHYS_None */
	VirtualProtect(P + 1, 1, Prot, &Prot);
	FlushInstructionCache(GetCurrentProcess(), P, 2);
	Applied = 1;
	Note(L"karmafix: frozen ragdolls now stay put (KFreezeRagdoll sets PHYS_None, not PHYS_Falling)");
	return 1;
}
