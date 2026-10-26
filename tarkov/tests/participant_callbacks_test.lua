package.loaded.trkv_positions = dofile("tarkov/mods/trkv_raid_core/trkv_positions.lua")
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
  raid_id = "raid",
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
package.loaded.trkv_perception = dofile("tarkov/mods/trkv_raid_core/trkv_perception.lua")
package.loaded.trkv_patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
package.loaded.trkv_deployment = dofile("tarkov/mods/trkv_raid_core/trkv_deployment.lua")
package.loaded.trkv_loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
package.loaded.trkv_encounter = dofile("tarkov/mods/trkv_raid_core/trkv_encounter.lua")
package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
package.loaded.trkv_hearing = dofile("tarkov/mods/trkv_raid_core/trkv_hearing.lua")
package.loaded.trkv_combat = dofile("tarkov/mods/trkv_raid_core/trkv_combat.lua")
package.loaded.trkv_reload = dofile("tarkov/mods/trkv_raid_core/trkv_reload.lua")
package.loaded.trkv_squad = dofile("tarkov/mods/trkv_raid_core/trkv_squad.lua")
package.loaded.trkv_cover = dofile("tarkov/mods/trkv_raid_core/trkv_cover.lua")
package.loaded.trkv_decision = dofile("tarkov/mods/trkv_raid_core/trkv_decision.lua")
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
local spawned, actors, last_template = 0, {}, nil
local point_mt = { __eq = function(a, b) return a.x == b.x and a.y == b.y and a.z == b.z end }
TripointAbsMs = { new = function(x, y, z) return setmetatable({ x = x, y = y, z = z }, point_mt) end }
gapi.get_map = function() return { abs_to_bub = function(_, p) return p end } end
gapi.get_all_npcs = function() return actors end
local spawn_blocker, terrain_blocker
-- Include a non-NPC blocker, mirroring an avatar/monster from the real query.
gapi.get_all_creatures = function()
  local found = {}
  for i, actor in ipairs(actors) do found[i] = actor end
  if spawn_blocker then found[#found + 1] = { get_pos_ms = function() return spawn_blocker end } end
  return found
end
gapi.can_place_npc_at = function(point)
  if terrain_blocker and terrain_blocker == point then return false end
  for _, actor in ipairs(gapi.get_all_creatures()) do
    if actor:get_pos_ms() == point then return false end
  end
  return true
end
local catalog_choose = package.loaded.trkv_loadouts.choose
package.loaded.trkv_loadouts.choose = function(roll, pool_id)
  assert(pool_id == "technical_rifle_v1" or pool_id == "technical_trained_rifle_v1" or
    pool_id == "technical_recruit_rifle_v1", "Combat manifest omitted its pool")
  return catalog_choose(roll, pool_id)
end
gapi.rng = function(low, high) assert(low == 1 and high == 12); return 1 end
gapi.spawn_npc_at = function(template, point)
  assert(where == "raid" and (template == "trkv_patrol_tester" or template == "trkv_combat_tester" or
    template == "trkv_combat_field_tester" or template == "trkv_combat_recruit_tester" or
    template == "trkv_combat_recruit_field_tester" or template == "trkv_combat_ak_tester" or
    template == "trkv_combat_recruit_ak_tester"))
  last_template = template
  spawned = spawned + 1
  local actor = { position = point, moves = 1000, values = {}, id = 100 + spawned }
  function actor:getID() return { get_value = function() return self.id end } end
  function actor:set_value(k, v) self.values[k] = v end
  function actor:get_value(k) return self.values[k] or "" end
  function actor:get_pos_ms() return self.position end
  function actor:get_moves() return self.moves end
  function actor:avoid_immediate_danger() return "" end
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
-- Exercise the registered AI callback against tables replaced during load.
local visual = true
local last_seen = TripointAbsMs.new(401, 402, 0)
local visual_target = { get_pos_ms = function() return last_seen end,
  abs_pos = function() assert(visual); return last_seen end }
local first_actor = actors[1]
local original_position, original_moves = first_actor.position, first_actor.moves
local original_target = first_actor.current_target
function first_actor:current_target() return visual_target end
function first_actor:sees_creature() return visual end
function first_actor:abs_pos() return self.position end
function first_actor:set_moves(value) self.moves = value end
assert(not game.npc_ai_functions.TRKV_PATROL(first_actor))
local old_member = root.participants.actors["101"]
assert(old_member.perception.status == "visible")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
visual = false; last_seen.x = 499
assert(game.npc_ai_functions.TRKV_PATROL(first_actor))
local new_member = root.participants.actors["101"]
assert(new_member ~= old_member and new_member.search.goal.position.x == 401)
assert(new_member.perception.status == "remembered" and old_member.perception.status == "visible")
assert(old_member.search.goal == nil and new_member.search.goal.attempts == 1)
first_actor.position, first_actor.moves, first_actor.current_target = original_position, original_moves, original_target
assert(spawned == 3 and new_member.patrol.index == 2)
print("PASS registered AI callback follows replaced memory/search records without refreshing hidden coordinates")
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
root.cold_expected = { encounter = "patrol", npc_ids = { 101, 102, 103 } }
for _, record in pairs(root.participants.actors) do record.patrol.index = 2 end
ItypeId = { new = function(value) return value end }
test_data.stage = "cold_npc_saved"
dofile("tarkov/tests/bn_integration.lua")
test_data.stage = "cold_ai_checkpoint"
dofile("tarkov/tests/bn_integration.lua")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
test_data.stage = "cold_npc_restored"
dofile("tarkov/tests/bn_integration.lua")
assert(spawned == 3)
assert(game.npc_ai_functions.TRKV_PATROL(first_actor))
assert(first_actor.position.y == 400)
test_data.stage = "cold_ai_resumed"
dofile("tarkov/tests/bn_integration.lua")
clock = clock + 31
assert(game.npc_ai_functions.TRKV_PATROL(first_actor))
assert(first_actor.position.y == 401)
test_data.stage = "cold_ai_expired"
dofile("tarkov/tests/bn_integration.lua")
print("PASS cold AI checkpoint bookkeeping, replaced storage and registered search continuation")
print("PASS cold probe checks saved route, side and ready slots after deployment recovery")
mod.extract(); closed()
assert(mod.depart("empty") and root.raid.encounter == "empty" and spawned == 3)
print("PASS selectable patrol encounter, pending mode, production adapter/AI callback and reload without duplicates")
mod.extract(); closed()
actors = {} -- Simulate engine dimension reset clearing the active actors.
assert(not mod.depart("unknown") and spawned == 3)
fail_enter, answer = true, 4
mod.start()
assert(root.raid.phase == "entering" and root.raid.encounter == "combat" and spawned == 3)
fail_enter, answer = false, 1
mod.start() -- Retry via the existing menu: mode must remain combat.
assert(last_template == "trkv_combat_tester" and spawned == 4 and #actors == 1)
local combat_id = root.participants.slots.combat_1.id
assert(root.participants.actors[tostring(combat_id)].side == "hostile_test")
assert(root.participants.slots.combat_1.loadout == "rifle_civilian_v1")
assert(actors[1]:get_value("trkv_loadout") == "rifle_civilian_v1")
root.raid, root.participants = copy(root.raid), copy(root.participants)
root.raid.encounter_deployed = false
gapi.rng = function() error("Load rerolled equipment") end
mod.loaded(); tick()
assert(spawned == 4 and root.raid.encounter_deployed and root.raid.encounter == "combat")
assert(not package.loaded.trkv_encounter.ensure(root.participants, context(), "unknown"))
print("PASS combat menu, production template, pending retry mode and restored deployment without duplicates")
mod.extract(); closed(); actors = {}
gapi.rng = function() return 4 end
assert(mod.depart("combat") and last_template == "trkv_combat_field_tester" and spawned == 5)
local field_id = root.participants.slots.combat_1.id
assert(root.participants.actors[tostring(field_id)].loadout == "rifle_field_v1")
root.participants.slots.combat_1 = { status = "creating", loadout = "rifle_field_v1" }
actors[1]:set_value("trkv_loadout", "rifle_civilian_v1")
local recovered, why = package.loaded.trkv_encounter.ensure(root.participants, context(), "combat")
assert(not recovered and why == "pending" and spawned == 5)
actors[1]:set_value("trkv_loadout", "rifle_field_v1")
assert(package.loaded.trkv_encounter.ensure(root.participants, context(), "combat") and spawned == 5)
assert(root.participants.slots.combat_1.loadout == "rifle_field_v1")
print("PASS field preset and reconciliation reject mismatched live loadout without spawning")
-- Both training profiles can receive either coherent equipment set.
for _, variant in ipairs({
  { roll = 5, id = "rifle_recruit_civilian_v1", template = "trkv_combat_recruit_tester" },
  { roll = 12, id = "rifle_recruit_field_v1", template = "trkv_combat_recruit_field_tester" },
}) do
  mod.extract(); closed(); actors = {}
  gapi.rng = function() return variant.roll end
  assert(mod.depart("combat") and last_template == variant.template and #actors == 1)
  local id = root.participants.slots.combat_1.id
  assert(root.participants.slots.combat_1.loadout == variant.id)
  assert(root.participants.actors[tostring(id)].loadout == variant.id)
  root.raid, root.participants = copy(root.raid), copy(root.participants)
  root.raid.encounter_deployed = false
  gapi.rng = function() error("Load rerolled training profile") end
  local before = spawned
  mod.loaded(); tick()
  assert(spawned == before and root.raid.encounter_deployed)
  assert(root.participants.slots.combat_1.loadout == variant.id)
end
print("PASS recruit variants use own templates and preserve training/equipment selection after load")
-- The native reload probe forces a field kit and restores the production picker.
mod.extract(); closed(); actors = {}
local original_choose = package.loaded.trkv_loadouts.choose
gapi.rng = function() error("Forced field probe must not roll the catalog") end
test_data = { stage = "npc_reload_depart" }
dofile("tarkov/tests/bn_npc_probe.lua")
assert(test_data.combat_loadout == "rifle_field_v1" and last_template == "trkv_combat_field_tester")
assert(package.loaded.trkv_loadouts.choose == original_choose)
print("PASS native reload setup uses production field template and restores the picker")
-- Real menu route, failed entry retry and mixed role pools in a hostile group.
mod.extract(); closed(); actors = {}
local group_rolls = { 1, 4, 2 }
local group_pools, group_draw = {}, 0
package.loaded.trkv_loadouts.choose = function(roll, pool_id)
  group_pools[#group_pools + 1] = pool_id
  return catalog_choose(roll, pool_id)
end
gapi.rng = function(low, high)
  assert(low == 1 and high == 4)
  group_draw = group_draw + 1
  return group_rolls[group_draw]
end
fail_enter, answer = true, 5
local before_group = spawned
mod.start()
assert(root.raid.phase == "entering" and root.raid.encounter == "squad" and spawned == before_group)
fail_enter, answer = false, 1
spawn_blocker = TripointAbsMs.new(398, 398, 0)
mod.start()
assert(root.raid.encounter == "squad" and not root.raid.encounter_deployed)
assert(spawned == before_group + 2 and group_draw == 3)
assert(root.participants.slots.hostile_1.status == "reserved")
assert(root.participants.slots.hostile_1.loadout == "rifle_civilian_v1")
assert(not root.raid.deployment_warning)
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
assert(spawned == before_group + 2 and group_draw == 3)
spawn_blocker = nil
terrain_blocker = TripointAbsMs.new(398, 398, 0)
tick()
assert(spawned == before_group + 2 and group_draw == 3)
assert(root.participants.slots.hostile_1.status == "reserved")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
assert(spawned == before_group + 2 and group_draw == 3 and not root.raid.deployment_warning)
assert(root.participants.slots.hostile_1.loadout == "rifle_civilian_v1")
terrain_blocker = nil
tick()
assert(root.raid.encounter == "squad" and #actors == 3 and spawned == before_group + 3)
assert(group_pools[1] == "technical_trained_rifle_v1")
assert(group_pools[2] == "technical_recruit_rifle_v1" and group_pools[3] == group_pools[2])
local by_id = {}
for _, actor in ipairs(actors) do by_id[actor.id] = actor end
for i = 1, 3 do actors[i] = by_id[root.participants.slots["hostile_" .. i].id] end
local choices = { "rifle_civilian_v1", "rifle_recruit_field_v1", "rifle_recruit_civilian_v1" }
for i, expected in ipairs(choices) do
  local slot = root.participants.slots["hostile_" .. i]
  assert(slot.id == actors[i].id and slot.loadout == expected)
end
local dead_id = actors[3].id
actors[3] = nil -- Engine casualty: ready slot remains consumed.
root.raid, root.participants = copy(root.raid), copy(root.participants)
root.raid.encounter_deployed = false
gapi.rng = function() error("Group load rerolled a participant") end
mod.loaded(); tick()
assert(root.raid.encounter_deployed and #actors == 2 and spawned == before_group + 3)
assert(root.participants.slots.hostile_3.id == dead_id)
assert(root.participants.slots.hostile_3.loadout == choices[3])
print("PASS hostile group menu, pending retry, explicit role pools and casualty replay without reroll/respawn")
-- New pools are isolated from v1 and survive the real sixth menu/retry path.
mod.extract(); closed(); actors = {}
local varied_picks, varied_before = 0, spawned
package.loaded.trkv_loadouts.choose = function(roll, pool)
  assert(pool == "technical_trained_rifle_v2" or pool == "technical_recruit_rifle_v2")
  return catalog_choose(roll, pool)
end
local varied_rolls = { 6, 4, 6 }
gapi.rng = function(low, high)
  assert(low == 1 and high == 6)
  varied_picks = varied_picks + 1
  return varied_rolls[varied_picks]
end
fail_enter, answer = true, 6
mod.start()
assert(root.raid.phase == "entering" and root.raid.encounter == "varied" and spawned == varied_before)
fail_enter, answer = false, 1
mod.start()
assert(root.raid.encounter == "varied" and root.raid.encounter_deployed and #actors == 3)
assert(varied_picks == 3 and spawned == varied_before + 3)
local varied_choices = { "rifle_ak_v1", "rifle_recruit_field_v1", "rifle_recruit_ak_v1" }
local varied_ids = {}
for i, choice in ipairs(varied_choices) do
  local slot = root.participants.slots["hostile_" .. i]
  assert(slot.loadout == choice and slot.id == actors[i].id)
  varied_ids[i] = slot.id
end
root.raid, root.participants = copy(root.raid), copy(root.participants)
root.raid.encounter_deployed = false
gapi.rng = function() error("Varied group rerolled after load") end
mod.loaded(); tick()
assert(root.raid.encounter_deployed and #actors == 3 and spawned == varied_before + 3)
for i, id in ipairs(varied_ids) do assert(root.participants.slots["hostile_" .. i].id == id) end
print("PASS varied menu, retry, role pools v2 and restored AK/M4 group without reroll")
root.cold_expected = { encounter = "varied", npc_ids = varied_ids, npc_choices = varied_choices }
actors[3] = nil
for _, record in pairs(root.participants.actors) do record.patrol.index = 1 end
test_data = { stage = "cold_npc_saved" }
dofile("tarkov/tests/bn_integration.lua")
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
test_data.stage = "cold_npc_restored"
dofile("tarkov/tests/bn_integration.lua")
assert(#actors == 2 and spawned == varied_before + 3)
print("PASS varied cold bookkeeping preserves role/kit/ID and consumed casualty")
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
