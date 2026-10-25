package.loaded.trkv_loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
local reload = dofile("tarkov/mods/trkv_raid_core/trkv_reload.lua")
local function copy(v)
  if type(v) ~= "table" then return v end
  local out = {}; for k, x in pairs(v) do out[k] = copy(x) end; return out
end
local function setup()
  local ctx = { phase = "active", at_raid = true, sequence = 1, dimension = "raid" }
  local memory = { sequence = 1, dimension = "raid", status = "visible",
    contact = { position = { x = 0, y = 0, z = 0 }, seen_at = 100, expires_at = 130 } }
  local box = { x = 2, moves = 1000, choices = 0, ready = true, valid = true, loaded = false }
  local api = {
    ready = function() return box.ready end,
    choose = function() box.choices = box.choices + 1; return { x = 4, y = 0, z = 0 } end,
    cover_failure = function() return "exposed_cover" end,
    validate = function(p) assert(p.x == 0); return box.valid end,
    at = function(p) return box.x == p.x end,
    position = function() return { x = box.x, y = 0, z = 0 } end,
    moves = function() return box.moves end,
    wait = function() box.moves = box.moves - 100 end,
    move_to = function() if not box.blocked then box.x = box.x + 1; box.moves = box.moves - 100 end end,
    failure = function() return "visible_target" end,
    reload = function(p)
      assert(p.x == 0)
      if box.fail_reload then return false end
      box.loaded, box.ready, box.moves = true, false, box.moves - 350
      return true
    end,
  }
  return ctx, memory, box, api
end
local ctx, memory, box, api = setup()
local state = {}
box.ready = false
assert(not reload.step(state, ctx, memory, 100, api) and state.cooldown_until == nil)
box.ready = true
assert(reload.step(state, ctx, memory, 101, api) and box.x == 3)
state = copy(state); memory.status = "remembered"
assert(reload.step(state, ctx, memory, 102, api) and box.x == 4 and box.choices == 1)
local ok, reason = reload.step(state, ctx, memory, 103, api)
assert(ok and reason == "reloaded" and box.loaded and box.moves == 450 and state.goal == nil)
assert(state.cooldown_until == 113)
-- Failed execution cannot fall through to hidden-target vanilla AI that tick.
ctx, memory, box, api = setup(); state = {}; box.x = 3
assert(reload.step(state, ctx, memory, 100, api))
box.fail_reload = true
ok, reason = reload.step(state, ctx, memory, 101, api)
assert(ok and reason == "reload_failed" and box.moves == 800 and state.goal == nil)
assert(state.failure_reason == "visible_target")
-- An unavailable route spends bounded waits; it cannot keep renewing a plan.
ctx, memory, box, api = setup(); state = {}; box.blocked = true
assert(reload.step(state, ctx, memory, 100, api))
assert(reload.step(state, ctx, memory, 101, api))
ok, reason = reload.step(state, ctx, memory, 102, api)
assert(not ok and reason == "unreachable" and box.moves == 800 and box.choices == 1)
for _, cause in ipairs({ "expired", "moved", "invalid", "memory", "clock" }) do
  ctx, memory, box, api = setup(); state = {}
  assert(reload.step(state, ctx, memory, 100, api))
  local now = 101
  if cause == "expired" then now = 108
  elseif cause == "moved" then memory.contact.position.x = 2
  elseif cause == "invalid" then box.valid = false
  elseif cause == "memory" then memory.contact = nil
  elseif cause == "clock" then now = 99 end
  local before = box.moves
  assert(not reload.step(state, ctx, memory, now, api) and state.goal == nil and before == box.moves)
  if cause == "invalid" then assert(state.failure_reason == "exposed_cover") end
end
ctx, memory, box, api = setup(); state = {}
assert(reload.step(state, ctx, memory, 100, api))
ctx.phase = "cleanup"
assert(not reload.step(state, ctx, memory, 101, {}) and state.goal == nil)
assert(not reload.step_actor({ loadout = "rifle_recruit_field_v1" }, ctx, {}, {}, 101))
print("PASS cover reload: readiness, saved approach, remembered threat, real action budget, failure wait, blocked/expired/moved/invalid/clock cancellation")

-- An interrupted approach may leave the actor already protected. The guarded
-- executor can reload there from fresh memory without inventing a new route.
ctx, memory, box, api = setup(); state = {}; memory.status = "remembered"
ok, reason = reload.step(state, ctx, memory, 101, api)
assert(ok and reason == "reloaded" and box.loaded and box.choices == 0 and state.goal == nil)
assert(box.moves == 650)
print("PASS remembered threat can permit an immediate guarded reload without a new movement plan")

-- No-memory maintenance requires the current raid identity and an explicit
-- 'none' observation; stale, remembered or future contacts cannot authorize it.
ctx, memory, box, api = setup(); state = {}
local idle_calls = 0
api.idle_reload = function() idle_calls = idle_calls + 1; box.moves = box.moves - 250; return true end
memory.contact, memory.status = nil, "none"
ok, reason = reload.step(state, ctx, memory, 140, api)
assert(ok and reason == "idle_reloaded" and idle_calls == 1 and box.moves == 750)
memory.sequence = 0
assert(not reload.step(state, ctx, memory, 141, api) and idle_calls == 1)
memory.sequence, memory.status = 1, "remembered"
assert(not reload.step(state, ctx, memory, 142, api) and idle_calls == 1)
-- The production adapter also requires the absence of active sound memory.
local member = { loadout = "rifle_field_v1", perception = { sequence = 1, dimension = "raid", status = "none" },
  hearing = { contact = { source = "sound" } } }
local engine_calls = 0
local actor = { reload_without_visible_target = function() engine_calls = engine_calls + 1; return true end }
assert(not reload.step_actor(member, ctx, actor, {}, 143) and engine_calls == 0)
member.hearing.contact = nil
ok, reason = reload.step_actor(member, ctx, actor, {}, 144)
assert(ok and reason == "idle_reloaded" and engine_calls == 1)
print("PASS post-contact reload ownership, stale-memory rejection and hearing priority")

-- Basic maintenance belongs to recruits too, but deliberate cover selection
-- remains a trained capability and must not invoke a selector for the recruit.
member = { loadout = "rifle_recruit_field_v1", perception = { sequence = 1, dimension = "raid", status = "none" } }
ok, reason = reload.step_actor(member, ctx, actor, {}, 145)
assert(ok and reason == "idle_reloaded" and engine_calls == 2)
member.perception.status = "visible"
member.perception.contact = { position = { x = 0, y = 0, z = 0 }, seen_at = 146, expires_at = 176 }
ok, reason = reload.step_actor(member, ctx, actor, {}, 146)
assert(not ok and reason == "cover_disabled" and engine_calls == 2 and member.reload.goal == nil)
print("PASS recruits reload between contacts without gaining trained cover maneuvers")

-- A saved approach must recheck the actual weapon/ammunition before movement,
-- even when its old cover would otherwise remain valid.
for _, restored in ipairs({ false, true }) do
  ctx, memory, box, api = setup(); state = {}
  assert(reload.step(state, ctx, memory, 100, api))
  if restored then state = copy(state) end
  local deadline, before, position = state.cooldown_until, box.moves, box.x
  state.failure_reason = "old_failure"
  box.ready = false
  api.validate = function() error("Unneeded approach evaluated terrain") end
  api.move_to = function() error("Unneeded approach moved") end
  ok, reason = reload.step(state, ctx, memory, 101, api)
  assert(not ok and reason == "no_longer_needed" and state.status == reason)
  assert(state.goal == nil and state.failure_reason == nil)
  assert(box.moves == before and box.x == position and state.cooldown_until == deadline)
  -- Returning ammunition cannot renew the cancelled plan inside its cooldown.
  box.ready = true
  ok, reason = reload.step(state, ctx, memory, 102, api)
  assert(not ok and reason == "cooldown" and box.choices == 1)
end
print("PASS reload approach rechecks inventory after interruptions and restore without spending moves or renewing cooldown")
