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


-- Test-only controller checkpoint: seeded plain records, not a claim that this
-- patrol actor observed or selected a combat position in the writer process.
local function copy_plain(value)
  if type(value) ~= "table" then return value end
  local result = {}; for k, v in pairs(value) do result[k] = copy_plain(v) end
  return result
end
local function assert_equal_plain(a, b)
  assert(type(a) == type(b), "Cold AI state changed type")
  if type(a) ~= "table" then assert(a == b, "Cold AI state changed value"); return end
  for k, v in pairs(a) do assert_equal_plain(v, b[k]) end
  for k in pairs(b) do assert(a[k] ~= nil, "Cold AI state gained a field") end
end
local function cold_ai_member()
  return assert(root.participants.actors[string.format("%d", root.cold_expected.npc_ids[1])])
end
local function check_cold_ai()
  if not root.cold_expected.ai then return end
  local member = cold_ai_member()
  for name, expected in pairs(root.cold_expected.ai) do assert_equal_plain(expected, member[name]) end
end

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
  local mode = test_data.cold_encounter or "patrol"
  local catalog = package.loaded.trkv_loadouts
  local choose, pick = catalog.choose, 0
  if mode == "varied" then
    local choices = { "rifle_ak_v1", "rifle_recruit_field_v1", "rifle_recruit_ak_v1" }
    catalog.choose = function(_, pool)
      pick = pick + 1
      assert(catalog.contains(pool, choices[pick]))
      return choices[pick]
    end
  end
  local ok, entered = pcall(game.mod_runtime.trkv_raid_core.depart, mode)
  catalog.choose = choose
  assert(ok and entered)
  take_payload()
  assert(gapi.get_map():set_ter_at(local_pos(15, 15), TerId.new("t_wall"):int_id()))
  root.cold_expected = { deadline = state.deadline, sequence = state.sequence, encounter = mode, npc_ids = {}, npc_choices = {} }
  for i = 1, 3 do
    local slot = root.participants.slots[(mode == "varied" and "hostile_" or "patrol_") .. i]
    root.cold_expected.npc_ids[i], root.cold_expected.npc_choices[i] = slot.id, slot.loadout
  end
  test_data.cold_npc_ids = root.cold_expected.npc_ids
  test_data.cold_encounter = root.cold_expected.encounter or "patrol"
elseif test_data.stage == "cold_npc_saved" then
  assert(#gapi.get_all_npcs() == 2)
  for _, id in ipairs(root.cold_expected.npc_ids) do
    assert(root.participants.actors[string.format("%d", id)].patrol.index == (root.cold_expected.encounter == "varied" and 1 or 2))
  end
  -- Persist a replay checkpoint, including the ready slot of a dead actor.
  state.encounter_deployed = false
elseif test_data.stage == "cold_ai_checkpoint" then
  assert(root.cold_expected.encounter == "patrol")
  local member, now = cold_ai_member(), api.now()
  local ctx = { phase = "active", at_raid = true, sequence = state.sequence, dimension = api.raid_id }
  local goal = { x = 398, y = 400, z = 0 }
  member.perception = {}
  package.loaded.trkv_perception.update(member.perception, ctx, now,
    { position = goal }, 30)
  package.loaded.trkv_perception.update(member.perception, ctx, now, nil, 30)
  member.search = { schema = 1, sequence = state.sequence, dimension = api.raid_id,
    observed = true, status = "searching", goal = { position = copy_plain(goal),
      seen_at = now, deadline = now + 30, attempts = 2, stalled = 0 } }
  member.hearing = {}
  package.loaded.trkv_hearing.update(member.hearing, ctx, now,
    string.format("%s|%d|402|402|0|combat", api.raid_id, now))
  assert(member.hearing.contact)
  member.hearing.entry = { x = 400, y = 400, z = 0 }
  member.hearing.search = { schema = 1, sequence = state.sequence, dimension = api.raid_id,
    observed = true, status = "searching", goal = { position = { x = 402, y = 402, z = 0 },
      seen_at = now, deadline = now + 20, attempts = 3, stalled = 1 } }
  member.combat = { schema = 1, sequence = state.sequence, dimension = api.raid_id,
    last_now = now, cooldown_until = now + 12, status = "standoff",
    goal = { position = copy_plain(goal), target = { x = 402, y = 390, z = 0 },
      started_at = now, deadline = now + 8, attempts = 1, stalled = 0 } }
  member.reload = { schema = 1, sequence = state.sequence, dimension = api.raid_id,
    last_now = now, cooldown_until = now + 12, status = "reload_cover",
    goal = { position = copy_plain(goal), threat = { x = 402, y = 390, z = 0 },
      started_at = now, deadline = now + 8, attempts = 1, stalled = 1 } }
  member.decisions = { schema = 1, sequence = state.sequence, dimension = api.raid_id,
    last_now = now, action = "visual_search", reason = "searching", handled = true,
    hearing_input = "new_region", refusals = { combat = "lost_contact" }, history = {} }
  for i = 1, 8 do
    member.decisions.history[i] = { at = now - 8 + i, last_at = now - 8 + i,
      action = i == 8 and "visual_search" or "wait", reason = i == 8 and "searching" or "wait_no_route",
      source = "visual_memory", repeats = i == 8 and 7 or 1 }
  end
  root.cold_expected.ai = {}
  for _, name in ipairs({ "perception", "search", "hearing", "combat", "reload", "decisions" }) do
    root.cold_expected.ai[name] = copy_plain(member[name])
  end
elseif test_data.stage == "cold_ai_resumed" then
  if root.cold_expected.ai then
    local member, expected = cold_ai_member(), root.cold_expected.ai
    assert(member.perception.status == "remembered" and member.perception.observed)
    assert(member.perception.contact.seen_at == expected.perception.contact.seen_at)
    assert(member.perception.contact.expires_at == expected.perception.contact.expires_at)
    assert(member.search.goal.attempts == 3 and member.search.goal.stalled == 0)
    assert(member.search.goal.deadline == expected.search.goal.deadline)
    assert(member.search.goal.position.x == 398 and member.search.goal.position.y == 400)
    assert(member.combat.goal == nil) -- remembered contact cannot continue a firing maneuver
    assert(member.combat.status == "disabled" or member.combat.status == "lost_contact")
    -- This checkpoint uses the unarmed patrol profile. Its restored reload
    -- record must survive deserialization exactly, then be cancelled on use.
    assert(member.reload.goal == nil and member.reload.status == "disabled")
    assert(member.reload.cooldown_until == nil and member.reload.last_now == nil)
    assert(member.decisions.action == "visual_search" and member.decisions.reason == "searching")
    assert(#member.decisions.history == 8 and member.decisions.history[8].repeats == 8)
    assert_equal_plain(expected.hearing.contact, member.hearing.contact)
    assert_equal_plain(expected.hearing.search, member.hearing.search)
    assert_equal_plain(expected.hearing.entry, member.hearing.entry)
  end
elseif test_data.stage == "cold_ai_expired" then
  local member, expected = cold_ai_member(), assert(root.cold_expected.ai)
  assert(member.perception.observed and member.perception.status == "none" and member.perception.contact == nil)
  assert(member.search.status == "expired" and member.search.goal.attempts == 3)
  assert(member.search.goal.deadline == expected.search.goal.deadline)
  assert(member.hearing.contact == nil and member.hearing.status == "none")
  assert(member.hearing.search.status == "expired" and member.hearing.search.goal.attempts == 3)
  assert(member.hearing.search.goal.deadline == expected.hearing.search.goal.deadline)
  assert(member.hearing.last_event == expected.hearing.last_event)
  assert(member.combat.goal == nil and member.decisions.action == "patrol" and member.decisions.handled)
  assert(member.reload.goal == nil and member.reload.status == "disabled")
  assert(#member.decisions.history <= 8)
elseif test_data.stage == "cold_npc_restored" then
  check_cold_ai()
  assert(state.encounter_deployed and #gapi.get_all_npcs() == 2)
  for i, id in ipairs(root.cold_expected.npc_ids) do
    local varied = root.cold_expected.encounter == "varied"
    local slot = root.participants.slots[(varied and "hostile_" or "patrol_") .. i]
    assert(slot.id == id and slot.status == "ready")
    local member = root.participants.actors[string.format("%d", id)]
    assert(member.patrol.index == (varied and 1 or 2) and member.patrol.sequence == state.sequence)
    assert(member.side == (varied and "hostile_test" or i == 3 and "bear" or "usec"))
    if varied then
      assert(member.squad == "varied_test" and slot.loadout == root.cold_expected.npc_choices[i])
    end
  end
elseif test_data.stage == "cold_read_active_loaded" then
  check_cold_ai()
  assert(api.at_raid() and state.phase == "active")
  assert(state.deadline == root.cold_expected.deadline and state.sequence == root.cold_expected.sequence)
  assert(state.wins == 0 and state.losses == 0)
  assert(state.encounter == (root.cold_expected.encounter or "patrol") and not state.encounter_deployed)
  test_data.cold_npc_ids = root.cold_expected.npc_ids
  test_data.cold_encounter = root.cold_expected.encounter or "patrol"
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
  test_data.cold_npc_ids = root.cold_expected.npc_ids
  test_data.cold_encounter = root.cold_expected.encounter or "patrol"
  check_stash()
elseif test_data.stage == "cold_read_cleanup" then
  assert(api.at_home() and state.phase == "home" and state.wins == 1)
  check_stash()
  assert(root.participants.closed and next(root.participants.actors) == nil)
  assert(game.mod_runtime.trkv_raid_core.depart(root.cold_expected.encounter or "patrol"))
  assert(state.sequence == root.cold_expected.sequence + 1)
  assert(#gapi.get_all_npcs() == 3)
  for i = 1, 3 do
    local new_id = root.participants.slots[(root.cold_expected.encounter == "varied" and "hostile_" or "patrol_") .. i].id
    for _, old_id in ipairs(root.cold_expected.npc_ids) do assert(new_id ~= old_id) end
    local fresh = root.participants.actors[string.format("%d", new_id)]
    assert(fresh.perception == nil and fresh.search == nil and fresh.hearing == nil)
    assert(fresh.combat == nil and fresh.reload == nil and fresh.decisions == nil)
  end
  assert(gapi.get_map():get_ter_at(local_pos(15, 15)) == TerId.new("t_floor"):int_id())
  take_payload()
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.losses == 1 and state.wins == 1)
  assert(not player:has_item_with_id(payload, false))
  check_stash()
else
  error("Unknown integration stage")
end
