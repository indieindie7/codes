// Director: Left-4-Dead-style survivor-bot layer for the AutoPlayer.
//  - threat board (enemies scored by size / distance, boss weight), nearest drops
//  - pacing ("AI director"): intensity from damage taken + enemies near, phases relax -> buildup -> peak -> fade
//  - occupancy map from placed objects (stations, chests, fences) so A* avoids them
//  - visited map for frontier exploration, danger cost near enemies for A*
//  - telemetry csv (BepInEx\ckauto\telemetry.csv) for long unattended tests
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Unity.Mathematics;
using UnityEngine;
using PugTilemap;

namespace CKCompanion
{
    public static class Director
    {
        public class Threat { public EntityMonoBehaviour e; public float dist, score; public int hp, max; public string name; public Vector3 pos; public bool boss; }
        public static readonly List<Threat> Threats = new List<Threat>();
        public static Threat Top => Threats.Count > 0 ? Threats[0] : null;
        public static Threat Nearest { get { Threat b = null; foreach (var t in Threats) if (b == null || t.dist < b.dist) b = t; return b; } }
        public static int Near(float r) { int n = 0; foreach (var t in Threats) if (t.dist < r) n++; return n; }
        public static Threat TopWithin(float r) { foreach (var t in Threats) if (t.dist <= r) return t; return null; }

        public static float Intensity; public static string Phase = "relax";
        public static int Deaths, Stucks, Repaths, Kills, Heals, Flees; public static float DamageTaken, LastHurt = -999f, LastDeath = -999f;
        public static readonly HashSet<int2> Visited = new HashSet<int2>();
        static readonly List<EntityMonoBehaviour> drops = new List<EntityMonoBehaviour>();
        public static IReadOnlyList<EntityMonoBehaviour> Drops => drops;

        static float lastHp = -1, tPeakEnd, tEnts, tOcc, tVisit, tTele; static EntityMonoBehaviour[] ents = new EntityMonoBehaviour[0];
        static string teleFile;

        public static void Init(string dir)
        {
            teleFile = Path.Combine(dir, "telemetry.csv"); traceFile = Path.Combine(dir, "trace.csv"); File.WriteAllText(traceFile, "t,x,z,mx,my,goal,reflex\n");
            File.WriteAllText(teleFile, "t,x,z,hp,max,intensity,phase,enemies,near4,goal,deaths,stucks,repaths,kills,heals,flees,damage,visited\n");
            Buddy.ExtraCost = Danger;
        }

        public static void Tick(string goalName)
        {
            var p = Manager.main.player; float now = Time.time; var pos = AutoPlayer.Pos;
            int hp = p.currentHealth, mx = p.GetMaxHealth();
            if (lastHp >= 0 && hp < lastHp && hp > 0) { DamageTaken += lastHp - hp; Intensity += (lastHp - hp) / (float)Math.Max(1, mx) * 150f; LastHurt = now; }
            if (lastHp > 0 && hp <= 0) { Deaths++; LastDeath = now; Intensity = 100; AutoPlayer.Log($"DIED at {Buddy.Fmt(pos)} (death {Deaths})"); }
            lastHp = hp;
            if (now > tEnts) { tEnts = now + 0.4f; ents = UnityEngine.Object.FindObjectsOfType<EntityMonoBehaviour>(); Scan(); }
            Intensity += Near(6f) * 3f * Time.deltaTime - 4f * Time.deltaTime; Intensity = Mathf.Clamp(Intensity, 0, 100);
            string ph = Phase;
            if (Phase == "relax" && Intensity > 25) ph = "buildup";
            else if (Phase == "buildup" && Intensity > 60) { ph = "peak"; tPeakEnd = now + 8f; }
            else if (Phase == "buildup" && Intensity < 8) ph = "relax";
            else if (Phase == "peak" && now > tPeakEnd && Intensity < 45) ph = "fade";
            else if (Phase == "fade" && Intensity < 12) ph = "relax";
            if (ph != Phase) { AutoPlayer.Log($"director: {Phase} -> {ph} (intensity {Intensity:F0}, {Threats.Count} threats)"); Phase = ph; }
            if (now > tVisit) { tVisit = now + 0.4f; var t = Buddy.Tile(pos); for (int dx = -2; dx <= 2; dx++) for (int dz = -2; dz <= 2; dz++) Visited.Add(t + new int2(dx, dz)); }
            if (now > tOcc) { tOcc = now + 2f; Occupancy(pos); }
            if (now > tTele)
            {
                tTele = now + 5f;
                try { File.AppendAllText(teleFile, string.Format(CultureInfo.InvariantCulture, "{0:F0},{1:F1},{2:F1},{3},{4},{5:F0},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17}\n",
                    now, pos.x, pos.z, hp, mx, Intensity, Phase, Threats.Count, Near(4f), (goalName ?? "").Replace(',', ' '), Deaths, Stucks, Repaths, Kills, Heals, Flees, DamageTaken, Visited.Count)); } catch { }
            }
        }

        static void Scan()
        {
            Threats.Clear(); drops.Clear(); var me = AutoPlayer.Pos; var pl = Manager.main.player;
            foreach (var e in ents)
            {
                if (e == null || e == pl) continue;
                try
                {
                    if (!e.isActiveAndEnabled) continue;
                    var w = e.WorldPosition; float d = Buddy.HDist(me, w);
                    if (e.isEnemy)
                    {
                        if (d > 16) continue; int h = e.currentHealth; if (h <= 0) continue; int m = e.GetMaxHealth(); bool boss = m >= 1500;
                        float sc = (1f + m / 100f) * (boss ? 3f : 1f) / Mathf.Max(0.5f, d);
                        Threats.Add(new Threat { e = e, dist = d, score = sc, hp = h, max = m, name = AutoPlayer.NameOf(e), pos = w, boss = boss });
                    }
                    else if (d < 8 && e.GetType().Name.IndexOf("Drop", StringComparison.Ordinal) >= 0) drops.Add(e);
                }
                catch { }
            }
            Threats.Sort((a, b) => b.score.CompareTo(a.score));
        }

        // tiles under static entities that carry a physics collider near the player (chests, stations, fences, root plants...);
        // run 29: "PlaceablePrefab only" missed a RootPlant/NonObtainable (+col) that blocked the spawn pocket exit and counted
        // collider-less placeables near home (paths there were found only with IgnoreOccupied). Ground torches stay walkable.
        static void Occupancy(Vector3 me)
        {
            var occ = new HashSet<int2>();
            foreach (var e in ents)
            {
                if (e == null) continue;
                try
                {
                    if (!e.isActiveAndEnabled || e.isEnemy) continue;
                    var info = e.objectInfo; if (info == null) continue;
                    var ot = info.objectType; if (ot == ObjectType.Critter || ot == ObjectType.Pet || ot == ObjectType.PlayerType || ot == ObjectType.Creature) continue;
                    var tn = e.GetType().Name; if (tn.IndexOf("Drop", StringComparison.Ordinal) >= 0) continue;
                    if (tn.IndexOf("Door", StringComparison.Ordinal) >= 0) continue; // WoodDoor/ElectricalDoor... open for the player (run 30: base doors over-blocked home)
                    var w = e.WorldPosition; if (Buddy.HDist(me, w) > 40) continue;
                    if (!EntityUtility.HasComponentData<Unity.Physics.PhysicsCollider>(e.entity, e.world)) continue;
                    if (info.prefabTileSize.x <= 1 && info.prefabTileSize.y <= 1 && info.objectID.ToString().IndexOf("Torch", StringComparison.Ordinal) >= 0) continue;
                    foreach (var t in Footprint(e, info)) occ.Add(t);
                }
                catch { }
            }
            Buddy.Occupied = occ;
        }

        // tiles under an entity the way the game computes them (DestroyEntityIfNotOnTileSystem): base = round(position), offset/size rotated by DirectionCD
        static List<int2> Footprint(EntityMonoBehaviour e, ObjectInfo info)
        {
            EntityUtility.GetPrefabSizeAndOffset(e.entity, info, out var size, out var offset);
            var b = Buddy.Tile(e.WorldPosition); var list = new List<int2>();
            for (int i = offset.x; i < offset.x + Math.Max(1, size.x); i++) for (int j = offset.y; j < offset.y + Math.Max(1, size.y); j++) list.Add(b + new int2(i, j));
            return list;
        }

        // GoTo bumped into something at waypoint wp (not in the tile map, not a PlaceablePrefab): remember the footprints of the
        // static non-enemy entities around it so A* avoids them from now on. Returns "objectID/type,..." for the log.
        public static string LearnBlockers(int2 wp, int2 mt)
        {
            var names = new List<string>(); var c = new Vector3(wp.x, 0, wp.y); var pl = Manager.main.player;
            foreach (var e in ents)
            {
                if (e == null || e == pl) continue;
                try
                {
                    if (!e.isActiveAndEnabled || e.isEnemy) continue;
                    var info = e.objectInfo; if (info == null) continue;
                    var ot = info.objectType; if (ot == ObjectType.Critter || ot == ObjectType.Pet || ot == ObjectType.PlayerType || ot == ObjectType.Creature) continue;
                    if (e.GetType().Name.IndexOf("Drop", StringComparison.Ordinal) >= 0) continue;
                    if (Buddy.HDist(c, e.WorldPosition) > 1.6f) continue;
                    int n = 0; foreach (var t in Footprint(e, info)) if (!t.Equals(mt)) { Buddy.Learned.Add(t); n++; }
                    if (n > 0) names.Add($"{info.objectID}/{ot}");
                }
                catch { }
            }
            return string.Join(",", names.Distinct().Take(4));
        }

        static float Danger(int2 t)
        {
            float c = 0;
            foreach (var th in Threats) { float d = math.distance((float2)t, new float2(th.pos.x, th.pos.z)); if (d < 3f) c += (3f - d) * 2f; }
            return c;
        }

        // frontier score: unvisited free tiles around t (7x7); flow = farther from the core is new ground
        public static float Frontier(int2 t)
        {
            int n = 0; for (int dx = -3; dx <= 3; dx++) for (int dz = -3; dz <= 3; dz++) { var u = t + new int2(dx, dz); if (!Visited.Contains(u) && Buddy.Free(u)) n++; }
            return n + 0.15f * math.length((float2)t);
        }

        // a tile near `from`, away from the threats, with few open neighbours (a corridor mouth) to fight in
        public static int2? Chokepoint(Vector3 from)
        {
            var me = Buddy.Tile(from); float2 away = float2.zero;
            foreach (var th in Threats) { var v = new float2(from.x - th.pos.x, from.z - th.pos.z); float l = math.length(v); if (l > 0.1f) away += v / (l * l); }
            int2? best = null; float bs = -1;
            for (int dx = -6; dx <= 6; dx++) for (int dz = -6; dz <= 6; dz++)
            {
                var t = me + new int2(dx, dz); if (!Buddy.Free(t)) continue;
                int open = 0; for (int ox = -1; ox <= 1; ox++) for (int oz = -1; oz <= 1; oz++) if ((ox != 0 || oz != 0) && Buddy.Free(t + new int2(ox, oz))) open++;
                if (open > 4) continue;
                float s = (8 - open) + math.dot(math.normalizesafe(away), math.normalizesafe(new float2(dx, dz))) * 4f - math.length(new float2(dx, dz)) * 0.3f;
                if (s > bs && Buddy.LineFree(me, t)) { bs = s; best = t; }
            }
            return best;
        }

        // one line of ground truth when GoTo is stuck: tiles under/ahead/at the waypoint and the entities around the player
        public static string Probe(Vector3 me, int2 wp, Vector2 d, int pi, int n)
        {
            var sb = new System.Text.StringBuilder(); var m = Manager.multiMap.GetTileLayerLookup();
            var mt = Buddy.Tile(me); var dn = d.normalized; var nt = Buddy.Tile(me + new Vector3(dn.x, 0, dn.y) * 0.7f);
            sb.Append(string.Format(CultureInfo.InvariantCulture, "probe me ({0:F2},{1:F2}) wp ({2},{3}) d ({4:F2},{5:F2}) pi {6}/{7} | ", me.x, me.z, wp.x, wp.y, d.x, d.y, pi, n));
            foreach (var t in new[] { mt, nt, wp })
            {
                var top = m.GetTopTileAndCheckWater(t, out bool hasWater);
                sb.Append($"({t.x},{t.y}) top {top.tileType}/{top.tileset}{(hasWater ? "+water" : "")} walk {Buddy.Walkable(t)} free {Buddy.Free(t)} occ {Buddy.Occupied.Contains(t)} learned {Buddy.Learned.Contains(t)} [");
                foreach (TileType tt2 in Enum.GetValues(typeof(TileType))) if (tt2 != TileType.none && m.HasTile(t, tt2)) sb.Append(tt2).Append(' ');
                sb.Append("] ");
            }
            var census = new Dictionary<TileType, int>();
            for (int dx = -3; dx <= 3; dx++) for (int dy = -3; dy <= 3; dy++) { var tt = m.GetTopTile(mt + new int2(dx, dy)).tileType; census[tt] = census.TryGetValue(tt, out var c) ? c + 1 : 1; }
            sb.Append("| top7x7 "); foreach (var kv in census.OrderByDescending(k => k.Value)) sb.Append(kv.Key).Append(':').Append(kv.Value).Append(' ');
            sb.Append("| grid (N up; #wall R root P pit ~water F fence o ore . ground , floor/other x none, lower-case = not Free, @ me):");
            for (int dy = 7; dy >= -7; dy--)
            {
                sb.Append(" | ");
                for (int dx = -7; dx <= 7; dx++)
                {
                    var t = mt + new int2(dx, dy); var tt = m.GetTopTile(t).tileType; char ch;
                    switch (tt) { case TileType.wall: case TileType.greatWall: case TileType.thinWall: ch = '#'; break; case TileType.bigRoot: ch = 'R'; break; case TileType.pit: ch = 'P'; break; case TileType.water: ch = '~'; break; case TileType.fence: ch = 'F'; break; case TileType.ore: ch = 'o'; break; case TileType.none: ch = 'x'; break; case TileType.ground: case TileType.dugUpGround: case TileType.wateredGround: ch = '.'; break; default: ch = ','; break; }
                    if (dx == 0 && dy == 0) ch = '@'; else if (Buddy.Walkable(t) && !Buddy.Free(t)) ch = 'e';
                    sb.Append(ch);
                }
            }
            sb.Append(" | ents ");
            foreach (var e in ents)
            {
                if (e == null || e == Manager.main.player) continue;
                try
                {
                    if (!e.isActiveAndEnabled) continue; var w = e.WorldPosition; float dist = Buddy.HDist(me, w); if (dist > 1.5f) continue;
                    var info = e.objectInfo; bool col = EntityUtility.HasComponentData<Unity.Physics.PhysicsCollider>(e.entity, e.world);
                    sb.Append(string.Format(CultureInfo.InvariantCulture, "{0}/{1}@({2:F1},{3:F1}){4}{5} ", info?.objectID, info?.objectType, w.x, w.z, col ? "+col" : "", e.isEnemy ? "+enemy" : ""));
                }
                catch (Exception ex) { sb.Append("err:" + ex.GetType().Name + " "); }
            }
            return sb.ToString();
        }

        static float tTrace; static string traceFile;
        public static void Trace(string goal, string reflex)
        {
            if (Time.time < tTrace) return; tTrace = Time.time + 0.25f; var pos = AutoPlayer.Pos;
            try { File.AppendAllText(traceFile, string.Format(CultureInfo.InvariantCulture, "{0:F2},{1:F2},{2:F2},{3:F2},{4:F2},{5},{6}\n", Time.time, pos.x, pos.z, AutoPlayer.Move.x, AutoPlayer.Move.y, goal, reflex)); } catch { }
        }

        public static string Status()
        {
            var top = Top;
            return $"DIRECTOR: phase {Phase} intensity {Intensity:F0} threats {Threats.Count} (near4 {Near(4f)}) top {(top == null ? "-" : top.name + " " + top.hp + "/" + top.max + " @" + top.dist.ToString("F1", CultureInfo.InvariantCulture))} | deaths {Deaths} stucks {Stucks} repaths {Repaths} kills {Kills} heals {Heals} flees {Flees} dmg {DamageTaken} visited {Visited.Count}";
        }
    }
}
