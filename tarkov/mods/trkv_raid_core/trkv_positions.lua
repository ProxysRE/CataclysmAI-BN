-- Ephemeral exclusions from nearby visible squadmates' saved intentions.
-- No global reservation table, engine references or hidden enemy positions.
local positions = {}
local function active(plan, ctx, now)
  local goal = plan and plan.goal
  return plan and plan.schema == 1 and plan.sequence == ctx.sequence and
    plan.dimension == ctx.dimension and goal and now >= goal.started_at and
    now < goal.deadline and (not plan.last_now or now >= plan.last_now)
end

function positions.collect(member, ctx, actor, roster, now, committed)
  local result = {}
  if not roster or roster.schema ~= 1 or roster.closed or roster.sequence ~= ctx.sequence or
      ctx.phase ~= "active" or not ctx.at_raid or not member.id or
      type(member.squad) ~= "string" or member.squad == "" then return result end
  local donors = {}
  for _, other in pairs(roster.actors) do
    -- New plans respect every existing claim. If restored plans conflict,
    -- the lower actor ID retains its claim and the other cancels on validation.
    if other.id ~= member.id and (not committed or other.id < member.id) and
        other.side == member.side and other.squad == member.squad and
        other.patrol.sequence == ctx.sequence and
        (active(other.combat, ctx, now) or active(other.reload, ctx, now)) then
      donors[other.id] = other
    end
  end
  if not next(donors) then return result end
  local origin, seen = actor:get_pos_ms(), {}
  for _, buddy in ipairs(gapi.get_all_npcs()) do
    local other = donors[buddy:getID():get_value()]
    if other and not buddy:is_dead() then
      local p = buddy:get_pos_ms()
      if p.z == origin.z and math.max(math.abs(p.x-origin.x), math.abs(p.y-origin.y)) <= 12 and actor:sees_creature(buddy) then
        for _, name in ipairs({ "combat", "reload" }) do
          local plan = other[name]
          if active(plan, ctx, now) then
            local q = plan.goal.position
            local key = string.format("%d:%d:%d", q.x, q.y, q.z)
            if not seen[key] then
              result[#result + 1], seen[key] = TripointAbsMs.new(q.x, q.y, q.z), true
            end
          end
        end
      end
    end
  end
  return result
end
return positions
