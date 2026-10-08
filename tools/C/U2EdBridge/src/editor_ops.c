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
 *   !meshverts [PAT] FILE        engine geometry/colours/lights dump for U2Bake (see "Baked lighting")
 *   !bakeload FILE               write U2Bake per-vertex colours into the static-mesh instances
 *   !bakeclear PAT ...|all       back to the engine's own vertex light
 *   !bakeinfo [derive on|off]    hook state
 *   !setprop NAME PROP VALUE     one property of one actor (e.g. a ZoneInfo's AmbientBrightness)
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

/* ================================================================================================
 * Baked lighting write-back (U2Bake <-> editor). See LIGHTING.md, "Write-back".
 *
 *   !meshverts [PAT] FILE     dump the engine's own static-mesh geometry (render vertex order), the
 *                             actors' LocalToWorld, current per-instance vertex colours, zones and lights
 *                             to a binary file for bake.py (format "U2MV", below)
 *   !bakeload FILE            write baked per-vertex colours (format "U2BK", made by bake.py) into the
 *                             actors' UStaticMeshInstance colour streams, through the StaticLight hook
 *   !bakeclear PAT ...|all    forget the bake of these actors and let the engine recompute its colours
 *   !bakeinfo                 hook state and baked actors
 *   !setprop NAME PROP VALUE  set one property of ONE actor (ImportText + PostEditChange), e.g.
 *                             !setprop ZoneInfo3 AmbientBrightness 40   (SET is class-wide)
 *
 * Engine facts (Engine.dll, Mar 14 2003; addresses at the Ghidra image base 0x10300000):
 *  - UStaticMesh::Illuminate (0x1043e3b0) stores only visibility bits: UStaticMeshInstance (actor+0x1c8)
 *    Lights[] at +0x28 ({AActor* Light; TArray<BYTE> Bits; UBOOL Applied} = 0x14 each) and a zeroed
 *    FRawColorStream at +0x34 (colours: TArray<FColor> at +0x38, Revision at +0x4c).
 *  - the colours are filled by FUN_10408ef0 (here "StaticLight"; cdecl (UStaticMesh*, Instance*,
 *    FDynamicActor*)): zero, Revision++, for each light whose render data is static: colour +=
 *    FColor(light.Color * SampleIntensity(pos, normal)) where the bit is set, Applied = 1; then the mesh's
 *    own colour stream multiplies (if mesh+0x128) and gives alpha.
 *  - callers: the per-actor draw path FUN_104097b0 (only when a light's Applied flag says its state
 *    changed: first draw after Illuminate, light toggles) and FStaticMeshBatchVertexStream::GetStreamData
 *    (every time a batch is built; batching is UseStaticMeshBatching, False in the game's ini, true in the
 *    editor section [Editor.EditorEngine] but ULevel::PostLoad only batches when !GIsEditor).
 *  - UStaticMeshInstance::Serialize saves the colour stream (LicenseeVer >= 13) and Lights with Applied.
 *    So a saved map renders the saved colours as long as StaticLight is not called again for it.
 * The hook: both call sites are redirected to BakeStaticLight, which calls the original and then adds
 * (or puts) our colours. When it meets an instance it has no record of, it first remembers what the
 * stream holds (= what was saved: engine light + our bake) and keeps the difference to the engine's
 * recomputed light as that actor's bake. So a baked map needs no side file.
 * ================================================================================================ */

#define ENGINE_IMAGE_BASE   0x10300000u
#define RVA_STATICLIGHT     (0x10408ef0u - ENGINE_IMAGE_BASE)
#define RVA_CALL_BATCH      (0x1040233bu - ENGINE_IMAGE_BASE)   /* in FStaticMeshBatchVertexStream::GetStreamData */
#define RVA_CALL_DRAW       (0x10409aa9u - ENGINE_IMAGE_BASE)   /* in FUN_104097b0 (FDynamicActor::Render's mesh path) */
#define RVA_GETSTREAMDATA   (0x10402200u - ENGINE_IMAGE_BASE)   /* exported: proves this is the same Engine.dll */

#define ACTOR_STATICMESH    0x38    /* StaticMesh (GetStreamData, FUN_104097b0) */
#define ACTOR_FLAGS60       0x60    /* bStatic = 0x40 (UStaticMesh::Illuminate) */
#define ACTOR_FLAGS268      0x268   /* 0x10 = mesh casts shadows in the static bake (Illuminate) */
#define ACTOR_INSTANCE      0x1c8   /* UStaticMeshInstance* */
#define DYNACTOR_L2W        0x08    /* FDynamicActor::LocalToWorld, 4x4 floats, row vectors */
#define DYNACTOR_AMBIENT    0xb8    /* FColor ambient (zones + AmbientGlow) */
#define MESH_SECTIONS       0x54    /* TArray<FStaticMeshSection>, 0x14 each, IsStrip at +4 */
#define MESH_VERTS          0x64    /* TArray<FStaticMeshVertex> {FVector Position, Normal} 0x18 each */
#define MESH_INDICES        0xc4    /* FRawIndexBuffer at 0xc0: TArray<WORD> Indices at +4 */
#define INST_LIGHTS         0x28
#define INST_COLORS         0x38
#define INST_REVISION       0x4c
#define INSTLIGHT_SIZE      0x14

typedef void (__cdecl *StaticLightFn)(void *mesh, void *inst, void *dynActor);
typedef float (TC *FloatFn)(void *self);
typedef const wchar_t *(TC *ImportTextFn)(void *prop, const wchar_t *buf, void *data, int flags, void *parent);

typedef struct { void *inst; int rev, n, mode; unsigned *data; } BakeRec;   /* mode 0 add, 1 replace */

static struct {
	int state;                  /* 0 not tried, 1 installed, -1 refused */
	unsigned char *base;
	StaticLightFn orig;
	int derive;                 /* derive a bake from saved colours on first sight */
	BakeRec *rec; int nrec, maxrec;
	int calls, derived;
	void *clsStaticMesh;
	int importSlot;
} BK = { 0, 0, 0, 1 };

static unsigned *BkAlloc(int n) { return (unsigned *)HeapAlloc(GetProcessHeap(), 0, (size_t)(n > 0 ? n : 1) * 4); }
static void BkFree(void *p) { if (p) HeapFree(GetProcessHeap(), 0, p); }

static BakeRec *BkFind(void *inst)
{
	int i;
	for (i = 0; i < BK.nrec; i++) if (BK.rec[i].inst == inst) return &BK.rec[i];
	return NULL;
}

static BakeRec *BkAdd(void *inst)
{
	BakeRec *r = BkFind(inst);
	if (r) return r;
	if (BK.nrec == BK.maxrec)
	{
		int m = BK.maxrec ? BK.maxrec * 2 : 256;
		BakeRec *p = BK.rec ? (BakeRec *)HeapReAlloc(GetProcessHeap(), 0, BK.rec, m * sizeof(BakeRec))
		                    : (BakeRec *)HeapAlloc(GetProcessHeap(), 0, m * sizeof(BakeRec));
		if (!p) return NULL;
		BK.rec = p; BK.maxrec = m;
	}
	r = &BK.rec[BK.nrec++];
	memset(r, 0, sizeof(*r));
	r->inst = inst;
	return r;
}

static void BkDrop(BakeRec *r)
{
	BkFree(r->data);
	*r = BK.rec[--BK.nrec];
}

/* saturating per-channel add / subtract of BGR, alpha kept from a */
static unsigned SatAdd(unsigned a, unsigned b)
{
	unsigned r = a & 0xff000000u;
	int k;
	for (k = 0; k < 24; k += 8)
	{
		unsigned s = ((a >> k) & 0xff) + ((b >> k) & 0xff);
		r |= (s > 255 ? 255 : s) << k;
	}
	return r;
}
static unsigned SatSub(unsigned a, unsigned b)
{
	unsigned r = 0;
	int k;
	for (k = 0; k < 24; k += 8)
	{
		int s = (int)((a >> k) & 0xff) - (int)((b >> k) & 0xff);
		r |= (unsigned)(s < 0 ? 0 : s) << k;
	}
	return r;
}

/* the replacement for both calls of StaticLight */
static void __cdecl BakeStaticLight(void *mesh, void *inst, void *dynActor)
{
	BakeRec *r = BkFind(inst);
	int n = AT(inst, INST_COLORS + 4, int), i;
	unsigned *col;
	BK.calls++;
	if (BK.derive && (!r || r->rev != AT(inst, INST_REVISION, int) || r->n != n))
	{
		/* first sight (or the engine relit it since): the stream holds what was saved or set last */
		unsigned *saved = BkAlloc(n);
		int any = 0;
		if (saved) memcpy(saved, AT(inst, INST_COLORS, unsigned *), (size_t)n * 4);
		BK.orig(mesh, inst, dynActor);
		col = AT(inst, INST_COLORS, unsigned *);
		if (saved)
		{
			for (i = 0; i < n; i++) { saved[i] = SatSub(saved[i], col[i]); any |= saved[i] != 0; }
			if (any)
			{
				if (!r) r = BkAdd(inst);
				if (r) { BkFree(r->data); r->data = saved; r->n = n; r->mode = 0; saved = NULL; BK.derived++; }
			}
			else if (r) { BkDrop(r); r = NULL; }
			BkFree(saved);
		}
		if (!r) return;
	}
	else
	{
		BK.orig(mesh, inst, dynActor);
		if (!r) return;
	}
	col = AT(inst, INST_COLORS, unsigned *);
	if (r->data && r->n == n)
		for (i = 0; i < n; i++)
			col[i] = r->mode ? (col[i] & 0xff000000u) | (r->data[i] & 0x00ffffffu) : SatAdd(col[i], r->data[i]);
	r->rev = AT(inst, INST_REVISION, int);   /* StaticLight bumped it: the renderer re-uploads the stream */
}

static int PatchCall(unsigned rva, void *to)
{
	unsigned char *at = BK.base + rva;
	DWORD old;
	int rel = (int)((unsigned char *)to - (at + 5));
	if (!VirtualProtect(at, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
	memcpy(at + 1, &rel, 4);
	VirtualProtect(at, 5, old, &old);
	FlushInstructionCache(GetCurrentProcess(), at, 5);
	return 1;
}

static int CallTargets(unsigned rva, unsigned target)
{
	unsigned char *at = BK.base + rva;
	int rel;
	if (at[0] != 0xE8) return 0;
	memcpy(&rel, at + 1, 4);
	return at + 5 + rel == BK.base + target;
}

/* checks everything before touching code; runs on the main thread (no concurrent renderer) */
static int BakeHookInstall(void)
{
	HMODULE eng = GetModuleHandleW(L"Engine.dll");
	static const unsigned char prologue[] = { 0x55, 0x8B, 0xEC, 0x6A, 0xFF, 0x68 };
	if (BK.state) return BK.state > 0;
	BK.state = -1;
	if (!eng) { CapLine(L"bake: Engine.dll not found"); return 0; }
	BK.base = (unsigned char *)eng;
	if ((unsigned char *)GetProcAddress(eng, "?GetStreamData@FStaticMeshBatchVertexStream@@UAEXPAX@Z") != BK.base + RVA_GETSTREAMDATA)
	{ CapLine(L"bake: Engine.dll is not the build the hook was written for (GetStreamData moved); hook refused"); return 0; }
	if (memcmp(BK.base + RVA_STATICLIGHT, prologue, sizeof(prologue)))
	{ CapLine(L"bake: StaticLight prologue differs; hook refused"); return 0; }
	if (!CallTargets(RVA_CALL_BATCH, RVA_STATICLIGHT) || !CallTargets(RVA_CALL_DRAW, RVA_STATICLIGHT))
	{
		if (CallTargets(RVA_CALL_BATCH, (unsigned)((unsigned char *)BakeStaticLight - BK.base)))
			CapLine(L"bake: call sites already point at another BakeStaticLight (second ops DLL?); hook refused");
		else
			CapLine(L"bake: StaticLight call sites differ; hook refused");
		return 0;
	}
	BK.orig = (StaticLightFn)(BK.base + RVA_STATICLIGHT);
	if (!PatchCall(RVA_CALL_BATCH, (void *)BakeStaticLight) || !PatchCall(RVA_CALL_DRAW, (void *)BakeStaticLight))
	{ CapLine(L"bake: VirtualProtect failed"); return 0; }
	BLog("bake: StaticLight hook installed (Engine.dll at %p)", (void *)BK.base);
	BK.state = 1;
	return 1;
}

/* ---- small binary writer/reader ---- */

typedef struct { HANDLE f; char buf[65536]; int len; int err; } BW;

static void BwFlush(BW *w)
{
	DWORD put;
	if (w->len && !w->err && (!WriteFile(w->f, w->buf, w->len, &put, NULL) || put != (DWORD)w->len)) w->err = 1;
	w->len = 0;
}
static void BwPut(BW *w, const void *p, int n)
{
	const char *s = (const char *)p;
	while (n > 0)
	{
		int k = (int)sizeof(w->buf) - w->len;
		if (k > n) k = n;
		memcpy(w->buf + w->len, s, k);
		w->len += k; s += k; n -= k;
		if (w->len == (int)sizeof(w->buf)) BwFlush(w);
	}
}
static void BwInt(BW *w, int v) { BwPut(w, &v, 4); }
static void BwStr(BW *w, const wchar_t *s) { int n = s ? lstrlenW(s) : 0; BwInt(w, n); BwPut(w, s, n * 2); }

typedef struct { const unsigned char *p, *end; int err; } BR;
static int BrInt(BR *r) { int v = 0; if (r->p + 4 > r->end) { r->err = 1; return 0; } memcpy(&v, r->p, 4); r->p += 4; return v; }
static const void *BrTake(BR *r, int n) { const void *q = r->p; if (n < 0 || r->p + n > r->end) { r->err = 1; return NULL; } r->p += n; return q; }
static int BrStr(BR *r, wchar_t *out, int max)
{
	int n = BrInt(r);
	const wchar_t *s = (const wchar_t *)BrTake(r, n * 2);
	if (!s || n >= max) { r->err = 1; out[0] = 0; return 0; }
	memcpy(out, s, n * 2); out[n] = 0;
	return 1;
}

static unsigned char *ReadWholeFile(const wchar_t *path, int *size)
{
	HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
	DWORD sz, got;
	unsigned char *p;
	if (f == INVALID_HANDLE_VALUE) return NULL;
	sz = GetFileSize(f, NULL);
	p = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, sz ? sz : 1);
	if (p && (!ReadFile(f, p, sz, &got, NULL) || got != sz)) { HeapFree(GetProcessHeap(), 0, p); p = NULL; }
	CloseHandle(f);
	*size = (int)sz;
	return p;
}

/* "a b c" -> rejoin tokens [from, n) with single spaces (file paths with spaces) */
static void JoinRest(wchar_t **tok, int from, int n, wchar_t *out, int max)
{
	int k;
	out[0] = 0;
	for (k = from; k < n; k++)
	{
		if (k > from) lstrcatW(out, L" ");
		if (lstrlenW(out) + lstrlenW(tok[k]) + 2 >= max) break;
		lstrcatW(out, tok[k]);
	}
	if (out[0] == L'"') { int l = lstrlenW(out); memmove(out, out + 1, l * 2); if (l > 1 && out[l - 2] == L'"') out[l - 2] = 0; }
}

static void *ActorMesh(void *a)
{
	void *m = AT(a, ACTOR_STATICMESH, void *);
	return m && BK.clsStaticMesh && O.IsA(m, BK.clsStaticMesh) ? m : NULL;
}

/* the engine's own validity test (GetStreamData / FUN_104097b0): colours and every light's bits sized */
static void *ValidInstance(void *a, void *mesh)
{
	void *inst = AT(a, ACTOR_INSTANCE, void *);
	int nv = AT(mesh, MESH_VERTS + 4, int), nl, i;
	if (!inst || AT(inst, INST_COLORS + 4, int) != nv) return NULL;
	nl = AT(inst, INST_LIGHTS + 4, int);
	for (i = 0; i < nl; i++)
		if (AT(AT(inst, INST_LIGHTS, char *) + i * INSTLIGHT_SIZE, 8, int) != (nv + 7) / 8) return NULL;
	return inst;
}

static int BakeInit(void)
{
	StaticClassFn sc;
	HMODULE eng = GetModuleHandleW(L"Engine.dll");
	int off;
	if (BK.clsStaticMesh) return 1;
	sc = eng ? (StaticClassFn)GetProcAddress(eng, "?StaticClass@UStaticMesh@@SAPAVUClass@@XZ") : NULL;
	if (!sc) { CapLine(L"bake: UStaticMesh::StaticClass not exported"); return 0; }
	BK.clsStaticMesh = sc();
	off = PropOffset(O.clsActor, L"StaticMesh");
	if (off != ACTOR_STATICMESH) { Out(L"bake: Actor.StaticMesh at +%x, the decompile says +%x; refused", off, ACTOR_STATICMESH); BK.clsStaticMesh = NULL; return 0; }
	if (O.offStatic != ACTOR_FLAGS60 || O.maskStatic != 0x40)
	{ Out(L"bake: bStatic at +%x/%x, the decompile says +60/40; refused", O.offStatic, O.maskStatic); BK.clsStaticMesh = NULL; return 0; }
	return 1;
}

/* ---- !meshverts ---- */
/*
 * U2MV v1, little endian. str = int32 count + UTF-16 chars.
 *   "U2MV" int version=1  float LevelBrightness
 *   int nmeshes, per mesh:  str fullname; int nverts; float[6*nverts] (mesh-space position, normal, in the
 *                           engine's vertex order = colour stream order); int nindices; uint16[nindices]
 *                           (triangle list; 0 indices if a section is a strip); pad to 4
 *   int nactors, per actor: str name; str class; int mesh; float[16] LocalToWorld (world = (x,y,z,1) * M,
 *                           rows); int flags (1 bStatic, 2 valid instance, 4 hidden in editor,
 *                           8 casts static shadows (0x268&0x10), 16 bSpecialLit); str zone;
 *                           uint32 ambient (FColor BGRA); int ncolors; uint32[ncolors] current colours
 *   int nlights, per light: str name; str class; float[3] location; int[3] rotation (pitch yaw roll);
 *                           uint8 type, effect, brightness, hue, saturation, radius, pad, pad;
 *                           float worldRadius; int flags (1 bStatic, 16 bSpecialLit); str zone
 */
static void ZoneName(void *a, wchar_t *out)
{
	int off = PropOffset(AT(a, UOBJ_CLASS, void *), L"Region");
	void *z = off >= 0 ? AT(a, off, void *) : NULL;
	lstrcpynW(out, z ? O.GetName(z) : L"", 128);
}

static int OpMeshVerts(wchar_t **tok, int n)
{
	void *lvl = Level(), **meshes = NULL;
	wchar_t path[1024], zone[128], buf[256];
	const wchar_t *pat = L"*";
	BW *w;
	int i, k, nmesh = 0, nact = 0, nlight = 0, offSpecial = -1, offLT, offLE, offLB, offLH, offLS, offLR;
	unsigned maskSpecial = 0;
	float lb = 1.0f;
	if (!BakeInit()) return 0;
	if (n < 1) { CapLine(L"usage: !meshverts [PAT] FILE"); return 0; }
	if (n >= 2) { pat = tok[0]; JoinRest(tok, 1, n, path, 1024); } else JoinRest(tok, 0, n, path, 1024);
	BoolProp(O.clsActor, L"bSpecialLit", &offSpecial, &maskSpecial);
	offLT = PropOffset(O.clsActor, L"LightType"); offLE = PropOffset(O.clsActor, L"LightEffect");
	offLB = PropOffset(O.clsActor, L"LightBrightness"); offLH = PropOffset(O.clsActor, L"LightHue");
	offLS = PropOffset(O.clsActor, L"LightSaturation"); offLR = PropOffset(O.clsActor, L"LightRadius");
	if (offLT != 0x28 || offLE != 0x29 || offLB != 0x2a || offLH != 0x2b || offLS != 0x2c || offLR != 0x2d)
	{ Out(L"bake: light byte properties at %x %x %x %x %x %x, the decompile says 28..2d; refused", offLT, offLE, offLB, offLH, offLS, offLR); return 0; }
	lb = (float)wcstod(PropText(O.LevelInfo(lvl), L"Brightness", buf), NULL);
	if (!(lb > 0.0f)) { Out(L"note: LevelInfo.Brightness reads '%s'; 1.0 written", buf); lb = 1.0f; }
	meshes = (void **)HeapAlloc(GetProcessHeap(), 0, sizeof(void *) * (NumActors(lvl) + 1));
	w = (BW *)HeapAlloc(GetProcessHeap(), 0, sizeof(BW));
	if (!meshes || !w) { CapLine(L"out of memory"); BkFree(meshes); BkFree(w); return 0; }
	w->len = 0; w->err = 0;
	w->f = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
	if (w->f == INVALID_HANDLE_VALUE) { Out(L"Can't write %s", path); BkFree(meshes); BkFree(w); return 0; }
	/* distinct meshes of the matching actors */
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i), *m;
		if (!Targets(lvl, pat, a) || !(m = ActorMesh(a))) continue;
		for (k = 0; k < nmesh && meshes[k] != m; k++) {}
		if (k == nmesh) meshes[nmesh++] = m;
	}
	BwPut(w, "U2MV", 4); BwInt(w, 1); BwPut(w, &lb, 4);
	BwInt(w, nmesh);
	for (k = 0; k < nmesh; k++)
	{
		void *m = meshes[k];
		int nv = AT(m, MESH_VERTS + 4, int), ni = AT(m, MESH_INDICES + 4, int), ns = AT(m, MESH_SECTIONS + 4, int), s, strip = 0;
		wchar_t full[512];
		for (s = 0; s < ns; s++) if (AT(AT(m, MESH_SECTIONS, char *) + s * 0x14, 4, int)) strip = 1;
		if (strip) ni = 0;
		wsprintfW(full, L"%s.%s", O.GetName(AT(m, 0x18, void *) ? AT(m, 0x18, void *) : m), O.GetName(m));  /* Outer at +0x18 */
		BwStr(w, full);
		BwInt(w, nv);
		BwPut(w, AT(m, MESH_VERTS, void *), nv * 0x18);
		BwInt(w, ni);
		BwPut(w, AT(m, MESH_INDICES, void *), ni * 2);
		if (ni & 1) BwPut(w, "\0\0", 2);
		if (strip) Out(L"note: %s has strip sections; its triangles are not dumped (occluder missing)", full);
	}
	for (i = 0; i < NumActors(lvl); i++) { void *a = ActorAt(lvl, i); if (Targets(lvl, pat, a) && ActorMesh(a)) nact++; }
	BwInt(w, nact);
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i), *m, *rd, *inst;
		int flags = 0, nc = 0;
		unsigned amb;
		if (!Targets(lvl, pat, a) || !(m = ActorMesh(a))) continue;
		for (k = 0; k < nmesh && meshes[k] != m; k++) {}
		rd = O.ActorRenderData(a);
		if (!rd) { Out(L"note: %s has no render data (skipped in the dump: actor count is now wrong)", O.GetName(a)); w->err = 1; break; }
		inst = ValidInstance(a, m);
		if (Flag(a, O.offStatic, O.maskStatic)) flags |= 1;
		if (inst) flags |= 2;
		if (Flag(a, O.offHiddenEd, O.maskHiddenEd) || Flag(a, O.offHiddenGroup, O.maskHiddenGroup)) flags |= 4;
		if (AT(a, ACTOR_FLAGS268, unsigned) & 0x10) flags |= 8;
		if (Flag(a, offSpecial, maskSpecial)) flags |= 16;
		BwStr(w, O.GetName(a));
		BwStr(w, O.GetName(AT(a, UOBJ_CLASS, void *)));
		BwInt(w, k);
		BwPut(w, (char *)rd + DYNACTOR_L2W, 64);
		BwInt(w, flags);
		ZoneName(a, zone); BwStr(w, zone);
		amb = AT(rd, DYNACTOR_AMBIENT, unsigned); BwInt(w, (int)amb);
		if (inst) nc = AT(inst, INST_COLORS + 4, int);
		BwInt(w, nc);
		if (nc) BwPut(w, AT(inst, INST_COLORS, void *), nc * 4);
	}
	for (i = 0; i < NumActors(lvl); i++) { void *a = ActorAt(lvl, i); if (a && AT(a, 0x28, unsigned char)) nlight++; }
	BwInt(w, nlight);
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i);
		float wr;
		int flags = 0;
		if (!a || !AT(a, 0x28, unsigned char)) continue;
		BwStr(w, O.GetName(a));
		BwStr(w, O.GetName(AT(a, UOBJ_CLASS, void *)));
		BwPut(w, (char *)a + O.offLocation, 12);
		BwPut(w, (char *)a + O.offRotation, 12);
		BwPut(w, (char *)a + 0x28, 6);
		BwPut(w, "\0\0", 2);
		wr = ((FloatFn)VSLOT(a, 0x7c))(a);               /* WorldLightRadius (Illuminate calls slot 0x7c) */
		BwPut(w, &wr, 4);
		if (Flag(a, O.offStatic, O.maskStatic)) flags |= 1;
		if (Flag(a, offSpecial, maskSpecial)) flags |= 16;
		BwInt(w, flags);
		ZoneName(a, zone); BwStr(w, zone);
	}
	BwFlush(w);
	k = w->err;
	CloseHandle(w->f);
	BkFree(w); BkFree(meshes);
	if (k) { Out(L"write error on %s", path); return 0; }
	Out(L"meshverts: %d meshes, %d actors, %d lights -> %s", nmesh, nact, nlight, path);
	return 1;
}

/* ---- !bakeload ---- */
/*
 * U2BK v1: "U2BK" int version=1, int mode (0 = add to the engine's own light, 1 = replace it),
 *          int nactors, per actor: str name; int nverts; uint32[nverts] FColor (BGRA in memory,
 *          0xAARRGGBB as a little-endian int; alpha ignored) in the engine's vertex order (!meshverts).
 */
static void *FindActorNamed(void *lvl, const wchar_t *name)
{
	int i;
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i);
		if (a && !_wcsicmp(O.GetName(a), name)) return a;
	}
	return NULL;
}

static int OpBakeLoad(wchar_t **tok, int n)
{
	void *lvl = Level();
	wchar_t path[1024], name[256];
	unsigned char *file;
	int size, mode, na, i, ok = 0, bad = 0;
	BR r;
	if (!BakeInit()) return 0;
	if (n < 1) { CapLine(L"usage: !bakeload FILE"); return 0; }
	JoinRest(tok, 0, n, path, 1024);
	if (!BakeHookInstall()) return 0;
	file = ReadWholeFile(path, &size);
	if (!file) { Out(L"Can't read %s", path); return 0; }
	r.p = file; r.end = file + size; r.err = 0;
	if (size < 16 || memcmp(file, "U2BK", 4)) { Out(L"%s is not a U2BK file", path); BkFree(file); return 0; }
	r.p += 4;
	if (BrInt(&r) != 1) { CapLine(L"bake: unknown U2BK version"); BkFree(file); return 0; }
	mode = BrInt(&r);
	na = BrInt(&r);
	Begin(L"Bridge Bake");
	for (i = 0; i < na && !r.err; i++)
	{
		int nv;
		const unsigned *cols;
		void *a, *m, *inst;
		BakeRec *rec;
		BrStr(&r, name, 256);
		nv = BrInt(&r);
		cols = (const unsigned *)BrTake(&r, nv * 4);
		if (r.err) break;
		a = FindActorNamed(lvl, name);
		if (!a) { if (bad++ < 50) Out(L"skip %s: no such actor", name); continue; }
		if (!(m = ActorMesh(a))) { if (bad++ < 50) Out(L"skip %s: no static mesh", name); continue; }
		if (AT(m, MESH_VERTS + 4, int) != nv)
		{ if (bad++ < 50) Out(L"skip %s: %d colours for %d engine vertices (re-dump with !meshverts)", name, nv, AT(m, MESH_VERTS + 4, int)); continue; }
		if (!(inst = ValidInstance(a, m)))
		{ if (bad++ < 50) Out(L"skip %s: no valid static lighting instance (bStatic + !light or LIGHT APPLY first)", name); continue; }
		rec = BkAdd(inst);
		if (!rec) { CapLine(L"out of memory"); break; }
		BkFree(rec->data);
		rec->data = BkAlloc(nv);
		if (!rec->data) { BkDrop(rec); CapLine(L"out of memory"); break; }
		memcpy(rec->data, cols, (size_t)nv * 4);
		rec->n = nv; rec->mode = mode ? 1 : 0;
		rec->rev = AT(inst, INST_REVISION, int);          /* known: not a first sight */
		((VoidFn)VSLOT(inst, VT_MODIFY))(inst);           /* undo record + package dirty */
		BakeStaticLight(m, inst, O.ActorRenderData(a));   /* engine light again, then ours on top */
		ok++;
	}
	End();
	BkFree(file);
	if (r.err) CapLine(L"bake: file truncated or corrupt (stopped there)");
	((EdLevelFn)VSLOT(g_ed, VT_ED_REDRAWLEVEL))(g_ed, lvl);
	Out(L"baked %d actor(s) (%s), %d skipped; save the map to keep it", ok, mode ? L"replace" : L"add", bad);
	return ok > 0;
}

static int OpBakeClear(wchar_t **tok, int n)
{
	void *lvl = Level();
	int i, k, count = 0, all = n == 1 && !_wcsicmp(tok[0], L"all");
	if (!n) { CapLine(L"usage: !bakeclear PAT ...|all"); return 0; }
	if (!BakeInit() || BK.state <= 0) { CapLine(L"bake: hook not installed, nothing baked this session"); return 0; }
	for (i = 0; i < NumActors(lvl); i++)
	{
		void *a = ActorAt(lvl, i), *m, *inst;
		BakeRec *rec;
		if (!a || !(m = ActorMesh(a))) continue;
		if (!all) { for (k = 0; k < n && !Targets(lvl, tok[k], a); k++) {} if (k == n) continue; }
		if (!(inst = ValidInstance(a, m))) continue;
		if ((rec = BkFind(inst))) BkDrop(rec);
		BK.orig(m, inst, O.ActorRenderData(a));               /* engine colours only */
		rec = BkAdd(inst);                                     /* remember it as "no bake" so the hook */
		if (rec) { rec->n = AT(inst, INST_COLORS + 4, int); rec->rev = AT(inst, INST_REVISION, int); }  /* won't re-derive */
		count++;
	}
	((EdLevelFn)VSLOT(g_ed, VT_ED_REDRAWLEVEL))(g_ed, lvl);
	Out(L"%d actor(s) back to the engine's own vertex light", count);
	return 1;
}

static int OpBakeInfo(wchar_t **tok, int n)
{
	int i, baked = 0;
	if (n == 2 && !_wcsicmp(tok[0], L"derive")) { BK.derive = !_wcsicmp(tok[1], L"on"); Out(L"derive %s", BK.derive ? L"on" : L"off"); return 1; }
	Out(L"hook: %s; StaticLight calls %d, bakes derived from saved colours %d, derive %s",
	    BK.state > 0 ? L"installed" : BK.state < 0 ? L"refused" : L"not installed", BK.calls, BK.derived, BK.derive ? L"on" : L"off");
	for (i = 0; i < BK.nrec; i++) if (BK.rec[i].data) baked++;
	Out(L"%d instance(s) carry a bake", baked);
	return 1;
}

/* ---- !setprop: one property of one actor ---- */
static int OpSetProp(wchar_t **tok, int n)
{
	void *lvl = Level(), *a, *p;
	wchar_t val[1024], b[256];
	if (n < 3) { CapLine(L"usage: !setprop ACTORNAME PROPERTY VALUE"); return 0; }
	if (!BK.importSlot)
	{
		/* find ImportText's vtable slot: compare UByteProperty's vtable with its exported ImportText */
		HMODULE core = GetModuleHandleW(L"Core.dll");
		void *fn = core ? (void *)GetProcAddress(core, "?ImportText@UByteProperty@@UBEPBGPBGPAEHPAVUStruct@@@Z") : NULL;
		void *bp = FindProp(O.clsActor, L"LightType"), **vt;
		int s;
		if (!fn || !bp) { CapLine(L"setprop: ImportText not found"); return 0; }
		vt = *(void ***)bp;
		for (s = 0; s < 128 && vt[s] != fn; s++) {}
		if (s == 128) { CapLine(L"setprop: ImportText slot not found"); return 0; }
		BK.importSlot = s * 4;
		BLog("setprop: ImportText at vtable +0x%x", BK.importSlot);
	}
	a = FindActorNamed(lvl, tok[0]);
	if (!a) { Out(L"Not found: %s", tok[0]); return 0; }
	p = FindProp(AT(a, UOBJ_CLASS, void *), tok[1]);
	if (!p) { Out(L"%s has no property %s", O.GetName(a), tok[1]); return 0; }
	JoinRest(tok, 2, n, val, 1024);
	Begin(L"Bridge SetProp");
	((VoidFn)VSLOT(a, VT_MODIFY))(a);
	if (!((ImportTextFn)VSLOT(p, BK.importSlot))(p, val, (char *)a + AT(p, UPROP_OFFSET, int), 0, NULL))
	{ End(); Out(L"Bad value for %s: %s", tok[1], val); return 0; }
	((VoidFn)VSLOT(a, VT_POSTEDITCHANGE))(a);   /* ZoneInfo: recomputes AmbientVector, clears all render data */
	End();
	Redraw(lvl);
	Out(L"%s.%s = %s", O.GetName(a), tok[1], PropText(a, tok[1], b));
	return 1;
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
	                                  L"!lights", L"!lightsat", L"!opsinfo", L"!meshverts", L"!bakeload",
	                                  L"!bakeclear", L"!bakeinfo", L"!setprop" };
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
	case 9: return OpMeshVerts(tok, n);
	case 10: return OpBakeLoad(tok, n);
	case 11: return OpBakeClear(tok, n);
	case 12: return OpBakeInfo(tok, n);
	case 13: return OpSetProp(tok, n);
	default: return OpInfo();
	}
}
