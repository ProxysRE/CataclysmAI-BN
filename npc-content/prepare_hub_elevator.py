#!/usr/bin/env python3
"""Build a bounded Hub elevator access bridge around stock BN transportation."""
import argparse
import copy
import difflib
import json
from pathlib import Path

from audit_hub_access import access_sources

ROOT = Path(__file__).resolve().parent
TRAIT = 'PROF_HUB01_ANCILLIARY'
MUTATIONS = 'data/json/mutations/mutations.json'
PAYLOAD = 'data/json/dda_hub_elevator_access.json'


def replacements():
    files = access_sources()
    result = {}
    source = files['bn/src/iexamine_elevator.cpp']
    source = source.replace('#include "iexamine.h"', '#include "iexamine.h"\n#include "hub_elevator_access.h"')
    old = 'void iexamine::elevator( player &p, const tripoint_bub_ms &examp )'
    assert source.count(old) == 1
    source = source.replace(old, 'static void elevator_travel( player &p, const tripoint_bub_ms &examp,\n                             const std::optional<int> fixed_destination )')
    old = '    const int movez = elevator::choose_floor( examp, this_omt, sm_orig );'
    assert source.count(old) == 1
    # optional::value_or would eagerly show the menu even for a fixed floor.
    source = source.replace(old, '    const int movez = fixed_destination ? *fixed_destination :\n                      elevator::choose_floor( examp, this_omt, sm_orig );')
    old = '    const auto vehicles_dest = elevator::vehicles_on( elevator_dest );'
    assert source.count(old) == 1
    source = source.replace(old, '''    if( fixed_destination && ( elevator_here.empty() ||
        !std::all_of( elevator_dest.begin(), elevator_dest.end(), [&here]( const auto &pos ) {
            return here.has_flag( TFLAG_ELEVATOR, pos );
        } ) ) ) {
        popup( _( "The elevator cannot reach that floor." ) );
        return;
    }
''' + old)
    source += '''
void iexamine::elevator( player &p, const tripoint_bub_ms &examp )
{
    elevator_travel( p, examp, std::nullopt );
}

static void hub_elevator( player &p, const tripoint_bub_ms &examp, int direction )
{
    if( !p.has_trait( trait_id( "PROF_HUB01_ANCILLIARY" ) ) ) {
        popup( _( "The control panels' screen flashes before displaying \\\"UNAUTHORIZED\\\" in bold red letters." ) );
        return;
    }
    const auto destination = dda_port::hub_elevator_destination( p, examp.z(), direction,
                             -OVERMAP_DEPTH, OVERMAP_HEIGHT );
    if( !destination ) {
        popup( _( "The elevator cannot reach that floor." ) );
        return;
    }
    elevator_travel( p, examp, destination );
}

void iexamine::robofac_elevator_up( player &p, const tripoint_bub_ms &examp )
{
    hub_elevator( p, examp, 1 );
}

void iexamine::robofac_elevator_down( player &p, const tripoint_bub_ms &examp )
{
    hub_elevator( p, examp, -1 );
}
'''
    result['src/iexamine_elevator.cpp'] = source
    source = files['bn/src/iexamine.h']
    old = 'void elevator( player &p, const tripoint_bub_ms &examp );'
    assert source.count(old) == 1
    result['src/iexamine.h'] = source.replace(old, old + '\nvoid robofac_elevator_up( player &p, const tripoint_bub_ms &examp );\nvoid robofac_elevator_down( player &p, const tripoint_bub_ms &examp );')
    source = files['bn/src/iexamine.cpp']
    old = '{ "elevator", &iexamine::elevator },'
    assert source.count(old) == 1
    result['src/iexamine.cpp'] = source.replace(old, old + '\n            { "robofac_elevator_up", &iexamine::robofac_elevator_up },\n            { "robofac_elevator_down", &iexamine::robofac_elevator_down },')
    # Retain the mutual exclusion in both directions, including the existing BN trait.
    source = files['bn/' + MUTATIONS]
    old = '"id": "PROF_FED",'
    assert source.count(old) == 1
    replacement = source.replace(old, old + '\n    "cancels": [ "' + TRAIT + '" ],')
    original = json.loads(source)
    expected = copy.deepcopy(original)
    fed = next(e for e in expected if e.get('id') == 'PROF_FED')
    assert 'cancels' not in fed
    fed['cancels'] = [TRAIT]
    assert json.loads(replacement) == expected
    result[MUTATIONS] = replacement
    return result


def payload():
    files = access_sources()
    source = json.loads(files['dda/data/json/mutations/professions.json'])
    trait = next(e for e in source if e.get('id') == TRAIT)
    assert trait['cancels'] == ['PROF_FED'] and trait['valid'] is False
    result = [copy.deepcopy(trait)]
    for direction in ('up', 'down'):
        result.append({'type': 'terrain', 'id': 't_elevator_control_robofac_' + direction,
                       'copy-from': 't_elevator_control', 'examine_action': 'robofac_elevator_' + direction})
    return result


def patch_sections():
    files = access_sources()
    return ''.join(''.join(difflib.unified_diff(files['bn/' + path].splitlines(keepends=True),
                     text.splitlines(keepends=True), 'a/' + path, 'b/' + path))
                   for path, text in replacements().items())


def prepare(check=False, bn_source=None):
    if bn_source:
        files = access_sources()
        for path in replacements():
            if (bn_source / path).read_text(encoding='utf-8') != files['bn/' + path]:
                raise ValueError('Hub access baseline drift: ' + path)
        for folder, kind in (('data/json/mutations', 'mutation'), ('data/json/furniture_and_terrain', 'terrain')):
            for path in (bn_source / folder).rglob('*.json'):
                entries = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(entries, dict):
                    entries = [entries]
                for e in entries:
                    identifiers = e.get('id', [])
                    identifiers = [identifiers] if isinstance(identifiers, str) else identifiers
                    if e.get('type') == kind and set(identifiers) & {TRAIT, 't_elevator_control_robofac_up', 't_elevator_control_robofac_down'}:
                        raise ValueError('Hub access ID already exists: ' + str(path))
    text = json.dumps(payload(), indent=2) + '\n'
    target = ROOT / 'native/dda_hub_elevator_access.json'
    if check:
        if target.read_text(encoding='utf-8') != text:
            raise ValueError('Stale Hub elevator payload')
    else:
        target.write_text(text, encoding='utf-8', newline='\n')
    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    options = parser.parse_args()
    prepare(options.check, options.bn_source)
    print('Hub access: stock BN transport, restricted directional controls and source ancillary trait')
