-- Test-only NPC lifecycle probe. Normal player raids remain unchanged.
print("Tarkov NPC probe stage: " .. tostring(test_data.stage))
local raid = assert(package.loaded.trkv_lifecycle)
local api = assert(package.loaded.trkv_bn)
local state = game.mod_storage.trkv_raid_core.raid

if test_data.stage == "npc_enter" then
  assert(api.at_home() and state.phase == "home")
  local before = state.sequence
  assert(raid.start(state, api, 1800))
  assert(api.at_raid() and state.phase == "active" and state.sequence == before + 1)
elseif test_data.stage == "npc_patrol_setup" then
  local root = game.mod_storage.trkv_raid_core
  root.patrol_probe = { sequence = state.sequence, index = 1, route = {
    { x = 402, y = 392, z = 0 }, { x = 402, y = 393, z = 0 },
  } }
  test_data.dispatches = 0
  game.npc_ai_functions["TRKV_PATROL_PROBE"] = function(actor)
    test_data.dispatches = test_data.dispatches + 1
    local current = game.mod_storage.trkv_raid_core
    local function pos(point)
      return gapi.get_map():abs_to_bub(TripointAbsMs.new(point.x, point.y, point.z))
    end
    local handled, reason = package.loaded.trkv_patrol.step(current.patrol_probe, {
      phase = current.raid.phase, sequence = current.raid.sequence, at_raid = api.at_raid(),
    }, {
      has_target = function() return actor:current_target() ~= nil end,
      danger = function() return actor:danger_assessment() end,
      at = function(point) return actor:get_pos_ms() == pos(point) end,
      moves = function() return actor:get_moves() end,
      move_to = function(point) actor:move_to(pos(point), true) end,
    })
    test_data.patrol_reason = reason
    return handled
  end
elseif test_data.stage == "npc_patrol_restored" then
  local saved = game.mod_storage.trkv_raid_core.patrol_probe
  assert(saved.sequence == state.sequence and saved.index == 2)
  assert(saved.route[2].y == 393)
elseif test_data.stage == "npc_patrol_resumed" then
  assert(game.mod_storage.trkv_raid_core.patrol_probe.index == 1)
elseif test_data.stage == "npc_step" then
  local actor = assert(test_data.actor)
  local before = actor:get_moves()
  actor:move_to(test_data.destination)
  assert(actor:get_pos_ms() == test_data.destination)
  assert(actor:get_moves() < before, "Moving the NPC did not consume actions")
elseif test_data.stage == "npc_extract" then
  assert(api.at_raid() and state.phase == "active")
  local wins = state.wins
  game.mod_runtime.trkv_raid_core.extract()
  assert(api.at_home() and state.phase == "home" and state.wins == wins + 1)
elseif test_data.stage == "npc_defeat" then
  assert(api.at_raid() and state.phase == "active")
  local losses = state.losses
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.phase == "home" and state.losses == losses + 1)
else
  error("Unknown NPC probe stage")
end
