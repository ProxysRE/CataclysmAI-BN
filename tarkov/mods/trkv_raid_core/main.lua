local mod = game.mod_runtime[game.current_mod]
local storage = game.mod_storage[game.current_mod]
local raid = require("trkv_lifecycle")
local api = require("trkv_bn")
api.check_capabilities()
storage.raid = storage.raid or {}
raid.initialize(storage.raid)
local state = storage.raid

local function report()
  gapi.add_msg(string.format("[Tarkov DEV0.1] %s | raids: %d | extracted: %d | lost: %d",
    state.phase, state.sequence, state.wins, state.losses))
  if state.last_error ~= "" then gapi.add_msg(state.last_error) end
end

mod.start = function()
  raid.recover(state, api)
  if state.phase ~= "home" or not api.at_home() then report(); return end
  local menu = UiList.new()
  menu:title("Tarkov DEV0.1: departure terminal")
  menu:add(1, "Enter test raid (30 game minutes)")
  menu:add(2, "Cancel")
  if menu:query() == 1 then raid.start(state, api, 30 * 60); report() end
end

mod.extract = function()
  -- Only the mapped exit furniture calls this; there is no pocket evacuation remote.
  if api.at_raid() then raid.finish(state, api, "extracted"); report() end
end

mod.started = function()
  if not api.return_home() then error("Could not initialize Tarkov test refuge") end
  gapi.add_msg("Tarkov DEV0.1: examine the departure terminal. Use a NEW, disposable world.")
end

mod.loaded = function() raid.recover(state, api); report() end

---@param params table
mod.death = function(params)
  local character = params and params.char
  if character ~= nil and not character:is_avatar() then return end
  if not api.at_raid() or (state.phase ~= "active" and state.phase ~= "returning") then return end
  -- Clear the fatal state before the engine checks it again.
  local player = gapi.get_avatar()
  player:set_all_parts_hp_to_max()
  player:clear_effects()
  raid.finish(state, api, "defeated")
  report()
  return true
end

local function tick()
  if state.phase == "active" and api.now() >= state.deadline then
    raid.finish(state, api, "timeout")
    report()
  end
  return true
end
gapi.add_on_every_x_hook(TimeDuration.from_seconds(1), tick)
