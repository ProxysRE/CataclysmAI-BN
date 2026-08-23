local mod = game.mod_runtime[game.current_mod]

local RESPONSE_KEY = "npctalk_var_cataclysm_ai_response"
local INPUT_TOPIC = "TALK_CATAI_INPUT"
local RESPONSE_TOPIC = "TALK_CATAI_RESPONSE"
local BRIDGE_TIMEOUT_MS = 15000

local function npc_name(npc)
    return npc:disp_name(false, true)
end

local function sanitize_dialogue_text(text)
    if not text then
        return ""
    end

    -- Dynamic dialogue lines expand <talk_tags>.  External text must not be
    -- allowed to inject those tags back into the dialogue parser.
    text = string.gsub(text, "<", "‹")
    text = string.gsub(text, ">", "›")
    return text
end

local function set_response(npc, text)
    npc:set_value(RESPONSE_KEY, sanitize_dialogue_text(text))
end

local function make_request(npc, player_text)
    local lines = {
        "CATAI/1",
        "NPC_NAME: " .. npc_name(npc),
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

    local name = npc_name(npc)
    local popup = PopupInputStr.new()
    popup:title("Вы")
    popup:desc("Введите реплику для " .. name)
    local player_text = popup:query_str()

    if not player_text or player_text == "" then
        set_response(npc, "...")
        return RESPONSE_TOPIC
    end

    if not cataclysm_ai or not cataclysm_ai.exchange then
        set_response(npc, "CATAI_ERROR: В этой сборке Bright Nights нет Cataclysm AI Bridge.")
        return RESPONSE_TOPIC
    end

    local response = cataclysm_ai.exchange(make_request(npc, player_text), BRIDGE_TIMEOUT_MS)
    if not response or response == "" then
        response = "CATAI_ERROR: внешний процесс вернул пустой ответ."
    end

    set_response(npc, response)
    return RESPONSE_TOPIC
end
