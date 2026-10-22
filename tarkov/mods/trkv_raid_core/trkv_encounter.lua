-- Technical patrol encounter. These neutral actors do not define final PMC diplomacy.
local deployment = require("trkv_deployment")
local encounter = {}
local specs = {}
for i, x in ipairs({ 14, 16, 20 }) do
  specs[i] = { slot = "patrol_" .. i, side = i == 3 and "bear" or "usec", squad = "test_patrol",
    route = { { x = 384 + x, y = 398, z = 0 }, { x = 384 + x, y = 399, z = 0 } } }
end
function encounter.ensure(members, context)
  return deployment.ensure(members, context, specs, {
    spawn = function(spec, sequence)
      local point = spec.route[1]
      local actor = gapi.spawn_npc_at("trkv_patrol_tester", TripointAbsMs.new(point.x, point.y, point.z))
      if not actor then return nil end
      actor:set_value("trkv_spawn_slot", spec.slot)
      actor:set_value("trkv_spawn_sequence", string.format("%d", sequence))
      return actor:getID():get_value()
    end,
    find_slot = function(sequence, slot)
      local found = {}
      for _, actor in ipairs(gapi.get_all_npcs()) do
        if actor:get_value("trkv_spawn_slot") == slot and
            actor:get_value("trkv_spawn_sequence") == string.format("%d", sequence) then
          found[#found + 1] = actor:getID():get_value()
        end
      end
      return found
    end,
  })
end
return encounter
