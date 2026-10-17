# Authorized autonomous work

User reaffirmed autonomous continuation on 2026-10-17. Repeated "continue" messages are not required to choose the next step within an active work session.

- Continue DDA NPCs, missions, related dependencies and standalone locations in coherent batches. Expand existing BN sites instead of adding duplicates.
- Reuse BN mechanisms. Record intentional semantic adaptations and block unsupported behavior rather than silently pretending it works.
- Persist code and reports to the existing port/dda-npc-locations branch. Keep highway work separate until integration is explicitly prepared and validated.
- Inspect CI failures, fix them, and continue independent work while Windows builds run. Passing static checks is not a playable-port claim.
- Request user input only for a material unresolved product choice, missing user data, or an actual blocker outside existing authorization.
- Work across several useful steps before reporting completion; avoid returning after a tiny audit when implementation can continue.
- A completed assistant turn does not leave an autonomous coding worker running. GitHub jobs already started continue independently.

The user accepted all confirmed missing/partial location groups as transfer goals on 2026-10-17. Follow location_catalog/PORT_TARGETS.json and PORT_ROADMAP.md; associated NPCs, quests and required dependencies are included. Keep the three renamed-layout review groups under investigation.

## BN currency reuse (user instruction, 2026-10-17)

Use stock BN money items for imported cash loot. The pinned BN definition `money_bundle` in `data/json/items/generic.json` is a bundle of twenty-dollar bills (250 ml, 20 g); `money_pile` is a separate, much larger item. Do not introduce DDA denominations, coin collections, `banknotes`/`coins` groups or a global monetary expansion. Map ordinary cash loot to `money_bundle` with container-safe quantities; preserve the original BN item, value, flags and distribution elsewhere. Upstream DDA currency files may remain archived as source references only.
