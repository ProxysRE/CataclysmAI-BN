# Use of BN mechanisms in the DDA port

The port reuses the pinned BN implementation where behavior matches. The
compatibility layer translates source data and extends missing behavior; prepared
data is kept separate from the installed native payload.

| Area | Existing BN implementation used | Added code and reason |
|---|---|---|
| NPC interaction | `ACT_WAIT_NPC`, ordinary `assign_activity`, calendar-duration progress, save/load, finish handler | Adapter fills required speaker-name slot; duration and activity whitelist prevent unsupported assignments |
| Faction trust | `faction_manager`, real `trusts_u`, existing faction serialization | Named-faction expression/effect syntax needed by DDA; preserves the explicitly named target |
| NPC opinion | Real `op_of_u` integer fields and ordinary NPC saves | Expression access for DDA syntax; no replacement opinion variables |
| Variables | Existing Character string storage and `u_add_var`/`u_has_var` when appropriate | Fraction-preserving arithmetic because stock adjustments/comparisons use integer conversion; world variables require new world-scoped storage |
| Conditions | BN `conditional_t<dialogue>` and normal condition handlers | Additional expression/location predicates where source semantics are absent or unrotated terrain-type IDs differ from concrete rotated IDs |
| Conditional immediate events | BN condition evaluator and `talk_effect_t` action parsing | Compiler expands reviewed immediate EOCs; native branch executes the selected ordinary effects. Delayed/recurring lifecycle remains blocked |
| Random math | BN `rng`/`rng_float`, existing seeded generator | DDA function syntax and rounding/range checks; no second random generator |
| Items | BN item types, inventory operations, item locations and normal serialization | DDA quantity/ammo/container semantics beyond the stock dialogue effect forms |
| Locations | Existing mapgen definitions, palettes, NPC placement and overmap specials | Reviewed replacements preserve existing BN variants and frequencies; chemist diff changes two lines |
| Windows package | Official BN CMake installation rules | Verification, build manifest, ZIP and SHA256; installed-data tests run before upload |

Boundaries still requiring actual implementation include delayed/recurring EOCs,
several activities, camp consumers and pockets. Unsupported definitions remain
preserved and blocked. For example, a dialogue-only `ACT_GAME` assignment is not
sent to BN's item-based game handler with an empty item target.

Source pins: BN `c621aaf42fa182473aad10feea2b55647704dcf1`, DDA
`c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`. The project does contain custom native
code; this is not a claim that the whole port works through stock JSON alone.
