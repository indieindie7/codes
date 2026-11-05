using System;
using System.Collections.Generic;
using BehaviorDesigner.Runtime;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using Isto.Atrio;
using Isto.Core.Beings;
using Isto.Core.Items;
using Isto.Core.Automation;
using Isto.Core.Game;
using Isto.Core.Power;
using UnityEngine.AI;
using UnityEngine;

namespace AtrioCompanion
{
    [BepInPlugin("local.atrio.companion", "Atrio Companion", "0.1.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static ManualLogSource Log;
        public static ConfigEntry<bool> Enabled, DebugNoPlayer, ShowHud, ShowFloating;
        public static ConfigEntry<KeyCode> ToggleKey, TestKey;
        public static ConfigEntry<int> AutoLoadSlot;
        public static ConfigEntry<float> SpawnOffset, MachineIdleSecs;
        public static ConfigEntry<float> FollowMin, FollowMax, Teleport, Speed, Sight, ResourceRadius, Volume, CdScale, ShowSecs, IdleAfter, LowHp;
        public static Dictionary<string, ConfigEntry<float>> Cd = new Dictionary<string, ConfigEntry<float>>();

        void Awake()
        {
            Log = Logger;
            Enabled = Config.Bind("General", "Enabled", true, "Companion on/off");
            ToggleKey = Config.Bind("General", "ToggleKey", KeyCode.F7, "Hotkey: toggle companion");
            TestKey = Config.Bind("General", "TestCalloutsKey", KeyCode.F8, "Hotkey: fire one of every callout (debug)");
            DebugNoPlayer = Config.Bind("Debug", "SpawnWithoutPlayer", false, "Spawn near camera even with no player (menu testing)");
            AutoLoadSlot = Config.Bind("Debug", "AutoLoadSaveSlot", -1, "Test only: load this save slot from the title screen automatically (-1 = off)");
            SpawnOffset = Config.Bind("Debug", "SpawnOffset", 0f, "Test only: spawn this many meters away (0 = beside player)");
            MachineIdleSecs = Config.Bind("Senses", "MachineIdleSeconds", 30f, "A machine with a recipe that has not cooked this long counts as idle");
            FollowMin = Config.Bind("Follow", "FollowDistanceMin", 2f, "Meters");
            FollowMax = Config.Bind("Follow", "FollowDistanceMax", 4f, "Meters");
            Teleport = Config.Bind("Follow", "TeleportDistance", 25f, "Teleport beside player if farther");
            Speed = Config.Bind("Follow", "Speed", 6f, "Base move speed, m/s (scales up when far)");
            Sight = Config.Bind("Senses", "SightRadius", 14f, "Companion only calls out what it sees within this radius (needs line of sight)");
            ResourceRadius = Config.Bind("Senses", "ResourceRadius", 9f, "Resource callout radius");
            LowHp = Config.Bind("Senses", "LowHealthFraction", 0.3f, "Low health threshold");
            ShowHud = Config.Bind("Callouts", "HudLine", true, "Corner HUD line");
            ShowFloating = Config.Bind("Callouts", "FloatingText", true, "Text above companion");
            Volume = Config.Bind("Callouts", "Volume", 1f, "0 = silent, scales text size/opacity");
            CdScale = Config.Bind("Callouts", "CooldownScale", 1f, "Multiplies all cooldowns");
            ShowSecs = Config.Bind("Callouts", "DisplaySeconds", 4f, "How long a line stays up");
            IdleAfter = Config.Bind("Callouts", "IdleChatterAfterSeconds", 90f, "Quiet time before idle chatter");
            foreach (var kv in Lines.Cooldowns)
                Cd[kv.Key] = Config.Bind("Cooldowns", kv.Key, kv.Value, "Seconds between '" + kv.Key + "' callouts");

            var go = new GameObject("AtrioCompanion");
            DontDestroyOnLoad(go);
            go.hideFlags = HideFlags.HideAndDontSave;
            go.AddComponent<Companion>();
            Log.LogInfo("Atrio Companion loaded (no Harmony patches needed: pure scene scanning)");
        }
    }

    static class Lines
    {
        public static readonly Dictionary<string, float> Cooldowns = new Dictionary<string, float>
        {
            {"enemy", 10f}, {"lowhealth", 25f}, {"resource", 45f}, {"night", 90f}, {"danger", 30f}, {"idle", 120f}, {"unpowered", 60f}, {"norecipe", 90f}, {"machineidle", 75f}
        };
        public static readonly Dictionary<string, string[]> Text = new Dictionary<string, string[]>
        {
            {"enemy", new[]{"Hostile, {0}!", "Contact, {0}!", "Something's moving, {0}.", "Eyes {0}!", "Got one {0}, watch out!"}},
            {"danger", new[]{"Several of them, {0}! Careful!", "That's a lot of hostiles!", "We're getting surrounded!"}},
            {"lowhealth", new[]{"You're hurt, patch up!", "Health's low, get somewhere safe.", "You're bleeding out here!", "Heal. Now."}},
            {"resource", new[]{"{0} over there.", "I see {0} nearby.", "Might want that {0}.", "Free {0}, just sitting there."}},
            {"night", new[]{"Night's falling.", "It's getting dark, stay close.", "Dark's coming. Light up.", "Night. Watch your back."}},
            {"unpowered", new[]{"That {0} has no power.", "{0}'s dark. Needs a tether.", "No juice on the {0}, {1}."}},
            {"norecipe", new[]{"{0} isn't set to make anything.", "Idle {0}, no recipe picked.", "That {0}'s just sitting there. Give it a job."}},
            {"machineidle", new[]{"{0} stopped working, {1}.", "{0} is starved for input.", "Hey, the {0} went quiet."}},
            {"idle", new[]{"Quiet out here...", "Too quiet.", "Anyone else hear that? No? Okay.", "I could use a rest.", "Wonder what the machines are up to."}}
        };
    }

    class Companion : MonoBehaviour
    {
        GameObject body; SpriteRenderer sr; Transform tr;
        PlayerController player; PlayerHealth pHealth; Transform camT;
        Health[] healthCache = new Health[0]; HarvestableController[] harvCache = new HarvestableController[0];
        DayNightCycle dnc; bool wasDay = true, dncKnown;
        float tScan, tSense, tLog, tFind, bodyScale = 1.5f, bobT;
        float lastCallout; readonly Dictionary<string, float> lastBy = new Dictionary<string, float>();
        string curText = ""; float curUntil; int curPrio;
        readonly List<string> hud = new List<string>();
        bool moving; Vector3 lastPlayerPos; float stillSince;
        GUIStyle style, shadow;
        int testIdx;

        void Update()
        {
            try { Tick(); } catch (Exception e) { Plugin.Log.LogError("tick: " + e); }
        }

        void Tick()
        {
            if (Input.GetKeyDown(Plugin.ToggleKey.Value)) { Plugin.Enabled.Value = !Plugin.Enabled.Value; Plugin.Log.LogInfo("toggle -> " + Plugin.Enabled.Value); }
            if (Input.GetKeyDown(Plugin.TestKey.Value)) ForceTest();
            if (!Plugin.Enabled.Value) { if (body) Destroy(body); body = null; return; }

            if (Time.unscaledTime > tFind) { tFind = Time.unscaledTime + 1f; FindRefs(); }
            if (camT == null && Camera.main != null) camT = Camera.main.transform;

            AutoLoad();
            bool havePlayer = player != null;
            if (!havePlayer && !(Plugin.DebugNoPlayer.Value && camT != null)) { if (body) { Destroy(body); body = null; Plugin.Log.LogInfo("companion despawned (no player)"); } return; }

            Vector3 target = havePlayer ? player.transform.position : GroundCam();
            if (body == null) Spawn(target);
            Follow(target, havePlayer);
            Billboard();

            if (Time.time > tSense) { tSense = Time.time + 0.5f; Sense(target, havePlayer); }
            if (Time.time > tLog) { tLog = Time.time + 5f; Plugin.Log.LogInfo(string.Format("[pos] companion={0} target={1} dist={2:F1} moving={3}", tr.position.ToString("F1"), target.ToString("F1"), HDist(tr.position, target), moving)); }
            if (Time.time - lastCallout > Plugin.IdleAfter.Value) Say("idle", 0, null);
        }

        bool autoLoaded; float titleSince = -1f;
        void AutoLoad()
        {
            if (autoLoaded || Plugin.AutoLoadSlot.Value < 0 || player != null) return;
            var gs = FindObjectOfType<GameState>();
            if (gs == null || GameState.CurrentlyLoading || !gs.IsInTitleScene()) { titleSince = -1f; return; }
            if (titleSince < 0) titleSince = Time.unscaledTime;
            if (Time.unscaledTime - titleSince < 4f) return;
            autoLoaded = true;
            Plugin.Log.LogInfo("debug autoload: loading save slot " + Plugin.AutoLoadSlot.Value);
            gs.LoadSaveGame(Plugin.AutoLoadSlot.Value);
        }

        Vector3 GroundCam() { var p = camT.position + camT.forward * 5f; return p; }

        void FindRefs()
        {
            if (player == null) { player = FindObjectOfType<PlayerController>(); if (player != null) { Plugin.Log.LogInfo("player found at " + player.transform.position.ToString("F1")); pHealth = null; stillSince = Time.time; } }
            if (player != null && pHealth == null) pHealth = player.GetComponentInChildren<PlayerHealth>(true) ?? FindObjectOfType<PlayerHealth>();
            if (dnc == null) dnc = FindObjectOfType<DayNightCycle>();
        }

        void Spawn(Vector3 near)
        {
            body = new GameObject("CompanionBody");
            tr = body.transform;
            var vis = new GameObject("Sprite"); vis.transform.SetParent(tr, false);
            sr = vis.AddComponent<SpriteRenderer>();
            sr.sprite = MakeSprite();
            sr.sortingOrder = 500;
            if (player != null)
            {
                var rs = player.GetComponentsInChildren<Renderer>();
                if (rs.Length > 0) { var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); bodyScale = Mathf.Clamp(b.size.y, 0.8f, 2f); }
            }
            float off = Plugin.SpawnOffset.Value > 0 ? Plugin.SpawnOffset.Value : 2.7f;
            tr.position = Ground(near + new Vector3(-off, 0, -off * 0.4f), near.y);
            Plugin.Log.LogInfo("companion spawned at " + tr.position.ToString("F1") + " scale=" + bodyScale.ToString("F2") + " player=" + (player != null));
            lastCallout = Time.time; stillSince = Time.time;
        }

        static Sprite MakeSprite()
        {
            int n = 64; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
            var c = new Color[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = x - 31.5f, dy = y - 28f; float d = Mathf.Sqrt(dx * dx + dy * dy);
                Color col = Color.clear;
                if (d < 22f) col = new Color(0.35f, 0.85f, 0.9f, 1f);
                if (d >= 19f && d < 22f) col = new Color(0.05f, 0.3f, 0.35f, 1f);
                if (y > 12 && y < 20 && (Mathf.Abs(x - 24) < 3 || Mathf.Abs(x - 40) < 3) && d < 18) col = Color.black;
                if (y > 44 && y < 52 && Mathf.Abs(dx) < 10 && dy > 14) col = new Color(0.35f, 0.85f, 0.9f, 1f);
                c[y * n + x] = col;
            }
            tex.SetPixels(c); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.1f), 64f);
        }

        void Billboard()
        {
            if (camT == null) return;
            sr.transform.rotation = camT.rotation;
            bobT += Time.deltaTime * (moving ? 12f : 2.5f);
            sr.transform.localPosition = Vector3.up * (0.06f * Mathf.Abs(Mathf.Sin(bobT)) * bodyScale);
            sr.transform.localScale = Vector3.one * bodyScale * (1f + 0.04f * Mathf.Sin(bobT));
        }

        static float HDist(Vector3 a, Vector3 b) { a.y = 0; b.y = 0; return Vector3.Distance(a, b); }

        void Follow(Vector3 target, bool havePlayer)
        {
            Vector3 pos = tr.position;
            float d = HDist(pos, target);
            if (havePlayer)
            {
                if ((target - lastPlayerPos).sqrMagnitude > 0.0004f) stillSince = Time.time;
                lastPlayerPos = target;
            }
            if (d > Plugin.Teleport.Value)
            {
                Vector3 back = camT != null ? -camT.up : Vector3.back; back.y = 0; back = back.sqrMagnitude < 0.01f ? Vector3.back : back.normalized;
                tr.position = new Vector3(target.x, target.y, target.z) + back * ((Plugin.FollowMin.Value + Plugin.FollowMax.Value) * 0.5f);
                Plugin.Log.LogInfo("companion teleported (was " + d.ToString("F1") + " m away)");
                moving = false; return;
            }
            float mid = (Plugin.FollowMin.Value + Plugin.FollowMax.Value) * 0.5f;
            if (!moving && d > Plugin.FollowMax.Value) moving = true;
            else if (moving && d < mid) moving = false;
            Vector3 flat = target - pos; flat.y = 0;
            if (d < Plugin.FollowMin.Value * 0.8f && d > 0.01f) { MoveDir(-flat.normalized, Plugin.Speed.Value * 0.5f, target.y); return; } // too close: back off
            if (!moving) { var p = tr.position; p.y = Mathf.Lerp(p.y, target.y, 0.2f); tr.position = p; corners = null; return; }
            float sp = Plugin.Speed.Value * Mathf.Clamp(d / Plugin.FollowMax.Value, 1f, 3f);
            Vector3 aim = target;
            if (Time.time > tPath) { tPath = Time.time + 0.4f; RePath(target); }
            if (corners != null && corner < corners.Length)
            {
                while (corner < corners.Length - 1 && HDist(pos, corners[corner]) < 0.4f) corner++;
                aim = corners[corner];
            }
            Vector3 ad = aim - pos; ad.y = 0;
            MoveDir(ad.sqrMagnitude > 0.01f ? ad.normalized : flat.normalized, sp, aim.y);
        }

        Vector3[] corners; int corner; float tPath; bool navLogged; NavMeshPath navPath;
        void RePath(Vector3 target)
        {
            corners = null;
            if (navPath == null) navPath = new NavMeshPath();
            NavMeshHit a, b;
            if (!NavMesh.SamplePosition(tr.position, out a, 3f, NavMesh.AllAreas) || !NavMesh.SamplePosition(target, out b, 3f, NavMesh.AllAreas)) return;
            if (NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, navPath) && navPath.status != NavMeshPathStatus.PathInvalid && navPath.corners.Length > 1)
            {
                corners = navPath.corners; corner = 1;
                if (!navLogged) { navLogged = true; Plugin.Log.LogInfo("navmesh path ok (" + corners.Length + " corners); following game pathing"); }
            }
        }

        Vector3 Ground(Vector3 p, float fallbackY)
        {
            NavMeshHit nh; if (NavMesh.SamplePosition(p, out nh, 3f, NavMesh.AllAreas)) return nh.position;
            p.y = fallbackY; return p;
        }

        void MoveDir(Vector3 dir, float speed, float y)
        {
            if (dir.sqrMagnitude < 0.0001f) return;
            float step = speed * Time.deltaTime;
            Vector3 origin = tr.position + Vector3.up * 0.5f;
            float[] angs = { 0, 30, -30, 60, -60, 90, -90, 135, -135 };
            foreach (float a in angs)
            {
                Vector3 dd = Quaternion.Euler(0, a, 0) * dir;
                RaycastHit hit;
                if (!Physics.SphereCast(origin, 0.3f, dd, out hit, step + 0.6f, ~0, QueryTriggerInteraction.Ignore) || IsIgnorable(hit.collider))
                {
                    var p = tr.position + dd * step; p.y = Mathf.Lerp(p.y, y, 0.2f); tr.position = p; return;
                }
            }
        }

        bool IsIgnorable(Collider c)
        {
            if (c == null) return true;
            if (player != null && c.transform.IsChildOf(player.transform.root)) return true;
            if (c.GetComponentInParent<Health>() != null) return true;
            return false;
        }

        // ---- senses ----
        bool Visible(Transform t, Vector3 center, float radius)
        {
            Vector3 eye = tr.position + Vector3.up * 0.8f;
            if (HDist(eye, center) > radius) return false;
            Vector3 to = center + Vector3.up * 0.5f;
            RaycastHit hit;
            if (Physics.Linecast(eye, to, out hit, ~0, QueryTriggerInteraction.Ignore))
            {
                if (hit.collider.transform.IsChildOf(t.root) || IsIgnorable(hit.collider)) return true;
                return false;
            }
            return true;
        }

        string Dir(Vector3 from, Vector3 to)
        {
            Vector3 v = to - from; v.y = 0; if (v.sqrMagnitude < 0.01f) return "right here";
            Vector3 right = camT != null ? camT.right : Vector3.right; right.y = 0; right.Normalize();
            Vector3 up = camT != null ? Vector3.ProjectOnPlane(camT.up, Vector3.up) : Vector3.forward; if (up.sqrMagnitude < 0.01f) up = Vector3.ProjectOnPlane(camT.forward, Vector3.up); up.Normalize();
            float x = Vector3.Dot(v.normalized, right), y = Vector3.Dot(v.normalized, up);
            if (Mathf.Abs(x) > Mathf.Abs(y)) return x < 0 ? "left" : "right";
            return y > 0 ? "ahead" : "behind";
        }

        void Sense(Vector3 target, bool havePlayer)
        {
            if (Time.time > tScan)
            {
                tScan = Time.time + 1.5f;
                healthCache = FindObjectsOfType<Health>();
                harvCache = FindObjectsOfType<HarvestableController>();
            }
            // enemies (own sight only; creatures w/ AI behaviour tree)
            int seen = 0; Health nearest = null; float nd = 1e9f;
            foreach (var h in healthCache)
            {
                if (h == null || !h.gameObject.activeInHierarchy || h.HP <= 0f) continue;
                if (h.GetComponentInParent<Behavior>() == null) continue;
                var p = h.transform.position;
                if (!Visible(h.transform, p, Plugin.Sight.Value)) continue;
                seen++;
                float d = HDist(tr.position, p); if (d < nd) { nd = d; nearest = h; }
            }
            if (seen >= 3 && Say("danger", 3, new object[] { Dir(tr.position, nearest.transform.position) })) { }
            else if (nearest != null) Say("enemy", 3, new object[] { Dir(target, nearest.transform.position) });

            // low health
            if (havePlayer && pHealth != null)
            {
                float cur = ReadHp(pHealth), max = pHealth.currentMaxHealth;
                if (max > 0 && cur > 0 && cur / max < Plugin.LowHp.Value) Say("lowhealth", 4, null);
            }
            // resources in sight
            HarvestableController best = null; float bd = 1e9f;
            foreach (var r in harvCache)
            {
                if (r == null || !r.gameObject.activeInHierarchy || !r.playerHarvestable || r.item == null) continue;
                if (r.IsGrowing) continue;
                var p = r.transform.position;
                float d = HDist(tr.position, p);
                if (d > Plugin.ResourceRadius.Value || d >= bd) continue;
                if (!Visible(r.transform, p, Plugin.ResourceRadius.Value)) continue;
                float sAt; if (seenRes.TryGetValue(r.GetInstanceID(), out sAt) && Time.time - sAt < 300f) continue; // already called out: no repeats
                best = r; bd = d;
            }
            if (best != null && Say("resource", 1, new object[] { Nice(SafeName(best.item)) })) seenRes[best.GetInstanceID()] = Time.time;
            // machines in sight
            if (Time.time > tMach)
            {
                tMach = Time.time + 2f;
                if (Time.time > tMachScan) { tMachScan = Time.time + 5f; facCache = FindObjectsOfType<Factory>(); tethCache = FindObjectsOfType<PowerTethered>(); }
                foreach (var t in tethCache)
                {
                    if (t == null || !t.isActiveAndEnabled || t.PowerSource || t.Powered || !t.Registered || t.IsBeingDestroyed) continue;
                    if (t.GetComponentInParent<InteractableItem>() == null) continue;
                    if (!Visible(t.transform, t.transform.position, Plugin.Sight.Value)) continue;
                    if (Say("unpowered", 2, new object[] { Nice(t.transform.root.name), Dir(target, t.transform.position) })) break;
                }
                foreach (var f in facCache)
                {
                    if (f == null || !f.isActiveAndEnabled) continue;
                    var af = facField != null ? facField.GetValue(f) as AutomationFactory : null; if (af == null) continue;
                    int id = f.GetInstanceID(); float lastBusy;
                    if (af.Cooking || af.WaitingToDropItem || !busy.TryGetValue(id, out lastBusy)) { busy[id] = Time.time; continue; }
                    if (Time.time - lastBusy < Plugin.MachineIdleSecs.Value) continue;
                    if (!Visible(f.transform, f.transform.position, Plugin.Sight.Value)) continue;
                    string nm = Nice(f.itemPile != null && f.itemPile.item != null ? SafeName(f.itemPile.item) : f.gameObject.name);
                    if (af.Recipe == null) { if (Say("norecipe", 1, new object[] { nm })) break; }
                    else if (Say("machineidle", 2, new object[] { nm, Dir(target, f.transform.position) })) break;
                }
            }
            // night
            if (dnc != null)
            {
                bool day = dnc.IsDaytime;
                if (dncKnown && wasDay && !day) Say("night", 2, null);
                wasDay = day; dncKnown = true;
            }
        }

        float tMach, tMachScan; Factory[] facCache = new Factory[0]; PowerTethered[] tethCache = new PowerTethered[0];
        readonly Dictionary<int, float> busy = new Dictionary<int, float>(), seenRes = new Dictionary<int, float>();
        static System.Reflection.FieldInfo facField = typeof(Factory).GetField("_systemFactory", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        static System.Reflection.FieldInfo hpField = typeof(PlayerHealth).GetField("_currentHealth", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        static float ReadHp(PlayerHealth h) { return hpField != null ? (float)hpField.GetValue(h) : -1f; }
        static string SafeName(Item it) { try { var n = it.itemName; if (!string.IsNullOrEmpty(n) && !n.StartsWith("#")) return n; } catch { } return it.name; }
        static string Nice(string n) { n = n.Replace("(Clone)", "").Replace("_", " ").Trim(); return n.Length == 0 ? "something" : n.ToLowerInvariant(); }

        // ---- callouts ----
        bool Say(string type, int prio, object[] args)
        {
            float now = Time.time;
            float cd = Plugin.Cd[type].Value * Plugin.CdScale.Value;
            float last;
            if (lastBy.TryGetValue(type, out last) && now - last < cd) return false;
            if (now < curUntil && prio < curPrio) return false;
            var arr = Lines.Text[type];
            string t = arr[UnityEngine.Random.Range(0, arr.Length)];
            if (args != null) t = string.Format(t, args);
            lastBy[type] = now; lastCallout = now;
            curText = t; curUntil = now + Plugin.ShowSecs.Value; curPrio = prio;
            hud.Add(t); if (hud.Count > 3) hud.RemoveAt(0);
            Plugin.Log.LogInfo(string.Format("[callout:{0}] \"{1}\" at companion={2}", type, t, tr != null ? tr.position.ToString("F1") : "-"));
            return true;
        }

        void ForceTest()
        {
            if (tr == null) { Plugin.Log.LogInfo("test callouts: no companion"); return; }
            var keys = new List<string>(Lines.Text.Keys);
            string k = keys[testIdx++ % keys.Count];
            lastBy.Remove(k); curUntil = 0;
            Say(k, 9, new object[] { "left", "wood" });
            Plugin.Log.LogInfo("test callout (debug, not sensed): " + k);
        }

        void OnGUI()
        {
            if (!Plugin.Enabled.Value || Plugin.Volume.Value <= 0.01f) return;
            if (style == null)
            {
                style = new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter, wordWrap = false };
                shadow = new GUIStyle(style);
            }
            int fs = Mathf.RoundToInt(18 * Mathf.Clamp(Plugin.Volume.Value, 0.3f, 2f));
            float a = Mathf.Clamp01(Plugin.Volume.Value);
            bool live = Time.time < curUntil;
            if (live && Plugin.ShowFloating.Value && tr != null && Camera.main != null)
            {
                var sp = Camera.main.WorldToScreenPoint(tr.position + Vector3.up * (bodyScale * 1.2f));
                if (sp.z > 0)
                {
                    var rect = new Rect(sp.x - 200, Screen.height - sp.y - 20, 400, 40);
                    Draw(rect, curText, fs, a);
                }
            }
            if (Plugin.ShowHud.Value && hud.Count > 0)
            {
                float y = Screen.height - 30 - 24 * hud.Count;
                for (int i = 0; i < hud.Count; i++)
                {
                    bool last = i == hud.Count - 1;
                    Draw(new Rect(10, y + 24 * i, 600, 24), "Companion: " + hud[i], fs - 4, a * (last && live ? 1f : 0.5f), TextAnchor.MiddleLeft);
                }
            }
        }

        void Draw(Rect r, string s, int fs, float alpha, TextAnchor al = TextAnchor.MiddleCenter)
        {
            style.fontSize = fs; style.alignment = al; shadow.fontSize = fs; shadow.alignment = al;
            shadow.normal.textColor = new Color(0, 0, 0, alpha);
            style.normal.textColor = new Color(1f, 0.92f, 0.5f, alpha);
            var r2 = r; r2.x += 1.5f; r2.y += 1.5f;
            GUI.Label(r2, s, shadow); GUI.Label(r, s, style);
        }
    }
}
