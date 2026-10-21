-- Engine-independent creation of a fixed encounter. Never persist actor references.
local participants = require("trkv_participants")
local deployment = {}
local function integer(value) return type(value) == "number" and value % 1 == 0 end
local function valid_manifest(specs)
  if type(specs) ~= "table" then return false end
  local seen = {}
  for _, spec in ipairs(specs) do
    if type(spec) ~= "table" or type(spec.slot) ~= "string" or spec.slot == "" or seen[spec.slot] or
        type(spec.side) ~= "string" or spec.side == "" or type(spec.squad) ~= "string" or
        type(spec.route) ~= "table" or #spec.route < 2 then return false end
    seen[spec.slot] = true
    for _, point in ipairs(spec.route) do
      if type(point) ~= "table" or not integer(point.x) or not integer(point.y) or not integer(point.z) then
        return false
      end
    end
  end
  return true
end

function deployment.ensure(state, context, specs, api)
  if type(state) ~= "table" or state.schema ~= 1 or state.closed or
      context.phase ~= "active" or not context.at_raid or state.sequence ~= context.sequence then
    return false, "inactive"
  end
  if not valid_manifest(specs) then return false, "invalid_manifest" end
  state.slots = state.slots or {}
  for _, spec in ipairs(specs) do
    local slot = state.slots[spec.slot]
    if not slot or slot.status ~= "ready" then
      local id
      if slot then
        -- A prior creation may have succeeded before registration was saved.
        -- Reconcile a uniquely tagged engine actor; never blindly spawn a second one.
        local found = api.find_slot(context.sequence, spec.slot)
        if #found ~= 1 then return false, #found == 0 and "pending" or "duplicate_slot" end
        id = found[1]
      else
        state.slots[spec.slot] = { status = "creating" }
        local ok, created = pcall(api.spawn, spec, context.sequence)
        if not ok or created == nil then return false, "spawn_failed" end
        id = created
      end
      local member = participants.find(state, context, id)
      if member then
        if member.deployment_slot ~= spec.slot or member.side ~= spec.side or member.squad ~= spec.squad then
          return false, "registration_conflict"
        end
      else
        member = participants.register(state, context.sequence, id, spec.side, spec.squad, spec.route)
        if not member then return false, "registration_failed" end
        member.deployment_slot = spec.slot
      end
      state.slots[spec.slot] = { status = "ready", id = id }
    end
    -- A ready slot remains consumed even if its actor subsequently dies or disappears.
    -- A load/extra terminal interaction must never respawn a defeated opponent.
  end
  return true
end

return deployment
