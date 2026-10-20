-- Runs INSIDE BN's real Lua state, with the actual map, avatar and SQLite world.
print("Tarkov runtime stage: " .. tostring(test_data.stage))
-- BN clears package.path after mod loading. Use the exact module instances
-- already loaded by main.lua, without invoking out-of-context require again.
local raid = assert(package.loaded.trkv_lifecycle, "Lifecycle module was not loaded by main.lua")
local api = assert(package.loaded.trkv_bn, "BN adapter was not loaded by main.lua")
local root = game.mod_storage["trkv_raid_core"]
local state = root.raid
local player = gapi.get_avatar()
local payload = ItypeId.new("trkv_test_payload")

---@param x integer
---@param y integer
local function local_pos(x, y, z)
  return gapi.get_map():abs_to_bub(TripointAbsMs.new(16 * 24 + x, 16 * 24 + y, z or 0))
end

local function check_boundary()
  local map = gapi.get_map()
  local border = TerId.new("t_pd_border"):int_id()
  local floor = TerId.new("t_floor"):int_id()
  -- Six faces of the bounded space, including above and below the playable floor.
  -- Try the actual setter, not a mock: outside geometry must not become floor.
  for _, xyz in ipairs({{-1, 12, 0}, {24, 12, 0}, {12, -1, 0},
      {12, 24, 0}, {12, 12, -1}, {12, 12, 1}}) do
    local pos = local_pos(xyz[1], xyz[2], xyz[3])
    assert(map:get_ter_at(pos) == border, "Space boundary has unexpected terrain")
    assert(not map:set_ter_at(pos, floor), "Map setter changed terrain outside space bounds")
    assert(map:get_ter_at(pos) == border, "Space boundary was replaced")
  end
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

-- Keep only a plain marker across travel. Never retain a Map/Item reference
-- while BN unloads the refuge and loads another dimension.
local stash_marker = "trkv_extracted_package_1"
local function check_stash()
  assert(api.at_home())
  local items = gapi.get_map():get_items_at(local_pos(8, 10)):items()
  assert(#items == 1, "Refuge locker must keep exactly one stored package")
  assert(items[1]:get_type():str() == "trkv_test_payload")
  assert(items[1]:get_var_str("trkv_stash", "") == stash_marker,
    "Refuge locker lost or replaced the extracted package")
end

local function store_payload()
  assert(api.at_home())
  for _, item in ipairs(player:all_items(false)) do
    if item:get_type():str() == "trkv_test_payload" then
      item:set_var_str("trkv_stash", stash_marker)
      local detached = player:remove_item(item)
      assert(gapi.get_map():add_item(local_pos(8, 10), detached) == nil,
        "Could not place the extracted package in the refuge locker")
      assert(not player:has_item_with_id(payload, false))
      check_stash()
      return
    end
  end
  error("No extracted package to store in the refuge")
end

local function fixture(marker)
  for _, item in ipairs(player:all_items(false)) do
    if item:get_var_str("trkv_fixture", "") == marker then return item end
  end
  error("Missing carried fixture: " .. marker)
end

local function check_equipped()
  assert(player:is_wielding(fixture("rifle")), "Test rifle is no longer wielded")
  assert(player:is_worn(fixture("nested_container")), "Test backpack is no longer worn")
end

if test_data.stage == "home" then
  game.mod_runtime["trkv_raid_core"].started()
  assert(api.at_home() and state.phase == "home")
elseif test_data.stage == "control_loaded" then
  assert(api.at_home() and state.phase == "home" and state.sequence == 0)
  check_boundary()
  -- Equip only after BN's no-travel normalization reload, before the C++
  -- baseline snapshots. Subsequent JSON comparisons still include every field.
  assert(player:wield(fixture("rifle")))
  assert(player:wear(fixture("nested_container"), false))
  check_equipped()
elseif test_data.stage == "failed_entry" then
  assert(not raid.start(state, api, 1800))
  assert(api.at_home() and state.phase == "entering" and state.sequence == 1)
  assert(state.wins == 0 and state.losses == 0 and state.outcome == "none")
  check_equipped()
  -- Time spent waiting at home must not turn a failed entry into a defeat.
  state.deadline = api.now() - 1
  assert(not raid.recover(state, api))
  assert(api.at_home() and state.phase == "entering" and state.losses == 0)
elseif test_data.stage == "entry_loaded" then
  assert(api.at_home() and state.phase == "entering" and state.sequence == 1)
  assert(state.deadline < api.now() and state.entry_duration == 1800)
  assert(state.wins == 0 and state.losses == 0 and state.settled == 0)
  check_equipped()
elseif test_data.stage == "enter" then
  assert(api.return_home())
  assert(api.at_home())
  assert(raid.start(state, api, 1800))
  assert(state.sequence == 1 and state.deadline == api.now() + 1800)
  assert(api.at_raid())
  check_boundary()
  check_equipped()
  take_payload()
  assert(player:has_item_with_id(payload, false))
  assert(gapi.get_map():set_ter_at(local_pos(15, 15), TerId.new("t_wall"):int_id()))
  -- The next real game::load/tick must warn, without renewing this saved deadline.
  assert(state.time_warning == 0)
  state.deadline = api.now() + 60
  test_data.warning_deadline = state.deadline
elseif test_data.stage == "before_restore" then
  test_data.old_state = state
  state.phase = "home"
  state.wins = 90
elseif test_data.stage == "restore" then
  assert(state ~= test_data.old_state, "BN must replace the nested save table")
  assert(state.phase == "active" and api.at_raid())
  assert(state.time_warning == 2 and state.deadline == test_data.warning_deadline)
  check_boundary()
  check_equipped()
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_wall"):int_id())
  -- Exercise the registered callbacks, including BN's repeated load notification.
  local mod = game.mod_runtime["trkv_raid_core"]
  mod.loaded()
  mod.extract()
  assert(api.at_home() and state.wins == 1 and state.phase == "home")
  assert(test_data.old_state.phase == "home" and test_data.old_state.wins == 90)
  assert(player:has_item_with_id(payload, false))
  assert(not raid.finish(state, api, "extracted"))
  check_equipped()
elseif test_data.stage == "loaded_cleanup" then
  assert(api.at_home() and state.phase == "cleanup" and state.wins == 0)
elseif test_data.stage == "recovered_cleanup" then
  assert(api.at_home() and state.phase == "home" and state.wins == 1)
  check_boundary()
  assert(player:has_item_with_id(payload, false))
  check_equipped()
  store_payload()
elseif test_data.stage == "continue" then
  check_stash()
  assert(raid.start(state, api, 1800))
  assert(state.time_warning == 0)
  check_boundary()
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_floor"):int_id())
  take_payload() -- fixed map loot must regenerate after reset
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.losses == 1 and state.wins == 1)
  assert(not player:has_item_with_id(payload, false))
  check_stash()
  assert(raid.start(state, api, 1800))
  state.deadline = api.now()
  assert(raid.recover(state, api))
  assert(api.at_home() and state.losses == 2)
  check_stash()
  test_data.passed = true
elseif test_data.stage == "prepare_death" then
  assert(raid.start(state, api, 1800))
  take_payload()
elseif test_data.stage == "verify_death" then
  assert(api.at_home() and state.phase == "home" and state.losses == 3)
  assert(not player:has_item_with_id(payload, false))
  check_stash()
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
  check_stash()
elseif test_data.stage == "cold_write" then
  assert(api.at_home() and state.phase == "home")
  player:add_item_with_id(payload, -1)
  store_payload()
  assert(raid.start(state, api, 1800))
  take_payload()
  assert(gapi.get_map():set_ter_at(local_pos(15, 15), TerId.new("t_wall"):int_id()))
  root.cold_expected = { deadline = state.deadline, sequence = state.sequence }
elseif test_data.stage == "cold_read_active_loaded" then
  assert(api.at_raid() and state.phase == "active")
  assert(state.deadline == root.cold_expected.deadline and state.sequence == root.cold_expected.sequence)
  assert(state.wins == 0 and state.losses == 0)
  assert(player:has_item_with_id(payload, false))
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_wall"):int_id())
  check_boundary()
elseif test_data.stage == "cold_read_active" then
  assert(state.deadline == root.cold_expected.deadline)
  game.mod_runtime["trkv_raid_core"].extract()
  assert(api.at_home() and state.phase == "home" and state.wins == 1)
  assert(player:has_item_with_id(payload, false))
  check_stash()
  -- reset_dimension saved cleanup before clearing; do not overwrite that checkpoint.
elseif test_data.stage == "cold_read_cleanup_loaded" then
  assert(api.at_home() and state.phase == "cleanup" and state.wins == 0)
  assert(state.sequence == root.cold_expected.sequence)
  check_stash()
elseif test_data.stage == "cold_read_cleanup" then
  assert(api.at_home() and state.phase == "home" and state.wins == 1)
  check_stash()
  assert(raid.start(state, api, 1800))
  assert(state.sequence == root.cold_expected.sequence + 1)
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_floor"):int_id())
  take_payload()
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.losses == 1 and state.wins == 1)
  assert(not player:has_item_with_id(payload, false))
  check_stash()
else
  error("Unknown integration stage")
end
