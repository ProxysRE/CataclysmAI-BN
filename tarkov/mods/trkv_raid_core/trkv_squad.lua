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
    state.waiting_for, state.checked_at = nil, nil
  end
  state.schema, state.sequence, state.dimension, state.last_now = 1, ctx.sequence, ctx.dimension, now
  if ctx.phase ~= "active" or not ctx.at_raid or visible then
    state.contact, state.search, state.status = nil, nil, "none"
    state.waiting_for, state.checked_at = nil, nil
    return
  end
  if state.contact and now < state.contact.expires_at then
    state.status = "remembered"
    return -- Reports cannot renew an investigation's position, deadline or budget.
  end
  state.contact, state.status = nil, "none"
  state.waiting_for, state.checked_at = nil, nil
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
    memory.waiting_for, memory.checked_at = nil, nil
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
          if p.z == origin.z and math.max(math.abs(p.x-origin.x), math.abs(p.y-origin.y)) <= 12 and actor:sees_creature(buddy) then
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

-- Inputs contain only legally communicated peer states, never hidden actors.
function squad.coordinate(memory, ctx, now, peers, own_id)
  local contact = memory.contact
  if memory.sequence ~= ctx.sequence or memory.dimension ~= ctx.dimension or
      not contact or not own_id or now < contact.seen_at or now >= contact.expires_at then return nil end
  local investigator, checked
  for _, peer in ipairs(peers) do
    local other = peer.memory
    local c, s = other.contact, other.search
    local goal = s and s.goal
    if other.sequence == ctx.sequence and other.dimension == ctx.dimension and
        c and c.source == "squad" and c.sender == contact.sender and
        now >= c.seen_at and now < c.expires_at and
        c.position.x == contact.position.x and c.position.y == contact.position.y and c.position.z == contact.position.z and
        goal and s.sequence == ctx.sequence and s.dimension == ctx.dimension and
        now >= goal.seen_at and now < goal.deadline and (not other.last_now or now >= other.last_now) and
        goal.position.x == c.position.x and goal.position.y == c.position.y and goal.position.z == c.position.z then
      if s.status == "checked" and other.checked_at and other.checked_at >= contact.seen_at and other.checked_at <= now then
        checked = math.min(checked or peer.id, peer.id)
      elseif s.status == "searching" and peer.id < own_id and goal.attempts < 12 and goal.stalled < 4 then
        investigator = math.min(investigator or peer.id, peer.id)
      end
    end
  end
  if checked then return "report_checked_by_squad", checked end
  if investigator then return "wait_for_investigator", investigator end
end

function squad.step_actor(member, ctx, actor, map, now, roster)
  if ctx.phase ~= "active" or not ctx.at_raid then return false, "inactive" end
  local memory = member.squad_memory
  if not memory or not memory.contact then return false, "no_report" end
  memory.search = memory.search or {}
  if memory.search.status == "checked_by_squad" then return false, "report_checked_by_squad" end
  if memory.search.status and memory.search.status ~= "searching" then
    memory.waiting_for = nil
    return search.step_actor(memory.search, ctx, memory, actor, map, now)
  end
  local peers = {}
  if roster and not roster.closed and roster.sequence == ctx.sequence and member.id and member.squad ~= "" then
    local candidates = {}
    for _, other in pairs(roster.actors) do
      if other.id ~= member.id and other.side == member.side and other.squad == member.squad and
          other.patrol.sequence == ctx.sequence and other.squad_memory then candidates[other.id] = other end
    end
    if next(candidates) then
      local origin = actor:get_pos_ms()
      for _, buddy in ipairs(gapi.get_all_npcs()) do
        local other = candidates[buddy:getID():get_value()]
        if other and not buddy:is_dead() then
          local p = buddy:get_pos_ms()
          if p.z == origin.z and math.max(math.abs(p.x-origin.x), math.abs(p.y-origin.y)) <= 12 and actor:sees_creature(buddy) then
            peers[#peers + 1] = {id = other.id, memory = other.squad_memory}
          end
        end
      end
    end
  end
  local reason, peer = squad.coordinate(memory, ctx, now, peers, member.id)
  memory.waiting_for = reason == "wait_for_investigator" and peer or nil
  if reason then
    if reason == "report_checked_by_squad" then
      memory.search.status, memory.search.finished_by = "checked_by_squad", peer
    end
    actor:set_moves(actor:get_moves() - 100)
    return true, reason
  end
  local handled, why = search.step_actor(memory.search, ctx, memory, actor, map, now)
  if handled and why == "checked" then memory.checked_at = now end
  return handled, why
end
return squad
