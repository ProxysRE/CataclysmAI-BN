"""Reconstruct all Factory floor grids and audit source-supported stair candidates.

Does not alter mapgen or create runtime stairs. Shared SVG symbols are evidence
of a stairwell, not proof that every apparent intermediate landing is usable.
"""
from collections import deque
import hashlib
import itertools
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from inspect_factory_reference import (SOURCE, SOURCE_DIGEST, OUT, LAYERS, SVG, XLINK,
                                       filtered, render, rasterize, write)
import json

CELL = .5


def component_map(rows):
    """Standing cells only; unmapped regions and obstacles never become routes."""
    h, w = len(rows), len(rows[0])
    labels, sizes = {}, []
    for y in range(h):
        for x in range(w):
            if rows[y][x] not in '.S' or (x,y) in labels:
                continue
            ident = len(sizes)
            pending = deque([(x,y)])
            labels[x,y] = ident
            count = 0
            while pending:
                px,py = pending.popleft()
                count += 1
                for nx,ny in [(px+1,py),(px-1,py),(px,py+1),(px,py-1)]:
                    if 0 <= nx < w and 0 <= ny < h and rows[ny][nx] in '.S' and (nx,ny) not in labels:
                        labels[nx,ny] = ident
                        pending.append((nx,ny))
            sizes.append(count)
    return labels, sizes


def shared_cells(lower, upper, bbox):
    """Only source stair cells whose centers lie inside this exact stair bbox."""
    x,y,w,h = bbox
    result = []
    for cy in range(max(0, math.floor(y/CELL)), min(len(lower), math.ceil((y+h)/CELL))):
        for cx in range(max(0, math.floor(x/CELL)), min(len(lower[0]), math.ceil((x+w)/CELL))):
            px,py = (cx+.5)*CELL, (cy+.5)*CELL
            if x <= px < x+w and y <= py < y+h and lower[cy][cx] == upper[cy][cx] == 'S':
                result.append((cx,cy))
    return result


def source_landings(root):
    records = []
    for layer,z,_ in LAYERS:
        group = next(g for g in root if g.get('id') == layer)
        parents = {child: parent for parent in group.iter() for child in parent}
        for use in group.iter(SVG+'use'):
            parent, direction = parents.get(use), 'unlabeled'
            while parent is not None:
                if parent.get('id','').endswith('-down'):
                    direction = 'down'; break
                if parent.get('id','').endswith('-up'):
                    direction = 'up'; break
                parent = parents.get(parent)
            records.append((use.get(XLINK+'href').lstrip('#'),z,direction))
    return records


def plan(grids, vertical):
    by_z = {g['z']: g['rows'] for g in grids}
    components = {z: component_map(rows) for z,rows in by_z.items()}
    pairs, ambiguous, missing = [], [], []
    reserved = set()
    by_ref = {}
    for landing in vertical['landings']:
        key = (landing['source_ref'], landing['z'])
        entry = by_ref.setdefault(landing['source_ref'], {}).setdefault(
            landing['z'], {**landing, 'directions': set()})
        if max(abs(a-b) for a,b in zip(entry['svg_bbox'], landing['svg_bbox'])) > .001:
            raise ValueError(f'Multiple distinct landings for {key}')
        entry['directions'].add(landing['direction'])
    for ref,landings in sorted(by_ref.items()):
        for lower,upper in itertools.combinations(sorted(landings.values(),key=lambda x:x['z']),2):
            low,high = lower['z'],upper['z']
            if high != low+1:
                if not any(low < other['z'] < high for other in landings.values()):
                    missing.append({'source_ref':ref,'from_z':low,'to_z':high,
                                    'status':'missing_intermediate_landing_do_not_connect'})
                continue
            bbox = lower['svg_bbox']
            if max(abs(a-b) for a,b in zip(bbox,upper['svg_bbox'])) > .001:
                raise ValueError(f'Moved source symbol {ref}; needs manual alignment')
            cells = shared_cells(by_z[low],by_z[high],bbox)
            # Prefer a central common stair cell; never move it through a wall.
            center = ((bbox[0]+bbox[2]/2)/CELL-.5,(bbox[1]+bbox[3]/2)/CELL-.5)
            cells.sort(key=lambda p: ((p[0]-center[0])**2+(p[1]-center[1])**2,p[1],p[0]))
            supported = bool(lower['directions'] & {'up','unlabeled'}) and 'down' in upper['directions']
            available = [p for p in cells if (low,*p) not in reserved and (high,*p) not in reserved] if supported else cells
            selected = available[0] if available else None
            if supported and selected:
                reserved.update([(low,*selected),(high,*selected)])
            record = {'source_ref':ref,'from_z':low,'to_z':high,'svg_bbox':bbox,
                      'lower_directions':sorted(lower['directions']),'upper_directions':sorted(upper['directions']),
                      'shared_stair_cells':len(cells),'proposed_position':list(selected) if selected else None,
                      'runtime_enabled':False,
                      'status':'direction_supported_candidate' if supported else 'direction_ambiguous_review'}
            if selected:
                p = selected
                record['component_sizes_at_position'] = [components[z][1][components[z][0][p]] for z in [low,high]]
                record['landing_isolated'] = min(record['component_sizes_at_position']) == 1
                record['horizontal_floor_cells_in_endpoint_components'] = [sum(
                    by_z[z][yy][xx] == '.' for (xx,yy),ident in components[z][0].items()
                    if ident == components[z][0][p]) for z in [low,high]]
                record['requires_intermediate_flight_review'] = min(record['horizontal_floor_cells_in_endpoint_components']) == 0
            else:
                record['status'] = 'no_shared_stair_cell_do_not_connect' if not cells else 'cell_conflict_do_not_connect'
            (pairs if supported else ambiguous).append(record)
    # A conditional component graph shows what verified pairs COULD connect;
    # ambiguous relations are never smuggled into a claim of actual navigation.
    graph = {}
    for z,(_,sizes) in components.items():
        for index in range(len(sizes)):
            graph[z,index] = set()
    for record in pairs:
        if record['proposed_position'] is None:
            continue
        p = tuple(record['proposed_position'])
        a,b = [(z,components[z][0][p]) for z in [record['from_z'],record['to_z']]]
        graph[a].add(b);graph[b].add(a)
    ground_main = max((n for n in graph if n[0] == 0), key=lambda n: components[0][1][n[1]])
    seen,pending = {ground_main},deque([ground_main])
    while pending:
        for node in graph[pending.popleft()]:
            if node not in seen:
                seen.add(node);pending.append(node)
    return {'status':'vertical_construction_plan_not_runtime','source_sha256':SOURCE_DIGEST,
            'svg_units_per_cell':CELL,'automatic_passage_repair':False,
            'direction_supported_candidates':pairs,'direction_ambiguous':ambiguous,
            'missing_intermediate_landings':missing,
            'floors':[{'z':z,'standing_cells':sum(sizes),'component_sizes':sorted(sizes,reverse=True),
                       'conditionally_reachable_cells_from_main_ground':sum(sizes[i] for zz,i in seen if zz==z)}
                      for z,(_,sizes) in sorted(components.items())],
            'warning':'Условная связность учитывает только кандидатов с направлением, не доказывает лестницы BN, двери, прыжки или путь НПС.'}


def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_DIGEST:
        raise ValueError('Factory source differs')
    root = ET.parse(SOURCE).getroot()
    _,_,width,height = map(float,root.get('viewBox').split())
    vertical = json.loads((OUT/'vertical_reference.json').read_text(encoding='utf-8'))
    expected = sorted(source_landings(root))
    recorded = sorted((x['source_ref'],x['z'],x['direction']) for x in vertical['landings'])
    if expected != recorded:
        raise ValueError('Stair references differ from the pinned SVG')
    grids = []
    with tempfile.TemporaryDirectory(prefix='factory-levels-') as temp:
        for layer,z,name in LAYERS:
            masks = {c:render(filtered(root,layer,c),Path(temp)/f'{layer}_{c}.png').getchannel('A')
                     for c in ['floor','solid','wall','stairs','ledge']}
            a = rasterize(masks,width,height,CELL)
            rows = [''.join(row) for row in np.array(list(' .#XS'))[a]]
            grids.append({'source_layer':layer,'name':name,'z':z,'size':[a.shape[1],a.shape[0]],'rows':rows})
    ground = json.loads((OUT/'ground_geometry.json').read_text(encoding='utf-8'))
    if next(g['rows'] for g in grids if g['z'] == 0) != ground['rows']:
        raise ValueError('The new common grid differs from the committed ground draft')
    data = {'status':'source_floor_blueprints_not_runtime','source_sha256':SOURCE_DIGEST,
            'svg_units_per_cell':CELL,'legend':ground['legend'],'floors':grids}
    write(OUT/'floor_blueprints.json',data)
    report = plan(grids,vertical)
    write(OUT/'vertical_plan.json',report)
    preview(grids,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['direction_supported_candidates','direction_ambiguous']},ensure_ascii=False))
    print(f"Supported direction candidates: {len(report['direction_supported_candidates'])}; ambiguous: {len(report['direction_ambiguous'])}")


def preview(grids,report):
    board = Image.new('RGB',(1700,2100),'#131c26')
    draw = ImageDraw.Draw(board)
    font = lambda n: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    draw.text((24,18),'ЗАВОД · общая сетка этажей и кандидаты лестниц',font=font(28),fill='white')
    draw.text((24,62),'0,5 SVG-единицы на клетку · одинаковая привязка всех этажей · переходы ещё не включены',font=font(17),fill='#c1cdd8')
    palette = {' ':(19,28,38),'.':(169,179,182),'#':(74,87,99),'X':(231,218,190),'S':(145,108,50)}
    for index,g in enumerate(grids):
        ox,oy = 24+(index%2)*850,110+(index//2)*930
        draw.text((ox,oy),f"{g['name']} · z={g['z']}",font=font(24),fill='white')
        arr = np.array([[palette[c] for c in r] for r in g['rows']],dtype=np.uint8)
        im = Image.fromarray(arr).resize((792,864),Image.Resampling.NEAREST)
        board.paste(im,(ox,oy+38))
        for collection,color in [('direction_supported_candidates','#49e0a2'),('direction_ambiguous','#ff7ba1')]:
            for r in report[collection]:
                if g['z'] not in [r['from_z'],r['to_z']] or not r['proposed_position']:
                    continue
                x,y = r['proposed_position'];px,py = ox+(x+.5)*3,oy+38+(y+.5)*3
                draw.ellipse((px-5,py-5,px+5,py+5),outline=color,width=2)
    draw.text((24,1990),'Зелёные — направление согласуется. Розовые — направление неоднозначно; требуется сверка.',font=font(18),fill='#d4dee6')
    draw.text((24,2023),'Тёмное — источник не размечен; здесь ещё не назначены стены, перекрытия или открытый воздух.',font=font(17),fill='#c1cdd8')
    draw.text((24,2057),'Производная схемы Shebuka · CC BY-NC-SA 4.0 · план строительства, не скриншот BN',font=font(16),fill='#c1cdd8')
    board.save(OUT/'vertical_plan.png')


if __name__ == '__main__':
    main()
