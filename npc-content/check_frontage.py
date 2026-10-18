#!/usr/bin/env python3
"""Verify the narrow fixed-special port and preserved placement constraints."""
from prepare_frontage import prepare, sources, replacement, patch_sections, ROOT

prepare()
files=sources()
before=files['bn/src/overmap/overmap.cpp']
after=replacement()
start=before.index('struct fixed_overmap_special_data:')
end=before.index('\nstruct mutable_overmap_join',start)
new_end=after.index('\nstruct mutable_overmap_join',start)
assert before[:start]==after[:start]
assert before[end:]==after[new_end:]
block=after[start:new_end]
# Null-only exception, not a general invalid-ID bypass.
assert 'if (!oter.is_null() && !oter.is_valid())' in block
assert 'if (elem.locations.empty())' in block
assert 'if (!l.is_valid())' in block
assert 'if (points.contains(pos))' in block
assert 'std::copy(terrains.begin(), terrains.end(), std::back_inserter(result));' in block
assert block.index('if (elem.terrain.is_null()) { continue; }') < block.index('result.omts_used.push_back(location)')
assert 'if (!ter.terrain.is_null()) { result.push_back(ter.terrain); }' in block
assert 'terrain.p.z() == 0 && !terrain.terrain.is_null()' in block
# BN already supports global uniqueness; do not reduce this to per-OM uniqueness.
assert 'special.has_flag("GLOBALLY_UNIQUE")' in before
fixture=(ROOT/'native/dda_special_constraints_test.cpp').read_text()
for text in ('can_place_special','place_special','om_direction::type::north','om_direction::type::east',
             'om_direction::type::south','om_direction::type::west','river_center','om->ter( frontage ) == field',
             'is duplicated','dda_missing_location','dda_missing_terrain'):
    assert text in fixture,text
assert patch_sections().count('+++ b/src/overmap/overmap.cpp')==1
print('PASS: DDA placement behavior, mapgen/preview null filtering and original BN validation; native tests prepared for four rotations, preserved terrain, water rejection and invalid input')
