# Cataclysm AI NPC — Project Roadmap

> **Start here in a new chat.** Before making code changes, read this document and then check the current GitHub PR / Actions status. This file is the project-level design contract for the Mantella-like AI NPC system for **Cataclysm: Bright Nights**.

## 1. Project goal

Build a **text-only Mantella-like AI interaction layer for NPCs in Cataclysm: Bright Nights**.

The player should be able to speak to an NPC in free-form text. Bright Nights provides the relevant game state, an external sidecar talks to an LLM, and the NPC responds inside the normal game dialogue flow.

This project deliberately does **not** target microphone input, speech-to-text, text-to-speech, or real-time voice interaction. Bright Nights is turn-based, so the intended interaction is textual.

The AI layer should augment vanilla NPC systems rather than replace them wholesale. Vanilla code remains authoritative for trading, missions, inventory, movement, combat, faction rules, relationship values, and other game mechanics.

## 2. Core architecture

Target data path:

```text
Bright Nights dialogue
    -> Lua mod / dialogue hook
    -> C++ Lua binding: cataclysm_ai.exchange(request, timeout_ms)
    -> file IPC under the BN config directory
    -> external Python sidecar
    -> LLM provider
    -> structured response
    -> Python sidecar
    -> C++ bridge
    -> Lua
    -> NPC dialogue / approved vanilla action
```

### Current bridge contract

```lua
cataclysm_ai.exchange(request, timeout_ms)
```

The C++ bridge publishes a UTF-8 request file, waits synchronously for a UTF-8 response file, returns the response to Lua, and handles bounded timeouts and size limits.

The file-IPC approach is intentional for the first implementation:

- no direct HTTP/network access from the Lua sandbox;
- no new network dependency inside Bright Nights;
- simple to debug independently from the LLM provider;
- sidecar can later change providers without changing the game-side bridge.

## 3. Non-negotiable design rule

**The LLM may propose an intent, but it must never directly mutate the game world.**

Bad design:

```text
LLM -> give_item("rifle") -> item appears
```

Required design:

```text
LLM -> intent: GIVE_ITEM
    -> Bright Nights validates NPC ownership, permissions, game state and rules
    -> vanilla / trusted game code performs the action or rejects it
```

The same rule applies to relationship changes, missions, movement, inventory, combat, faction state, map state, spawning, rewards, and any other mechanical effect.

## 4. Development rule

Work one verified layer at a time.

Do not mix bridge changes, dialogue integration, Python, LLM calls, packaging, and gameplay actions into one untestable step.

Preferred progression:

```text
pristine BN baseline
-> minimal Lua API bridge
-> Lua/C++ runtime round-trip test
-> Python ECHO sidecar
-> free-form dialogue UI
-> real LLM
-> NPC/world context
-> memory
-> validated gameplay intents
-> advanced social / autonomous systems
```

Each layer should have its own automated proof before the next layer is considered complete.

## 5. Current confirmed technical baseline

Pinned upstream baseline used by the CI work at the time this document was created:

```text
cataclysmbn/Cataclysm-BN
commit: 17a0df280e6d009402bcc41ffafbce12670c4b99
```

Confirmed milestones before the Python-sidecar stage:

1. A pristine Windows Bright Nights build succeeded under GitHub Actions.
2. A dedicated C++ Lua binding for `cataclysm_ai.exchange()` compiled and linked successfully into `cataclysm-bn-tiles.exe`.
3. An automated Lua runtime test successfully completed the round trip:

```text
Lua -> C++ bridge -> file IPC -> responder -> file IPC -> C++ bridge -> Lua
PING -> PONG
```

The next active milestone is the same round trip through a **real external Python ECHO sidecar**.

## 6. Functional roadmap by difficulty

### A. Playable prototype — LOW difficulty

#### A1. Free-form NPC dialogue

Add a vanilla-compatible dialogue option similar to:

```text
[AI] Say something in your own words
```

Flow:

```text
player text
-> Lua
-> bridge
-> Python sidecar
-> LLM
-> NPC reply
```

Vanilla dialogue options remain available.

**Difficulty:** Low once the bridge and sidecar are stable.

#### A2. Minimal NPC identity context

Send the LLM basic information such as:

- NPC name;
- sex / gender data available in BN;
- faction;
- NPC class / role;
- current relationship / opinion values;
- current player utterance;
- recent turns of the current conversation.

**Difficulty:** Low.

### B. Believable NPC — LOW to MEDIUM difficulty

#### B1. Stable NPC personality

Derive or persist personality traits from BN data and procedural additions:

- aggression;
- bravery;
- altruism;
- collector tendency;
- faction / role;
- speech style;
- temperament;
- values;
- fears;
- attitude to violence;
- attitude to the player.

The objective is to prevent every NPC from sounding like the same generic assistant.

**Difficulty:** Low–Medium.

#### B2. Persistent conversation memory

Give each NPC a stable identity key and persist:

- recent conversation history;
- important facts;
- promises;
- insults;
- favors;
- relationship-relevant events;
- compact long-term summaries.

Do not continuously resend the full lifetime chat log. Maintain recent context plus summarized long-term memory.

**Difficulty:** Medium.

#### B3. Local world context

Provide selected current information:

- date and time;
- weather;
- local terrain / location type;
- NPC health and condition;
- visible equipment;
- nearby danger;
- nearby creatures / characters where appropriate;
- selected recent events.

**Difficulty:** Medium. The challenge is extracting and compressing useful game state rather than calling the model.

### C. Knowledge and consequences — MEDIUM to HIGH difficulty

#### C1. NPC knowledge boundary

Separate **what exists in the game** from **what this NPC actually knows**.

Possible knowledge sources:

- own faction;
- own missions;
- personally visited locations;
- witnessed events;
- known people;
- rumors;
- player-provided information.

Do not expose omniscient world state to the LLM by default.

**Difficulty:** Medium–High, mostly because of game design and state modeling.

#### C2. AI conversation affects relationships

The LLM may classify social consequences, for example:

```json
{
  "tone": "hostile",
  "trust_delta": -2,
  "fear_delta": 1
}
```

Bright Nights clamps and validates all changes before applying them.

Potential effects:

- trust;
- fear;
- anger;
- respect / value if available in the underlying NPC model;
- willingness to cooperate.

**Difficulty:** Medium–High.

### D. Natural-language frontend to vanilla gameplay — HIGH difficulty

#### D1. Safe NPC commands

Examples:

```text
Wait here.
Follow me.
Guard this place.
Stop following me.
Take this weapon.
Give me the bandages.
```

Model output should be structured, for example:

```json
{
  "reply": "All right. I'll wait here.",
  "intent": {
    "type": "guard_position"
  }
}
```

The game validates the request and maps it to trusted vanilla behavior.

**Difficulty:** High because a safe, explicit action API is required.

#### D2. Natural-language trading

Examples:

```text
Do you have any 9 mm ammunition?
Show me what you have for sale.
I'd trade this rifle for food.
```

The LLM understands the intent, but the normal BN trading system controls prices, inventories, ownership and the actual transfer.

**Difficulty:** High.

#### D3. Natural-language mission interface

Examples:

```text
Do you need anything done?
I brought the medicine you wanted.
What was I supposed to find for you?
```

The LLM identifies the intent. Vanilla mission code determines available missions, verifies completion and awards rewards.

**Difficulty:** High.

### E. Deep social awareness — HIGH difficulty

#### E1. Several NPCs in one conversation

Support nearby participants, addressee selection, interruptions, and responses based on:

- distance;
- who can hear whom;
- relationships between NPCs;
- who was addressed;
- conversation history.

**Difficulty:** High.

#### E2. Memory of gameplay events outside dialogue

Create an event stream for selected meaningful events, for example:

```text
PLAYER_KILLED_CREATURE
PLAYER_HURT_NPC
PLAYER_HEALED_NPC
PLAYER_GAVE_ITEM
NPC_SAW_THEFT
NPC_SAW_MURDER
PLAYER_SAVED_NPC
NPC_ALLY_DIED
```

Relevant witnesses can convert these events into persistent memories and later mention them in dialogue.

**Difficulty:** High.

### F. Experimental endgame systems — VERY HIGH / EXTREME difficulty

These should be attempted only after the ordinary dialogue system, memory, context and safe gameplay intents are stable and polished.

#### F1. Autonomous NPC goals and planning

NPCs form their own goals and attempt plans such as obtaining medicine, avoiding a dangerous player, relocating, or requesting help.

Requires:

- persistent goals;
- plan state;
- risk evaluation;
- failure / retry handling;
- integration with trusted game actions.

**Difficulty:** Very High.

#### F2. AI-generated missions

NPCs may formulate new missions using strictly validated templates.

Do not allow the LLM to invent arbitrary item IDs, monster IDs, map coordinates or rewards and directly inject them into the world.

Recommended implementation is a bounded library of mission templates whose parameters are selected and validated by game code.

**Difficulty:** Very High.

#### F3. Autonomous social simulation

Long-term possible scope:

- NPC-to-NPC conversations without the player;
- rumors spreading;
- evolving interpersonal relationships;
- social conflicts;
- shared memories and witnessed events;
- autonomous decisions based on social information.

This has serious token-cost, performance, persistence and debugging implications.

**Difficulty:** Extreme. Last-stage experiment only.

## 7. Recommended release sequence

### Stage A — Playable prototype

Goal: free-form one-on-one conversation works reliably.

Required:

- Python sidecar;
- free text input;
- NPC text output;
- minimal identity context;
- robust error / timeout handling.

### Stage B — Believable NPC

Goal: conversations feel character-specific and continuous.

Add:

- personality;
- persistent memory;
- local context;
- stable NPC identity.

### Stage C — Knowledge and social consequences

Goal: NPCs know only what they should know and conversation matters mechanically.

Add:

- knowledge boundary;
- validated relationship effects;
- better context filtering.

### Stage D — Natural-language gameplay interface

Goal: free-form speech can invoke safe vanilla systems.

Add progressively:

- wait / follow / guard and other narrow commands;
- trade intent;
- vanilla mission intent;
- selected inventory interactions.

### Stage E — Deep memory and social interaction

Goal: NPCs react to events and multiple characters can participate coherently.

Add:

- witnessed-event memory;
- several-NPC conversations;
- rumors / shared social facts if practical.

### Stage F — Experimental autonomy

Only after all earlier stages are stable:

- autonomous plans;
- bounded generated missions;
- autonomous social simulation.

## 8. What should be implemented early vs late

### Implement early

- file IPC bridge;
- Python sidecar;
- ECHO round-trip;
- free-form dialogue input/output;
- LLM provider abstraction;
- NPC identity context;
- short conversation context;
- simple persistent memory;
- clear timeout/error fallback;
- logs useful for debugging.

### Implement after the core is pleasant to use

- richer personality;
- local world context;
- knowledge filtering;
- relationship consequences;
- a small whitelist of gameplay intents.

### Implement late

- complex inventory commands;
- natural-language trading edge cases;
- mission integration;
- multi-NPC conversations;
- event/witness memory.

### Implement last, if at all

- autonomous planning;
- generated missions;
- continuous NPC-to-NPC social simulation.

## 9. Safety / robustness rules for the implementation

1. **No arbitrary code or command execution from LLM output.**
2. **No direct game-state mutation from LLM output.**
3. Parse responses through a strict schema whenever an action is requested.
4. Unknown or invalid intents degrade to dialogue-only output.
5. All numerical deltas are bounded by game-side limits.
6. All item, monster, mission, faction and location identifiers are resolved by trusted game code.
7. Timeouts must return control to the player cleanly.
8. Sidecar failure must not corrupt saves or block normal vanilla dialogue permanently.
9. Vanilla dialogue remains available as a fallback.
10. Keep logs sufficient to reproduce sidecar, parsing and intent failures.

## 10. Testing gates

A feature is not considered complete merely because it compiles.

Preferred proof levels:

1. **Compile proof** — source builds and links.
2. **Runtime API proof** — Lua can call the API in an actual BN Lua state.
3. **Round-trip proof** — request leaves BN and a response returns.
4. **Integration proof** — the real dialogue flow displays the result.
5. **Persistence proof** — save/reload keeps required memory/state.
6. **Failure proof** — sidecar absent, timeout, malformed response and provider errors fail gracefully.
7. **Gameplay proof** — any action intent is validated and cannot bypass vanilla rules.

## 11. Immediate next milestones

At the time of writing, the project is moving through these gates:

```text
[done] pristine Windows BN build
[done] minimal cataclysm_ai.exchange() C++/Lua binding
[done] Lua runtime PING -> PONG round-trip using file IPC
[in progress] external Python ECHO sidecar round-trip
[next] free-form text input inside a real NPC dialogue
[next] ECHO reply shown as the NPC's actual dialogue response
[next] replace ECHO responder with an LLM provider
[next] add minimal NPC identity/context
```

Do not skip directly to autonomous NPC systems before these milestones are stable.

## 12. CI / build policy

The known-good build path is GitHub Actions on Windows/MSVC using a pinned pristine Bright Nights checkout.

For development, prefer hosted CI and ready artifacts instead of requiring repeated local Bright Nights compilation.

Packaging is secondary to functional proof. A modified executable that compiles, launches and passes runtime integration tests is more important than a polished distribution archive during early development.

## 13. Definition of the intended mature system

A mature version should let the player naturally say things such as:

```text
Who are you?
What happened here?
Do you remember me?
Do you know where the hospital is?
Do you have any ammunition to trade?
Wait here until I come back.
I brought the medicine you asked for.
Why are you angry with me?
```

The NPC should answer according to its identity, knowledge, memory, relationship and present situation. When the utterance implies a mechanical action, Bright Nights should validate and execute that action through trusted game systems.

That is the target: **natural language as an additional interface to a persistent, game-aware NPC — not an omnipotent LLM controlling the simulation directly.**
