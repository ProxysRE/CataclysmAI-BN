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
  gapi.get_map():set_ter_at(local_pos(15, 15), TerId.new("t_wall"))
elseif test_data.stage == "restore" then
  root.raid = test_data.restored
  state = root.raid
  assert(state.phase == "active")
  assert(raid.recover(state, api))
  assert(raid.finish(state, api, "extracted"))
  assert(api.at_home() and state.wins == 1 and state.phase == "home")
  assert(player:has_item_with_id(payload, false))
  assert(not raid.finish(state, api, "extracted"))
  assert(raid.start(state, api, 1800))
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_floor"))
  take_payload() -- fixed map loot must regenerate after reset
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.losses == 1 and state.wins == 1)
  assert(not player:has_item_with_id(payload, false))
  assert(raid.start(state, api, 1800))
  state.deadline = api.now()
  assert(raid.recover(state, api))
  assert(api.at_home() and state.losses == 2)
  test_data.passed = true
else
  error("Unknown integration stage")
end
