local mod = game.mod_runtime[game.current_mod]

local RESPONSE_KEY = "npctalk_var_cataclysm_ai_response"
local INPUT_TOPIC = "TALK_CATAI_INPUT"
local RESPONSE_TOPIC = "TALK_CATAI_RESPONSE"

local function set_response(npc, text)
    npc:set_value(RESPONSE_KEY, text)
end

local function make_request(npc, player_text)
    local lines = {
        "CATAI/1",
        "NPC_NAME: " .. npc:get_name(),
        "NPC_HP_PERCENT: " .. tostring(npc:hp_percentage()),
        "PLAYER_TEXT:",
        player_text
    }
    return table.concat(lines, "\n")
end

mod.on_dialogue_option = function(params)
    if params.next_topic ~= INPUT_TOPIC then
        return nil
    end

    local npc = params.npc
    if not npc then
        return nil
    end

    local popup = PopupInputStr.new()
    popup:title("Вы")
    popup:desc("Введите реплику для " .. npc:get_name())
    local player_text = popup:query_str()

    if not player_text or player_text == "" then
        set_response(npc, "...")
        return RESPONSE_TOPIC
    end

    if not cataclysm_ai or not cataclysm_ai.exchange then
        set_response(npc, "CATAI_ERROR: В этой сборке Bright Nights нет Cataclysm AI Bridge.")
        return RESPONSE_TOPIC
    end

    local response = cataclysm_ai.exchange(make_request(npc, player_text), 120000)
    if not response or response == "" then
        response = "CATAI_ERROR: внешний процесс вернул пустой ответ."
    end

    set_response(npc, response)
    return RESPONSE_TOPIC
end
