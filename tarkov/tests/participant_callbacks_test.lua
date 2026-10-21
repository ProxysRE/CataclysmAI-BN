-- Exercise the production lifecycle wiring, including replaced nested save tables.
local members = dofile("tarkov/mods/trkv_raid_core/trkv_participants.lua")
local raid = dofile("tarkov/mods/trkv_raid_core/trkv_lifecycle.lua")
local root, mod = {}, {}
local where, clock, answer, tick = "home", 100, 1, nil
local fail_enter, fail_return, fail_cleanup, loading = false, false, false, false
local resets = 0
local function copy(value)
  if type(value) ~= "table" then return value end
  local result = {}
  for k, v in pairs(value) do result[k] = copy(v) end
  return result
end
local api = {
  check_capabilities = function() end,
  at_home = function() return where == "home" end,
  at_raid = function() return where == "raid" end,
  now = function() return clock end,
  enter = function()
    assert(not loading)
    assert(root.participants.sequence == root.raid.sequence and not root.participants.closed)
    if fail_enter then return false end
    where = "raid"; return true
  end,
  return_home = function()
    assert(not loading)
    if fail_return then return false end
    where = "home"; return true
  end,
  cleanup = function()
    assert(not loading and where == "home" and root.raid.phase == "cleanup")
    assert(not root.participants.closed, "Registry closed before engine reset succeeded")
    resets = resets + 1
    return not fail_cleanup
  end,
  penalize = function() end,
}
locale = { gettext = function(s) return s end }
game = { current_mod = "trkv_raid_core", mod_runtime = { trkv_raid_core = mod },
  mod_storage = { trkv_raid_core = root } }
gapi = { add_msg = function() end, add_on_every_x_hook = function(_, fn) tick = fn end,
  get_avatar = function() return { set_all_parts_hp_to_max = function() end, clear_effects = function() end } end }
TimeDuration = { from_seconds = function(v) return v end }
UiList = { new = function() return { title = function() end, add = function() end,
  query = function() return answer end } end }
package.loaded.trkv_lifecycle, package.loaded.trkv_bn = raid, api
package.loaded.trkv_participants = members
package.loaded.trkv_patrol = dofile("tarkov/mods/trkv_raid_core/trkv_patrol.lua")
dofile("tarkov/mods/trkv_raid_core/main.lua")
local function context()
  return { phase = root.raid.phase, sequence = root.raid.sequence, at_raid = api.at_raid() }
end
local function add(id)
  assert(root.raid.phase == "active")
  return assert(members.register(root.participants, root.raid.sequence, id, "usec", "alpha", {
    { x = 1, y = 1, z = 0 }, { x = 1, y = 2, z = 0 },
  }))
end
local function closed()
  assert(where == "home" and root.raid.phase == "home")
  assert(root.participants.closed and next(root.participants.actors) == nil)
end
mod.start()
add(10).patrol.index = 2
add(11)
fail_return = true
mod.extract()
assert(root.raid.phase == "returning" and members.find(root.participants, context(), 10) == nil)
assert(root.participants.actors["10"].patrol.index == 2 and resets == 0)
-- BN replaces BOTH nested tables. Capturing either old identity loses/erases actors.
local old_members = root.participants
root.raid, root.participants = copy(root.raid), copy(root.participants)
old_members.actors["10"].side = "old_table"
fail_return, fail_cleanup = false, true
mod.loaded(); tick()
assert(root.raid.phase == "cleanup" and not root.participants.closed)
assert(root.participants.actors["10"].side == "usec" and root.participants.actors["11"])
local cleanup_raid, cleanup_members = copy(root.raid), copy(root.participants)
answer, fail_cleanup = 2, false
mod.start() -- Terminal recovery uses the same engine cleanup wrapper.
closed()
assert(old_members.actors["10"].side == "old_table")
-- Replay the pre-reset saved checkpoint. Load hooks themselves must do no travel.
root.raid, root.participants = cleanup_raid, cleanup_members
loading = true
local before = resets
mod.loaded(); mod.loaded()
assert(resets == before and not root.participants.closed)
loading = false
tick(); closed()
assert(root.raid.wins == 1)
answer = 1
mod.start()
assert(root.raid.sequence == 2 and next(root.participants.actors) == nil)
add(12).patrol.index = 2
root.raid, root.participants = copy(root.raid), copy(root.participants)
mod.loaded(); tick()
assert(members.find(root.participants, context(), 12).patrol.index == 2)
assert(mod.death({ char = { is_avatar = function() return false end } }) == nil)
assert(root.participants.actors["12"])
assert(mod.death({ char = { is_avatar = function() return true end } }))
closed()
mod.start(); add(13)
clock = root.raid.deadline
tick(); closed()
-- Failed entry never closes/reopens the same pending registry or consumes a new ID.
fail_enter = true
mod.start()
local pending, seq = root.participants, root.raid.sequence
assert(root.raid.phase == "entering" and not pending.closed)
mod.loaded(); tick()
assert(root.participants == pending and root.raid.sequence == seq)
fail_enter = false
mod.start()
assert(root.raid.phase == "active" and root.participants == pending and root.raid.sequence == seq)
-- An old save lacking registry data gets an empty registry, without spawning replacements.
root.participants = nil
mod.loaded(); tick()
assert(root.participants.sequence == seq and not root.participants.closed)
assert(next(root.participants.actors) == nil)
print("PASS participant lifecycle: failed return/reset, checkpoint replay, replaced tables, death, timeout, retry and legacy save")
