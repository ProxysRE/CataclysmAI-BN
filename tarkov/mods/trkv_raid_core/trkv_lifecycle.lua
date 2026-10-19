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
  if state.phase ~= "home" or not api.at_home() then return false end
  state.sequence = state.sequence + 1
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
  state.phase = "cleanup"
  state.outcome = "entry_failed"
  raid.cleanup(state, api)
  return false
end

---@param state RaidState
---@param api RaidAdapter
function raid.recover(state, api)
  raid.initialize(state)
  if state.phase == "entering" then
    if api.at_raid() then state.phase = "active" else state.phase = "cleanup" end
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
