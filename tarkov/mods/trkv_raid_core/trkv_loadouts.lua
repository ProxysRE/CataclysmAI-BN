-- Versioned complete NPC variants: training profile and coherent equipment.
-- Existing IDs retain their meaning. BN saves actual stats, skills, HP and items.
local loadouts = {}
local pool = {
  { id = "rifle_civilian_v1", template = "trkv_combat_tester", profile = "rifle_trained_v1", equipment = "civilian_v1", weight = 3 },
  { id = "rifle_field_v1", template = "trkv_combat_field_tester", profile = "rifle_trained_v1", equipment = "field_v1", weight = 1 },
  { id = "rifle_recruit_civilian_v1", template = "trkv_combat_recruit_tester",
    profile = "rifle_recruit_v1", equipment = "civilian_v1", weight = 6 },
  { id = "rifle_recruit_field_v1", template = "trkv_combat_recruit_field_tester",
    profile = "rifle_recruit_v1", equipment = "field_v1", weight = 2 },
}

function loadouts.choose(roll)
  local total = 0
  for _, preset in ipairs(pool) do total = total + preset.weight end
  local value = roll(1, total)
  if type(value) ~= "number" or value % 1 ~= 0 or value < 1 or value > total then
    error("Invalid loadout roll")
  end
  for _, preset in ipairs(pool) do
    value = value - preset.weight
    if value <= 0 then return preset.id end
  end
end

function loadouts.template(id)
  for _, preset in ipairs(pool) do
    if preset.id == id then return preset.template end
  end
  return nil
end

-- Return a fresh plain description; callers cannot change the selection catalog.
function loadouts.describe(id)
  for _, preset in ipairs(pool) do
    if preset.id == id then
      return { profile = preset.profile, equipment = preset.equipment, template = preset.template }
    end
  end
  return nil
end

return loadouts
