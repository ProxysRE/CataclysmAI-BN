# Cataclysm AI NPC — Project Roadmap

> **Start here in a new chat.** Before making code changes, read this document and then check the current GitHub PR / Actions status. This file is the project-level design contract for the Mantella-like AI NPC system for **Cataclysm: Bright Nights**.

## 1. Project goal

Build a **text-only Mantella-like AI interaction layer for NPCs in Cataclysm: Bright Nights**.

The player should be able to speak to an NPC in free-form text. Bright Nights provides the relevant game state, an external sidecar talks to an LLM, and the NPC responds inside the normal game dialogue flow.

This project deliberately does **not** target microphone input, speech-to-text, text-to-speech, or real-time voice interaction. Bright Nights is turn-based, so the intended interaction is textual.

The AI layer should augment vanilla NPC systems rather than replace them wholesale. Vanilla code remains authoritative for trading, missions, inventory, movement, combat, faction rules, relationship values, map state and other game mechanics.

A major long-term goal is that AI dialogue should be grounded in the **actual persistent world of the current save**. NPCs should be able to have biographies tied to real generated cities, buildings, roads and landmarks rather than hallucinated geography.

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

**The LLM may propose an intent or narrative interpretation, but it must never directly mutate the game world.**

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

The same rule applies to relationship changes, missions, movement, inventory, combat, faction state, map state, spawning, rewards, map markers and any other mechanical effect.

For biographies, the same principle applies in reverse: trusted game code supplies real world facts first; the LLM may turn those facts into prose, but it may not silently invent persistent locations or physical objects and treat them as already real.

## 4. Development rule

Work one verified layer at a time.

Do not mix bridge changes, dialogue integration, Python, LLM calls, packaging, gameplay actions and world-generation changes into one untestable step.

Preferred progression:

```text
pristine BN baseline
-> minimal Lua API bridge
-> Lua/C++ runtime round-trip test
-> Python ECHO sidecar
-> free-form dialogue UI
-> real LLM
-> NPC/world context
-> world-grounded biography
-> memory
-> knowledge boundary
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

#### B2. Local world context

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

#### B3. World-grounded biography

Generate an NPC's backstory from **real persistent overmap facts** instead of letting the LLM invent arbitrary geography.

Bright Nights already maintains overmap-level information for generated parts of the world, including city records, overmap terrain, roads, building/location types and major landmarks. Detailed local mapgen, loot, many spawns and map extras may happen later when an overmap terrain tile is actually generated as a local map.

The biography system should therefore use a trusted game-side **biography seed**.

Example seed:

```text
NPC: Boris
Age: 37
Profession: mechanic

Origin city: New Franklin
Former home: house at OMT (548, 322, 0)
Nearby landmark: fire station across the road
Nearby workplace candidate: garage 6 OMT north-west
```

The LLM may then turn this into natural prose such as:

```text
I'm from New Franklin. I lived almost opposite the fire station,
across the road. Before the Cataclysm I worked at a garage nearby.
```

The important property is that **New Franklin, the house, the fire station and the garage are real locations in that save**.

##### B3.1 Persist structured biography facts

Do not store only prose. Persist canonical references where possible:

```json
{
  "origin_city": "New Franklin",
  "home_omt": [548, 322, 0],
  "work_omt": [542, 316, 0],
  "landmarks": [
    {
      "type": "fire_station",
      "omt": [550, 322, 0]
    }
  ]
}
```

This allows later systems to use the same facts for dialogue, map markers, knowledge, missions and memories without asking the model to reconstruct coordinates from prose.

##### B3.2 Three truth levels

The biography system must explicitly distinguish:

**Hard world facts** — supplied by trusted BN state and safe to state as facts:

- city name, position and size;
- real overmap terrain / building type;
- roads;
- nearby landmarks;
- directions and distances;
- major overmap specials that already exist.

**Generated biography facts** — invented by the LLM but constrained not to contradict hard facts:

- the NPC lived there with a spouse;
- the NPC worked at the nearby garage;
- personal relationships;
- habits, memories, opinions and ordinary life history.

**Unresolved physical facts** — details that must not be asserted as persistent reality before the relevant local map exists, unless a later trusted system commits them:

- exact room layout;
- a specific object under a specific bed;
- a particular weapon in a basement;
- exact furniture placement;
- exact corpse / loot / monster presence.

Early versions should simply forbid or soften unresolved physical claims.

##### B3.3 Lazy initialization

Do **not** call an LLM for every generated NPC immediately.

Recommended flow:

```text
NPC exists normally in BN
-> first meaningful AI interaction
-> no biography record exists
-> trusted code selects / validates origin city, home, work candidate and landmarks
-> sidecar asks LLM to turn the seed into a biography
-> structured seed + generated biography are saved permanently for that NPC ID
```

A cheap deterministic geographic seed may be assigned before the first LLM call if that improves stability.

##### B3.4 Population plausibility

The nearest city should not automatically become every NPC's hometown.

Origin selection can later account for:

- local residents;
- nearby-city migrants;
- more distant refugees;
- faction context;
- profession;
- plausible residential terrain;
- plausible workplace terrain.

Profession should influence probabilities without becoming a hard rule. A mechanic may plausibly work near a garage, a doctor near a clinic or hospital, and a firefighter near a fire station, while home and workplace remain separate locations.

##### B3.5 Later gameplay use

Once structured biography locations exist, later stages may safely support utterances such as:

```text
Where did you live?
Can you show me your house on the map?
Where did you work?
Do you know a pharmacy in your old town?
```

A future trusted intent may add a map marker such as `Boris's former home` using the stored OMT coordinate.

The biography becomes part of the NPC's initial knowledge and long-term memory rather than a decorative paragraph.

**Difficulty:** Medium for the first version; Medium–High for profession-aware migration, robust knowledge integration and map-marker/gameplay use.

#### B4. Persistent conversation memory

Give each NPC a stable identity key and persist:

- recent conversation history;
- important facts;
- promises;
- insults;
- favors;
- relationship-relevant events;
- compact long-term summaries;
- the canonical world-grounded biography seed and important biography facts.

Do not continuously resend the full lifetime chat log. Maintain recent context plus summarized long-term memory.

**Difficulty:** Medium.

### C. Knowledge and consequences — MEDIUM to HIGH difficulty

#### C1. NPC knowledge boundary

Separate **what exists in the game** from **what this NPC actually knows**.

Possible knowledge sources:

- own biography and origin locations;
- own faction;
- own missions;
- personally visited locations;
- witnessed events;
- known people;
- rumors;
- player-provided information.

Do not expose omniscient world state to the LLM by default. A world-grounded biography may give an NPC knowledge of its home town and associated landmarks without giving it knowledge of every generated location in the save.

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

#### D4. Biography-aware location intents

Use validated structured biography references for safe interactions such as:

```text
Show me where your old house was.
Mark your workplace on my map.
Which road leads toward your home town?
```

The LLM identifies the requested location; trusted game code resolves the stored reference and decides whether the NPC knows enough to reveal it and whether a map marker may be added.

**Difficulty:** High, but significantly safer than allowing free-form coordinates from model output.

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

These should be attempted only after the ordinary dialogue system, memory, context, world-grounded biography and safe gameplay intents are stable and polished.

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

World-grounded biography can supply validated mission locations. For example, an NPC may ask the player to return to its real former home or workplace, but mission creation must still use trusted templates and validated coordinates.

**Difficulty:** Very High.

#### F3. Narrative-backed future mapgen

Very late experiment: allow selected unresolved biography details to become real when an ungenerated local map is eventually generated.

Example:

```text
NPC says: "I hid a family photograph under my bed."
-> system stores a validated persistent narrative detail tied to home_omt
-> when that OMT is first locally generated, a trusted mapgen hook attempts to realize the detail
-> if placement is impossible, the game uses a deterministic fallback or marks the detail unresolved
```

This must never work by executing arbitrary LLM instructions. It requires a small whitelist of supported persistent detail templates such as a named keepsake, cache, note or other bounded object placement.

This feature is intentionally deferred because local mapgen may not yet exist when the biography is written, and consistency across save/load, mapgen variants and failures is difficult.

**Difficulty:** Very High / Extreme.

#### F4. Autonomous social simulation

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

Goal: conversations feel character-specific, continuous and grounded in the actual save.

Add:

- personality;
- local context;
- world-grounded biography;
- persistent memory;
- stable NPC identity.

The first biography implementation should stop at existing overmap facts and generated prose. It should not modify future local mapgen.

### Stage C — Knowledge and social consequences

Goal: NPCs know only what they should know and conversation matters mechanically.

Add:

- knowledge boundary;
- biography facts as part of personal knowledge;
- validated relationship effects;
- better context filtering.

### Stage D — Natural-language gameplay interface

Goal: free-form speech can invoke safe vanilla systems.

Add progressively:

- wait / follow / guard and other narrow commands;
- trade intent;
- vanilla mission intent;
- selected inventory interactions;
- biography-aware map/location intents.

### Stage E — Deep memory and social interaction

Goal: NPCs react to events and multiple characters can participate coherently.

Add:

- witnessed-event memory;
- several-NPC conversations;
- rumors / shared social facts if practical.

### Stage F — Experimental autonomy and narrative world realization

Only after all earlier stages are stable:

- autonomous plans;
- bounded generated missions;
- selected narrative-backed future mapgen;
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
- world-grounded biography using existing overmap facts;
- persistent structured biography references;
- knowledge filtering;
- relationship consequences;
- a small whitelist of gameplay intents.

### Implement late

- complex inventory commands;
- natural-language trading edge cases;
- mission integration;
- biography-aware map markers and location actions;
- multi-NPC conversations;
- event/witness memory.

### Implement last, if at all

- autonomous planning;
- generated missions;
- narrative-backed future mapgen;
- continuous NPC-to-NPC social simulation.

## 9. Safety / robustness rules for the implementation

1. **No arbitrary code or command execution from LLM output.**
2. **No direct game-state mutation from LLM output.**
3. Parse responses through a strict schema whenever an action is requested.
4. Unknown or invalid intents degrade to dialogue-only output.
5. All numerical deltas are bounded by game-side limits.
6. All item, monster, mission, faction and location identifiers are resolved by trusted game code.
7. Biography coordinates and landmark identities originate from trusted world-state extraction, not free-form LLM output.
8. Distinguish hard world facts, generated biography facts and unresolved physical facts.
9. Timeouts must return control to the player cleanly.
10. Sidecar failure must not corrupt saves or block normal vanilla dialogue permanently.
11. Vanilla dialogue remains available as a fallback.
12. Keep logs sufficient to reproduce sidecar, parsing, intent, biography and world-reference failures.

## 10. Testing gates

A feature is not considered complete merely because it compiles.

Preferred proof levels:

1. **Compile proof** — source builds and links.
2. **Runtime API proof** — Lua can call the API in an actual BN Lua state.
3. **Round-trip proof** — request leaves BN and a response returns.
4. **Integration proof** — the real dialogue flow displays the result.
5. **Persistence proof** — save/reload keeps required memory/state.
6. **World-grounding proof** — biography references resolve to the same real city/building/landmark after save/reload.
7. **Knowledge proof** — NPC does not gain unrelated omniscient map knowledge from biography extraction.
8. **Failure proof** — sidecar absent, timeout, malformed response and provider errors fail gracefully.
9. **Gameplay proof** — any action intent is validated and cannot bypass vanilla rules.
10. **Future-mapgen proof** — required only if Stage F narrative-backed mapgen is ever implemented; persistent narrative details survive generation variants and fail safely.

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
[next] add local world context
[next] prototype world-grounded biography seed from real overmap data
```

Do not skip directly to autonomous NPC systems or narrative mapgen before these milestones are stable.

## 12. CI / build policy

The known-good build path is GitHub Actions on Windows/MSVC using a pinned pristine Bright Nights checkout.

For development, prefer hosted CI and ready artifacts instead of requiring repeated local Bright Nights compilation.

Packaging is secondary to functional proof. A modified executable that compiles, launches and passes runtime integration tests is more important than a polished distribution archive during early development.

## 13. World-grounded biography architecture notes

This section is the reference for future implementation work on biographies.

### 13.1 What the game knows before local mapgen

The overmap layer can already hold persistent macro geography for generated overmaps: cities, their names and positions, overmap terrain, roads and building/location terrain types. Local mapgen later resolves an OMT into detailed map squares, furniture, items, many spawns and map extras.

Therefore biography generation should preferentially query **existing overmaps**. It may deliberately generate additional overmaps only when a design decision explicitly calls for that; it should not casually expand the world merely to create an NPC biography.

### 13.2 Canonical biography record

A future implementation should keep a structured sidecar/game record similar to:

```json
{
  "npc_id": "...",
  "origin": {
    "city_name": "New Franklin",
    "city_center_omt": [542, 318, 0],
    "home_omt": [548, 322, 0],
    "work_omt": [542, 316, 0]
  },
  "known_landmarks": [
    {
      "terrain": "fire_station",
      "omt": [550, 322, 0],
      "relation": "across the road from former home"
    }
  ],
  "generated_summary": "...",
  "schema_version": 1
}
```

Exact field names are not yet frozen. Coordinates and terrain IDs must remain machine-readable even when a localized human-readable description is also stored.

### 13.3 Determinism and identity

Once assigned, origin/home/work references must not be rerolled merely because the player starts another conversation. The record belongs to the stable NPC identity and survives save/reload.

If an referenced overmap terrain later changes because gameplay destroys or transforms the location, the biography remains historical truth: the NPC **used to live there**. Current-world context may separately describe what is there now.

### 13.4 LLM prompt rule

The prompt should clearly separate:

```text
CANONICAL WORLD FACTS
CANONICAL NPC FACTS
ALLOWED CREATIVE GAPS
UNKNOWN / DO NOT ASSERT AS FACT
```

The model may narrativize the first two and creatively fill the third, but must not convert the fourth into canonical persistent facts.

### 13.5 Relationship with future missions

Biography is not itself a mission generator. It supplies validated locations that later mission templates may use.

Example future chain:

```text
NPC has home_omt
-> player asks about family belongings
-> LLM proposes intent / narrative hook
-> game selects an allowed retrieve-keepsake mission template
-> trusted code validates home_omt and mission parameters
-> mission system creates the objective
```

This preserves the project rule that the LLM proposes meaning while the game owns mechanics.

## 14. Definition of the intended mature system

A mature version should let the player naturally say things such as:

```text
Who are you?
Where did you live before the Cataclysm?
What was near your house?
Can you show me your old home on the map?
What happened here?
Do you remember me?
Do you know where the hospital is?
Do you have any ammunition to trade?
Wait here until I come back.
I brought the medicine you asked for.
Why are you angry with me?
```

The NPC should answer according to its identity, knowledge, memory, relationship, biography and present situation. Geographic claims derived from its biography should correspond to the actual persistent world of the current save. When the utterance implies a mechanical action, Bright Nights should validate and execute that action through trusted game systems.

That is the target: **natural language as an additional interface to a persistent, game-aware NPC whose personal history belongs to the actual procedural world — not an omnipotent LLM controlling or inventing the simulation directly.**
