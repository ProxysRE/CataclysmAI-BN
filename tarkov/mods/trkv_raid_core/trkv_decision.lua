-- First single-actor controller. Visible combat still belongs to BN.
local perception = require("trkv_perception")
local search = require("trkv_search")
local hearing = require("trkv_hearing")
local patrol = require("trkv_patrol")
local combat = require("trkv_combat")
local decision = {}

function decision.step_actor(member, context, actor, map, now)
  if context.phase ~= "active" or not context.at_raid or
      member.patrol.sequence ~= context.sequence then
    if member.combat then combat.cancel(member.combat, "inactive") end
    return false, "inactive"
  end
  member.perception, member.search = member.perception or {}, member.search or {}
  perception.observe_actor(member.perception, context, actor, now, 30)
  member.hearing = member.hearing or {}
  hearing.update(member.hearing, context, now, actor:get_value("trkv_heard_noise"))
  local hazard = actor:avoid_immediate_danger()
  if hazard ~= "" then return true, "escape_" .. hazard end
  local handled, reason = combat.step_actor(member, context, actor, map, now)
  if handled then return handled, reason end
  handled, reason = search.step_actor(member.search, context, member.perception, actor, map, now)
  if handled then return handled, reason end
  if member.perception.status ~= "visible" then
    handled, reason = hearing.step_actor(member.hearing, context, actor, map, now)
    if handled then return handled, reason end
  end
  -- Once contact was established, absence of vision must not hand a hidden
  -- target back to BN through its danger cache after the search finishes.
  local controlled = (member.search.observed or member.hearing.observed) and
    member.perception.status ~= "visible"
  handled, reason = patrol.step_actor(member.patrol, context, actor, map, controlled)
  if controlled and not handled then
    actor:set_moves(actor:get_moves() - 100)
    return true, "wait_" .. reason
  end
  return handled, reason
end

return decision
