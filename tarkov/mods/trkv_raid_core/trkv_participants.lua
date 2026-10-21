-- Raid-local identity only. Side and squad are separate; neither implies diplomacy.
-- All persisted fields are plain values. BN owns the actual NPCs and their equipment.
local participants = {}
local function integer(value)
  return type(value) == "number" and value % 1 == 0
end
local function key(id)
  if not integer(id) or id <= 0 or id > 2147483647 then return nil end
  return string.format("%d", id)
end

function participants.initialize(state)
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported participant save schema") end
  state.schema = 1
  state.sequence = state.sequence or 0
  if state.closed == nil then state.closed = true end
  state.actors = state.actors or {}
  state.slots = state.slots or {}
end

function participants.begin(state, sequence)
  participants.initialize(state)
  if not integer(sequence) or sequence <= 0 or sequence < state.sequence then return false end
  if sequence == state.sequence then return not state.closed end
  state.sequence, state.closed, state.actors, state.slots = sequence, false, {}, {}
  return true
end

function participants.register(state, sequence, id, side, squad, route)
  local id_key = key(id)
  if state.schema ~= 1 or state.closed or state.sequence ~= sequence or not id_key then return nil end
  if state.actors[id_key] or type(side) ~= "string" or side == "" or type(squad) ~= "string" then return nil end
  if type(route) ~= "table" then return nil end
  local points = {}
  for i, point in ipairs(route) do
    if type(point) ~= "table" or not integer(point.x) or not integer(point.y) or not integer(point.z) then
      return nil
    end
    -- Copy only known scalar fields, never a caller's userdata, functions or shared tables.
    points[i] = { x = point.x, y = point.y, z = point.z }
  end
  local actor = { id = id, side = side, squad = squad,
    patrol = { sequence = sequence, index = 1, route = points } }
  state.actors[id_key] = actor
  return actor
end

function participants.find(state, context, id)
  local id_key = key(id)
  if type(state) ~= "table" or state.schema ~= 1 or state.closed or
      type(state.actors) ~= "table" or not id_key or context.phase ~= "active" or
      not context.at_raid or state.sequence ~= context.sequence then return nil end
  return state.actors[id_key]
end

-- Call only after successful engine cleanup; a failed return must retain membership.
function participants.finish(state, sequence)
  if state.schema ~= 1 or state.sequence ~= sequence then return false end
  state.closed, state.actors, state.slots = true, {}, {}
  return true
end

return participants
