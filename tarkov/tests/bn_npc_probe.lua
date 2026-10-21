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

if test_data.stage == "npc_enter" then
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
    local handled, reason = package.loaded.trkv_patrol.step_actor(member.patrol,
      decision_context, actor, gapi.get_map())
    test_data.patrol_moves_after = actor:get_moves()
    test_data.patrol_handled = handled
    test_data.patrol_reason = reason
    return handled
  end
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
  assert(test_data.patrol_target and not test_data.patrol_handled)
  assert(test_data.patrol_reason == "threat")
  assert(test_data.patrol_moves_after == test_data.patrol_moves_before,
    "Patrol spent combat actions before handing off to BN")
  assert(saved_actor().patrol.index == 2,
    "Patrol advanced its waypoint while the actor was fighting")
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
  assert(next(root.participants.actors) == nil and root.participants.closed)
  assert(participants.find(root.participants, context(), test_data.actor_id) == nil)
elseif test_data.stage == "npc_defeat" then
  assert(api.at_raid() and state.phase == "active")
  local losses = state.losses
  assert(raid.finish(state, api, "defeated"))
  assert(api.at_home() and state.phase == "home" and state.losses == losses + 1)
  assert(next(root.participants.actors) == nil and root.participants.closed)
else
  error("Unknown NPC probe stage")
end
