package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
local hearing = dofile("tarkov/mods/trkv_raid_core/trkv_hearing.lua")
local ctx = { phase = "active", at_raid = true, sequence = 1, dimension = "raid" }
local state = {}
local event = "raid|100|6|10|0|combat"
hearing.update(state, ctx, 101, event)
assert(state.status == "remembered" and state.contact.source == "sound")
assert(state.contact.position.x == 6 and state.contact.radius == 2)
assert(state.contact.seen_at == 100 and state.contact.expires_at == 120)
local first_contact = state.contact
hearing.update(state, ctx, 110, event)
assert(state.contact == first_contact and state.contact.expires_at == 120)
hearing.update(state, ctx, 111, "raid|111|6|10|0|movement")
assert(state.contact == first_contact and state.contact.expires_at == 120)
-- Restored plain memory cannot reconsume the saved NPC inbox or extend its age.
local function copy(v)
  if type(v) ~= "table" then return v end
  local t = {}; for k, x in pairs(v) do t[k] = copy(x) end; return t
end
state = copy(state)
hearing.update(state, ctx, 119, "raid|111|6|10|0|movement")
assert(state.contact.seen_at == 100)
hearing.update(state, ctx, 120, "raid|111|6|10|0|movement")
assert(state.contact == nil and state.status == "none")
hearing.update(state, ctx, 121, "raid|111|6|10|0|movement")
assert(state.contact == nil)
for _, invalid in ipairs({ "other|121|6|10|0|combat", "raid|200|6|10|0|combat",
    "raid|121|7|10|0|combat", "raid|121|6|10|0|speech", "garbage" }) do
  hearing.update(state, ctx, 121, invalid)
  assert(state.contact == nil)
end
-- A genuinely fresh event may start another episode; unrelated regions replace it.
hearing.update(state, ctx, 122, "raid|122|-2|-6|0|combat")
assert(state.contact.position.x == -2 and state.contact.position.y == -6)
hearing.update(state, ctx, 123, "raid|123|10|10|0|movement")
assert(state.contact.position.x == 10 and state.contact.expires_at == 143)
ctx.sequence = 2
hearing.update(state, ctx, 124, "raid|123|10|10|0|movement")
assert(state.contact == nil and not state.observed)
ctx.phase = "cleanup"
assert(not hearing.update(state, ctx, 125, event))
print("PASS anonymous hearing region, original expiry, inbox replay, repeated area, malformed/future/cross-raid input")

ctx.phase, ctx.sequence = "active", 1
state = {}
hearing.update(state, ctx, 100, "raid|100|6|10|0|combat")
local position, moves, selections, blocked = { x = 0, y = 0, z = 0 }, 1000, 0, false
local choice = { x = 4, y = 8, z = 0 } -- Reachable edge; center may be a wall.
local api = {
  in_region = function(p)
    return position.z == p.z and position.x >= p.x - 2 and position.x < p.x + 2 and
      position.y >= p.y - 2 and position.y < p.y + 2
  end,
  position = function() return position end,
  moves = function() return moves end,
  wait = function() moves = moves - 100 end,
  choose_entry = function() selections = selections + 1; return choice end,
  move_to = function(p)
    assert(p.x == choice.x and p.y == choice.y)
    if not blocked then
      position = { x = position.x + 1, y = p.y, z = p.z }; moves = moves - 100
    end
  end,
}
assert(hearing.step(state, ctx, 101, api))
assert(state.entry.x == 4 and selections == 1 and state.search.goal.attempts == 1)
state = copy(state)
assert(hearing.step(state, ctx, 102, api) and selections == 1)
assert(state.search.goal.attempts == 2 and state.entry.x == 4)
blocked = true
assert(hearing.step(state, ctx, 103, api))
assert(hearing.step(state, ctx, 104, api) and selections == 1)
assert(state.search.goal.stalled == 2)
choice, blocked = { x = 7, y = 11, z = 0 }, false
assert(hearing.step(state, ctx, 105, api))
assert(selections == 2 and state.entry.x == 7 and state.search.goal.attempts == 5)
assert(state.search.goal.deadline == 120 and state.search.goal.stalled == 0)
assert(hearing.step(state, ctx, 106, api))
local ok, reason = hearing.step(state, ctx, 107, api)
assert(ok and reason == "sound_checked")
assert(not hearing.step(state, ctx, 108, api) and selections == 2)
-- A fully unavailable region spends bounded waits, never a hidden-target fallback.
hearing.update(state, ctx, 110, "raid|110|14|18|0|combat")
assert(state.entry == nil)
choice = nil
for time = 111, 114 do assert(hearing.step(state, ctx, time, api)) end
ok, reason = hearing.step(state, ctx, 115, api)
assert(ok and reason == "sound_unreachable" and state.search.goal.attempts == 4)
assert(state.search.goal.deadline == 130)
local before = selections
assert(not hearing.step(state, ctx, 116, api) and selections == before)
print("PASS reachable hearing entry, stable saved approach, bounded reselection and unavailable area")
