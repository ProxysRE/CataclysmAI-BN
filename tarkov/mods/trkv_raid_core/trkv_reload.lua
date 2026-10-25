-- Reload behind terrain cover; all persisted data is plain and raid-local.
local loadouts = require("trkv_loadouts")
local reload = {}
local function copy(p) return { x = p.x, y = p.y, z = p.z } end
local function distance(a, b)
  if a.z ~= b.z then return math.huge end
  return math.max(math.abs(a.x - b.x), math.abs(a.y - b.y))
end
function reload.cancel(state, reason)
  state.goal, state.cooldown_until, state.last_now, state.failure_reason = nil, nil, nil, nil
  state.status = reason
  return false, reason
end
function reload.step(state, ctx, memory, now, api)
  if ctx.phase ~= "active" or not ctx.at_raid then return reload.cancel(state, "inactive") end
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported reload schema") end
  if state.sequence ~= ctx.sequence or state.dimension ~= ctx.dimension then reload.cancel(state, "new_raid") end
  state.schema, state.sequence, state.dimension = 1, ctx.sequence, ctx.dimension
  if state.last_now and now < state.last_now then
    reload.cancel(state, "clock_reset"); state.last_now, state.cooldown_until = now, now + 12
    return false, state.status
  end
  state.last_now = now
  local contact = memory.contact
  if memory.sequence ~= ctx.sequence or memory.dimension ~= ctx.dimension or not contact or
      now < contact.seen_at or now >= contact.expires_at then
    state.goal, state.status = nil, "no_memory"
    if memory.sequence == ctx.sequence and memory.dimension == ctx.dimension and
        memory.status == "none" and not contact and api.idle_reload and api.idle_reload() then
      state.status, state.failure_reason = "idle_reloaded", nil
      return true, state.status
    end
    return false, state.status
  end
  local goal = state.goal
  -- Inventory may change between decisions or while a saved approach is paused.
  -- Stop before validating terrain or taking another step with a loaded gun /
  -- unavailable ammunition. Keep the original cooldown to avoid plan churn.
  if goal and not api.ready() then
    state.goal, state.status, state.failure_reason = nil, "no_longer_needed", nil
    return false, state.status
  end
  if not goal then
    if memory.status ~= "visible" then
      -- A previous maneuver can be cancelled after an emergency. If already
      -- behind cover, do not force an empty gun back toward the remembered foe.
      if api.ready() and api.reload(contact.position) then
        state.status, state.failure_reason = "reloaded", nil
        return true, state.status
      end
      return false, "no_visible_threat"
    end
    if api.allow_cover == false then return false, "cover_disabled" end
    if not api.ready() then return false, "not_needed" end
    if now < (state.cooldown_until or 0) then return false, "cooldown" end
    state.cooldown_until = now + 12
    local selected = api.choose(contact.position)
    if not selected then return false, "no_cover" end
    goal = { position = copy(selected), threat = copy(contact.position), started_at = now,
      deadline = now + 8, attempts = 0, stalled = 0 }
    state.goal, state.failure_reason = goal, nil
  end
  if now < goal.started_at or now >= goal.deadline or distance(goal.threat, contact.position) > 1 then
    state.goal, state.status = nil, "cancelled"; return false, state.status
  end
  if not api.validate(contact.position, goal.position) then
    state.failure_reason = api.cover_failure and api.cover_failure(contact.position, goal.position) or "unknown"
    state.goal, state.status = nil, "invalid_cover"; return false, state.status
  end
  if api.at(goal.position) then
    local before = api.moves()
    local success = api.reload(contact.position)
    state.failure_reason = not success and (api.failure and api.failure() or "unknown") or nil
    if api.moves() >= before then api.wait() end
    state.goal, state.status = nil, success and "reloaded" or "reload_failed"
    return true, state.status
  end
  if goal.attempts >= 4 or goal.stalled >= 2 then
    state.goal, state.status = nil, "unreachable"; return false, state.status
  end
  local before, origin = api.moves(), copy(api.position())
  api.move_to(goal.position)
  goal.attempts = goal.attempts + 1
  goal.stalled = distance(origin, api.position()) == 0 and goal.stalled + 1 or 0
  if api.moves() >= before then api.wait() end
  state.status = "reload_cover"
  return true, state.status
end
function reload.step_actor(member, ctx, actor, map, now)
  local preset = member.loadout and loadouts.describe(member.loadout)
  if not preset or (preset.profile ~= "rifle_trained_v1" and preset.profile ~= "rifle_recruit_v1") then
    if member.reload then return reload.cancel(member.reload, "disabled") end
    return false, "disabled"
  end
  member.reload = member.reload or {}
  local function absolute(p) return TripointAbsMs.new(p.x, p.y, p.z) end
  return reload.step(member.reload, ctx, member.perception, now, {
    allow_cover = preset.profile == "rifle_trained_v1",
    ready = function() return actor:can_reload_empty_gun() end,
    idle_reload = function()
      if member.hearing and member.hearing.contact then return false end
      if member.squad_memory and member.squad_memory.contact then return false end
      return actor:reload_without_visible_target()
    end,
    choose = function(p) return actor:choose_reload_cover(absolute(p)) end,
    validate = function(p, goal) return actor:choose_reload_cover(absolute(p), absolute(goal)) ~= nil end,
    cover_failure = function(p, goal) return actor:reload_cover_status(absolute(p), absolute(goal)) end,
    at = function(p) return actor:get_pos_ms() == map:abs_to_bub(absolute(p)) end,
    position = function() return copy(actor:abs_pos()) end,
    moves = function() return actor:get_moves() end,
    move_to = function(p) actor:move_towards(map:abs_to_bub(absolute(p))) end,
    reload = function(p) return actor:reload_under_cover(absolute(p)) end,
    failure = function() return actor:get_value("trkv_reload_result") end,
    wait = function() actor:set_moves(actor:get_moves() - 100) end,
  })
end
return reload
