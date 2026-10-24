package.loaded.trkv_perception = dofile("tarkov/mods/trkv_raid_core/trkv_perception.lua")
package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
package.loaded.trkv_hearing = dofile("tarkov/mods/trkv_raid_core/trkv_hearing.lua")
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
  get_value = function() return "" end,
  avoid_immediate_danger = function() return "" end,
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

-- Hazards override both a visible fight and a remembered search. They do not
-- consume search attempts or renew the contact deadline while taking priority.
ctx.phase = "active"
member = { patrol = { sequence = 1, index = 1, route = {} } }
local hazard = "field"
actor.avoid_immediate_danger = function() moves = moves - 100; return hazard end
visible = true
ok, reason = decision.step_actor(member, ctx, actor, map, 200)
assert(ok and reason == "escape_field" and member.search.goal == nil)
visible = false
actor.avoid_immediate_danger = function() return "" end
actor.move_towards = function(_, q) destination = q; moves = moves - 100 end
assert(decision.step_actor(member, ctx, actor, map, 201))
local deadline, attempts = member.search.goal.deadline, member.search.goal.attempts
actor.avoid_immediate_danger = function() moves = moves - 100; return "explosive" end
ok, reason = decision.step_actor(member, ctx, actor, map, 202)
assert(ok and reason == "escape_explosive" and member.search.goal.attempts == attempts)
assert(member.search.goal.deadline == deadline and member.perception.contact.seen_at == 200)
ok, reason = decision.step_actor(member, ctx, actor, map, 230)
assert(ok and reason == "escape_explosive" and member.perception.contact == nil)
actor.avoid_immediate_danger = function() return "" end
decision.step_actor(member, ctx, actor, map, 231)
assert(member.search.status == "expired" and member.search.goal.deadline == deadline)
ctx.phase = "cleanup"
actor.avoid_immediate_danger = function() error("Inactive callback entered hazard executor") end
assert(not decision.step_actor(member, ctx, actor, map, 232))
print("PASS hazard priority over combat/search, preserved attempt budget and aging contact during escape")

-- Sound investigation uses its region, never turns an anonymous noise into a
-- visual target, and returns to owned waiting after completion/expiry.
ctx.phase = "active"
member = { patrol = { sequence = 1, index = 1, route = {} } }
local packet = "raid|300|6|10|0|combat"
actor.get_value = function(_, key) assert(key == "trkv_heard_noise"); return packet end
actor.current_target = function() return nil end
actor.avoid_immediate_danger = function() return "" end
ok, reason = decision.step_actor(member, ctx, actor, map, 301)
assert(ok and reason == "sound_searching" and destination.x == 6 and destination.y == 10)
assert(member.perception.contact == nil and member.hearing.contact.source == "sound")
local sound_deadline = member.hearing.contact.expires_at
origin.x, origin.y = 4, 8 -- Enter the region; do not require its exact center.
ok, reason = decision.step_actor(member, ctx, actor, map, 302)
assert(ok and reason == "sound_checked")
ok, reason = decision.step_actor(member, ctx, actor, map, 303)
assert(ok and reason == "wait_no_route" and member.hearing.contact.expires_at == sound_deadline)
packet = "raid|304|6|10|0|movement"
ok, reason = decision.step_actor(member, ctx, actor, map, 304)
assert(ok and reason == "wait_no_route" and member.hearing.search.status == "checked")
ok, reason = decision.step_actor(member, ctx, actor, map, 320)
assert(ok and reason == "wait_no_route" and member.hearing.contact == nil)
-- A real visual target takes precedence over fresh anonymous sound.
visible = true; actor.current_target = function() return target end
packet = "raid|321|14|18|0|combat"
ok, reason = decision.step_actor(member, ctx, actor, map, 321)
assert(not ok and reason == "threat" and member.perception.status == "visible")
assert(member.hearing.search.goal == nil)
print("PASS anonymous sound investigation, region arrival, no replay/rearm, expiry and visual priority")
