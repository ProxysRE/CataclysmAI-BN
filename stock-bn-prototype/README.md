# Stock Bright Nights AI bridge

This prototype runs with an **unmodified official Cataclysm: Bright Nights Windows build**. It does not compile, patch, or replace `cataclysm-bn-tiles.exe`.

The stock-binary transport has been validated live in a persistent Windows world with both the synthetic bridge test and a real NPC ECHO exchange.

## Transport

```text
player types a line in BN
        |
        v
Lua writes game.mod_storage["cataclysm_ai"].ipc_request
        |
        v
ONE forced gdebug.save_game() for the new outbound request
        |
        v
<BN user dir>/save/<world>/lua_state.json
        |
        v
Python companion decodes BN's serialized Lua table
        |
        v
Provider generates/reuses a response
        |
        v
<BN>/data/lua/lib/catai_runtime/response_<id>.lua
        |
        v
Lua require("lib.catai_runtime.response_<id>")
        |
        v
NPC displays the returned text
```

No DLL injection, binary patching, CMake, vcpkg, `io`, `os`, `loadfile`, or custom game executable is required.

## Save behavior

A new external AI request currently needs one normal BN save because stock Lua has no direct writable file/socket API suitable for the outbound bridge. The save publishes `game.mod_storage` to the world's `lua_state.json`.

The original prototype also forced a second full save after consuming every response just to persist an ACK. That has been removed.

After a response is consumed, Lua clears the request **in live `mod_storage` only**. The cleared state is persisted naturally by the next ordinary game save or by the next AI request. Therefore receiving an answer does not itself trigger another full-world save.

Expected steady-state behavior:

```text
new player line -> one save -> Python response -> NPC answer -> no ACK save
```

## Idempotent companion cache

Removing the forced ACK save creates one crash/restart edge case: the on-disk `lua_state.json` may still contain an already-processed request until BN next saves.

To prevent that from causing another LLM/provider call, the companion stores the exact result of processed requests in:

```text
<BN>/data/lua/lib/catai_runtime/companion_cache.json
```

The cache key includes both the world-state path and `request_id`. On a companion restart, a stale request is answered from the cached result instead of calling the provider again.

The cache is bounded and written atomically. Old ACK-based saves remain readable for backwards compatibility.

## Provider layer

Transport and response generation are now separated:

```text
sidecar/providers.py
```

Current provider:

- `EchoProvider` — deterministic transport verification.

The sidecar accepts:

```text
--provider echo
```

A real LLM provider can now be added without changing save parsing, polling, response-module publication, or the BN Lua transport.

## Why stock BN can do this

Bright Nights already supplies the two mechanisms needed by the bridge:

1. `game.mod_storage` is serialized by the engine during a normal save to the world's `lua_state.json`.
2. `require()` remains enabled and uses BN's C++ Lua module searcher, so `lib.*` modules can be loaded from `data/lua/lib/` even though stock BN disables Lua `dofile`, `loadfile`, `load`, and `loadstring`.

Python decodes BN's actual `serialize_lua_table()` representation (`entries` plus typed key/value wrappers), not an ordinary-JSON approximation.

## Files

```text
stock-bn-prototype/
  run_stock_bn_ai.cmd
  launch_stock_bn_ai.py
  mod/CataclysmAI/
    modinfo.json
    main.lua
  sidecar/
    providers.py
    cataclysm_ai_stock_sidecar.py
```

The companion creates:

```text
<BN>/data/lua/lib/catai_runtime/
```

## Windows launch

1. Unpack an official Windows Bright Nights archive into a writable directory.
2. Double-click `run_stock_bn_ai.cmd`.
3. Enter the directory containing `cataclysm-bn-tiles.exe`.
4. Create/load a world with **Cataclysm AI** enabled.

Direct launcher equivalent:

```powershell
python launch_stock_bn_ai.py "C:\Games\Cataclysm-BN"
```

The launcher installs the user mod, starts the companion, starts the **unmodified** BN executable with explicit `--basepath` and `--userdir`, and stops the companion when BN exits.

## Live tests

### Transport test

Action menu -> **AI bridge test**.

First invocation sends `ping`; second invocation consumes the response.

Expected:

```text
Cataclysm AI bridge test response: [ECHO:Bridge Test] ping
Cataclysm AI bridge test: SUCCESS
```

This full round trip has been confirmed in a real persistent Windows BN world.

### NPC test

Stand next to an NPC:

1. Action menu -> **AI dialogue**.
2. Select the NPC.
3. Enter `ping`.
4. After the companion publishes the response, open **AI dialogue** again and select the same NPC.

Expected:

```text
[ECHO:<NPC name>] ping
```

This real-NPC route has also been confirmed live.

## Separate user directory

```powershell
python launch_stock_bn_ai.py `
  "C:\Games\Cataclysm-BN" `
  --user-dir "C:\Games\CataclysmAI-Test-User"
```

Bright Nights requires option name/value as separate arguments; do not use `--userdir=...`.

## Automated validation

The dedicated workflow does **not build Cataclysm**.

It validates:

- `providers.py` Python syntax;
- companion Python syntax;
- launcher Python syntax;
- sidecar self-test using BN's real typed Lua-table JSON representation;
- provider output and persistent response-cache replay;
- Lua 5.3 syntax;
- installation through the stock launcher;
- loading the actual mod with the official pinned Windows BN executable;
- stock `require()` from `data/lua/lib/catai_runtime/`;
- `game.mod_storage` access;
- successful `gdebug.save_game()`.

Run the local companion self-test with:

```powershell
python sidecar\cataclysm_ai_stock_sidecar.py --self-test
```

Expected:

```text
[CataclysmAI] self-test passed
```

## Protocol v1

Outbound logical request (BN stores this in its own typed Lua serialization):

```json
{
  "protocol": 1,
  "request_id": "42_7",
  "npc_id": "42",
  "npc_name": "Old Guard",
  "player_name": "Survivor",
  "player_text": "ping",
  "current_turn": "..."
}
```

Inbound module:

```lua
return {
  protocol = 1,
  request_id = "42_7",
  ok = true,
  text = "[ECHO:Old Guard] ping"
}
```

## Next engineering layer

With transport and real NPC ECHO proven, the next work is no longer bridge research:

1. add a real model provider behind the provider interface;
2. send richer NPC/world context;
3. add external long-term NPC memory;
4. define a strict structured action schema;
5. execute only allow-listed actions through stock BN Lua bindings;
6. later use Lua NPC AI hooks for low-frequency planning/autonomy.

The remaining forced save is therefore a transport-performance limitation, not a blocker for dialogue, memory, relationships, quests, or low-frequency planning.
