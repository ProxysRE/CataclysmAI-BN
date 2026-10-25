"""Rebuild fixed industrial_01 geometry and constructor manifest (no runtime hooks)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'locations/industrial_01'
MOD = ROOT / 'mods/trkv_locations_dev'
BASE = '4add4eaaa9c4cbfd6b67deb77ebab95b8b404bc5'
BN = '554950f3635f50ddd1d32c6e1b6e2bdee9842bd6'


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build():
    g = [['#'] * 72 for _ in range(72)]

    def rect(x0, y0, x1, y1, char):
        for y in range(y0, y1):
            for x in range(x0, x1):
                g[y][x] = char

    def frame(x0, y0, x1, y1):
        rect(x0, y0, x1, y0 + 1, '#')
        rect(x0, y1 - 1, x1, y1, '#')
        rect(x0, y0, x0 + 1, y1, '#')
        rect(x1 - 1, y0, x1, y1, '#')

    rect(2, 2, 70, 60, '.')
    rect(2, 60, 70, 70, ',')
    # West: three distinct rooms and a six-cell longitudinal service corridor.
    for a, b in [(5, 20), (20, 40), (40, 60)]:
        frame(2, a, 21, b)
    # East: stores, sorting area and dispatch; shared walls retain two-cell doors.
    for a, b in [(5, 23), (23, 40), (40, 60)]:
        frame(49, a, 70, b)
    # Main production hall, connected to west/east at three elevations.
    frame(27, 5, 50, 60)
    for x in [20, 27, 49]:
        for a, b in [(12, 15), (33, 38), (51, 55)]:
            rect(x, a, x + 1, b, '.')
    # Exterior/main links: broad openings, not rows of artificial narrow doors.
    for x0, x1 in [(8, 12), (34, 40), (59, 64)]:
        rect(x0, 5, x1, 6, '.')
        rect(x0, 59, x1, 60, '.')
    for y in [22, 23, 39, 40]:
        rect(60, y, 63, y + 1, '.')
    for y in [19, 20, 39, 40]:
        rect(8, y, 11, y + 1, '+')
    # Two conventional room doors, with other routes around their closed state.
    rect(20, 12, 21, 14, '+')
    rect(49, 51, 50, 53, '+')
    # Solid piers: actual concrete, not machinery falsely advertised as cover.
    for x, y in [(34, 15), (43, 25), (34, 43), (43, 53)]:
        rect(x, y, x + 2, y + 4, '#')
    # Offset screens protect start pockets and break long sightlines.
    rect(12, 6, 13, 12, '#')
    rect(58, 6, 59, 13, '#')
    rect(13, 62, 14, 70, '#')
    rect(57, 60, 58, 67, '#')
    # Functional furniture; racks are transparent and impassable in pinned BN.
    for x in [53, 65]:
        rect(x, 25, x + 1, 31, 'r')
    # Sorting screen stops a north/south spawn sightline; both ends can be bypassed.
    rect(58, 31, 67, 32, '#')
    for x in [53, 64]:
        rect(x, 8, x + 1, 12, 'r')
    rect(4, 23, 5, 31, 'l')
    rect(4, 43, 12, 44, 'c')
    rect(52, 43, 56, 44, 'c')
    rect(31, 22, 34, 24, 'c')
    rect(41, 46, 45, 48, 'c')
    # Loading islands leave several cells on both sides for circulation.
    rect(24, 63, 29, 65, 'R')
    rect(42, 66, 47, 68, 'R')
    lamps = [(10, 15), (24, 15), (24, 36), (24, 53), (38, 10),
             (38, 30), (38, 41), (38, 55), (62, 16), (59, 35),
             (61, 48), (34, 64)]
    for x, y in lamps:
        assert g[y][x] in '.,', (x, y, g[y][x])
        g[y][x] = 'a' if g[y][x] == '.' else 'A'

    terrain = {'.': 't_thconc_floor', ',': 't_pavement', '#': 't_concrete_wall',
               '+': 't_door_c', 'A': 't_pavement', 'R': 't_pavement',
               **{c: 't_thconc_floor' for c in 'rlca'}}
    furniture = {'r': 'f_rack', 'R': 'f_rack', 'l': 'f_locker', 'c': 'f_counter',
                 'a': 'f_olight_nogrid', 'A': 'f_olight_nogrid'}
    tiles, overmap, placement, blocks = [], [], [], []
    for by in range(3):
        for bx in range(3):
            ident = f'trkv_loc_industrial_01_{bx}_{by}'
            rows = [''.join(row[bx * 24:(bx + 1) * 24]) for row in g[by * 24:(by + 1) * 24]]
            used = set(''.join(rows))
            tiles.append({'type': 'mapgen', 'om_terrain': [ident], 'method': 'json',
                          'object': {'fill_ter': 't_concrete_wall', 'rows': rows,
                                     'terrain': {c: v for c, v in terrain.items() if c in used},
                                     'furniture': {c: v for c, v in furniture.items() if c in used}}})
            overmap.append({'type': 'overmap_terrain', 'id': ident,
                            'name': 'Промышленный узел: макет', 'sym': 'I', 'color': 'light_gray',
                            'see_cost': 0, 'mondensity': 0, 'flags': ['NO_ROTATE']})
            placement.append({'point': [bx, by, 0], 'overmap': ident})
            blocks.append({'terrain_id': ident, 'origin': [bx * 24, by * 24, 0], 'size': [24, 24]})
    save(MOD / 'mapgen.json', tiles)
    save(MOD / 'overmap.json', overmap + [{'type': 'overmap_special',
         'id': 'trkv_loc_industrial_01', 'overmaps': placement, 'locations': ['land'],
         'occurrences': [0, 0], 'flags': ['CLASSIC']}])
    save(MOD / 'modinfo.json', [{'type': 'MOD_INFO', 'id': 'trkv_locations_dev',
         'name': 'Тарков: экспериментальные локации', 'authors': ['ProxysRE'],
         'description': 'Изолированный макет промышленного узла. Не подключает рейд или эвакуацию.',
         'category': 'content', 'dependencies': ['bn']}])

    def area(box):
        x0, y0, x1, y1 = box
        return {'min': [x0, y0, 0], 'max': [x1, y1, 1]}

    zone_specs = [
        ('security', 'Проходная', [3, 6, 20, 19]),
        ('lockers', 'Раздевалка', [3, 21, 20, 39]),
        ('maintenance', 'Ремонтная мастерская', [3, 41, 20, 59]),
        ('service', 'Служебная галерея', [21, 5, 27, 59]),
        ('production', 'Производственный зал', [28, 6, 49, 33]),
        ('assembly', 'Участок сборки', [28, 38, 49, 59]),
        ('crossing', 'Поперечная связь', [21, 33, 50, 38]),
        ('stores', 'Склад сырья', [50, 6, 69, 22]),
        ('sorting', 'Сортировка', [50, 24, 69, 39]),
        ('dispatch', 'Экспедиция', [50, 41, 69, 59]),
        ('loading', 'Погрузочный двор', [2, 60, 70, 70]),
        ('north_link', 'Северный проход', [2, 2, 70, 5])]
    links = []

    def link(a, b, box, kind='opening'):
        links.append({'id': f'link_{len(links) + 1:02}', 'zones': [a, b],
                      'area': area(box), 'kind': kind})

    link('security', 'service', [20, 12, 21, 15], 'mixed_door_opening')
    link('lockers', 'service', [20, 33, 21, 38])
    link('maintenance', 'service', [20, 51, 21, 55])
    link('service', 'production', [27, 12, 28, 15])
    link('service', 'crossing', [24, 33, 25, 34])
    link('crossing', 'production', [28, 32, 49, 34])
    link('crossing', 'assembly', [28, 37, 49, 39])
    link('crossing', 'sorting', [49, 33, 50, 38])
    link('assembly', 'service', [27, 51, 28, 55])
    link('production', 'stores', [49, 12, 50, 15])
    link('assembly', 'dispatch', [49, 51, 50, 55], 'mixed_door_opening')
    link('stores', 'sorting', [60, 22, 63, 24])
    link('sorting', 'dispatch', [60, 39, 63, 41])
    link('security', 'lockers', [8, 19, 11, 21], 'doors')
    link('lockers', 'maintenance', [8, 39, 11, 41], 'doors')
    for zone, x0, x1 in [('security', 8, 12), ('production', 34, 40), ('stores', 59, 64)]:
        link(zone, 'north_link', [x0, 5, x1, 6])
    link('service', 'north_link', [21, 4, 27, 6])
    for zone, x0, x1 in [('maintenance', 8, 12), ('assembly', 34, 40), ('dispatch', 59, 64)]:
        link(zone, 'loading', [x0, 59, x1, 60])
    link('service', 'loading', [21, 59, 27, 61])
    zones = [{'id': ident, 'name': name, 'area': area(box),
              'neighbors': sorted({b if a == ident else a for l in links for a, b in [l['zones']] if ident in (a, b)}),
              'connections': [l['id'] for l in links if ident in l['zones']]}
             for ident, name, box in zone_specs]
    spawns = []
    for ident, name, zone, box, pts in [
        ('entry_nw', 'Проходная', 'security', [4, 7, 10, 12], [[5, 8, 0], [7, 8, 0], [5, 10, 0], [7, 10, 0]]),
        ('entry_ne', 'Северный склад', 'stores', [61, 7, 64, 12], [[61, 8, 0], [63, 8, 0], [61, 10, 0], [63, 10, 0]]),
        ('entry_sw', 'Юго-западный двор', 'loading', [4, 63, 10, 69], [[5, 64, 0], [7, 64, 0], [5, 67, 0], [7, 67, 0]]),
        ('entry_se', 'Юго-восточный двор', 'loading', [62, 63, 68, 69], [[63, 64, 0], [65, 64, 0], [63, 67, 0], [65, 67, 0]])]:
        spawns.append({'id': ident, 'name': name, 'zone': zone, 'area': area(box),
                       'capacity': 3, 'primary': pts[:3], 'fallback': pts[3:]})
    pois = [{'id': ident, 'name': name, 'zone': zone, 'position': [x, y, 0]}
            for ident, name, zone, x, y in [
                ('shift_log', 'Журнал смен', 'security', 16, 10),
                ('lockers', 'Шкафчики рабочих', 'lockers', 6, 26),
                ('tools', 'Ремонтный верстак', 'maintenance', 9, 45),
                ('control', 'Пост управления линией', 'production', 38, 22),
                ('assembly', 'Сборочный пост', 'assembly', 38, 46),
                ('stock', 'Учёт сырья', 'stores', 61, 18),
                ('sorting', 'Сортировочные стеллажи', 'sorting', 60, 29),
                ('shipping', 'Отгрузочные документы', 'dispatch', 60, 45)]]
    manifest = {'schema_version': 1, 'location_id': 'industrial_01', 'version': '0.1.0',
        'name': 'Промышленный узел', 'base_commit': BASE, 'bn_commit': BN,
        'coordinates': {'origin': 'northwest', 'x': 'east', 'y': 'south', 'z': 'up',
                        'areas': 'min_inclusive_max_exclusive'},
        'size': [72, 72], 'levels': [0], 'blocks': blocks, 'zones': zones, 'connections': links,
        'spawn_areas': spawns, 'spawn_pair_policy': 'deny_unlisted',
        'spawn_pairs': [{'areas': [a['id'], b['id']], 'allowed': False,
                         'reason': 'awaiting_engine_los'}
                        for i,a in enumerate(spawns) for b in spawns[i+1:]],
        'extraction_areas': [
            {'id': 'extract_west', 'name': 'Служебный выход', 'zone': 'maintenance',
             'area': area([4, 52, 9, 57]), 'approach': [10, 53, 0], 'runtime_enabled': False},
            {'id': 'extract_east', 'name': 'Ворота отгрузки', 'zone': 'dispatch',
             'area': area([63, 52, 68, 57]), 'approach': [61, 54, 0], 'runtime_enabled': False}],
        'pois': pois, 'loot_candidates': [
            {'id': f'loot_{i:03}', 'position': [x, y, 0], 'furniture': furniture[g[y][x]],
             'interaction_from': next(([xx, yy, 0] for xx, yy in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
                                       if g[yy][xx] in '.,ac'), None)}
            for i, (x, y) in enumerate([(4, 25), (4, 28), (7, 43), (54, 43), (53, 9), (53, 27), (65, 29)], 1)],
        'doors': [{'position': [x, y, 0], 'terrain': 't_door_c', 'locked': False}
                  for y in range(72) for x in range(72) if g[y][x] == '+'],
        'lighting': [{'position': [x,y,0], 'furniture': 'f_olight_nogrid',
                      'power': 'no_grid', 'runtime_verified': False} for x,y in lamps],
        'cover': [{'id': 'concrete_piers', 'terrain': 't_concrete_wall',
                   'areas': [area([x,y,x+2,y+4]) for x,y in [(34,15),(43,25),(34,43),(43,53)]],
                   'blocks_movement': True, 'blocks_los': True, 'bullet_proof': 'unverified'},
                  {'id': 'racks', 'furniture': 'f_rack', 'blocks_movement': True,
                   'blocks_los': False, 'bullet_proof': False}],
        'runtime_status': 'not_integrated'}
    # Conservative static screening lives in the independent checker; initially all pairs denied.
    save(OUT / 'manifest.json', manifest)


if __name__ == '__main__':
    build()
