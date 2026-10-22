-- Exercise the production lifecycle wiring, including replaced nested save tables.
local members = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
local raid = dofile("tarkov/mods/trkv_raid_core/trkv_lifecycle.lua")
local root, mod = {}, {}
local where, clock, answer, tick = "home", 100, 1, nil
local fail_enter, fail_return, fail_cleanup, loading = false, false, false, false
local resets = 0
local function copy(value)
  if type(value) ~= "table" then return value end
  local result = {}
  for k, v in pairs(value) do result[k] = copy(v) end
  return result
end
local api = {
  check_capabilities = function() end,
  at_home = function() return where == "home" end,
  at_raid = function() return where == "raid" end,
  now = function() return clock end,
  enter = function()
    assert(not loading)
    assert(root.participants.sequence == root.raid.sequence and not root.participants.closed)
    if fail_enter then return false end
    where = "raid"; return true
  end,
  return_home = function()
    assert(not loading)
    if fail_return then return false end
    where = "home"; return true
  end,
  cleanup = function()
    assert(not loading and where == "home" and root.raid.phase == "cleanup")
    assert(not root.participants.closed, "Registry closed before engine reset succeeded")
    resets = resets + 1
    return not fail_cleanup
  end,
  penalize = function() end,
}
locale = { gettext = function(s) return s end }
game = { current_mod = "trkv_raid_core", mod_runtime = { trkv_raid_core = mod },
  mod_storage = { trkv_raid_core = root } }
gapi = { add_msg = function() end, add_on_every_x_hook = function(_, fn) tick = fn end,
  get_avatar = function() return { set_all_parts_hp_to_max = function() end, clear_effects = function() end } end }
TimeDuration = { from_seconds = function(v) return v end }
UiList = { new = function() return { title = function() end, add = function() end,
  query = function() return answer end } end }
package.loaded.trkv_lifecycle, package.loaded.trkv_bn = raid, api
package.loaded.trkv_participants = members
package.loaded.trkv_patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
package.loaded.trkv_deployment = dofile("tarkov/mods/trkv_raid_core/trkv_deployment.lua")
package.loaded.trkv_encounter = dofile("tarkov/mods/trkv_raid_core/trkv_encounter.lua")
dofile("tarkov/mods/trkv_raid_core/main.lua")
local function context()
  return { phase = root.raid.phase, sequence = root.raid.sequence, at_raid = api.at_raid() }
end
local function add(id)
  assert(root.raid.phase == "active")
  return assert(members.register(root.participants, root.raid.sequence, id, "usec", "alpha", {
    { x = 1, y = 1, z = 0 }, { x = 1, y = 2, z = 0 },
  }))
end
local function closed()
  assert(where == "home" and root.raid.phase == "home")
  assert(root.participants.closed and next(root.participants.actors) == nil)
end
mod.start()
add(10).patrol.index = 2
add(11)
fail_return = true
mod.extract()
assert(root.raid.phase == "returning" and members.find(root.participants, context(), 10) == nil)
assert(root.participants.actors["10"].patrol.index == 2 and resets == 0)
-- BN replaces BOTH nested tables. Capturing either old identity loses/erases actors.
local old_members = root.participants
root.raid, root.participants = copy(root.raid), copy(root.participants)
old_members.actors["10"].side = "old_table"
fail_return, fail_cleanup = false, true
mod.loaded(); tick()
assert(root.raid.phase == "cleanup" and not root.participants.closed)
assert(root.participants.actors["10"].side == "usec" and root.participants.actors["11"])
local cleanup_raid, cleanup_members = copy(root.raid), copy(root.participants)
answer, fail_cleanup = 2, false
mod.start() -- Terminal recovery uses the same engine cleanup wrapper.
closed()
assert(old_members.actors["10"].side == "old_table")
-- Replay the pre-reset saved checkpoint. Load hooks themselves must do no travel.
root.raid, root.participants = cleanup_raid, cleanup_members
loading = true
local before = resets
mod.loaded(); mod.loaded()
assert(resets == before and not root.participants.closed)
loading = false
tick(); closed()
assert(root.raid.wins == 1)
answer = 1
mod.start()
assert(root.raid.sequence == 2 and next(root.participants.actors) == nil)
add(12).patrol.index = 2
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
assert(members.find(root.participants, context(), 12).patrol.index == 2)
assert(mod.death({ char = { is_avatar = function() return false end } }) == nil)
assert(root.participants.actors["12"])
assert(mod.death({ char = { is_avatar = function() return true end } }))
closed()
mod.start(); add(13)
clock = root.raid.deadline
tick(); closed()
-- Failed entry never closes/reopens the same pending registry or consumes a new ID.
fail_enter = true
mod.start()
local pending, seq = root.participants, root.raid.sequence
assert(root.raid.phase == "entering" and not pending.closed)
mod.loaded(); tick()
assert(root.participants == pending and root.raid.sequence == seq)
fail_enter = false
mod.start()
assert(root.raid.phase == "active" and root.participants == pending and root.raid.sequence == seq)
-- An old save lacking registry data gets an empty registry, without spawning replacements.
root.participants = nil
mod.loaded(); tick()
assert(root.participants.sequence == seq and not root.participants.closed)
assert(next(root.participants.actors) == nil)
print("PASS participant lifecycle: failed return/reset, checkpoint replay, replaced tables, death, timeout, retry and legacy save")

-- Exercise the actual encounter adapter from the player departure callback.
mod.extract(); closed()
local spawned, actors = 0, {}
local point_mt = { __eq = function(a, b) return a.x == b.x and a.y == b.y and a.z == b.z end }
TripointAbsMs = { new = function(x, y, z) return setmetatable({ x = x, y = y, z = z }, point_mt) end }
gapi.get_map = function() return { abs_to_bub = function(_, p) return p end } end
gapi.get_all_npcs = function() return actors end
gapi.spawn_npc_at = function(template, point)
  assert(where == "raid" and template == "trkv_patrol_tester")
  spawned = spawned + 1
  local actor = { position = point, moves = 1000, values = {}, id = 100 + spawned }
  function actor:getID() return { get_value = function() return self.id end } end
  function actor:set_value(k, v) self.values[k] = v end
  function actor:get_value(k) return self.values[k] or "" end
  function actor:get_pos_ms() return self.position end
  function actor:get_moves() return self.moves end
  function actor:current_target() return nil end
  function actor:danger_assessment() return -10 end
  function actor:move_towards(p)
    local step = p.y > self.position.y and 1 or -1
    self.position, self.moves = TripointAbsMs.new(p.x, self.position.y + step, p.z), self.moves - 100
    return true
  end
  actors[#actors + 1] = actor
  return actor
end
fail_enter = true
assert(not mod.depart("patrol") and spawned == 0 and root.raid.encounter == "patrol")
fail_enter = false
assert(mod.depart("empty")) -- Pending retry must retain the originally chosen patrol mode.
assert(root.raid.encounter == "patrol" and root.raid.encounter_deployed and spawned == 3)
assert(game.npc_ai_functions.TRKV_PATROL(actors[1]))
assert(actors[1].position.y == 399 and actors[1].moves == 900)
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
assert(spawned == 3 and root.participants.actors["101"].patrol.index == 2)
root.raid.encounter_deployed = false -- Replay a checkpoint before marking deployment complete.
tick()
assert(spawned == 3 and root.raid.encounter_deployed)
-- Replay the actual native probe's casualty checkpoint against replaced storage.
test_data = { stage = "npc_live_casualty_before", group_ids = { 101, 102, 103 } }
dofile("tarkov/tests/bn_npc_probe.lua")
local casualty = table.remove(actors, 3)
function casualty:is_avatar() return false end
mod.death({ char = casualty })
test_data.stage = "npc_live_casualty_checkpoint"
dofile("tarkov/tests/bn_npc_probe.lua")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
test_data.stage = "npc_live_casualty_check"
dofile("tarkov/tests/bn_npc_probe.lua")
assert(spawned == 3 and root.participants.slots.patrol_3.id == 103)
print("PASS casualty checkpoint retains ready slot without respawn or settling player raid")
-- Execute the new cold-probe bookkeeping branches with plain restored records.
root.cold_expected = { npc_ids = { 101, 102, 103 } }
for _, record in pairs(root.participants.actors) do record.patrol.index = 2 end
ItypeId = { new = function(value) return value end }
test_data.stage = "cold_npc_saved"
dofile("tarkov/tests/bn_integration.lua")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
test_data.stage = "cold_npc_restored"
dofile("tarkov/tests/bn_integration.lua")
assert(spawned == 3)
print("PASS cold probe checks saved route, side and ready slots after deployment recovery")
mod.extract(); closed()
assert(mod.depart("empty") and root.raid.encounter == "empty" and spawned == 3)
print("PASS selectable patrol encounter, pending mode, production adapter/AI callback and reload without duplicates")
-- Regression for the actual native probe's door setup: unchanged terrain is not failure.
local door_map, set_calls, terrain = {}, 0, "t_door_c"
TerId = { new = function(value) return { int_id = function() return value end } end }
function door_map:abs_to_bub(p) return p end
function door_map:set_ter_at(p, value)
  assert(p.x == 394 and p.y == 391 and value == "t_door_c")
  set_calls = set_calls + 1
  return false -- BN's result when the closed door is already present.
end
function door_map:get_ter_at() return terrain end
gapi.get_map = function() return door_map end
assert(members.register(root.participants, root.raid.sequence, 1001, "usec", "door_test", {}))
test_data = { stage = "npc_live_door_setup", door_actor_id = 1001 }
dofile("tarkov/tests/bn_npc_probe.lua")
dofile("tarkov/tests/bn_npc_probe.lua")
assert(set_calls == 2)
terrain = "t_wall" -- A genuinely failed setup must still fail the same invariant.
assert(not pcall(dofile, "tarkov/tests/bn_npc_probe.lua"))
print("PASS native door setup accepts unchanged closed terrain and rejects incorrect terrain")
