"""Build an isolated ground-floor geometry draft from the pinned Factory SVG.

Unknown source regions are sealed test boundaries, never inferred new rooms.
SVG silhouettes get provisional terrain; this is not a material/ballistics model.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from inspect_factory_reference import SOURCE, SOURCE_DIGEST, OUT, filtered, render, rasterize, write

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'mods/trkv_factory_dev'
CELL = .5
TERRAIN = {' ': 't_rock', '.': 't_thconc_floor', '#': 't_concrete_wall',
           'X': 't_concrete_wall', 'S': 't_thconc_floor'}


def build():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_DIGEST:
        raise ValueError('Factory SVG differs from the pinned source')
    root = ET.parse(SOURCE).getroot()
    _, _, width, height = map(float, root.get('viewBox').split())
    with tempfile.TemporaryDirectory(prefix='factory-mapgen-') as temp:
        masks = {c: render(filtered(root, 'Ground_Floor', c), Path(temp)/f'{c}.png').getchannel('A')
                 for c in ['floor', 'solid', 'wall', 'stairs', 'ledge']}
        grid = rasterize(masks, width, height, CELL)
    chars = np.array(list(' .#XS'))
    rows = [''.join(row) for row in chars[grid]]
    h, w = grid.shape
    MOD.mkdir(parents=True, exist_ok=True)
    tiles, overmap, placements, blocks = [], [], [], []
    for by in range(h//24):
        for bx in range(w//24):
            ident = f'trkv_loc_factory_01_g_{bx}_{by}'
            part = [r[bx*24:(bx+1)*24] for r in rows[by*24:(by+1)*24]]
            used = set(''.join(part))
            tiles.append({'type': 'mapgen', 'om_terrain': [ident], 'method': 'json',
                          'object': {'fill_ter': 't_rock', 'rows': part,
                                     'terrain': {c: TERRAIN[c] for c in sorted(used)}}})
            overmap.append({'type': 'overmap_terrain', 'id': ident,
                            'name': 'Завод: контуры основного этажа', 'sym': 'F',
                            'color': 'light_gray', 'see_cost': 0, 'mondensity': 0,
                            'flags': ['NO_ROTATE']})
            placements.append({'point': [bx, by, 0], 'overmap': ident})
            blocks.append({'terrain_id': ident, 'origin': [bx*24, by*24, 0], 'size': [24, 24]})
    write(MOD/'mapgen.json', tiles)
    write(MOD/'overmap.json', overmap + [{'type': 'overmap_special',
          'id': 'trkv_loc_factory_01_ground_draft', 'overmaps': placements,
          'locations': ['land'], 'occurrences': [0, 0], 'flags': ['CLASSIC']}])
    write(MOD/'modinfo.json', [{'type': 'MOD_INFO', 'id': 'trkv_factory_dev',
          'name': 'Тарков: Завод — геометрический черновик', 'authors': ['ProxysRE'],
          'description': 'Основной этаж по схеме Shebuka. Черновые материалы, без лестниц и рейда.',
          'category': 'content', 'dependencies': ['bn']}])
    write(OUT/'ground_geometry.json', {'status': 'mapgen_ground_geometry_draft',
          'source_sha256': SOURCE_DIGEST, 'source_layer': 'Ground_Floor',
          'svg_units_per_cell': CELL, 'size': [w, h], 'z': 0,
          'legend': {' ': 'unmapped_sealed_test_boundary', '.': 'floor',
                     '#': 'source_silhouette_provisional_solid', 'X': 'source_wall_line',
                     'S': 'stair_reference_floor_without_vertical_transition'},
          'terrain': TERRAIN, 'rows': rows})
    write(OUT/'ground_manifest.json', {'location_id': 'factory_01',
          'stage': 'ground_geometry_draft', 'bn_commit': '554950f3635f50ddd1d32c6e1b6e2bdee9842bd6',
          'mod_id': 'trkv_factory_dev', 'size': [w, h], 'levels': [0],
          'coordinates': {'origin': 'SVG top-left', 'x': 'SVG right', 'y': 'SVG down',
                          'z': 'up', 'geographic_orientation': 'not_established'},
          'source_sha256': SOURCE_DIGEST, 'svg_units_per_cell': CELL,
          'blocks': blocks, 'spawn_areas': [], 'extraction_areas': [],
          'vertical_transitions': [], 'runtime_status': 'not_integrated',
          'adaptations': [
              'Дискретизация 0.5 SVG-единицы на клетку; длина в метрах не установлена.',
              'Неразмеченные области временно закрыты t_rock как граница теста, не стены оригинала.',
              'Силуэты временно заменены t_concrete_wall; материал и LOS не подтверждены.',
              'Графические площадки лестниц остаются полом; вертикальных переходов пока нет.',
              'Проёмы не исправляются автоматически; двери, мебель, свет и содержимое пока не добавлены.'
          ], 'derived_geometry_license': 'CC-BY-NC-SA-4.0', 'source_author': 'Shebuka'})
    image = Image.fromarray(np.array([[19,28,38], [169,179,182], [74,87,99],
                                     [231,218,190], [233,174,66]], dtype=np.uint8)[grid])
    scale = 3
    image = image.resize((w*scale, h*scale), Image.Resampling.NEAREST)
    board = Image.new('RGB', (1160, 1050), '#131c26')
    board.paste(image, (22, 120))
    draw = ImageDraw.Draw(board)
    font = lambda n: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', n)
    draw.text((22, 20), 'ЗАВОД · основной этаж в сетке BN', font=font(27), fill='white')
    draw.text((22, 66), f'{w}×{h} клеток · {len(blocks)} блоков · геометрический черновик',
              font=font(18), fill='#bdcbd5')
    for i, text in enumerate(['Светлое — пол', 'Серое — силуэт', 'Кремовое — стена',
                              'Жёлтое — лестница', '(пока обычный пол)', 'Тёмное — нет данных',
                              'Проёмы без правок', 'Материалы временные', 'Этажи ещё не связаны']):
        draw.text((840, 150+i*37), text, font=font(16), fill='#d9e1e6')
    draw.text((22, 1002), 'По схеме Shebuka · CC BY-NC-SA 4.0 · визуализация JSON, не скриншот BN',
              font=font(17), fill='#bdcbd5')
    board.save(OUT/'ground_mapgen.png')
    print(f'Factory ground draft: {w}x{h}, {len(blocks)} mapgen blocks')


if __name__ == '__main__':
    build()
