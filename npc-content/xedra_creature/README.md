# XEDRA church creature dependencies and configurable native ranged pull

Status: native code and payload prepared; Windows compile/runtime validation pending. The XEDRA church itself is not enabled.

The source dust field and emitter are copied exactly, including colored light, half-life, emission frequency and concentration. The glowing string item preserves its source fields with only ITEM -> BN GENERIC. The monster keeps source weight, volume, health, speed, vision, faction, species, scent and grab strength.

The existing BN RANGED_PULL implementation is reused, with an optional ranged_pull_options object on the monster type:

- range: default 3, configured to 5;
- max_weight_ratio: default 0 (legacy weight check disabled), configured to 3;
- full_range: default false (legacy melee-damage-derived pull distance), configured true;
- use_grab_strength: default false (legacy effect intensity +4), configured true (at least source strength 35);
- respect_seatbelts: default false, configured true for a boarded character on an unbroken seatbelt part.

All other attack functions are unchanged. Existing LOS, walls/furniture/creature and rotated vehicle obstruction checks, dodge, movement, unboarding and trap handling remain BN native. Failed weight/seatbelt checks return before movement or move cost. No monster ID is hardcoded in the attack.

Compatibility limits remain explicit. BN's two-turn grab lifecycle is retained rather than importing DDA's permanent, limb/attacker-tracked grabs. The unsupported RANGED_ATTACKER AI flag is omitted, so BN's normal monster planning applies. DISAPPEAR supplies corpse-free death with BN wording, rather than DDA's custom death message. Source GRAB_FILTER/maimed_arm conditions and exclusive-grab handling require further review. This is a BN adaptation, not complete behavioral equivalence.

Native tests check loaded source values, unchanged legacy defaults, field/emitter/item registration and rejection of an overweight visible target without movement. Successful pulls, vehicle seatbelts, traps and the grab lifecycle still need runtime/field testing. Local source/diff/packaging checks passed. The Windows workflow checks all three pinned native source files; fast validation rejects typed ID collisions against the full pinned BN JSON tree.

The source bundle preserves pinned BN mtype/loader/attack files and DDA attack actors. The church source bundle supplies original monster, field, emitter and item data. Protective XEDRA suit and corpse contents remain staged and block enabling natural generation of the paranormal church.
