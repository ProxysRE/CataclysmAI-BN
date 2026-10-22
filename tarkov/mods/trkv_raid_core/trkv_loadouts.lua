-- Versioned, coherent technical presets. BN creates and saves their actual items.
local loadouts = {}
local pool = {
  { id = "rifle_civilian_v1", template = "trkv_combat_tester", weight = 3 },
  { id = "rifle_field_v1", template = "trkv_combat_field_tester", weight = 1 },
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

return loadouts
