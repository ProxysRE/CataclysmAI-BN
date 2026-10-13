# Lighthouse community checkpoint

Pinned official DDA sources and original IDs are preserved. Four NPCs, 26 dialogue definitions and seven missions include the lighthouse family, associated survivor, floor-cleaning sequence, family rescue and lighthouse repair. Duplicate topic IDs and shared BN topics require additive merging, not wholesale replacement.

Sources now also include both lighthouse maps, island special layouts, all 13 terrain IDs, their abstract parent, camp update maps and two camp recipes. The selected abstract is stored separately; SOURCE_MANIFEST identifies its original upstream file. Run prepare_lighthouse.py and check_lighthouse_links.py to reproduce staging and static link checks.

All thirteen terrain IDs have matching mapgen definitions, placement coordinates are unique, and referenced update mapgen IDs resolve within the checkpoint. External mission target house_04_basement remains an explicit dependency for native verification.

The native bridge handles all 23 arithmetic expressions, including NPC-scoped counters and timers. A dedicated mission-goal-context regression checks the cleanup count belongs to the NPC rather than the player. Earlier timer regression passed Windows validation; the new goal regression is pending.

This is not an installable package. Full native mission start/end and map generation tests, BN terrain inheritance and safety flags, safe-space/NPC-location conditions, common-dialogue merging, item/trait closure and the camp engine remain unresolved release gates.
