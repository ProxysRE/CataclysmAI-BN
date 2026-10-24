-- Bounded first search: visit the last visual contact, then resume the route.
-- No hidden target, NPC, map or item references are stored in this state.
local search = {}
local function point(p) return { x = p.x, y = p.y, z = p.z } end
local function same(a, b) return a.x == b.x and a.y == b.y and a.z == b.z end

function search.step(state, context, memory, now, api)
  if context.phase ~= "active" or not context.at_raid then return false, "inactive" end
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported search schema") end
  if state.sequence ~= context.sequence or state.dimension ~= context.dimension then
    state.observed, state.goal, state.status = false, nil, "idle"
  end
  state.schema, state.sequence, state.dimension = 1, context.sequence, context.dimension
  if memory.sequence ~= context.sequence or memory.dimension ~= context.dimension then
    return false, "stale_memory"
  end
  if memory.status == "visible" then
    state.observed, state.goal, state.status = true, nil, "contact"
    return false, "visible"
  end
  local contact = memory.contact
  if not contact or now < contact.seen_at or now >= contact.expires_at then
    if state.goal then state.status = "expired" end
    return false, "no_memory"
  end
  if memory.status ~= "remembered" then return false, "no_memory" end
  state.observed = true
  if not state.goal then
    state.goal = { position = point(contact.position), seen_at = contact.seen_at,
      deadline = contact.expires_at, attempts = 0, stalled = 0 }
    state.status = "searching"
  end
  -- The plan is immutable until a new visual contact clears it. Ticks/load do
  -- not renew the deadline, attempts or a completed/unreachable search.
  local goal = state.goal
  if state.status ~= "searching" then return false, state.status end
  if now >= goal.deadline then state.status = "expired"; return false, "expired" end
  if api.at(goal.position) then
    state.status = "checked"
    api.wait()
    return true, "checked"
  end
  if goal.attempts >= 12 or goal.stalled >= 4 then
    state.status = "unreachable"
    api.wait()
    return true, "unreachable"
  end
  local before, origin = api.moves(), point(api.position())
  api.move_to(goal.position)
  goal.attempts = goal.attempts + 1
  if same(origin, api.position()) then goal.stalled = goal.stalled + 1 else goal.stalled = 0 end
  if api.moves() >= before then api.wait() end
  return true, "searching"
end

function search.step_actor(state, context, memory, actor, map, now)
  local function pos(p) return map:abs_to_bub(TripointAbsMs.new(p.x, p.y, p.z)) end
  return search.step(state, context, memory, now, {
    at = function(p) return actor:get_pos_ms() == pos(p) end,
    position = function() local p = actor:abs_pos(); return point(p) end,
    moves = function() return actor:get_moves() end,
    move_to = function(p) actor:move_towards(pos(p)) end,
    wait = function() actor:set_moves(actor:get_moves() - 100) end,
  })
end

return search
