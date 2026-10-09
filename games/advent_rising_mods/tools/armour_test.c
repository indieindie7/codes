/* offline check of armour.c: load the .amesh, pose it with its own reference skeleton as the
   engine would hand it (FCoords per bone, both row conventions), skin it (must reproduce the
   reference vertices), cast rays at armour and flesh faces, and time a cast.
   Run from a folder that has ..\AdventMod\Armour\<mesh>.amesh next to it. */
#include "armour.c"

void Note(const wchar_t* Fmt, ...)
{
	va_list A;
	va_start(A, Fmt);
	vwprintf(Fmt, A);
	va_end(A);
	wprintf(L"\n");
}

int wmain(int argc, wchar_t** argv)
{
	AMesh* A;
	FCoords* Bones;
	int i, conv, armourOk = 0, armourN = 0, fleshOk = 0, fleshN = 0, misses = 0;
	float maxErr = 0;
	LARGE_INTEGER T0, T1;
	if (argc < 2) { wprintf(L"usage: armour_test <mesh>\n"); return 1; }
	QueryPerformanceFrequency(&Freq);
	A = Load(argv[1]);
	if (!A) return 1;
	Bones = (FCoords*)calloc(A->NB, sizeof(FCoords));
	for (conv = 1; conv <= 2; conv++)
	{
		int learned;
		for (i = 0; i < A->NB; i++)
		{
			Mat3 R = A->B[i].RefR;
			if (conv == 1) R = Tr(R);          /* rows as basis vectors = the columns of R */
			Bones[i].O = A->B[i].RefO;
			Bones[i].X = V3(R.m[0][0], R.m[0][1], R.m[0][2]);
			Bones[i].Y = V3(R.m[1][0], R.m[1][1], R.m[1][2]);
			Bones[i].Z = V3(R.m[2][0], R.m[2][1], R.m[2][2]);
		}
		learned = LearnConv(A, Bones);
		wprintf(L"posed with convention %d: learned %d %ls\n", conv, learned, learned == conv ? L"(right)" : L"(WRONG)");
		A->Conv = learned;
	}
	/* convention 2 is in Bones now: skin and compare */
	{
		float t, u, v;
		CastRay(A, Bones, V3(0, 0, 0), V3(1, 0, 0), &t, &u, &v);
		for (i = 0; i < A->NV; i++) { float e = Len(Sub(A->Skinned[i], A->V[i].P)); if (e > maxErr) maxErr = e; }
		wprintf(L"skinned in the reference pose: max vertex error %.4f units over %d vertices\n", maxErr, A->NV);
	}
	/* rays at face centroids from outside (along both normals: the nearer unoccluded side) */
	for (i = 0; i < A->NF; i += 7)
	{
		AFace* F = &A->F[i];
		Vec a = A->V[F->V[0]].P, b = A->V[F->V[1]].P, c = A->V[F->V[2]].P;
		Vec cen = Mul(Add(a, Add(b, c)), 1.0f / 3), n = Cross(Sub(b, a), Sub(c, a));
		int side, got = -1;
		float t, u, v;
		if (Len(n) < 1e-6f) continue;
		n = Mul(n, 1.0f / Len(n));
		for (side = -1; side <= 1 && got != i; side += 2)
		{
			Vec O = Add(cen, Mul(n, 60.0f * side)), D = Mul(n, (float)-side);
			got = CastRay(A, Bones, O, D, &t, &u, &v);
		}
		if (F->Armour) { armourN++; if (got >= 0 && A->F[got].Armour) armourOk++; }
		else { fleshN++; if (got >= 0 && !A->F[got].Armour) fleshOk++; }
		if (got < 0) misses++;
	}
	wprintf(L"rays at face centroids: armour faces %d/%d answered armour, flesh faces %d/%d answered flesh, %d rays met nothing (a hit on another face in front is counted by that face's flag)\n", armourOk, armourN, fleshOk, fleshN, misses);
	{
		float t, u, v;
		int n = 200, k;
		QueryPerformanceCounter(&T0);
		for (k = 0; k < n; k++) CastRay(A, Bones, V3(0, -500, 300), V3(0, 1, -0.3f), &t, &u, &v);
		QueryPerformanceCounter(&T1);
		wprintf(L"a cast (skin %d vertices + %d triangles): %.1f us\n", A->NV, A->NF, (T1.QuadPart - T0.QuadPart) * 1e6 / Freq.QuadPart / n);
	}
	return 0;
}
