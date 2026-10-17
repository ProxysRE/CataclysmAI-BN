# Named faction trust and existing chemist map

The DDA expression `faction_trust('robofac') -= 20` in
`MISSION_HUB01_PAY_BACK_RIOT_GEAR` now adapts to a native effect that updates the
named faction's actual `trusts_u`. Reads, assignment, addition/subtraction and
increments use that same field. They do not depend on the current speaker's
faction or a synthetic player variable. Dynamic faction names remain unsupported.

Semantics were checked against DDA's `faction_trust_eval` and `faction_trust_ass`
in [the pinned source](https://github.com/CleverRaven/Cataclysm-DDA/blob/c19e95bc96d27d8bef8e2e246a63cd4cd6f89974/src/math_parser_diag.cpp).
BN already serializes `trusts_u`; no new save field is introduced. Fractional
assignments truncate like DDA's assignment to the integer field. Non-finite or
out-of-range results fail explicitly.

The native regression uses a speaker from `your_followers`, updates `robofac`
twice, verifies the other faction is unchanged, and saves/loads the resulting
negative trust. This does not yet install the full Hub mission package.

The engine patch also replaces `data/json/mapgen/chemical_lab.json` using the
reviewed merge. The textual diff changes only two lines: the chemist's chair and
its placement representation. Coordinates, every other map entry, roof, stock,
ownership and BN-specific heater remain unchanged. Trade zones and DDA chemist
quests are still deferred.

The previous Windows checkpoint passed 31 cases / 1,065 assertions in run
38976175204 at c644c36547e6349663987d98b912ffe6b01cde66. These new changes require
another native run. Adaptation retains 1,767 definitions with 65 blocked originals.
