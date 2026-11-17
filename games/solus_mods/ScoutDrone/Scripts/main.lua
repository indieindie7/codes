-- ScoutDrone: a small scanning-ball drone that follows the player and points out
-- useful items the player walked past without looking at.
-- Fair play: the drone only knows items it has seen itself (range + line of sight
-- from the drone). "Not looked at" = the game's own per-item flag
-- HasEverBeenViewedOrUsed (set when the player looks at / uses the item).

-- Log + selftest.flag folder. If it does not exist the mod runs without a log.
local ROOT = "C:/re/projectsolus/"
local LOG = ROOT .. "scoutdrone_log.txt"
local CFG = {
  sense_r = 2500,      -- drone sensor range (uu)
  scan_s = 0.5,        -- scan period
  near = 1200,         -- player counted as "passing" an item inside this
  far = 1700,          -- ...and as having walked past once beyond this
  linger_s = 25,       -- unviewed item this close for this long -> also hint
  linger_r = 1000,
  guide_max_s = 40,
  cooldown_s = 15,
  leash = 3500,        -- drone never goes further than this from the player
  speed = 900,         -- uu/s
  follow_up = 110,     -- above the player's feet origin (eye ~60): sits in the upper half of the view
  ahead = 520,         -- scout post: this far (+0..200) along the player's WALKING direction, not the view
  cruise = 420,        -- calm speed while scouting (guide flights use speed)
  post_far = 1100,     -- post further than this from the player -> pick a new one
  unseen_s = 6,        -- out of the player's view this long -> drift to a spot in view
  hover_up = 110,
}
-- ItemTypes enum values worth pointing out (others: rocks, unknown, NewEnumeratorN)
local USEFUL = {
  [1]="torch",[2]="torch",[3]="torch",[4]="torch",[5]="metal",[6]="light crystal",[8]="sharp rock",
  [11]="pipe",[12]="coconut",[13]="cabbage",[14]="water bottle",[15]="water bottle",[16]="empty bottle",
  [17]="food can",[18]="food can",[20]="roots",[21]="heat crystal",[22]="ice crystal",[23]="rope",
  [24]="satellite piece",[25]="flashlight",[26]="lighter",
}
local FOOD = {[12]=1,[13]=1,[17]=1,[18]=1,[20]=1}
local WATER = {[14]=1,[15]=1,[16]=1,[12]=1}

local lf = io.open(LOG, "a")
local DT = 0.016
local NOW = 0  -- game-loop seconds (ticks x dt); os.clock is CPU time, not wall time
local function log(s) if not lf then return end; lf:write(string.format("[%7.1f] %s\n", NOW, s)); lf:flush() end
log("ScoutDrone loaded " .. os.date())

local BC = false; do local f = io.open(ROOT .. "selftest.flag", "r"); if f then BC = (f:read("a") or ""):find("bc") ~= nil; f:close() end end
local function bc(x) if BC then log("  . " .. x) end end
local VIS = false; do local f = io.open(ROOT .. "selftest.flag", "r"); if f then VIS = (f:read("a") or ""):find("vis") ~= nil; f:close() end end
local SHOT = false; do local f = io.open(ROOT .. "selftest.flag", "r"); if f then SHOT = (f:read("a") or ""):find("shot") ~= nil; f:close() end end
local S = { drone = nil, light = nil, known = {}, items = {}, items_t = -99, scan_t = 0,
            mode = "follow", target = nil, guide_t = 0, cool_t = -99, pos = nil, time = 0,
            hint_n = 0, seen_n = 0 }
local ksl, gs, world, mesh, cue

local function V(x, y, z) return {X = x, Y = y, Z = z} end
local function dist(a, b) return math.sqrt((a.X-b.X)^2 + (a.Y-b.Y)^2 + (a.Z-b.Z)^2) end
local function valid(o) return o ~= nil and o:IsValid() end
local function key(it) return it:GetFName():ToString() end

-- Body (user 11-17, refs: shell-ball drone, fan orb, twin-lens desk lamp): "a ball with a lamp on top that has some
-- kind of eyes". Own design. Engine basic shapes (100 uu each). off = offset from drone centre (uu, before G, +X = front),
-- sc = scale, col = colour, pitch 90 = cylinder axis points forward. Parts turn with the drone (S.yaw).
local G = 0.6
local SHELL, DARK, STEEL, EYE = {R=0.80, G=0.80, B=0.78, A=1}, {R=0.03, G=0.03, B=0.035, A=1}, {R=0.35, G=0.36, B=0.38, A=1}, {R=1.0, G=0.97, B=0.85, A=1}
local PARTS = {
  {m="Sphere",   off={0, 0, 0},      sc={0.90, 0.90, 0.90}, col=SHELL},            -- ball (root)
  {m="Cylinder", off={0, 0, -2},     sc={0.93, 0.93, 0.06}, col=DARK},             -- equator seam
  {m="Sphere",   off={0, 0, -9},     sc={0.84, 0.84, 0.84}, col=DARK},             -- dark underside
  {m="Cylinder", off={0, 0, -44},    sc={0.42, 0.42, 0.10}, col=STEEL},            -- fan duct
  {m="Sphere",   off={40, 0, 4},     sc={0.16, 0.16, 0.16}, col=DARK},             -- body camera
  {m="Cylinder", off={-6, 0, 46},    sc={0.20, 0.20, 0.06}, col=STEEL},            -- lamp base
  {m="Cylinder", off={-6, 0, 62},    sc={0.06, 0.06, 0.30}, col=STEEL},            -- lamp arm
  {m="Sphere",   off={-6, 0, 78},    sc={0.12, 0.12, 0.12}, col=STEEL},            -- arm joint
  {m="Cylinder", off={4, 14, 84},    sc={0.27, 0.27, 0.16}, col=STEEL, pitch=90},  -- lamp cup L
  {m="Cylinder", off={4, -14, 84},   sc={0.27, 0.27, 0.16}, col=STEEL, pitch=90},  -- lamp cup R
  {m="Cylinder", off={12.5, 14, 84}, sc={0.22, 0.22, 0.02}, col=EYE, pitch=90},    -- eye L
  {m="Cylinder", off={12.5, -14, 84},sc={0.22, 0.22, 0.02}, col=EYE, pitch=90},    -- eye R
  {m="Sphere",   off={13.5, 14, 84}, sc={0.08, 0.08, 0.08}, col=DARK},             -- pupil L
  {m="Sphere",   off={13.5, -14, 84},sc={0.08, 0.08, 0.08}, col=DARK},             -- pupil R
}
local LAMP = {26, 0, 84}   -- point light sits just in front of the eyes
local SHAPE, shape_mat, kml = {}, nil, nil

local function load_assets()
  for _, n in ipairs({"Cylinder", "Sphere", "Cube"}) do
    local pth = "/Engine/BasicShapes/" .. n .. "." .. n
    pcall(LoadAsset, pth); local o = StaticFindObject(pth)
    if valid(o) then SHAPE[n] = o end
    log("shape " .. n .. " " .. tostring(valid(o)))
  end
  local mpth = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"
  pcall(LoadAsset, mpth); shape_mat = StaticFindObject(mpth)
  kml = StaticFindObject("/Script/Engine.Default__KismetMaterialLibrary")
  log("shape material " .. tostring(valid(shape_mat)) .. " kml " .. tostring(valid(kml)))
  ksl = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
  gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
  local mp = "/Game/Environment/Intelligence/Meshes/SM_Intelligence_ScanningBall.SM_Intelligence_ScanningBall"
  LoadAsset(mp); mesh = StaticFindObject(mp)
end

-- Never keep an asset pointer across frames: nothing references the cue, so engine GC frees it (~60 s) and the stale
-- pointer crashed the game at the first real hint (user play 11-17, access violation). Resolve it at each use.
local CUE_PATH = "/Game/Sounds/AI/Wav/SO_DroneIdle_Cue.SO_DroneIdle_Cue"
local function get_cue()
  local c = StaticFindObject(CUE_PATH)
  if not valid(c) then pcall(LoadAsset, CUE_PATH); c = StaticFindObject(CUE_PATH) end
  return valid(c) and c or nil
end

local function spawn(pawn)
  world = FindFirstOf("World")
  if not valid(world) then return false end
  if not ksl then load_assets() end
  local L = pawn:K2_GetActorLocation()
  local p = V(L.X - 150, L.Y, L.Z + CFG.follow_up)
  local d = world:SpawnActor(StaticFindObject("/Script/Engine.StaticMeshActor"), p, {Pitch=0, Yaw=0, Roll=0})
  if not valid(d) then log("spawn failed"); return false end
  local c = d.StaticMeshComponent
  c.Mobility = 2
  pcall(function() c:SetCollisionEnabled(0) end)
  pcall(function() c:SetCastShadow(true) end)
  S.parts = {}
  if SHAPE.Cylinder and SHAPE.Sphere and SHAPE.Cube then
    local col_ok = 0
    for i, pt in ipairs(PARTS) do
      local a = (i == 1) and d or world:SpawnActor(StaticFindObject("/Script/Engine.StaticMeshActor"), p, {Pitch = pt.pitch or 0, Yaw = 0, Roll = 0})
      if valid(a) then
        local pc_ = a.StaticMeshComponent
        pc_.Mobility = 2
        pcall(function() pc_:SetStaticMesh(SHAPE[pt.m]) end)
        pcall(function() pc_:SetCollisionEnabled(0) end)
        a:SetActorScale3D(V(pt.sc[1] * G, pt.sc[2] * G, pt.sc[3] * G))
        local okc = pcall(function()
          local mid = kml:CreateDynamicMaterialInstance(world, shape_mat)
          mid:SetVectorParameterValue(FName("Color"), pt.col)
          pc_:SetMaterial(0, mid)
        end)
        if okc then col_ok = col_ok + 1 end
        if i > 1 then S.parts[#S.parts + 1] = {a = a, off = pt.off, pitch = pt.pitch or 0} end
      end
    end
    log(string.format("body parts %d coloured %d", #S.parts + 1, col_ok))
  else
    pcall(function() c:SetStaticMesh(mesh) end)
    d:SetActorScale3D(V(0.35, 0.35, 0.35))
    log("saucer shapes missing, ball fallback")
  end
  local l = world:SpawnActor(StaticFindObject("/Script/Engine.PointLight"), p, {Pitch=0, Yaw=0, Roll=0})
  if valid(l) then
    local lc = l.LightComponent
    lc.Mobility = 2
    pcall(function() lc:SetIntensity(800) end)
    pcall(function() lc:SetAttenuationRadius(450) end)
    pcall(function() lc:SetLightColor({R=0.4, G=0.8, B=1.0, A=1}, true) end)
    pcall(function() lc:SetCastShadows(false) end)
  end
  S.drone, S.light, S.pos = d, l, p
  S.known, S.mode, S.target = {}, "follow", nil
  S.yaw, S.post, S.pp, S.head_x, S.head_y, S.unseen_t = 0, nil, nil, nil, nil, 0
  log(string.format("drone spawned at %.0f %.0f %.0f mesh=%s light=%s", p.X, p.Y, p.Z, tostring(valid(mesh)), tostring(valid(l))))
  return true
end

-- line of sight from the drone; true when nothing but the item blocks the line
local function los(from, it)
  bc("los " .. key(it))
  local P = it:K2_GetActorLocation()
  local hit = {}
  local ok, r = pcall(function()
    return ksl:LineTraceSingle(world, from, P, 0, false, {S.drone, S.light}, 0, hit, true,
      {R=0,G=0,B=0,A=0}, {R=0,G=0,B=0,A=0}, 0)
  end)
  if not ok then return false end
  if not r then return true end
  local ha; pcall(function() ha = hit.Actor:Get() end)
  if ha and valid(ha) and ha:GetAddress() == it:GetAddress() then return true end
  local hd = 0; pcall(function() hd = hit.Distance end)
  return hd > dist(from, P) - 40
end

local function item_ok(it)
  if not valid(it) then return false end
  local ok, good = pcall(function()
    if not USEFUL[it.ItemType] then return false end
    if it.HasEverBeenViewedOrUsed then return false end
    if it.HeldByPlayer ~= 0 or it.bHidden then return false end
    if it.iamaplantandhasbeenpickedup then return false end
    local o, p = it.OriginalLocation.Translation, it:K2_GetActorLocation()  -- OriginalLocation is an FTransform
    if o and dist(o, p) > 60 then return false end
    return true
  end)
  return ok and good
end

local function need(kind)
  local lib = StaticFindObject("/Script/Solus.Default__SolusStatsLibrary")
  local ok, v = pcall(function()
    if kind == "food" then return lib:SolusStats__TimeSinceLastAte() end
    return lib:SolusStats__TimeSinceLastDrank()
  end)
  return ok and tonumber(v) or 0
end

local function scan(pawn)
  if S.time - S.items_t > 3 then
    S.items = FindAllOf("Item_Standard_C") or {}; S.items_t = S.time
  end
  local D = S.drone:K2_GetActorLocation()
  local Pp = pawn:K2_GetActorLocation()
  for _, it in ipairs(S.items) do
    if item_ok(it) then
      local k = key(it); local P = it:K2_GetActorLocation()
      local m = S.known[k]
      if not m and dist(D, P) < CFG.sense_r and los(D, it) then
        m = {it = it, type = it.ItemType, seen_t = S.time, near = false, near_t = nil, done = false}
        S.known[k] = m; S.seen_n = S.seen_n + 1
        log(string.format("saw %s (%s) at %.0f from drone (drone %.0f %.0f %.0f), LOS ok", k, USEFUL[m.type], dist(D, P), D.X, D.Y, D.Z))
      end
      if m then
        local dp = dist(Pp, P)
        if dp < CFG.near then m.near = true; m.near_t = m.near_t or S.time end
        if dp >= CFG.near then m.near_t = nil end
        m.passed = m.near and dp > CFG.far and dp < CFG.leash
        m.linger = m.near_t and (S.time - m.near_t) > CFG.linger_s and dp < CFG.linger_r
      end
    else
      local k = valid(it) and key(it)
      if k and S.known[k] then S.known[k] = nil end
    end
  end
end

local function pick(pawn)
  local best, bs = nil, -1
  local hunger, thirst = need("food"), need("water")
  local Pp = pawn:K2_GetActorLocation()
  for k, m in pairs(S.known) do
    if not m.done and (m.passed or m.linger) and valid(m.it) then
      local s = 1 + (FOOD[m.type] and hunger / 600 or 0) + (WATER[m.type] and thirst / 600 or 0)
      s = s / (1 + dist(Pp, m.it:K2_GetActorLocation()) / 2000)
      if s > bs then best, bs = k, s end
    end
  end
  return best
end

local function move(goal, dt, speed)
  local p = S.pos
  local dx, dy, dz = goal.X - p.X, goal.Y - p.Y, goal.Z - p.Z
  local d = math.sqrt(dx*dx + dy*dy + dz*dz)
  local step = math.min(d, math.min(speed or CFG.speed, math.max(60, d * 2.0)) * dt)   -- eases in on arrival
  if d > 1 then
    local n = V(p.X + dx/d*step, p.Y + dy/d*step, p.Z + dz/d*step)
    -- keep out of walls: if the step is blocked, climb instead
    bc("move trace")
    local hit = {}
    local ok, r = pcall(function()
      return ksl:LineTraceSingle(world, p, n, 0, false, {S.drone, S.light}, 0, hit, true,
        {R=0,G=0,B=0,A=0}, {R=0,G=0,B=0,A=0}, 0)
    end)
    if ok and r then n = V(p.X, p.Y, p.Z + CFG.speed * dt) end
    S.pos = n
  end
  local bob = math.sin(S.time * 2.2) * 12
  local at = V(S.pos.X, S.pos.Y, S.pos.Z + bob)
  bc("move set")
  -- face the flight direction while travelling, else look at the player (S.look); turn at most 200 deg/s
  local ty = S.yaw
  if d > 60 then ty = math.deg(math.atan(dy, dx))
  elseif S.look then ty = math.deg(math.atan(S.look.Y - p.Y, S.look.X - p.X)) end
  local diff = (ty - S.yaw + 540) % 360 - 180
  local lim = 200 * dt
  S.yaw = S.yaw + math.max(-lim, math.min(lim, diff))
  local cy, sy = math.cos(math.rad(S.yaw)), math.sin(math.rad(S.yaw))
  S.drone:K2_SetActorLocation(at, false, {}, true)
  S.drone:K2_SetActorRotation({Pitch = 0, Yaw = S.yaw, Roll = 0}, true)
  for _, q in ipairs(S.parts or {}) do
    if valid(q.a) then
      local ox, oy = q.off[1] * G, q.off[2] * G
      q.a:K2_SetActorLocation(V(at.X + ox * cy - oy * sy, at.Y + ox * sy + oy * cy, at.Z + q.off[3] * G), false, {}, true)
      q.a:K2_SetActorRotation({Pitch = q.pitch, Yaw = S.yaw, Roll = 0}, true)
    end
  end
  if valid(S.light) then
    local ox = LAMP[1] * G
    S.light:K2_SetActorLocation(V(at.X + ox * cy, at.Y + ox * sy, at.Z + LAMP[3] * G), false, {}, true)
  end
end

-- Scout post (user 11-17: "the npc is locked to my poisiton", "if i turn my head its poisiton moves ... not realistic"):
-- the drone holds a point in the WORLD. Turning the view never moves it. A new post is picked only when the player
-- walks on (along the walking direction), gets far away, or the drone has been out of view for unseen_s.
local function flat(a, b) return math.sqrt((a.X - b.X)^2 + (a.Y - b.Y)^2) end
local function new_post(Pp, hx, hy, why)
  local side = ((math.random() < 0.5) and -1 or 1) * (120 + math.random() * 160)
  local ahead = CFG.ahead + math.random() * 200
  S.post = V(Pp.X + hx * ahead - hy * side, Pp.Y + hy * ahead + hx * side, Pp.Z + CFG.follow_up)
  S.post_from, S.unseen_t = V(Pp.X, Pp.Y, Pp.Z), 0
  log(string.format("post %.0f %.0f %.0f (%s)", S.post.X, S.post.Y, S.post.Z, why))
end
local function follow_post(pawn, Pp, dt)
  if S.pp and dt > 0 then
    local vx, vy = (Pp.X - S.pp.X) / dt, (Pp.Y - S.pp.Y) / dt
    local sp = math.sqrt(vx * vx + vy * vy)
    if sp > 80 and sp < 3000 then   -- walking; ignores standing still and teleports
      local k = math.min(1, dt * 3)
      local hx = (S.head_x or vx / sp) + (vx / sp - (S.head_x or vx / sp)) * k
      local hy = (S.head_y or vy / sp) + (vy / sp - (S.head_y or vy / sp)) * k
      local hl = math.sqrt(hx * hx + hy * hy)
      if hl > 0.01 then S.head_x, S.head_y = hx / hl, hy / hl end
    end
  end
  S.pp = V(Pp.X, Pp.Y, Pp.Z)
  local fwd = pawn:GetActorForwardVector()
  if not S.post then new_post(Pp, S.head_x or fwd.X, S.head_y or fwd.Y, "first") end
  local d = flat(S.post, Pp)
  if d > CFG.post_far then
    new_post(Pp, S.head_x or fwd.X, S.head_y or fwd.Y, "player far")
  elseif S.head_x and flat(Pp, S.post_from) > 300 then
    local along = (S.post.X - Pp.X) * S.head_x + (S.post.Y - Pp.Y) * S.head_y
    if along < 150 then new_post(Pp, S.head_x, S.head_y, "player walked on") end
  end
  local dd = flat(S.pos, Pp)
  local dot = dd > 1 and ((S.pos.X - Pp.X) * fwd.X + (S.pos.Y - Pp.Y) * fwd.Y) / dd or 1
  if dot < 0.35 then S.unseen_t = (S.unseen_t or 0) + dt else S.unseen_t = 0 end
  if S.unseen_t > CFG.unseen_s then new_post(Pp, fwd.X, fwd.Y, "out of view") end
  if math.abs(S.post.Z - (Pp.Z + CFG.follow_up)) > 60 then S.post.Z = Pp.Z + CFG.follow_up end
  return S.post
end

local function set_light(i, r, g, b)
  if not valid(S.light) then return end
  local lc = S.light.LightComponent
  pcall(function() lc:SetIntensity(i) end)
  pcall(function() lc:SetLightColor({R=r, G=g, B=b, A=1}, true) end)
end

local function end_guide(why)
  local m = S.target and S.known[S.target]
  if m then m.done = true end
  log(string.format("guide end %s: %s", tostring(S.target), why))
  S.mode, S.target, S.cool_t = "follow", nil, S.time
  S.post = nil
  set_light(800, 0.4, 0.8, 1.0)
end

local function tick(pawn, dt)
  S.time = S.time + dt
  local Pp = pawn:K2_GetActorLocation()
  -- seen 11-17: rare bad struct return (nil .X) -> skip this tick
  if type(Pp) ~= "userdata" and type(Pp) ~= "table" or type(Pp.X) ~= "number" or type(S.pos.X) ~= "number" then return end
  bc("tick " .. S.mode)
  S.look = Pp
  if S.time - S.scan_t >= CFG.scan_s then S.scan_t = S.time; scan(pawn); bc("scanned") end
  if S.mode == "follow" then
    local goal = follow_post(pawn, Pp, dt)
    if dist(S.pos, Pp) > CFG.leash then S.pos = V(goal.X, goal.Y, goal.Z) end
    move(goal, dt, CFG.cruise)
    if S.time - S.cool_t > CFG.cooldown_s then
      bc("pick"); local k = pick(pawn); bc("picked " .. tostring(k))
      if k then
        local m = S.known[k]
        S.mode, S.target, S.guide_t = "guide", k, S.time
        S.hint_n = S.hint_n + 1
        log(string.format("guide start %s (%s) player %.0f away, %s, hunger %.0f thirst %.0f",
          k, USEFUL[m.type], dist(Pp, m.it:K2_GetActorLocation()), m.passed and "walked past" or "lingered unseen",
          need("food"), need("water")))
        local c = get_cue(); log("cue " .. tostring(c ~= nil))
        if c then pcall(function() gs:PlaySoundAtLocation(world, c, S.pos, {Pitch=0,Yaw=0,Roll=0}, 0.6, 1.0, 0, nil, nil, nil) end) end
      end
    end
  else
    local m = S.known[S.target]
    if not m or not valid(m.it) then return end_guide("item gone") end
    local P = m.it:K2_GetActorLocation()
    move(V(P.X, P.Y, P.Z + CFG.hover_up), dt)
    local pulse = 0.5 + 0.5 * math.sin(S.time * 6)
    set_light(1500 + 4000 * pulse, 1.0, 0.75, 0.3)
    if not item_ok(m.it) then return end_guide("player looked at / took it") end
    if dist(Pp, P) < 250 then return end_guide("player reached it") end
    if dist(Pp, P) > CFG.leash then return end_guide("player left") end
    if S.time - S.guide_t > CFG.guide_max_s then return end_guide("timeout") end
  end
end

-- optional self-test: walk the pawn past a known item without looking at it
local LATE = false; do local f = io.open(ROOT .. "selftest.flag", "r"); if f then LATE = (f:read("a") or ""):find("late") ~= nil; f:close() end end
local selftest = io.open(ROOT .. "selftest.flag", "r")
if selftest then selftest:close(); log("SELFTEST on") end
local st = nil
local function selftest_step(pawn)
  if not st then
    local Pp = pawn:K2_GetActorLocation(); local best, bd
    for _, it in ipairs(FindAllOf("Item_Standard_C") or {}) do
      if item_ok(it) then local d = dist(Pp, it:K2_GetActorLocation()); if not bd or d < bd then best, bd = it, d end end
    end
    if not best then log("SELFTEST no item"); return end
    local P = best:K2_GetActorLocation()
    st = {item = key(best), from = V(P.X - 1500, P.Y + 500, P.Z + 120), to = V(P.X + 2500, P.Y + 500, P.Z + 120), t = 0}
    log("SELFTEST target " .. st.item .. string.format(" at %.0f %.0f %.0f, path passes 500 uu away", P.X, P.Y, P.Z))
    S.pos = V(st.from.X - 150, st.from.Y, st.from.Z + CFG.follow_up)
  end
  if LATE and S.time < 100 then return end
  st.t = st.t + 1
  st.s = (st.s or 0) + DT                 -- self-test seconds (real frame time)
  local a = math.min(1, st.s / 6.6)       -- ~6.6 s walk past the item
  local x = st.from.X + (st.to.X - st.from.X) * a
  bc("st teleport " .. st.t)
  pawn:K2_SetActorLocation(V(x, st.from.Y, st.from.Z), false, {}, true)
  if S.mode == "guide" then
    st.g = (st.g or 0) + DT
    local m = S.known[S.target]
    if VIS and m and valid(m.it) and st.g > 1 then  -- visual check: stand back and above, look down at drone + item
      local P = m.it:K2_GetActorLocation()
      if not st.park then  -- 11-17 user: the old fixed spot was inside a rock. Pick an open spot: sky above clear + clear both ways to the drone
        local function clear(a, b)
          local hit = {}
          local ok, r = pcall(function()
            return ksl:LineTraceSingle(world, a, b, 0, false, {S.drone, S.light, pawn}, 0, hit, true,
              {R=0,G=0,B=0,A=0}, {R=0,G=0,B=0,A=0}, 0)
          end)
          return ok and not r
        end
        local D = S.pos
        for _, rad in ipairs({260, 380, 180, 520}) do
          for _, up in ipairs({60, 140, 240}) do
            for k = 0, 11 do
              local a = k * math.pi / 6
              local c = V(D.X + math.cos(a) * rad, D.Y + math.sin(a) * rad, D.Z + up)
              local e = V(c.X + (D.X - c.X) * 0.75, c.Y + (D.Y - c.Y) * 0.75, c.Z + (D.Z - c.Z) * 0.75)
              if not st.park and clear(V(c.X, c.Y, c.Z + 2500), c) and clear(c, e) and clear(e, c)
                 and clear(c, V(c.X, c.Y, c.Z - 60)) then
                st.park = c
                log(string.format("VIS park %.0f %.0f %.0f rad %d up %d ang %d", c.X, c.Y, c.Z, rad, up, k * 30))
              end
            end
          end
        end
        if not st.park then st.park = V(P.X + 300, st.from.Y, st.from.Z); log("VIS park fallback (no open spot)") end
      end
      pawn:K2_SetActorLocation(st.park, false, {}, true)
    end
    local D, E = S.pos, pawn:K2_GetActorLocation()
    local dx, dy, dz = D.X - E.X, D.Y - E.Y, D.Z - (E.Z + 60)
    local yaw = math.deg(math.atan(dy, dx)); local pitch = math.deg(math.atan(dz, math.sqrt(dx*dx + dy*dy)))
    pcall(function() FindFirstOf("PlayerController"):SetControlRotation({Pitch = pitch, Yaw = yaw, Roll = 0}) end)
    if SHOT and not st.shot and st.g > 3 then  -- HighResShot crashes the game when minimized (11-17)
      st.shot = true
      local ok = pcall(function() ksl:ExecuteConsoleCommand(world, "HighResShot 1280x720", FindFirstOf("PlayerController")) end)
      log(string.format("SELFTEST shot ok=%s drone %.0f %.0f %.0f", tostring(ok), D.X, D.Y, D.Z))
    end
  end
  if st.s > (VIS and 45 or 20) and not st.done then
    st.done = true
    log(string.format("SELFTEST end: seen=%d hints=%d mode=%s target=%s frames=%d -> %s", S.seen_n, S.hint_n, S.mode,
      tostring(S.target), st.t, (S.hint_n > 0) and "PASS" or "FAIL"))
    log("DONE")
  end
end

-- All Lua runs on the game thread, driven by the player's ReceiveTick hook.
-- (LoopAsync work beside game-thread Lua corrupted the Lua VM: crash 11-17, same as Abiotic Factor 11-12.)
local seen_pawn = 0
local vis_seen, vis_block, vis_done, vis_t = {}, false, false, 0
if VIS then
  for _, fn in ipairs({"/Script/Engine.GameplayStatics:SetGamePaused", "/Script/Engine.PlayerController:SetPause"}) do
    local ok, e = pcall(RegisterHook, fn, function(ctx, a, b)
      for _, prm in ipairs({a, b}) do
        local okv, v = pcall(function() return prm:get() end)
        if okv and v == true then pcall(function() prm:set(false) end); vis_block = true; log("VIS pause blocked " .. fn) end
      end
    end)
    log("VIS hook " .. fn .. " " .. tostring(ok) .. " " .. tostring(e))
  end
end
local function step(dt)
  DT = dt; NOW = NOW + dt
  local pc = FindFirstOf("PlayerController")
  if not valid(pc) or not valid(pc.Pawn) then return end
  local pawn = pc.Pawn
  if not pawn:GetFullName():find("SolusPlayer") then return end
  seen_pawn = seen_pawn + dt
  if seen_pawn < 4 then return end   -- first frames: pawn not yet at PlayerStart
  if VIS and not vis_done then  -- visual check: wait for the intro's pod menu, block its pause, remove it, then start the test
    vis_t = (vis_t or 0) + dt
    if vis_t > 0.5 or vis_block then
      vis_t = 0
      for _, w in ipairs(FindAllOf("UserWidget") or {}) do
        local ok, inv = pcall(function() return w:IsInViewport() end)
        if ok and inv then
          local n = w:GetFullName()
          if not vis_block then vis_seen[n] = true
          elseif not vis_seen[n] then log("VIS remove " .. n); pcall(function() w:RemoveFromParent() end) end
        end
      end
      if vis_block then
        vis_done = true
        pcall(function() pc:SetViewTargetWithBlend(pawn, 0, 0, 0, false) end)
        log("VIS menu cleared, test starts")
      end
    end
    return
  end
  if not valid(S.drone) then if not spawn(pawn) then return end end
  if selftest then selftest_step(pawn) end
  tick(pawn, dt)
end

local hooked, queued = false, false
local function on_tick(self, delta)
  if queued then return end
  local d = 0.016; pcall(function() d = delta:get() end)
  queued = true
  -- engine calls straight inside a hook hung Abiotic Factor; queue to the next game-thread slot
  ExecuteInGameThread(function()
    queued = false
    local ok, e = pcall(step, math.min(0.1, d))
    if not ok then log("ERR " .. tostring(e)) end
  end)
end

-- bootstrap only: find the player class and hook its tick, then the async loop ends
LoopAsync(500, function()
  if hooked then return true end
  ExecuteInGameThread(function()
    if hooked then return end
    local pc = FindFirstOf("PlayerController")
    if not valid(pc) or not valid(pc.Pawn) then return end
    local full = pc.Pawn:GetClass():GetFullName()          -- "BlueprintGeneratedClass /Game/....SolusPlayer_C"
    if not full:find("SolusPlayer") then return end
    local path = full:match("%s(%S+)$") .. ":ReceiveTick"
    local ok, e = pcall(function() RegisterHook(path, on_tick) end)
    hooked = true
    log("hook " .. path .. " ok=" .. tostring(ok) .. (ok and "" or (" " .. tostring(e))))
  end)
  return false
end)
