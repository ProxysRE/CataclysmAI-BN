# World-scoped community state

Unprefixed DDA math names are global, not player or NPC variables. The reference
is `math_exp::math_exp_impl::new_var` in pinned DDA `src/math_parser.cpp`
(`c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`): `u_` selects the player, `n_`
selects the NPC, `v_` selects a variable talker, and `_` selects context.
The latter two remain unsupported. DDA constants pi/π/e/true/false are compiled
as literals, not mistaken for global variable names.

The BN bridge now supports global numeric reads, assignment, increments and
`has_var`, plus literal global string assignment/comparison. Globals use their
own map in `game`, serialize in the world's master save, clear before loading
older saves that lack the member, and reset at game setup. They are shared by
all characters and dimensions of the world. Player/NPC string variables remain
separate, including when the same name exists in all three scopes.

The generated IR uses `actor: global`. Native JSON also supports
`dda_set_global_string` and `dda_global_string`, including yes/no dynamic lines.
Numeric reads reject nonnumeric string state instead of silently converting
it. These are compatibility additions for the staged communities; the large
batch is still not automatically installed.

EOC expansion now rejects delayed, inline, recurring and extended calls instead
of executing them immediately or ignoring lifecycle arguments. Runtime
conditions beyond an explicit expects_vars assertion remain blocked. A bug
that iterated the keys of a single-object EOC effect has also been fixed.
Blocked definitions retain their original source for later engine support.

On the unchanged 1,647-definition batch the known blocked count falls from 125
to 63, including explicit lifecycle blockers newly reported by the stricter
expander. This is conversion coverage, not gameplay certification.

Local checks cover scoping, constants, source retention, safe EOC rejection,
single-object expansion, standalone C++ evaluation and patch applicability.
Pending native Windows coverage checks sharing between two NPCs, isolation
from player/NPC variables, global string branches, real master-save round-trip
and clearing on legacy load. Game setup clearing is implemented but not invoked
by this test fixture.
