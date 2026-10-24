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
