-- First local support action: hold and fire while a visible squadmate moves.
local loadouts = require("trkv_loadouts")
local cover = {}
function cover.supports(plan, ctx, now, observed)
  local goal = plan and plan.goal
  local threat = goal and (goal.threat or goal.target)
  return plan and plan.schema == 1 and plan.sequence == ctx.sequence and plan.dimension == ctx.dimension and
    goal and threat and now >= goal.started_at and now < goal.deadline and
    (not plan.last_now or (now >= plan.last_now and now - plan.last_now <= 2)) and
    type(goal.attempts) == "number" and type(goal.stalled) == "number" and
    goal.attempts > 0 and goal.attempts < 4 and goal.stalled < 2 and
    threat.z == observed.z and math.max(math.abs(threat.x-observed.x), math.abs(threat.y-observed.y)) <= 1
end
function cover.step_actor(member, ctx, actor, now, roster)
  member.cover = nil
  local profile = member.loadout and loadouts.describe(member.loadout)
  local memory = member.perception
  if ctx.phase ~= "active" or not ctx.at_raid then return false, "inactive" end
  if not profile or profile.profile ~= "rifle_trained_v1" then return false, "disabled" end
  if not memory or memory.sequence ~= ctx.sequence or memory.dimension ~= ctx.dimension or memory.status ~= "visible" or
      not memory.contact or now < memory.contact.seen_at or now >= memory.contact.expires_at then return false, "no_visible_contact" end
  if not roster or roster.closed or roster.sequence ~= ctx.sequence or not member.id or
      type(member.squad) ~= "string" or member.squad == "" then return false, "no_squad" end
  local candidates = {}
  for _, other in pairs(roster.actors) do
    if other.id ~= member.id and other.side == member.side and other.squad == member.squad and other.patrol.sequence == ctx.sequence and
        (cover.supports(other.reload, ctx, now, memory.contact.position) or
        (member.id < other.id and cover.supports(other.combat, ctx, now, memory.contact.position))) then
      candidates[other.id] = other
    end
  end
  if not next(candidates) then return false, "no_moving_peer" end
  local origin, selected = actor:get_pos_ms(), nil
  for _, buddy in ipairs(gapi.get_all_npcs()) do
    local other = candidates[buddy:getID():get_value()]
    if other and not buddy:is_dead() then
      local p = buddy:get_pos_ms()
      if p.z == origin.z and math.max(math.abs(p.x-origin.x), math.abs(p.y-origin.y)) <= 12 and actor:sees_creature(buddy) then
        if not selected or other.id < selected then selected = other.id end
      end
    end
  end
  if not selected then return false, "no_local_peer" end
  local p = memory.contact.position
  local result = actor:cover_visible_target(TripointAbsMs.new(p.x, p.y, p.z))
  if result == "" then return false, "no_firing_solution" end
  member.cover = {schema = 1, sequence = ctx.sequence, dimension = ctx.dimension, at = now, buddy = selected, action = result}
  return true, result
end
return cover
