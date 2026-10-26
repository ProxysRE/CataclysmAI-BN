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
