local memory = dofile("tarkov/mods/trkv_raid_core/trkv_perception.lua")
local context = { phase = "active", at_raid = true, sequence = 7, dimension = "raid" }
local state, visible, position_reads = {}, true, 0
local p = { x = 10, y = 20, z = 0 }
local target = {
  get_pos_ms = function() error("Target tile must not be read before creature visibility") end,
  abs_pos = function() position_reads = position_reads + 1; return p end,
}
local actor = { current_target = function() return target end, sees = function() error("Tile visibility is insufficient") end,
  sees_creature = function(_, other) assert(other == target); return visible end }
assert(memory.observe_actor(state, context, actor, 100, 30))
assert(state.status == "visible" and state.contact.position.x == 10)
p.x, visible = 99, false
memory.observe_actor(state, context, actor, 105, 30)
assert(position_reads == 1 and state.status == "remembered")
assert(state.contact.position.x == 10 and state.contact.expires_at == 130)
-- A serialized copy remains independent; load does not refresh either timestamp.
local function copy(v)
  if type(v) ~= "table" then return v end
  local result = {}; for k, value in pairs(v) do result[k] = copy(value) end
  return result
end
state = copy(state)
memory.observe_actor(state, context, actor, 129, 30)
assert(state.contact.seen_at == 100 and state.contact.expires_at == 130)
memory.observe_actor(state, context, actor, 130, 30)
assert(state.status == "none" and state.contact == nil and position_reads == 1)
visible = true
memory.observe_actor(state, context, actor, 140, 30)
assert(state.contact.position.x == 99)
visible = false
context.dimension = "other"
memory.observe_actor(state, context, actor, 141, 30)
assert(state.contact == nil)
visible = true
memory.observe_actor(state, context, actor, 150, 30)
context.sequence = 8; visible = false
memory.observe_actor(state, context, actor, 151, 30)
assert(state.contact == nil)
visible = true
memory.observe_actor(state, context, actor, 160, 30)
visible = false
memory.observe_actor(state, context, actor, 159, 30)
assert(state.contact == nil)
context.phase = "cleanup"
local before = position_reads
-- Inactive update is rejected without altering persisted state.
assert(not memory.update(state, context, 200, nil, 30))
assert(position_reads == before)
print("PASS visual memory, hidden position isolation, expiration, reload, dimension and sequence isolation")
