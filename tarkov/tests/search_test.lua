local search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
local ctx = { phase = "active", at_raid = true, sequence = 7, dimension = "raid" }
local state, memory = {}, { sequence = 7, dimension = "raid", status = "visible" }
local p, moves, walks, waits, blocked = { x = 0, y = 0, z = 0 }, 1000, 0, 0, false
local api = {
  at = function(q) return p.x == q.x and p.y == q.y and p.z == q.z end,
  position = function() return p end,
  moves = function() return moves end,
  wait = function() moves = moves - 100; waits = waits + 1 end,
  move_to = function(q)
    walks = walks + 1
    if not blocked then p = { x = p.x + 1, y = q.y, z = q.z }; moves = moves - 100 end
  end,
}
assert(not search.step(state, ctx, memory, 100, api))
memory.status = "remembered"
memory.contact = { position = { x = 2, y = 0, z = 0 }, seen_at = 100, expires_at = 130 }
assert(search.step(state, ctx, memory, 101, api) and p.x == 1)
local function copy(v)
  if type(v) ~= "table" then return v end
  local t = {}; for k, x in pairs(v) do t[k] = copy(x) end; return t
end
state = copy(state)
assert(search.step(state, ctx, memory, 102, api) and p.x == 2)
assert(state.goal.attempts == 2 and state.goal.deadline == 130)
local ok, reason = search.step(state, ctx, memory, 103, api)
assert(ok and reason == "checked" and waits == 1)
local before = walks
assert(not search.step(state, ctx, memory, 104, api) and walks == before)
-- A fresh visible contact is the only way to rearm a completed search.
memory.status = "visible"
search.step(state, ctx, memory, 105, api)
memory.status = "remembered"; memory.contact.seen_at = 105; memory.contact.expires_at = 135
memory.contact.position.x = 9; blocked = true
for i = 1, 4 do assert(search.step(state, ctx, memory, 105 + i, api)) end
assert(state.goal.stalled == 4 and state.goal.attempts == 4)
ok, reason = search.step(state, ctx, memory, 110, api)
assert(ok and reason == "unreachable")
before = walks
assert(not search.step(state, ctx, memory, 111, api) and walks == before)
search.step(state, ctx, memory, 135, api)
assert(state.status == "expired" and state.goal.deadline == 135)
-- Even successful movement cannot extend the attempt budget indefinitely.
memory.status = "visible"; search.step(state, ctx, memory, 140, api)
memory.status = "remembered"; memory.contact.seen_at = 140; memory.contact.expires_at = 200
memory.contact.position.x = 100; blocked = false
for i = 1, 12 do assert(search.step(state, ctx, memory, 140 + i, api)) end
ok, reason = search.step(state, ctx, memory, 153, api)
assert(ok and reason == "unreachable" and state.goal.attempts == 12)
ctx.sequence = 8
assert(not search.step(state, ctx, memory, 154, api) and not state.observed and not state.goal)
ctx.phase = "cleanup"; before = walks
assert(not search.step(state, ctx, memory, 155, api) and walks == before)
print("PASS bounded search, arrival, blocked/attempt budgets, reload, expiry, reacquisition and stale raid")
