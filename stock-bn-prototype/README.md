# Stock Bright Nights AI bridge prototype

This prototype targets an **unmodified official Cataclysm: Bright Nights Windows archive**. It does not compile, patch, or replace `cataclysm-bn-tiles.exe`.

The first milestone is deliberately only deterministic ECHO. A real LLM provider comes after this transport is proven in a stock game build.

## Transport

```text
player types a line in BN
        |
        v
Lua mod writes game.mod_storage["cataclysm_ai"].ipc_request
        |
        v
gdebug.save_game()
        |
        v
<BN user dir>/save/<world>/lua_state.json
        |
        v
Python companion reads the request
        |
        v
<BN>/data/lua/lib/catai_runtime/response_<id>.lua
        |
        v
Lua require("lib.catai_runtime.response_<id>")
        |
        v
NPC says the returned text
```

No DLL injection, binary patching, CMake, vcpkg, `io`, `os`, `loadfile`, or custom game executable is required.

## Why this works in stock BN

Bright Nights already provides the two mechanisms required by the bridge:

1. `game.mod_storage` is serialized by the engine during a normal save. `game::save()` writes the Lua state to the world's `lua_state.json` file.
2. BN leaves `require()` enabled and installs its own C++ Lua module searcher. `lib.*` modules are resolved from `data/lua/lib/` and loaded by the engine itself.

This matters because stock BN deliberately disables Lua `dofile`, `loadfile`, `load`, and `loadstring`; this prototype does not rely on any of them.

## Files

```text
stock-bn-prototype/
  launch_stock_bn_ai.py
  mod/CataclysmAI/
    modinfo.json
    main.lua
  sidecar/
    cataclysm_ai_stock_sidecar.py
```

The companion creates this directory automatically:

```text
<BN>/data/lua/lib/catai_runtime/
```

## Recommended Windows ECHO test

1. Unpack a recent official Windows Bright Nights archive into a writable directory.
2. From this prototype directory run:

```powershell
python launch_stock_bn_ai.py "C:\Games\Cataclysm-BN"
```

The launcher does all path-sensitive setup itself:

- locates `cataclysm-bn-tiles.exe`;
- copies `CataclysmAI` to the explicit BN user mod directory;
- verifies that `data/lua/lib/catai_runtime/` is writable;
- starts the Python companion with the same user directory;
- starts the **unmodified** stock executable with explicit `--basepath` and `--userdir` arguments;
- stops the companion when BN exits.

This removes dependence on the shell's current working directory and on BN's implicit Windows portable-path behavior.

3. Create or load a world with **Cataclysm AI** enabled.
4. Stand next to an NPC.
5. Open the in-game action menu and choose **AI dialogue**.
6. Select the adjacent NPC and enter:

```text
ping
```

7. BN performs a normal save. The companion should detect the new request in that world's `lua_state.json` and print that it published `response_<id>.lua`.
8. Open **AI dialogue** again and select the same NPC.
9. The NPC should say:

```text
[ECHO:<NPC name>] ping
```

The mod then persists an ACK so a companion restart cannot replay the consumed request.

### Separate user-data directory

If desired, keep test saves/config outside the BN archive:

```powershell
python launch_stock_bn_ai.py `
  "C:\Games\Cataclysm-BN" `
  --user-dir "C:\Games\CataclysmAI-Test-User"
```

### Install/path validation without launching BN

```powershell
python launch_stock_bn_ai.py `
  "C:\Games\Cataclysm-BN" `
  --user-dir "C:\Games\CataclysmAI-Test-User" `
  --install-only
```

The GitHub Windows stock-binary job uses this same `--install-only` path before asking the official executable to load the mod.

## Manual diagnostic launch

The launcher is preferred, but the companion can still be run directly:

```powershell
python sidecar\cataclysm_ai_stock_sidecar.py `
  --game-dir "C:\Games\Cataclysm-BN" `
  --user-dir "C:\Games\CataclysmAI-Test-User"
```

Then launch BN with matching paths:

```powershell
C:\Games\Cataclysm-BN\cataclysm-bn-tiles.exe `
  --basepath="C:\Games\Cataclysm-BN" `
  --userdir="C:\Games\CataclysmAI-Test-User"
```

Or provide the companion directories directly:

```powershell
python sidecar\cataclysm_ai_stock_sidecar.py `
  --save-root "C:\Games\CataclysmAI-Test-User\save" `
  --response-dir "C:\Games\Cataclysm-BN\data\lua\lib\catai_runtime"
```

The stock executable also supports `--paths`, which can print its resolved user/config/data paths if a package uses an unusual layout.

## Automated validation against an official executable

The dedicated workflow does **not build Cataclysm**.

It has two layers:

1. Python/Lua protocol checks: Python compilation, companion self-test, and Lua 5.3 syntax.
2. Stock Windows load test: download the official Bright Nights `2026-08-24` MSVC nightly archive, install the mod through `launch_stock_bn_ai.py --install-only`, inject a CI-only `require()` probe, and run the shipped `cataclysm-bn-tiles.exe --check-mods cataclysm_ai`.

The nightly is pinned deliberately so changes in upstream releases cannot silently change what a given commit was validated against.

## Companion self-test

This test does not launch BN. It validates JSON request parsing, request IDs, ECHO generation, Lua response escaping, and ACK parsing:

```powershell
python sidecar\cataclysm_ai_stock_sidecar.py --self-test
```

Expected:

```text
[CataclysmAI] self-test passed
```

## Protocol v1

Outbound request stored in `lua_state.json`:

```json
{
  "cataclysm_ai": {
    "ipc_request": {
      "protocol": 1,
      "request_id": "42_7",
      "npc_id": "42",
      "npc_name": "Old Guard",
      "player_name": "Survivor",
      "player_text": "ping",
      "current_turn": "..."
    }
  }
}
```

Inbound response module:

```lua
return {
  protocol = 1,
  request_id = "42_7",
  ok = true,
  text = "[ECHO:Old Guard] ping"
}
```

After consumption Lua clears `ipc_request`, writes `ipc_ack`, and saves again.

## Important prototype limitation

The outbound path currently calls a **normal game save for each external AI request**, and another save when the response is acknowledged. This is acceptable for proving a stock-binary bridge, but it is not the final transport for high-frequency autonomous NPC AI.

If ECHO works, the next engineering decision is measured rather than speculative:

- keep save/require IPC for low-frequency dialogue and planning if save latency is acceptable; or
- replace only the transport with a tiny runtime bridge/injected helper while keeping the official BN executable and all Lua gameplay logic.

Either route avoids rebuilding Cataclysm itself.

## After ECHO

Only after the stock-binary ECHO route is confirmed:

1. replace `make_response()` with a provider abstraction (`EchoProvider`, later LLM provider);
2. send richer NPC/world context;
3. add external long-term memory;
4. define a strict structured action schema;
5. execute only allow-listed actions through existing BN Lua bindings;
6. test Lua-driven NPC planning (`game.npc_ai_functions`) at a deliberately low request cadence.
