local _ = locale.gettext
local mod = game.mod_runtime[game.current_mod]
local storage = game.mod_storage[game.current_mod]
local raid = require("trkv_lifecycle")
local api = require("trkv_bn")
-- Load while BN still provides package.path.
local decision = require("trkv_decision")
local participants = require("trkv_participants")
require("trkv_deployment")
local encounter = require("trkv_encounter")
api.check_capabilities()
storage.raid = storage.raid or {}
raid.initialize(storage.raid)
-- BN replaces nested tables while deserializing mod_storage. Resolve it for each
-- callback instead of capturing the table created before a save is loaded.
local function current_state()
  return storage.raid
end

local function current_participants()
  storage.participants = storage.participants or {}
  participants.initialize(storage.participants)
  return storage.participants
end

local function prepare_participants()
  local state, members = current_state(), current_participants()
  if state.phase == "home" then
    if members.sequence <= state.settled then participants.finish(members, members.sequence) end
    return true
  end
  if state.phase == "entering" or state.phase == "active" or
      state.phase == "returning" or state.phase == "cleanup" then
    return participants.begin(members, state.sequence)
  end
  return false
end
prepare_participants()

-- Keep bookkeeping in the same path as engine travel/reset, including recovery.
-- Resolve both nested tables afresh: BN replaces them during deserialization.
local engine_enter, engine_cleanup = api.enter, api.cleanup
api.enter = function()
  if not prepare_participants() then return false end
  return engine_enter()
end
api.cleanup = function()
  -- Refuse to drop bookkeeping if the registry belongs to another raid.
  if not prepare_participants() then return false end
  if not engine_cleanup() then return false end
  return participants.finish(current_participants(), current_state().sequence)
end

---@param state table
local function report(state)
  local phases = {
    home = _("At refuge"), entering = _("Entering raid"), active = _("Raid in progress"),
    returning = _("Returning to refuge"), cleanup = _("Resetting raid area"),
  }
  gapi.add_msg(string.format(_("[Tarkov DEV0.1] %s | raids: %d | extracted: %d | lost: %d"),
    phases[state.phase] or state.phase, state.sequence, state.wins, state.losses))
  if state.last_error ~= "" then gapi.add_msg(_(state.last_error)) end
end

local function deploy_encounter()
  local state = current_state()
  if (state.encounter ~= "patrol" and state.encounter ~= "combat" and state.encounter ~= "squad" and state.encounter ~= "varied") or state.encounter_deployed or
      state.phase ~= "active" or not api.at_raid() then
    return
  end
  local ok, reason = encounter.ensure(current_participants(), {
    phase = state.phase, sequence = state.sequence, at_raid = true,
  }, state.encounter)
  if ok then
    state.encounter_deployed = true
  elseif reason == "blocked" then
    return -- Retry blocked entries later; other free slots may already be ready.
  elseif not state.deployment_warning then
    state.deployment_warning = true
    print("Tarkov encounter deployment paused: " .. tostring(reason))
    gapi.add_msg(_("[Tarkov DEV0.1] Encounter deployment paused; leave the raid and start a new one."))
  end
end

game.npc_ai_functions = game.npc_ai_functions or {}
game.npc_ai_functions["TRKV_PATROL"] = function(actor)
  local state = current_state()
  local context = { phase = state.phase, sequence = state.sequence, at_raid = api.at_raid() }
  local member = participants.find(current_participants(), context, actor:getID():get_value())
  if not member then return false end
  context.dimension = api.raid_id
  local handled = decision.step_actor(member, context, actor, gapi.get_map(), api.now())
  return handled
end

mod.depart = function(mode)
  local state = current_state()
  if not api.at_home() then return false end
  if state.phase == "home" then
    if mode ~= "empty" and mode ~= "patrol" and mode ~= "combat" and mode ~= "squad" and mode ~= "varied" then return false end
    state.encounter, state.encounter_deployed, state.deployment_warning = mode, false, false
  end
  local entered = raid.start(state, api, 30 * 60)
  if entered then deploy_encounter() end
  report(state)
  return entered
end

mod.start = function()
  local state = current_state()
  raid.recover(state, api)
  if (state.phase ~= "home" and state.phase ~= "entering") or not api.at_home() then report(state); return end
  local menu = UiList.new()
  menu:title(_("Tarkov DEV0.1: departure terminal"))
  menu:add(1, state.phase == "entering" and _("Retry pending raid entry") or _("Enter test raid (30 game minutes)"))
  if state.phase == "home" then
    menu:add(3, _("Enter patrol test raid (3 neutral NPCs)"))
    menu:add(4, _("Enter combat test raid (1 hostile rifleman)"))
    menu:add(5, _("Enter group test raid (3 hostile NPCs)"))
    menu:add(6, _("Enter varied group raid (3 equipment kits)"))
  end
  menu:add(2, _("Cancel"))
  local choice = menu:query()
  if choice == 1 then mod.depart("empty")
  elseif choice == 3 and state.phase == "home" then mod.depart("patrol")
  elseif choice == 4 and state.phase == "home" then mod.depart("combat")
  elseif choice == 5 and state.phase == "home" then mod.depart("squad")
  elseif choice == 6 and state.phase == "home" then mod.depart("varied") end
end

mod.extract = function()
  local state = current_state()
  -- Only the mapped exit furniture calls this; there is no pocket evacuation remote.
  if api.at_raid() then raid.finish(state, api, "extracted"); report(state) end
end

mod.started = function()
  if not api.return_home() then error("Could not initialize Tarkov test refuge") end
  gapi.add_msg(_("Tarkov DEV0.1: examine the departure terminal. Use a NEW, disposable world."))
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
    prepare_participants()
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
        gapi.add_msg(string.format(_("[Tarkov DEV0.1] Raid time remaining: %d:%02d. Reach extraction."),
          math.floor(remaining / 60), remaining % 60))
      end
    end
  end
  deploy_encounter()
  return true
end
gapi.add_on_every_x_hook(TimeDuration.from_seconds(1), tick)
