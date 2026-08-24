local mod_id = game.current_mod
local mod = game.mod_runtime[mod_id]
local storage = game.mod_storage[mod_id]

storage.request_seq = storage.request_seq or 0
mod.pending = mod.pending or {}

local BRIDGE_TEST_ID = "bridge_test"

local function npc_key(npc)
    return tostring(npc:getID():get_value())
end

local function response_module(request_id)
    return "lib.catai_runtime.response_" .. request_id
end

local function load_response(request_id)
    local module_name = response_module(request_id)
    local ok, response = pcall(require, module_name)
    if not ok then
        return nil, response
    end

    -- Every response module has a unique request id, but clear it after
    -- consumption so a retry never reuses Lua's package.loaded cache.
    package.loaded[module_name] = nil

    if type(response) ~= "table" then
        return nil, "response module did not return a table"
    end
    if tonumber(response.protocol) ~= 1 then
        return nil, "response protocol mismatch"
    end
    if tostring(response.request_id or "") ~= tostring(request_id) then
        return nil, "response request_id mismatch"
    end

    return response, nil
end

local function persist_request(npc_id, npc_name, player_text)
    storage.request_seq = storage.request_seq + 1

    local request_id = npc_id .. "_" .. tostring(storage.request_seq)
    local avatar = gapi.get_avatar()

    storage.ipc_request = {
        protocol = 1,
        request_id = request_id,
        npc_id = npc_id,
        npc_name = npc_name,
        player_name = avatar:get_name(),
        player_text = player_text,
        current_turn = tostring(gapi.current_turn())
    }
    storage.ipc_ack = nil
    mod.pending[npc_id] = request_id

    -- Stock BN serializes game.mod_storage to <world>/lua_state.json as part
    -- of a normal save. This gives the external companion a deterministic,
    -- engine-supported outbound channel without io/os/loadfile or a custom EXE.
    if not gdebug.save_game() then
        storage.ipc_request = nil
        mod.pending[npc_id] = nil
        return nil, "Bright Nights failed to save the IPC request"
    end

    return request_id, nil
end

local function acknowledge_response(npc_id, request_id)
    mod.pending[npc_id] = nil

    if storage.ipc_request and tostring(storage.ipc_request.request_id or "") == request_id then
        storage.ipc_request = nil
    end
    storage.ipc_ack = request_id

    -- Persist the ACK so a companion restart cannot mistake an already-consumed
    -- request for new work.
    gdebug.save_game()
end

local function pending_request_id(npc_id)
    local request_id = mod.pending[npc_id]

    -- Runtime state is intentionally not saved. Recover a pending request from
    -- persistent mod_storage after loading a save or reloading Lua code.
    if not request_id and storage.ipc_request and tostring(storage.ipc_request.npc_id or "") == npc_id then
        request_id = tostring(storage.ipc_request.request_id or "")
        if request_id ~= "" then
            mod.pending[npc_id] = request_id
        end
    end

    return request_id
end

local function consume_pending_response(npc_id)
    local request_id = pending_request_id(npc_id)
    if not request_id then
        return nil, nil, false
    end

    local response, err = load_response(request_id)
    if not response then
        return nil, err, true
    end

    acknowledge_response(npc_id, request_id)
    return response, nil, true
end

local function show_pending_response(npc)
    local npc_id = npc_key(npc)
    local response, err, had_pending = consume_pending_response(npc_id)

    if not had_pending then
        return true
    end
    if not response then
        gapi.add_msg("Cataclysm AI: response is not ready yet.")
        if err then
            gdebug.log_info("Cataclysm AI pending response " .. npc_id .. ": " .. tostring(err))
        end
        return false
    end

    if response.ok == false then
        gapi.add_msg("Cataclysm AI error: " .. tostring(response.error or "unknown companion error"))
        return true
    end

    npc:say(tostring(response.text or ""))
    return true
end

mod.run_bridge_test = function()
    local response, err, had_pending = consume_pending_response(BRIDGE_TEST_ID)

    if had_pending then
        if not response then
            gapi.add_msg("Cataclysm AI bridge test: response is not ready yet.")
            if err then
                gdebug.log_info("Cataclysm AI bridge test pending: " .. tostring(err))
            end
            return
        end

        if response.ok == false then
            gapi.add_msg("Cataclysm AI bridge test failed: " .. tostring(response.error or "unknown companion error"))
            return
        end

        local text = tostring(response.text or "")
        gapi.add_msg("Cataclysm AI bridge test response: " .. text)
        if text == "[ECHO:Bridge Test] ping" then
            gapi.add_msg("Cataclysm AI bridge test: SUCCESS")
            gdebug.log_info("CATAI_LIVE_BRIDGE_TEST_OK")
        else
            gapi.add_msg("Cataclysm AI bridge test: unexpected ECHO payload")
        end
        return
    end

    local request_id, request_err = persist_request(BRIDGE_TEST_ID, "Bridge Test", "ping")
    if not request_id then
        gapi.add_msg("Cataclysm AI bridge test failed: " .. tostring(request_err))
        return
    end

    gapi.add_msg("Cataclysm AI bridge test request " .. request_id .. " sent. Run AI bridge test again to read the response.")
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

    local npc_id = npc_key(npc)
    local request_id, err = persist_request(npc_id, npc:get_name(), player_text)
    if not request_id then
        gapi.add_msg("Cataclysm AI: " .. tostring(err))
        return
    end

    gapi.add_msg("Cataclysm AI: request " .. request_id .. " sent. Open AI dialogue again to receive the answer.")
end

gapi.register_action_menu_entry({
    id = "CATAI_BRIDGE_TEST",
    name = "AI bridge test",
    category = "misc",
    fn = function()
        return mod.run_bridge_test()
    end
})

gapi.register_action_menu_entry({
    id = "CATAI_DIALOGUE",
    name = "AI dialogue",
    category = "misc",
    fn = function()
        return mod.open_ai_dialogue()
    end
})

gdebug.log_info("Cataclysm AI stock-BN prototype loaded")
