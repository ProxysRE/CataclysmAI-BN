#!/usr/bin/env python3
"""Compose radio and hotel additions into one patch of the shared city file."""
import argparse
import difflib
import json
from pathlib import Path
from compare_location_catalog import read_sources
from prepare_radio_stations import prepare_data as radio_data, sources as radio_sources, MAP, CITY
from prepare_hotel_roofs import prepare_data as hotel_data, sources as hotel_sources, COMMERCIAL

ROOT = Path(__file__).resolve().parent
PAYLOAD = 'data/json/dda_hotel_roof_caps.json'


def prepare_data():
    outputs, _, _ = radio_data()
    payload, city, _ = hotel_data(outputs[CITY])
    outputs[CITY] = json.dumps(city, ensure_ascii=True, indent=2) + '\n'
    return outputs, payload


def patch_sections():
    outputs, _ = prepare_data()
    catalog, _ = read_sources()
    old = {MAP: radio_sources()['bn/station_radio.json'], CITY: catalog['bn/' + CITY]}
    return ''.join(''.join(difflib.unified_diff(old[p].splitlines(keepends=True), text.splitlines(keepends=True),
                   'a/' + p, 'b/' + p)) for p, text in outputs.items())


def prepare(check=False, bn_source=None):
    _, payload = prepare_data()
    if bn_source:
        catalog, _ = read_sources()
        for relative, expected in [('data/json/mapgen/hotel_tower.json', hotel_sources()['bn']),
                                    (COMMERCIAL, catalog['bn/' + COMMERCIAL])]:
            if (bn_source / relative).read_text(encoding='utf-8') != expected:
                raise ValueError('Hotel baseline drift: ' + relative)
        names = set(payload[0]['id'])
        def flat(v):
            if isinstance(v, str):
                yield v
            elif isinstance(v, list):
                for child in v:
                    yield from flat(child)
        for directory in ('data/json/mapgen', 'data/json/overmap/overmap_terrain'):
            for path in (bn_source / directory).rglob('*.json'):
                entries = json.loads(path.read_text(encoding='utf-8'))
                for e in entries if isinstance(entries, list) else [entries]:
                    if names.intersection(flat(e.get('id', e.get('om_terrain', [])))):
                        raise ValueError('Hotel ID collision: ' + str(path))
    target = ROOT / 'native/dda_hotel_roof_caps.json'
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    if check:
        assert target.read_text(encoding='utf-8') == text, 'Stale hotel native payload'
    else:
        target.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bn-source', type=Path)
    args = parser.parse_args()
    prepare(args.check, args.bn_source)
