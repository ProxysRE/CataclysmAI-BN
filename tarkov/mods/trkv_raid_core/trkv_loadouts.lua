-- Versioned complete NPC variants: training profile and coherent equipment.
-- Catalog IDs retain their meaning; pools control which variants a role may draw.
local loadouts = {}
local catalog = {
  rifle_ak_v1 = { template = "trkv_combat_ak_tester", profile = "rifle_trained_v1", equipment = "ak_v1" },
  rifle_recruit_ak_v1 = { template = "trkv_combat_recruit_ak_tester", profile = "rifle_recruit_v1", equipment = "ak_v1" },
  rifle_civilian_v1 = { template = "trkv_combat_tester", profile = "rifle_trained_v1", equipment = "civilian_v1" },
  rifle_field_v1 = { template = "trkv_combat_field_tester", profile = "rifle_trained_v1", equipment = "field_v1" },
  rifle_recruit_civilian_v1 = { template = "trkv_combat_recruit_tester",
    profile = "rifle_recruit_v1", equipment = "civilian_v1" },
  rifle_recruit_field_v1 = { template = "trkv_combat_recruit_field_tester",
    profile = "rifle_recruit_v1", equipment = "field_v1" },
}
local pools = {
  technical_trained_rifle_v2 = {
    { id = "rifle_civilian_v1", weight = 3 },
    { id = "rifle_field_v1", weight = 1 },
    { id = "rifle_ak_v1", weight = 2 },
  },
  technical_recruit_rifle_v2 = {
    { id = "rifle_recruit_civilian_v1", weight = 3 },
    { id = "rifle_recruit_field_v1", weight = 1 },
    { id = "rifle_recruit_ak_v1", weight = 2 },
  },
  technical_rifle_v1 = {
    { id = "rifle_civilian_v1", weight = 3 },
    { id = "rifle_field_v1", weight = 1 },
    { id = "rifle_recruit_civilian_v1", weight = 6 },
    { id = "rifle_recruit_field_v1", weight = 2 },
  },
  technical_trained_rifle_v1 = {
    { id = "rifle_civilian_v1", weight = 3 },
    { id = "rifle_field_v1", weight = 1 },
  },
  technical_recruit_rifle_v1 = {
    { id = "rifle_recruit_civilian_v1", weight = 3 },
    { id = "rifle_recruit_field_v1", weight = 1 },
  },
}
-- Reject authoring errors at module load, before any participant can be created.
for _, pool in pairs(pools) do
  local seen, total = {}, 0
  for _, entry in ipairs(pool) do
    assert(catalog[entry.id] and not seen[entry.id], "Invalid/duplicate NPC pool entry")
    assert(type(entry.weight) == "number" and entry.weight % 1 == 0 and entry.weight > 0,
      "Invalid NPC pool weight")
    seen[entry.id], total = true, total + entry.weight
  end
  assert(total > 0, "Empty NPC pool")
  pool.total = total
end

function loadouts.choose(roll, pool_id)
  local pool = type(pool_id) == "string" and pools[pool_id]
  if not pool then error("Unknown NPC pool") end
  local value = roll(1, pool.total)
  if type(value) ~= "number" or value % 1 ~= 0 or value < 1 or value > pool.total then
    error("Invalid loadout roll")
  end
  for _, entry in ipairs(pool) do
    value = value - entry.weight
    if value <= 0 then return entry.id end
  end
end

function loadouts.contains(pool_id, id)
  local pool = type(pool_id) == "string" and pools[pool_id]
  if not pool then return false end
  for _, entry in ipairs(pool) do
    if entry.id == id then return true end
  end
  return false
end

function loadouts.template(id)
  local preset = catalog[id]
  return preset and preset.template or nil
end

-- Return a fresh plain description; callers cannot change the selection catalog.
function loadouts.describe(id)
  local preset = catalog[id]
  if preset then
    return { profile = preset.profile, equipment = preset.equipment, template = preset.template }
  end
  return nil
end

return loadouts
