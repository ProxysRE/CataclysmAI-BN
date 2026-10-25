package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
local squad = dofile("tarkov/mods/trkv_raid_core/trkv_squad.lua")
local ctx = { phase = "active", at_raid = true, sequence = 1, dimension = "raid" }
local function report(id, t, x)
  return { sender = id, contact = { source = "vision", seen_at = t, expires_at = t + 30,
    position = { x = x or 8, y = 4, z = 0 } } }
end
local state, a, b = {}, report(20, 100), report(10, 100)
squad.update(state, ctx, 101, { a, b })
assert(state.contact.sender == 10 and state.contact.source == "squad")
assert(state.contact.seen_at == 100 and state.contact.expires_at == 110 and state.observed)
b.contact.position.x = 999
assert(state.contact.position.x == 8)
state.search.goal = { attempts = 3 }
squad.update(state, ctx, 105, { report(20, 105, 99) })
assert(state.contact.position.x == 8 and state.contact.expires_at == 110 and state.search.goal.attempts == 3)
squad.update(state, ctx, 110, {})
assert(state.contact == nil and state.observed)
for _, p in ipairs({report(10, 100), report(10, 112)}) do
  squad.update(state, ctx, 111, {p}); assert(state.contact == nil)
end
local relayed = report(10, 111); relayed.contact.source = "squad"
squad.update(state, ctx, 111, {relayed}); assert(state.contact == nil)
squad.update(state, ctx, 112, {report(10, 112)})
assert(state.contact)
squad.update(state, ctx, 111, {})
assert(state.contact == nil and not state.observed)
squad.update(state, ctx, 113, {report(10, 113)})
squad.update(state, ctx, 114, {}, true)
assert(state.contact == nil and state.search == nil)
ctx.sequence = 2; squad.update(state, ctx, 115, {})
assert(not state.observed)
print("PASS squad report snapshot, deterministic source, fixed deadline/budget, no relay, expiry, clock and raid reset")

ctx.sequence = 1
local contact = report(2, 100).contact
local receiver = { id = 1, side = "usec", squad = "alpha", perception = {status = "none"} }
local donor = { id = 2, side = "usec", squad = "alpha", patrol = {sequence = 1},
  perception = { sequence = 1, dimension = "raid", status = "visible", contact = contact } }
local roster = {schema = 1, sequence = 1, closed = false, actors = {donor}}
local pos, visible, dead, reads = {x = 2, y = 0, z = 0}, true, false, 0
local buddy = { getID = function() return {get_value = function() return 2 end} end,
  is_dead = function() return dead end, get_pos_ms = function() return pos end,
  abs_pos = function() error("Report must not query enemy or buddy absolute position") end }
gapi = { get_all_npcs = function() reads = reads + 1; return {buddy} end }
local actor = {get_pos_ms = function() return {x = 0, y = 0, z = 0} end, sees_creature = function() return visible end}
actor.sees = function() error("Tile visibility cannot authorize creature perception") end
local function observe() receiver.squad_memory = nil; squad.observe_actor(receiver, ctx, actor, roster, 101); return receiver.squad_memory.contact end
assert(observe() and reads == 1)
for _, cause in ipairs({"wall", "invisible", "range", "floor", "dead", "side", "squad", "raid", "dimension", "remembered", "closed"}) do
  visible, dead, pos.x, pos.z = true, false, 2, 0
  donor.side, donor.squad, donor.perception.status = "usec", "alpha", "visible"
  donor.perception.sequence, donor.perception.dimension, roster.closed = 1, "raid", false
  if cause == "wall" or cause == "invisible" then visible = false
  elseif cause == "range" then pos.x = 13
  elseif cause == "floor" then pos.z = 1
  elseif cause == "dead" then dead = true
  elseif cause == "side" then donor.side = "bear"
  elseif cause == "squad" then donor.squad = "other"
  elseif cause == "raid" then donor.perception.sequence = 2
  elseif cause == "dimension" then donor.perception.dimension = "other"
  elseif cause == "remembered" then donor.perception.status = "remembered"
  elseif cause == "closed" then roster.closed = true end
  assert(not observe(), cause)
end
print("PASS local communication requires living visible nearby same-floor same-side same-squad registered donor with personal current observation")

-- Local cooperation never changes the report's lifetime or invents a new
-- search budget. Failure/death/communication loss releases the waiting actor.
local function episode(status)
  return {sequence=1,dimension="raid",last_now=100,status="remembered",
    contact={source="squad",sender=2,seen_at=100,expires_at=110,position={x=8,y=4,z=0}},
    search={sequence=1,dimension="raid",status=status or "searching",
      goal={position={x=8,y=4,z=0},seen_at=100,deadline=110,attempts=2,stalled=0}}}
end
local own, peer = episode(), episode()
local reason, id = squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10)
assert(reason=="wait_for_investigator" and id==3)
assert(not squad.coordinate(own,ctx,101,{{id=20,memory=peer}},10))
peer.search.goal.stalled=4
assert(not squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10))
peer.search.goal.stalled=0; peer.search.status="unreachable"
assert(not squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10))
peer.search.status="checked"; peer.checked_at=101
peer.checked_at=99
assert(not squad.coordinate(own,ctx,101,{{id=20,memory=peer}},10))
peer.checked_at=101
reason,id=squad.coordinate(own,ctx,101,{{id=20,memory=peer}},10)
assert(reason=="report_checked_by_squad" and id==20)
peer.search.status="checked_by_squad" -- no relayed assertion of completion
assert(not squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10))
peer.search.status="searching"; peer.contact.sender=99
assert(not squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10))
peer.contact.sender=2
assert(not squad.coordinate(own,ctx,110,{{id=3,memory=peer}},10))
peer.contact.position.x=9
assert(not squad.coordinate(own,ctx,101,{{id=3,memory=peer}},10))
print("PASS investigator ID priority, fixed report deadline, failed/completed peer, no completion relay and unrelated contact rejection")

receiver={id=10,side="usec",squad="alpha",squad_memory=episode()}
receiver.squad_memory.search={}
donor={id=3,side="usec",squad="alpha",patrol={sequence=1},squad_memory=episode()}
roster={schema=1,sequence=1,closed=false,actors={donor}}
buddy.getID=function() return {get_value=function() return 3 end} end
visible,dead,pos.x,pos.z=true,false,2,0
local moves,steps=1000,0
actor.get_moves=function() return moves end
actor.set_moves=function(_,value) moves=value end
actor.abs_pos=function() return {x=0,y=0,z=0} end
actor.move_towards=function() steps=steps+1; moves=moves-100 end
TripointAbsMs={new=function(x,y,z) return {x=x,y=y,z=z} end}
local map={abs_to_bub=function(_,p) return p end}
assert(squad.step_actor(receiver,ctx,actor,map,101,roster))
assert(moves==900 and steps==0 and receiver.squad_memory.waiting_for==3)
assert(receiver.squad_memory.search.goal==nil and receiver.squad_memory.contact.expires_at==110)
dead=true
assert(squad.step_actor(receiver,ctx,actor,map,102,roster))
assert(steps==1 and receiver.squad_memory.waiting_for==nil and receiver.squad_memory.search.goal.deadline==110)
dead=false; donor.squad_memory.search.status="checked"; donor.squad_memory.checked_at=103
local handled,why=squad.step_actor(receiver,ctx,actor,map,103,roster)
assert(handled and why=="report_checked_by_squad" and steps==1)
assert(receiver.squad_memory.search.finished_by==3)
assert(not squad.step_actor(receiver,ctx,actor,map,104,roster) and steps==1)
print("PASS live adapter waits without moving, resumes after investigator death and accepts visible peer completion once")
