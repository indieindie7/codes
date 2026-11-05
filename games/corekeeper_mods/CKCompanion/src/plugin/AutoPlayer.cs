// AutoPlayer: drive the local player from text instructions.
// instruction text -> Goals (parser) -> task tree (each goal expands into compound/primitive tasks)
// -> primitives set a virtual stick / aim / use button that Harmony feeds into PlayerInput.
// Channel: append lines to BepInEx\ckauto\inbox.txt; state in BepInEx\ckauto\status.txt.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using BepInEx;
using HarmonyLib;
using Unity.Mathematics;
using UnityEngine;
using PugTilemap;

namespace CKCompanion
{
    public enum St { Running, Done, Failed }

    // ---------- task tree ----------
    public abstract class Task
    {
        public string Name; public St State = St.Running; public string Note = "";
        public float Started = -1f, Timeout = 60f;
        public virtual IEnumerable<Task> Kids => Enumerable.Empty<Task>();
        public St Tick()
        {
            if (Started < 0) { Started = Time.time; AutoPlayer.Log("start " + Name); }
            if (State != St.Running) return State;
            if (Time.time - Started > Timeout) { State = St.Failed; Note = "timeout"; }
            else State = Step();
            if (State != St.Running) AutoPlayer.Log((State == St.Done ? "done " : "FAILED ") + Name + (Note != "" ? " (" + Note + ")" : ""));
            return State;
        }
        protected abstract St Step();
        // a reflex suspended this task for dt seconds: do not count that time against the timeout
        public void Shift(float dt) { if (Started >= 0 && State == St.Running) Started += dt; foreach (var k in Kids) k.Shift(dt); }
    }

    // Runs children in order; children are produced lazily by Next() so the plan can re-decide each step.
    public class Seq : Task
    {
        readonly List<Task> done = new List<Task>(); Task cur; readonly Func<int, Task> next; int i;
        public Seq(string name, Func<int, Task> next, float timeout = 600f) { Name = name; this.next = next; Timeout = timeout; }
        public Seq(string name, params Task[] steps) : this(name, k => k < steps.Length ? steps[k] : null) { }
        public override IEnumerable<Task> Kids => cur == null ? done : done.Concat(new[] { cur });
        protected override St Step()
        {
            if (cur == null) { cur = next(i++); if (cur == null) return St.Done; }
            var s = cur.Tick();
            if (s == St.Running) return St.Running;
            done.Add(cur); if (done.Count > 6) done.RemoveAt(0);
            var failed = cur; cur = null;
            if (s == St.Failed) { Note = failed.Name + ": " + failed.Note; return St.Failed; }
            return St.Running;
        }
    }

    // Repeats a sub-plan until count reached or the plan generator returns null (nothing left to do).
    public class Repeat : Task
    {
        readonly Func<Task> make; readonly int count; int n, fails; Task cur; readonly List<Task> hist = new List<Task>();
        public Repeat(string name, int count, Func<Task> make) { Name = name; this.count = count; this.make = make; Timeout = 1800f; }
        public override IEnumerable<Task> Kids => cur == null ? hist : hist.Concat(new[] { cur });
        protected override St Step()
        {
            if (n >= count) return St.Done;
            if (cur == null) { cur = make(); if (cur == null) { Note = n + "/" + count + ", nothing more found"; return n > 0 ? St.Done : St.Failed; } }
            var s = cur.Tick();
            if (s == St.Running) return St.Running;
            hist.Add(cur); if (hist.Count > 4) hist.RemoveAt(0);
            if (s == St.Done) { n++; fails = 0; } else if (++fails >= 4) { Note = "4 fails in a row"; return St.Failed; }
            cur = null; Name = Regex.Replace(Name, @"\[\d+/", "[" + n + "/");
            return St.Running;
        }
    }

    // ---------- primitives ----------
    public class GoTo : Task
    {
        readonly int2 dest; readonly float within; List<int2> path; int pi; float tPath, tProgress, tJiggle; Vector3 lastPos; Vector2 jiggle; int noPath, unstick;
        public GoTo(int2 dest, float within = 0.6f, float timeout = 60f) { this.dest = dest; this.within = within; Timeout = timeout; Name = $"goto ({dest.x},{dest.y})"; }
        protected override St Step()
        {
            var me = AutoPlayer.Pos;
            if (Buddy.HDist(me, new Vector3(dest.x, me.y, dest.y)) <= within) { AutoPlayer.Move = Vector2.zero; return St.Done; }
            if (Time.time < tJiggle) { AutoPlayer.Move = jiggle; AutoPlayer.Aim = jiggle; return St.Running; }
            if (path == null || Time.time > tPath)
            {
                if (path == null && Time.time < tPath) { AutoPlayer.Move = Vector2.zero; return St.Running; }
                tPath = Time.time + 1.5f; path = Buddy.FindPath(Buddy.Tile(me), dest, 6000, true); pi = 1; Director.Repaths++;
                if (path == null)
                {   // greedy dead end (run 26: a pocket 17 tiles from home, the way out leads away from it, 6k nodes ran out first) -> search wider once
                    // run 31: the goal tile itself sits under a placed object (the core at (0,0)): nothing free is closer than where we stand -> we are there
                    if (!Buddy.Free(dest) && Buddy.HDist(me, new Vector3(dest.x, me.y, dest.y)) <= 2.5f) { Note = "destination under a placed object, stopped next to it"; AutoPlayer.Log("goto (" + dest.x + "," + dest.y + "): " + Note); return St.Done; }
                    if (noPath == 0) { path = Buddy.FindPath(Buddy.Tile(me), dest, 40000, true); if (path != null) AutoPlayer.Log("no path at 6k nodes, found at 40k"); }
                    if (path == null && noPath == 0) { Buddy.IgnoreOccupied = true; try { path = Buddy.FindPath(Buddy.Tile(me), dest, 40000, true); } finally { Buddy.IgnoreOccupied = false; } if (path != null) AutoPlayer.Log("no path at 40k, found when ignoring placed objects: " + (path[path.Count - 1].Equals(dest) ? "full" : "partial") + " path"); else AutoPlayer.Log("no path even ignoring placed objects: " + Director.Probe(me, dest, new Vector2(dest.x - me.x, dest.y - me.z), 0, 0)); }
                }
                if (path == null)
                {   // boxed in by our own avoid marks or learned blockers? drop them once and retry
                    if (Buddy.TempBlocked.Count > 0 || Buddy.Learned.Count > 0) { Buddy.TempBlocked.Clear(); Buddy.Learned.Clear(); AutoPlayer.Log("no path, cleared avoid marks + learned blockers"); tPath = 0; }
                    if (++noPath >= 3) { Note = "no path from " + Buddy.Fmt(me); return St.Failed; } AutoPlayer.Move = Vector2.zero; return St.Running;
                }
                noPath = 0;
            }
            while (pi < path.Count - 1 && Buddy.HDist(me, new Vector3(path[pi].x, me.y, path[pi].y)) < 0.35f) pi++;
            var wp = pi < path.Count ? path[pi] : dest;
            var d = new Vector2(wp.x - me.x, wp.y - me.z);
            AutoPlayer.Move = d.sqrMagnitude > 0.0001f ? d.normalized : Vector2.zero;
            AutoPlayer.Aim = AutoPlayer.Move;
            if (Buddy.HDist(me, lastPos) > 0.4f) { lastPos = me; tProgress = Time.time; }
            else if (tProgress > 0 && Time.time - tProgress > 1.5f)
            {   // stuck on something not in the tile map. 1st: sidestep (jiggle); 2nd+: learn the blocker (entity footprints around the waypoint),
                // avoid the waypoint tile itself for 20 s and re-path. Never mark the tile we stand on.
                unstick++; Director.Stucks++; tProgress = Time.time; AutoPlayer.Log(Director.Probe(me, wp, d, pi, path.Count));
                if (unstick % 2 == 1) { jiggle = new Vector2(-d.normalized.y, d.normalized.x) * (unstick % 4 == 1 ? 1 : -1); tJiggle = Time.time + 0.5f; AutoPlayer.Log($"stuck near ({wp.x},{wp.y}), sidestep"); }
                else
                {
                    var mt = Buddy.Tile(me); string learned = Director.LearnBlockers(wp, mt);
                    if (!wp.Equals(mt)) Buddy.TempBlocked[wp] = Time.time + 20f;
                    path = null; tPath = 0; AutoPlayer.Log($"blocked at ({wp.x},{wp.y}), avoid + re-path" + (learned != "" ? " [learned " + learned + "]" : ""));
                }
                if (unstick > 8) { Note = "stuck at " + Buddy.Fmt(me); AutoPlayer.Move = Vector2.zero; return St.Failed; }
            }
            if (tProgress <= 0) tProgress = Time.time;
            return St.Running;
        }
    }

    public class Equip : Task
    {
        readonly string[] kinds;
        public Equip(params string[] kinds) { this.kinds = kinds; Name = "equip " + string.Join("/", kinds); Timeout = 3f; }
        protected override St Step()
        {
            var p = Manager.main.player;
            int slot = AutoPlayer.FindHotbar(kinds);
            if (slot < 0) { Note = "none on hotbar (" + AutoPlayer.Hotbar() + ")"; return St.Failed; }
            if (p.equippedSlotIndex != slot) p.EquipSlot(slot);
            Note = "slot " + (slot - p.hotbarStartIndex + 1);
            return St.Done;
        }
    }

    public class Dig : Task
    {
        readonly int2 t;
        public Dig(int2 t) { this.t = t; Name = $"dig ({t.x},{t.y})"; Timeout = 25f; }
        protected override St Step()
        {
            var m = Manager.multiMap.GetTileLayerLookup();
            if (!AutoPlayer.IsDiggable(m, t)) { AutoPlayer.Use = false; return St.Done; }
            var me = AutoPlayer.Pos; var d = new Vector2(t.x - me.x, t.y - me.z);
            if (d.magnitude > 2.2f) { Note = "too far"; return St.Failed; }
            AutoPlayer.Move = Vector2.zero; AutoPlayer.Aim = d.normalized; AutoPlayer.Use = true;
            return St.Running;
        }
    }

    // L4D-style melee: pick the top threat, close in, strike, step back from its reach, fall back to a chokepoint when swarmed.
    public class Combat : Task
    {
        readonly float radius; readonly int wanted; int kills, lastHp; Director.Threat target; float tSwitch, tQuiet, tHold, tPath, tLost, tHitLog; int2? hold; List<int2> path; int pi;
        public Combat(float radius, int wanted) { this.radius = radius; this.wanted = wanted; Name = "combat"; Timeout = 90f; }
        protected override St Step()
        {
            var me = AutoPlayer.Pos; var p = Manager.main.player;
            if (p.isDyingOrDead || p.currentHealth <= 0) { Note = "down"; AutoPlayer.Use = false; return St.Failed; }
            if (target != null)
            {   // a kill is only a kill when we saw its hp reach 0 or the entity is gone; inactive/exception = lost sight (no kill)
                string why = null; int hp = -1;
                try { if (target.e == null) why = "gone"; else { hp = target.e.currentHealth; if (hp <= 0) why = "hp0"; else if (!target.e.gameObject.activeInHierarchy) why = "inactive"; } }
                catch (Exception ex) { why = "err " + ex.GetType().Name; }
                if (why == "gone" || why == "hp0")
                { kills++; Director.Kills++; AutoPlayer.Log($"killed {target.name} ({kills}, {why}, last hp {lastHp})"); target = null; tLost = 0; if (kills >= wanted) { AutoPlayer.Use = false; return St.Done; } }
                else if (why != null) { if (tLost == 0) tLost = Time.time; if (Time.time - tLost > 1f) { AutoPlayer.Log($"lost {target.name} ({why})"); target = null; tLost = 0; } }
                else
                {
                    if (lastHp > 0 && hp < lastHp && Time.time > tHitLog) { tHitLog = Time.time + 1f; AutoPlayer.Log($"hit {target.name} hp {lastHp}->{hp}"); }
                    lastHp = hp; tLost = 0;
                }
            }
            if (target == null || Time.time > tSwitch)
            {   // re-target by threat score every 2 s (a bigger threat in reach wins)
                tSwitch = Time.time + 2f; var top = Director.TopWithin(radius);
                if (top != null && (target == null || top.e != target.e)) { target = top; lastHp = top.hp; tLost = 0; AutoPlayer.Log("target " + top.name + $" {top.hp}/{top.max} at {top.dist:F1}"); }
                if (target == null) { if (tQuiet == 0) tQuiet = Time.time; AutoPlayer.Move = Vector2.zero; AutoPlayer.Use = false; if (Time.time - tQuiet > 2f) { Note = kills + " kills, clear"; return St.Done; } return St.Running; }
                tQuiet = 0;
            }
            foreach (var th in Director.Threats) if (th.e == target.e) { target = th; break; }
            if (target.dist > radius + 6f) { Note = "lost it"; AutoPlayer.Use = false; return St.Done; }
            var w = target.pos; var d = new Vector2(w.x - me.x, w.z - me.z); float dist = d.magnitude; var dir = dist > 0.01f ? d / dist : Vector2.up;
            AutoPlayer.Aim = dir;
            if (hold == null && Director.Near(4f) >= 3 && Time.time > tHold) { hold = Director.Chokepoint(me); tHold = Time.time + 8f; if (hold != null) AutoPlayer.Log($"swarmed ({Director.Near(4f)}), fall back to ({hold.Value.x},{hold.Value.y})"); }
            if (hold != null)
            {   // fall back to the chokepoint, then stand there and swing at what comes within reach; release when the swarm thins or after 8 s
                var h = hold.Value; var hv = new Vector2(h.x - me.x, h.y - me.z);
                if (Time.time > tHold || Director.Near(4f) <= 1) { AutoPlayer.Log("hold released"); hold = null; tHold = Time.time + 4f; }
                else if (hv.magnitude < 0.5f) { AutoPlayer.Move = Vector2.zero; AutoPlayer.Use = dist < 2.3f; return St.Running; }
                else { AutoPlayer.Move = hv.normalized; AutoPlayer.Use = dist < 2.2f; return St.Running; }
            }
            if (dist > 1.8f)
            {
                var mt = Buddy.Tile(me); var tt = Buddy.Tile(w);
                if (Buddy.LineFree(mt, tt)) { AutoPlayer.Move = dir; path = null; }
                else
                {
                    if (path == null || Time.time > tPath) { tPath = Time.time + 1f; path = Buddy.FindPath(mt, tt, 1500, true); pi = 1; }
                    if (path != null && path.Count > 1) { while (pi < path.Count - 1 && Buddy.HDist(me, new Vector3(path[pi].x, me.y, path[pi].y)) < 0.35f) pi++; var wp = path[Math.Min(pi, path.Count - 1)]; var v = new Vector2(wp.x - me.x, wp.y - me.z); AutoPlayer.Move = v.normalized; }
                    else AutoPlayer.Move = Vector2.zero;
                }
                AutoPlayer.Use = dist < 2.3f;
            }
            else if (dist < 0.9f)
            {
                var back = -dir; var nt = Buddy.Tile(me + new Vector3(back.x, 0, back.y) * 0.8f);
                AutoPlayer.Move = Buddy.Free(nt) ? back : Vector2.zero; AutoPlayer.Use = true;
            }
            else { AutoPlayer.Move = Vector2.zero; AutoPlayer.Use = true; }
            return St.Running;
        }
    }

    // run away from the threats for a few seconds (then the heal reflex can fire)
    public class Flee : Task
    {
        readonly float secs; static readonly Vector2[] dirs = { new Vector2(1, 0), new Vector2(-1, 0), new Vector2(0, 1), new Vector2(0, -1), new Vector2(.7f, .7f), new Vector2(.7f, -.7f), new Vector2(-.7f, .7f), new Vector2(-.7f, -.7f) };
        public Flee(float secs) { this.secs = secs; Name = "flee"; Timeout = secs + 2; }
        protected override St Step()
        {
            if (Time.time - Started > secs) return St.Done;
            var me = AutoPlayer.Pos; var away = Vector2.zero;
            foreach (var th in Director.Threats) { var v = new Vector2(me.x - th.pos.x, me.z - th.pos.z); float l = v.magnitude; if (l > 0.1f && l < 10f) away += v / (l * l); }
            if (away.sqrMagnitude < 1e-4f) { Note = "clear"; return St.Done; }
            away.Normalize(); Vector2 best = Vector2.zero; float bs = -9;
            foreach (var dd in dirs)
            {   // prefer directions with a long free run (no dead ends), weighted by "away from the threats"
                int run = 0; for (int k = 1; k <= 4; k++) { if (!Buddy.Free(Buddy.Tile(me + new Vector3(dd.x, 0, dd.y) * (k * 1.1f)))) break; run++; }
                if (run == 0) continue;
                float sc = Vector2.Dot(dd, away) + run * 0.2f;
                if (sc > bs) { bs = sc; best = dd; }
            }
            AutoPlayer.Move = best; AutoPlayer.Aim = -away; AutoPlayer.Use = false;
            return St.Running;
        }
    }

    // eat the first food in the hotbar (right click with it equipped)
    public class Heal : Task
    {
        int slot = -1, held = -1, hp0; float tEat;
        public Heal() { Name = "eat"; Timeout = 6f; }
        internal static bool HasFood() => AutoPlayer.FindHotbar(Goals.Food) >= 0;
        protected override St Step()
        {
            var p = Manager.main.player;
            if (slot < 0) { slot = AutoPlayer.FindHotbar(Goals.Food); if (slot < 0) { Note = "no food"; return St.Failed; } held = p.equippedSlotIndex; hp0 = p.currentHealth; p.EquipSlot(slot); tEat = Time.time + 0.3f; return St.Running; }
            AutoPlayer.Move = Vector2.zero;
            if (Time.time < tEat) return St.Running;
            if (Time.time < tEat + 0.8f) { AutoPlayer.Use2 = true; return St.Running; }
            AutoPlayer.Use2 = false;
            if (Time.time <= tEat + 2f) return St.Running;
            // put the weapon/tool back; count the heal only if hp went up
            if (held >= 0 && held != slot) p.EquipSlot(held);
            if (p.currentHealth > hp0) { Director.Heals++; Note = $"hp {hp0}->{p.currentHealth}"; return St.Done; }
            Note = "no effect"; return St.Failed;
        }
    }

    // down: wait for the respawn, then the goal resumes
    public class Recover : Task
    {
        public Recover() { Name = "recover (respawn)"; Timeout = 180f; }
        protected override St Step()
        {
            var p = Manager.main.player; AutoPlayer.Move = Vector2.zero;
            if (p.currentHealth > 0 && !p.isDyingOrDead && Time.time - Started > 2f) { Note = "back at " + Buddy.Fmt(AutoPlayer.Pos); Buddy.TempBlocked.Clear(); return St.Done; }
            return St.Running;
        }
    }

    public class Wait : Task
    {
        readonly float secs;
        public Wait(float secs) { this.secs = secs; Name = "wait " + secs + "s"; Timeout = secs + 5; }
        protected override St Step() { AutoPlayer.Move = Vector2.zero; return Time.time - Started >= secs ? St.Done : St.Running; }
    }

    // test helper: raw movement in a direction for N seconds, logs how far the player actually got (ground-truth for tile passability)
    public class Push : Task
    {
        readonly Vector2 dir; readonly float secs; Vector3 from;
        public Push(float dx, float dz, float secs) { dir = new Vector2(dx, dz).normalized; this.secs = secs; Name = $"push ({dx},{dz}) {secs}s"; Timeout = secs + 5; }
        protected override St Step()
        {
            if (from == Vector3.zero) from = AutoPlayer.Pos;
            if (Time.time - Started < secs) { AutoPlayer.Move = dir; return St.Running; }
            AutoPlayer.Move = Vector2.zero; var me = AutoPlayer.Pos;
            Note = string.Format(System.Globalization.CultureInfo.InvariantCulture, "moved {0:F2} from ({1:F2},{2:F2}) to ({3:F2},{4:F2}) tile {5}", Buddy.HDist(me, from), from.x, from.z, me.x, me.z, Buddy.Tile(me));
            return St.Done;
        }
    }

    // ---------- the driver ----------
    public class AutoPlayer : MonoBehaviour
    {
        internal static Vector2 Move, Aim = new Vector2(0, -1); internal static bool Use, Use2, Active;
        internal static Vector3 Pos => Manager.main.player.WorldPosition;
        static string dir, inbox, status;
        readonly Queue<(string text, Task goal)> goals = new Queue<(string, Task)>();
        (string text, Task goal) cur; Task reflex; float tPoll, tStatus; long inboxPos;
        readonly List<string> recent = new List<string>();
        static AutoPlayer I;

        internal static void Log(string s) { Plugin.Log.LogInfo("[auto] " + s); if (I != null) { I.recent.Add($"{Time.time:F0}s {s}"); if (I.recent.Count > 12) I.recent.RemoveAt(0); } }

        void Awake()
        {
            I = this;
            dir = Path.Combine(Paths.BepInExRootPath, "ckauto"); Directory.CreateDirectory(dir);
            inbox = Path.Combine(dir, "inbox.txt"); status = Path.Combine(dir, "status.txt");
            File.WriteAllText(inbox, ""); inboxPos = 0; Director.Init(dir);
        }

        void Update()
        {
            var p = Manager.main?.player;
            bool inGame = p != null && Manager.load != null && Manager.load.GetNameOfCurrentScene() == "Main" && Manager.multiMap != null;
            if (Time.time > tPoll) { tPoll = Time.time + 0.5f; PollInbox(); }
            if (!inGame) { Active = false; return; }
            try { Run(); if (Active) Director.Trace(cur.goal?.Name, reflex?.Name); }
            catch (Exception e) { Log("error: " + e.Message); cur = default; reflex = null; Release(); }
            if (Time.time > tStatus) { tStatus = Time.time + 0.5f; try { WriteStatus(); } catch { } }
        }

        static void Release() { Move = Vector2.zero; Use = false; Use2 = false; Active = false; }

        float tHeal, tLoot, tFlee, tReflex;
        void Run()
        {
            Move = Vector2.zero; Use = false; Use2 = false;
            Director.Tick(cur.goal?.Name);
            var p = Manager.main.player; int hp = p.currentHealth, mx = p.GetMaxHealth(); float frac = mx > 0 ? hp / (float)mx : 1f;
            bool busy = cur.goal != null || goals.Count > 0;
            // reflexes (survivor-bot priorities) interrupt the current goal; it resumes afterwards (its timeout clock is paused meanwhile)
            if (busy)
            {
                string gn = cur.goal?.Name ?? "", rn = reflex?.Name ?? "";
                var near = Director.Nearest; float nd = near?.dist ?? 99f; int n4 = Director.Near(4f);
                Task next = null; string why = null;
                // survival checks run every frame and preempt any running reflex (except themselves)
                if ((hp <= 0 || p.isDyingOrDead) && !rn.StartsWith("recover")) { next = new Recover(); why = "down -> wait for respawn"; }
                else if (hp > 0 && frac < 0.35f && nd < 5f && Time.time > tFlee && !rn.StartsWith("flee") && !gn.StartsWith("flee"))
                {   // run, then eat once clear (if there is food); otherwise just run
                    next = Heal.HasFood() ? new Seq("flee + eat", new Flee(3f), new Heal()) : new Flee(3f);
                    tFlee = Time.time + 6f; Director.Flees++; why = $"hp {hp}/{mx} with {near.name} at {nd:F1} -> flee";
                }
                else if (reflex == null)
                {
                    if (frac < 0.5f && nd > 6f && Time.time > tHeal && Heal.HasFood()) { next = new Heal(); tHeal = Time.time + 12f; why = $"hp {hp}/{mx}, clear -> eat"; }
                    else if (!gn.StartsWith("fight") && !gn.StartsWith("defend") && !gn.StartsWith("hold") && !(frac < 0.35f && Heal.HasFood())
                             && (nd < 3.5f || (Director.Phase == "peak" && nd < 6f) || n4 >= 2))
                    { next = Goals.Fight("defend", 99, 7f); why = $"{near.name} at {nd:F1} ({Director.Threats.Count} threats, {Director.Phase}) -> defend"; }
                    else if (nd > 6f && Time.time > tLoot && Director.Drops.Count > 0 && !gn.StartsWith("loot"))
                    {
                        EntityMonoBehaviour d = null; float bd = 7f; foreach (var x in Director.Drops) { float dx = Buddy.HDist(Pos, x.WorldPosition); if (dx < bd) { bd = dx; d = x; } }
                        tLoot = Time.time + 4f;
                        if (d != null) { var t = Buddy.Tile(d.WorldPosition); if (Buddy.Free(t)) { next = new GoTo(t, 0.4f, 12f) { Name = "loot " + NameOf(d) }; why = "loot " + NameOf(d); } }
                    }
                }
                if (next != null)
                {
                    if (reflex != null) { Log("reflex " + reflex.Name + " preempted"); EndReflex(); }
                    reflex = next; tReflex = Time.time; Log("reflex: " + why);
                }
            }
            if (reflex != null)
            {
                Active = true;
                if (reflex.Tick() != St.Running) EndReflex();
                return;
            }
            if (cur.goal == null)
            {
                if (goals.Count == 0) { Active = false; return; }
                cur = goals.Dequeue(); Log("GOAL " + cur.goal.Name + "  <- \"" + cur.text + "\"");
            }
            Active = true;
            var s = cur.goal.Tick();
            if (s != St.Running) { Log("GOAL " + (s == St.Done ? "done: " : "failed: ") + cur.goal.Name + (cur.goal.Note != "" ? " (" + cur.goal.Note + ")" : "")); cur = default; Release(); }
        }

        // a reflex ended: the suspended goal gets the time back
        void EndReflex() { if (reflex != null && cur.goal != null) cur.goal.Shift(Time.time - tReflex); reflex = null; }

        void PollInbox()
        {
            try
            {
                var fi = new FileInfo(inbox); if (!fi.Exists || fi.Length <= inboxPos) { if (fi.Exists && fi.Length < inboxPos) inboxPos = 0; return; }
                string text;
                using (var fs = new FileStream(inbox, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) { fs.Seek(inboxPos, SeekOrigin.Begin); text = new StreamReader(fs).ReadToEnd(); inboxPos = fs.Length; }
                foreach (var line in text.Split('\n').Select(l => l.Trim()).Where(l => l.Length > 0)) Instruct(line);
            }
            catch (Exception e) { Log("inbox: " + e.Message); }
        }

        internal void Instruct(string line)
        {
            Log("instruction: \"" + line + "\"");
            if (line.Trim().ToLowerInvariant() == "probe") { try { var me = Pos; Log(Director.Probe(me, Buddy.Tile(me + new Vector3(2, 0, 0)), new Vector2(1, 0), 0, 0)); } catch (Exception e) { Log("probe: " + e.Message); } return; }
            var parsed = Goals.Parse(line, out var stop, out var errs);
            foreach (var er in errs) Log("didn't get: \"" + er + "\"");
            if (stop) { goals.Clear(); cur = default; reflex = null; Release(); Log("stopped, control back to you"); }
            foreach (var g in parsed) { goals.Enqueue((line, g)); Log("queued goal: " + g.Name); }
        }

        void WriteStatus()
        {
            var p = Manager.main.player; var sb = new StringBuilder();
            sb.AppendLine($"time {Time.time:F0}  active {Active}  pos {Buddy.Fmt(Pos)}  hp {p.currentHealth}/{p.GetMaxHealth()}  held {Hotbar()}");
            sb.AppendLine(Director.Status());
            if (reflex != null) { sb.AppendLine("REFLEX:"); Tree(sb, reflex, 1); }
            sb.AppendLine(cur.goal == null ? "GOAL: (none)" : "GOAL: \"" + cur.text + "\""); if (cur.goal != null) Tree(sb, cur.goal, 1);
            sb.AppendLine("QUEUE: " + (goals.Count == 0 ? "(empty)" : string.Join(" | ", goals.Select(g => g.goal.Name))));
            sb.AppendLine("MAP (# wall, o ore, . floor, ~ water, O object, E enemy, X avoided, @ you, N north up):"); var lk = Manager.multiMap.GetTileLayerLookup(); var pt = Buddy.Tile(Pos);
            for (int dz = 5; dz >= -5; dz--) { sb.Append("  "); for (int dx = -8; dx <= 8; dx++) { var t = pt + new int2(dx, dz);
                char ch = dx == 0 && dz == 0 ? '@' : Buddy.TempBlocked.ContainsKey(t) ? 'X' : Buddy.Occupied.Contains(t) ? 'O' : Director.Threats.Any(th => Buddy.Tile(th.pos).Equals(t)) ? 'E' : lk.HasTile(t, TileType.ore) ? 'o' : lk.HasTile(t, TileType.wall) ? '#' : lk.HasTile(t, TileType.water) ? '~' : Buddy.Walkable(t) ? '.' : ' ';
                sb.Append(ch); } sb.AppendLine(); }
            sb.AppendLine("RECENT:"); foreach (var r in recent) sb.AppendLine("  " + r);
            File.WriteAllText(status, sb.ToString());
        }

        static void Tree(StringBuilder sb, Task t, int depth)
        {
            if (depth > 6) return;
            string mark = t.State == St.Running ? (t.Started < 0 ? "[ ]" : "[>]") : t.State == St.Done ? "[x]" : "[!]";
            sb.Append(' ', depth * 2).Append(mark).Append(' ').Append(t.Name); if (t.Note != "") sb.Append("  -- ").Append(t.Note); sb.AppendLine();
            foreach (var k in t.Kids) Tree(sb, k, depth + 1);
        }

        // ---------- world helpers ----------
        internal static string NameOf(EntityMonoBehaviour e) { try { return e.objectData.objectID.ToString(); } catch { return "something"; } }

        internal static bool IsDiggable(SinglePugMap.TileLayerLookup m, int2 t) => m.HasTile(t, TileType.wall) || m.HasTile(t, TileType.ore);

        internal static string Hotbar()
        {
            var p = Manager.main.player; var l = new List<string>();
            for (int i = p.hotbarStartIndex; i < p.hotbarEndIndex && l.Count < 10; i++)
            {
                try { var id = p.GetInventorySlot(i).objectData.objectID; var info = PugDatabase.GetObjectInfo(id); if (info == null) continue;
                    l.Add((i - p.hotbarStartIndex + 1) + ":" + id + (i == p.equippedSlotIndex ? "*" : "")); } catch { }
            }
            return string.Join(" ", l);
        }

        internal static int FindHotbar(string[] kinds)
        {
            var p = Manager.main.player;
            foreach (var k in kinds) // kinds in order of preference
            for (int i = p.hotbarStartIndex; i < p.hotbarEndIndex; i++)
            {
                try
                {
                    var id = p.GetInventorySlot(i).objectData.objectID; var info = PugDatabase.GetObjectInfo(id); if (info == null) continue;
                    string s = (info.objectType + " " + id).ToLowerInvariant();
                    if (s.Contains(k)) return i;
                }
                catch { }
            }
            return -1;
        }
    }

    // ---------- instruction -> goals -> plans ----------
    public static class Goals
    {
        static readonly System.Random rng = new System.Random();
        internal static readonly string[] Pick = { "miningpick", "pickaxe" }, Weapon = { "meleeweapon", "sword", "rangeweapon", "miningpick", "pickaxe" }, Food = { "eatable" };

        public static List<Task> Parse(string line, out bool stop, out List<string> errs)
        {
            var res = new List<Task>(); errs = new List<string>(); stop = false;
            foreach (var raw in Regex.Split(line.ToLowerInvariant(), @"\s*(?:,|;|\bthen\b|\band then\b|\band\b)\s*"))
            {
                var c = raw.Trim(); if (c == "") continue; Match m;
                if (Regex.IsMatch(c, @"^(stop|cancel|halt|abort|quit)\b")) { stop = true; res.Clear(); continue; }
                if (Regex.IsMatch(c, @"\b(home|core|base|back)\b")) { res.Add(Home("go home")); continue; }
                if ((m = Regex.Match(c, @"\b(?:go|walk|move)\s*(?:to)?\s*(-?\d+)\s+(-?\d+)")).Success) { res.Add(new GoTo(new int2(int.Parse(m.Groups[1].Value), int.Parse(m.Groups[2].Value)), 0.8f, 120f)); continue; }
                if ((m = Regex.Match(c, @"\bexplore\b(?:\D*(\d+))?")).Success) { res.Add(Explore(m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : 5)); continue; }
                if ((m = Regex.Match(c, @"\b(?:mine|dig|get|collect|gather)\b(?:\D*?(\d+))?\s*(.*)$")).Success)
                {
                    int n = m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : 5;
                    string what = Regex.Replace(m.Groups[2].Value, @"\b(some|the|a|of|ore|ores|blocks?|tiles?|veins?|up|me|for)\b", "").Trim();
                    res.Add(Mine(what, n)); continue;
                }
                if ((m = Regex.Match(c, @"\b(?:fight|kill|attack|clear|defend|hunt)\b(?:\D*(\d+))?")).Success) { res.Add(Fight("fight", m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : 99, 9f)); continue; }
                if (Regex.IsMatch(c, @"\b(heal|eat|food)\b")) { res.Add(new Heal()); continue; }
                if (Regex.IsMatch(c, @"\b(flee|run|escape|retreat)\b")) { res.Add(new Flee(4f)); continue; }
                if (Regex.IsMatch(c, @"\b(loot|pick\s*up|pickup)\b")) { res.Add(Loot()); continue; }
                if ((m = Regex.Match(c, @"\bhold\b(?:\D*(\d+))?")).Success) { res.Add(Hold(m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : 30)); continue; }
                if ((m = Regex.Match(c, @"\bwait\b(?:\D*(\d+))?")).Success) { res.Add(new Wait(m.Groups[1].Success ? int.Parse(m.Groups[1].Value) : 5)); continue; }
                if ((m = Regex.Match(c, @"\bpush\s+(-?\d+)\s+(-?\d+)(?:\s+(\d+))?")).Success) { res.Add(new Push(int.Parse(m.Groups[1].Value), int.Parse(m.Groups[2].Value), m.Groups[3].Success ? int.Parse(m.Groups[3].Value) : 2)); continue; }
                errs.Add(c);
            }
            return res;
        }

        public static Task Home(string why)
        {   // the Core sits at (0,0); stand on the nearest walkable tile south of it
            int2 best = new int2(0, -2);
            for (int r = 2; r < 6; r++) { bool f = false; for (int dx = -r; dx <= r && !f; dx++) { var t = new int2(dx, -r); if (Buddy.Walkable(t)) { best = t; f = true; } } if (f) break; }
            return new Seq(why == "go home" ? "go home (core)" : "go home: " + why, new GoTo(best, 1.5f, 180f));
        }

        public static Task Explore(int legs)
        {   // frontier exploration: of random reachable tiles 8-18 away, take the one with most unvisited ground around it
            var seen = new List<int2>();
            return new Repeat($"explore [0/{legs}]", legs, () =>
            {
                var me = Buddy.Tile(AutoPlayer.Pos); var cands = new List<(float s, int2 t)>();
                for (int i = 0; i < 120; i++)
                {
                    float a = (float)(rng.NextDouble() * Math.PI * 2), r = 8 + (float)rng.NextDouble() * 10;
                    var t = me + new int2(Mathf.RoundToInt(Mathf.Cos(a) * r), Mathf.RoundToInt(Mathf.Sin(a) * r));
                    if (!Buddy.Free(t) || seen.Any(s => math.distance((float2)s, (float2)t) < 6)) continue;
                    cands.Add((Director.Frontier(t), t));
                }
                List<int2> bestPartial = null; float bestPS = -1; int nulls = 0, tried = 0;
                foreach (var c in cands.OrderByDescending(c => c.s).Take(12))
                {
                    tried++; var path = Buddy.FindPath(me, c.t, 4000, true); if (path == null) { nulls++; continue; }
                    var end = path[path.Count - 1];
                    if (math.distance((float2)end, (float2)c.t) < 1.5f) { seen.Add(c.t); return new GoTo(c.t, 1f, 45f) { Name = $"goto ({c.t.x},{c.t.y}) frontier {c.s:F0}" }; }
                    float ps = Director.Frontier(end); if (ps > bestPS && math.distance((float2)end, (float2)me) > 4f) { bestPS = ps; bestPartial = path; }
                }
                if (bestPartial != null)
                {   // nothing fully reachable: walk to the far end of the best partial path (new ground anyway)
                    var e = bestPartial[bestPartial.Count - 1]; seen.Add(e); AutoPlayer.Log($"explore: partial leg to ({e.x},{e.y})");
                    return new GoTo(e, 1f, 45f) { Name = $"goto ({e.x},{e.y}) partial {bestPS:F0}" };
                }
                AutoPlayer.Log($"explore: {cands.Count} candidates, {tried} tried, {nulls} unreachable, no partial > 4 tiles");
                if (Buddy.TempBlocked.Count > 0) { Buddy.TempBlocked.Clear(); AutoPlayer.Log("explore: nothing reachable, cleared avoid marks"); }
                return null;
            });
        }

        public static Task Mine(string what, int count)
        {
            bool anyWall = what == "" || Regex.IsMatch(what, @"\b(wall|walls|dirt|stone|rock)\b");
            var failedTiles = new HashSet<int2>();
            string label = anyWall ? "walls" : what + " ore";
            return new Repeat($"mine {label} [0/{count}]", count, () =>
            {
                var target = FindDigTarget(what, anyWall, failedTiles, out var stand);
                if (target == null) return null;
                var t = target.Value; failedTiles.Add(t);
                return new Seq($"mine {OreName(t)} at ({t.x},{t.y})", new Equip(Pick), new GoTo(stand, 0.45f, 40f), new Dig(t));
            });
        }

        // nearest diggable tile of the wanted kind that has a reachable walkable neighbour (4-neighbourhood)
        static int2? FindDigTarget(string what, bool anyWall, HashSet<int2> skip, out int2 stand)
        {
            stand = default; var m = Manager.multiMap.GetTileLayerLookup(); var me = Buddy.Tile(AutoPlayer.Pos);
            var cands = new List<(float d, int2 t)>();
            for (int dx = -20; dx <= 20; dx++) for (int dz = -20; dz <= 20; dz++)
            {
                var t = me + new int2(dx, dz); if (skip.Contains(t)) continue;
                bool ok = anyWall ? m.HasTile(t, TileType.wall) && !m.HasTile(t, TileType.ore) : m.HasTile(t, TileType.ore) && (what == "" || OreName(t).Contains(what));
                if (ok) cands.Add((dx * dx + dz * dz, t));
            }
            int2[] n4 = { new int2(1, 0), new int2(-1, 0), new int2(0, 1), new int2(0, -1) };
            foreach (var c in cands.OrderBy(c => c.d).Take(25))
                foreach (var o in n4)
                {
                    var s = c.t + o; if (!Buddy.Walkable(s)) continue;
                    if (Buddy.FindPath(me, s, 4000) == null) continue;
                    stand = s; return c.t;
                }
            return null;
        }

        static string OreName(int2 t)
        {
            var m = Manager.multiMap.GetTileLayerLookup();
            for (int ts = 0; ts < 64; ts++)
                if (m.HasTile(t, TileType.ore, ts)) return ((Tileset)ts).ToString().ToLowerInvariant();
            return m.HasTile(t, TileType.ore) ? "ore" : "wall";
        }

        public static EntityMonoBehaviour NearestEnemy(float radius)
        {
            var me = AutoPlayer.Pos; EntityMonoBehaviour best = null; float bd = radius;
            foreach (var e in UnityEngine.Object.FindObjectsOfType<EntityMonoBehaviour>())
            {
                try
                {
                    if (!e.isEnemy || e.currentHealth <= 0) continue;
                    float d = Buddy.HDist(me, e.WorldPosition); if (d < bd) { bd = d; best = e; }
                }
                catch { }
            }
            return best;
        }

        public static Task Fight(string name, int count, float radius)
        {
            return new Seq($"{name} [{(count >= 99 ? "all" : count + " kills")}]", new Equip(Weapon), new Combat(radius, count));
        }

        public static Task Loot()
        {
            return new Repeat("loot [0/6]", 6, () =>
            {
                EntityMonoBehaviour best = null; float bd = 12f;
                foreach (var d in Director.Drops) { float x = Buddy.HDist(AutoPlayer.Pos, d.WorldPosition); if (x < bd) { bd = x; best = d; } }
                if (best == null) return null;
                return new GoTo(Buddy.Tile(best.WorldPosition), 0.4f, 15f) { Name = "loot " + AutoPlayer.NameOf(best) };
            });
        }

        // stand here and fight whatever comes for N seconds (hold position)
        public static Task Hold(int secs)
        {
            // position and clock are taken when the hold STARTS, not when the line is parsed (run 26: parsed 5 min earlier -> expired at once, "0/999")
            int2 at = default; float until = -1;
            return new Repeat($"hold {secs}s", 999, () =>
            {
                if (until < 0) { at = Buddy.Tile(AutoPlayer.Pos); until = Time.time + secs; AutoPlayer.Log($"hold at ({at.x},{at.y}) for {secs}s"); }
                if (Time.time > until) return null;
                if (Director.TopWithin(6f) != null) return new Seq("engage", new Equip(Weapon), new Combat(7f, 99));
                if (Buddy.HDist(AutoPlayer.Pos, new Vector3(at.x, 0, at.y)) > 1.5f) return new GoTo(at, 0.7f, 20f);
                return new Wait(1f);
            }) { Timeout = secs + 60 };
        }
    }

    // ---------- input injection ----------
    [HarmonyPatch]
    public static class AutoInputPatches
    {
        [HarmonyPatch(typeof(PlayerInput), nameof(PlayerInput.GetInputAxisValue), new[] { typeof(PlayerInput.InputAxisType), typeof(PlayerInput.InputAxisType) })]
        [HarmonyPrefix]
        static bool Axis2(PlayerInput.InputAxisType horizontalAxisType, ref Vector2 __result)
        {
            if (!AutoPlayer.Active) return true;
            if (horizontalAxisType == PlayerInput.InputAxisType.CHARACTER_MOVEMENT_HORIZONTAL) { __result = AutoPlayer.Move; return false; }
            if (horizontalAxisType == PlayerInput.InputAxisType.CHARACTER_AIM_HORIZONTAL) { __result = AutoPlayer.Aim; return false; }
            return true;
        }

        [HarmonyPatch(typeof(PlayerInput), nameof(PlayerInput.IsButtonCurrentlyDown))]
        [HarmonyPrefix]
        static bool Down(PlayerInput.InputType inputType, ref bool __result)
        {
            if (!AutoPlayer.Active) return true;
            if (inputType == PlayerInput.InputType.INTERACT) { __result = AutoPlayer.Use; return false; }
            if (inputType == PlayerInput.InputType.SECOND_INTERACT) { __result = AutoPlayer.Use2; return false; }
            return true;
        }

        static bool lastUse, lastUse2;
        [HarmonyPatch(typeof(PlayerInput), nameof(PlayerInput.WasButtonPressedDownThisFrame))]
        [HarmonyPrefix]
        static bool Pressed(PlayerInput.InputType inputType, ref bool __result)
        {
            if (!AutoPlayer.Active) return true;
            if (inputType == PlayerInput.InputType.INTERACT) { __result = AutoPlayer.Use && !lastUse; lastUse = AutoPlayer.Use; return false; }
            if (inputType == PlayerInput.InputType.SECOND_INTERACT) { __result = AutoPlayer.Use2 && !lastUse2; lastUse2 = AutoPlayer.Use2; return false; }
            return true;
        }

        [HarmonyPatch(typeof(PlayerInput), nameof(PlayerInput.PrefersKeyboardAndMouse))]
        [HarmonyPrefix]
        static bool Kbm(ref bool __result) { if (!AutoPlayer.Active) return true; __result = false; return false; }
    }
}
