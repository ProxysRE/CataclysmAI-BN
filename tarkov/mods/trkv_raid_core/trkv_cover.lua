-- First local support action: hold and fire while a visible squadmate moves.
local loadouts = require("trkv_loadouts")
local cover = {}
local function near(a, b, radius)
  return a.z == b.z and math.max(math.abs(a.x-b.x), math.abs(a.y-b.y)) <= radius
end
local function same_group(a, b, ctx)
  return a.id ~= b.id and a.side == b.side and a.squad == b.squad and
    b.patrol and b.patrol.sequence == ctx.sequence
end
-- An actual recent support action owns this local role for at most two turns.
-- Hidden/distant/dead supporters cannot reserve it, and no role is relayed.
local function occupied(member, ctx, actor, now, roster, live, buddy)
  local origin = actor:get_pos_ms()
  for _, peer in pairs(roster.actors) do
    local role, memory = peer.cover, peer.perception
    if same_group(member, peer, ctx) and peer.id ~= buddy and role and
        role.schema == 1 and role.sequence == ctx.sequence and role.dimension == ctx.dimension and
        role.buddy == buddy and (role.action == "cover_aim" or role.action == "cover_fire") and
        now >= role.at and now - role.at <= 2 and memory and memory.status == "visible" and
        memory.sequence == ctx.sequence and memory.dimension == ctx.dimension and memory.contact and
        now >= memory.contact.seen_at and now < memory.contact.expires_at and
        near(memory.contact.position, member.perception.contact.position, 1) then
      local supporter = live[peer.id]
      if supporter and not supporter:is_dead() and actor:sees_creature(supporter) and
          near(origin, supporter:get_pos_ms(), 12) then return true end
    end
  end
  return false
end
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
  local candidates, live = {}, {}
  for _, buddy in ipairs(gapi.get_all_npcs()) do live[buddy:getID():get_value()] = buddy end
  local origin = actor:get_pos_ms()
  for _, other in pairs(roster.actors) do
    if same_group(member, other, ctx) then
      local kind = cover.supports(other.reload, ctx, now, memory.contact.position) and "reload" or
        (member.id < other.id and cover.supports(other.combat, ctx, now, memory.contact.position) and "combat")
      if kind then
        local buddy = live[other.id]
        if buddy and not buddy:is_dead() and actor:sees_creature(buddy) and near(origin, buddy:get_pos_ms(), 12) then
          candidates[#candidates+1] = {id = other.id, kind = kind}
        end
      end
    end
  end
  if #candidates == 0 then return false, "no_local_peer" end
  table.sort(candidates, function(a, b)
    if a.kind ~= b.kind then return a.kind == "reload" end
    return a.id < b.id
  end)
  local selected
  for _, candidate in ipairs(candidates) do
    if not occupied(member, ctx, actor, now, roster, live, candidate.id) then
      selected = candidate; break
    end
  end
  if not selected then return false, "peer_already_covered" end
  local p = memory.contact.position
  local result = actor:cover_visible_target(TripointAbsMs.new(p.x, p.y, p.z))
  if result == "" then return false, "no_firing_solution" end
  member.cover = {schema = 1, sequence = ctx.sequence, dimension = ctx.dimension, at = now, buddy = selected.id, kind = selected.kind, action = result}
  return true, result
end
return cover
