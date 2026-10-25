local positions = dofile("tarkov/mods/trkv_raid_core/trkv_positions.lua")
TripointAbsMs = {new = function(x,y,z) return {x=x,y=y,z=z} end}
local ctx = {phase="active", at_raid=true, sequence=1, dimension="raid"}
local member = {id=10, side="usec", squad="alpha"}
local function plan(x)
  return {schema=1, sequence=1, dimension="raid", last_now=100,
    goal={position={x=x,y=4,z=0}, started_at=100, deadline=108}}
end
local other = {id=20, side="usec", squad="alpha", patrol={sequence=1}, combat=plan(8), reload=plan(8)}
local roster = {schema=1, closed=false, sequence=1, actors={other}}
local point, visible, dead = {x=2,y=0,z=0}, true, false
local buddy = {getID=function() return {get_value=function() return other.id end} end,
  get_pos_ms=function() return point end, is_dead=function() return dead end,
  abs_pos=function() error("Reservation must not query hidden or absolute positions") end}
gapi = {get_all_npcs=function() return {buddy} end}
local actor = {get_pos_ms=function() return {x=0,y=0,z=0} end, sees=function() return visible end}
local function collect(committed, now) return positions.collect(member,ctx,actor,roster,now or 101,committed) end
local list = collect(false)
assert(#list==1 and list[1].x==8) -- duplicate combat/reload claims collapse
other.combat.goal.position.x = 99
assert(list[1].x==8) -- ephemeral result does not share saved tables
other.combat.goal.position.x = 8
assert(#collect(true)==0) -- restored conflict: lower actor ID retains its point
member.id = 30
assert(#collect(true)==1)
assert(#collect(false,108)==0 and #collect(false,99)==0)
for _, cause in ipairs({"wall","range","floor","dead","side","squad","raid","dimension","closed","clock"}) do
  visible, dead, point.x, point.z = true, false, 2, 0
  other.side, other.squad, other.combat.sequence, other.reload.sequence = "usec", "alpha", 1, 1
  other.combat.dimension, other.reload.dimension, roster.closed = "raid", "raid", false
  other.combat.last_now, other.reload.last_now = 100, 100
  if cause=="wall" then visible=false
  elseif cause=="range" then point.x=13
  elseif cause=="floor" then point.z=1
  elseif cause=="dead" then dead=true
  elseif cause=="side" then other.side="bear"
  elseif cause=="squad" then other.squad="other"
  elseif cause=="raid" then other.combat.sequence=2; other.reload.sequence=2
  elseif cause=="dimension" then other.combat.dimension="other"; other.reload.dimension="other"
  elseif cause=="closed" then roster.closed=true
  elseif cause=="clock" then other.combat.last_now=102; other.reload.last_now=102 end
  assert(#collect(false)==0,cause)
end
print("PASS visible local squad position claims, copied/deduplicated exclusions, deterministic conflict priority, expiry and invalid-state rejection")

-- Exercise both production adapters: collection must reach the native selector
-- on creation and revalidation; a later conflicting claim cancels before moving.
package.loaded.trkv_positions = positions
package.loaded.trkv_loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
local reload = dofile("tarkov/mods/trkv_raid_core/trkv_reload.lua")
local combat = dofile("tarkov/mods/trkv_raid_core/trkv_combat.lua")
other.combat.last_now, other.reload.last_now = 100, 100
member.loadout = "rifle_field_v1"
member.perception = {sequence=1, dimension="raid", status="visible",
  contact={position={x=0,y=0,z=0},seen_at=100,expires_at=130}}
local moves, steps = 1000, 0
actor.can_reload_empty_gun = function() return true end
actor.get_moves = function() return moves end
actor.set_moves = function(_, value) moves=value end
actor.abs_pos = function() return {x=2,y=4,z=0} end
actor.move_towards = function() steps=steps+1; moves=moves-100 end
actor.reload_cover_status = function() return "reserved_cover" end
local function select(committed, excluded)
  assert(#excluded==1)
  if committed and excluded[1].x==committed.x then return nil end
  return committed or {x=9,y=4,z=0}
end
actor.choose_reload_cover = function(_,p,committed,excluded) return select(committed,excluded) end
actor.choose_standoff_position = function(_,p,committed,lane,excluded)
  if lane and not committed then return nil end
  return select(committed,excluded)
end
local map = {abs_to_bub=function(_,p) return p end}
for _, controller in ipairs({reload,combat}) do
  member.reload, member.combat = nil, nil
  other.combat.goal.position.x, other.reload.goal.position.x = 8, 8
  assert(controller.step_actor(member,ctx,actor,map,101,roster))
  local before, count = moves, steps
  other.combat.goal.position.x, other.reload.goal.position.x = 9, 9
  local handled, reason = controller.step_actor(member,ctx,actor,map,102,roster)
  assert(not handled and (reason=="invalid_cover" or reason=="invalid_position"))
  assert(moves==before and steps==count)
end
print("PASS combat/reload adapters pass squad exclusions on selection and validation, cancelling conflicting approaches before movement")
