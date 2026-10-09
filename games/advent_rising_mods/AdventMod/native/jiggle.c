/* jiggle.c - secondary flesh motion for the Seekers (JIGGLE.md): damped springs on added
   leaf bones, applied inside the engine's own pose build.

   The mesh (tools/jiggle_rig.py, imported by ModJiggleMesh) carries ten "J_" bones, each a leaf at
   its parent's joint with no rotation, weighted to the flesh of its region only (never to an armour
   triangle: the plates keep their ordinary bones and move with the skeleton alone). The game's clips
   have no track for them, so they sit at the parent's axes. Here each one gets a director with Space
   99 and a world-spacer callback (the pattern of footik.c: SetBoneDirection, SetWorldSpacerFunction,
   vtbl 0x11C/0x120), and in the callback a damped angular spring turns the bone about the joint:

       theta'' = gain * (c x -a) / |c|^2 - k theta - d theta'      (theta, c, a in the parent's frame)

   a = the acceleration of the region's centre (the parent's joint moved by the lever c), finite-
   differenced from its world position frame to frame, so the flesh lags and overshoots the body's
   own motion; hits (JiggleHit, from ModReact's flinch) add an angular impulse. |theta| is clamped
   per bone. The parameters per bone come from the fit to the soft-body reference
   (tools/jiggle_fit.py -> ModJiggleBones), overridable from the ini through ModJiggle.

   Script: "JiggleConfig <gain> <log> <max accel>", "JiggleBone <name> <k> <d> <gain> <max deg>
   <lever x y z>" (per bone name, before any install), "Jiggle <pawn> <class> <n> <bone index>..."
   (indices from MatchRefBone), "JiggleOff <pawn> <class>", "JiggleHit <pawn> <class> dx dy dz
   <strength>" (world direction). The pawn is found through Core's GObjObjects.

   Safety as footik.c: exports resolved by name, the instance's vtable slots must be those exports,
   a hooked bone must be a leaf (NumChildren 0) whose name starts with "J_" (never one of
   EonEngine's), the callback is in __try/__except and answers "as animated" on any doubt, ragdolls
   and deleted actors are left alone, a dt over 0.1 s (an unposed stretch) resets the history so a
   jump never reads as an acceleration. */
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

void Note(const wchar_t* Fmt, ...);

typedef struct { float x, y, z; } Vec;
typedef struct { Vec O, X, Y, Z; } FCoords;
typedef struct { float m[3][3]; } Mat3;

typedef int (__fastcall *SetBoneDirection_t)(void* Inst, void* Edx, DWORD Name, int Pitch, int Yaw, int Roll, float tx, float ty, float tz, float Alpha, int Space, int Pre);
typedef int (__fastcall *SetWorldSpacer_t)(void* Inst, void* Edx, DWORD Name, void* Fn, int Pre);
typedef int (__fastcall *MatchRefBone_t)(void* Inst, void* Edx, DWORD Name);
typedef float* (__fastcall *MeshToWorld_t)(void* Inst, void* Edx, float* Out16);
typedef const wchar_t* (__fastcall *GetName_t)(void* This, void* Edx);
typedef void* (__fastcall *GetClass_t)(void* This, void* Edx);
typedef const wchar_t* (__fastcall *FNameStr_t)(const DWORD* Name, void* Edx);
typedef struct { void** Data; int Num; int Max; } ObjArray;

static SetBoneDirection_t SetBoneDirection;
static SetWorldSpacer_t SetWorldSpacer;
static MatchRefBone_t MatchRefBone;
static MeshToWorld_t MeshToWorld;
static GetName_t GetName;
static GetClass_t GetClass;
static FNameStr_t FNameStr;
static ObjArray* Objs;
static int Ready, Tried;
static LARGE_INTEGER Freq;

/* config */
static float GlobalGain = 1.0f, MaxAccel = 30000.0f;
static int LogOn;

/* the bone FCoords convention (as footik.c): 1 = rows are basis vectors, 2 = rows of the rotation */
static int Conv;

/* per bone name parameters */
typedef struct { wchar_t Name[32]; float K, D, Gain, MaxRad; Vec Lever; } BoneParam;
#define MAXPARAMS 16
static BoneParam Params[MAXPARAMS];
static int NParams;

typedef struct {
	int Bone, Parent;
	DWORD Name;
	BoneParam* P;
	Vec Theta, Omega;               /* the spring state, parent frame (rad, rad/s) */
	Vec PosW[2];                    /* the region centre's world position, last two frames */
	Vec VelW;
	int History;                    /* how many valid positions */
	LARGE_INTEGER LastT;
	float AmpMax, AmpSum; int AmpN; /* log */
	Vec Impulse;                    /* pending hit impulse (parent frame, rad/s) */
} JBone;

typedef struct {
	void* Actor; void* Inst; void* Mesh;
	int Active;
	wchar_t Name[48];
	int NB;
	JBone B[16];
	int Calls, Faults;
	double SolveUs;
	DWORD LastLog;
} JPawn;

#define MAXPAWNS 48
static JPawn Pawns[MAXPAWNS];
static int NPawns;
static int TotalFaults;

/* ------------------------------------------------------------ maths */

static Vec V(float x, float y, float z) { Vec r; r.x = x; r.y = y; r.z = z; return r; }
static Vec Add(Vec a, Vec b) { return V(a.x + b.x, a.y + b.y, a.z + b.z); }
static Vec Sub(Vec a, Vec b) { return V(a.x - b.x, a.y - b.y, a.z - b.z); }
static Vec Mul(Vec a, float s) { return V(a.x * s, a.y * s, a.z * s); }
static float Dot(Vec a, Vec b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static Vec Cross(Vec a, Vec b) { return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static float Len(Vec a) { return (float)sqrt(Dot(a, a)); }
static Mat3 Ident(void) { Mat3 r; memset(&r, 0, sizeof(r)); r.m[0][0] = r.m[1][1] = r.m[2][2] = 1; return r; }
static Mat3 Tr(Mat3 a) { Mat3 r; int i, j; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) r.m[i][j] = a.m[j][i]; return r; }
static Mat3 MM(Mat3 a, Mat3 b) { Mat3 r; int i, j, k; for (i = 0; i < 3; i++) for (j = 0; j < 3; j++) { float s = 0; for (k = 0; k < 3; k++) s += a.m[i][k] * b.m[k][j]; r.m[i][j] = s; } return r; }
static Vec MV(Mat3 a, Vec v) { return V(a.m[0][0] * v.x + a.m[0][1] * v.y + a.m[0][2] * v.z, a.m[1][0] * v.x + a.m[1][1] * v.y + a.m[1][2] * v.z, a.m[2][0] * v.x + a.m[2][1] * v.y + a.m[2][2] * v.z); }

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

/* the rotation of a rotation vector (Rodrigues) */
static Mat3 Exp(Vec t)
{
	float a = Len(t), s, c, x, y, z;
	Mat3 r = Ident();
	if (a < 1e-6f) return r;
	x = t.x / a; y = t.y / a; z = t.z / a;
	s = (float)sin(a); c = (float)cos(a);
	r.m[0][0] = c + x * x * (1 - c);     r.m[0][1] = x * y * (1 - c) - z * s; r.m[0][2] = x * z * (1 - c) + y * s;
	r.m[1][0] = y * x * (1 - c) + z * s; r.m[1][1] = c + y * y * (1 - c);     r.m[1][2] = y * z * (1 - c) - x * s;
	r.m[2][0] = z * x * (1 - c) - y * s; r.m[2][1] = z * y * (1 - c) + x * s; r.m[2][2] = c + z * z * (1 - c);
	return r;
}

/* ------------------------------------------------------------ engine access (as footik.c) */

static int Resolve(void)
{
	HMODULE Eng = GetModuleHandleW(L"Engine.dll"), Core = GetModuleHandleW(L"Core.dll");
	if (Tried) return Ready;
	Tried = 1;
	QueryPerformanceFrequency(&Freq);
	if (!Eng || !Core) { Note(L"jiggle: Engine.dll/Core.dll not loaded"); return 0; }
	SetBoneDirection = (SetBoneDirection_t)GetProcAddress(Eng, "?SetBoneDirection@USkeletalMeshInstance@@UAEHVFName@@VFRotator@@VFVector@@MHH@Z");
	SetWorldSpacer = (SetWorldSpacer_t)GetProcAddress(Eng, "?SetWorldSpacerFunction@USkeletalMeshInstance@@UAEHVFName@@PAXH@Z");
	MatchRefBone = (MatchRefBone_t)GetProcAddress(Eng, "?MatchRefBone@USkeletalMeshInstance@@UAEHVFName@@@Z");
	MeshToWorld = (MeshToWorld_t)GetProcAddress(Eng, "?MeshToWorld@USkeletalMeshInstance@@UAE?AVFMatrix@@XZ");
	GetName = (GetName_t)GetProcAddress(Core, "?GetName@UObject@@QBEPBGXZ");
	GetClass = (GetClass_t)GetProcAddress(Core, "?GetClass@UObject@@QBEPAVUClass@@XZ");
	FNameStr = (FNameStr_t)GetProcAddress(Core, "??DFName@@QBEPBGXZ");
	Objs = (ObjArray*)GetProcAddress(Core, "?GObjObjects@UObject@@1V?$TArray@PAVUObject@@@@A");
	if (!SetBoneDirection || !SetWorldSpacer || !MatchRefBone || !MeshToWorld || !GetName || !GetClass || !FNameStr || !Objs)
	{
		Note(L"jiggle: an engine export is missing (SetBoneDirection %p, SetWorldSpacerFunction %p, MatchRefBone %p, MeshToWorld %p, GetName %p, GetClass %p, FName* %p, GObjObjects %p): off",
			SetBoneDirection, SetWorldSpacer, MatchRefBone, MeshToWorld, GetName, GetClass, FNameStr, Objs);
		return 0;
	}
	Ready = 1;
	return 1;
}

static void* InstanceOf(void* Actor, const wchar_t* Why)
{
	void* Inst = *(void**)((BYTE*)Actor + 0xF8);
	void** Vt;
	if (!Inst) { if (Why) Note(L"jiggle: %ls has no mesh instance yet", Why); return NULL; }
	Vt = *(void***)Inst;
	if (Vt[0x11C / 4] != (void*)SetBoneDirection || Vt[0x120 / 4] != (void*)SetWorldSpacer || Vt[0x124 / 4] != (void*)MatchRefBone || Vt[0x13C / 4] != (void*)MeshToWorld)
	{
		if (Why) Note(L"jiggle: %ls: the mesh instance's vtable isn't a USkeletalMeshInstance's: refused", Why);
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

/* FMeshBone 0x40: FName +0, position +0x18, ParentIndex +0x34, NumChildren +0x38 (FEET.md) */
static BYTE* RefBone(void* Mesh, int Bone)
{
	BYTE* Arr = *(BYTE**)((BYTE*)Mesh + 0x1DC);
	int Num = *(int*)((BYTE*)Mesh + 0x1E0);
	if (!Arr || Bone < 0 || Bone >= Num) return NULL;
	return Arr + Bone * 0x40;
}

static void* FindActor(const wchar_t* Name, const wchar_t* ClassName)
{
	int i;
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
		if (*(DWORD*)((BYTE*)O + 0x34) & 0x80) continue;
		Best = O;
	}
	return Best;
}

static JPawn* PawnByInst(void* Inst)
{
	int i;
	for (i = 0; i < NPawns; i++) if (Pawns[i].Inst == Inst && Pawns[i].Active) return &Pawns[i];
	return NULL;
}

static Vec ToWorld(const float* M, Vec m)
{
	return V(m.x * M[0] + m.y * M[4] + m.z * M[8] + M[12], m.x * M[1] + m.y * M[5] + m.z * M[9] + M[13], m.x * M[2] + m.y * M[6] + m.z * M[10] + M[14]);
}
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
	return V(w.x * inv[0] + w.y * inv[3] + w.z * inv[6], w.x * inv[1] + w.y * inv[4] + w.z * inv[7], w.x * inv[2] + w.y * inv[5] + w.z * inv[8]);
}

/* the convention, from the parent's offset in ITS parent's frame against the ref skeleton */
static void LearnConvention(JPawn* P, JBone* B, void* Inst)
{
	BYTE* RP = RefBone(P->Mesh, B->Parent);
	int G;
	FCoords *CP, *CG;
	Vec d, A, Bv, Ref;
	float ea, eb;
	if (Conv || !RP) return;
	G = *(int*)(RP + 0x34);
	if (G == B->Parent || G < 0) return;
	CP = BoneCoords(Inst, B->Parent); CG = BoneCoords(Inst, G);
	if (!CP || !CG) return;
	d = Sub(CP->O, CG->O);
	A = V(Dot(d, CG->X), Dot(d, CG->Y), Dot(d, CG->Z));
	Bv = V(CG->X.x * d.x + CG->Y.x * d.y + CG->Z.x * d.z, CG->X.y * d.x + CG->Y.y * d.y + CG->Z.y * d.z, CG->X.z * d.x + CG->Y.z * d.y + CG->Z.z * d.z);
	Ref = *(Vec*)(RP + 0x18);
	ea = Len(Sub(A, Ref)); eb = Len(Sub(Bv, Ref));
	if (ea < 0.5f && eb > 2.0f) { Conv = 1; Note(L"jiggle: bone coords convention: rows are the bone's basis vectors (%.2f vs %.2f)", ea, eb); }
	else if (eb < 0.5f && ea > 2.0f) { Conv = 2; Note(L"jiggle: bone coords convention: rows are the rotation's rows (%.2f vs %.2f)", eb, ea); }
}

/* ------------------------------------------------------------ the callback */

static void Identity(FCoords* Ret, void* Inst, int Bone)
{
	FCoords* C = Inst ? BoneCoords(Inst, Bone) : NULL;
	if (C) *Ret = *C;
	else { memset(Ret, 0, sizeof(*Ret)); Ret->X.x = Ret->Y.y = Ret->Z.z = 1; }
}

static void Spring(JPawn* P, JBone* B, FCoords* Ret, const FCoords* Cur, void* Inst)
{
	FCoords* CP = BoneCoords(Inst, B->Parent);
	BoneParam* K = B->P;
	Mat3 Rp;
	Vec c, centre, cw, a, al, drive;
	float M[16], dt, len, l2;
	LARGE_INTEGER Now;
	int sub, n;
	*Ret = *Cur;
	if (!CP || !K) return;
	if (!Conv) { LearnConvention(P, B, Inst); if (!Conv) return; }
	Rp = RotOf(CP);
	c = K->Lever;
	l2 = Dot(c, c);
	if (l2 < 1) return;
	/* the region centre, world, and its acceleration */
	MeshToWorld(Inst, NULL, M);
	centre = Add(CP->O, MV(Rp, c));
	cw = ToWorld(M, centre);
	QueryPerformanceCounter(&Now);
	dt = B->LastT.QuadPart ? (float)((Now.QuadPart - B->LastT.QuadPart) / (double)Freq.QuadPart) : 0.0f;
	B->LastT = Now;
	if (dt <= 0 || dt > 0.1f) { B->History = 0; B->PosW[0] = cw; B->History = 1; dt = 0; }
	a = V(0, 0, 0);
	if (dt > 0)
	{
		Vec v = Mul(Sub(cw, B->PosW[0]), 1.0f / dt);
		if (B->History >= 2) a = Mul(Sub(v, B->VelW), 1.0f / dt);
		B->VelW = v;
		B->PosW[0] = cw;
		if (B->History < 2) B->History++;
		len = Len(a);
		if (len > MaxAccel) a = Mul(a, MaxAccel / len);
	}
	/* into the parent's frame: a_l = Rp^T a_mesh */
	al = DirToMesh(M, a);
	al = MV(Tr(Rp), al);
	drive = Mul(Cross(c, Mul(al, -1.0f)), K->Gain * GlobalGain / l2);
	/* the impulse of a hit */
	if (Len(B->Impulse) > 0) { B->Omega = Add(B->Omega, B->Impulse); B->Impulse = V(0, 0, 0); }
	/* integrate (semi-implicit Euler, substeps so a stiff spring stays stable) */
	if (dt > 0)
	{
		n = (int)(dt * 480) + 1;
		if (n > 16) n = 16;
		for (sub = 0; sub < n; sub++)
		{
			float h = dt / n;
			Vec acc = Sub(Sub(drive, Mul(B->Theta, K->K)), Mul(B->Omega, K->D));
			B->Omega = Add(B->Omega, Mul(acc, h));
			B->Theta = Add(B->Theta, Mul(B->Omega, h));
		}
	}
	len = Len(B->Theta);
	if (len > K->MaxRad)
	{
		B->Theta = Mul(B->Theta, K->MaxRad / len);
		/* no velocity outward past the clamp */
		{
			Vec n0 = Mul(B->Theta, 1.0f / K->MaxRad);
			float out = Dot(B->Omega, n0);
			if (out > 0) B->Omega = Sub(B->Omega, Mul(n0, out));
		}
		len = K->MaxRad;
	}
	B->AmpSum += len; B->AmpN++; if (len > B->AmpMax) B->AmpMax = len;
	if (len < 1e-5f) return;
	SetRot(Ret, MM(Rp, Exp(B->Theta)));
}

static void LogPawn(JPawn* P)
{
	DWORD Now = GetTickCount();
	wchar_t Line[600] = L"";
	int i;
	if (!LogOn || Now - P->LastLog < 5000) return;
	P->LastLog = Now;
	for (i = 0; i < P->NB; i++)
	{
		JBone* B = &P->B[i];
		swprintf(Line + wcslen(Line), 60, L" %ls %.1f/%.1f", B->P ? B->P->Name : L"?", B->AmpN ? B->AmpSum / B->AmpN * 57.2958f : 0.0f, B->AmpMax * 57.2958f);
		B->AmpSum = 0; B->AmpN = 0; B->AmpMax = 0;
	}
	Note(L"jiggle: %ls: %d callbacks, %.1f us each, faults %d; amplitude mean/max (deg):%ls", P->Name, P->Calls, P->Calls ? P->SolveUs / P->Calls : 0.0, P->Faults, Line);
	P->Calls = 0; P->SolveUs = 0;
}

static FCoords* Solve(FCoords* Ret, void* Owner, int Bone, int Dir, void* Inst)
{
	JPawn* P = PawnByInst(Inst);
	FCoords* Cur = BoneCoords(Inst, Bone);
	LARGE_INTEGER T0, T1;
	int i;
	if (!P || !Cur || P->Actor != Owner) { Identity(Ret, Inst, Bone); return Ret; }
	if (*((BYTE*)Owner + 0x55) == 0xF || (*(DWORD*)((BYTE*)Owner + 0x34) & 0x80)) { *Ret = *Cur; return Ret; }
	QueryPerformanceCounter(&T0);
	P->Calls++;
	for (i = 0; i < P->NB; i++) if (P->B[i].Bone == Bone) { Spring(P, &P->B[i], Ret, Cur, Inst); break; }
	if (i == P->NB) *Ret = *Cur;
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
		JPawn* P;
		TotalFaults++;
		__try { P = PawnByInst(Inst); if (P) { P->Faults++; if (P->Faults > 3) P->Active = 0; } Identity(Ret, Inst, Bone); }
		__except (EXCEPTION_EXECUTE_HANDLER) { memset(Ret, 0, sizeof(*Ret)); Ret->X.x = Ret->Y.y = Ret->Z.z = 1; }
		if (TotalFaults <= 5) Note(L"jiggle: exception in the callback (bone %d): the bone was left as animated", Bone);
		return Ret;
	}
}

/* ------------------------------------------------------------ commands */

static BoneParam* ParamByName(const wchar_t* Name)
{
	int i;
	for (i = 0; i < NParams; i++) if (!_wcsicmp(Params[i].Name, Name)) return &Params[i];
	return NULL;
}

static int Hook(JPawn* P, JBone* B, void* Fn, float Alpha)
{
	int a = SetBoneDirection(P->Inst, NULL, B->Name, 0, 0, 0, 0, 0, 0, Alpha, 99, B->Bone);
	int b = SetWorldSpacer(P->Inst, NULL, B->Name, Fn, B->Bone);
	if (!a || !b) Note(L"jiggle: %ls: director on bone %d: SetBoneDirection %d, SetWorldSpacerFunction %d", P->Name, B->Bone, a, b);
	return a && b;
}

static int Install(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	int n, i, used = 0;
	void* Actor;
	void* Inst;
	JPawn* P = NULL;
	const wchar_t* s = Arg;
	if (swscanf(Arg, L"%47s %47s %d%n", Name, Class, &n, &used) != 3 || n < 1 || n > 16) { Note(L"jiggle: bad install '%ls'", Arg); return 0; }
	s += used;
	if (!Resolve()) return 0;
	Actor = FindActor(Name, Class);
	if (!Actor) { Note(L"jiggle: no actor %ls (%ls)", Name, Class); return 0; }
	Inst = InstanceOf(Actor, Name);
	if (!Inst) return 0;
	for (i = 0; i < NPawns; i++) if (Pawns[i].Actor == Actor) P = &Pawns[i];
	if (P && P->Active && P->Inst == Inst) return 1;
	if (!P) for (i = 0; i < NPawns; i++) if (!Pawns[i].Active) { P = &Pawns[i]; break; }
	if (!P) { if (NPawns >= MAXPAWNS) { Note(L"jiggle: no room for %ls", Name); return 0; } P = &Pawns[NPawns++]; }
	memset(P, 0, sizeof(*P));
	P->Actor = Actor; P->Inst = Inst; P->Mesh = *(void**)((BYTE*)Actor + 0xD4);
	wcscpy(P->Name, Name);
	if (!P->Mesh) return 0;
	for (i = 0; i < n; i++)
	{
		int bone;
		BYTE* RB;
		const wchar_t* bn;
		JBone* B = &P->B[P->NB];
		if (swscanf(s, L" %d%n", &bone, &used) != 1) { Note(L"jiggle: %ls: bone list short", Name); return 0; }
		s += used;
		RB = RefBone(P->Mesh, bone);
		if (!RB || bone < 1) { Note(L"jiggle: %ls: bone %d isn't in the mesh", Name, bone); return 0; }
		bn = FNameStr((DWORD*)RB, NULL);
		if (!bn || _wcsnicmp(bn, L"J_", 2) || *(int*)(RB + 0x38) != 0) { Note(L"jiggle: %ls: bone %d (%ls) isn't a J_ leaf: refused", Name, bone, bn ? bn : L"?"); return 0; }
		B->Bone = bone;
		B->Parent = *(int*)(RB + 0x34);
		B->Name = *(DWORD*)RB;
		B->P = ParamByName(bn);
		if (!B->P) { Note(L"jiggle: %ls: no parameters for %ls (JiggleBone first)", Name, bn); return 0; }
		P->NB++;
	}
	P->Active = 1;
	for (i = 0; i < P->NB; i++)
		if (!Hook(P, &P->B[i], WorldSpacer, 1.0f)) { P->Active = 0; return 0; }
	if (LogOn) Note(L"jiggle: hooked %ls (%ls): %d bones, %d posed", Name, Class, P->NB, *(int*)((BYTE*)Inst + 0xB8));
	return 1;
}

static int Remove(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	int i, j;
	if (swscanf(Arg, L"%47s %47s", Name, Class) != 2) return 0;
	for (i = 0; i < NPawns; i++)
	{
		JPawn* P = &Pawns[i];
		if (!P->Active || _wcsicmp(P->Name, Name)) continue;
		P->Active = 0;
		if (!(*(DWORD*)((BYTE*)P->Actor + 0x34) & 0x80) && InstanceOf(P->Actor, NULL) == P->Inst)
			for (j = 0; j < P->NB; j++) Hook(P, &P->B[j], NULL, 0.0f);
		if (LogOn) Note(L"jiggle: released %ls", Name);
		return 1;
	}
	return 0;
}

static int HitCmd(const wchar_t* Arg)
{
	wchar_t Name[48], Class[48];
	Vec d;
	float strength, M[16];
	int i, j;
	void* Inst;
	if (swscanf(Arg, L"%47s %47s %f %f %f %f", Name, Class, &d.x, &d.y, &d.z, &strength) != 6) return 0;
	for (i = 0; i < NPawns; i++)
	{
		JPawn* P = &Pawns[i];
		Vec dm;
		if (!P->Active || _wcsicmp(P->Name, Name)) continue;
		Inst = P->Inst;
		MeshToWorld(Inst, NULL, M);
		dm = DirToMesh(M, d);
		if (Len(dm) < 1e-6f) return 1;
		dm = Mul(dm, 1.0f / Len(dm));
		for (j = 0; j < P->NB; j++)
		{
			JBone* B = &P->B[j];
			FCoords* CP = BoneCoords(Inst, B->Parent);
			Vec dl, c;
			if (!CP || !B->P || !Conv) continue;
			dl = MV(Tr(RotOf(CP)), dm);
			c = B->P->Lever;
			/* a push along d swings the mass about the joint: omega += strength * (c x d) / |c| */
			B->Impulse = Add(B->Impulse, Mul(Cross(c, dl), strength / (Len(c) + 1e-3f)));
		}
		return 1;
	}
	return 0;
}

static int BoneCmd(const wchar_t* Arg)
{
	wchar_t Name[32];
	float k, d, g, deg, lx, ly, lz;
	BoneParam* P;
	if (swscanf(Arg, L"%31s %f %f %f %f %f %f %f", Name, &k, &d, &g, &deg, &lx, &ly, &lz) != 8) { Note(L"jiggle: bad bone line '%ls'", Arg); return 0; }
	P = ParamByName(Name);
	if (!P) { if (NParams >= MAXPARAMS) return 0; P = &Params[NParams++]; wcscpy(P->Name, Name); }
	P->K = k; P->D = d; P->Gain = g; P->MaxRad = deg * 0.0174533f; P->Lever = V(lx, ly, lz);
	return 1;
}

static int Config(const wchar_t* Arg)
{
	float g, ma; int lg;
	if (swscanf(Arg, L"%f %d %f", &g, &lg, &ma) != 3) return 0;
	GlobalGain = g; LogOn = lg; MaxAccel = ma;
	Note(L"jiggle: config gain %.2f log %d max accel %.0f", GlobalGain, LogOn, MaxAccel);
	return Resolve();
}

int JiggleCommand(const wchar_t* Cmd)
{
	if (!_wcsnicmp(Cmd, L"JiggleConfig ", 13)) return Config(Cmd + 13);
	if (!_wcsnicmp(Cmd, L"JiggleBone ", 11)) return BoneCmd(Cmd + 11);
	if (!_wcsnicmp(Cmd, L"JiggleOff ", 10)) return Remove(Cmd + 10);
	if (!_wcsnicmp(Cmd, L"JiggleHit ", 10)) return HitCmd(Cmd + 10);
	if (!_wcsnicmp(Cmd, L"Jiggle ", 7)) return Install(Cmd + 7);
	return 0;
}
