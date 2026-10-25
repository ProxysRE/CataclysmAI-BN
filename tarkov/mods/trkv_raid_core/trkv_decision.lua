-- First single-actor controller. Visible combat still belongs to BN.
local perception = require("trkv_perception")
local search = require("trkv_search")
local hearing = require("trkv_hearing")
local patrol = require("trkv_patrol")
local combat = require("trkv_combat")
local reload = require("trkv_reload")
local squad = require("trkv_squad")
local decision = {}

-- Only transitions are retained. No actor references, hidden coordinates or
-- unbounded per-tick log; repeated decisions update the latest entry in place.
local function record(member, context, now, action, handled, reason, refusals)
  local trace = member.decisions
  if not trace or trace.sequence ~= context.sequence or trace.dimension ~= context.dimension or
      (trace.last_now and now < trace.last_now) then
    trace = { schema = 1, sequence = context.sequence, dimension = context.dimension, history = {} }
    member.decisions = trace
  end
  local history = trace.history
  local last = history[#history]
  local source = member.perception and member.perception.status == "visible" and "vision" or
    (member.perception and member.perception.contact and "visual_memory" or
    (member.squad_memory and member.squad_memory.contact and "squad" or
    (member.hearing and member.hearing.contact and "sound" or "none")))
  if last and last.action == action and last.reason == reason and last.source == source then
    last.last_at, last.repeats = now, math.min((last.repeats or 1) + 1, 999)
  else
    history[#history + 1] = { at = now, last_at = now, action = action, reason = reason,
      source = source, repeats = 1 }
    if #history > 8 then table.remove(history, 1) end
  end
  trace.last_now, trace.action, trace.reason, trace.handled = now, action, reason, handled
  trace.hearing_input = member.hearing and member.hearing.input_reason or "none"
  trace.refusals = refusals -- Short current decision chain, not a historical queue.
  return handled, reason
end

function decision.step_actor(member, context, actor, map, now, roster)
  local refusals = {}
  local function finish(action, handled, reason)
    return record(member, context, now, action, handled, reason, refusals)
  end
  if context.phase ~= "active" or not context.at_raid or
      member.patrol.sequence ~= context.sequence then
    if member.combat then combat.cancel(member.combat, "inactive") end
    if member.reload then reload.cancel(member.reload, "inactive") end
    if member.squad_memory then
      member.squad_memory.contact, member.squad_memory.search = nil, nil
      member.squad_memory.status = "inactive"
    end
    return finish("inactive", false, "inactive")
  end
  member.perception, member.search = member.perception or {}, member.search or {}
  perception.observe_actor(member.perception, context, actor, now, 30)
  squad.observe_actor(member, context, actor, roster, now)
  member.hearing = member.hearing or {}
  hearing.update(member.hearing, context, now, actor:get_value("trkv_heard_noise"))
  local hazard = actor:avoid_immediate_danger()
  if hazard ~= "" then return finish("escape", true, "escape_" .. hazard) end
  local handled, reason = reload.step_actor(member, context, actor, map, now, roster)
  if handled then
    if member.combat then combat.cancel(member.combat, "reload_cover") end
    return finish("reload", handled, reason)
  end
  refusals.reload = reason
  handled, reason = combat.step_actor(member, context, actor, map, now, roster)
  if handled then return finish("maneuver", handled, reason) end
  refusals.combat = reason
  handled, reason = search.step_actor(member.search, context, member.perception, actor, map, now)
  if handled then return finish("visual_search", handled, reason) end
  refusals.search = reason
  if member.perception.status ~= "visible" then
    handled, reason = squad.step_actor(member, context, actor, map, now)
    if handled then return finish("squad_search", handled, reason) end
    refusals.squad = reason
    handled, reason = hearing.step_actor(member.hearing, context, actor, map, now)
    if handled then return finish("sound_search", handled, reason) end
    refusals.hearing = reason
  end
  -- Observation ownership survives an emergency that prevented search.step
  -- from ever running while the target was visible.
  local controlled = (member.perception.observed or member.search.observed or member.hearing.observed or
    (member.squad_memory and member.squad_memory.observed)) and
    member.perception.status ~= "visible"
  handled, reason = patrol.step_actor(member.patrol, context, actor, map, controlled)
  if controlled and not handled then
    actor:set_moves(actor:get_moves() - 100)
    return finish("wait", true, "wait_" .. reason)
  end
  return finish(handled and "patrol" or "vanilla", handled, reason)
end

return decision
