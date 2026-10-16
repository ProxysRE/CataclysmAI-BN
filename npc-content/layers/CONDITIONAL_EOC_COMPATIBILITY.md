# Conditional activation effects and shared math

Immediate activation EOCs can now compile to a runtime conditional effect
(`dda_if`) instead of discarding a condition or choosing a branch while
preparing data. Named and inline activation definitions preserve the condition,
true effect, false effect, nested calls and the order of actions. The runtime
reads the condition anew on each invocation and executes one branch only.
Branches contain effect actions, not dialogue opinion/topic metadata.

Delayed calls, extended call arguments, recurring definitions, deactivation
metadata and unsupported lifecycle fields remain blocked. An expects_vars
assertion is checked against supplied context before its remaining condition
is compiled. Unknown references and recursion remain errors. Defining the full
native EOC registry and scheduler is still separate work; the 34 staged EOC
declarations are not automatically installed by this inliner.

The math compiler additionally supports binary min/max, ternary clamp, and
`time_since('cataclysm', 'unit':'days')`. Calendar origin uses BN's actual
start_of_cataclysm value. Reference behavior is DDA time_since_eval in
`src/math_parser_diag.cpp`, pinned commit
`c19e95bc96d27d8bef8e2e246a63cd4cd6f89974`. Invalid clamp bounds fail instead
of invoking undefined behavior. UI input, random expressions and new activity
handlers are not inferred from these arithmetic additions.

The unchanged 1,762-definition batch has 67 known blocked definitions, down
from 70. This count remains a bounded conversion audit, not a native load or
gameplay pass. Local compiler, selective-location, preservation and standalone
C++ checks pass. Native tests cover runtime branch switching, exactly one
trust increment, calendar origin and the existing master-save round-trip.
Windows execution is pending.

Run 38923398535 failed to compile its save test because game::serialize_master
was private. The existing stream serializer is now declared beside the public
unserialize_master method, allowing an in-memory round-trip without invoking
filesystem saves. Its serialization implementation and file-save callers are
unchanged.

The subsequent dependency selection adds pinned Exodii common dialogue and
generic NPC EOC sources, resolving the previously unknown warehouse-directions
and drivebelt-completion references. The expanded batch is 1,767 definitions
with 68 known blockers, including the newly selected lifecycle declarations.
The drivebelt completion's global/lifecycle metadata remains blocked.

Immediate `if`/`then`/`else` action objects now use the same runtime conditional.
Literal and actor/global-variable one_in_chance predicates call BN's one_in
with DDA-compatible integer conversion. Values <=1 are certain; out-of-range
positive inputs fail without overflowing. Runtime tests cover global changes,
fractional conversion and the upper bound. This does not implement arbitrary
rand/rng math functions or a scheduler.
