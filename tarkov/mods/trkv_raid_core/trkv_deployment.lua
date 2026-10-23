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
  local blocked = false
  for _, spec in ipairs(specs) do
    local slot = state.slots[spec.slot]
    if not slot or slot.status ~= "ready" then
      local id
      if not slot then
        local choice
        if api.select then
          local ok, selected = pcall(api.select, spec, context.sequence)
          if not ok or type(selected) ~= "string" or selected == "" then return false, "selection_failed" end
          choice = selected
        end
        slot = { status = "reserved", loadout = choice }
        state.slots[spec.slot] = slot
      end
      if slot.status == "reserved" then
        -- No engine creation has been attempted. Occupancy can be checked again
        -- after a tick/load without rerolling the reserved variant.
        if api.available then
          local ok, available = pcall(api.available, spec, context.sequence, slot.loadout)
          if not ok or type(available) ~= "boolean" then return false, "placement_failed" end
          if not available then
            blocked = true
            goto next_slot -- This reservation must not hold up other free entries.
          end
        end
        slot.status = "creating" -- Mark uncertainty BEFORE calling the engine.
        local ok, created = pcall(api.spawn, spec, context.sequence, slot.loadout)
        if not ok or created == nil then return false, "spawn_failed" end
        id = created
      else
        -- A prior creation may have succeeded before registration was saved.
        -- Reconcile a uniquely tagged engine actor; never blindly spawn a second one.
        local found = api.find_slot(context.sequence, spec.slot, slot.loadout)
        if #found ~= 1 then return false, #found == 0 and "pending" or "duplicate_slot" end
        id = found[1]
      end
      local member = participants.find(state, context, id)
      local choice = state.slots[spec.slot].loadout
      if member then
        if member.deployment_slot ~= spec.slot or member.side ~= spec.side or member.squad ~= spec.squad or
            (choice ~= nil and member.loadout ~= choice) then
          return false, "registration_conflict"
        end
      else
        member = participants.register(state, context.sequence, id, spec.side, spec.squad, spec.route)
        if not member then return false, "registration_failed" end
        member.deployment_slot = spec.slot
        member.loadout = choice
      end
      state.slots[spec.slot] = { status = "ready", id = id, loadout = choice }
    end
    ::next_slot::
    -- A ready slot remains consumed even if its actor subsequently dies or disappears.
    -- A load/extra terminal interaction must never respawn a defeated opponent.
  end
  if blocked then return false, "blocked" end
  return true
end

return deployment
