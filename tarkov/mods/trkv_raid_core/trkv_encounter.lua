-- Technical encounters. These actors do not define final PMC diplomacy.
local deployment = require("trkv_deployment")
local loadouts = require("trkv_loadouts")
local encounter = {}
local specs = {}
for i, x in ipairs({ 14, 16, 20 }) do
  specs[i] = { slot = "patrol_" .. i, side = i == 3 and "bear" or "usec", squad = "test_patrol",
    route = { { x = 384 + x, y = 398, z = 0 }, { x = 384 + x, y = 402, z = 0 } } }
end
local combat = { { slot = "combat_1", side = "hostile_test", squad = "combat_test",
  pool = "technical_rifle_v1",
  route = { { x = 402, y = 392, z = 0 }, { x = 402, y = 394, z = 0 } } } }
function encounter.ensure(members, context, mode)
  mode = mode or "patrol"
  if mode ~= "patrol" and mode ~= "combat" then return false, "unknown_encounter" end
  local adapter = {
    spawn = function(spec, sequence, choice)
      local template = "trkv_patrol_tester"
      if mode == "combat" then
        if not loadouts.contains(spec.pool, choice) then return nil end
        template = loadouts.template(choice)
      end
      if not template then return nil end
      local point = spec.route[1]
      local actor = gapi.spawn_npc_at(template, TripointAbsMs.new(point.x, point.y, point.z))
      if not actor then return nil end
      actor:set_value("trkv_spawn_slot", spec.slot)
      actor:set_value("trkv_spawn_sequence", string.format("%d", sequence))
      if choice then actor:set_value("trkv_loadout", choice) end
      return actor:getID():get_value()
    end,
    find_slot = function(sequence, slot, choice)
      local found = {}
      for _, actor in ipairs(gapi.get_all_npcs()) do
        if actor:get_value("trkv_spawn_slot") == slot and
            actor:get_value("trkv_spawn_sequence") == string.format("%d", sequence) and
            (choice == nil or actor:get_value("trkv_loadout") == choice) then
          found[#found + 1] = actor:getID():get_value()
        end
      end
      return found
    end,
  }
  if mode == "combat" then
    adapter.select = function(spec) return loadouts.choose(gapi.rng, spec.pool) end
  end
  return deployment.ensure(members, context, mode == "combat" and combat or specs, adapter)
end
return encounter
