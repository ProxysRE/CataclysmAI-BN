local participants = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
package.loaded.trkv_participants = participants
local deploy = dofile("tarkov/mods/trkv_raid_core/trkv_deployment.lua")
local state, context = {}, { phase = "active", at_raid = true, sequence = 1 }
assert(participants.begin(state, 1))
local specs = {}
for i = 1, 3 do
  specs[i] = { slot = "guard_" .. i, side = i == 3 and "bear" or "usec", squad = "test",
    route = { { x = 400 + i, y = 398, z = 0 }, { x = 400 + i, y = 399, z = 0 } } }
end
local calls, next_id, tagged, fail_slot = 0, 100, {}, nil
local api = {
  spawn = function(spec, sequence)
    calls, next_id = calls + 1, next_id + 1
    tagged[sequence .. ":" .. spec.slot] = { next_id }
    if fail_slot == spec.slot then error("Interrupted after engine creation") end
    return next_id
  end,
  find_slot = function(sequence, slot) return tagged[sequence .. ":" .. slot] or {} end,
}
assert(deploy.ensure(state, context, specs, api) and calls == 3)
assert(deploy.ensure(state, context, specs, api) and calls == 3)
assert(state.actors["101"].side == "usec" and state.actors["103"].side == "bear")
state.actors["102"].patrol.index = 2
state.slots.guard_2 = { status = "creating" }
assert(deploy.ensure(state, context, specs, api) and calls == 3)
assert(state.actors["102"].patrol.index == 2)
-- A defeated/missing actor is not re-created by repeating deployment.
state.actors["101"] = nil
tagged["1:guard_1"] = nil
assert(deploy.ensure(state, context, specs, api) and calls == 3)
local function copy(value)
  if type(value) ~= "table" then return value end
  local result = {}; for k, v in pairs(value) do result[k] = copy(v) end; return result
end
state = copy(state)
assert(deploy.ensure(state, context, specs, api) and calls == 3)
assert(participants.finish(state, 1) and next(state.slots) == nil)
assert(not deploy.ensure(state, context, specs, api) and calls == 3)
context.sequence = 2
assert(participants.begin(state, 2))
fail_slot = "guard_2"
local ok, reason = deploy.ensure(state, context, specs, api)
assert(not ok and reason == "spawn_failed" and calls == 5)
assert(state.slots.guard_1.status == "ready" and state.slots.guard_2.status == "creating")
state = copy(state) -- saved partial deployment
fail_slot = nil
assert(deploy.ensure(state, context, specs, api) and calls == 6)
assert(state.slots.guard_2.id == 105 and state.slots.guard_3.id == 106)
-- Ambiguous recovery fails closed, with no additional spawning.
state.slots.guard_2 = { status = "creating" }
tagged["2:guard_2"] = { 105, 999 }
ok, reason = deploy.ensure(state, context, specs, api)
assert(not ok and reason == "duplicate_slot" and calls == 6)
tagged["2:guard_2"] = {}
ok, reason = deploy.ensure(state, context, specs, api)
assert(not ok and reason == "pending" and calls == 6)
context.at_raid = false
assert(not deploy.ensure(state, context, specs, api) and calls == 6)
context.at_raid = true
local invalid = copy(specs); invalid[2].slot = invalid[1].slot
ok, reason = deploy.ensure(state, context, invalid, api)
assert(not ok and reason == "invalid_manifest" and calls == 6)
invalid = copy(specs); invalid[1].route[1].x = "400"
assert(not deploy.ensure(state, context, invalid, api) and calls == 6)
print("PASS encounter deployment: three slots, save/load, no respawn, partial creation recovery and ambiguous/missing fail closed")


-- A known no-spawn state can wait; an uncertain creating state cannot respawn.
local waiting, wait_context = {}, { phase = "active", at_raid = true, sequence = 1 }
participants.begin(waiting, 1)
local picks, attempts, free = 0, 0, false
local wait_api = {
  select = function() picks = picks + 1; return "saved_variant" end,
  available = function() return free end,
  spawn = function() attempts = attempts + 1; return 500 end,
  find_slot = function() error("Reserved slot must not reconcile an unattempted creation") end,
}
local one = { specs[1] }
local ok, reason = deploy.ensure(waiting, wait_context, one, wait_api)
assert(not ok and reason == "blocked" and picks == 1 and attempts == 0)
assert(waiting.slots.guard_1.status == "reserved" and waiting.slots.guard_1.loadout == "saved_variant")
waiting = copy(waiting)
assert(not deploy.ensure(waiting, wait_context, one, wait_api) and picks == 1 and attempts == 0)
wait_api.available = function() error("Read-only placement probe failed") end
ok, reason = deploy.ensure(waiting, wait_context, one, wait_api)
assert(not ok and reason == "placement_failed" and waiting.slots.guard_1.status == "reserved" and attempts == 0)
wait_api.available = function() return true end
assert(deploy.ensure(waiting, wait_context, one, wait_api) and picks == 1 and attempts == 1)
waiting.actors["500"] = nil
assert(deploy.ensure(waiting, wait_context, one, wait_api) and attempts == 1)
print("PASS reserved occupied slot, save/load without reroll, placement failure retry and no respawn after creation")
