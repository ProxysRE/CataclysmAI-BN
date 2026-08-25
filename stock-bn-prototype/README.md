# Cataclysm AI on stock Bright Nights

This prototype runs against an **unmodified official Cataclysm: Bright Nights Windows build**. It does not compile, patch, inject into, or replace `cataclysm-bn-tiles.exe`.

The following milestones have been validated in a persistent Windows world:

- full stock-BN Lua -> Python -> Lua round trip;
- real adjacent NPC dialogue route;
- one-save-per-new-request transport (no ACK save);
- real NPC/player/world context v1;
- persistent per-NPC dialogue memory across a full BN/companion restart.

The current branch also contains the first real OpenAI model provider.

## Transport

```text
player types a line in BN
        |
        v
Lua captures NPC/player/world context
        |
        v
game.mod_storage["cataclysm_ai"].ipc_request
        |
        v
ONE forced gdebug.save_game() for the new outbound request
        |
        v
<BN user dir>/save/<world>/lua_state.json
        |
        v
Python decodes BN's typed Lua serialization
        |
        +--> per-NPC persistent memory
        |
        +--> provider (OpenAI when configured; memory probe otherwise)
        |
        v
response cache + persistent NPC memory
        |
        v
<BN>/data/lua/lib/catai_runtime/response_<id>.lua
        |
        v
stock BN require("lib.catai_runtime.response_<id>")
        |
        v
NPC says the returned text
```

Receiving the answer does **not** force a second game save.

## Persistent state

Long-lived companion state is stored outside the mod files:

```text
<BN user dir>/cataclysm_ai/
  npc_memory.json
  config.json          # only after local OpenAI setup
```

`npc_memory.json` is keyed by world save path plus Bright Nights' stable `npc_id`. Each NPC keeps at most 32 successful exchanges. Duplicate `request_id` values are ignored.

The short-lived response cache remains under:

```text
<BN>/data/lua/lib/catai_runtime/companion_cache.json
```

This cache makes model calls idempotent if BN or the companion exits after a response was generated but before the world naturally persisted the cleared request.

## Dialogue context v1

Lua currently supplies fields confirmed by stock BN's exported Lua API.

NPC:
- stable id and name;
- personality: aggression, bravery, collector, altruism;
- opinion of player: trust, fear, value, anger, owed;
- relationship flags: enemy, following, player ally, guarding, patrolling, travelling, hostility flags;
- pain, perceived pain, stamina, morale, hostile anger level.

Player:
- name;
- pain, perceived pain, stamina, morale.

World/dialogue:
- current turn;
- NPC danger assessment;
- current NPC target name when present.

## Real OpenAI provider

`sidecar/providers.py` now includes an OpenAI Responses API provider using only Python's standard library. No Python package installation is required.

Default model:

```text
gpt-5.6-terra
```

Override it before launch with:

```powershell
$env:CATAI_OPENAI_MODEL = "another-model-id"
```

The provider sends:
- current dialogue context v1;
- at most the last 8 exchanges with this NPC;
- the player's new line.

It instructs the model to return only natural NPC speech, stay in character, use the player's language, use relationship/personality/danger/memory as behavioral context, and avoid inventing detailed facts that are absent from game state or remembered conversation.

Responses API requests use `store: false`.

### API key setup

OpenAI API access and API billing are separate from a ChatGPT subscription. Create an API-platform key at:

```text
https://platform.openai.com/api-keys
```

The easiest Windows path is then simply to run:

```text
run_stock_bn_ai.cmd
```

On the first normal launch with no existing key, the launcher asks for the API key using hidden console input. If supplied, it stores the key locally in:

```text
<BN user dir>/cataclysm_ai/config.json
```

The key is never committed to GitHub, copied into the mod, printed in logs, or placed in process command-line arguments. The prototype config file itself contains the key locally, so protect that file like any other API credential.

If `OPENAI_API_KEY` is already set in the environment, it takes precedence and the launcher does not need to store a key.

To replace a locally saved key:

```powershell
python launch_stock_bn_ai.py "C:\Games\Cataclysm-BN" --configure-openai
```

If the prompt is left empty and no environment key exists, Cataclysm AI continues using the deterministic `[MEM:...]` provider instead of preventing BN from starting.

Never share the API key in GitHub issues, logs, screenshots, or chat messages.

## Windows launch

1. Unpack an official Windows Bright Nights archive into a writable directory.
2. Download this branch and open `stock-bn-prototype`.
3. Double-click `run_stock_bn_ai.cmd`.
4. Enter the directory containing `cataclysm-bn-tiles.exe`.
5. Configure an API key when prompted if you want real model dialogue.
6. Create/load a world with **Cataclysm AI** enabled.

The launcher installs the user mod, starts the companion, starts the **unmodified** BN executable with explicit `--basepath` and `--userdir`, and stops the companion when BN exits.

## Action menu

### AI bridge test

This remains deterministic and does not call the model, even when OpenAI is configured.

First invocation sends `ping`; second invocation consumes the response.

Expected:

```text
Cataclysm AI bridge test response: [ECHO:Bridge Test] ping
Cataclysm AI bridge test: SUCCESS
```

### AI dialogue

Stand next to an NPC:

1. Action menu -> **AI dialogue**.
2. Select the adjacent NPC.
3. Type a line.
4. One BN save publishes the request.
5. After the companion logs `published`, open **AI dialogue** again and select the same NPC.
6. The NPC says the provider response. Receiving it causes no ACK save.

With no API key this returns the diagnostic `[MEM:...]` response. With a configured key it returns model-generated NPC speech.

## Automated validation

The dedicated workflow does **not build Cataclysm**.

It validates:
- `memory.py`, provider, sidecar, launcher, and provider-selftest Python syntax;
- stock-BN typed Lua serialization decoding;
- dialogue context v1;
- persistent memory reload/deduplication;
- response cache replay;
- OpenAI request payload construction without making a network/API call;
- Responses API output-text parsing using representative JSON;
- no-key model fallback;
- Lua 5.3 syntax;
- installation through the stock launcher;
- loading the actual mod with the pinned official Windows BN executable;
- stock `require()`, `game.mod_storage`, and `gdebug.save_game()`.

Local offline tests:

```powershell
python sidecar\cataclysm_ai_stock_sidecar.py --self-test
python sidecar\provider_selftest.py
```

## Proven live examples

Transport:

```text
Cataclysm AI bridge test response: [ECHO:Bridge Test] ping
Cataclysm AI bridge test: SUCCESS
```

Context from a real NPC:

```text
[CTX:Rufus 'Badger' Tierney] trust=1 fear=-4 anger=0 value=4; aggr=3 brave=3 altruism=-5; ally=false following=false enemy=false; npc_pain=0 player_pain=0 danger=0.0 target=-
```

Persistent memory after a full restart:

```text
[MEM:Rufus 'Badger' Tierney] previous_exchanges=1; last_player=Remember: my favorite color is red
```

## Next engineering layers

After the first live model dialogue is validated:

1. enrich identity/knowledge/context (faction, role, inventory/equipment, local environment, missions where exposed);
2. memory summarization and important-event memory beyond the rolling dialogue window;
3. strict structured response schema (`speech` plus allow-listed actions);
4. validated item/trade/relationship/mission actions through stock Lua bindings;
5. low-frequency NPC planning and later autonomous `lua_ai` execution.

The remaining forced save is a transport-performance constraint, not a blocker for dialogue, memory, relationships, quests, or low-frequency planning.
