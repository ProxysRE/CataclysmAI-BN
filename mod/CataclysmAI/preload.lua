---@class ModCataclysmAI
---@field registered boolean
---@field register_hooks fun()
---@field on_dialogue_option fun(params: OnDialogueOptionParams): string?
local mod = game.mod_runtime[game.current_mod]

mod.registered = false

mod.register_hooks = function()
    if mod.registered then
        return
    end
    mod.registered = true

    game.add_hook("on_dialogue_option", function(...)
        return mod.on_dialogue_option(...)
    end)
end

game.add_hook("on_game_started", function()
    mod.register_hooks()
end)

game.add_hook("on_game_load", function()
    mod.register_hooks()
end)
