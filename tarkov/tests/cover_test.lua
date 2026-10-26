package.loaded.trkv_loadouts=dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
local cover=dofile("tarkov/mods/trkv_raid_core/trkv_cover.lua")
local ctx={phase="active",at_raid=true,sequence=1,dimension="raid"}
local point={x=8,y=4,z=0}
local member={id=10,side="usec",squad="alpha",loadout="rifle_field_v1",
  perception={sequence=1,dimension="raid",status="visible",contact={position=point,seen_at=100,expires_at=130}}}
local plan={schema=1,sequence=1,dimension="raid",last_now=100,
  goal={target=point,position={x=6,y=5,z=0},started_at=100,deadline=108,attempts=1,stalled=0}}
local other={id=20,side="usec",squad="alpha",patrol={sequence=1},combat=plan}
local roster={sequence=1,closed=false,actors={other}}
local visible,dead,calls,moves=true,false,0,1000
local buddy={getID=function() return {get_value=function() return other.id end} end,
  get_pos_ms=function() return {x=2,y=0,z=0} end,is_dead=function() return dead end}
gapi={get_all_npcs=function() return {buddy} end}
TripointAbsMs={new=function(x,y,z) return {x=x,y=y,z=z} end}
local result="cover_fire"
local actor={get_pos_ms=function() return {x=0,y=0,z=0} end,sees_creature=function() return visible end,
  cover_visible_target=function(_,p) assert(p.x==8);calls=calls+1;if result~="" then moves=moves-200 end;return result end}
local ok,why=cover.step_actor(member,ctx,actor,101,roster)
assert(ok and why=="cover_fire" and calls==1 and moves==800 and member.cover.buddy==20)
-- A same-turn pair cannot both stop moving to cover each other.
member.id=30
assert(not cover.step_actor(member,ctx,actor,101,roster) and calls==1 and member.cover==nil)
-- Empty-weapon approaches take support regardless of actor ID.
other.reload,other.combat=plan,nil;plan.goal.threat,plan.goal.target=point,nil
result="cover_aim"
assert(cover.step_actor(member,ctx,actor,101,roster) and calls==2)
for _,cause in ipairs({"lost","dead","hidden","expired","stale","shifted","blocked","recruit","side","squad"}) do
  member.perception.status,member.loadout="visible","rifle_field_v1"
  visible,dead,plan.last_now,plan.goal.deadline,plan.goal.stalled=true,false,100,108,0
  other.side,other.squad="usec","alpha"; plan.goal.threat={x=8,y=4,z=0}
  if cause=="lost" then member.perception.status="remembered"
  elseif cause=="dead" then dead=true
  elseif cause=="hidden" then visible=false
  elseif cause=="expired" then plan.goal.deadline=101
  elseif cause=="stale" then plan.last_now=97
  elseif cause=="shifted" then plan.goal.threat.x=10
  elseif cause=="blocked" then plan.goal.stalled=2
  elseif cause=="recruit" then member.loadout="rifle_recruit_field_v1"
  elseif cause=="side" then other.side="bear"
  elseif cause=="squad" then other.squad="other" end
  local before=calls
  assert(not cover.step_actor(member,ctx,actor,101,roster) and calls==before and member.cover==nil,cause)
end
other.squad="alpha";result=""
assert(not cover.step_actor(member,ctx,actor,101,roster) and member.cover==nil)
print("PASS support role: local visible moving peer, deterministic combat priority, reload precedence, real action ownership and cancellation")

-- A loaded supporter prioritizes an empty-gun approach over a combat move,
-- independent of table enumeration order and actor ID ordering for reload.
local function clone(v)
  if type(v) ~= "table" then return v end
  local r = {}; for k, x in pairs(v) do r[k] = clone(x) end; return r
end
member.id,member.loadout,member.perception.status=10,"rifle_field_v1","visible"
visible,dead,result=true,false,"cover_fire"
plan.last_now,plan.goal.deadline,plan.goal.stalled=100,108,0
plan.goal.threat={x=8,y=4,z=0}
other.side,other.squad,other.reload,other.combat="usec","alpha",nil,clone(plan)
local empty={id=5,side="usec",squad="alpha",patrol={sequence=1},reload=clone(plan)}
local empty_body={getID=function() return {get_value=function() return 5 end} end,
  get_pos_ms=function() return {x=3,y=0,z=0} end,is_dead=function() return false end}
local incumbent={id=7,side="usec",squad="alpha",patrol={sequence=1},perception=clone(member.perception)}
local incumbent_dead,incumbent_hidden,incumbent_far=false,false,false
local incumbent_body={getID=function() return {get_value=function() return 7 end} end,
  get_pos_ms=function() return {x=incumbent_far and 30 or 4,y=0,z=0} end,
  is_dead=function() return incumbent_dead end}
actor.sees_creature=function(_,b) return b~=incumbent_body or not incumbent_hidden end
gapi.get_all_npcs=function() return {incumbent_body,buddy,empty_body} end
roster.actors={incumbent,other,empty}
assert(cover.step_actor(member,ctx,actor,101,roster) and member.cover.buddy==5 and member.cover.kind=="reload")
incumbent.cover=clone(member.cover)
-- A recent visible actual support action prevents duplicate support. The actor
-- can support a different unclaimed mover instead of holding the whole group.
assert(cover.step_actor(member,ctx,actor,101,roster) and member.cover.buddy==20 and member.cover.kind=="combat")
other.combat=nil
local before_claim=calls
local handled,reason=cover.step_actor(member,ctx,actor,101,roster)
assert(not handled and reason=="peer_already_covered" and calls==before_claim and member.cover==nil)
-- Repeated refusal does not refresh the owner's timestamp or spend moves.
assert(not cover.step_actor(member,ctx,actor,102,roster) and incumbent.cover.at==101 and calls==before_claim)
for _,cause in ipairs({"dead","hidden","far","stale","future","side","lost_contact","shifted_contact","old_raid"}) do
  incumbent_dead,incumbent_hidden,incumbent_far=false,false,false
  incumbent.cover.at,incumbent.cover.sequence,incumbent.side=101,1,"usec"
  incumbent.perception=clone(member.perception)
  empty.reload.last_now=100
  local now=102
  if cause=="dead" then incumbent_dead=true
  elseif cause=="hidden" then incumbent_hidden=true
  elseif cause=="far" then incumbent_far=true
  elseif cause=="stale" then now=104; plan.last_now=104;empty.reload.last_now=104
  elseif cause=="future" then incumbent.cover.at=103
  elseif cause=="side" then incumbent.side="bear"
  elseif cause=="lost_contact" then incumbent.perception.status="remembered"
  elseif cause=="shifted_contact" then incumbent.perception.contact.position.x=20
  elseif cause=="old_raid" then incumbent.cover.sequence=0 end
  assert(cover.step_actor(member,ctx,actor,now,roster) and member.cover.buddy==5,cause)
end
-- A restored plain role still prevents duplicates; after expiration a new
-- supporter can take over without changing the mover's original plan deadline.
incumbent_dead,incumbent_hidden,incumbent_far=false,false,false
incumbent.side,incumbent.perception="usec",clone(member.perception)
incumbent.cover={schema=1,sequence=1,dimension="raid",at=104,buddy=5,action="cover_aim"}
roster=clone(roster) -- No live engine objects in the saved membership/role data.
local deadline=roster.actors[3].reload.goal.deadline
assert(not cover.step_actor(member,ctx,actor,105,roster))
roster.actors[3].reload.last_now=107
assert(cover.step_actor(member,ctx,actor,107,roster))
assert(roster.actors[3].reload.goal.deadline==deadline)
print("PASS reload priority, one local supporter, alternative mover, saved role, bounded takeover and invalid-owner release")
