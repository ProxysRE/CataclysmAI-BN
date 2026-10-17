#!/usr/bin/env python3
"""Check bounded native access adaptation, source fidelity and baseline collisions."""
import json
from pathlib import Path
import tempfile

from audit_hub_access import access_sources
from prepare_hub_elevator import MUTATIONS, TRAIT, payload, prepare, replacements


def check():
    prepare(check=True)
    files = access_sources()
    adapted = payload()
    original = next(e for e in json.loads(files['dda/data/json/mutations/professions.json']) if e.get('id') == TRAIT)
    assert adapted[0] == original
    assert adapted[0]['valid'] is False and adapted[0]['profession'] is True
    generated = replacements()
    baseline = json.loads(files['bn/' + MUTATIONS])
    merged = json.loads(generated[MUTATIONS])
    assert len(baseline) == len(merged)
    for a, b in zip(baseline, merged):
        if a.get('id') == 'PROF_FED':
            assert b == dict(a, cancels=[TRAIT])
        else:
            assert a == b
    parent = next(e for e in json.loads(files['bn/data/json/furniture_and_terrain/terrain-mechanisms.json']) if e.get('id') == 't_elevator_control')
    for terrain, direction in zip(adapted[1:], ('up', 'down')):
        assert terrain == dict(parent, id='t_elevator_control_robofac_' + direction, looks_like='t_elevator_control', examine_action='robofac_elevator_' + direction)
        assert 'copy-from' not in terrain  # Must load before the parent file too.
    native = generated['src/iexamine_elevator.cpp']
    for operation in ('move_creatures_away', 'move_items', 'move_creatures', 'move_vehicles', 'move_player'):
        assert native.count('elevator::' + operation + '(') == 1
    assert native.count('"on_elevator_try_use"') == 1
    assert 'fixed_destination ? *fixed_destination :' in native
    assert 'fixed_destination && ( elevator_here.empty()' in native
    assert 'std::all_of( elevator_dest.begin(), elevator_dest.end()' in native
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory)
        for name in generated:
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(files['bn/' + name], encoding='utf-8')
        prepare(check=True, bn_source=checkout)
        conflict = checkout / 'data/json/furniture_and_terrain/elsewhere.json'
        conflict.parent.mkdir(parents=True, exist_ok=True)
        conflict.write_text(json.dumps([{'type': 'terrain', 'id': ['t_elevator_control_robofac_up', 'another_id']}]))
        try:
            prepare(check=True, bn_source=checkout)
        except ValueError:
            pass
        else:
            raise AssertionError('Conflicting terrain in an unrelated file was accepted')
        conflict.unlink()
        path = checkout / 'src/iexamine_elevator.cpp'
        path.write_text(path.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        try:
            prepare(check=True, bn_source=checkout)
        except ValueError:
            pass
        else:
            raise AssertionError('Unreviewed BN elevator implementation was accepted')
    print('PASS: Hub credential fidelity, mutual exclusion, BN transport reuse, directional binding, fail-closed shaft guard and whole-catalog collision checks')


if __name__ == '__main__':
    check()
