/* footik.c - native foot IK for Advent Rising (research/native-animation-hooks.md, hook point 1;
   report "Dynamic body kinematics", slices K6 + K9).

   The engine's own bone "directors" (USkeletalMeshInstance::SetBoneDirection) are applied inside
   the pose build, bone by bone during the hierarchy walk, after the bone's mesh-space coords are
   final and before its children are placed. A director with a Space code the engine doesn't know
   (99) calls its world-spacer callback (SetWorldSpacerFunction, FCoords* __cdecl fn(FCoords* ret,
   AActor*, int bone, int director, USkeletalMeshInstance*)) and takes the axes it returns; the
   bone's origin is kept. So, per leg, three directors (thigh, calf, foot) give a two-bone IK that
   is skinned in the same frame:
     thigh: trace the floor under the animated ankle, pick the ankle target (clamped lift/drop),
            solve the knee (the animated knee gives the bend plane) and rotate the thigh there;
     calf:  rotate the calf so the ankle reaches the target;
     foot:  undo both rotations on the foot, so it keeps the orientation the clip gave it; then, with
            the tilt on, turn it level with the floor traced under it (pitch and roll only: the
            smallest rotation taking up onto the floor's normal has a level axis, so the clip's yaw
            stays; at most MaxTilt degrees; the normal eased at Gain as the lift is).
   No pelvis move in this pass: Hips is EonEngine's (orient-to-floor), so the reach is what the
   knee's bend allows; the uphill foot lifts (MaxLift), the downhill one drops a little (MaxDrop).

   Script (ModFeet) installs it per pawn: "FootIKConfig drop lift gain log [tilt]", "FootIK <pawn name>
   <class name> <left thigh> <left calf> <left foot> <right...> <standing collision height>" (bone
   indices from MatchRefBone),
   "FootIKOff <pawn name> <class name>". The pawn is found through Core's GObjObjects.

   Safety: every engine entry point is an export resolved by name and the mesh instance's vtable
   slots must point at those very exports, the ref skeleton's parent chain must be thigh->calf->
   foot, the callback is wrapped in __try/__except and answers with the bone's current axes (no
   change) on any doubt; ragdolls (PHYS_KarmaRagDoll) and deleted actors are left alone.
   Nothing here touches the engine's own directors (spine*, Hips, aim bones). */
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

void Note(const wchar_t* Fmt, ...);

typedef struct { float x, y, z; } Vec;
typedef struct { Vec O, X, Y, Z; } FCoords;          /* 48 bytes, as the engine's */
typedef struct { float m[3][3]; } Mat3;              /* mesh = R * local (column basis) */

/* __thiscall through __fastcall with a dummy edx */
typedef int (__fastcall *SetBoneDirection_t)(void* Inst, void* Edx, DWORD Name, int Pitch, int Yaw, int Roll, float tx, float ty, float tz, float Alpha, int Space, int Pre);
typedef int (__fastcall *SetWorldSpacer_t)(void* Inst, void* Edx, DWORD Name, void* Fn, int Pre);
typedef int (__fastcall *MatchRefBone_t)(void* Inst, void* Edx, DWORD Name);
typedef float* (__fastcall *MeshToWorld_t)(void* Inst, void* Edx, float* Out16);
typedef int (__fastcall *SingleLineCheck_t)(void* Level, void* Edx, void* Hit, void* Source, const Vec* End, const Vec* Start, DWORD Flags, float ex, float ey, float ez);
typedef const wchar_t* (__fastcall *GetName_t)(void* This, void* Edx);
typedef void* (__fastcall *GetClass_t)(void* This, void* Edx);
typedef const wchar_t* (__fastcall *FNameStr_t)(const DWORD* Name, void* Edx);
typedef struct { void** Data; int Num; int Max; } ObjArray;

static SetBoneDirection_t SetBoneDirection;
static SetWorldSpacer_t SetWorldSpacer;
static MatchRefBone_t MatchRefBone;
static MeshToWorld_t MeshToWorld;
static SingleLineCheck_t SingleLineCheck;
static GetName_t GetName;
static GetClass_t GetClass;
static FNameStr_t FNameStr;
static ObjArray* Objs;
static int Ready, Tried;

/* config (FootIKConfig) */
static float MaxDrop = 12, MaxLift = 35, Gain = 10, MaxTilt = 25;
static int LogOn, TiltOn = 1;

/* the bone FCoords convention: 1 = rows are the bone's basis vectors in mesh space,
   2 = rows are the rows of the local->mesh rotation; 0 = not known yet (nothing is changed) */
static int Conv;
static float ConvSumA, ConvSumB; static int ConvN; static Vec ConvPrevA, ConvPrevB; static int ConvHavePrev, ConvGaveUp;

typedef struct {
	int Thigh, Calf, Foot;
	DWORD NameT, NameC, NameF;
	Vec KneeLocal, AnkleLocal;       /* child origin in the parent's frame (constant) */
	int HaveKnee, HaveAnkle, HaveCalfLocal;
	Mat3 CalfLocal;                  /* the calf's animated rotation relative to the thigh, last frame */
	float L1, L2;
	Mat3 QThigh, QCalf;              /* this frame's corrections (mesh space) */
	int PendingCalf, PendingFoot;
	Vec DeltaMesh;                   /* this frame's ankle move, mesh space */
	float Lift;                      /* smoothed world dz */
	Vec FloorN, TiltN;               /* the floor's normal under the ankle (world), and the eased one the foot follows */
	int HaveFloorN, HaveTilt;
	float Dt, TiltDeg;               /* this frame's step, and the tilt applied (log) */
	float LastGap, LastGround;       /* log */
	int Solves;
	LARGE_INTEGER LastT;
	float AnimZ, TargetZ, GroundZ, FloorZ;   /* diagnostics (world) */
	DWORD LastDiag;
} Leg;

typedef struct {
	void* Actor; void* Inst; void* Mesh;
	int Active, Checked;
	float StandHeight;               /* the standing CollisionHeight: crouched, Location goes down by the difference and PrePivot up */
	wchar_t Name[48];
	Leg L[2];
	int Calls, Traces, Faults, Clamped;
	double SolveUs;
	DWORD LastLog;
} PawnIK;

#define MAXPAWNS 48
static PawnIK Pawns[MAXPAWNS];
static int NPawns;
static LARGE_INTEGER Freq;
static int TotalFaults;

/* ------------------------------------------------------------ small vector / matrix helpers */

static Vec V(float x, float y, float z) { Vec r; r.x = x; r.y = y; r.z = z; return r; }
static Vec Add(Vec a, Vec b) { return V(a.x + b.x, a.y + b.y, a.z + b.z); }
static Vec Sub(Vec a, Vec b) { return V(a.x - b.x, a.y - b.y, a.z - b.z); }
static Vec Mul(Vec a, float s) { return V(a.x * s, a.y * s, a.z * s); }
static float Dot(Vec a, Vec b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static Vec Cross(Vec a, Vec b) { return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static float Len(Vec a) { return (float)sqrt(Dot(a, a)); }
static Vec Norm(Vec a) { float l = Len(a); return l > 1e-6f ? Mul(a, 1.0f / l) : V(0, 0, 0); }

static Mat3 Ident(void) { Mat3 r; memset(&r, 0, sizeof(r)); r.m[0][0] = r.m[1][1] = r.m[2][2] = 1; return r; }
static Mat3 Tr(Mat3 a) { Mat3 r; int i, j; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) r.m[i][j] = a.m[j][i]; return r; }
static Mat3 MM(Mat3 a, Mat3 b) { Mat3 r; int i, j, k; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) { float s = 0; for (k = 0; k < 3; k++) s += a.m[i][k] * b.m[k][j]; r.m[i][j] = s; } return r; }
static Mat3 Inv3(Mat3 a)
{
	Mat3 r;
	float det = a.m[0][0] * (a.m[1][1] * a.m[2][2] - a.m[1][2] * a.m[2][1]) - a.m[0][1] * (a.m[1][0] * a.m[2][2] - a.m[1][2] * a.m[2][0]) + a.m[0][2] * (a.m[1][0] * a.m[2][1] - a.m[1][1] * a.m[2][0]);
	if (fabs(det) < 1e-12) return Tr(a);
	det = 1.0f / det;
	r.m[0][0] = (a.m[1][1] * a.m[2][2] - a.m[1][2] * a.m[2][1]) * det; r.m[0][1] = (a.m[0][2] * a.m[2][1] - a.m[0][1] * a.m[2][2]) * det; r.m[0][2] = (a.m[0][1] * a.m[1][2] - a.m[0][2] * a.m[1][1]) * det;
	r.m[1][0] = (a.m[1][2] * a.m[2][0] - a.m[1][0] * a.m[2][2]) * det; r.m[1][1] = (a.m[0][0] * a.m[2][2] - a.m[0][2] * a.m[2][0]) * det; r.m[1][2] = (a.m[0][2] * a.m[1][0] - a.m[0][0] * a.m[1][2]) * det;
	r.m[2][0] = (a.m[1][0] * a.m[2][1] - a.m[1][1] * a.m[2][0]) * det; r.m[2][1] = (a.m[0][1] * a.m[2][0] - a.m[0][0] * a.m[2][1]) * det; r.m[2][2] = (a.m[0][0] * a.m[1][1] - a.m[0][1] * a.m[1][0]) * det;
	return r;
}
static Vec MV(Mat3 a, Vec v) { return V(a.m[0][0] * v.x + a.m[0][1] * v.y + a.m[0][2] * v.z, a.m[1][0] * v.x + a.m[1][1] * v.y + a.m[1][2] * v.z, a.m[2][0] * v.x + a.m[2][1] * v.y + a.m[2][2] * v.z); }

/* the bone's rotation R (mesh = R * local) from its FCoords rows, and back, by convention */
static Mat3 RotOf(const FCoords* C)
{
	Mat3 r;
	r.m[0][0] = C->X.x; r.m[0][1] = C->X.y; r.m[0][2] = C->X.z;
	r.m[1][0] = C->Y.x; r.m[1][1] = C->Y.y; r.m[1][2] = C->Y.z;
	r.m[2][0] = C->Z.x; r.m[2][1] = C->Z.y; r.m[2][2] = C->Z.z;
	return Conv == 1 ? Tr(r) : r;
}
static void SetRot(FCoords* C, Mat3 R)
{
	if (Conv == 1) R = Tr(R);
	C->X = V(R.m[0][0], R.m[0][1], R.m[0][2]);
	C->Y = V(R.m[1][0], R.m[1][1], R.m[1][2]);
	C->Z = V(R.m[2][0], R.m[2][1], R.m[2][2]);
}

/* the smallest rotation taking unit a onto unit b (Rodrigues) */
static Mat3 RotBetween(Vec a, Vec b)
{
	Vec k = Cross(a, b);
	float s = Len(k), c = Dot(a, b), t;
	Mat3 r = Ident(), K;
	if (s < 1e-5f) return r;      /* parallel (or opposite: left alone) */
	k = Mul(k, 1.0f / s);
	memset(&K, 0, sizeof(K));
	K.m[0][1] = -k.z; K.m[0][2] = k.y; K.m[1][0] = k.z; K.m[1][2] = -k.x; K.m[2][0] = -k.y; K.m[2][1] = k.x;
	t = 1 - c;
	{
		int i, j;
		Mat3 K2 = MM(K, K);
		for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) r.m[i][j] += K.m[i][j] * s + K2.m[i][j] * t;
	}
	return r;
}

/* ------------------------------------------------------------ engine access */

static int Resolve(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll"), Core = GetModuleHandleW(L"Core.dll");
	if (Tried) return Ready;
	Tried = 1;
	QueryPerformanceFrequency(&Freq);
	if (!Eng || !Core) { Note(L"footik: Engine.dll/Core.dll not loaded"); return 0; }
	SetBoneDirection = (SetBoneDirection_t)GetProcAddress(Eng, "?SetBoneDirection@USkeletalMeshInstance@@UAEHVFName@@VFRotator@@VFVector@@MHH@Z");
	SetWorldSpacer = (SetWorldSpacer_t)GetProcAddress(Eng, "?SetWorldSpacerFunction@USkeletalMeshInstance@@UAEHVFName@@PAXH@Z");
	MatchRefBone = (MatchRefBone_t)GetProcAddress(Eng, "?MatchRefBone@USkeletalMeshInstance@@UAEHVFName@@@Z");
	MeshToWorld = (MeshToWorld_t)GetProcAddress(Eng, "?MeshToWorld@USkeletalMeshInstance@@UAE?AVFMatrix@@XZ");
	SingleLineCheck = (SingleLineCheck_t)GetProcAddress(Eng, "?SingleLineCheck@ULevel@@UAEHAAUFCheckResult@@PAVAActor@@ABVFVector@@2KV4@@Z");
	GetName = (GetName_t)GetProcAddress(Core, "?GetName@UObject@@QBEPBGXZ");
	GetClass = (GetClass_t)GetProcAddress(Core, "?GetClass@UObject@@QBEPAVUClass@@XZ");
	FNameStr = (FNameStr_t)GetProcAddress(Core, "??DFName@@QBEPBGXZ");
	Objs = (ObjArray*)GetProcAddress(Core, "?GObjObjects@UObject@@1V?$TArray@PAVUObject@@@@A");
	if (!SetBoneDirection || !SetWorldSpacer || !MatchRefBone || !MeshToWorld || !SingleLineCheck || !GetName || !GetClass || !FNameStr || !Objs)
	{
		Note(L"footik: an engine export is missing (SetBoneDirection %p, SetWorldSpacerFunction %p, MatchRefBone %p, MeshToWorld %p, SingleLineCheck %p, GetName %p, GetClass %p, FName* %p, GObjObjects %p): off",
			SetBoneDirection, SetWorldSpacer, MatchRefBone, MeshToWorld, SingleLineCheck, GetName, GetClass, FNameStr, Objs);
		return 0;
	}
	Ready = 1;
	Note(L"footik: engine entry points resolved (SetBoneDirection %p, SetWorldSpacerFunction %p, SingleLineCheck %p)", SetBoneDirection, SetWorldSpacer, SingleLineCheck);
	return 1;
}

/* the actor's skeletal mesh instance, with its vtable checked against the exports we call:
   the slots the pose build uses (0x11C SetBoneDirection, 0x120 SetWorldSpacerFunction,
   0x124 MatchRefBone, 0x13C MeshToWorld) must be exactly those thunks */
static void* InstanceOf(void* Actor, const wchar_t* Why)
{
	void* Inst = *(void**)((BYTE*)Actor + 0xF8);
	void** Vt;
	if (!Inst) { if (Why) Note(L"footik: %ls has no mesh instance yet", Why); return NULL; }
	Vt = *(void***)Inst;
	if (Vt[0x11C / 4] != (void*)SetBoneDirection || Vt[0x120 / 4] != (void*)SetWorldSpacer || Vt[0x124 / 4] != (void*)MatchRefBone || Vt[0x13C / 4] != (void*)MeshToWorld)
	{
		if (Why) Note(L"footik: %ls: the mesh instance's vtable isn't a USkeletalMeshInstance's (slots %p %p %p %p): refused", Why, Vt[0x11C / 4], Vt[0x120 / 4], Vt[0x124 / 4], Vt[0x13C / 4]);
		return NULL;
	}
	return Inst;
}

static FCoords* BoneCoords(void* Inst, int Bone)
{
	FCoords* Arr = *(FCoords**)((BYTE*)Inst + 0xB4);
	int Num = *(int*)((BYTE*)Inst + 0xB8);
	if (!Arr || Bone < 0 || Bone >= Num) return NULL;
	return Arr + Bone;
}

/* FMeshBone (0x40 in this build): FName +0, Flags +4, quat +8, ref position +0x18, length +0x24, +0x28..+0x30 sizes/pointer,
   ParentIndex +0x34, NumChildren +0x38, +0x3C a pointer (read from a dump of leftLeg: parent 79 = leftUpLeg, 1 child) */
static BYTE* RefBone(void* Mesh, int Bone)
{
	BYTE* Arr = *(BYTE**)((BYTE*)Mesh + 0x1DC);
	int Num = *(int*)((BYTE*)Mesh + 0x1E0);
	if (!Arr || Bone < 0 || Bone >= Num) return NULL;
	return Arr + Bone * 0x40;
}

/* the pawn by name and class name, through the object table */
static void* FindActor(const wchar_t* Name, const wchar_t* ClassName)
{
	int i, Found = 0;
	void* Best = NULL;
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
		if (*(DWORD*)((BYTE*)O + 0x34) & 0x80) continue;    /* bDeleteMe */
		Found++;
		Best = O;
	}
	if (Found > 1) Note(L"footik: %d actors called %ls (%ls): the last one taken", Found, Name, ClassName);
	return Best;
}

static PawnIK* PawnByInst(void* Inst)
{
	int i;
	for (i = 0; i < NPawns; i++) if (Pawns[i].Inst == Inst && Pawns[i].Active) return &Pawns[i];
	return NULL;
}

/* world <- mesh, through the engine's own MeshToWorld matrix (row vectors, as GetBoneCoords does) */
static Vec ToWorld(const float* M, Vec m)
{
	return V(m.x * M[0] + m.y * M[4] + m.z * M[8] + M[12], m.x * M[1] + m.y * M[5] + m.z * M[9] + M[13], m.x * M[2] + m.y * M[6] + m.z * M[10] + M[14]);
}
/* a world-space direction into mesh space: the inverse of the matrix's 3x3 */
static Vec DirToMesh(const float* M, Vec w)
{
	float a = M[0], b = M[1], c = M[2], d = M[4], e = M[5], f = M[6], g = M[8], h = M[9], i = M[10];
	float det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
	float inv[9];
	if (fabs(det) < 1e-12) return V(0, 0, 0);
	det = 1.0f / det;
	inv[0] = (e * i - f * h) * det; inv[1] = (c * h - b * i) * det; inv[2] = (b * f - c * e) * det;
	inv[3] = (f * g - d * i) * det; inv[4] = (a * i - c * g) * det; inv[5] = (c * d - a * f) * det;
	inv[6] = (d * h - e * g) * det; inv[7] = (b * g - a * h) * det; inv[8] = (a * e - b * d) * det;
	/* row vector w times inv */
	return V(w.x * inv[0] + w.y * inv[3] + w.z * inv[6], w.x * inv[1] + w.y * inv[4] + w.z * inv[7], w.x * inv[2] + w.y * inv[5] + w.z * inv[8]);
}

/* the floor under a world point: its height and normal, or 0 when nothing is within Up above / Down below */
static int FloorUnder(PawnIK* P, Vec At, float Up, float Down, float* OutZ, Vec* OutN)
{
	DWORD Hit[24];
	Vec Start = V(At.x, At.y, At.z + Up), End = V(At.x, At.y, At.z - Down);
	void* Level = *(void**)((BYTE*)P->Actor + 0xBC);
	if (!Level) return 0;
	memset(Hit, 0, sizeof(Hit));
	P->Traces++;
	if (SingleLineCheck(Level, NULL, Hit, P->Actor, &End, &Start, 0x86 /* TRACE_World */, 0, 0, 0)) return 0;   /* 1 = nothing hit */
	*OutZ = ((float*)Hit)[4];    /* FCheckResult.Location.Z (Location at +8, Normal at +0x14) */
	if (OutN) *OutN = V(((float*)Hit)[5], ((float*)Hit)[6], ((float*)Hit)[7]);
	return 1;
}

/* ------------------------------------------------------------ the callback */

static void Identity(FCoords* Ret, void* Inst, int Bone)
{
	FCoords* C = Inst ? BoneCoords(Inst, Bone) : NULL;
	if (C) *Ret = *C;
	else { memset(Ret, 0, sizeof(*Ret)); Ret->X.x = Ret->Y.y = Ret->Z.z = 1; }
}

/* the bone's FCoords convention, from the calf's offset in the thigh's frame: it must equal the
   ref skeleton's position of the calf, or at least stay constant while the leg moves */
static void LearnConvention(PawnIK* P, Leg* L, const FCoords* T, const FCoords* C)
{
	Vec d = Sub(C->O, T->O), A, B, Ref;
	BYTE* RB = RefBone(P->Mesh, L->Calf);
	float ea, eb;
	if (Conv || ConvGaveUp) return;
	A = V(Dot(d, T->X), Dot(d, T->Y), Dot(d, T->Z));
	B = V(T->X.x * d.x + T->Y.x * d.y + T->Z.x * d.z, T->X.y * d.x + T->Y.y * d.y + T->Z.y * d.z, T->X.z * d.x + T->Y.z * d.y + T->Z.z * d.z);
	if (RB)
	{
		Ref = *(Vec*)(RB + 0x18);
		ea = Len(Sub(A, Ref)); eb = Len(Sub(B, Ref));
		if (ea < 0.5f && eb > 2.0f) { Conv = 1; Note(L"footik: bone coords convention: rows are the bone's basis vectors (ref offset check %.2f vs %.2f)", ea, eb); return; }
		if (eb < 0.5f && ea > 2.0f) { Conv = 2; Note(L"footik: bone coords convention: rows are the rotation's rows (ref offset check %.2f vs %.2f)", eb, ea); return; }
	}
	if (ConvHavePrev) { ConvSumA += Len(Sub(A, ConvPrevA)); ConvSumB += Len(Sub(B, ConvPrevB)); ConvN++; }
	ConvPrevA = A; ConvPrevB = B; ConvHavePrev = 1;
	if (ConvN >= 60 && ConvSumA + ConvSumB > 2)
	{
		if (ConvSumA * 4 < ConvSumB) { Conv = 1; Note(L"footik: bone coords convention: rows are the bone's basis vectors (drift %.2f vs %.2f over %d frames)", ConvSumA, ConvSumB, ConvN); }
		else if (ConvSumB * 4 < ConvSumA) { Conv = 2; Note(L"footik: bone coords convention: rows are the rotation's rows (drift %.2f vs %.2f over %d frames)", ConvSumB, ConvSumA, ConvN); }
	}
	if (ConvN >= 900 && !Conv) { ConvGaveUp = 1; Note(L"footik: the bone coords convention couldn't be told (drift %.2f vs %.2f, ref offsets %.2f / %.2f): foot IK stays off", ConvSumA, ConvSumB, RB ? Len(Sub(A, *(Vec*)(RB + 0x18))) : -1.0f, RB ? Len(Sub(B, *(Vec*)(RB + 0x18))) : -1.0f); }
}

static int SmallChain(const Leg* L) { return L->L1 < 5 || L->L2 < 5; }

static void ThighStage(PawnIK* P, Leg* L, FCoords* Ret, const FCoords* T, void* Inst)
{
	Mat3 Rt = RotOf(T), Rc, Q;
	Vec H = T->O, K, A, Hw, Aw, Up, target, Kp, d, n, floorN;
	float M[16], dt, groundFoot, groundActor, delta, dist, L1 = L->L1, L2 = L->L2, cosa, sina;
	LARGE_INTEGER Now;
	BYTE* Actor = (BYTE*)P->Actor;

	L->PendingCalf = L->PendingFoot = 0;
	if (!L->HaveKnee || !L->HaveAnkle || !L->HaveCalfLocal || SmallChain(L)) { *Ret = *T; return; }

	/* the animated chain (the calf's local rotation is last frame's: a few ms old) */
	K = Add(H, MV(Rt, L->KneeLocal));
	Rc = MM(Rt, L->CalfLocal);
	A = Add(K, MV(Rc, L->AnkleLocal));

	/* world: where the floor is under the ankle, against the floor under the pawn */
	MeshToWorld(Inst, NULL, M);
	Hw = ToWorld(M, H);
	Aw = ToWorld(M, A);
	if (!P->Checked)
	{
		Vec Loc = *(Vec*)(Actor + 0x130);
		float CH = *(float*)(Actor + 0x1FC);
		float dz = Hw.z - Loc.z, dxy = Len(Sub(V(Hw.x, Hw.y, 0), V(Loc.x, Loc.y, 0)));
		P->Checked = 1;
		if (dxy > CH + 20 || dz < -CH - 10 || dz > CH + 10 || Aw.z > Hw.z)
		{
			P->Active = 0;
			Note(L"footik: %ls: MeshToWorld doesn't put the hip near the pawn (hip %.0f %.0f %.0f, ankle z %.0f, pawn %.0f %.0f %.0f, height %.0f): off for this pawn", P->Name, Hw.x, Hw.y, Hw.z, Aw.z, Loc.x, Loc.y, Loc.z, CH);
			*Ret = *T; return;
		}
		if (LogOn) Note(L"footik: %ls: hip at %.0f %.0f %.0f over the pawn's %.0f %.0f %.0f (height %.0f), ankle z %.0f, leg %.1f + %.1f", P->Name, Hw.x, Hw.y, Hw.z, Loc.x, Loc.y, Loc.z, CH, Aw.z, L1, L2);
	}
	QueryPerformanceCounter(&Now);
	dt = L->LastT.QuadPart ? (float)((Now.QuadPart - L->LastT.QuadPart) / (double)Freq.QuadPart) : 0.016f;
	if (dt > 0.1f) dt = 0.1f;
	L->LastT = Now;
	L->Dt = dt;

	/* where the clip stands: the bottom of the collision cylinder as drawn (PrePivot included: the
	   script lowers the whole body with it so the lower foot can reach). A trace under the centre
	   would be wrong on a step edge, where the cylinder is held up by the edge. */
	groundActor = ((float*)(Actor + 0x130))[2] + ((float*)(Actor + 0x1B4))[2] - P->StandHeight;
	if (!FloorUnder(P, Aw, 60, 120, &groundFoot, &floorN) || groundFoot - groundActor > MaxLift + 5 || groundFoot - groundActor < -(MaxDrop + 40))
	{
		/* nothing under the foot (a ledge, water), or a surface the pawn couldn't step onto (a crate,
		   a bench: higher than the lift allows) or reach down to: not ground for the feet, ease out */
		L->Lift *= 0.9f;
		delta = L->Lift;
		P->Clamped++;
		L->HaveFloorN = 0;               /* (the foot eases back level) */
	}
	else
	{
		delta = groundFoot - groundActor;
		L->FloorN = floorN;
		L->HaveFloorN = floorN.z > 0.5f; /* a wall's side under the ankle (n.z low) isn't a floor to stand level with */
		L->LastGround = delta;
		L->GroundZ = groundFoot; L->FloorZ = groundActor; L->AnimZ = Aw.z;
		if (delta > MaxLift) delta = MaxLift;
		if (delta < -MaxDrop) delta = -MaxDrop;
		L->Lift += (delta - L->Lift) * (Gain * dt > 1 ? 1 : Gain * dt);
		delta = L->Lift;
	}
	L->Solves++;
	if (fabs(delta) < 0.05f) { *Ret = *T; L->DeltaMesh = V(0, 0, 0); L->QThigh = L->QCalf = Ident(); L->PendingCalf = L->PendingFoot = 1; return; }

	/* the ankle target, and the knee that reaches it in the animated bend plane */
	Up = DirToMesh(M, V(0, 0, delta));
	L->DeltaMesh = Up;
	target = Add(A, Up);
	L->TargetZ = ToWorld(M, target).z;
	d = Sub(target, H);
	dist = Len(d);
	if (dist > (L1 + L2) * 0.995f) dist = (L1 + L2) * 0.995f;
	if (dist < fabs(L1 - L2) * 1.05f + 0.5f) dist = (float)fabs(L1 - L2) * 1.05f + 0.5f;
	d = Norm(d);
	n = Sub(Sub(K, H), Mul(d, Dot(Sub(K, H), d)));
	if (Len(n) < 0.5f) { *Ret = *T; L->DeltaMesh = V(0, 0, 0); L->QThigh = L->QCalf = Ident(); L->PendingCalf = L->PendingFoot = 1; return; }   /* straight leg: no bend plane */
	n = Norm(n);
	cosa = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist);
	if (cosa > 1) cosa = 1; if (cosa < -1) cosa = -1;
	sina = (float)sqrt(1 - cosa * cosa);
	Kp = Add(H, Add(Mul(d, L1 * cosa), Mul(n, L1 * sina)));
	Q = RotBetween(Norm(Sub(K, H)), Norm(Sub(Kp, H)));
	L->QThigh = Q;
	L->QCalf = Ident();
	L->PendingCalf = L->PendingFoot = 1;
	*Ret = *T;
	SetRot(Ret, MM(Q, Rt));
}

static void CalfStage(PawnIK* P, Leg* L, FCoords* Ret, const FCoords* C, void* Inst)
{
	FCoords* T = BoneCoords(Inst, L->Thigh);
	Mat3 Rt, Rc, Q;
	Vec Ac, Aanim, H, target;
	*Ret = *C;
	if (!T) return;
	if (!Conv) { LearnConvention(P, L, T, C); return; }
	Rt = RotOf(T); Rc = RotOf(C);
	/* what this frame's animation gave the calf, relative to the (already corrected) thigh: the
	   correction is a pure rotation of the thigh, so the local pose is the clip's */
	L->CalfLocal = MM(Inv3(Rt), Rc);
	L->KneeLocal = MV(Inv3(Rt), Sub(C->O, T->O));
	L->L1 = Len(Sub(C->O, T->O));
	L->HaveCalfLocal = L->HaveKnee = 1;
	if (!L->PendingCalf || !L->HaveAnkle) return;
	L->PendingCalf = 0;
	if (Len(L->DeltaMesh) < 1e-4f) return;
	/* the ankle as the clip has it now (undo the thigh's turn), moved by this frame's delta */
	H = T->O;
	Ac = Add(C->O, MV(Rc, L->AnkleLocal));
	Aanim = Add(H, MV(Tr(L->QThigh), Sub(Ac, H)));
	target = Add(Aanim, L->DeltaMesh);
	Q = RotBetween(Norm(Sub(Ac, C->O)), Norm(Sub(target, C->O)));
	L->QCalf = Q;
	SetRot(Ret, MM(Q, Rc));
}

/* the foot tilted to the floor under it (TiltOn): the smallest rotation taking mesh-up onto the traced
   normal, whose axis is level, so the clip's yaw is kept and only pitch and roll change; at most
   MaxTilt degrees; the normal is eased at Gain as the lift is, and goes back to level where there is
   no ground to use. Applied about the ankle (the FCoords origin is the engine's), so the toe follows
   the slope. Answers 1 when Rf was changed */
static int FootTilt(PawnIK* P, Leg* L, void* Inst, Mat3* Rf)
{
	float M[16], k, c, cmax, smax;
	Vec target, upM, nM, perp;
	Mat3 T;
	target = L->HaveFloorN ? L->FloorN : V(0, 0, 1);
	k = Gain * L->Dt;
	if (k > 1) k = 1;
	if (!L->HaveTilt) { L->TiltN = target; L->HaveTilt = 1; }
	else L->TiltN = Norm(Add(L->TiltN, Mul(Sub(target, L->TiltN), k)));
	if (Len(L->TiltN) < 0.5f) L->TiltN = V(0, 0, 1);
	L->TiltDeg = 0;
	if (L->TiltN.z > 0.99995f) return 0;                 /* level */
	MeshToWorld(Inst, NULL, M);
	upM = Norm(DirToMesh(M, V(0, 0, 1)));
	nM = Norm(DirToMesh(M, L->TiltN));
	if (Len(upM) < 0.5f || Len(nM) < 0.5f) return 0;
	c = Dot(upM, nM);
	cmax = (float)cos(MaxTilt * 3.14159265f / 180);
	smax = (float)sin(MaxTilt * 3.14159265f / 180);
	if (c < cmax)
	{
		/* steeper than the foot may tilt: the same direction, MaxTilt from up */
		perp = Sub(nM, Mul(upM, c));
		if (Len(perp) < 1e-5f) return 0;
		perp = Norm(perp);
		nM = Add(Mul(upM, cmax), Mul(perp, smax));
		c = cmax;
	}
	if (c > 1) c = 1;
	L->TiltDeg = (float)(acos(c) * 180 / 3.14159265);
	T = RotBetween(upM, nM);
	*Rf = MM(T, *Rf);
	return 1;
}

static void FootStage(PawnIK* P, Leg* L, FCoords* Ret, const FCoords* F, void* Inst)
{
	FCoords* C = BoneCoords(Inst, L->Calf);
	Mat3 Rc, Rf;
	int Changed = 0;
	*Ret = *F;
	if (!C || !Conv) return;
	Rc = RotOf(C);
	L->AnkleLocal = MV(Inv3(Rc), Sub(F->O, C->O));
	L->L2 = Len(Sub(F->O, C->O));
	L->HaveAnkle = 1;
	if (!L->PendingFoot) return;
	L->PendingFoot = 0;
	Rf = RotOf(F);
	if (Len(L->DeltaMesh) >= 1e-4f)
	{
		if (LogOn && GetTickCount() - L->LastDiag > 1000)
		{
			float M[16];
			Vec Fw;
			L->LastDiag = GetTickCount();
			MeshToWorld(Inst, NULL, M);
			Fw = ToWorld(M, F->O);
			Note(L"footik: %ls %ls: ankle as animated z %.1f, asked z %.1f, got z %.1f (floor under it %.1f, the body's base %.1f, lift %+.1f, tilt %.1f deg) at %.0f %.0f %.0f", P->Name, L == &P->L[0] ? L"left" : L"right", L->AnimZ, L->TargetZ, Fw.z, L->GroundZ, L->FloorZ, L->Lift, L->TiltDeg, ((float*)((BYTE*)P->Actor + 0x130))[0], ((float*)((BYTE*)P->Actor + 0x130))[1], ((float*)((BYTE*)P->Actor + 0x130))[2]);
		}
		/* the foot keeps the orientation the clip gave it: undo the calf's and the thigh's turns */
		Rf = MM(Tr(L->QThigh), MM(Tr(L->QCalf), Rf));
		Changed = 1;
	}
	/* ... then level with its floor */
	if (TiltOn && FootTilt(P, L, Inst, &Rf)) Changed = 1;
	if (Changed) SetRot(Ret, Rf);
}

static void LogPawn(PawnIK* P)
{
	DWORD Now = GetTickCount();
	if (!LogOn || Now - P->LastLog < 5000) return;
	P->LastLog = Now;
	Note(L"footik: %ls: %d callbacks, %d traces, %.1f us per callback, %d passes (no ground to use); left ground %+.1f lift %+.1f tilt %.1f, right ground %+.1f lift %+.1f tilt %.1f (conv %d, faults %d)",
		P->Name, P->Calls, P->Traces, P->Calls ? P->SolveUs / P->Calls : 0.0, P->Clamped, P->L[0].LastGround, P->L[0].Lift, P->L[0].TiltDeg, P->L[1].LastGround, P->L[1].Lift, P->L[1].TiltDeg, Conv, P->Faults);
	P->Calls = P->Traces = 0; P->SolveUs = 0;
}

static FCoords* Solve(FCoords* Ret, void* Owner, int Bone, int Dir, void* Inst)
{
	PawnIK* P = PawnByInst(Inst);
	FCoords* Cur = BoneCoords(Inst, Bone);
	LARGE_INTEGER T0, T1;
	int i;
	if (!P || !Cur || P->Actor != Owner) { Identity(Ret, Inst, Bone); return Ret; }
	if (*((BYTE*)Owner + 0x55) == 0xF || (*(DWORD*)((BYTE*)Owner + 0x34) & 0x80)) { *Ret = *Cur; return Ret; }   /* ragdoll, deleted */
	QueryPerformanceCounter(&T0);
	P->Calls++;
	for (i = 0; i < 2; i++)
	{
		Leg* L = &P->L[i];
		if (Bone == L->Thigh) { ThighStage(P, L, Ret, Cur, Inst); break; }
		if (Bone == L->Calf) { CalfStage(P, L, Ret, Cur, Inst); break; }
		if (Bone == L->Foot) { FootStage(P, L, Ret, Cur, Inst); break; }
	}
	if (i == 2) *Ret = *Cur;
	QueryPerformanceCounter(&T1);
	P->SolveUs += (T1.QuadPart - T0.QuadPart) * 1e6 / Freq.QuadPart;
	LogPawn(P);
	return Ret;
}

static FCoords* __cdecl WorldSpacer(FCoords* Ret, void* Owner, int Bone, int Dir, void* Inst)
{
	__try
	{
		return Solve(Ret, Owner, Bone, Dir, Inst);
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		PawnIK* P;
		TotalFaults++;
		__try { P = PawnByInst(Inst); if (P) { P->Faults++; if (P->Faults > 3) P->Active = 0; } Identity(Ret, Inst, Bone); }
		__except (EXCEPTION_EXECUTE_HANDLER) { memset(Ret, 0, sizeof(*Ret)); Ret->X.x = Ret->Y.y = Ret->Z.z = 1; }
		if (TotalFaults <= 5) Note(L"footik: exception in the callback (bone %d): the bone was left as animated", Bone);
		return Ret;
	}
}

/* ------------------------------------------------------------ commands */

static int LegOk(PawnIK* P, Leg* L, const wchar_t* Side)
{
	BYTE *T = RefBone(P->Mesh, L->Thigh), *C = RefBone(P->Mesh, L->Calf), *F = RefBone(P->Mesh, L->Foot);
	if (!T || !C || !F || L->Thigh < 1) { Note(L"footik: %ls: %ls leg bones %d %d %d aren't in the mesh", P->Name, Side, L->Thigh, L->Calf, L->Foot); return 0; }
	if (*(int*)(C + 0x34) != L->Thigh || *(int*)(F + 0x34) != L->Calf)
	{
		wchar_t Hex[400] = L"", Flt[400] = L"";
		int k;
		for (k = 0; k < 16; k++) { swprintf(Hex + wcslen(Hex), 24, L"%08X ", ((DWORD*)C)[k]); swprintf(Flt + wcslen(Flt), 24, L"%.3g ", ((float*)C)[k]); }
		Note(L"footik: %ls: %ls leg isn't a thigh->calf->foot chain (parents %d %d %d): refused; calf record: %ls= %ls", P->Name, Side, *(int*)(T + 0x34), *(int*)(C + 0x34), *(int*)(F + 0x34), Hex, Flt);
		return 0;
	}
	L->NameT = *(DWORD*)T; L->NameC = *(DWORD*)C; L->NameF = *(DWORD*)F;
	return 1;
}

static int Hook(PawnIK* P, Leg* L, int Bone, DWORD Name, void* Fn, float Alpha)
{
	int a = SetBoneDirection(P->Inst, NULL, Name, 0, 0, 0, 0, 0, 0, Alpha, 99, Bone);
	int b = SetWorldSpacer(P->Inst, NULL, Name, Fn, Bone);
	if (!a || !b) Note(L"footik: %ls: director on bone %d (%ls): SetBoneDirection %d, SetWorldSpacerFunction %d", P->Name, Bone, FNameStr(&Name, NULL), a, b);
	return a && b;
}

static int Install(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	int b[6], i;
	float Stand = 0;
	void* Actor;
	void* Inst;
	PawnIK* P = NULL;
	if (swscanf(Arg, L"%47s %47s %d %d %d %d %d %d %f", Name, Class, &b[0], &b[1], &b[2], &b[3], &b[4], &b[5], &Stand) != 9 || Stand < 10) { Note(L"footik: bad install '%ls'", Arg); return 0; }
	if (!Resolve()) return 0;
	Actor = FindActor(Name, Class);
	if (!Actor) { Note(L"footik: no actor %ls (%ls)", Name, Class); return 0; }
	Inst = InstanceOf(Actor, Name);
	if (!Inst) return 0;
	for (i = 0; i < NPawns; i++) if (Pawns[i].Actor == Actor) P = &Pawns[i];
	if (P && P->Active && P->Inst == Inst) return 1;
	if (!P) for (i = 0; i < NPawns; i++) if (!Pawns[i].Active) { P = &Pawns[i]; break; }
	if (!P) { if (NPawns >= MAXPAWNS) { Note(L"footik: no room for %ls", Name); return 0; } P = &Pawns[NPawns++]; }
	memset(P, 0, sizeof(*P));
	P->Actor = Actor; P->Inst = Inst; P->Mesh = *(void**)((BYTE*)Actor + 0xD4);
	P->StandHeight = Stand;
	wcscpy(P->Name, Name);
	P->L[0].Thigh = b[0]; P->L[0].Calf = b[1]; P->L[0].Foot = b[2];
	P->L[1].Thigh = b[3]; P->L[1].Calf = b[4]; P->L[1].Foot = b[5];
	if (!P->Mesh || !LegOk(P, &P->L[0], L"left") || !LegOk(P, &P->L[1], L"right")) return 0;
	P->Active = 1;   /* before the hooks: the callback looks the pawn up by instance */
	for (i = 0; i < 2; i++)
	{
		Leg* L = &P->L[i];
		if (!Hook(P, L, L->Thigh, L->NameT, WorldSpacer, 1.0f) || !Hook(P, L, L->Calf, L->NameC, WorldSpacer, 1.0f) || !Hook(P, L, L->Foot, L->NameF, WorldSpacer, 1.0f))
		{
			P->Active = 0;
			return 0;
		}
	}
	if (LogOn) Note(L"footik: hooked %ls (%ls): left %d/%d/%d right %d/%d/%d (%ls/%ls/%ls), %d bones posed", Name, Class, b[0], b[1], b[2], b[3], b[4], b[5], FNameStr(&P->L[0].NameT, NULL), FNameStr(&P->L[0].NameC, NULL), FNameStr(&P->L[0].NameF, NULL), *(int*)((BYTE*)Inst + 0xB8));
	return 1;
}

static int Remove(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	int i, j;
	if (swscanf(Arg, L"%47s %47s", Name, Class) != 2) return 0;
	for (i = 0; i < NPawns; i++)
	{
		PawnIK* P = &Pawns[i];
		if (!P->Active || _wcsicmp(P->Name, Name)) continue;
		P->Active = 0;
		/* the directors go inert: alpha 0 skips them in the pose build, and no callback either */
		if (!(*(DWORD*)((BYTE*)P->Actor + 0x34) & 0x80) && InstanceOf(P->Actor, NULL) == P->Inst)
		{
			for (j = 0; j < 2; j++)
			{
				Leg* L = &P->L[j];
				Hook(P, L, L->Thigh, L->NameT, NULL, 0.0f);
				Hook(P, L, L->Calf, L->NameC, NULL, 0.0f);
				Hook(P, L, L->Foot, L->NameF, NULL, 0.0f);
			}
		}
		if (LogOn) Note(L"footik: released %ls", Name);
		return 1;
	}
	return 0;
}

static int Config(const wchar_t* Arg)
{
	float d, l, g; int lg, tl = 1, n;
	n = swscanf(Arg, L"%f %f %f %d %d", &d, &l, &g, &lg, &tl);
	if (n < 4) return 0;
	MaxDrop = d; MaxLift = l; Gain = g; LogOn = lg; TiltOn = tl != 0;
	Note(L"footik: config drop %.0f lift %.0f gain %.1f log %d tilt %d (at most %.0f deg)", MaxDrop, MaxLift, Gain, LogOn, TiltOn, MaxTilt);
	return Resolve();
}

/* "FootIKConfig drop lift gain log [tilt]", "FootIK <name> <class> <6 bones>", "FootIKOff <name> <class>" */
int FootIKCommand(const wchar_t* Cmd)
{
	if (!_wcsnicmp(Cmd, L"FootIKConfig ", 13)) return Config(Cmd + 13);
	if (!_wcsnicmp(Cmd, L"FootIKOff ", 10)) return Remove(Cmd + 10);
	if (!_wcsnicmp(Cmd, L"FootIK ", 7)) return Install(Cmd + 7);
	return 0;
}
