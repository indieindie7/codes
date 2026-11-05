// Core Keeper Companion: a clumsy, good-willed AI buddy that looks like a random player,
// follows you, and calls out (L4D style) only what it can see itself.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using Unity.Mathematics;
using UnityEngine;
using PugTilemap;

namespace CKCompanion
{
    [BepInPlugin("local.corekeeper.companion", "Core Keeper Companion", "0.1.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static ManualLogSource Log;
        public static ConfigEntry<bool> Enabled, HudLine, FloatingText;
        public static ConfigEntry<KeyCode> ToggleKey, TestKey;
        public static ConfigEntry<float> FollowMin, FollowMax, TeleportDist, Speed, Sight, LowHp, CooldownScale, DisplaySecs, IdleAfter, Clumsiness, SpawnOffset, WanderRadius;
        public static ConfigEntry<int> AutoLoadWorld, AutoLoadChar, Seed;
        public static ConfigEntry<string> BuddyName;

        void Awake()
        {
            Log = Logger;
            Enabled = Config.Bind("General", "Enabled", true, "Companion on/off (also ToggleKey)");
            ToggleKey = Config.Bind("General", "ToggleKey", KeyCode.F7, "Show/hide the companion");
            TestKey = Config.Bind("General", "TestCalloutsKey", KeyCode.F8, "Fire each callout type in turn (debug)");
            BuddyName = Config.Bind("General", "Name", "", "Companion name (empty = random)");
            Seed = Config.Bind("General", "LookSeed", 0, "Random look seed (0 = new look every session)");
            FollowMin = Config.Bind("Follow", "FollowDistanceMin", 1.5f, "Tiles");
            FollowMax = Config.Bind("Follow", "FollowDistanceMax", 3f, "Tiles");
            TeleportDist = Config.Bind("Follow", "TeleportDistance", 20f, "Teleport beside the player when farther than this (tiles)");
            Speed = Config.Bind("Follow", "Speed", 5f, "Tiles per second");
            Clumsiness = Config.Bind("Follow", "Clumsiness", 1f, "0 = never trips, 1 = default, 3 = disaster");
            Sight = Config.Bind("Senses", "SightRadius", 9f, "Tiles; walls block sight");
            LowHp = Config.Bind("Senses", "LowHealthFraction", 0.3f, "");
            HudLine = Config.Bind("Callouts", "HudLine", true, "");
            FloatingText = Config.Bind("Callouts", "FloatingText", true, "");
            CooldownScale = Config.Bind("Callouts", "CooldownScale", 1f, "Multiply all cooldowns");
            DisplaySecs = Config.Bind("Callouts", "DisplaySeconds", 4f, "");
            IdleAfter = Config.Bind("Callouts", "IdleChatterAfterSeconds", 90f, "");
            AutoLoadWorld = Config.Bind("Debug", "AutoLoadWorld", -1, "Test only: from the title screen load this world slot (-1 = off)");
            AutoLoadChar = Config.Bind("Debug", "AutoLoadCharacter", 0, "Test only: character slot for AutoLoadWorld");
            SpawnOffset = Config.Bind("Debug", "SpawnOffset", 0f, "Test only: spawn this many tiles away (0 = beside player)");
            WanderRadius = Config.Bind("Debug", "WanderRadius", 0f, "Test only: walk to random walkable points this far around the player instead of following (0 = off)");
            var go = new GameObject("CKCompanionHost");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<Buddy>();
            go.AddComponent<AutoPlayer>();
            new HarmonyLib.Harmony("local.corekeeper.companion.auto").PatchAll(typeof(AutoInputPatches));
            Log.LogInfo("Core Keeper Companion loaded");
        }
    }

    public class Buddy : MonoBehaviour
    {
        // animator hashes (PlayerController.UpdateAnimatorSpeedAndOrientation)
        const int H_MOVE_X = -1801483167, H_MOVE_Y = -476529417, H_FACE_X = 898384463, H_FACE_Y = 1116435161, H_SPEED = -1985230220;

        PlayerController player;
        GameObject body; PlayerController bodyPc; Animator anim;
        Vector3 wpos;            // world space (tiles); render = wpos - RenderOrigo
        bool moving, visible = true;
        string myName;
        System.Random rng;

        static readonly Dictionary<string, float> baseCd = new Dictionary<string, float> {
            {"enemy", 10f}, {"danger", 25f}, {"boss", 60f}, {"lowhealth", 25f}, {"ore", 40f}, {"chest", 60f},
            {"idle", 120f}, {"trip", 50f}, {"stuck", 30f}, {"hello", 9999f}, {"teleport", 30f} };
        static readonly Dictionary<string, string[]> lines = new Dictionary<string, string[]> {
            {"hello", new[]{"Hi! I'm {0}. I'll help! Probably.", "{0} reporting for duty! Where's the duty?", "Hey buddy, it's me, {0}. I brought... enthusiasm."}},
            {"enemy", new[]{"{0} {1}! Uh, I'll be right behind you.", "Watch out, {0} {1}!", "{0}, {1}! It looks grumpy.", "Is that {0} friendly? It's {1}. No? Okay!"}},
            {"danger", new[]{"That's a LOT of them!", "Too many! Too many!", "I count {0}... and I can only count to {0}!"}},
            {"boss", new[]{"Big one {1}! {0}! Big big big!", "Uh oh. {0}, {1}. Hold my... nothing.", "That {0} is the size of a house. A mean house."}},
            {"lowhealth", new[]{"You're hurt! Eat something!", "You look terrible. Supportively terrible.", "Health's low, friend! Back off a bit?"}},
            {"ore", new[]{"Shiny! {0} {1}.", "{0} {1}! I'd mine it but I'd miss.", "Ooh, {0} in the wall {1}."}},
            {"chest", new[]{"A chest {1}! Yours, I mean. Definitely yours.", "Treasure {1}! I touched nothing. Promise.", "{0} {1}. Open it open it open it."}},
            {"idle", new[]{"I'm having a great time.", "Do you think the Core likes me?", "I tried to pet a slime once. Once.", "We make a good team. You do the work, I do the cheering.", "Sorry I stepped on your foot earlier. And now."}},
            {"trip", new[]{"Whoa- I'm okay!", "Oof. The floor attacked me.", "I meant to do that.", "Who put that ground there?"}},
            {"stuck", new[]{"Hang on, there's a wall in my way. Rude.", "I can't get there! Wait up!", "Is this a door? It's not a door."}},
            {"teleport", new[]{"Wait for me!", "Found you! I took a shortcut. Don't ask.", "Huff... huff... here!"}},
        };
        readonly Dictionary<string, float> lastSaid = new Dictionary<string, float>();
        readonly Dictionary<string, int> variant = new Dictionary<string, int>();
        string floatText = ""; float floatUntil; int floatPrio = -1;
        readonly List<string> hud = new List<string>();
        float lastAnyCallout, tSense, tScan, tPos, tripUntil, tStuckSince = -1f, tTitle = -1f;
        EntityMonoBehaviour[] ents = new EntityMonoBehaviour[0];
        readonly Dictionary<int, float> seenThing = new Dictionary<int, float>();
        readonly Dictionary<long, float> seenOre = new Dictionary<long, float>();
        bool autoLoaded; string lastScene = "";

        void Start() { rng = new System.Random(Plugin.Seed.Value != 0 ? Plugin.Seed.Value : Environment.TickCount); }

        void Update()
        {
            try { Tick(); } catch (Exception e) { Plugin.Log.LogError("tick: " + e); enabled = false; }
        }

        void Tick()
        {
            if (Input.GetKeyDown(Plugin.ToggleKey.Value)) { visible = !visible; if (body) body.SetActive(visible); Plugin.Log.LogInfo("toggle visible=" + visible); }
            if (Manager.main == null) return;
            string scene = Manager.load != null ? Manager.load.GetNameOfCurrentScene() : "";
            if (scene != lastScene) { Plugin.Log.LogInfo("scene: " + scene); lastScene = scene; }
            player = Manager.main.player;
            AutoLoad(scene);
            if (player == null || !player.gameObject.activeInHierarchy || !Plugin.Enabled.Value)
            {
                if (body && player == null) { Destroy(body); body = null; Plugin.Log.LogInfo("player gone, companion removed"); }
                return;
            }
            if (body == null) { if (Manager.multiMap.GetTileLayerLookup().AllTiles.Count() == 0) return; Spawn(); if (body == null) return; }
            if (!visible) return;
            if (Input.GetKeyDown(Plugin.TestKey.Value)) TestCallout();
            Follow();
            Place();
            if (Time.time > tSense) { tSense = Time.time + 0.5f; Sense(); }
            if (Time.time > tPos) { tPos = Time.time + 5f; Plugin.Log.LogInfo($"[pos] companion={Fmt(wpos)} player={Fmt(player.WorldPosition)} dist={HDist(wpos, player.WorldPosition).ToString("F1", System.Globalization.CultureInfo.InvariantCulture)} moving={moving} {TileDiag()}"); }
        }

        void AutoLoad(string scene)
        {
            if (autoLoaded || Plugin.AutoLoadWorld.Value < 0 || player != null) return;
            bool title = scene.IndexOf("title", StringComparison.OrdinalIgnoreCase) >= 0 || scene.IndexOf("menu", StringComparison.OrdinalIgnoreCase) >= 0;
            if (!title || Manager.load.IsSceneTransitionOrLoading()) { tTitle = -1f; return; }
            if (tTitle < 0) tTitle = Time.unscaledTime;
            if (Time.unscaledTime - tTitle < 6f) return;
            autoLoaded = true;
            Plugin.Log.LogInfo($"debug autoload: world {Plugin.AutoLoadWorld.Value} character {Plugin.AutoLoadChar.Value}");
            SaveSlotPlayOption.StartGameFromActivity(Plugin.AutoLoadWorld.Value, Plugin.AutoLoadChar.Value);
        }

        // ---------- look: clone of the player rig with a random customization ----------
        void Spawn()
        {
            var holder = new GameObject("CKCompanionHolder"); holder.SetActive(false);
            var clone = Instantiate(player.gameObject, holder.transform);
            clone.name = "CKCompanion";
            foreach (var c in clone.GetComponentsInChildren<Component>(true))
            {
                if (c == null) continue;
                if (c is Collider || c is Collider2D || c is Rigidbody || c is Rigidbody2D || c is Camera || c is AudioListener || c is AudioSource) DestroyImmediate(c);
            }
            bodyPc = clone.GetComponent<PlayerController>();
            foreach (var sr in new[] { bodyPc.carryableSwingItemSprite, bodyPc.carryableRangeItemSprite, bodyPc.carryableShieldItemSprite, bodyPc.instrumentSprite,
                bodyPc.carryablePlaceItemSprite, bodyPc.carryableBigSpearItemSprite, bodyPc.carryableBigSwingItemSprite, bodyPc.carryableDrillToolSprite, bodyPc.carryableFishingRodSprite, bodyPc.hitAreaBoxSR, bodyPc.hitAreaSR })
                if (sr != null) sr.enabled = false;
            clone.transform.SetParent(null, false);
            Destroy(holder);
            body = clone;
            anim = bodyPc.animator;
            try { RandomLook(); } catch (Exception e) { Plugin.Log.LogWarning("random look failed, keeping player look: " + e.Message); }
            float off = Plugin.SpawnOffset.Value > 0 ? Plugin.SpawnOffset.Value : 1.5f;
            var pp = player.WorldPosition; wpos = pp;
            for (int i = 0; i < 16; i++)
            {
                float a = i * Mathf.PI / 8f; var c = pp + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * off;
                if (Walkable(Tile(c))) { wpos = c; break; }
            }
            {
                var lk = Manager.multiMap.GetTileLayerLookup(); var o = Manager.camera.RenderOrigo; var o2 = new int2(o.x, o.z);
                int nA = 0, nB = 0; for (int dx = -5; dx <= 5; dx++) for (int dz = -5; dz <= 5; dz++) { var d = new int2(dx, dz);
                    if (lk.GetTopTile(Tile(pp) + d).tileType != TileType.none) nA++; if (lk.GetTopTile(Tile(pp) + o2 + d).tileType != TileType.none) nB++; }
                Plugin.Log.LogInfo($"spawn check: walkable={Walkable(Tile(pp))} origo={o} tf={Fmt(player.transform.position)} tilesNear={nA} tilesNear+origo={nB}");
            }
            Place();
            Plugin.Log.LogInfo($"companion spawned: {myName} at {Fmt(wpos)} (player {Fmt(player.WorldPosition)})");
            Say("hello", 0, myName);
        }

        void RandomLook()
        {
            var t = bodyPc.customizationTable.Get();
            var c = bodyPc.activeCustomization;
            var bodies = t.bodySkinCollection.Get(); int bi = rng.Next(bodies.Count);
            c.body = bodies[bi].address;
            c.eyes = t.eyeSkinCollection.Get()[bi].address;
            var shirts = t.shirtSkinCollection.Get(); c.shirtSkin = shirts[bi].address;
            var shirtCols = shirts[bi].replacementColorsCollectionRef.Get(); c.shirtColor = shirtCols[rng.Next(shirtCols.Count)].address;
            var pants = t.pantsSkinCollection.Get(); c.pantsSkin = pants[bi].address;
            var pantsCols = pants[bi].replacementColorsCollectionRef.Get(); c.pantsColor = pantsCols[rng.Next(pantsCols.Count)].address;
            var skin = t.skinReplacementColors.Get(); int si = rng.Next(skin.Count);
            c.skinColor = skin[si].address;
            var shade = t.hairShadeReplacementColors.Get(); c.hairShadeColor = shade[Math.Min(si, shade.Count - 1)].address;
            var hair = t.hairSkinCollection.Get(); c.hair = hair[rng.Next(hair.Count)].address;
            var hairCols = t.hairReplacementColors.Get(); c.hairColor = hairCols[rng.Next(hairCols.Count)].address;
            var eyeCols = t.eyeReplacementColors.Get(); c.eyesColor = eyeCols[rng.Next(eyeCols.Count)].address;
            c.helm = default; c.breastArmor = default; c.pantsArmor = default;
            string[] names = { "Pip", "Bumble", "Dobbs", "Nib", "Tumble", "Gus", "Moss", "Wobble", "Fennel", "Bix" };
            myName = string.IsNullOrEmpty(Plugin.BuddyName.Value) ? names[rng.Next(names.Length)] : Plugin.BuddyName.Value;
            bodyPc.activeCustomization = c;
            bodyPc.RefreshCustomization();
            Plugin.Log.LogInfo($"random look: body {bi}/{bodies.Count} skin {si}/{skin.Count} hair {hair.Count} options");
        }

        // ---------- movement on the tile grid ----------
        List<int2> path; int pathI; float tPath, tWander; Vector3 wanderAt;

        void Follow()
        {
            Vector3 target = player.WorldPosition;
            if (Plugin.WanderRadius.Value > 0)
            {
                if (Time.time > tWander || HDist(wpos, wanderAt) < 1f)
                {
                    tWander = Time.time + 8f;
                    for (int i = 0; i < 12; i++)
                    {
                        float a = (float)(rng.NextDouble() * Math.PI * 2), rr = Plugin.WanderRadius.Value * (0.4f + 0.6f * (float)rng.NextDouble());
                        var c = target + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * rr;
                        if (Walkable(Tile(c))) { wanderAt = c; Plugin.Log.LogInfo("[wander] to " + Fmt(c)); break; }
                    }
                }
                target = wanderAt; moving = true;
            }
            float d = HDist(wpos, target);
            if (HDist(wpos, player.WorldPosition) > Plugin.TeleportDist.Value) { Teleport("far " + d.ToString("F1")); return; }
            if (Time.time < tripUntil) { moving = false; Anim(Vector3.zero); return; }
            if (!moving && d > Plugin.FollowMax.Value) moving = true;
            if (moving && d < (Plugin.FollowMin.Value + Plugin.FollowMax.Value) * 0.5f) { moving = false; path = null; }
            if (!moving) { Anim(Vector3.zero, target - wpos); tStuckSince = -1f; return; }

            if (Time.time > tPath) { tPath = Time.time + 0.4f; path = FindPath(Tile(wpos), Tile(target)); pathI = 1; }
            Vector3 aim = target;
            if (path != null && path.Count > 1)
            {
                while (pathI < path.Count - 1 && HDist(wpos, ToV(path[pathI])) < 0.3f) pathI++;
                aim = ToV(path[Math.Min(pathI, path.Count - 1)]);
                tStuckSince = -1f;
            }
            else
            {
                if (tStuckSince < 0) tStuckSince = Time.time;
                if (Time.time - tStuckSince > 3f) { Say("stuck", 1); Teleport("no path"); return; }
            }
            Vector3 dir = aim - wpos; dir.y = 0;
            if (dir.sqrMagnitude < 0.0001f) return;
            float sp = Plugin.Speed.Value * Mathf.Clamp(d / Plugin.FollowMax.Value, 1f, 2.2f);
            Vector3 step = dir.normalized * Mathf.Min(sp * Time.deltaTime, dir.magnitude);
            Vector3 next = wpos + step;
            if (Walkable(Tile(next))) wpos = next;
            wpos.y = Mathf.Lerp(wpos.y, target.y, 0.2f);
            Anim(dir.normalized);
            // clumsy: the odd trip while walking
            if (Plugin.Clumsiness.Value > 0 && rng.NextDouble() < 0.0025 * Plugin.Clumsiness.Value * Time.deltaTime * 60f / 4f)
            {
                if (Say("trip", 1)) { tripUntil = Time.time + 1.1f; Plugin.Log.LogInfo("[clumsy] tripped at " + Fmt(wpos)); }
            }
        }

        void Teleport(string why)
        {
            var p = player.WorldPosition; Vector3 best = p;
            for (int i = 0; i < 8; i++)
            {
                float a = i * Mathf.PI / 4f; var c = p + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * 1.5f;
                if (Walkable(Tile(c))) { best = c; break; }
            }
            wpos = best; path = null; moving = false; tStuckSince = -1f;
            Plugin.Log.LogInfo($"[teleport] {why} -> {Fmt(wpos)}");
            Say("teleport", 0);
        }

        void Anim(Vector3 dir, Vector3? face = null)
        {
            if (anim == null) return;
            Vector3 f = face ?? dir;
            anim.SetFloat(H_MOVE_X, dir.x); anim.SetFloat(H_MOVE_Y, dir.z);
            anim.SetFloat(H_SPEED, dir.sqrMagnitude > 0.01f ? 1f : 0f);
            if (f.sqrMagnitude > 0.01f)
            {
                // snap to 4 directions like the player
                Vector2 v = Mathf.Abs(f.x) > Mathf.Abs(f.z) ? new Vector2(Mathf.Sign(f.x), 0) : new Vector2(0, Mathf.Sign(f.z));
                anim.SetFloat(H_FACE_X, v.x); anim.SetFloat(H_FACE_Y, v.y);
            }
        }

        void Place()
        {
            if (body == null) return;
            Vector3 origo = (Vector3)Manager.camera.RenderOrigo;
            body.transform.position = wpos - origo;
        }

        string TileDiag()
        {
            try
            {
                var all = Manager.multiMap.GetTileLayerLookup().AllTiles; int n = all.Count(); string k = "";
                if (n > 0) { var ks = all.GetKeyArray(Unity.Collections.Allocator.Temp); k = ks[0].ToString(); ks.Dispose(); }
                return $"tiles={n} key0={k} walk={Walkable(Tile(player.WorldPosition))}";
            }
            catch (Exception e) { return "tilediag " + e.GetType().Name; }
        }

        internal static int2 Tile(Vector3 w) => new int2(Mathf.RoundToInt(w.x), Mathf.RoundToInt(w.z));
        Vector3 ToV(int2 t) => new Vector3(t.x, wpos.y, t.y);

        internal static readonly Dictionary<int2, float> TempBlocked = new Dictionary<int2, float>();
        internal static bool Walkable(int2 t)
        {
            if (TempBlocked.Count > 0 && TempBlocked.TryGetValue(t, out var until)) { if (Time.time < until) return false; TempBlocked.Remove(t); }
            // same rule the game uses for walkability (TileTypeUtility.IsWalkableTile on the top tile): ground/floor/bridge/rug/rail/... yes; water/pit/bigRoot/fence/wall/ore/none no
            return Manager.multiMap.GetTileLayerLookup().GetTopTile(t).tileType.IsWalkableTile();
        }

        internal static bool BlocksSight(int2 t)
        {
            var m = Manager.multiMap.GetTileLayerLookup();
            return m.HasTile(t, TileType.wall) || m.HasTile(t, TileType.ore) || m.HasTile(t, TileType.greatWall);
        }

        static readonly int2[] nb = { new int2(1, 0), new int2(-1, 0), new int2(0, 1), new int2(0, -1), new int2(1, 1), new int2(1, -1), new int2(-1, 1), new int2(-1, -1) };
        // Tiles covered by placed objects (stations, chests, fences...): not in the tile map, rebuilt by AutoPlayer.
        internal static HashSet<int2> Occupied = new HashSet<int2>();
        // Extra per-tile cost (danger near enemies etc.), set by the Director; null = none.
        internal static Func<int2, float> ExtraCost;
        // Tiles learned the hard way: footprints of entities we bumped into (Director.LearnBlockers). Persistent for the session.
        internal static readonly HashSet<int2> Learned = new HashSet<int2>();
        internal static bool WalkableNoOcc(int2 t) => Walkable(t);
        internal static bool IgnoreOccupied; // last-resort search: placed-object footprints may over-block (run 27)
        internal static bool Free(int2 t) => Walkable(t) && (IgnoreOccupied || !Occupied.Contains(t)) && !Learned.Contains(t);
        // low collider the player slips past on a diagonal (bigRoot only; walls and fences keep the no-corner-cut rule)
        internal static bool Squeezable(int2 t) => Manager.multiMap.GetTileLayerLookup().GetTopTile(t).tileType == TileType.bigRoot;

        // binary heap keyed by f
        sealed class Heap
        {
            readonly List<(float f, int2 t)> a = new List<(float, int2)>();
            public int Count => a.Count;
            public void Push(float f, int2 t) { a.Add((f, t)); int i = a.Count - 1; while (i > 0) { int p = (i - 1) >> 1; if (a[p].f <= a[i].f) break; (a[p], a[i]) = (a[i], a[p]); i = p; } }
            public (float f, int2 t) Pop()
            {
                var r = a[0]; int n = a.Count - 1; a[0] = a[n]; a.RemoveAt(n); int i = 0;
                while (true) { int l = 2 * i + 1, m = i; if (l < n && a[l].f < a[m].f) m = l; if (l + 1 < n && a[l + 1].f < a[m].f) m = l + 1; if (m == i) break; (a[m], a[i]) = (a[i], a[m]); i = m; }
                return r;
            }
        }

        // A*: 8 neighbours, no corner cutting, wall-hug penalty (the player has a radius), optional danger cost,
        // partial = path to the node closest to b when b is unreachable within maxNodes. Result is string-pulled (Theta-like).
        internal static List<int2> FindPath(int2 a, int2 b, int maxNodes = 3000, bool partial = false)
        {
            if (a.Equals(b)) return new List<int2> { a, b };
            var open = new Heap(); var came = new Dictionary<int2, int2>(); var g = new Dictionary<int2, float>(); var closed = new HashSet<int2>();
            var cache = new Dictionary<int2, bool>(); bool F(int2 t) { if (!cache.TryGetValue(t, out var v)) { v = Free(t); cache[t] = v; } return v; } // per-search cache: big searches (40k nodes) stay cheap
            g[a] = 0; open.Push(H(a, b), a); int2 best = a; float bestH = H(a, b); var extra = ExtraCost;
            while (open.Count > 0 && closed.Count < maxNodes)
            {
                var (f, p) = open.Pop(); if (closed.Contains(p)) continue; closed.Add(p);
                float hp = H(p, b); if (hp < bestH) { bestH = hp; best = p; }
                if (p.Equals(b) || hp < 1.1f) return Smooth(Rebuild(came, p));
                foreach (var o in nb)
                {
                    var n = p + o;
                    bool diag = o.x != 0 && o.y != 0;
                    if (!F(n) && !n.Equals(b)) continue;
                    // no corner cutting past walls; but the player squeezes diagonally between bigRoot tiles (run 24: push (1,1) crossed, push (1,0) did not)
                    bool squeeze = false;
                    if (diag)
                    {
                        var ox = new int2(p.x + o.x, p.y); var oy = new int2(p.x, p.y + o.y);
                        if (!F(ox)) { if (!Squeezable(ox)) continue; squeeze = true; }
                        if (!F(oy)) { if (!Squeezable(oy)) continue; squeeze = true; }
                    }
                    float step = diag ? 1.414f : 1f; if (squeeze) step += 0.6f;
                    if (!F(new int2(n.x + 1, n.y)) || !F(new int2(n.x - 1, n.y)) || !F(new int2(n.x, n.y + 1)) || !F(new int2(n.x, n.y - 1))) step += 0.35f; // hug penalty
                    if (extra != null) step += extra(n);
                    float ng = g[p] + step;
                    if (g.TryGetValue(n, out var og) && og <= ng) continue;
                    g[n] = ng; came[n] = p; open.Push(ng + H(n, b), n);
                }
            }
            if (partial && !best.Equals(a)) return Smooth(Rebuild(came, best));
            return null;
        }
        static List<int2> Rebuild(Dictionary<int2, int2> came, int2 p) { var res = new List<int2> { p }; while (came.TryGetValue(p, out var q)) { p = q; res.Add(p); } res.Reverse(); return res; }
        // drop waypoints when the straight line between the kept ones only crosses free tiles (with a 1-tile margin check at diagonals)
        static List<int2> Smooth(List<int2> path)
        {
            if (path == null || path.Count < 3) return path;
            var res = new List<int2> { path[0] }; int i = 0;
            while (i < path.Count - 1)
            {
                int j = Math.Min(path.Count - 1, i + 12);
                while (j > i + 1 && !LineFree(path[i], path[j])) j--;
                res.Add(path[j]); i = j;
            }
            return res;
        }
        internal static bool LineFree(int2 a, int2 b)
        {
            int dx = Math.Abs(b.x - a.x), dy = Math.Abs(b.y - a.y), sx = a.x < b.x ? 1 : -1, sy = a.y < b.y ? 1 : -1, err = dx - dy; int x = a.x, y = a.y, guard = 0;
            while (guard++ < 200)
            {
                var t = new int2(x, y); if (!Free(t) && !t.Equals(b)) return false;
                if (x == b.x && y == b.y) return true;
                int e2 = 2 * err;
                if (e2 > -dy) { err -= dy; x += sx; if (!Free(new int2(x, y))) return false; }
                if (e2 < dx) { err += dx; y += sy; if (!Free(new int2(x, y))) return false; }
            }
            return false;
        }
        static float H(int2 a, int2 b) => math.distance((float2)a, (float2)b);

        // ---------- senses (fair: radius + no wall between) ----------
        bool CanSee(Vector3 w, float radius)
        {
            if (HDist(wpos, w) > radius) return false;
            int2 a = Tile(wpos), b = Tile(w);
            float len = math.distance((float2)a, (float2)b); int steps = Mathf.CeilToInt(len * 2);
            for (int i = 1; i < steps; i++)
            {
                var p = math.lerp((float2)a, (float2)b, i / (float)steps);
                var t = new int2((int)math.round(p.x), (int)math.round(p.y));
                if (t.Equals(a) || t.Equals(b)) continue;
                if (BlocksSight(t)) return false;
            }
            return true;
        }

        void Sense()
        {
            if (Time.time > tScan) { tScan = Time.time + 1.5f; ents = FindObjectsOfType<EntityMonoBehaviour>(); }
            Vector3 pp = player.WorldPosition;
            // low health: the buddy sees the player
            try { int hp = player.currentHealth, mx = player.GetMaxHealth(); if (mx > 0 && hp > 0 && hp < mx * Plugin.LowHp.Value) Say("lowhealth", 3); } catch { }

            int enemies = 0; EntityMonoBehaviour nearest = null, boss = null; float nd = 1e9f;
            foreach (var e in ents)
            {
                if (e == null || e == bodyPc || e == player || !e.isActiveAndEnabled) continue;
                bool isEnemy; try { isEnemy = e.isEnemy; } catch { continue; }
                Vector3 ep = e.WorldPosition;
                if (isEnemy)
                {
                    int hp, mx; try { hp = e.currentHealth; mx = e.GetMaxHealth(); } catch { continue; }
                    if (hp <= 0 || !CanSee(ep, Plugin.Sight.Value)) continue;
                    enemies++;
                    float d = HDist(wpos, ep); if (d < nd) { nd = d; nearest = e; }
                    if (mx >= 1500 && boss == null) boss = e;
                    continue;
                }
                string id; try { id = e.objectData.objectID.ToString(); } catch { continue; }
                if (id.IndexOf("Chest", StringComparison.Ordinal) >= 0 && !id.StartsWith("Locked") && CanSee(ep, Plugin.Sight.Value))
                {
                    int key = e.GetInstanceID();
                    if (seenThing.TryGetValue(key, out var ts) && Time.time - ts < 600f) continue;
                    if (Say("chest", 1, Nice(id), Dir(pp, ep))) seenThing[key] = Time.time;
                }
            }
            if (boss != null) Say("boss", 4, NameOf(boss), Dir(pp, boss.WorldPosition));
            if (enemies >= 3) Say("danger", 3, enemies);
            if (nearest != null) Say("enemy", 2, NameOf(nearest), Dir(pp, nearest.WorldPosition));

            // ore veins in walls, seen from here
            if (Time.time - Last("ore") > Cd("ore"))
            {
                int2 me = Tile(wpos); int r = Mathf.CeilToInt(Plugin.Sight.Value * 0.7f);
                var m = Manager.multiMap.GetTileLayerLookup();
                for (int dx = -r; dx <= r; dx++) for (int dz = -r; dz <= r; dz++)
                {
                    var t = me + new int2(dx, dz);
                    if (!m.HasTile(t, TileType.ore)) continue;
                    long key = ((long)t.x << 32) ^ (uint)t.y;
                    if (seenOre.TryGetValue(key, out var ts) && Time.time - ts < 300f) continue;
                    Vector3 w = new Vector3(t.x, wpos.y, t.y);
                    if (!CanSee(w, r)) continue;
                    string kind = OreName(m, t);
                    // mark the whole vein around it as seen
                    for (int ex = -3; ex <= 3; ex++) for (int ez = -3; ez <= 3; ez++) seenOre[((long)(t.x + ex) << 32) ^ (uint)(t.y + ez)] = Time.time;
                    if (Say("ore", 1, kind, Dir(pp, w))) { dx = r + 1; break; }
                }
            }

            if (Time.time - lastAnyCallout > Plugin.IdleAfter.Value && !moving) Say("idle", 0);
        }

        static string OreName(PugTilemap.SinglePugMap.TileLayerLookup m, int2 t)
        {
            for (int ts = 0; ts < 64; ts++)
                if (m.HasTile(t, TileType.ore, ts)) { var n = Nice(((Tileset)ts).ToString()); return n.EndsWith("ore") ? n : n + " ore"; }
            return "ore";
        }

        string NameOf(EntityMonoBehaviour e) { try { return Nice(e.objectData.objectID.ToString()); } catch { return "something"; } }

        static string Nice(string id)
        {
            if (string.IsNullOrEmpty(id)) return "thing";
            return Regex.Replace(id, "(?<=[a-z])(?=[A-Z0-9])", " ").ToLowerInvariant();
        }

        // screen: +z is up, +x is right
        static string Dir(Vector3 from, Vector3 to)
        {
            Vector3 d = to - from; d.y = 0;
            if (d.magnitude < 1.5f) return "right here";
            float a = Mathf.Atan2(d.z, d.x) * Mathf.Rad2Deg;
            if (a > -22.5f && a <= 22.5f) return "to the right";
            if (a > 22.5f && a <= 67.5f) return "up right";
            if (a > 67.5f && a <= 112.5f) return "up ahead";
            if (a > 112.5f && a <= 157.5f) return "up left";
            if (a > 157.5f || a <= -157.5f) return "to the left";
            if (a > -157.5f && a <= -112.5f) return "down left";
            if (a > -112.5f && a <= -67.5f) return "below us";
            return "down right";
        }

        // ---------- talking ----------
        float Cd(string k) => (baseCd.TryGetValue(k, out var c) ? c : 30f) * Plugin.CooldownScale.Value;
        float Last(string k) => lastSaid.TryGetValue(k, out var t) ? t : -9999f;

        bool Say(string type, int prio, params object[] args)
        {
            if (Time.time - Last(type) < Cd(type)) return false;
            if (Time.time < floatUntil && prio < floatPrio) return false;
            var opts = lines[type];
            int v = variant.TryGetValue(type, out var vv) ? vv : rng.Next(opts.Length);
            variant[type] = (v + 1 + rng.Next(opts.Length - 1 > 0 ? opts.Length - 1 : 1)) % opts.Length;
            string text; try { text = string.Format(opts[v % opts.Length], args); } catch { text = opts[v % opts.Length]; }
            if (text.Length > 0) text = char.ToUpperInvariant(text[0]) + text.Substring(1);
            lastSaid[type] = Time.time; lastAnyCallout = Time.time;
            floatText = text; floatUntil = Time.time + Plugin.DisplaySecs.Value; floatPrio = prio;
            hud.Add(myName + ": " + text); if (hud.Count > 3) hud.RemoveAt(0);
            Plugin.Log.LogInfo($"[callout:{type}] \"{text}\" at companion={Fmt(wpos)}");
            return true;
        }

        int testI;
        void TestCallout()
        {
            var k = lines.Keys.ToArray()[testI++ % lines.Count];
            lastSaid.Remove(k); floatUntil = 0;
            Plugin.Log.LogInfo("[debug] test callout " + k);
            Say(k, 9, "slime", "to the left");
        }

        GUIStyle style, hudStyle;
        void OnGUI()
        {
            if (body == null || !visible || player == null) return;
            if (style == null)
            {
                style = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.LowerCenter, fontSize = 18, fontStyle = FontStyle.Bold, wordWrap = true };
                hudStyle = new GUIStyle(GUI.skin.label) { fontSize = 15 };
            }
            var cam = Camera.main;
            if (Plugin.FloatingText.Value && Time.time < floatUntil && cam != null)
            {
                Vector3 sp = cam.WorldToScreenPoint(body.transform.position + Vector3.up * 1.6f + Vector3.forward * 0.6f);
                if (sp.z > 0)
                {
                    var r = new Rect(sp.x - 170, Screen.height - sp.y - 70, 340, 70);
                    style.normal.textColor = Color.black; GUI.Label(new Rect(r.x + 2, r.y + 2, r.width, r.height), floatText, style);
                    style.normal.textColor = new Color(1f, 0.95f, 0.6f); GUI.Label(r, floatText, style);
                }
            }
            if (Plugin.HudLine.Value)
                for (int i = 0; i < hud.Count; i++) { hudStyle.normal.textColor = new Color(1, 1, 1, 0.85f); GUI.Label(new Rect(12, Screen.height - 150 + i * 20, 700, 22), hud[i], hudStyle); }
        }

        internal static float HDist(Vector3 a, Vector3 b) { a.y = 0; b.y = 0; return Vector3.Distance(a, b); }
        internal static string Fmt(Vector3 v) => string.Format(System.Globalization.CultureInfo.InvariantCulture, "({0:F1}, {1:F1}, {2:F1})", v.x, v.y, v.z);
    }

}
