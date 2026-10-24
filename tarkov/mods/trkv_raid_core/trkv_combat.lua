-- First deliberate combat move: a short standoff for a trained rifle profile.
local loadouts = require("trkv_loadouts")
local combat = {}
local function copy(p) return { x = p.x, y = p.y, z = p.z } end
local function distance(a, b)
  if a.z ~= b.z then return math.huge end
  return math.max(math.abs(a.x - b.x), math.abs(a.y - b.y))
end

function combat.cancel(state, reason)
  state.goal, state.cooldown_until, state.last_now = nil, nil, nil
  state.status = reason
  return false, reason
end

function combat.step(state, context, memory, now, api)
  if context.phase ~= "active" or not context.at_raid then
    return combat.cancel(state, "inactive")
  end
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported combat schema") end
  if state.sequence ~= context.sequence or state.dimension ~= context.dimension then
    state.goal, state.cooldown_until, state.last_now = nil, 0, nil
  end
  state.schema, state.sequence, state.dimension = 1, context.sequence, context.dimension
  if state.last_now and now < state.last_now then
    combat.cancel(state, "clock_reset")
    state.last_now, state.cooldown_until = now, now + 12
    return false, state.status
  end
  state.last_now = now
  local contact = memory.contact
  if memory.status ~= "visible" or not contact or memory.sequence ~= context.sequence or
      memory.dimension ~= context.dimension then
    state.goal, state.status = nil, "lost_contact"
    return false, state.status
  end
  local goal = state.goal
  if goal then
    if now < goal.started_at or now >= goal.deadline or
        distance(goal.target, contact.position) > 1 then
      state.goal, state.status = nil, "cancelled"
      return false, state.status
    end
    if api.at(goal.position) then
      state.goal, state.status = nil, "arrived"
      return false, state.status -- Leave this turn's actions for BN firing/reload.
    end
    if goal.attempts >= 4 or goal.stalled >= 2 then
      state.goal, state.status = nil, "cancelled"
      return false, state.status
    end
    if not api.validate(contact.position, goal.position) then
      state.goal, state.status = nil, "invalid_position"
      return false, state.status
    end
  else
    if now < (state.cooldown_until or 0) then return false, "cooldown" end
    state.cooldown_until = now + 12
    local selected = api.choose(contact.position)
    if not selected then state.status = "no_position"; return false, state.status end
    goal = { position = copy(selected), target = copy(contact.position), started_at = now,
      deadline = now + 8, attempts = 0, stalled = 0 }
    state.goal = goal
  end
  local before, origin = api.moves(), copy(api.position())
  api.move_to(goal.position)
  goal.attempts = goal.attempts + 1
  goal.stalled = distance(origin, api.position()) == 0 and goal.stalled + 1 or 0
  if api.moves() >= before then api.wait() end
  state.status = "standoff"
  return true, state.status
end

function combat.step_actor(member, context, actor, map, now)
  local preset = member.loadout and loadouts.describe(member.loadout)
  if not preset or preset.profile ~= "rifle_trained_v1" then
    if member.combat then return combat.cancel(member.combat, "disabled") end
    return false, "disabled"
  end
  member.combat = member.combat or {}
  local function absolute(p) return TripointAbsMs.new(p.x, p.y, p.z) end
  return combat.step(member.combat, context, member.perception, now, {
    choose = function(p) return actor:choose_standoff_position(absolute(p)) end,
    validate = function(p, goal)
      return actor:choose_standoff_position(absolute(p), absolute(goal)) ~= nil
    end,
    at = function(p) return actor:get_pos_ms() == map:abs_to_bub(absolute(p)) end,
    position = function() local p = actor:abs_pos(); return copy(p) end,
    moves = function() return actor:get_moves() end,
    move_to = function(p) actor:move_towards(map:abs_to_bub(absolute(p))) end,
    wait = function() actor:set_moves(actor:get_moves() - 100) end,
  })
end

return combat
