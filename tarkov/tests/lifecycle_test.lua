local raid = dofile("tarkov/mods/trkv_raid_core/trkv_lifecycle.lua")
local count = 0

---@param name string
---@param fn fun()
local function test(name, fn)
  fn()
  count = count + 1
  print("PASS " .. name)
end

---@class FakeWorld
---@field where string
---@field clock integer
---@field penalties integer
---@field resets integer
---@field fail_return boolean
---@field fail_cleanup boolean
---@field fail_enter boolean
---@field saved table|nil

---@param value table
local function copy(value)
  local result = {}
  for k, v in pairs(value) do result[k] = type(v) == "table" and copy(v) or v end
  return result
end

local function fixture()
  local state = {}
  raid.initialize(state)
  local world = { where = "home", clock = 100, penalties = 0, resets = 0 }
  local api = {
    at_home = function() return world.where == "home" end,
    at_raid = function() return world.where == "raid" end,
    now = function() return world.clock end,
    enter = function()
      if world.fail_enter then return false end
      world.where = "raid"
      return true
    end,
    return_home = function()
      if world.fail_return then return false end
      world.where = "home"
      return true
    end,
    cleanup = function()
      assert(world.where == "home", "Cleanup attempted while occupied")
      world.saved = copy(state) -- mirrors the engine's save BEFORE reset
      world.resets = world.resets + 1
      return not world.fail_cleanup
    end,
    penalize = function() world.penalties = world.penalties + 1 end,
  }
  return state, api, world
end

test("extraction and duplicate completion", function()
  local s, a, w = fixture()
  assert(raid.start(s, a, 1800))
  assert(not raid.start(s, a, 1800))
  assert(raid.finish(s, a, "extracted"))
  assert(s.wins == 1 and s.losses == 0 and w.penalties == 0)
  assert(not raid.finish(s, a, "extracted"))
end)

test("defeat penalty is applied only once after failed return", function()
  local s, a, w = fixture()
  assert(raid.start(s, a, 1800))
  w.fail_return = true
  assert(not raid.finish(s, a, "defeated"))
  assert(w.penalties == 1 and s.phase == "returning")
  w.fail_return = false
  assert(raid.recover(s, a))
  assert(w.penalties == 1 and s.losses == 1)
end)

test("cleanup failure blocks next raid and is retryable", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.fail_cleanup = true
  assert(not raid.finish(s, a, "extracted"))
  assert(s.phase == "cleanup" and s.wins == 0)
  assert(not raid.start(s, a, 1800))
  w.fail_cleanup = false
  assert(raid.recover(s, a) and s.wins == 1)
end)

test("reload engine's cleanup checkpoint does not duplicate rewards", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  assert(raid.finish(s, a, "extracted"))
  local restored = w.saved
  assert(restored.phase == "cleanup" and restored.wins == 0)
  assert(raid.recover(restored, a) and restored.wins == 1)
  assert(raid.recover(restored, a) and restored.wins == 1)
end)

test("late extraction becomes timeout", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.clock = s.deadline
  assert(raid.finish(s, a, "extracted"))
  assert(s.outcome == "timeout" and s.losses == 1 and w.penalties == 1)
end)

test("timeout is checked immediately on load", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.clock = s.deadline + 1
  assert(raid.recover(s, a))
  assert(s.losses == 1 and w.penalties == 1)
end)

test("loading active raid preserves deadline", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  local restored = copy(s)
  w.clock = 500
  assert(raid.recover(restored, a))
  assert(restored.phase == "active" and restored.deadline == 1900)
end)

test("entry failure never awards victory or applies inventory penalty", function()
  local s, a, w = fixture()
  w.fail_enter = true
  assert(not raid.start(s, a, 1800))
  assert(s.wins == 0 and s.losses == 0 and w.penalties == 0)
end)

test("entering checkpoint recovers at destination", function()
  local s, a, w = fixture()
  s.phase = "entering"
  s.deadline = 1900
  w.where = "raid"
  assert(raid.recover(s, a) and s.phase == "active")
end)

test("dimension mismatch does not delete or penalize unrelated world", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.where = "unrelated"
  assert(not raid.recover(s, a))
  assert(not raid.finish(s, a, "defeated"))
  assert(w.penalties == 0 and w.resets == 0)
end)

test("stale return cannot teleport player out of unrelated dimension", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.fail_return = true
  assert(not raid.finish(s, a, "extracted"))
  w.fail_return = false
  w.where = "unrelated"
  assert(not raid.recover(s, a))
  assert(w.where == "unrelated" and w.penalties == 0 and w.resets == 0)
end)

test("death during failed extraction becomes defeat", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.fail_return = true
  assert(not raid.finish(s, a, "extracted"))
  w.fail_return = false
  assert(raid.finish(s, a, "defeated"))
  assert(s.outcome == "defeated" and s.losses == 1 and s.wins == 0 and w.penalties == 1)
end)

test("failed extraction expires before retry", function()
  local s, a, w = fixture()
  raid.start(s, a, 1800)
  w.fail_return = true
  assert(not raid.finish(s, a, "extracted"))
  w.fail_return = false
  w.clock = s.deadline
  assert(raid.recover(s, a))
  assert(s.outcome == "timeout" and s.losses == 1 and s.wins == 0 and w.penalties == 1)
end)

test("unknown schema and phase fail closed", function()
  assert(not pcall(raid.initialize, { schema = 99 }))
  local s, a = fixture()
  s.phase = "unexpected"
  assert(not raid.recover(s, a))
end)

test("multiple raids keep independent outcomes", function()
  local s, a, w = fixture()
  for i = 1, 5 do
    assert(raid.start(s, a, 1800))
    assert(raid.finish(s, a, i % 2 == 0 and "defeated" or "extracted"))
  end
  assert(s.sequence == 5 and s.wins == 3 and s.losses == 2 and w.penalties == 2)
end)

print(string.format("%d lifecycle tests passed (Lua fixtures, not BN runtime)", count))
