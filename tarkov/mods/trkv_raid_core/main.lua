local mod = game.mod_runtime[game.current_mod]
local storage = game.mod_storage[game.current_mod]
local raid = require("trkv_lifecycle")
local api = require("trkv_bn")
api.check_capabilities()
storage.raid = storage.raid or {}
raid.initialize(storage.raid)
-- BN replaces nested tables while deserializing mod_storage. Resolve it for each
-- callback instead of capturing the table created before a save is loaded.
local function current_state()
  return storage.raid
end

---@param state table
local function report(state)
  gapi.add_msg(string.format("[Tarkov DEV0.1] %s | raids: %d | extracted: %d | lost: %d",
    state.phase, state.sequence, state.wins, state.losses))
  if state.last_error ~= "" then gapi.add_msg(state.last_error) end
end

mod.start = function()
  local state = current_state()
  raid.recover(state, api)
  if (state.phase ~= "home" and state.phase ~= "entering") or not api.at_home() then report(state); return end
  local menu = UiList.new()
  menu:title("Tarkov DEV0.1: departure terminal")
  menu:add(1, state.phase == "entering" and "Retry pending raid entry" or "Enter test raid (30 game minutes)")
  menu:add(2, "Cancel")
  if menu:query() == 1 then raid.start(state, api, 30 * 60); report(state) end
end

mod.extract = function()
  local state = current_state()
  -- Only the mapped exit furniture calls this; there is no pocket evacuation remote.
  if api.at_raid() then raid.finish(state, api, "extracted"); report(state) end
end

mod.started = function()
  if not api.return_home() then error("Could not initialize Tarkov test refuge") end
  gapi.add_msg("Tarkov DEV0.1: examine the departure terminal. Use a NEW, disposable world.")
end

local pending_load_recovery = false
mod.loaded = function()
  -- game::load blocks saves while invoking its load hooks. Dimension travel and
  -- reset both save internally, so recover on the first post-load game tick.
  pending_load_recovery = true
end

---@param params table
mod.death = function(params)
  local state = current_state()
  local character = params and params.char
  if character ~= nil and not character:is_avatar() then return end
  if not api.at_raid() or (state.phase ~= "active" and state.phase ~= "returning") then return end
  -- Clear the fatal state before the engine checks it again.
  local player = gapi.get_avatar()
  player:set_all_parts_hp_to_max()
  player:clear_effects()
  raid.finish(state, api, "defeated")
  report(state)
  return true
end

local function tick()
  local state = current_state()
  if pending_load_recovery then
    pending_load_recovery = false
    raid.recover(state, api)
    report(state)
  end
  local waiting_to_extract = state.phase == "returning" and state.outcome == "extracted"
  if state.phase == "active" or waiting_to_extract then
    local remaining = state.deadline - api.now()
    if remaining <= 0 then
      raid.finish(state, api, "timeout")
      report(state)
    elseif api.at_raid() then
      local level = remaining <= 60 and 2 or (remaining <= 300 and 1 or 0)
      if level > state.time_warning then
        state.time_warning = level
        gapi.add_msg(string.format("[Tarkov DEV0.1] Raid time remaining: %d:%02d. Reach extraction.",
          math.floor(remaining / 60), remaining % 60))
      end
    end
  end
  return true
end
gapi.add_on_every_x_hook(TimeDuration.from_seconds(1), tick)
