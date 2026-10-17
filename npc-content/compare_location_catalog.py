#!/usr/bin/env python3
"""Compare pinned core location registrations and review only meaningful gaps."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'location_catalog'


def read_sources():
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    parts = sorted(ROOT.glob('SOURCE.part*'))
    if [p.name for p in parts] != manifest['parts']:
        raise ValueError('Missing location catalog source part')
    raw = gzip.decompress(base64.b64decode(b''.join(p.read_bytes() for p in parts), validate=True))
    if hashlib.sha256(raw).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Catalog source checksum mismatch')
    files = json.loads(raw)
    if set(files) != set(manifest['files']):
        raise ValueError('Catalog source manifest mismatch')
    for path, text in files.items():
        if hashlib.sha256(text.encode()).hexdigest() != manifest['files'][path]['sha256']:
            raise ValueError('Catalog source changed: ' + path)
    return files, manifest


def ids(entry):
    value = entry.get('id', [])
    return [value] if isinstance(value, str) else value


def normalized(identifier, index):
    if identifier in index:
        return identifier
    for suffix in ('_north', '_east', '_south', '_west'):
        if identifier.endswith(suffix):
            return identifier[:-len(suffix)]
    return identifier


def physical_refs(entry):
    """Mutable piece references are template names, not terrain IDs."""
    overmaps = entry.get('overmaps', [])
    values = overmaps.values() if isinstance(overmaps, dict) else overmaps
    for value in values:
        if isinstance(value, dict) and isinstance(value.get('overmap'), str):
            yield value['overmap']


def static_summary(entry):
    cells = entry.get('overmaps', [])
    if not isinstance(cells, list):
        return {'mutable': True}
    placed = [c for c in cells if 'overmap' in c and 'point' in c]
    return {'terrain_placements': len(placed), 'constraint_records': len(cells) - len(placed),
            'z_levels': sorted({c['point'][2] for c in placed})}


def compare():
    files, manifest = read_sources()
    sites = {'dda': {}, 'bn': {}}
    terrain = {'dda': {}, 'bn': {}}
    for path, text in files.items():
        if path.startswith('meta/'):
            continue
        side = path.split('/')[0]
        entries = json.loads(text)
        for position, entry in enumerate(entries if isinstance(entries, list) else [entries]):
            kind = entry.get('type')
            target = terrain[side] if kind == 'overmap_terrain' else sites[side] if kind in ('overmap_special', 'city_building') else None
            if target is not None:
                for identifier in ids(entry):
                    key = identifier if kind == 'overmap_terrain' else kind + ':' + identifier
                    if key in target:
                        if kind == 'overmap_terrain':
                            target[key].setdefault('additional_providers', []).append({'file': path, 'index': position})
                            continue
                        raise ValueError('Duplicate typed catalog identity: ' + side + '/' + key)
                    target[key] = {'file': path, 'index': position, 'definition': entry}
    rows = []
    for key, source in sorted(sites['dda'].items()):
        entry = source['definition']
        refs = sorted({normalized(i, terrain['dda']) for i in physical_refs(entry)})
        missing = [i for i in refs if i not in terrain['bn']]
        baseline = sites['bn'].get(key)
        rows.append({'identity': key, 'source': {k: source[k] for k in ('file', 'index')},
                     'baseline': {k: baseline[k] for k in ('file', 'index')} if baseline else None,
                     'source_summary': static_summary(entry),
                     'baseline_summary': static_summary(baseline['definition']) if baseline else None,
                     'terrain_ids_not_declared_in_bn_core': missing,
                     'classification': 'same_registration' if baseline else 'different_or_absent_registration',
                     'note': 'Missing IDs alone do not rule out renamed analogues; reviewed groups provide semantic classifications'})
    reviewed = json.loads((ROOT / 'REVIEWED_GROUPS.json').read_text(encoding='utf-8'))
    by_id = {r['identity']: r for r in rows}
    for group in reviewed:
        evidence = []
        for identifier in group['source_identities']:
            row = by_id[identifier]
            if group['status'] == 'absent_specific_location_or_variant':
                assert row['baseline'] is None, identifier
                assert row['terrain_ids_not_declared_in_bn_core'], identifier
            elif group['status'] == 'expanded_or_older_version':
                assert row['baseline'] is not None or group.get('bn_analogues'), identifier
            evidence.append({k: row[k] for k in ('identity', 'source_summary', 'baseline_summary', 'terrain_ids_not_declared_in_bn_core')})
        for analogue in group.get('bn_analogues', []):
            assert analogue in sites['bn'], analogue
        group['evidence'] = evidence
        group['analogue_summaries'] = {i: static_summary(sites['bn'][i]['definition']) for i in group.get('bn_analogues', [])}
    report = {'pins': manifest['pins'], 'scope': 'Core JSON registrations, all overmap terrain declarations, full mapgen file inventory and six focused mapgen files. Mods excluded. Not an exhaustive semantic diff of every interior/nested variant.',
              'source_files': len(files) - 1,
              'registration_counts': {s: len(v) for s, v in sites.items()},
              'terrain_counts': {s: len(v) for s, v in terrain.items()},
              'reviewed_groups': reviewed, 'all_registration_comparisons': rows,
              'not_a_playable_port': True,
              'important_exclusions': ['Nuclear plant is already substantially present in BN',
                'Different IDs for existing generic churches, prisons, shops or farms do not imply their entire category is absent',
                'Roof-only changes, field/rock support cells and naming migrations are not presented as whole new locations',
                'Mutable template labels are not treated as physical terrain IDs']}
    (ROOT / 'COMPARISON.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'REVIEWED_REPORT.json').write_text(json.dumps({k: v for k, v in report.items() if k != 'all_registration_comparisons'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    lines = ['# Локации DDA, отсутствующие или неполные в основном контенте BN', '',
             'Срез исходников проекта: DDA `' + manifest['pins']['dda'][:12] + '`, BN `' + manifest['pins']['bn'][:12] + '`.', '',
             report['scope'], '', 'В списке отсутствует именно указанная локация или версия, а не весь тип зданий.', '']
    for status, heading in [('absent_specific_location_or_variant', 'Отсутствующие локации и отдельные новые варианты'), ('expanded_or_older_version', 'Существующие локации с неполной или старой версией')]:
        lines += ['## ' + heading, '', '| Локация | Подтверждённое отличие |', '|---|---|']
        for group in reviewed:
            if group['status'] == status:
                links = []
                for identity in group['source_identities']:
                    source = by_id[identity]['source']['file'][4:]
                    url = 'https://github.com/CleverRaven/Cataclysm-DDA/blob/' + manifest['pins']['dda'] + '/' + source
                    link = '[исходник](' + url + ')'
                    if link not in links:
                        links.append(link)
                lines.append('| ' + group['name'] + ' | ' + group['difference'] + ' ' + ' '.join(links) + ' |')
        lines.append('')
    lines += ['Это подтверждённая выборка крупных и различимых объектов. Внутренние варианты с теми же ID требуют дальнейшего сравнения mapgen; данный отчёт не объявляет такой аудит завершённым.', '']
    (ROOT / 'MISSING_AND_PARTIAL.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print('Reviewed', len(reviewed), 'groups from', len(rows), 'DDA location registrations')
    return report


if __name__ == '__main__':
    compare()
