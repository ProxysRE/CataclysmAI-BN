# Shared relationship and duration compatibility

The bulk compiler now supports `n_npc_anger()`, `n_npc_fear()`,
`n_npc_trust()` and `n_npc_value()` reads, assignments, `+=`/`-=`, and
increments/decrements. They map to the speaker's real BN `op_of_u` fields,
not similarly named `npctalk_var_` strings. The expression bridge rejects a
missing/non-NPC speaker. Assignment rejects nonfinite/out-of-range numbers
before converting to BN's integer fields; ordinary fractions truncate toward
zero as with DDA's integer setters.

Reference: pinned DDA `src/math_parser_diag.cpp` (`npc_*_eval` and `npc_*_ass`)
and `src/talker_npc.cpp` (`get_npc_*` / `set_npc_*`), commit
`c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`. BN's corresponding fields are in
the pinned `npc_opinion` structure. The new IR leaf is
`{"op":"npc_opinion","name":"anger"}`; the new assignment effect is
`dda_set_npc_opinion` with `target` and `expression` members.

Duration literals accept full second/minute/hour/day/week units (singular and
plural), in addition to the existing s/m/h/d abbreviations. These compile to
seconds, including the Hub's 14-day and 44-day waits. Invalid units, arguments
and keywords remain errors. Global variables, time-since-cataclysm, arbitrary
math functions and EOC lifecycle support are not implicitly enabled.

On the unchanged 1,647-definition source batch, blocked definitions decrease
from 185 to 125 (Godco 74 to 23, Hub 01 92 to 85, chemist 8 to 7, scrap trader
3 to 2). This measures complete-definition conversion, not playable content.
Converted staging remains outside the native package.

Local compiler/regression checks, standalone C++ expression checks and patch
application pass. A native Windows regression was added for real opinion
thresholds, increment effects, field isolation, missing actors, fractional
conversion and range rejection. Windows execution is pending for this change.
