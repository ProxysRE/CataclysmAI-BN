local mod = game.mod_runtime[game.current_mod]
---@param params table
game.examine_functions["TRKV_DEPART"] = function(params)
  if params.user:is_avatar() then mod.start() end
end
---@param params table
game.examine_functions["TRKV_EXTRACT"] = function(params)
  if params.user:is_avatar() then mod.extract() end
end
table.insert(game.hooks.on_game_started, function() mod.started() end)
table.insert(game.hooks.on_game_load, function() mod.loaded() end)
---@param params table
table.insert(game.hooks.on_character_death, function(params) return mod.death(params) end)
