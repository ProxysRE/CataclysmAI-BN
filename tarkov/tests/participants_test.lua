local members = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
local state = {}
assert(members.begin(state, 1))
local context = { phase = "active", at_raid = true, sequence = 1 }
local route = { { x = 402, y = 392, z = 0, actor = io.stdout }, { x = 402, y = 393, z = 0 } }
local first = assert(members.register(state, 1, 10, "usec", "alpha", route))
local second = assert(members.register(state, 1, 11, "usec", "beta", route))
local third = assert(members.register(state, 1, 12, "bear", "beta", route))
assert(not members.find(nil, context, 10))
assert(not members.find({ schema = 1 }, context, 10))
assert(members.find(state, context, 10) == first)
assert(first.squad ~= second.squad and second.side ~= third.side)
route[1].x = 0
first.patrol.index = 2
assert(first.patrol.route[1].x == 402 and first.patrol.route[1].actor == nil)
assert(second.patrol.index == 1 and second.patrol.route[1].x == 402)
assert(not members.register(state, 1, 10, "bear", "changed", route))
assert(first.side == "usec" and first.squad == "alpha")
assert(members.begin(state, 1) and members.find(state, context, 10) == first)
for _, id in ipairs({ -1, 0, 1.5, 2147483648, "10" }) do
  assert(not members.register(state, 1, id, "usec", "alpha", route))
  assert(not members.find(state, context, id))
end
assert(not members.register(state, 2, 20, "usec", "alpha", route))
assert(not members.register(state, 1, 20, "", "alpha", route))
assert(not members.register(state, 1, 20, "usec", {}, route))
assert(not members.register(state, 1, 20, "usec", "alpha", { { x = "402", y = 1, z = 0 } }))
for _, invalid in ipairs({
  { phase = "home", at_raid = true, sequence = 1 },
  { phase = "active", at_raid = false, sequence = 1 },
  { phase = "active", at_raid = true, sequence = 2 },
}) do assert(not members.find(state, invalid, 10)) end
assert(not members.finish(state, 2) and members.find(state, context, 10) == first)
assert(members.finish(state, 1) and next(state.actors) == nil)
assert(not members.find(state, context, 10))
assert(not members.begin(state, 1)) -- A closed raid cannot be resurrected by a retry.
assert(members.begin(state, 2) and not members.begin(state, 1))
assert(next(state.actors) == nil)
assert(not pcall(members.initialize, { schema = 99 }))
print("PASS participant identity, separate side/squad, no shared routes or userdata, duplicate/stale rejection and cleanup")
