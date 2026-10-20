-- Engine-independent lifecycle. Persist only this plain-data state, never userdata.
local raid = {}

---@class RaidState
---@field schema integer
---@field phase string
---@field sequence integer
---@field wins integer
---@field losses integer
---@field settled integer
---@field deadline integer
---@field entry_duration integer
---@field outcome string
---@field penalty_applied boolean
---@field last_error string

---@class RaidAdapter
---@field at_home fun(): boolean
---@field at_raid fun(): boolean
---@field enter fun(): boolean
---@field return_home fun(): boolean
---@field cleanup fun(): boolean
---@field penalize fun()
---@field now fun(): integer

---@param state table
function raid.initialize(state)
  if state.schema ~= nil and state.schema ~= 1 then error("Unsupported raid save schema") end
  state.schema = 1
  state.phase = state.phase or "home"
  state.sequence = state.sequence or 0
  state.wins = state.wins or 0
  state.losses = state.losses or 0
  state.settled = state.settled or 0
  state.deadline = state.deadline or 0
  state.entry_duration = state.entry_duration or 0
  state.outcome = state.outcome or "none"
  state.penalty_applied = state.penalty_applied or false
  state.last_error = state.last_error or ""
end

---@param state RaidState
---@param api RaidAdapter
function raid.cleanup(state, api)
  if state.phase ~= "cleanup" or not api.at_home() then return false end
  -- BN cleanup saves the game BEFORE deleting. The saved phase must permit replay.
  if not api.cleanup() then
    state.last_error = "Raid cleanup failed; retry from the departure terminal."
    return false
  end
  if state.settled < state.sequence then
    if state.outcome == "extracted" then state.wins = state.wins + 1 end
    if state.outcome == "defeated" or state.outcome == "timeout" then
      state.losses = state.losses + 1
    end
    state.settled = state.sequence
  end
  state.phase = "home"
  state.last_error = ""
  return true
end

---@param state RaidState
---@param api RaidAdapter
---@param outcome string
function raid.finish(state, api, outcome)
  if state.phase == "active" then
    if not api.at_raid() then return false end
    if outcome ~= "extracted" and outcome ~= "defeated" and outcome ~= "timeout" then return false end
    if outcome == "extracted" and api.now() >= state.deadline then outcome = "timeout" end
    state.outcome = outcome
    state.phase = "returning"
  elseif state.phase ~= "returning" then
    return false
  end
  if not api.at_raid() and not api.at_home() then
    state.last_error = "Return dimension mismatch; automatic changes stopped."
    return false
  end
  -- Requesting extraction is not success until the player actually reaches home.
  if api.at_raid() and state.outcome == "extracted" then
    if outcome == "defeated" then
      state.outcome = "defeated"
    elseif api.now() >= state.deadline then
      state.outcome = "timeout"
    end
  end
  -- A failed return may be retried, but must not repeat the inventory penalty.
  if state.outcome ~= "extracted" and not state.penalty_applied then
    if not api.at_raid() then return false end
    api.penalize()
    state.penalty_applied = true
  end
  if not api.at_home() and not api.return_home() then
    state.last_error = "Return failed; use the exit terminal to retry."
    return false
  end
  if not api.at_home() then return false end
  state.phase = "cleanup"
  return raid.cleanup(state, api)
end

---@param state RaidState
---@param api RaidAdapter
---@param duration integer
function raid.start(state, api, duration)
  if (state.phase ~= "home" and state.phase ~= "entering") or not api.at_home() then return false end
  local retry = state.phase == "entering"
  if retry and state.entry_duration > 0 then duration = state.entry_duration end
  if type(duration) ~= "number" or duration <= 0 or duration % 1 ~= 0 then return false end
  if not retry then state.sequence = state.sequence + 1 end
  state.entry_duration = duration
  state.phase = "entering"
  state.outcome = "none"
  state.penalty_applied = false
  state.last_error = ""
  state.deadline = api.now() + duration
  if api.enter() and api.at_raid() then
    state.phase = "active"
    return true
  end
  -- Never delete a dimension the player still occupies, even after a partial failure.
  if api.at_raid() then
    state.phase = "active"
    return true
  end
  -- A failed save may happen BEFORE the dimension even exists. reset_dimension
  -- cannot distinguish that from another failure. Keep this attempt pending;
  -- the departure terminal can retry it without deleting anything or scoring it.
  state.last_error = "Entry failed; use the departure terminal to retry this raid."
  return false
end

---@param state RaidState
---@param api RaidAdapter
function raid.recover(state, api)
  raid.initialize(state)
  -- Migrate old DEV0.1 failed-entry checkpoints. No raid was played or scored.
  if state.phase == "cleanup" and state.outcome == "entry_failed" and api.at_home() then
    state.phase = "entering"
    state.outcome = "none"
  end
  if state.phase == "entering" then
    if api.at_raid() then
      state.phase = "active"
    else
      state.last_error = api.at_home()
        and "Entry pending; use the departure terminal to retry this raid."
        or "Entry dimension mismatch; automatic changes stopped."
      -- Loading must not silently retry travel or consume a failed raid's timer.
      return false
    end
  end
  if state.phase == "returning" then return raid.finish(state, api, state.outcome) end
  if state.phase == "cleanup" then return raid.cleanup(state, api) end
  if state.phase == "active" then
    if not api.at_raid() then
      state.last_error = "Active raid dimension mismatch; automatic changes stopped."
      return false
    end
    if api.now() >= state.deadline then return raid.finish(state, api, "timeout") end
  elseif state.phase ~= "home" then
    state.last_error = "Unknown raid phase; automatic changes stopped."
    return false
  end
  return true
end

return raid
