# Godco NPC interaction activity

`ACT_WAIT_NPC` now adapts to the existing BN activity, preserving static duration
and filling `str_values[0]` with the current NPC's name. BN's
`activity_handlers::wait_npc_finish` reads that slot unconditionally; assigning the
activity without it can access an empty vector when the interaction ends.

The adapter accepts static positive durations only for reviewed activity IDs
`ACT_MEASURE` and `ACT_WAIT_NPC`. The native handler enforces the same whitelist
and bounds duration before converting it to moves. NPC interaction requires a
current speaker. Existing BN rooted, interruptibility and no-resume behavior is
preserved; no replacement activity definition is loaded.

The two adapted definitions are Helena's `TALK_GODCO_Helena_Tell_FreeMerch`
and `MISSION_GODCO_HELENA_VISIT_MERCHANTS`. The complete Godco package remains staged.
Blocked definitions decrease from 65 to 63, with all 1,767 originals retained.

`ACT_GAME` remains blocked: the existing BN turn handler dereferences the target
game item, which the DDA dialogue assignment does not provide. Generic EOC and
surgery activities also remain blocked pending their actual lifecycle support.

Native regression covers 30 elapsed minutes under 300% activity progress,
alternating player move budgets, activity save/reload halfway through, retention
of the speaker name and the real completion handler. Windows validation is pending.

Sources, both pinned:

- [BN activities](https://github.com/cataclysmbn/Cataclysm-BN/blob/c621aaf42fa182473aad10feea2b55647704dcf1/data/json/player_activities.json)
- [BN wait and game handlers](https://github.com/cataclysmbn/Cataclysm-BN/blob/c621aaf42fa182473aad10feea2b55647704dcf1/src/activity_handlers.cpp)
- [DDA activities](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/data/json/player_activities.json)
- [DDA assignment effect](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/npctalk.cpp)
