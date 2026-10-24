package.loaded.trkv_perception = dofile("tarkov/mods/trkv_raid_core/trkv_perception.lua")
package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
package.loaded.trkv_patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
local decision = dofile("tarkov/mods/trkv_raid_core/trkv_decision.lua")
TripointAbsMs = { new = function(x, y, z) return { x = x, y = y, z = z } end }
local map = { abs_to_bub = function(_, p) return p end }
local ctx = { phase = "active", at_raid = true, sequence = 1, dimension = "raid" }
local member = { patrol = { sequence = 1, index = 1, route = {} } }
local visible, p, moves, reads, destination = true, { x = 2, y = 2, z = 0 }, 1000, 0, nil
local target = { get_pos_ms = function() return p end,
  abs_pos = function() assert(visible); reads = reads + 1; return p end }
local origin = { x = 1, y = 2, z = 0 }
local actor = {
  current_target = function() return target end, -- Includes a deliberately stale cache.
  sees = function() return visible end,
  get_pos_ms = function() return origin end,
  abs_pos = function() return origin end,
  get_moves = function() return moves end,
  set_moves = function(_, n) moves = n end,
  danger_assessment = function() return 99 end,
  move_towards = function(_, q) destination = q; moves = moves - 100 end,
}
local ok, reason = decision.step_actor(member, ctx, actor, map, 100)
assert(not ok and reason == "threat" and moves == 1000)
visible = false; p.x = 99
ok, reason = decision.step_actor(member, ctx, actor, map, 101)
assert(ok and reason == "searching" and reads == 1 and destination.x == 2 and moves == 900)
-- Returning no_route after expiry must spend a turn instead of invoking vanilla
-- with the stale target or positive danger. The same holds for blocked routes.
ok, reason = decision.step_actor(member, ctx, actor, map, 130)
assert(ok and reason == "wait_no_route" and moves == 800 and reads == 1)
member.patrol.route = { { x = 4, y = 2, z = 0 }, { x = 5, y = 2, z = 0 } }
ok, reason = decision.step_actor(member, ctx, actor, map, 131)
assert(ok and reason == "patrol" and destination.x == 4 and reads == 1)
actor.move_towards = function() end
ok, reason = decision.step_actor(member, ctx, actor, map, 132)
assert(ok and reason == "wait_blocked" and moves == 600)
visible = true
ok, reason = decision.step_actor(member, ctx, actor, map, 133)
assert(not ok and reason == "threat" and member.search.goal == nil and reads == 2)
ctx.phase = "cleanup"
assert(not decision.step_actor(member, ctx, actor, map, 134) and reads == 2)
print("PASS decision integration, visible combat handoff, immutable hidden goal and no post-search hidden fallback")
