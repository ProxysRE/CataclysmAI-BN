# Stock Bright Nights AI bridge prototype

This prototype is intentionally built for an **unmodified official Cataclysm: Bright Nights archive**. It does not require compiling Cataclysm-BN.

## Transport

```text
BN Lua mod
  -> gdebug.log_info("CATAI_REQ|...")
  -> config/debug.log
  -> Python sidecar
  -> mods/CataclysmAI/runtime/response_<id>.lua
  -> Lua loadfile(...)
  -> NPC response
```

The current provider is deterministic ECHO. The purpose of this branch is to prove the transport against a stock BN binary before adding an LLM provider.

## Why this works without rebuilding BN

Current BN Lua opens the standard Lua `base` library, which includes `loadfile`/`dofile`. The mod captures `game.current_mod_path`, so it can load response files written by the external sidecar directly from its own directory. Outbound requests use the existing `gdebug.log_info` binding, which writes to BN's normal debug log.

No DLL injection, binary patching, CMake, vcpkg, or custom game executable is involved.

## Files

```text
stock-bn-prototype/
  mod/CataclysmAI/
    modinfo.json
    main.lua
  sidecar/
    cataclysm_ai_stock_sidecar.py
```

The `runtime/` directory is created automatically by the sidecar.

## Manual ECHO test on Windows

1. Unpack a recent official Windows Bright Nights build.
2. Copy `mod/CataclysmAI` to `<BN>\mods\CataclysmAI`.
3. Enable `Cataclysm AI` in the world.
4. Start the companion in a terminal:

```powershell
python cataclysm_ai_stock_sidecar.py --game-dir "C:\Games\Cataclysm-BN"
```

5. Load the world and stand next to an NPC.
6. Open the in-game action menu and choose **AI dialogue**.
7. Select the adjacent NPC and enter `ping`.
8. The mod logs the request. The sidecar should print that it received the request and published `response_<id>.lua`.
9. Open **AI dialogue** again and select the same NPC. The NPC should say:

```text
[ECHO:<NPC name>] ping
```

The same invocation then opens the text input for the next line, so a conversation can continue turn by turn.

## Sidecar path overrides

If the portable layout is different, paths can be explicit:

```powershell
python cataclysm_ai_stock_sidecar.py `
  --debug-log "C:\path\to\config\debug.log" `
  --mod-dir "C:\path\to\mods\CataclysmAI"
```

## Protocol v1

Outbound log line:

```text
CATAI_REQ|1|<request_id>|<npc_id>|<npc_name>|<player_name>|<player_text>|<turn>
```

Text fields are percent-escaped for `%`, `|`, CR and LF.

Inbound file:

```lua
return {
  protocol = 1,
  request_id = "...",
  ok = true,
  text = "..."
}
```

After Lua consumes the response it logs:

```text
CATAI_ACK|1|<request_id>
```

The sidecar then removes the consumed response file.

## Next step after ECHO is proven

Do not add an LLM before the stock-binary ECHO route is confirmed. After that, replace only `make_response()` with a provider layer and expand the request context (NPC personality, faction, opinion, inventory, surroundings, memories, missions, and allowed structured actions).
