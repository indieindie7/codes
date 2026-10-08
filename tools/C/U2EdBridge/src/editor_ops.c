/*
 * editor_ops.c - per-actor editor operations for U2EdBridge (the "ops" build only).
 *
 * Built into bin\U2EdBridge_ops.dll by compiling u2edbridge.c with -DU2ED_OPS, which #includes this
 * file. The ops build listens on its own pipe (\\.\pipe\U2EdBridgeOps-<pid>) and uses its own window
 * message, so it can be injected into an editor that already runs the normal bridge.
 *
 *   !select [+] PAT ...          select the actors whose names match (wildcards * ?); "+" adds to the
 *                                selection instead of replacing it. One undo step, NoteSelectionChange.
 *   !deselect PAT ... | all
 *   !list [PAT] [class=CLS]      Name Class Location Rotation [selected] - one actor per line
 *   !move PAT x y z [p y r]      absolute place (PAT must match ONE actor; "-" keeps a value)
 *   !moveby PAT dx dy dz [dp dy dr]   relative, every matching actor
 *   !light PAT ... | selected    rebuild the static (vertex) lighting of these StaticMeshActors only;
 *                                BSP lightmaps and every other actor are left alone
 *   !lights PAT                  light-list diagnosis for one actor: zones, ambient, the lights the
 *                                BSP light lists give it (what LIGHT APPLY will use)
 *   !lightsat x y z              the same for a point (BSP leaf + zone at that spot)
 *   !opsinfo                     resolved offsets / exports
 * PAT "selected" means the current selection.
 *
 * Everything here was read from the Ghidra decompile of Unreal II's Editor.dll / Engine.dll / Core.dll
 * (build of Mar 14 2003); EDITOR_OPS.md has the evidence. Data offsets are taken from the property
 * system at runtime where the property exists in UnrealScript, and checked against the decompile;
 * if a check fails the commands refuse to run instead of guessing.
 */

/* ---- layout facts from the decompile ---- */
#define UOBJ_CLASS        0x24   /* UObject::Class (GlobalSetProperty, StaticFindObject) */
#define UFIELD_SUPER      0x28   /* UField::SuperField (class chain walked in GlobalSetProperty) */
#define UFIELD_NEXT       0x2c   /* UField::Next (FindField helper FUN_101339f0) */
#define USTRUCT_CHILDREN  0x3c   /* UStruct::Children (same helper) */
#define UPROP_ELEMSIZE    0x38   /* UProperty::ElementSize (UProperty::ExportText) */
#define UPROP_OFFSET      0x48   /* UProperty::Offset (UObject::StaticExec -> GlobalSetProperty) */
#define UBOOL_MASK        0x6c   /* UBoolProperty::BitMask (UBoolProperty::ExportTextItem) */
#define LEVEL_ACTORS      0x2c   /* ULevel::Actors, TArray: data, num */
#define LEVEL_MODEL       0x8c   /* ULevel::Model (shadowIlluminateBsp, UModel::Illuminate) */
#define MODEL_LEAVES      0xc0   /* UModel::Leaves, FLeaf = { iZone, iPermeating, iVolumetric, QWORD } */
#define MODEL_LIGHTS      0xcc   /* UModel::Lights, AActor* runs ended by NULL (FEditorVisibility) */
#define FLEAF_SIZE        0x14
/* virtual slots, byte offsets into the vtable */
#define VT_MODIFY         0x24   /* UObject::Modify */
#define VT_POSTEDITCHANGE 0x54   /* UObject::PostEditChange */
#define VT_POSTEDITMOVE   0x8c   /* AActor::PostEditMove (AMover/ANavigationPoint/AProjector override it) */
#define VT_GETPRIMITIVE   0xd0   /* AActor::GetPrimitive */
#define VT_ILLUMINATE     0x84   /* UPrimitive::Illuminate(AActor*, UBOOL bChangedOnly) */
#define VT_ED_REDRAWLEVEL 0xdc   /* UEditorEngine::RedrawLevel(ULevel*) */
#define VT_ED_NOTESEL     0xe8   /* UEditorEngine::NoteSelectionChange(ULevel*) */
#define VT_ED_UPDPROPS    0xf8   /* UEditorEngine::UpdatePropertiesWindows() */
#define VT_ED_SELECTACTOR 0x130  /* UEditorEngine::SelectActor(ULevel*, AActor*, UBOOL sel, UBOOL notify) */
#define VT_ED_SELECTNONE  0x134  /* UEditorEngine::SelectNone(ULevel*, UBOOL notify, UBOOL bspSurfs) */
#define VT_TRANS_BEGIN    0x78   /* UTransBuffer::Begin(const TCHAR*) */
#define VT_TRANS_END      0x7c   /* UTransBuffer::End() */

#define AT(p, off, T) (*(T *)((char *)(p) + (off)))
#define VSLOT(obj, off) ((*(void ***)(obj))[(off) / 4])

typedef struct { float X, Y, Z; } OpsVec;
typedef struct { int Pitch, Yaw, Roll; } OpsRot;
typedef struct { void *Zone; int iLeaf; unsigned char ZoneNumber; char pad[3]; } OpsPointRegion;

typedef const wchar_t *(TC *GetNameFn)(void *obj);
typedef int (TC *IsAFn)(void *obj, void *cls);
typedef void *(__cdecl *StaticClassFn)(void);
typedef void (TC *VoidFn)(void *self);
typedef void *(TC *PtrFn)(void *self);
typedef void *(TC *PtrIntFn)(void *self, int i);
typedef int (TC *ExportTextFn)(void *prop, int index, wchar_t *out, void *data, void *delta, int flags);
typedef int (TC *FarMoveActorFn)(void *level, void *actor, float x, float y, float z, int test, int nocheck, int attached);
typedef OpsPointRegion *(TC *PointRegionFn)(void *model, OpsPointRegion *ret, void *zone, float x, float y, float z);
typedef void (TC *IlluminateFn)(void *prim, void *actor, int changedOnly);
typedef void (TC *EdLevelFn)(void *ed, void *level);
typedef void (TC *EdSelectActorFn)(void *ed, void *level, void *actor, int sel, int notify);
typedef void (TC *EdSelectNoneFn)(void *ed, void *level, int notify, int bspSurfs);
typedef void (TC *TransBeginFn)(void *trans, const wchar_t *what);

static void *g_ed;                       /* GEditor, set by Main in u2edbridge.c */

static struct {
	int ready, failed;
	GetNameFn GetName;
	IsAFn IsA;
	void *clsProperty, *clsBoolProperty, *clsActor, *clsMover;
	FarMoveActorFn FarMoveActor;
	PtrFn LevelBrush, LevelInfo, ActorRenderData;
	PtrIntFn ZoneActor;
	VoidFn ClearRenderData;
	PointRegionFn PointRegion;
	void *illum[4];                      /* UStaticMesh/UPrimitive/UModel/UTerrainPrimitive::Illuminate */
	void *edVtbl;
	/* offsets resolved from the property system */
	int offLocation, offRotation, offXLevel, offLeaves, offLevel, offTrans;
	int offSelected; unsigned maskSelected;
	int offStatic; unsigned maskStatic;
	int offHiddenEd; unsigned maskHiddenEd;
	int offHiddenGroup; unsigned maskHiddenGroup;
	int offLock; unsigned maskLock;
} O;

static void Out(const wchar_t *fmt, ...)
{
	wchar_t buf[2048];
	va_list ap;
	va_start(ap, fmt);
	_vsnwprintf(buf, 2047, fmt, ap);
	va_end(ap);
	buf[2047] = 0;
	CapLine(buf);
}

/* ---- property system ---- */

static void *FindProp(void *cls, const wchar_t *name)
{
	void *s, *f;
	int guard = 0;
	for (s = cls; s && guard < 64; s = AT(s, UFIELD_SUPER, void *), guard++)
		for (f = AT(s, USTRUCT_CHILDREN, void *); f && guard < 100000; f = AT(f, UFIELD_NEXT, void *), guard++)
			if (O.IsA(f, O.clsProperty) && !_wcsicmp(O.GetName(f), name))
				return f;
	return NULL;
}

static int PropOffset(void *cls, const wchar_t *name)
{
	void *p = FindProp(cls, name);
	return p ? AT(p, UPROP_OFFSET, int) : -1;
}

static int BoolProp(void *cls, const wchar_t *name, int *off, unsigned *mask)
{
	void *p = FindProp(cls, name);
	*off = -1; *mask = 0;
	if (!p || !O.IsA(p, O.clsBoolProperty)) return 0;
	*off = AT(p, UPROP_OFFSET, int);
	*mask = AT(p, UBOOL_MASK, unsigned);
	return 1;
}

static int Flag(void *obj, int off, unsigned mask)
{
	return off >= 0 && (AT(obj, off, unsigned) & mask) != 0;
}

/* a property of any object as text, through the engine's own ExportText ("?" if there is none) */
static const wchar_t *PropText(void *obj, const wchar_t *name, wchar_t *buf)
{
	void *p = obj ? FindProp(AT(obj, UOBJ_CLASS, void *), name) : NULL;
	buf[0] = 0;
	if (!p) { lstrcpyW(buf, L"?"); return buf; }
	((ExportTextFn)VSLOT(p, 0xa8))(p, 0, buf, obj, NULL, 0);
	return buf;
}

/* ---- setup ---- */

#define NEED(var, mod, name) do { if (!((var) = (void *)GetProcAddress(mod, name))) { BLog("ops: missing export %s", name); ok = 0; } } while (0)

static int OpsInit(void)
{
	HMODULE core = GetModuleHandleW(L"Core.dll"), eng = GetModuleHandleW(L"Engine.dll"),
	        ed = GetModuleHandleW(L"Editor.dll");
	StaticClassFn sc;
	void *edClass;
	int ok = 1, off;
	unsigned mask;
	if (O.ready) return 1;
	if (O.failed) { CapLine(L"ops: disabled (startup checks failed, see U2EdBridge_ops.log)"); return 0; }
	if (!core || !eng || !ed || !g_ed) { CapLine(L"ops: editor modules not found"); return 0; }

	NEED(O.GetName, core, "?GetName@UObject@@QBEPBGXZ");
	NEED(O.IsA, core, "?IsA@UObject@@QBEHPAVUClass@@@Z");
	NEED(sc, core, "?StaticClass@UProperty@@SAPAVUClass@@XZ");      if (sc) O.clsProperty = sc();
	NEED(sc, core, "?StaticClass@UBoolProperty@@SAPAVUClass@@XZ");  if (sc) O.clsBoolProperty = sc();
	NEED(sc, eng, "?StaticClass@AActor@@SAPAVUClass@@XZ");          if (sc) O.clsActor = sc();
	NEED(sc, eng, "?StaticClass@AMover@@SAPAVUClass@@XZ");          if (sc) O.clsMover = sc();
	NEED(O.FarMoveActor, eng, "?FarMoveActor@ULevel@@UAEHPAVAActor@@VFVector@@HHH@Z");
	NEED(O.LevelBrush, eng, "?Brush@ULevel@@QAEPAVABrush@@XZ");
	NEED(O.LevelInfo, eng, "?GetLevelInfo@ULevel@@QAEPAVALevelInfo@@XZ");
	NEED(O.ZoneActor, eng, "?GetZoneActor@ULevel@@QAEPAVAZoneInfo@@H@Z");
	NEED(O.ActorRenderData, eng, "?GetActorRenderData@AActor@@QAEPAVFDynamicActor@@XZ");
	NEED(O.ClearRenderData, eng, "?ClearRenderData@AActor@@QAEXXZ");
	NEED(O.PointRegion, eng, "?PointRegion@UModel@@QBE?AUFPointRegion@@PAVAZoneInfo@@VFVector@@@Z");
	NEED(O.illum[0], eng, "?Illuminate@UStaticMesh@@UAEXPAVAActor@@H@Z");
	NEED(O.illum[1], eng, "?Illuminate@UPrimitive@@UAEXPAVAActor@@H@Z");
	NEED(O.illum[2], eng, "?Illuminate@UModel@@UAEXPAVAActor@@H@Z");
	NEED(O.illum[3], eng, "?Illuminate@UTerrainPrimitive@@UAEXPAVAActor@@H@Z");
	NEED(O.edVtbl, ed, "??_7UEditorEngine@@6BUObject@@@");
	if (!ok) goto fail;

	/* the editor slots were read from UEditorEngine's own vtable: GEditor must be exactly that class */
	if (*(void **)g_ed != O.edVtbl) { BLog("ops: GEditor's vtable is not UEditorEngine's (subclass?)"); goto fail; }

	/* actor properties, checked against the offsets the decompiled code uses */
	O.offLocation = PropOffset(O.clsActor, L"Location");
	O.offRotation = PropOffset(O.clsActor, L"Rotation");
	O.offXLevel   = PropOffset(O.clsActor, L"XLevel");
	O.offLeaves   = PropOffset(O.clsActor, L"Leaves");
	BoolProp(O.clsActor, L"bSelected", &O.offSelected, &O.maskSelected);
	BoolProp(O.clsActor, L"bStatic", &O.offStatic, &O.maskStatic);
	BoolProp(O.clsActor, L"bHiddenEd", &O.offHiddenEd, &O.maskHiddenEd);
	BoolProp(O.clsActor, L"bHiddenEdGroup", &O.offHiddenGroup, &O.maskHiddenGroup);
	BoolProp(O.clsActor, L"bLockLocation", &O.offLock, &O.maskLock);
	BLog("ops: Location %x Rotation %x XLevel %x Leaves %x bSelected %x/%x bStatic %x/%x bHiddenEd %x/%x bHiddenEdGroup %x/%x",
	     O.offLocation, O.offRotation, O.offXLevel, O.offLeaves, O.offSelected, O.maskSelected,
	     O.offStatic, O.maskStatic, O.offHiddenEd, O.maskHiddenEd, O.offHiddenGroup, O.maskHiddenGroup);
	if (O.offLocation != 0x124 || O.offRotation != 0x130 || O.offXLevel != 0xd4
	    || O.offSelected != 0x364 || O.maskSelected != 0x200)
	{
		BLog("ops: actor layout differs from the decompile (Location 0x124, Rotation 0x130, XLevel 0xd4, bSelected 0x364/0x200)");
		goto fail;
	}
	if (O.offLeaves < 0) O.offLeaves = 0xf4;          /* UStaticMesh::Illuminate / UpdateRenderData use 0xf4 */

	/* GEditor->Level and ->Trans: script properties of EditorEngine if declared, else the decompiled 0x120 / 0x13c */
	edClass = AT(g_ed, UOBJ_CLASS, void *);
	off = PropOffset(edClass, L"Level"); O.offLevel = off >= 0 ? off : 0x120;
	off = PropOffset(edClass, L"Trans"); O.offTrans = off >= 0 ? off : 0x13c;
	BLog("ops: GEditor Level at %x, Trans at %x", O.offLevel, O.offTrans);
	(void)mask;
	O.ready = 1;
	return 1;
fail:
	O.failed = 1;
	CapLine(L"ops: startup checks failed, commands disabled (see U2EdBridge_ops.log)");
	return 0;
}

/* ---- level and actors ---- */

static void *Level(void) { return AT(g_ed, O.offLevel, void *); }
static void *Trans(void) { return AT(g_ed, O.offTrans, void *); }

static int NumActors(void *lvl) { return AT(lvl, LEVEL_ACTORS + 4, int); }
static void *ActorAt(void *lvl, int i) { return AT(lvl, LEVEL_ACTORS, void **)[i]; }

/* case-insensitive glob: * and ? */
static int Match(const wchar_t *pat, const wchar_t *s)
{
	for (; *pat; pat++, s++)
	{
		if (*pat == L'*')
		{
			while (pat[1] == L'*') pat++;
			if (!pat[1]) return 1;
			for (; *s; s++) if (Match(pat + 1, s)) return 1;
			return 0;
		}
		if (!*s) return 0;
		if (*pat != L'?' && towlower(*pat) != towlower(*s)) return 0;
	}
	return !*s;
}

static int IsSelected(void *a) { return Flag(a, O.offSelected, O.maskSelected); }

static int Targets(void *lvl, const wchar_t *pat, void *a)
{
	if (!a || a == O.LevelBrush(lvl)) return 0;
	if (!_wcsicmp(pat, L"selected")) return IsSelected(a);
	return Match(pat, O.GetName(a));
}

/* split the argument string in place; returns the count */
static int Split(wchar_t *s, wchar_t **tok, int max)
{
	int n = 0;
	while (*s && n < max)
	{
		while (*s == L' ' || *s == L'\t') s++;
		if (!*s) break;
		tok[n++] = s;
		while (*s && *s != L' ' && *s != L'\t') s++;
		if (*s) *s++ = 0;
	}
	return n;
}

static void Begin(const wchar_t *what) { void *t = Trans(); if (t) ((TransBeginFn)VSLOT(t, VT_TRANS_BEGIN))(t, what); }
static void End(void) { void *t = Trans(); if (t) ((VoidFn)VSLOT(t, VT_TRANS_END))(t); }
static void Redraw(void *lvl)
{
	((EdLevelFn)VSLOT(g_ed, VT_ED_REDRAWLEVEL))(g_ed, lvl);
	((VoidFn)VSLOT(g_ed, VT_ED_UPDPROPS))(g_ed);
}

/* ---- !select / !deselect / !list ---- */

static int OpSelect(wchar_t **tok, int n, int select)
{
	void *lvl = Level();
	int i, k, count = 0, add = 0, all = 0;
	if (n && (!wcscmp(tok[0], L"+") || !_wcsicmp(tok[0], L"add"))) { add = 1; tok++; n--; }
	if (!select && n == 1 && !_wcsicmp(tok[0], L"all")) all = 1;
	if (!n) { CapLine(select ? L"usage: !select [+] NAME|PATTERN ..." : L"usage: !deselect NAME|PATTERN ...|all"); return 0; }
	Begin(select ? L"Bridge Select" : L"Bridge Deselect");
	if ((select && !add) || all)
		((EdSelectNoneFn)VSLOT(g_ed, VT_ED_SELECTNONE))(g_ed, lvl, 0, 1);
	if (!all)
		for (i = 0; i < NumActors(lvl); i++)
		{
			void *a = ActorAt(lvl, i);
			for (k = 0; k < n; k++)
				if (Targets(lvl, tok[k], a))
				{
					((EdSelectActorFn)VSLOT(g_ed, VT_ED_SELECTACTOR))(g_ed, lvl, a, select, 0);
					if (count < 200) Out(L"%s %s", select ? L"selected" : L"deselected", O.GetName(a));
					count++;
					break;
				}
		}
	End();
	((EdLevelFn)VSLOT(g_ed, VT_ED_NOTESEL))(g_ed, lvl);
	((EdLevelFn)VSLOT(g_ed, VT_ED_REDRAWLEVEL))(g_ed, lvl);
	if (all) CapLine(L"selection cleared");
	else Out(L"%s %d actor(s)", select ? L"selected" : L"deselected", count);
	if (select && !count) CapLine(L"Not found: no actor name matches");
	return count > 0 || all;
}

static int OpList(wchar_t **tok, int n)
{
	void *lvl = Level();
	const wchar_t *pat = L"*", *cls = NULL;
	wchar_t loc[256], rot[256];
	int i, k, count = 0;
	for (k = 0; k < n; k++)
		if (!_wcsnicmp(tok[k], L"class=", 6)) cls = tok[k] + 6; else pat = tok[k];
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i), *c;
		if (!Targets(lvl, pat, a)) continue;
		if (cls)
		{
			for (c = AT(a, UOBJ_CLASS, void *); c; c = AT(c, UFIELD_SUPER, void *))
				if (!_wcsicmp(O.GetName(c), cls)) break;
			if (!c) continue;
		}
		Out(L"%s %s %s %s%s", O.GetName(a), O.GetName(AT(a, UOBJ_CLASS, void *)),
		    PropText(a, L"Location", loc), PropText(a, L"Rotation", rot), IsSelected(a) ? L" selected" : L"");
		count++;
	}
	Out(L"%d actor(s)", count);
	return 1;
}

/* ---- !move / !moveby ---- */

static int ParseNum(const wchar_t *s, double *v)
{
	wchar_t *end;
	if (!wcscmp(s, L"-") || !wcscmp(s, L"_")) return 0;   /* keep */
	*v = wcstod(s, &end);
	return end != s;
}

static void MoveOne(void *lvl, void *a, const double *val, const int *have, int relative)
{
	OpsVec *loc = &AT(a, O.offLocation, OpsVec);
	OpsRot *rot = &AT(a, O.offRotation, OpsRot);
	OpsVec to = *loc;
	OpsRot r = *rot;
	wchar_t lb[256], rb[256];
	float *tv = &to.X;
	int *rv = &r.Pitch, k;
	for (k = 0; k < 3; k++) if (have[k]) tv[k] = (float)(relative ? tv[k] + val[k] : val[k]);
	for (k = 0; k < 3; k++) if (have[3 + k]) rv[k] = (int)(relative ? rv[k] + val[3 + k] : val[3 + k]);
	if (Flag(a, O.offLock, O.maskLock)) Out(L"%s has bLockLocation (moved anyway)", O.GetName(a));
	((VoidFn)VSLOT(a, VT_MODIFY))(a);                       /* undo record */
	*rot = r;                                               /* before the move, so the collision hash sees it */
	if (!O.FarMoveActor(lvl, a, to.X, to.Y, to.Z, 0, 1, 0)) /* bTest=0, bNoCheck=1: no encroach test */
		Out(L"Can't move %s (FarMoveActor refused)", O.GetName(a));
	((VoidFn)VSLOT(a, VT_POSTEDITMOVE))(a);
	((VoidFn)VSLOT(a, VT_POSTEDITCHANGE))(a);               /* bLightChanged + ClearRenderData */
	Out(L"moved %s to %s %s", O.GetName(a), PropText(a, L"Location", lb), PropText(a, L"Rotation", rb));
}

static int OpMove(wchar_t **tok, int n, int relative)
{
	void *lvl = Level();
	double val[6] = { 0 };
	int have[6] = { 0 }, i, k, count = 0, matches = 0;
	if (n != 4 && n != 7)
	{
		CapLine(relative ? L"usage: !moveby NAME|PATTERN|selected dx dy dz [dpitch dyaw droll]"
		                 : L"usage: !move NAME|selected x y z [pitch yaw roll]   (- keeps a value)");
		return 0;
	}
	for (k = 1; k < n; k++)
	{
		have[k - 1] = ParseNum(tok[k], &val[k - 1]);
		if (!have[k - 1] && wcscmp(tok[k], L"-") && wcscmp(tok[k], L"_")) { Out(L"Invalid number: %s", tok[k]); return 0; }
	}
	for (i = 0; i < NumActors(lvl); i++) if (Targets(lvl, tok[0], ActorAt(lvl, i))) matches++;
	if (!matches) { Out(L"Not found: %s", tok[0]); return 0; }
	if (!relative && matches > 1) { Out(L"Can't place %d actors at one spot (%s); use !moveby or one name", matches, tok[0]); return 0; }
	Begin(relative ? L"Bridge MoveBy" : L"Bridge Move");
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i);
		if (Targets(lvl, tok[0], a)) { MoveOne(lvl, a, val, have, relative); count++; }
	}
	End();
	Redraw(lvl);
	Out(L"%d actor(s) moved; static lighting is stale until !light or LIGHT APPLY", count);
	return 1;
}

/* ---- light lists (diagnosis) ---- */

static void ZoneLine(void *lvl, int iZone)
{
	void *z = O.ZoneActor(lvl, iZone);
	wchar_t b1[64], b2[64], b3[64];
	Out(L"  zone %d: %s AmbientBrightness=%s AmbientHue=%s AmbientSaturation=%s", iZone,
	    z ? O.GetName(z) : L"(none)", PropText(z, L"AmbientBrightness", b1), PropText(z, L"AmbientHue", b2),
	    PropText(z, L"AmbientSaturation", b3));
}

/* lights in the leaf's permeating list (built only by MAP REBUILD: FEditorVisibility::TestVisibility) */
static int LeafLights(void *lvl, int iLeaf, void **seen, int nseen, int max)
{
	void *model = AT(lvl, LEVEL_MODEL, void *);
	int numLeaves = AT(model, MODEL_LEAVES + 4, int), numLights = AT(model, MODEL_LIGHTS + 4, int), k, j;
	void **lights = AT(model, MODEL_LIGHTS, void **);
	char *leaf;
	if (iLeaf < 0 || iLeaf >= numLeaves) return nseen;
	leaf = AT(model, MODEL_LEAVES, char *) + iLeaf * FLEAF_SIZE;
	k = AT(leaf, 4, int);                                    /* iPermeating */
	for (; k >= 0 && k < numLights && lights[k]; k++)
	{
		for (j = 0; j < nseen && seen[j] != lights[k]; j++) {}
		if (j == nseen && nseen < max) seen[nseen++] = lights[k];
	}
	return nseen;
}

static void LightLines(void *target, void **seen, int nseen)
{
	wchar_t t[64], b[64], r[64], s[64];
	int k, mySpecial = -1, off;
	unsigned mask;
	if (target && BoolProp(AT(target, UOBJ_CLASS, void *), L"bSpecialLit", &off, &mask)) mySpecial = Flag(target, off, mask);
	for (k = 0; k < nseen; k++)
	{
		void *L = seen[k];
		int sp = -1;
		if (BoolProp(AT(L, UOBJ_CLASS, void *), L"bSpecialLit", &off, &mask)) sp = Flag(L, off, mask);
		Out(L"  light %s: LightType=%s LightBrightness=%s LightRadius=%s bSpecialLit=%d%s%s", O.GetName(L),
		    PropText(L, L"LightType", t), PropText(L, L"LightBrightness", b), PropText(L, L"LightRadius", r), sp,
		    mySpecial >= 0 && sp >= 0 && sp != mySpecial ? L"  <- bSpecialLit differs: this light skips it" : L"",
		    Flag(L, O.offHiddenEd, O.maskHiddenEd) ? L" (bHiddenEd)" : L"");
		(void)s;
	}
	if (!nseen)
		CapLine(L"  no lights in these BSP leaves' light lists: lights placed, moved or re-imported since the last MAP REBUILD "
		        L"are not in the lists (only MAP REBUILD rebuilds them), so LIGHT APPLY gives this spot nothing but zone ambient");
}

static int OpLights(wchar_t **tok, int n)
{
	void *lvl = Level(), *a = NULL, *seen[256];
	int i, k, nseen = 0, zones[64], nz = 0, z, numLeaves, *leaves;
	wchar_t b[256];
	void *model = AT(lvl, LEVEL_MODEL, void *);
	if (n != 1) { CapLine(L"usage: !lights NAME"); return 0; }
	for (i = 0; i < NumActors(lvl) && !a; i++) if (Targets(lvl, tok[0], ActorAt(lvl, i))) a = ActorAt(lvl, i);
	if (!a) { Out(L"Not found: %s", tok[0]); return 0; }
	O.ActorRenderData(a);                                   /* refreshes Leaves after a move */
	Out(L"%s (%s) at %s", O.GetName(a), O.GetName(AT(a, UOBJ_CLASS, void *)), PropText(a, L"Location", b));
	Out(L"  bStatic=%d bHiddenEd=%d bHiddenEdGroup=%d StaticMesh=%s", Flag(a, O.offStatic, O.maskStatic),
	    Flag(a, O.offHiddenEd, O.maskHiddenEd), Flag(a, O.offHiddenGroup, O.maskHiddenGroup), PropText(a, L"StaticMesh", b));
	if (!Flag(a, O.offStatic, O.maskStatic)) CapLine(L"  not bStatic: gets no baked static lighting (lit dynamically)");
	if (Flag(a, O.offHiddenEd, O.maskHiddenEd) || Flag(a, O.offHiddenGroup, O.maskHiddenGroup))
		CapLine(L"  hidden in the editor: LIGHT APPLY skips it (UStaticMesh::Illuminate tests both hidden flags)");
	numLeaves = AT(a, O.offLeaves + 4, int);
	leaves = AT(a, O.offLeaves, int *);
	Out(L"  in %d BSP leaves", numLeaves);
	for (i = 0; i < numLeaves; i++)
	{
		int iLeaf = leaves[i];
		if (iLeaf < 0 || iLeaf >= AT(model, MODEL_LEAVES + 4, int)) continue;
		z = AT(AT(model, MODEL_LEAVES, char *) + iLeaf * FLEAF_SIZE, 0, int);
		for (k = 0; k < nz && zones[k] != z; k++) {}
		if (k == nz && nz < 64) zones[nz++] = z;
		nseen = LeafLights(lvl, iLeaf, seen, nseen, 256);
	}
	for (k = 0; k < nz; k++) ZoneLine(lvl, zones[k]);
	Out(L"  %d light(s) in its leaves' light lists (UStaticMesh::Illuminate then also needs distance < radius and a clear ray):", nseen);
	LightLines(a, seen, nseen);
	return 1;
}

static int OpLightsAt(wchar_t **tok, int n)
{
	void *lvl = Level(), *seen[256];
	void *model = AT(lvl, LEVEL_MODEL, void *);
	OpsPointRegion reg;
	double v[3];
	int k, nseen;
	if (n != 3) { CapLine(L"usage: !lightsat x y z"); return 0; }
	for (k = 0; k < 3; k++) if (!ParseNum(tok[k], &v[k])) { Out(L"Invalid number: %s", tok[k]); return 0; }
	memset(&reg, 0, sizeof(reg));
	O.PointRegion(model, &reg, O.LevelInfo(lvl), (float)v[0], (float)v[1], (float)v[2]);
	Out(L"point (%g,%g,%g): leaf %d, zone %d (%s)", v[0], v[1], v[2], reg.iLeaf, reg.ZoneNumber,
	    reg.Zone ? O.GetName(reg.Zone) : L"none");
	if (reg.iLeaf < 0) CapLine(L"  no leaf: the point is in solid space (inside a wall) or outside the BSP");
	ZoneLine(lvl, reg.ZoneNumber);
	nseen = LeafLights(lvl, reg.iLeaf, seen, 0, 256);
	Out(L"  %d light(s) in this leaf's light list:", nseen);
	LightLines(NULL, seen, nseen);
	return 1;
}

/* ---- !light: static-mesh-only relight ---- */

static int OpLight(wchar_t **tok, int n)
{
	void *lvl = Level();
	int i, k, lit = 0, skipped = 0;
	if (!n) { CapLine(L"usage: !light NAME|PATTERN ...|selected"); return 0; }
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i), *prim, *fn;
		for (k = 0; k < n && !Targets(lvl, tok[k], a); k++) {}
		if (k == n) continue;
		if (O.IsA(a, O.clsMover)) { Out(L"skip %s: movers relight with LIGHT APPLY only", O.GetName(a)); skipped++; continue; }
		if (!Flag(a, O.offStatic, O.maskStatic)) { Out(L"skip %s: not bStatic (dynamic lighting, nothing to bake)", O.GetName(a)); skipped++; continue; }
		if (Flag(a, O.offHiddenEd, O.maskHiddenEd) || Flag(a, O.offHiddenGroup, O.maskHiddenGroup))
		{ Out(L"skip %s: hidden in the editor (the engine refuses to light it; unhide first)", O.GetName(a)); skipped++; continue; }
		prim = ((PtrFn)VSLOT(a, VT_GETPRIMITIVE))(a);
		fn = prim ? VSLOT(prim, VT_ILLUMINATE) : NULL;
		if (!prim || (fn != O.illum[0] && fn != O.illum[1] && fn != O.illum[2] && fn != O.illum[3]))
		{ Out(L"skip %s: its primitive has no known Illuminate", O.GetName(a)); skipped++; continue; }
		if (fn == O.illum[2]) { Out(L"skip %s: BSP model (brushes): use LIGHT APPLY", O.GetName(a)); skipped++; continue; }
		O.ClearRenderData(a);
		O.ActorRenderData(a);                               /* Leaves for the current spot */
		((IlluminateFn)fn)(prim, a, 0);                     /* full relight of this actor, as LIGHT APPLY does */
		O.ClearRenderData(a);
		Out(L"lit %s", O.GetName(a));
		lit++;
	}
	((EdLevelFn)VSLOT(g_ed, VT_ED_REDRAWLEVEL))(g_ed, lvl);
	Out(L"%d actor(s) relit, %d skipped; BSP lightmaps untouched", lit, skipped);
	return lit > 0;
}

static int OpInfo(void)
{
	Out(L"GEditor %p Level %p (+%x) Trans %p (+%x)", g_ed, Level(), O.offLevel, Trans(), O.offTrans);
	Out(L"Actor: Location +%x Rotation +%x XLevel +%x Leaves +%x", O.offLocation, O.offRotation, O.offXLevel, O.offLeaves);
	Out(L"bSelected +%x/%x bStatic +%x/%x bHiddenEd +%x/%x bHiddenEdGroup +%x/%x bLockLocation +%x/%x",
	    O.offSelected, O.maskSelected, O.offStatic, O.maskStatic, O.offHiddenEd, O.maskHiddenEd,
	    O.offHiddenGroup, O.maskHiddenGroup, O.offLock, O.maskLock);
	Out(L"%d actors in the level", NumActors(Level()));
	return 1;
}

/* returns -1 if cmd is not an ops command */
static int OpsBang(const wchar_t *cmd)
{
	static const wchar_t *names[] = { L"!select", L"!deselect", L"!list", L"!move", L"!moveby", L"!light",
	                                  L"!lights", L"!lightsat", L"!opsinfo" };
	wchar_t buf[4096], *tok[64];
	int i, len, n;
	for (i = 0; i < (int)(sizeof(names) / sizeof(names[0])); i++)
	{
		len = lstrlenW(names[i]);
		if (!_wcsnicmp(cmd, names[i], len) && (cmd[len] == 0 || cmd[len] == L' ')) break;
	}
	if (i == (int)(sizeof(names) / sizeof(names[0]))) return -1;
	if (!OpsInit()) return 0;
	if (!Level()) { CapLine(L"ops: no level open"); return 0; }
	lstrcpynW(buf, cmd + len, 4096);
	n = Split(buf, tok, 64);
	switch (i)
	{
	case 0: return OpSelect(tok, n, 1);
	case 1: return OpSelect(tok, n, 0);
	case 2: return OpList(tok, n);
	case 3: return OpMove(tok, n, 0);
	case 4: return OpMove(tok, n, 1);
	case 5: return OpLight(tok, n);
	case 6: return OpLights(tok, n);
	case 7: return OpLightsAt(tok, n);
	default: return OpInfo();
	}
}
