-- Short local reports, separate from personal sight and anonymous sound.
local search = require("trkv_search")
local squad = {}
local function copy(p) return { x = p.x, y = p.y, z = p.z } end
local function fresh(p, now)
  return p and p.source == "vision" and now >= p.seen_at and now - p.seen_at <= 2 and now < p.expires_at
end

function squad.update(state, ctx, now, reports, visible)
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported squad report schema") end
  if state.sequence ~= ctx.sequence or state.dimension ~= ctx.dimension or
      (state.last_now and now < state.last_now) then
    state.contact, state.search, state.observed = nil, nil, false
  end
  state.schema, state.sequence, state.dimension, state.last_now = 1, ctx.sequence, ctx.dimension, now
  if ctx.phase ~= "active" or not ctx.at_raid or visible then
    state.contact, state.search, state.status = nil, nil, "none"
    return
  end
  if state.contact and now < state.contact.expires_at then
    state.status = "remembered"
    return -- Reports cannot renew an investigation's position, deadline or budget.
  end
  state.contact, state.status = nil, "none"
  local selected
  for _, report in ipairs(reports) do
    if fresh(report.contact, now) and (not selected or
        report.contact.seen_at > selected.contact.seen_at or
        (report.contact.seen_at == selected.contact.seen_at and report.sender < selected.sender)) then
      selected = report
    end
  end
  if selected then
    local p = selected.contact
    state.contact = { source = "squad", sender = selected.sender, position = copy(p.position),
      seen_at = p.seen_at, expires_at = math.min(p.expires_at, p.seen_at + 10) }
    state.search, state.status, state.observed = {}, "remembered", true
  end
end

function squad.observe_actor(member, ctx, actor, roster, now)
  member.squad_memory = member.squad_memory or {}
  local memory = member.squad_memory
  if memory.side ~= member.side or memory.squad ~= member.squad then
    memory.contact, memory.search, memory.observed = nil, nil, false
  end
  memory.side, memory.squad = member.side, member.squad
  local reports = {}
  local eligible = roster and roster.schema == 1 and not roster.closed and
    roster.sequence == ctx.sequence and type(member.squad) == "string" and member.squad ~= ""
  if eligible and ctx.phase == "active" and ctx.at_raid and member.perception.status ~= "visible" then
    local donors = {}
    for _, other in pairs(roster.actors) do
      local p = other.perception
      if other.id ~= member.id and other.side == member.side and other.squad == member.squad and
          other.patrol.sequence == ctx.sequence and p and p.sequence == ctx.sequence and
          p.dimension == ctx.dimension and p.status == "visible" and fresh(p.contact, now) then
        donors[other.id] = other
      end
    end
    if next(donors) then
      local origin = actor:get_pos_ms()
      for _, buddy in ipairs(gapi.get_all_npcs()) do
        local other = donors[buddy:getID():get_value()]
        if other and not buddy:is_dead() then
          local p = buddy:get_pos_ms()
          -- Local visual communication: no radio, no report through a wall,
          -- no hidden enemy query and no relay of another report.
          if p.z == origin.z and math.max(math.abs(p.x-origin.x), math.abs(p.y-origin.y)) <= 12 and actor:sees(p) then
            reports[#reports + 1] = { sender = other.id, contact = other.perception.contact }
          end
        end
      end
    end
  end
  if not eligible then
    member.squad_memory.contact, member.squad_memory.search = nil, nil
  end
  squad.update(member.squad_memory, ctx, now, reports, member.perception.status == "visible")
end

function squad.step_actor(member, ctx, actor, map, now)
  local memory = member.squad_memory
  if not memory or not memory.contact then return false, "no_report" end
  memory.search = memory.search or {}
  return search.step_actor(memory.search, ctx, memory, actor, map, now)
end
return squad
