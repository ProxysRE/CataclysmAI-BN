-- Anonymous 4x4 sound regions, separate from identified visual contacts.
local search = require("trkv_search")
local hearing = {}
local function same_region(a, b)
  return a.x == b.x and a.y == b.y and a.z == b.z
end

function hearing.update(state, context, now, event)
  if context.phase ~= "active" or not context.at_raid then return false, "inactive" end
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported hearing schema") end
  if state.sequence ~= context.sequence or state.dimension ~= context.dimension then
    state.contact, state.search, state.observed = nil, {}, false
  end
  state.schema, state.sequence, state.dimension = 1, context.sequence, context.dimension
  if state.contact and (now < state.contact.seen_at or now >= state.contact.expires_at) then
    state.contact = nil
  end
  if type(event) == "string" and event ~= "" and event ~= state.last_event then
    state.last_event = event -- Reading the same saved inbox cannot renew memory.
    local dim, turn, x, y, z, kind = event:match("^([^|]+)|(%-?%d+)|(%-?%d+)|(%-?%d+)|(%-?%d+)|(%a+)$")
    turn, x, y, z = tonumber(turn), tonumber(x), tonumber(y), tonumber(z)
    local function integer(n) return n and n == n and math.abs(n) < 2147483647 and n % 1 == 0 end
    if dim == context.dimension and integer(turn) and integer(x) and integer(y) and integer(z) and
        (kind == "movement" or kind == "combat") and turn <= now and now < turn + 20 and
        x % 4 == 2 and y % 4 == 2 then
      local p = { x = x, y = y, z = z }
      -- Repeated noises in the same active episode do not reset attempts/deadline.
      if not state.contact or not same_region(p, state.contact.position) then
        state.contact = { source = "sound", position = p, seen_at = turn, expires_at = turn + 20,
          kind = kind, event = event, radius = 2 }
        state.search = {}
      end
      state.observed = true
    end
  end
  state.status = state.contact and "remembered" or "none"
  return true, state.status
end

function hearing.step_actor(state, context, actor, map, now)
  local memory = { sequence = state.sequence, dimension = state.dimension,
    status = state.status, contact = state.contact }
  state.search = state.search or {}
  local function own_position()
    local p = actor:abs_pos(); return { x = p.x, y = p.y, z = p.z }
  end
  local handled, reason = search.step(state.search, context, memory, now, {
    at = function(p)
      local q = own_position()
      return q.z == p.z and q.x >= p.x - 2 and q.x < p.x + 2 and
        q.y >= p.y - 2 and q.y < p.y + 2
    end,
    position = own_position,
    moves = function() return actor:get_moves() end,
    move_to = function(p)
      actor:move_towards(map:abs_to_bub(TripointAbsMs.new(p.x, p.y, p.z)))
    end,
    wait = function() actor:set_moves(actor:get_moves() - 100) end,
  })
  return handled, "sound_" .. reason
end

return hearing
