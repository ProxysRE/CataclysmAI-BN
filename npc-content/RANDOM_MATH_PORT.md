# DDA random dialogue math

Implemented `rng(a,b)` and `rand(n)` for the expression bridge. The former uses
BN `rng_float` (real values), the latter BN `rng(0, round(n))` (inclusive integer
bounds). Both engines swap reversed bounds. Random values are drawn at execution,
not when adapting JSON, and use the game's seeded generator.

Reference sources:

- [DDA math functions at the pinned commit](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/math_parser_func.h): `math_rng`, `rand`, function registry.
- [DDA RNG](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/rng.cpp).
- [BN RNG](https://github.com/cataclysmbn/Cataclysm-BN/blob/c621aaf42fa182473aad10feea2b55647704dcf1/src/rng.cpp).

Non-finite arguments, overflowing integer conversions and overflowing real
interval widths fail explicitly. The pure evaluator requires an explicit random
source; the game bridge supplies BN's RNG. No substitute zero or reward is granted
when random evaluation fails.

This unblocks adaptation of `TALK_Directions_exodii_false` and
`TALK_ROBOFAC_MERC_PAT`, reducing blocked definitions from 68 to 66 while retaining
all 1,767 source definitions. This is adaptation coverage, not runtime certification
of either NPC or the Exodii mission chain.

Checks include exact real-number preservation, half-away-from-zero rounding,
integer overflow rejection, runtime JSON parsing, reversed bounds and current
actor variable reads. Windows native tests are pending.

The native patch has been regenerated to include these changes and the previously
edited test-isolation fix. `check_native_patch_sources.py` checks all ten generated
native file sections against their actual sources, plus the workflow checksum.
It runs in both fast CI and before the Windows build.
