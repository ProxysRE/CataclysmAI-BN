-- Test-only NPC lifecycle probe. Normal player raids remain unchanged.
print("Tarkov NPC probe stage: " .. tostring(test_data.stage))
local raid = assert(package.loaded.trkv_lifecycle)
local api = assert(package.loaded.trkv_bn)
local root = game.mod_storage.trkv_raid_core
local state = root.raid
local participants = assert(package.loaded.trkv_participants)
local function context()
  local current = game.mod_storage.trkv_raid_core.raid
  return { phase = current.phase, sequence = current.sequence, at_raid = api.at_raid() }
end
local function saved_actor()
  return assert(participants.find(game.mod_storage.trkv_raid_core.participants,
    context(), test_data.actor_id))
end

local function record_hostile_group(dead_id)
  test_data.hostile_dead_id = dead_id
  test_data.hostile_ids, test_data.hostile_choices = {}, {}
  for i = 1, 3 do
    local slot = root.participants.slots["hostile_" .. i]
    assert(slot.status == "ready")
    local definition = assert(package.loaded.trkv_loadouts.describe(slot.loadout))
    assert(definition.profile == (i == 1 and "rifle_trained_v1" or "rifle_recruit_v1"))
    test_data.hostile_ids[i], test_data.hostile_choices[i] = slot.id, slot.loadout
  end
  assert(state.encounter == "squad" and state.encounter_deployed and #gapi.get_all_npcs() == (dead_id and 2 or 3))
end

if test_data.stage == "npc_follower_enter" then
  assert(api.at_home() and state.phase == "home")
  assert(game.mod_runtime.trkv_raid_core.depart("empty"))
  assert(api.at_raid() and state.phase == "active" and state.encounter == "empty")
  assert(#gapi.get_all_npcs() == 0)
elseif test_data.stage == "npc_enter" then
  assert(api.at_home() and state.phase == "home")
  local before = state.sequence
  assert(raid.start(state, api, 1800))
  assert(api.at_raid() and state.phase == "active" and state.sequence == before + 1)
  assert(root.participants.sequence == state.sequence and not root.participants.closed)
  assert(next(root.participants.actors) == nil)
elseif test_data.stage == "npc_patrol_setup" then
  assert(participants.register(root.participants, state.sequence, test_data.actor_id,
    test_data.actor_side, "probe_squad", {
      { x = 402, y = 392, z = 0 }, { x = 402, y = 393, z = 0 },
    }))
  test_data.dispatches = 0
  game.npc_ai_functions["TRKV_PATROL_PROBE"] = function(actor)
    test_data.dispatches = test_data.dispatches + 1
    local current = game.mod_storage.trkv_raid_core
    test_data.patrol_target = actor:current_target() ~= nil
    test_data.patrol_moves_before = actor:get_moves()
    local decision_context = context()
    local member = participants.find(current.participants, decision_context, actor:getID():get_value())
    if not member then return false end
    decision_context.dimension = api.raid_id
    local handled, reason = package.loaded.trkv_decision.step_actor(member,
      decision_context, actor, gapi.get_map(), api.now())
    test_data.patrol_moves_after = actor:get_moves()
    test_data.patrol_handled = handled
    test_data.patrol_reason = reason
    return handled
  end
elseif test_data.stage == "npc_group_deploy" or test_data.stage == "npc_group_recover" then
  local specs = {}
  for i, x in ipairs({ 14, 16, 20 }) do
    specs[i] = { slot = "group_" .. i, side = i == 3 and "bear" or "usec", squad = "probe_group",
      route = { { x = 384 + x, y = 398, z = 0 }, { x = 384 + x, y = 399, z = 0 } } }
  end
  if test_data.stage == "npc_group_recover" then
    -- Replay a partial bookkeeping checkpoint against the uniquely tagged live actor.
    root.participants.slots.group_2 = { status = "creating" }
  end
  local ok, reason = package.loaded.trkv_deployment.ensure(root.participants, context(), specs, {
    spawn = function(spec, sequence)
      return test_data.spawn_member(spec.slot, spec.route[1].x, spec.route[1].y, sequence)
    end,
    find_slot = function(sequence, slot)
      local found = {}
      for _, actor in ipairs(gapi.get_all_npcs()) do
        if actor:get_value("trkv_spawn_sequence") == string.format("%d", sequence) and
            actor:get_value("trkv_spawn_slot") == slot then
          found[#found + 1] = actor:getID():get_value()
        end
      end
      return found
    end,
  })
  assert(ok, tostring(reason))
  test_data.group_ids = {}
  for i, spec in ipairs(specs) do
    local slot = root.participants.slots[spec.slot]
    local member = assert(participants.find(root.participants, context(), slot.id))
    assert(member.side == spec.side and member.squad == spec.squad and member.deployment_slot == spec.slot)
    test_data.group_ids[i] = slot.id
  end
elseif test_data.stage == "npc_group_routes" then
  local count = 0
  for _, member in pairs(root.participants.actors) do
    assert(member.patrol.index == test_data.expected_index)
    count = count + 1
  end
  assert(count == 3)
elseif test_data.stage == "npc_live_depart" then
  assert(api.at_home() and state.phase == "home")
  assert(game.mod_runtime.trkv_raid_core.depart("patrol"))
  assert(state.encounter == "patrol" and state.encounter_deployed)
  assert(#gapi.get_all_npcs() == 3)
  local before = #gapi.get_all_npcs()
  local function pos(x, y) return TripointAbsMs.new(384 + x, 384 + y, 0) end
  assert(gapi.can_place_npc_at(pos(18, 18)))
  assert(not gapi.can_place_npc_at(pos(10, 8))) -- wall
  assert(not gapi.can_place_npc_at(pos(14, 14))) -- occupied
  assert(not gapi.can_place_npc_at(TripointAbsMs.new(100000, 100000, 0))) -- outside bubble
  assert(gapi.spawn_npc_at("trkv_missing_template", pos(18, 18)) == nil)
  assert(gapi.spawn_npc_at("trkv_patrol_tester", pos(10, 8)) == nil) -- wall
  assert(gapi.spawn_npc_at("trkv_patrol_tester", pos(14, 14)) == nil) -- occupied
  assert(#gapi.get_all_npcs() == before)
  test_data.group_ids = {}
  for i = 1, 3 do test_data.group_ids[i] = root.participants.slots["patrol_" .. i].id end
elseif test_data.stage == "npc_live_restored" then
  assert(state.encounter == "patrol" and state.encounter_deployed)
  assert(#gapi.get_all_npcs() == 3)
  for i, id in ipairs(test_data.group_ids) do
    assert(root.participants.slots["patrol_" .. i].id == id)
    assert(participants.find(root.participants, context(), id).patrol.index == 2)
  end
elseif test_data.stage == "npc_live_door_setup" then
  local member = assert(participants.find(root.participants, context(), test_data.door_actor_id))
  member.patrol.route = { { x = 393, y = 391, z = 0 }, { x = 396, y = 391, z = 0 } }
  member.patrol.index = 1
  local map = gapi.get_map()
  local position = map:abs_to_bub(TripointAbsMs.new(394, 391, 0))
  local closed = TerId.new("t_door_c"):int_id()
  -- set_ter_at returns false when the desired terrain is already present.
  map:set_ter_at(position, closed)
  assert(map:get_ter_at(position) == closed, "Door setup did not leave a closed door")
elseif test_data.stage == "npc_live_door_open" then
  local member = assert(participants.find(root.participants, context(), test_data.door_actor_id))
  assert(member.patrol.index == 2 and member.patrol.route[2].x == 396)
  assert(gapi.get_map():get_ter_at(gapi.get_map():abs_to_bub(TripointAbsMs.new(394, 391, 0))) ==
    TerId.new("t_door_o"):int_id())
elseif test_data.stage == "npc_live_detour_setup" then
  local member = assert(participants.find(root.participants, context(), test_data.door_actor_id))
  member.patrol.route = { { x = 400, y = 395, z = 0 }, { x = 400, y = 397, z = 0 } }
  member.patrol.index = 1
elseif test_data.stage == "npc_live_detour_intact" then
  local map = gapi.get_map()
  for x = 397, 402 do
    assert(map:get_ter_at(map:abs_to_bub(TripointAbsMs.new(x, 396, 0))) == TerId.new("t_wall"):int_id())
  end
elseif test_data.stage == "npc_live_path_blocked" then
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.door_actor_id then actor = candidate end
  end
  assert(actor)
  local before, position = actor:get_moves(), actor:get_pos_ms()
  local map = gapi.get_map()
  assert(not actor:move_towards(map:abs_to_bub(TripointAbsMs.new(394, 392, 0)))) -- solid wall
  assert(not actor:move_towards(map:abs_to_bub(TripointAbsMs.new(396, 391, 1)))) -- other floor
  assert(actor:get_moves() == before and actor:get_pos_ms() == position)
  assert(map:get_ter_at(map:abs_to_bub(TripointAbsMs.new(394, 392, 0))) == TerId.new("t_wall"):int_id())
elseif test_data.stage == "npc_live_timeout" then
  state.deadline = api.now()
elseif test_data.stage == "npc_combat_depart" or test_data.stage == "npc_reload_depart" then
  assert(api.at_home() and state.phase == "home")
  -- The reload probe needs a field kit regardless of the workflow's seed. Only
  -- replace the picker; use production departure, spawning, JSON and actual AI.
  local catalog = assert(package.loaded.trkv_loadouts)
  local choose = catalog.choose
  if test_data.stage == "npc_reload_depart" then
    catalog.choose = function() return "rifle_field_v1" end
  end
  local ok, departed = pcall(game.mod_runtime.trkv_raid_core.depart, "combat")
  catalog.choose = choose
  assert(ok and departed)
  test_data.combat_id = root.participants.slots.combat_1.id
  test_data.combat_loadout = root.participants.slots.combat_1.loadout
  local definition = assert(package.loaded.trkv_loadouts.describe(test_data.combat_loadout))
  test_data.combat_profile = definition.profile
  test_data.combat_equipment = definition.equipment
  assert(state.encounter == "combat" and state.encounter_deployed)
  assert(#gapi.get_all_npcs() == 1)
elseif test_data.stage == "npc_varied_reload_depart" then
  assert(api.at_home() and state.phase == "home")
  local catalog = assert(package.loaded.trkv_loadouts)
  local choose, pick = catalog.choose, 0
  local choices = { "rifle_ak_v1", "rifle_recruit_field_v1", "rifle_recruit_ak_v1" }
  catalog.choose = function(_, pool)
    pick = pick + 1
    assert(catalog.contains(pool, choices[pick]))
    return choices[pick]
  end
  local ok, entered = pcall(game.mod_runtime.trkv_raid_core.depart, "varied")
  catalog.choose = choose
  assert(ok and entered and pick == 3 and state.encounter_deployed)
  test_data.varied_ids, test_data.varied_choices = {}, {}
  for i = 1, 3 do
    local slot = root.participants.slots["hostile_" .. i]
    assert(slot.status == "ready" and slot.loadout == choices[i])
    test_data.varied_ids[i], test_data.varied_choices[i] = slot.id, slot.loadout
  end
  test_data.combat_id, test_data.combat_loadout = test_data.varied_ids[1], choices[1]
  assert(state.encounter == "varied" and #gapi.get_all_npcs() == 3)
elseif test_data.stage == "npc_varied_checkpoint" then
  state.encounter_deployed = false
elseif test_data.stage == "npc_varied_restored" then
  assert(state.encounter == "varied" and state.encounter_deployed and #gapi.get_all_npcs() == 3)
  for i = 1, 3 do
    local slot = root.participants.slots["hostile_" .. i]
    assert(slot.status == "ready" and slot.id == test_data.varied_ids[i])
    assert(slot.loadout == test_data.varied_choices[i])
    local member = participants.find(root.participants, context(), slot.id)
    assert(member and member.squad == "varied_test" and member.loadout == slot.loadout)
  end
elseif test_data.stage == "npc_hostile_group_depart" then
  assert(api.at_home() and state.phase == "home")
  assert(game.mod_runtime.trkv_raid_core.depart("squad"))
  record_hostile_group()
elseif test_data.stage == "npc_reserved_enter" then
  assert(api.at_home() and state.phase == "home")
  assert(game.mod_runtime.trkv_raid_core.depart("empty"))
  -- Arrange a checkpoint before group deployment; C++ will occupy its first point.
  state.encounter, state.encounter_deployed = "squad", false
  test_data.reserved_choice = nil
  test_data.waiting_ids, test_data.waiting_choices = {}, {}
  test_data.waiting_dead_id = nil
elseif test_data.stage == "npc_reserved_wall" or test_data.stage == "npc_reserved_floor" then
  local wall = test_data.stage == "npc_reserved_wall"
  local map = gapi.get_map()
  local point = map:abs_to_bub(TripointAbsMs.new(398, 398, 0))
  local terrain = TerId.new(wall and "t_wall" or "t_floor"):int_id()
  map:set_ter_at(point, terrain)
  assert(map:get_ter_at(point) == terrain)
  assert(gapi.can_place_npc_at(TripointAbsMs.new(398, 398, 0)) == not wall)
  test_data.reserved_wall = wall
elseif test_data.stage == "npc_reserved_check" then
  assert(state.encounter == "squad" and not state.encounter_deployed)
  assert(not state.deployment_warning and #gapi.get_all_npcs() == (test_data.waiting_dead_id and 1 or 2))
  for _, actor in ipairs(gapi.get_all_npcs()) do
    assert(actor:getID():get_value() ~= test_data.waiting_dead_id)
  end
  local slot = assert(root.participants.slots.hostile_1)
  assert(slot.status == "reserved")
  for i = 2, 3 do
    local ready = assert(root.participants.slots["hostile_" .. i])
    assert(ready.status == "ready")
    assert(package.loaded.trkv_loadouts.contains("technical_recruit_rifle_v1", ready.loadout))
    if test_data.waiting_ids[i] then
      assert(ready.id == test_data.waiting_ids[i] and ready.loadout == test_data.waiting_choices[i])
    end
    test_data.waiting_ids[i], test_data.waiting_choices[i] = ready.id, ready.loadout
  end
  assert(package.loaded.trkv_loadouts.contains("technical_trained_rifle_v1", slot.loadout))
  if test_data.reserved_choice then assert(slot.loadout == test_data.reserved_choice) end
  test_data.reserved_choice = slot.loadout
  if test_data.reserved_wall then
    local map = gapi.get_map()
    assert(map:get_ter_at(map:abs_to_bub(TripointAbsMs.new(398, 398, 0))) == TerId.new("t_wall"):int_id())
    assert(not gapi.can_place_npc_at(TripointAbsMs.new(398, 398, 0)))
  end
elseif test_data.stage == "npc_reserved_released" then
  record_hostile_group(test_data.waiting_dead_id)
  assert(test_data.hostile_choices[1] == test_data.reserved_choice)
  for i = 2, 3 do
    assert(test_data.hostile_ids[i] == test_data.waiting_ids[i])
    assert(test_data.hostile_choices[i] == test_data.waiting_choices[i])
  end
elseif test_data.stage == "npc_hostile_group_checkpoint" then
  state.encounter_deployed = false
elseif test_data.stage == "npc_hostile_group_restored" then
  assert(state.encounter == "squad" and state.encounter_deployed)
  assert(#gapi.get_all_npcs() == (test_data.hostile_dead_id and 2 or 3))
  for i = 1, 3 do
    local slot = root.participants.slots["hostile_" .. i]
    assert(slot.status == "ready" and slot.id == test_data.hostile_ids[i])
    assert(slot.loadout == test_data.hostile_choices[i])
    local member = participants.find(root.participants, context(), slot.id)
    assert(member.side == "hostile_test" and member.squad == "mixed_test" and member.loadout == slot.loadout)
  end
elseif test_data.stage == "npc_combat_checkpoint" then
  state.encounter_deployed = false
elseif test_data.stage == "npc_combat_restored" then
  assert(state.encounter == "combat" and state.encounter_deployed and #gapi.get_all_npcs() == 1)
  assert(root.participants.slots.combat_1.id == test_data.combat_id)
  assert(root.participants.slots.combat_1.loadout == test_data.combat_loadout)
  local member = participants.find(root.participants, context(), test_data.combat_id)
  assert(member.side == "hostile_test" and member.loadout == test_data.combat_loadout)
elseif test_data.stage == "npc_live_casualty_before" then
  test_data.casualty_id = test_data.group_ids[3]
  test_data.casualty_sequence, test_data.casualty_deadline = state.sequence, state.deadline
  test_data.casualty_wins, test_data.casualty_losses = state.wins, state.losses
elseif test_data.stage == "npc_live_casualty_checkpoint" then
  -- Simulate the saved interval before deployment was marked complete. Ready
  -- slots must retain dead members, rather than replacing them on recovery.
  state.encounter_deployed = false
elseif test_data.stage == "npc_live_casualty_check" then
  assert(api.at_raid() and state.phase == "active")
  assert(state.sequence == test_data.casualty_sequence and state.deadline == test_data.casualty_deadline)
  assert(state.wins == test_data.casualty_wins and state.losses == test_data.casualty_losses)
  assert(state.encounter_deployed and #gapi.get_all_npcs() == 2)
  local slot = root.participants.slots.patrol_3
  assert(slot.status == "ready" and slot.id == test_data.casualty_id)
  for _, actor in ipairs(gapi.get_all_npcs()) do
    assert(actor:getID():get_value() ~= test_data.casualty_id)
  end
elseif test_data.stage == "npc_live_wait_restored" then
  for i = 1, 2 do
    local member = assert(participants.find(root.participants, context(), test_data.group_ids[i]))
    assert(member.patrol.index == (i == 1 and 2 or 1))
    assert(member.patrol.route[2].x == (i == 1 and 399 or 400))
  end
elseif test_data.stage == "npc_live_crossing_setup" or test_data.stage == "npc_live_wait_setup" then
  local crossing = test_data.stage == "npc_live_crossing_setup"
  local routes = crossing and {
    { { x = 398, y = 400, z = 0 }, { x = 402, y = 400, z = 0 } },
    { { x = 401, y = 400, z = 0 }, { x = 397, y = 400, z = 0 } },
  } or {
    { { x = 398, y = 402, z = 0 }, { x = 399, y = 402, z = 0 } },
    { { x = 399, y = 402, z = 0 }, { x = 400, y = 402, z = 0 } },
  }
  for i, route in ipairs(routes) do
    local member = assert(participants.find(root.participants, context(), test_data.group_ids[i]))
    member.patrol.route, member.patrol.index = route, 1
  end
elseif test_data.stage == "npc_live_empty" then
  assert(api.at_home() and state.phase == "home")
  assert(game.mod_runtime.trkv_raid_core.depart("empty"))
  assert(state.encounter == "empty" and #gapi.get_all_npcs() == 0)
  assert(next(root.participants.slots) == nil)
elseif test_data.stage == "npc_patrol_restored" then
  local member = saved_actor()
  assert(member.id == test_data.actor_id and member.side == test_data.actor_side)
  assert(member.squad == "probe_squad")
  local saved = member.patrol
  assert(saved.sequence == state.sequence and saved.index == 2)
  assert(saved.route[2].y == 393)
elseif test_data.stage == "npc_patrol_resumed" then
  assert(saved_actor().patrol.index == 1)
elseif test_data.stage == "npc_combat_handoff" then
  local memory = assert(saved_actor().perception)
  assert(memory.status == "visible" and memory.contact.source == "vision")
  local player_position = gapi.get_avatar():abs_pos()
  assert(memory.contact.position.x == player_position.x and memory.contact.position.y == player_position.y)
  assert(memory.contact.position.z == player_position.z and memory.contact.seen_at == api.now())
  assert(test_data.patrol_target and not test_data.patrol_handled)
  assert(test_data.patrol_reason == "threat")
  assert(test_data.patrol_moves_after == test_data.patrol_moves_before,
    "Patrol spent combat actions before handing off to BN")
  assert(saved_actor().patrol.index == 2,
    "Patrol advanced its waypoint while the actor was fighting")
elseif test_data.stage == "npc_memory_hidden" then
  local member = saved_actor()
  local old = assert(member.perception.contact)
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor and not actor:sees(gapi.get_avatar():get_pos_ms()))
  local ctx = context()
  ctx.dimension = api.raid_id
  package.loaded.trkv_perception.observe_actor(member.perception, ctx, actor, api.now(), 30)
  assert(member.perception.status == "remembered")
  assert(member.perception.contact == old and old.position.x == 402 and old.position.y == 390)
  assert(old.expires_at == old.seen_at + 30)
elseif test_data.stage == "npc_search_started" or test_data.stage == "npc_search_restored" then
  local member = saved_actor()
  local plan = assert(member.search.goal)
  assert(member.perception.observed)
  assert(member.decisions.action == "visual_search" and member.decisions.reason == "searching")
  assert(#member.decisions.history <= 8)
  assert(member.search.status == "searching" and plan.attempts == 1 and plan.stalled == 0)
  assert(plan.position.x == 402 and plan.position.y == 390 and plan.position.z == 0)
  assert(plan.deadline == member.perception.contact.expires_at)
  if test_data.stage == "npc_search_started" then
    test_data.search_deadline = plan.deadline
    test_data.search_seen_at = plan.seen_at
  else
    assert(plan.deadline == test_data.search_deadline and plan.seen_at == test_data.search_seen_at)
  end
elseif test_data.stage == "npc_hazard_checkpoint" then
  local member = saved_actor()
  test_data.hazard_attempts = member.search.goal.attempts
  test_data.hazard_patrol_index = member.patrol.index
elseif test_data.stage == "npc_hazard_field" or test_data.stage == "npc_hazard_explosive" then
  local member = saved_actor()
  local expected = test_data.stage == "npc_hazard_field" and "escape_field" or "escape_explosive"
  assert(test_data.patrol_handled and test_data.patrol_reason == expected)
  assert(member.decisions.action == "escape" and member.decisions.reason == expected)
  assert(member.perception.observed)
  assert(member.search.goal.attempts == test_data.hazard_attempts)
  assert(member.patrol.index == test_data.hazard_patrol_index)
  assert(member.search.goal.deadline == test_data.search_deadline)
  assert(member.search.goal.position.x == 402 and member.search.goal.position.y == 390)
elseif test_data.stage == "npc_search_checked" then
  local member = saved_actor()
  assert(member.search.status == "checked" and member.search.goal.attempts == 3)
  assert(member.search.goal.deadline == test_data.search_deadline)
  assert(member.perception.status == "remembered" and test_data.patrol_reason == "checked")
elseif test_data.stage == "npc_search_expired" then
  local member = saved_actor()
  assert(member.perception.status == "none" and member.perception.contact == nil)
  assert(member.search.status == "expired" and member.search.goal.deadline == test_data.search_deadline)
  assert(test_data.patrol_handled and test_data.patrol_reason == "patrol")
elseif test_data.stage == "npc_hearing_area_entry" then
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor)
  local map = gapi.get_map()
  local function absolute(x, y, z) return TripointAbsMs.new(x, y, z or 0) end
  local center = map:abs_to_bub(absolute(386, 394))
  map:set_ter_at(center, TerId.new("t_wall"):int_id())
  assert(map:get_ter_at(center) == TerId.new("t_wall"):int_id())
  local entry = assert(actor:choose_area_entry(absolute(384, 392), absolute(387, 395)))
  assert(entry.x >= 384 and entry.x <= 387 and entry.y >= 392 and entry.y <= 395 and entry.z == 0)
  assert(entry.x ~= 386 or entry.y ~= 394)
  assert(not actor:choose_area_entry(absolute(387, 395), absolute(384, 392)))
  assert(not actor:choose_area_entry(absolute(384, 392, 1), absolute(387, 395, 1)))
  assert(not actor:choose_area_entry(absolute(384, 392), absolute(389, 395)))
  -- An unrelated fully walled region must not yield a seemingly feasible entry.
  local original = {}
  for x = 398, 401 do
    for y = 388, 391 do
      local pos = map:abs_to_bub(absolute(x, y))
      original[#original + 1] = { position = pos, terrain = map:get_ter_at(pos) }
      map:set_ter_at(pos, TerId.new("t_wall"):int_id())
    end
  end
  assert(not actor:choose_area_entry(absolute(398, 388), absolute(401, 391)))
  map:set_ter_at(map:abs_to_bub(absolute(400, 390)), TerId.new("t_floor"):int_id())
  assert(not actor:choose_area_entry(absolute(398, 388), absolute(401, 391)),
    "An isolated passable tile is not a reachable destination")
  for _, cell in ipairs(original) do map:set_ter_at(cell.position, cell.terrain) end
elseif test_data.stage == "npc_hearing_started" or test_data.stage == "npc_hearing_restored" then
  local member = saved_actor()
  local heard = assert(member.hearing.contact)
  assert(heard.source == "sound" and heard.kind == "combat" and heard.radius == 2)
  assert(heard.position.x == 386 and heard.position.y == 394 and heard.position.z == 0)
  assert(member.perception.contact == nil and member.hearing.search.goal.attempts == 1)
  local entry = assert(member.hearing.entry)
  assert(entry.x >= 384 and entry.x <= 387 and entry.y >= 392 and entry.y <= 395 and entry.z == 0)
  assert(entry.x ~= 386 or entry.y ~= 394)
  assert(heard.expires_at == heard.seen_at + 20)
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor and actor:get_value("trkv_heard_noise") == member.hearing.last_event)
  if test_data.stage == "npc_hearing_started" then
    test_data.hearing_event, test_data.hearing_deadline = heard.event, heard.expires_at
    test_data.hearing_entry = { x = entry.x, y = entry.y, z = entry.z }
  else
    assert(heard.event == test_data.hearing_event and heard.expires_at == test_data.hearing_deadline)
    assert(entry.x == test_data.hearing_entry.x and entry.y == test_data.hearing_entry.y and
      entry.z == test_data.hearing_entry.z)
  end
elseif test_data.stage == "npc_hearing_expired" then
  local heard = assert(saved_actor().hearing)
  assert(heard.contact == nil and heard.status == "none")
  assert(heard.search.status == "expired" and heard.search.goal.deadline == test_data.hearing_deadline)
  assert(heard.last_event == test_data.hearing_event)
elseif test_data.stage:match("^npc_cover_reload_") then
  local member, actor = saved_actor()
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor)
  local map = gapi.get_map()
  local wall = map:abs_to_bub(TripointAbsMs.new(401, 390, 0))
  if test_data.stage == "npc_cover_reload_wall" then
    assert(map:get_ter_at(wall) == TerId.new("t_floor"):int_id())
    assert(map:set_ter_at(wall, TerId.new("t_wall"):int_id()))
    member.loadout, member.reload, member.combat = "rifle_field_v1", {}, {}
  elseif test_data.stage == "npc_cover_reload_choose" then
    local observed = gapi.get_avatar():abs_pos()
    assert(actor:can_reload_empty_gun())
    local selected = actor:choose_reload_cover(observed)
    assert(selected and actor:choose_reload_cover(observed, selected))
    test_data.cover_selected = { x = selected.x, y = selected.y, z = selected.z }
    assert(not actor:reload_under_cover(observed), "Cannot reload under cover while still exposed")
    assert(not actor:reload_without_visible_target(), "Idle reload must reject a visible selected target")
    test_data.cover_reloaded = false
  elseif test_data.stage == "npc_cover_reload_idle" then
    assert(member.reload.status == "idle_reloaded" and member.reload.goal == nil)
    assert(member.perception.status == "none" and member.perception.contact == nil and member.perception.observed)
    assert(member.hearing.contact == nil)
    assert(member.decisions.action == "reload" and member.decisions.reason == "idle_reloaded")
    assert(actor:get_value("trkv_reload_result") == "idle_reloaded")
  elseif test_data.stage == "npc_cover_reload_restore_wall" then
    assert(map:set_ter_at(wall, TerId.new("t_floor"):int_id()))
  elseif test_data.stage == "npc_cover_reload_started" or test_data.stage == "npc_cover_reload_restored" then
    local goal = assert(member.reload.goal)
    assert(member.reload.status == "reload_cover" and goal.attempts == 1 and goal.stalled == 0)
    assert(member.decisions.action == "reload" and member.decisions.reason == "reload_cover")
    if test_data.stage == "npc_cover_reload_started" then
      test_data.cover_goal = { x = goal.position.x, y = goal.position.y, z = goal.position.z }
      test_data.cover_deadline = goal.deadline
      test_data.cover_seen_at = member.perception.contact.seen_at
    else
      assert(goal.position.x == test_data.cover_goal.x and goal.position.y == test_data.cover_goal.y)
      assert(goal.position.z == test_data.cover_goal.z and goal.deadline == test_data.cover_deadline)
      assert(member.perception.contact.seen_at == test_data.cover_seen_at)
    end
  elseif test_data.stage == "npc_cover_reload_progress" then
    if member.reload.status == "reloaded" then
      assert(member.reload.goal == nil and member.decisions.action == "reload")
      assert(member.perception.status == "remembered")
      assert(member.perception.contact.seen_at == test_data.cover_seen_at)
      test_data.cover_reloaded = true
    else
      local goal = assert(member.reload.goal, "Cover reload terminated: status=" .. tostring(member.reload.status) ..
        "; failure=" .. tostring(member.reload.failure_reason) ..
        "; executor=" .. actor:get_value("trkv_reload_result") .. "; action=" .. tostring(member.decisions.action))
      assert(member.reload.status == "reload_cover" and goal.deadline == test_data.cover_deadline)
      assert(goal.position.x == test_data.cover_goal.x and goal.position.y == test_data.cover_goal.y)
    end
  else error("Unknown cover reload stage") end
elseif test_data.stage == "npc_lane_clear" or test_data.stage == "npc_lane_setup" then
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor)
  local target = gapi.get_avatar():abs_pos()
  local proposed = actor:choose_standoff_position(target, nil, true)
  if test_data.stage == "npc_lane_clear" then
    assert(proposed == nil, "Clear firing line must not trigger lane recovery")
  else
    assert(proposed and actor:choose_standoff_position(target, proposed, true))
    assert(not actor:choose_standoff_position(TripointAbsMs.new(target.x + 1, target.y, target.z), nil, true))
    saved_actor().combat = {}
  end
elseif test_data.stage == "npc_standoff_setup" or test_data.stage == "npc_standoff_hidden" then
  local actor
  for _, candidate in ipairs(gapi.get_all_npcs()) do
    if candidate:getID():get_value() == test_data.actor_id then actor = candidate end
  end
  assert(actor)
  local target = gapi.get_avatar():abs_pos()
  local proposed = actor:choose_standoff_position(target)
  if test_data.stage == "npc_standoff_hidden" then
    assert(proposed == nil)
  else
    assert(proposed and proposed.z == target.z)
    assert(actor:choose_standoff_position(target, proposed))
    assert(not actor:choose_standoff_position(TripointAbsMs.new(target.x, target.y + 1, target.z)))
    local member = saved_actor()
    member.loadout, member.combat = "rifle_civilian_v1", {}
  end
elseif test_data.stage == "npc_standoff_started" or test_data.stage == "npc_standoff_restored" or
    test_data.stage == "npc_lane_started" or test_data.stage == "npc_lane_restored" then
  local member = saved_actor()
  local expected_kind = test_data.stage:match("^npc_lane_") and "firing_lane" or "standoff"
  local plan = assert(member.combat.goal)
  local trace = assert(member.decisions)
  assert(trace.action == "maneuver" and trace.reason == expected_kind and trace.handled)
  assert(#trace.history <= 8 and trace.history[#trace.history].source == "vision")
  assert(saved_actor().combat.status == expected_kind and plan.kind == expected_kind and plan.attempts == 1 and plan.stalled == 0)
  if test_data.stage == "npc_standoff_started" or test_data.stage == "npc_lane_started" then
    test_data.standoff_position = { x = plan.position.x, y = plan.position.y, z = plan.position.z }
    test_data.standoff_deadline = plan.deadline
    test_data.standoff_arrived = false
    test_data.standoff_trace_at = trace.last_now
    test_data.standoff_trace_size = #trace.history
  else
    assert(plan.position.x == test_data.standoff_position.x and plan.position.y == test_data.standoff_position.y)
    assert(plan.position.z == test_data.standoff_position.z and plan.deadline == test_data.standoff_deadline)
    assert(trace.last_now == test_data.standoff_trace_at and #trace.history == test_data.standoff_trace_size)
  end
elseif test_data.stage == "npc_standoff_progress" or test_data.stage == "npc_lane_progress" then
  local state = assert(saved_actor().combat)
  if state.status == "arrived" then
    assert(state.goal == nil)
    test_data.standoff_arrived = true
  else
    local plan = assert(state.goal)
    assert(state.status == (test_data.stage == "npc_lane_progress" and "firing_lane" or "standoff") and
      plan.deadline == test_data.standoff_deadline)
    assert(plan.position.x == test_data.standoff_position.x and plan.position.y == test_data.standoff_position.y)
  end
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
  assert(next(root.participants.actors) == nil and next(root.participants.slots) == nil and root.participants.closed)
  assert(participants.find(root.participants, context(), test_data.actor_id) == nil)
elseif test_data.stage == "npc_defeat" then
  assert(api.at_raid() and state.phase == "active")
  local losses = state.losses
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.phase == "home" and state.losses == losses + 1)
  assert(next(root.participants.actors) == nil and next(root.participants.slots) == nil and root.participants.closed)
else
  error("Unknown NPC probe stage")
end
