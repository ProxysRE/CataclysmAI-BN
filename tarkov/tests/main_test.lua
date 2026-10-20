-- Callback regression: BN deserialization replaces nested mod_storage tables.
local raid = dofile("tarkov/mods/trkv_raid_core/trkv_lifecycle.lua")
local root, mod = {}, {}
local where, clock, penalties, tick = "home", 100, 0, nil
local loading = false
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
  add_msg = function() end,
  get_avatar = function() return player end,
  add_on_every_x_hook = function(_, fn) tick = fn end,
}
TimeDuration = { from_seconds = function(value) return value end }
package.loaded.trkv_lifecycle = raid
package.loaded.trkv_bn = api
dofile("tarkov/mods/trkv_raid_core/main.lua")
local initial = root.raid

local function restored_raid()
  local replacement = {}
  raid.initialize(replacement)
  where = "home"
  assert(raid.start(replacement, api, 1800))
  root.raid = replacement -- matches BN's replacement of a nested Lua table
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
root.raid = cleanup_checkpoint
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
