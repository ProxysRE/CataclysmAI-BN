local mod_id = game.current_mod
local mod = game.mod_runtime[mod_id]

mod.root_path = game.current_mod_path
mod.pending = mod.pending or {}
mod.request_seq = mod.request_seq or 0

local function percent_encode(value)
    local text = tostring(value or "")
    text = text:gsub("%%", "%%25")
    text = text:gsub("|", "%%7C")
    text = text:gsub("\r", "%%0D")
    text = text:gsub("\n", "%%0A")
    return text
end

local function npc_key(npc)
    return tostring(npc:getID():get_value())
end

local function response_path(request_id)
    return mod.root_path .. "/runtime/response_" .. request_id .. ".lua"
end

local function load_response(request_id)
    local chunk, load_error = loadfile(response_path(request_id), "t", {})
    if not chunk then
        return nil, load_error
    end

    local ok, response = pcall(chunk)
    if not ok then
        return nil, response
    end

    if type(response) ~= "table" then
        return nil, "response chunk did not return a table"
    end
    if tostring(response.request_id or "") ~= tostring(request_id) then
        return nil, "response request_id mismatch"
    end

    return response, nil
end

local function emit_request(npc, player_text)
    mod.request_seq = mod.request_seq + 1

    local npc_id = npc_key(npc)
    local request_id = npc_id .. "_" .. tostring(mod.request_seq)
    local avatar = gapi.get_avatar()

    local wire = table.concat({
        "CATAI_REQ",
        "1",
        request_id,
        npc_id,
        percent_encode(npc:get_name()),
        percent_encode(avatar:get_name()),
        percent_encode(player_text),
        percent_encode(tostring(gapi.current_turn()))
    }, "|")

    gdebug.log_info(wire)
    mod.pending[npc_id] = request_id
    return request_id
end

local function show_pending_response(npc)
    local npc_id = npc_key(npc)
    local request_id = mod.pending[npc_id]
    if not request_id then
        return true
    end

    local response, err = load_response(request_id)
    if not response then
        gapi.add_msg("Cataclysm AI: response is not ready yet.")
        if err and not tostring(err):find("No such file", 1, true) then
            gdebug.log_warn("CATAI response read error for " .. request_id .. ": " .. tostring(err))
        end
        return false
    end

    mod.pending[npc_id] = nil
    gdebug.log_info("CATAI_ACK|1|" .. request_id)

    if response.ok == false then
        gapi.add_msg("Cataclysm AI error: " .. tostring(response.error or "unknown sidecar error"))
        return true
    end

    npc:say(tostring(response.text or ""))
    return true
end

mod.open_ai_dialogue = function()
    local pos = gapi.choose_adjacent("Choose an adjacent NPC for AI dialogue", false)
    if not pos then
        return
    end

    local npc = gapi.get_npc_at(pos, false)
    if not npc then
        gapi.add_msg("Cataclysm AI: there is no NPC on that tile.")
        return
    end

    if not show_pending_response(npc) then
        return
    end

    local input = PopupInputStr.new()
    input:title("You")
    input:desc("Say something to " .. npc:get_name() .. ":")
    local player_text = input:query_str()

    if not player_text or player_text == "" then
        return
    end

    local request_id = emit_request(npc, player_text)
    gapi.add_msg("Cataclysm AI: request " .. request_id .. " sent. Open AI dialogue again to receive the answer.")
end

gapi.register_action_menu_entry({
    id = "CATAI_DIALOGUE",
    name = "AI dialogue",
    category = "misc",
    fn = function()
        return mod.open_ai_dialogue()
    end
})

gdebug.log_info("Cataclysm AI stock-BN prototype loaded from " .. tostring(mod.root_path))
