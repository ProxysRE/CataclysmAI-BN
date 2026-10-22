local patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
local function saved(index)
  return { sequence = 7, index = index or 1, route = {
    { x = 1, y = 1, z = 0 }, { x = 1, y = 2, z = 0 },
  } }
end
local state = saved()
local context = { phase = "active", sequence = 7, at_raid = true }
local position, moves, calls, threat, danger, blocked = state.route[1], 1000, 0, false, 0, false
local api = {
  has_target = function() return threat end,
  danger = function() return danger end,
  at = function(p) return p.x == position.x and p.y == position.y and p.z == position.z end,
  moves = function() return moves end,
  move_to = function(p)
    calls = calls + 1
    if not blocked then position, moves = p, moves - 100 end
  end,
}
assert(patrol.step(state, context, api))
assert(state.index == 2 and position.y == 2 and calls == 1 and moves == 900)
assert(patrol.step(state, context, api))
assert(state.index == 1 and position.y == 1 and calls == 2)
-- Returning false must leave all available actions for BN's own decision.
for _, observation in ipairs({ "target", "danger" }) do
  threat, danger = observation == "target", observation == "danger" and 1 or 0
  local handled, reason = patrol.step(state, context, api)
  assert(not handled and reason == "threat" and calls == 2 and moves == 800)
end
threat, danger, blocked = false, 0, true
local handled, reason = patrol.step(state, context, api)
assert(not handled and reason == "blocked" and moves == 800)
local before = calls
for _, field in ipairs({ "phase", "sequence", "at_raid" }) do
  local invalid = { phase = "active", sequence = 7, at_raid = true }
  invalid[field] = ({ phase = "cleanup", sequence = 8, at_raid = false })[field]
  assert(not patrol.step(state, invalid, api))
  assert(calls == before)
end
-- Deserialized plain state resumes the saved waypoint, with no actor reference.
blocked = false
state = saved(2)
assert(patrol.step(state, context, api) and position.y == 2)
assert(not patrol.step({ sequence = 7, route = {} }, context, api))
assert(not patrol.step(saved(99), context, api))
print("PASS patrol loop, action budget, threat handoff, blocked fallback, stale raid and restored route")

-- A distant waypoint stays selected until reached. Opening a door spends actions
-- without changing position and must still count as a handled patrol decision.
state = { sequence = 7, index = 1, route = { { x = 1, y = 1, z = 0 }, { x = 1, y = 4, z = 0 } } }
position, moves = state.route[1], 1000
local door_closed = true
api.move_to = function(p)
  moves = moves - 100
  if door_closed then door_closed = false; return end
  position = { x = 1, y = position.y + (p.y > position.y and 1 or -1), z = 0 }
end
assert(patrol.step(state, context, api) and state.index == 2 and position.y == 1 and moves == 900)
for expected = 2, 4 do
  assert(patrol.step(state, context, api) and state.index == 2 and position.y == expected)
end
assert(patrol.step(state, context, api) and state.index == 1 and position.y == 3)
print("PASS distant waypoints and door action retain target until arrival")
