package.loaded.trkv_positions = dofile("tarkov/mods/trkv_raid_core/trkv_positions.lua")
package.loaded.trkv_perception = dofile("tarkov/mods/trkv_raid_core/trkv_perception.lua")
-- Callback regression: BN deserialization replaces nested mod_storage tables.
locale = { gettext = function(text) return text end }
local raid = dofile("tarkov/mods/trkv_raid_core/trkv_lifecycle.lua")
local root, mod = {}, {}
local where, clock, penalties, tick = "home", 100, 0, nil
local loading = false
local messages = {}
local player = {
  set_all_parts_hp_to_max = function() end,
  clear_effects = function() end,
}
local api = {
  check_capabilities = function() end,
  at_home = function() return where == "home" end,
  at_raid = function() return where == "raid" end,
  now = function() return clock end,
  enter = function() where = "raid"; return true end,
  return_home = function() assert(not loading); where = "home"; return true end,
  cleanup = function() assert(not loading); return true end,
  penalize = function() penalties = penalties + 1 end,
}
game = { current_mod = "trkv_raid_core", mod_runtime = { trkv_raid_core = mod },
  mod_storage = { trkv_raid_core = root } }
gapi = {
  add_msg = function(message) messages[#messages + 1] = message end,
  get_avatar = function() return player end,
  add_on_every_x_hook = function(_, fn) tick = fn end,
}
TimeDuration = { from_seconds = function(value) return value end }
package.loaded.trkv_lifecycle = raid
package.loaded.trkv_bn = api
package.loaded.trkv_patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
package.loaded.trkv_participants = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
package.loaded.trkv_deployment = dofile("tarkov/mods/trkv_raid_core/trkv_deployment.lua")
package.loaded.trkv_loadouts = dofile("tarkov/mods/trkv_raid_core/trkv_loadouts.lua")
package.loaded.trkv_encounter = dofile("tarkov/mods/trkv_raid_core/trkv_encounter.lua")
package.loaded.trkv_search = dofile("tarkov/mods/trkv_raid_core/trkv_search.lua")
package.loaded.trkv_hearing = dofile("tarkov/mods/trkv_raid_core/trkv_hearing.lua")
package.loaded.trkv_combat = dofile("tarkov/mods/trkv_raid_core/trkv_combat.lua")
package.loaded.trkv_reload = dofile("tarkov/mods/trkv_raid_core/trkv_reload.lua")
package.loaded.trkv_squad = dofile("tarkov/mods/trkv_raid_core/trkv_squad.lua")
package.loaded.trkv_decision = dofile("tarkov/mods/trkv_raid_core/trkv_decision.lua")
dofile("tarkov/mods/trkv_raid_core/main.lua")
local initial = root.raid

local function restored_raid()
  local replacement = {}
  raid.initialize(replacement)
  where = "home"
  -- Loading a different fixture replaces both nested save tables.
  root.raid, root.participants = replacement, {}
  assert(raid.start(replacement, api, 1800))
  return replacement
end

local extracted = restored_raid()
mod.loaded()
mod.loaded() -- BN's load path invokes load hooks twice
mod.extract()
assert(extracted.phase == "home" and extracted.wins == 1 and where == "home")
assert(initial.phase == "home" and initial.sequence == 0)
print("PASS registered extraction callbacks follow replaced save table")

local timed_out = restored_raid()
clock = timed_out.deadline
assert(tick())
assert(timed_out.phase == "home" and timed_out.losses == 1 and penalties == 1)
print("PASS registered timer follows replaced save table")

local defeated = restored_raid()
assert(mod.death({ char = { is_avatar = function() return false end } }) == nil)
assert(defeated.phase == "active")
assert(mod.death({ char = { is_avatar = function() return true end } }))
assert(defeated.phase == "home" and defeated.losses == 1 and penalties == 2)
print("PASS registered death callback follows replaced save table and ignores NPC death")

local expired_on_load = restored_raid()
clock = expired_on_load.deadline
loading = true
mod.loaded()
mod.loaded()
assert(expired_on_load.phase == "active" and where == "raid")
loading = false
assert(tick())
assert(expired_on_load.phase == "home" and expired_on_load.losses == 1 and penalties == 3)
print("PASS load recovery waits until BN permits saves and transitions")

local cleanup_checkpoint = {}
raid.initialize(cleanup_checkpoint)
cleanup_checkpoint.phase = "cleanup"
cleanup_checkpoint.sequence = 1
cleanup_checkpoint.outcome = "extracted"
root.raid, root.participants = cleanup_checkpoint, {}
loading = true
mod.loaded()
mod.loaded()
assert(cleanup_checkpoint.phase == "cleanup" and cleanup_checkpoint.wins == 0)
loading = false
assert(tick())
assert(cleanup_checkpoint.phase == "home" and cleanup_checkpoint.wins == 1)
assert(tick())
assert(cleanup_checkpoint.wins == 1)
print("PASS repeated load hooks settle cleanup once after loading")

local pending = {}
raid.initialize(pending)
pending.phase, pending.sequence, pending.deadline, pending.entry_duration = "entering", 1, 1, 90
root.raid, where, clock = pending, "home", 5000
local entries = 0
api.enter = function()
  assert(not loading)
  entries = entries + 1
  if entries == 1 then return false end
  where = "raid"
  return true
end
api.cleanup = function() error("Pending entry must not reset a possibly absent dimension") end
loading = true
mod.loaded()
mod.loaded()
loading = false
assert(tick())
assert(entries == 0 and pending.phase == "entering" and where == "home")
assert(pending.wins == 0 and pending.losses == 0 and penalties == 3)
print("PASS loading a pending entry does not retry travel or apply a timeout")

local answer, title = 2, nil
UiList = { new = function() return {
  title = function() end,
  add = function(_, id, text) if id == 1 then title = text end end,
  query = function() return answer end,
} end }
mod.start() -- closing the menu does not retry or discard the attempt
assert(entries == 0 and pending.sequence == 1 and pending.phase == "entering")
assert(title == "Retry pending raid entry")
answer = 1
mod.start() -- first explicit retry still fails
assert(entries == 1 and pending.phase == "entering" and pending.sequence == 1)
mod.start() -- second succeeds, with the originally requested 90 seconds
assert(entries == 2 and pending.phase == "active" and pending.sequence == 1)
assert(pending.deadline == 5090 and pending.wins == 0 and pending.losses == 0)
print("PASS departure callback retries the same pending attempt only after menu confirmation")

-- Restore normal travel/cleanup after the pending-entry fault fixture.
api.enter = function() where = "raid"; return true end
api.cleanup = function() return true end
local warned = restored_raid()
messages = {}
clock = warned.deadline - 301
assert(tick() and #messages == 0)
clock = warned.deadline - 300
assert(tick() and warned.time_warning == 1 and #messages == 1)
assert(messages[1]:find("5:00", 1, true))
assert(tick() and #messages == 1)
clock = warned.deadline - 60
assert(tick() and warned.time_warning == 2 and #messages == 2)
assert(messages[2]:find("1:00", 1, true))
assert(tick() and #messages == 2)
print("PASS raid countdown warns once at five minutes and once at one minute")

local restored_warning = {}
for k, v in pairs(warned) do restored_warning[k] = v end
root.raid = restored_warning
mod.loaded()
mod.loaded()
assert(tick())
-- report() adds a status line on load; count only timer warnings.
local function warning_count()
  local count = 0
  for _, message in ipairs(messages) do
    if message:find("Raid time remaining:", 1, true) then count = count + 1 end
  end
  return count
end
assert(warning_count() == 2 and restored_warning.time_warning == 2)
assert(restored_warning.deadline == warned.deadline)
print("PASS loaded warning state suppresses duplicate countdown and preserves deadline")

local jumped = restored_raid()
messages = {}
clock = jumped.deadline - 45
jumped.phase, jumped.outcome = "returning", "extracted"
assert(tick() and jumped.time_warning == 2 and warning_count() == 1)
assert(messages[1]:find("0:45", 1, true))
-- A failed extraction remains subject to warnings and the same hard deadline.
assert(tick() and warning_count() == 1)
clock = jumped.deadline
assert(tick() and jumped.losses == 1 and jumped.phase == "home")
assert(warning_count() == 1)
assert(raid.start(jumped, api, 1800) and jumped.time_warning == 0)
print("PASS time jumps show only urgent warning and pending extraction still expires")

messages = {}
where = "unrelated"
clock = jumped.deadline - 60
assert(tick() and warning_count() == 0 and jumped.time_warning == 0)
where, jumped.phase = "home", "entering"
assert(tick() and warning_count() == 0)
print("PASS countdown ignores unrelated dimensions and pending entry at home")
