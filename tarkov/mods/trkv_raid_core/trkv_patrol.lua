-- Experimental controller. State contains only saveable values; actors stay in adapters.
local patrol = {}

function patrol.step(state, context, api)
  if context.phase ~= "active" or not context.at_raid or
      state.sequence ~= context.sequence then return false, "inactive" end
  -- Observations come from BN's freshly regenerated NPC cache, never avatar coordinates.
  if api.has_target() or api.danger() > 0 then return false, "threat" end
  if #state.route < 2 then return false, "no_route" end
  local index = state.index or 1
  local target = state.route[index]
  if not target then return false, "invalid_route" end
  if api.at(target) then
    index = index % #state.route + 1
    target = state.route[index]
    state.index = index
  end
  local before = api.moves()
  api.move_to(target)
  if api.moves() >= before then return false, "blocked" end
  return true, "patrol"
end

-- Called during npc_class.lua_ai, after BN has regenerated this actor's AI cache.
-- These references live only for this decision and never enter saved state.
function patrol.step_actor(state, context, actor, map)
  local function pos(point)
    return map:abs_to_bub(TripointAbsMs.new(point.x, point.y, point.z))
  end
  return patrol.step(state, context, {
    has_target = function() return actor:current_target() ~= nil end,
    danger = function() return actor:danger_assessment() end,
    at = function(point) return actor:get_pos_ms() == pos(point) end,
    moves = function() return actor:get_moves() end,
    move_to = function(point) actor:move_to(pos(point), true) end,
  })
end

return patrol
