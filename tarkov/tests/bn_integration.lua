-- Runs INSIDE BN's real Lua state, with the actual map, avatar and SQLite world.
local raid = require("data.mods.trkv_raid_core.trkv_lifecycle")
local api = require("data.mods.trkv_raid_core.trkv_bn")
local root = game.mod_storage["trkv_raid_core"]
local state = root.raid
local player = gapi.get_avatar()
local payload = ItypeId.new("trkv_test_payload")

---@param x integer
---@param y integer
local function local_pos(x, y)
  return gapi.get_map():abs_to_bub(TripointAbsMs.new(16 * 24 + x, 16 * 24 + y, 0))
end

local function take_payload()
  local map = gapi.get_map()
  local pos = local_pos(6, 8)
  for _, item in ipairs(map:get_items_at(pos):items()) do
    if item:get_type():str() == "trkv_test_payload" then
      player:add_item(map:detach_item_at(pos, item))
      return
    end
  end
  error("Generated raid did not contain its test payload")
end

if test_data.stage == "enter" then
  assert(api.return_home())
  assert(api.at_home())
  assert(raid.start(state, api, 1800))
  assert(api.at_raid())
  take_payload()
  assert(player:has_item_with_id(payload, false))
  assert(gapi.get_map():set_ter_at(local_pos(15, 15), TerId.new("t_wall"):int_id()))
elseif test_data.stage == "before_restore" then
  test_data.old_state = state
  state.phase = "home"
  state.wins = 90
elseif test_data.stage == "restore" then
  assert(state ~= test_data.old_state, "BN must replace the nested save table")
  assert(state.phase == "active" and api.at_raid())
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_wall"):int_id())
  -- Exercise the registered callbacks, including BN's repeated load notification.
  local mod = game.mod_runtime["trkv_raid_core"]
  mod.loaded()
  mod.extract()
  assert(api.at_home() and state.wins == 1 and state.phase == "home")
  assert(test_data.old_state.phase == "home" and test_data.old_state.wins == 90)
  assert(player:has_item_with_id(payload, false))
  assert(not raid.finish(state, api, "extracted"))
elseif test_data.stage == "loaded_cleanup" then
  assert(api.at_home() and state.phase == "cleanup" and state.wins == 0)
elseif test_data.stage == "recovered_cleanup" then
  assert(api.at_home() and state.phase == "home" and state.wins == 1)
  assert(player:has_item_with_id(payload, false))
elseif test_data.stage == "continue" then
  assert(raid.start(state, api, 1800))
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_floor"):int_id())
  take_payload() -- fixed map loot must regenerate after reset
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.losses == 1 and state.wins == 1)
  assert(not player:has_item_with_id(payload, false))
  assert(raid.start(state, api, 1800))
  state.deadline = api.now()
  assert(raid.recover(state, api))
  assert(api.at_home() and state.losses == 2)
  test_data.passed = true
elseif test_data.stage == "prepare_death" then
  assert(raid.start(state, api, 1800))
  take_payload()
elseif test_data.stage == "verify_death" then
  assert(api.at_home() and state.phase == "home" and state.losses == 3)
  assert(not player:has_item_with_id(payload, false))
elseif test_data.stage == "prepare_write_failure" then
  assert(raid.start(state, api, 1800))
  take_payload()
elseif test_data.stage == "failed_return" then
  assert(not raid.finish(state, api, "extracted"))
  assert(api.at_raid() and state.phase == "returning")
  assert(state.wins == 1 and state.losses == 3)
  assert(player:has_item_with_id(payload, false))
elseif test_data.stage == "retry_return" then
  game.mod_runtime["trkv_raid_core"].extract()
  assert(api.at_home() and state.phase == "home")
  assert(state.wins == 2 and state.losses == 3)
  assert(player:has_item_with_id(payload, false))
  assert(not raid.finish(state, api, "extracted"))
else
  error("Unknown integration stage")
end
