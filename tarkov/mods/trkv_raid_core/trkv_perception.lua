-- Plain raid-local visual memory. No actor references or hidden-position queries.
local memory = {}
local function finite(n)
  return type(n) == "number" and n == n and n > -math.huge and n < math.huge
end

function memory.update(state, context, now, observation, lifetime)
  if context.phase ~= "active" or not context.at_raid then return false, "inactive" end
  assert(finite(now) and finite(lifetime) and lifetime > 0)
  assert(type(context.dimension) == "string" and context.dimension ~= "")
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported perception schema") end
  if state.sequence ~= context.sequence or state.dimension ~= context.dimension then
    state.contact, state.observed = nil, false
  end
  state.schema, state.sequence, state.dimension = 1, context.sequence, context.dimension
  if observation then
    local p = observation.position
    assert(type(p) == "table" and finite(p.x) and finite(p.y) and finite(p.z))
    assert(p.x % 1 == 0 and p.y % 1 == 0 and p.z % 1 == 0)
    state.contact = { source = "vision", seen_at = now, expires_at = now + lifetime,
      position = { x = p.x, y = p.y, z = p.z } }
    state.status, state.observed = "visible", true
  elseif state.contact and now >= state.contact.seen_at and now < state.contact.expires_at then
    state.status = "remembered"
  else
    -- Clock reversal cannot make a future observation usable.
    state.contact, state.status = nil, "none"
  end
  return true, state.status
end

-- Called after BN refreshes the actor cache. Read position only after explicit Creature visibility.
-- This observes the current selected target; it is not an all-enemy sensor.
function memory.observe_actor(state, context, actor, now, lifetime)
  if context.phase ~= "active" or not context.at_raid then return false, "inactive" end
  local observation
  local target = actor:current_target()
  if target and actor:sees_creature(target) then
    local p = target:abs_pos()
    observation = { position = { x = p.x, y = p.y, z = p.z } }
  end
  return memory.update(state, context, now, observation, lifetime)
end

return memory
