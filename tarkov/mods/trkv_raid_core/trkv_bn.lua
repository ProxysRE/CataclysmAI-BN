local adapter = {}
adapter.world_type_id = "trkv_raid_space"
adapter.home_id = "trkv_dev01_home"
adapter.raid_id = "trkv_dev01_raid"

---@param dimension string
---@param terrain string
---@param x integer
---@param y integer
local function travel(dimension, terrain, x, y)
  return gapi.place_player_dimension_at({
    dimension_id = dimension,
    target_ms = TripointAbsMs.new(16 * 24 + x, 16 * 24 + y, 0),
    world_type = adapter.world_type_id,
    bounds_min_omt = TripointAbsOmt.new(16, 16, 0),
    bounds_max_omt = TripointAbsOmt.new(16, 16, 0),
    overmap_terrain = { { { terrain } } },
  })
end

function adapter.check_capabilities()
  for _, name in ipairs({ "place_player_dimension_at", "get_current_dimension_id", "reset_dimension" }) do
    if type(gapi[name]) ~= "function" then error("Tarkov DEV0.1 requires BN API: " .. name) end
  end
end

function adapter.at_home() return gapi.get_current_dimension_id() == adapter.home_id end
function adapter.at_raid() return gapi.get_current_dimension_id() == adapter.raid_id end
function adapter.now() return gapi.current_turn():to_turn() end
function adapter.enter() return travel(adapter.raid_id, "trkv_test_yard", 3, 3) end
function adapter.return_home() return travel(adapter.home_id, "trkv_test_home", 12, 12) end
function adapter.cleanup()
  if not adapter.at_home() then return false end
  -- Keep generation metadata so a cleanup saved mid-operation can be repeated.
  return gapi.reset_dimension(adapter.raid_id)
end

function adapter.penalize()
  local player = gapi.get_avatar()
  player:drop_all_items()
  player:clear_effects()
  player:set_all_parts_hp_cur(30)
end

return adapter
