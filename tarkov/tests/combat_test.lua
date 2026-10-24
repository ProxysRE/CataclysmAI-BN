package.loaded.trkv_loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
local combat = dofile("tarkov/mods/trkv_raid_core/trkv_combat.lua")
local ctx = { phase = "active", at_raid = true, sequence = 1, dimension = "raid" }
local memory = { sequence = 1, dimension = "raid", status = "visible",
  contact = { position = { x = 0, y = 0, z = 0 } } }
local state, position, moves, choices, blocked, valid = {}, { x = 2, y = 0, z = 0 }, 1000, 0, false, true
local selected = { x = 4, y = 0, z = 0 }
local api = {
  choose = function() choices = choices + 1; return selected end,
  validate = function(_, p) assert(p.x == 4); return valid end,
  at = function(p) return p.x == position.x and p.y == position.y and p.z == position.z end,
  position = function() return position end,
  moves = function() return moves end,
  wait = function() moves = moves - 100 end,
  move_to = function(p)
    if not blocked then position = { x = position.x + 1, y = p.y, z = p.z }; moves = moves - 100 end
  end,
}
assert(combat.step(state, ctx, memory, 100, api) and position.x == 3 and choices == 1)
local function copy(v)
  if type(v) ~= "table" then return v end
  local t = {}; for k, x in pairs(v) do t[k] = copy(x) end; return t
end
state = copy(state)
assert(combat.step(state, ctx, memory, 101, api) and position.x == 4 and choices == 1)
local ok, reason = combat.step(state, ctx, memory, 102, api)
assert(not ok and reason == "arrived" and moves == 800)
assert(state.goal == nil and state.cooldown_until == 112)
assert(not combat.step(state, ctx, memory, 103, api) and choices == 1)
position, blocked = { x = 2, y = 0, z = 0 }, true
assert(combat.step(state, ctx, memory, 112, api))
assert(combat.step(state, ctx, memory, 113, api))
ok, reason = combat.step(state, ctx, memory, 114, api)
assert(not ok and reason == "cancelled" and state.cooldown_until == 124)
blocked = false
assert(combat.step(state, ctx, memory, 124, api))
valid = false
ok, reason = combat.step(state, ctx, memory, 125, api)
assert(not ok and reason == "invalid_position" and state.goal == nil)
valid = true; position.x = 2
assert(combat.step(state, ctx, memory, 136, api))
memory.status = "remembered"
ok, reason = combat.step(state, ctx, memory, 137, api)
assert(not ok and reason == "lost_contact" and state.goal == nil)
memory.status = "visible"; position.x = 2
assert(combat.step(state, ctx, memory, 148, api))
memory.contact.position.x = 5
assert(not combat.step(state, ctx, memory, 149, api) and state.status == "cancelled")
memory.contact.position.x = 0; position.x = 2
assert(combat.step(state, ctx, memory, 160, api))
assert(not combat.step(state, ctx, memory, 168, api) and state.status == "cancelled")
ctx.sequence = 2
assert(not combat.step(state, ctx, memory, 169, api) and state.goal == nil)
ctx.phase = "cleanup"
assert(not combat.step(state, ctx, memory, 170, api))
-- The pilot is enabled only for controlled trained rifle presets.
assert(not combat.step_actor({ loadout = "rifle_recruit_field_v1" }, ctx, {}, {}, 170))
print("PASS persistent combat intention, reload copy, arrival handoff, cooldown, stalled/expired/invalid/lost-target cancellation")

-- A saved cooldown belongs to its clock and cannot freeze AI after a rollback.
ctx.phase, ctx.sequence = "active", 1
memory.sequence, memory.contact.position.x = 1, 0
position.x, blocked = 2, false
state = {}
assert(combat.step(state, ctx, memory, 1000, api))
state = copy(state)
local before_reset = moves
ok, reason = combat.step(state, ctx, memory, 10, api)
assert(not ok and reason == "clock_reset" and state.goal == nil)
assert(state.cooldown_until == 22 and moves == before_reset)
assert(not combat.step(state, ctx, memory, 21, api))
position.x = 2
assert(combat.step(state, ctx, memory, 22, api))
-- Cancellation must happen before any engine adapter is used.
ctx.phase = "cleanup"
ok, reason = combat.step(state, ctx, memory, 23, {})
assert(not ok and reason == "inactive" and state.goal == nil and state.cooldown_until == nil)
ctx.phase = "active"; position.x = 2
assert(combat.step(state, ctx, memory, 24, api))
local member = { loadout = "rifle_recruit_field_v1", combat = state }
ok, reason = combat.step_actor(member, ctx, {}, {}, 25)
assert(not ok and reason == "disabled" and state.goal == nil and state.last_now == nil)
-- Changing raid identity clears the previous clock as well as its goal.
state = { schema = 1, sequence = 0, dimension = "old", last_now = 9999, cooldown_until = 9999 }
position.x = 2
assert(combat.step(state, ctx, memory, 30, api) and state.goal.started_at == 30)
print("PASS combat cancellation on inactive/profile change, clock rollback cooldown recovery and raid identity reset")

-- The dispatcher has its own early exit; it must not bypass cancellation.
local saved_modules = {}
local module_names = { "trkv_perception", "trkv_search", "trkv_hearing", "trkv_patrol", "trkv_combat" }
for _, name in ipairs(module_names) do
  saved_modules[name] = package.loaded[name]
  package.loaded[name] = name == "trkv_combat" and combat or {}
end
local decision = dofile("tarkov/mods/trkv_raid_core/trkv_decision.lua")
local inactive_member = { patrol = { sequence = 1 }, combat = state }
ctx.phase = "cleanup"
ok, reason = decision.step_actor(inactive_member, ctx, {}, {}, 31)
assert(not ok and reason == "inactive" and state.goal == nil and state.cooldown_until == nil)
for _, name in ipairs(module_names) do package.loaded[name] = saved_modules[name] end
print("PASS dispatcher inactive exit cancels a pending combat maneuver without engine calls")
