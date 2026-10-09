/* armour.c - where a shot lands on an enemy's skin: armour plate or flesh (ARMOUR.md, "where
   the plates are").

   The engine only says where a hit met the collision cylinder. This skins the character's
   own triangles with the pose the engine holds right now (the mesh instance's per-bone
   FCoords at +0xB4, the same ones GetBoneCoords reads, with the weights and reference pose
   exported from the mesh by tools/make_armour_data.py into <game>\AdventMod\Armour\<mesh>.amesh)
   and intersects the shot's ray with them. The triangle hit carries its armour flag (the
   mesh's one material section split per triangle by the game's own chrome mask), its UVs
   and its bones.

   Script: "ArmourHit <pawn name> <class name> ox oy oz dx dy dz" (world origin and direction)
   answers true when the ray meets the mesh on an ARMOUR triangle; "ArmourLast" then answers
   whether the ray met the mesh at all (flesh = ArmourLast and not ArmourHit), "ArmourLog 1|0"
   turns the per-hit log line on. Every hit is noted in AdventNative.log with the bone, the
   triangle, the UV, the world point and the time it took (tools read it back for the contact sheet).

   Conventions, measured rather than assumed: the bone FCoords rows (basis vectors or rotation
   rows, as footik.c learns it) are told from the reference skeleton's local positions on the
   first query per mesh; the ref skeleton's names are checked against the engine's before any
   data is trusted. Everything runs inside __try: a fault answers "no hit".

   The pawn is found by name and class through Core's object table, a scan of every object per
   query (0.7-1.3 ms of the cast's time in game, ARMOUR.md); the last few pawns found are kept
   by name with their table index, and a repeat hit on one of them skips the scan when its slot
   still holds the same pointer, not marked for deletion, with the same name and class. */
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

void Note(const wchar_t* Fmt, ...);

typedef struct { float x, y, z; } Vec;
typedef struct { Vec O, X, Y, Z; } FCoords;
typedef struct { float m[3][3]; } Mat3;

typedef float* (__fastcall *MeshToWorld_t)(void* Inst, void* Edx, float* Out16);
typedef const wchar_t* (__fastcall *GetName_t)(void* This, void* Edx);
typedef void* (__fastcall *GetClass_t)(void* This, void* Edx);
typedef const wchar_t* (__fastcall *FNameStr_t)(const DWORD* Name, void* Edx);
typedef struct { void** Data; int Num; int Max; } ObjArray;

static MeshToWorld_t MeshToWorld;
static GetName_t GetName;
static GetClass_t GetClass;
static FNameStr_t FNameStr;
static ObjArray* Objs;
static int Ready, Tried, LogOn = 1;
static LARGE_INTEGER Freq;

/* ------------------------------------------------------------ the data */

typedef struct { char Name[32]; int Parent; Vec LocalPos; Mat3 RefR; Vec RefO; Mat3 RefInv; } ABone;
typedef struct { Vec P; int Bone[4]; float W[4]; } AVert;
typedef struct { unsigned short V[3]; float UV[3][2]; unsigned char Armour, Section; } AFace;
typedef struct {
	wchar_t Mesh[48];
	int NB, NV, NF, Conv, Checked, Bad, Undecided;
	ABone* B; AVert* V; AFace* F;
	Vec* Skinned;                    /* scratch, NV */
	char Mats[8][32];
} AMesh;

#define MAXMESHES 16
static AMesh Meshes[MAXMESHES];
static int NMeshes;

/* the last test, for ArmourLast and the log */
static int LastHit, LastArmour, LastFace, LastBone;
static float LastU, LastV, LastDist, LastUs;
static Vec LastPoint;

static Vec V3(float x, float y, float z) { Vec r; r.x = x; r.y = y; r.z = z; return r; }
static Vec Add(Vec a, Vec b) { return V3(a.x + b.x, a.y + b.y, a.z + b.z); }
static Vec Sub(Vec a, Vec b) { return V3(a.x - b.x, a.y - b.y, a.z - b.z); }
static Vec Mul(Vec a, float s) { return V3(a.x * s, a.y * s, a.z * s); }
static float Dot(Vec a, Vec b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static Vec Cross(Vec a, Vec b) { return V3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static float Len(Vec a) { return (float)sqrt(Dot(a, a)); }
static Mat3 Tr(Mat3 a) { Mat3 r; int i, j; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) r.m[i][j] = a.m[j][i]; return r; }
static Mat3 MM(Mat3 a, Mat3 b) { Mat3 r; int i, j, k; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) { float s = 0; for (k = 0; k < 3; k++) s += a.m[i][k] * b.m[k][j]; r.m[i][j] = s; } return r; }
static Vec MV(Mat3 a, Vec v) { return V3(a.m[0][0] * v.x + a.m[0][1] * v.y + a.m[0][2] * v.z, a.m[1][0] * v.x + a.m[1][1] * v.y + a.m[1][2] * v.z, a.m[2][0] * v.x + a.m[2][1] * v.y + a.m[2][2] * v.z); }

static int Resolve(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll"), Core = GetModuleHandleW(L"Core.dll");
	if (Tried) return Ready;
	Tried = 1;
	QueryPerformanceFrequency(&Freq);
	if (!Eng || !Core) return 0;
	MeshToWorld = (MeshToWorld_t)GetProcAddress(Eng, "?MeshToWorld@USkeletalMeshInstance@@UAE?AVFMatrix@@XZ");
	GetName = (GetName_t)GetProcAddress(Core, "?GetName@UObject@@QBEPBGXZ");
	GetClass = (GetClass_t)GetProcAddress(Core, "?GetClass@UObject@@QBEPAVUClass@@XZ");
	FNameStr = (FNameStr_t)GetProcAddress(Core, "??DFName@@QBEPBGXZ");
	Objs = (ObjArray*)GetProcAddress(Core, "?GObjObjects@UObject@@1V?$TArray@PAVUObject@@@@A");
	Ready = MeshToWorld && GetName && GetClass && FNameStr && Objs;
	if (!Ready) Note(L"armour: an engine export is missing (MeshToWorld %p GetName %p GetClass %p FName %p GObjObjects %p): off", MeshToWorld, GetName, GetClass, FNameStr, Objs);
	return Ready;
}

/* <game>\AdventMod\Armour\<mesh>.amesh (the game runs from System: one up) */
static AMesh* Load(const wchar_t* MeshName)
{
	wchar_t Path[MAX_PATH];
	FILE* F;
	char Tag[4];
	int Ver, i, k;
	AMesh* M;
	for (i = 0; i < NMeshes; i++) if (!_wcsicmp(Meshes[i].Mesh, MeshName)) return Meshes[i].Bad ? NULL : &Meshes[i];
	if (NMeshes >= MAXMESHES) return NULL;
	M = &Meshes[NMeshes++];
	memset(M, 0, sizeof(*M));
	wcsncpy(M->Mesh, MeshName, 47);
	swprintf(Path, MAX_PATH, L"..\\AdventMod\\Armour\\%ls.amesh", MeshName);
	F = _wfopen(Path, L"rb");
	if (!F) { M->Bad = 1; Note(L"armour: no data for mesh %ls (%ls): the bone table decides", MeshName, Path); return NULL; }
	if (fread(Tag, 1, 4, F) != 4 || memcmp(Tag, "AMSH", 4) || fread(&Ver, 4, 1, F) != 1 || Ver != 1 || fread(&M->NB, 4, 1, F) != 1 || fread(&M->NV, 4, 1, F) != 1 || fread(&M->NF, 4, 1, F) != 1
		|| M->NB < 1 || M->NB > 512 || M->NV < 3 || M->NV > 65535 || M->NF < 1 || M->NF > 200000)
	{ fclose(F); M->Bad = 1; Note(L"armour: %ls isn't an AMSH v1 file", Path); return NULL; }
	M->B = (ABone*)calloc(M->NB, sizeof(ABone));
	M->V = (AVert*)calloc(M->NV, sizeof(AVert));
	M->F = (AFace*)calloc(M->NF, sizeof(AFace));
	M->Skinned = (Vec*)calloc(M->NV, sizeof(Vec));
	for (i = 0; i < M->NB; i++)
	{
		ABone* B = &M->B[i];
		if (fread(B->Name, 32, 1, F) != 1 || fread(&B->Parent, 4, 1, F) != 1 || fread(&B->LocalPos, 12, 1, F) != 1 || fread(&B->RefR, 36, 1, F) != 1 || fread(&B->RefO, 12, 1, F) != 1) { M->Bad = 1; break; }
		B->RefInv = Tr(B->RefR);   /* a rotation: its inverse is its transpose */
	}
	for (i = 0; i < M->NV && !M->Bad; i++)
	{
		AVert* V = &M->V[i];
		if (fread(&V->P, 12, 1, F) != 1) { M->Bad = 1; break; }
		for (k = 0; k < 4; k++) if (fread(&V->Bone[k], 4, 1, F) != 1 || fread(&V->W[k], 4, 1, F) != 1 || V->Bone[k] < 0 || V->Bone[k] >= M->NB) { M->Bad = 1; break; }
	}
	for (i = 0; i < M->NF && !M->Bad; i++)
	{
		AFace* Fc = &M->F[i];
		if (fread(Fc->V, 6, 1, F) != 1 || fread(Fc->UV, 24, 1, F) != 1 || fread(&Fc->Armour, 1, 1, F) != 1 || fread(&Fc->Section, 1, 1, F) != 1 || Fc->V[0] >= M->NV || Fc->V[1] >= M->NV || Fc->V[2] >= M->NV) { M->Bad = 1; break; }
	}
	for (i = 0; i < 8 && !M->Bad; i++) if (fread(M->Mats[i], 32, 1, F) != 1) break;
	fclose(F);
	if (M->Bad) { Note(L"armour: %ls is cut short or inconsistent: refused", Path); return NULL; }
	{
		int na = 0;
		for (i = 0; i < M->NF; i++) na += M->F[i].Armour != 0;
		Note(L"armour: %ls loaded: %d bones, %d vertices, %d triangles (%d armour)", MeshName, M->NB, M->NV, M->NF, na);
	}
	return M;
}

/* the last pawns found, by name and class, with where they sat in the object table */
typedef struct { void* Actor; int Index; wchar_t Name[48]; wchar_t Class[48]; } ActorCacheEntry;
#define ACTOR_CACHE 8
static ActorCacheEntry ActorCache[ACTOR_CACHE];
static int ActorCacheNext, CacheHits, CacheScans;
static const wchar_t* LastLookup = L"scan";

/* is this cached pointer still that object: its slot unchanged, alive, the same name and class */
static int CacheValid(const ActorCacheEntry* E)
{
	void* O = E->Actor;
	void* C;
	const wchar_t* N;
	if (!O || E->Index < 0 || E->Index >= Objs->Num || Objs->Data[E->Index] != O) return 0;
	if (*(DWORD*)((BYTE*)O + 0x34) & 0x80) return 0;
	N = GetName(O, NULL);
	if (!N || _wcsicmp(N, E->Name)) return 0;
	C = GetClass(O, NULL);
	if (!C) return 0;
	N = GetName(C, NULL);
	return N && !_wcsicmp(N, E->Class);
}

static void* FindActor(const wchar_t* Name, const wchar_t* ClassName)
{
	int i, BestI = -1;
	void* Best = NULL;
	ActorCacheEntry* E;
	for (i = 0; i < ACTOR_CACHE; i++)
	{
		E = &ActorCache[i];
		if (!E->Actor || _wcsicmp(E->Name, Name) || _wcsicmp(E->Class, ClassName)) continue;
		if (CacheValid(E)) { CacheHits++; LastLookup = L"cache"; return E->Actor; }
		E->Actor = NULL;          /* gone, or the name is another object's now: scan */
		break;
	}
	CacheScans++;
	LastLookup = L"scan";
	for (i = 0; i < Objs->Num; i++)
	{
		void* O = Objs->Data[i];
		void* C;
		const wchar_t* N;
		if (!O) continue;
		C = GetClass(O, NULL);
		if (!C) continue;
		N = GetName(C, NULL);
		if (!N || _wcsicmp(N, ClassName)) continue;
		N = GetName(O, NULL);
		if (!N || _wcsicmp(N, Name)) continue;
		if (*(DWORD*)((BYTE*)O + 0x34) & 0x80) continue;
		Best = O;
		BestI = i;
	}
	if (Best)
	{
		E = &ActorCache[ActorCacheNext];
		ActorCacheNext = (ActorCacheNext + 1) % ACTOR_CACHE;
		E->Actor = Best; E->Index = BestI;
		wcsncpy(E->Name, Name, 47); E->Name[47] = 0;
		wcsncpy(E->Class, ClassName, 47); E->Class[47] = 0;
	}
	return Best;
}

/* the engine's ref skeleton (FMeshBone 0x40: FName +0, ParentIndex +0x34) against ours */
static int CheckSkeleton(AMesh* M, void* Mesh)
{
	BYTE* Arr = *(BYTE**)((BYTE*)Mesh + 0x1DC);
	int Num = *(int*)((BYTE*)Mesh + 0x1E0), i, bad = 0;
	if (!Arr || Num != M->NB) { Note(L"armour: %ls: the engine has %d bones, the data %d: refused", M->Mesh, Num, M->NB); return 0; }
	for (i = 0; i < Num; i++)
	{
		const wchar_t* N = FNameStr((DWORD*)(Arr + i * 0x40), NULL);
		wchar_t Ours[32];
		int P = *(int*)(Arr + i * 0x40 + 0x34);
		MultiByteToWideChar(CP_ACP, 0, M->B[i].Name, -1, Ours, 32);
		if (!N || _wcsicmp(N, Ours) || (i > 0 && P != M->B[i].Parent)) { if (bad < 3) Note(L"armour: %ls: bone %d is %ls (parent %d) in the engine, %ls (parent %d) in the data", M->Mesh, i, N ? N : L"?", P, Ours, M->B[i].Parent); bad++; }
	}
	if (bad) { Note(L"armour: %ls: %d bones differ: refused", M->Mesh, bad); return 0; }
	return 1;
}

static Mat3 RotOf(const FCoords* C, int Conv)
{
	Mat3 r;
	r.m[0][0] = C->X.x; r.m[0][1] = C->X.y; r.m[0][2] = C->X.z;
	r.m[1][0] = C->Y.x; r.m[1][1] = C->Y.y; r.m[1][2] = C->Y.z;
	r.m[2][0] = C->Z.x; r.m[2][1] = C->Z.y; r.m[2][2] = C->Z.z;
	return Conv == 1 ? Tr(r) : r;
}

/* which way the FCoords rows go: the convention under which every child's offset, expressed in
   its parent's frame, is the ref skeleton's local position */
static int LearnConv(AMesh* M, const FCoords* Bones)
{
	float e[3] = { 0, 0, 0 };
	int i, c, n = 0;
	for (i = 1; i < M->NB; i++)
	{
		int p = M->B[i].Parent;
		Vec d = Sub(Bones[i].O, Bones[p].O);
		if (p < 0 || p >= M->NB || Len(M->B[i].LocalPos) < 1) continue;
		for (c = 1; c <= 2; c++)
		{
			Mat3 R = RotOf(&Bones[p], c);
			Vec local = MV(Tr(R), d);       /* mesh = R local  ->  local = R^T mesh */
			e[c] += Len(Sub(local, M->B[i].LocalPos));
		}
		n++;
	}
	if (!n) return 0;
	/* a pose near the reference (every bone's rotation near identity) can't tell the two apart:
	   not decided yet, asked again on the next query (the offline check: both 0.00 in the ref pose) */
	if (fabs(e[1] - e[2]) / n < 0.25f) return 0;
	Note(L"armour: %ls: bone coords convention %d (rows as basis vectors: %.2f, rows as rotation rows: %.2f units per bone over %d bones)", M->Mesh, e[1] < e[2] ? 1 : 2, e[1] / n, e[2] / n, n);
	return e[1] < e[2] ? 1 : 2;
}

/* Moeller-Trumbore, both windings */
static int RayTri(Vec O, Vec D, Vec A, Vec B, Vec C, float* T, float* U, float* Vv)
{
	Vec e1 = Sub(B, A), e2 = Sub(C, A), p = Cross(D, e2), q, s;
	float det = Dot(e1, p), inv, u, v, t;
	if (fabs(det) < 1e-8f) return 0;
	inv = 1.0f / det;
	s = Sub(O, A);
	u = Dot(s, p) * inv;
	if (u < 0 || u > 1) return 0;
	q = Cross(s, e1);
	v = Dot(D, q) * inv;
	if (v < 0 || u + v > 1) return 0;
	t = Dot(e2, q) * inv;
	if (t < 0) return 0;
	*T = t; *U = u; *Vv = v;
	return 1;
}

/* a world point/direction into mesh space through the inverse of MeshToWorld (row vectors) */
static int Invert4(const float* M, float* Inv)
{
	float a = M[0], b = M[1], c = M[2], d = M[4], e = M[5], f = M[6], g = M[8], h = M[9], i = M[10];
	float det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
	if (fabs(det) < 1e-12) return 0;
	det = 1.0f / det;
	Inv[0] = (e * i - f * h) * det; Inv[1] = (c * h - b * i) * det; Inv[2] = (b * f - c * e) * det;
	Inv[3] = (f * g - d * i) * det; Inv[4] = (a * i - c * g) * det; Inv[5] = (c * d - a * f) * det;
	Inv[6] = (d * h - e * g) * det; Inv[7] = (b * g - a * h) * det; Inv[8] = (a * e - b * d) * det;
	return 1;
}
static Vec RowMul(const float* Inv9, Vec w) { return V3(w.x * Inv9[0] + w.y * Inv9[3] + w.z * Inv9[6], w.x * Inv9[1] + w.y * Inv9[4] + w.z * Inv9[7], w.x * Inv9[2] + w.y * Inv9[5] + w.z * Inv9[8]); }
static Vec ToWorld(const float* M, Vec m) { return V3(m.x * M[0] + m.y * M[4] + m.z * M[8] + M[12], m.x * M[1] + m.y * M[5] + m.z * M[9] + M[13], m.x * M[2] + m.y * M[6] + m.z * M[10] + M[14]); }

/* the mesh skinned with the pose Bones (mesh space), and the nearest triangle on the ray O+tD
   (mesh space): its index, or -1 */
static int CastRay(AMesh* A, const FCoords* Bones, Vec Om, Vec Dm, float* OutT, float* OutU, float* OutV)
{
	static Mat3 R[512];
	int i, c, best = -1;
	float bestT = 1e30f;
	/* skin: v = O_b + R_b (RefInv_b (p - RefO_b)), blended over the weights */
	for (i = 0; i < A->NB; i++) R[i] = RotOf(&Bones[i], A->Conv);
	for (i = 0; i < A->NV; i++)
	{
		AVert* V = &A->V[i];
		Vec s = V3(0, 0, 0);
		for (c = 0; c < 4; c++)
		{
			int b = V->Bone[c];
			Vec local, posed;
			if (V->W[c] <= 0) continue;
			local = MV(A->B[b].RefInv, Sub(V->P, A->B[b].RefO));
			posed = Add(Bones[b].O, MV(R[b], local));
			s = Add(s, Mul(posed, V->W[c]));
		}
		A->Skinned[i] = s;
	}
	for (i = 0; i < A->NF; i++)
	{
		AFace* Fc = &A->F[i];
		float t, u, v;
		if (RayTri(Om, Dm, A->Skinned[Fc->V[0]], A->Skinned[Fc->V[1]], A->Skinned[Fc->V[2]], &t, &u, &v) && t < bestT) { bestT = t; best = i; *OutU = u; *OutV = v; }
	}
	*OutT = bestT;
	return best;
}

static int Test(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	Vec O, D;
	void *Actor, *Inst, *Mesh;
	const FCoords* Bones;
	int NumBones, best = -1;
	float M16[16], Inv[9], bestT = 1e30f, bu = 0, bv = 0;
	Vec Om, Dm;
	AMesh* A;
	LARGE_INTEGER T0, T1;

	LastHit = LastArmour = 0;
	if (swscanf(Arg, L"%47s %47s %f %f %f %f %f %f", Name, Class, &O.x, &O.y, &O.z, &D.x, &D.y, &D.z) != 8) { Note(L"armour: bad test '%ls'", Arg); return 0; }
	if (!Resolve()) return 0;
	QueryPerformanceCounter(&T0);
	Actor = FindActor(Name, Class);
	if (!Actor) { Note(L"armour: no actor %ls (%ls)", Name, Class); return 0; }
	Inst = *(void**)((BYTE*)Actor + 0xF8);
	Mesh = *(void**)((BYTE*)Actor + 0xD4);
	if (!Inst || !Mesh) { Note(L"armour: %ls has no mesh instance", Name); return 0; }
	A = Load(GetName(Mesh, NULL));
	if (!A) return 0;
	if (!A->Checked) { A->Checked = 1; if (!CheckSkeleton(A, Mesh)) { A->Bad = 1; return 0; } }
	Bones = *(const FCoords**)((BYTE*)Inst + 0xB4);
	NumBones = *(int*)((BYTE*)Inst + 0xB8);
	if (!Bones || NumBones < A->NB) { Note(L"armour: %ls: the instance has %d posed bones, the data needs %d", Name, NumBones, A->NB); return 0; }
	if (!A->Conv)
	{
		/* undecided on this pose: the rotation-rows reading is used for this query, unlocked */
		A->Conv = LearnConv(A, Bones);
		if (!A->Conv) { A->Conv = 2; A->Undecided = 1; } else A->Undecided = 0;
	}
	/* the ray in mesh space */
	MeshToWorld(Inst, NULL, M16);
	if (!Invert4(M16, Inv)) return 0;
	Om = RowMul(Inv, V3(O.x - M16[12], O.y - M16[13], O.z - M16[14]));
	Dm = RowMul(Inv, D);
	if (Len(Dm) < 1e-6f) return 0;
	Dm = Mul(Dm, 1.0f / Len(Dm));
	best = CastRay(A, Bones, Om, Dm, &bestT, &bu, &bv);
	if (A->Undecided) A->Conv = 0;
	QueryPerformanceCounter(&T1);
	LastUs = (float)((T1.QuadPart - T0.QuadPart) * 1e6 / Freq.QuadPart);
	if (best < 0)
	{
		if (LogOn) Note(L"armour: %ls: the ray from %.0f %.0f %.0f along %.2f %.2f %.2f misses the mesh (%.0f us, actor by %ls)", Name, O.x, O.y, O.z, D.x, D.y, D.z, LastUs, LastLookup);
		return 0;
	}
	{
		AFace* Fc = &A->F[best];
		float w0 = 1 - bu - bv;
		int vb = Fc->V[0], bb;
		Vec pm = Add(Mul(A->Skinned[Fc->V[0]], w0), Add(Mul(A->Skinned[Fc->V[1]], bu), Mul(A->Skinned[Fc->V[2]], bv)));
		LastHit = 1;
		LastArmour = Fc->Armour != 0;
		LastFace = best;
		LastU = w0 * Fc->UV[0][0] + bu * Fc->UV[1][0] + bv * Fc->UV[2][0];
		LastV = w0 * Fc->UV[0][1] + bu * Fc->UV[1][1] + bv * Fc->UV[2][1];
		LastDist = bestT;
		LastPoint = ToWorld(M16, pm);
		/* the heaviest bone of the nearest corner */
		if (bu > w0 && bu > bv) vb = Fc->V[1]; else if (bv > w0 && bv > bu) vb = Fc->V[2];
		bb = A->V[vb].Bone[0];
		LastBone = bb;
		if (LogOn)
		{
			wchar_t BN[32], MT[32];
			MultiByteToWideChar(CP_ACP, 0, A->B[bb].Name, -1, BN, 32);
			MultiByteToWideChar(CP_ACP, 0, A->Mats[Fc->Section < 8 ? Fc->Section : 0], -1, MT, 32);
			Note(L"armour hit: %ls %ls armour=%ls uv=%.3f,%.3f tri=%d section=%ls at %.1f %.1f %.1f mesh %.1f %.1f %.1f dist=%.0f (%.0f us, actor by %ls)", Name, BN, LastArmour ? L"yes" : L"no", LastU, LastV, best, MT, LastPoint.x, LastPoint.y, LastPoint.z, pm.x, pm.y, pm.z, bestT, LastUs, LastLookup);
		}
	}
	return LastArmour;
}

static int Guarded(const wchar_t* Arg)
{
	__try { return Test(Arg); }
	__except (EXCEPTION_EXECUTE_HANDLER) { Note(L"armour: exception in the test (%ls): no hit", Arg); LastHit = LastArmour = 0; return 0; }
}

/* "ArmourHit ...", "ArmourLast", "ArmourLog 1|0", "ArmourReady", "ArmourStats" (the actor cache's hits and scans, logged) */
int ArmourCommand(const wchar_t* Cmd)
{
	if (!_wcsnicmp(Cmd, L"ArmourHit ", 10)) return Guarded(Cmd + 10);
	if (!_wcsicmp(Cmd, L"ArmourLast")) return LastHit;
	if (!_wcsicmp(Cmd, L"ArmourStats")) { Note(L"armour: actor lookups: %d from the cache, %d scans of the object table", CacheHits, CacheScans); return CacheHits + CacheScans; }
	if (!_wcsnicmp(Cmd, L"ArmourLog ", 10)) { LogOn = _wtoi(Cmd + 10) != 0; return 1; }
	if (!_wcsicmp(Cmd, L"ArmourReady")) return Resolve();
	return 0;
}
