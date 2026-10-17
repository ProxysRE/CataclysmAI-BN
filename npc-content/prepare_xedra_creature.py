#!/usr/bin/env python3
"""Reuse BN ranged pull with optional source-driven parameters and XEDRA creature data."""
import argparse
import base64
import copy
import difflib
import gzip
import hashlib
import json
from pathlib import Path
from prepare_rural_churches import sources as church_sources

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'xedra_creature'
PAYLOAD = 'data/json/dda_xedra_creature.json'
CORE = ('mtype.h', 'monstergenerator.cpp', 'monattack.cpp')


def sources():
    m = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    raw = gzip.decompress(base64.b64decode(b''.join((FOLDER / n).read_bytes() for n in m['parts']), validate=True))
    assert hashlib.sha256(raw).hexdigest() == m['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(m['files'])
    for name, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == m['files'][name]
    return files


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:80]
    return text.replace(old, new)


def replacements():
    files = sources()
    result = {name: files['bn/' + name] for name in CORE}
    anchor = '        int grab_strength = 1;    /**intensity of the effect_grabbed applied*/'
    result['mtype.h'] = replace_once(result['mtype.h'], anchor, anchor + '''

        // Optional ranged-pull profile. Defaults preserve all legacy attacks.
        int ranged_pull_range = 3;
        float ranged_pull_weight_ratio = 0.0f;
        bool ranged_pull_full_range = false;
        bool ranged_pull_use_grab_strength = false;
        bool ranged_pull_respect_seatbelts = false;''')
    anchor = '    assign( jo, "grab_strength", grab_strength, strict, 0 );'
    result['monstergenerator.cpp'] = replace_once(result['monstergenerator.cpp'], anchor, anchor + '''

    if( jo.has_object( "ranged_pull_options" ) ) {
        JsonObject pull = jo.get_object( "ranged_pull_options" );
        assign( pull, "range", ranged_pull_range, strict, 2, 50 );
        assign( pull, "max_weight_ratio", ranged_pull_weight_ratio, strict, 0.0f, 100.0f );
        pull.read( "full_range", ranged_pull_full_range );
        pull.read( "use_grab_strength", ranged_pull_use_grab_strength );
        pull.read( "respect_seatbelts", ranged_pull_respect_seatbelts );
    }''')
    text = result['monattack.cpp']
    text = replace_once(text, '#include "weighted_list.h"', '#include "weighted_list.h"\n#include "vehicle/vpart_position.h"')
    start = text.index('bool mattack::ranged_pull( monster *z )')
    end = text.index('\nbool mattack::grab( monster *z )', start)
    function = text[start:end]
    function = replace_once(function, 'rl_dist( z->bub_pos(), target->bub_pos() ) > 3',
                            'rl_dist( z->bub_pos(), target->bub_pos() ) > z->type->ranged_pull_range')
    anchor = '    player *foe = dynamic_cast< player * >( target );'
    function = replace_once(function, anchor, anchor + '''
    if( z->type->ranged_pull_weight_ratio > 0.0f &&
        target->get_weight() > z->get_weight() * z->type->ranged_pull_weight_ratio ) {
        return false;
    }
    if( z->type->ranged_pull_respect_seatbelts && foe != nullptr && foe->in_vehicle &&
        here.veh_at( target->bub_pos() ).part_with_feature( "SEATBELT", true ) ) {
        return false;
    }
''')
    function = replace_once(function, '( z->type->melee_sides * z->type->melee_dice ) / 10,',
                            '( z->type->ranged_pull_full_range ? z->type->ranged_pull_range :\n                            ( z->type->melee_sides * z->type->melee_dice ) / 10 ),')
    function = replace_once(function, 'prev_effect + 4 );',
                            'z->type->ranged_pull_use_grab_strength ?\n                        std::max( prev_effect, z->get_grab_strength() ) : prev_effect + 4 );')
    result['monattack.cpp'] = text[:start] + function + text[end:]
    return result


def patch_sections():
    files = sources()
    return ''.join(''.join(difflib.unified_diff(files['bn/' + name].splitlines(keepends=True),
                    text.splitlines(keepends=True), 'a/src/' + name, 'b/src/' + name))
                   for name, text in replacements().items())


def payload():
    files = church_sources()
    field = next(e for e in json.loads(files['dda/field_type.json']) if e.get('id') == 'fd_twisting_mass_dust')
    emit = next(e for e in json.loads(files['dda/emit.json']) if e.get('id') == 'emit_twisting_mass_dust')
    mon = copy.deepcopy(next(e for e in json.loads(files['dda/nether.json']) if e.get('id') == 'mon_twisting_mass'))
    mon['special_attacks'] = [['RANGED_PULL', 20]]
    mon['ranged_pull_options'] = {'range': 5, 'max_weight_ratio': 3.0, 'full_range': True,
                                 'use_grab_strength': True, 'respect_seatbelts': True}
    mon['death_function'] = ['DISAPPEAR']
    mon['flags'].remove('RANGED_ATTACKER')  # No such AI flag exists in pinned BN.
    item = copy.deepcopy(next(e for e in json.loads(files['dda/extradimensional_artifacts.json']) if e.get('id') == 'inert_glowing_string'))
    item['type'] = 'GENERIC'
    return [field, emit, mon, item]


def validate_bn_data(folder):
    from quest_dependency_graph import ITEM_TYPES
    names = {'field_type': {'fd_twisting_mass_dust'}, 'emit': {'emit_twisting_mass_dust'},
             'MONSTER': {'mon_twisting_mass'}, 'item': {'inert_glowing_string'}}
    for path in (folder / 'data/json').rglob('*.json'):
        entries = json.loads(path.read_text(encoding='utf-8'))
        for e in entries if isinstance(entries, list) else [entries]:
            if not isinstance(e, dict):
                continue
            kind = 'item' if e.get('type') in ITEM_TYPES else e.get('type')
            value = e.get('id', [])
            ids = {value} if isinstance(value, str) else set(value)
            if ids.intersection(names.get(kind, set())):
                raise ValueError('XEDRA typed ID collision: ' + str(path))


def prepare(check=False, bn_source=None, bn_data=None):
    if bn_source:
        files = sources()
        for name in CORE:
            if (bn_source / 'src' / name).read_text(encoding='utf-8') != files['bn/' + name]:
                raise ValueError('Ranged pull source baseline drift: ' + name)
    if bn_source or bn_data:
        validate_bn_data(bn_source or bn_data)
    text = json.dumps(payload(), ensure_ascii=True, indent=2) + '\n'
    target = ROOT / 'native/dda_xedra_creature.json'
    if check:
        assert target.read_text(encoding='utf-8') == text
    else:
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    parser.add_argument('--bn-data', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source, args.bn_data)
