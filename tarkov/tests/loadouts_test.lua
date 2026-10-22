local loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
local counts = {}
for roll = 1, 4 do
  local id = loadouts.choose(function(low, high) assert(low == 1 and high == 4); return roll end)
  counts[id] = (counts[id] or 0) + 1
  assert(loadouts.template(id))
end
assert(counts.rifle_civilian_v1 == 3 and counts.rifle_field_v1 == 1)
assert(loadouts.template("unknown") == nil)
for _, value in ipairs({ 0, 5, 1.5, "1" }) do
  assert(not pcall(loadouts.choose, function() return value end))
end
print("PASS coherent loadout weighted boundaries and invalid selection")

package.loaded.trkv_participants = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
local members = package.loaded.trkv_participants
local deploy = dofile("tarkov/mods/trkv_raid_core/trkv_deployment.lua")
local state, context = {}, { phase = "active", at_raid = true, sequence = 1 }
members.begin(state, 1)
local specs = { { slot = "one", side = "test", squad = "test", route = {
  { x = 1, y = 1, z = 0 }, { x = 2, y = 1, z = 0 },
} } }
local selections, spawns = 0, 0
local api = {
  select = function() selections = selections + 1; return "rifle_field_v1" end,
  spawn = function(_, _, choice)
    spawns = spawns + 1
    assert(choice == "rifle_field_v1" and state.slots.one.loadout == choice)
    error("Interruption after engine creation")
  end,
  find_slot = function(_, _, choice) assert(choice == "rifle_field_v1"); return { 17 } end,
}
local ok, reason = deploy.ensure(state, context, specs, api)
assert(not ok and reason == "spawn_failed" and selections == 1 and spawns == 1)
-- Deserialization replaces tables; a changed picker must not replace the saved choice.
state = { schema = 1, sequence = 1, closed = false, actors = {},
  slots = { one = { status = "creating", loadout = state.slots.one.loadout } } }
api.select = function() error("Recovery rerolled a saved loadout") end
assert(deploy.ensure(state, context, specs, api))
assert(state.slots.one.loadout == "rifle_field_v1" and state.actors["17"].loadout == "rifle_field_v1")
state.actors["17"] = nil -- Defeated actor: retain the consumed ready slot.
assert(deploy.ensure(state, context, specs, api) and spawns == 1 and selections == 1)
members.begin(state, 2); context.sequence = 2
api.select = function() return {} end
ok, reason = deploy.ensure(state, context, specs, api)
assert(not ok and reason == "selection_failed" and next(state.slots) == nil and spawns == 1)
print("PASS saved loadout before spawn, interrupted recovery, no reroll/respawn and invalid-choice rejection")
