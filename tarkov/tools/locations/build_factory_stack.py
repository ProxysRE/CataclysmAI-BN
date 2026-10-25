"""Package the four source floor grids and reviewed geometric stair candidates.

This is an isolated volume draft. Two reviewed workshop regions have air;
remaining unknown cells are sealed test boundaries. Roof, materials and floor
support are not a finished physical model.
"""
import hashlib
import json
from pathlib import Path

from check_factory import OUT
from factory_volumes import air_candidates
SOURCE = OUT/'reference/Factory.svg'
SOURCE_DIGEST = 'c8e576ca7974e086b78151f9bff532b5a99b2fc4a130b080e5be030236bc07bd'

def write(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT/'mods/trkv_factory_stack_dev'
TERRAIN = {' ': 't_rock', '.': 't_thconc_floor', '#': 't_concrete_wall',
           'X': 't_concrete_wall', 'S': 't_thconc_floor',
           '<': 't_stairs_up', '>': 't_stairs_down_no_roof', '~': 't_open_air'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def construct(blueprints, vertical, volumes=None):
    if blueprints['source_sha256'] != SOURCE_DIGEST or blueprints['svg_units_per_cell'] != .5:
        raise ValueError('Unexpected source or scale')
    if vertical['source_sha256'] != SOURCE_DIGEST or vertical['svg_units_per_cell'] != .5:
        raise ValueError('Vertical plan source or scale differs')
    computed = vertical
    grids = {f['z']: [list(row) for row in f['rows']] for f in blueprints['floors']}
    transitions = []
    for candidate in computed['direction_supported_candidates']:
        if candidate['status'] != 'direction_supported_candidate' or candidate['requires_intermediate_flight_review']:
            continue
        x,y = candidate['proposed_position']
        lo,hi = candidate['from_z'],candidate['to_z']
        if grids[lo][y][x] != 'S' or grids[hi][y][x] != 'S':
            raise ValueError('Stair placement would overwrite another object')
        grids[lo][y][x],grids[hi][y][x] = '<','>'
        transitions.append({'id':candidate['source_ref']+f'_{lo}_{hi}',
                            'source_ref':candidate['source_ref'], 'from':[x,y,lo], 'to':[x,y,hi],
                            'evidence':'shared_source_symbol_direction_and_horizontal_approach',
                            'actor_traversal_verified':False})
    if volumes is not None:
        for x,y,z in air_candidates(blueprints,volumes):
            if grids[z][y][x] != ' ':
                raise ValueError('Volume inference would overwrite geometry')
            grids[z][y][x] = '~'
    return {z:[''.join(row) for row in rows] for z,rows in grids.items()},transitions


def build():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_DIGEST:
        raise ValueError('Factory SVG differs')
    blueprints = load(OUT/'floor_blueprints.json')
    vertical = load(OUT/'vertical_plan.json')
    volumes = load(OUT/'volume_rules.json')
    grids,transitions = construct(blueprints,vertical,volumes)
    w,h = blueprints['floors'][0]['size']
    tiles,overmap,placements,blocks = [],[],[],[]
    for layer_index,(z,rows) in enumerate(sorted(grids.items())):
        for by in range(h//24):
            for bx in range(w//24):
                ident = f'trkv_loc_factory_stack_{layer_index}_{bx}_{by}'
                part = [r[bx*24:(bx+1)*24] for r in rows[by*24:(by+1)*24]]
                used = set(''.join(part))
                tiles.append({'type':'mapgen','om_terrain':[ident],'method':'json',
                              'object':{'fill_ter':'t_rock','rows':part,
                                        'terrain':{c:TERRAIN[c] for c in sorted(used)}}})
                overmap.append({'type':'overmap_terrain','id':ident,'name':'Завод: многоэтажный макет',
                                'sym':'F','color':'light_gray','see_cost':0,'mondensity':0,'flags':['NO_ROTATE']})
                placements.append({'point':[bx,by,z],'overmap':ident})
                blocks.append({'terrain_id':ident,'origin':[bx*24,by*24,z],'size':[24,24]})
    MOD.mkdir(parents=True,exist_ok=True)
    write(MOD/'mapgen.json',tiles)
    write(MOD/'overmap.json',overmap+[{'type':'overmap_special','id':'trkv_loc_factory_stack_draft',
          'overmaps':placements,'locations':['land'],'occurrences':[0,0],'flags':['CLASSIC']}])
    write(MOD/'modinfo.json',[{'type':'MOD_INFO','id':'trkv_factory_stack_dev',
          'name':'Тарков: Завод — многоэтажный макет','authors':['ProxysRE'],
          'description':'Четыре уровня, парные лестницы и черновые объёмы цехов. Изолированный макет, без рейда.',
          'category':'content','dependencies':['bn']}])
    write(MOD/'world_types.json',[{'type':'world_type','id':'trkv_factory_probe',
          'name':'Завод: проверка перемещения',
          'description':'Неограниченное тестовое измерение конструктора, не рейд проекта.',
          'region_settings':'default','infinite_bounds':True,'save_prefix':'trkv_factory_probe_',
          'allow_npc_travel':False,'allow_vehicle_travel':False}])
    write(OUT/'stack_geometry.json',{'status':'four_level_workshop_volume_draft','source_sha256':SOURCE_DIGEST,
          'svg_units_per_cell':.5,'terrain':TERRAIN,
          'floors':[{'z':z,'size':[w,h],'rows':rows} for z,rows in sorted(grids.items())]})
    write(OUT/'stack_manifest.json',{'location_id':'factory_01','stage':'four_level_workshop_volume_draft',
          'bn_commit':'554950f3635f50ddd1d32c6e1b6e2bdee9842bd6','mod_id':'trkv_factory_stack_dev',
          'source_sha256':SOURCE_DIGEST,'size':[w,h],'levels':sorted(grids),'blocks':blocks,
          'vertical_transitions':transitions,'spawn_areas':[],'extraction_areas':[],
          'runtime_status':'not_integrated','automatic_passage_repair':False,
          'open_air_cells':sum(row.count('~') for rows in grids.values() for row in rows),
          'volume_rules':'volume_rules.json',
          'adaptations':[
              'Неразмеченные клетки вне принятых цеховых объёмов закрыты t_rock как тестовая граница.',
              'Силуэты пока бетонные: материалы и прострелы не определены.',
              'Лестничный пролёт сжимается в одну парную клетку внутри общей исходной области.',
              'Лестничные обозначения без принятой пары остаются полом, без вертикального перехода.',
              'Воздух задан только в двух цеховых зонах по правилам volume_rules.json; крыша, падение и опора мостков не проверены.',
              'Семь кандидатов без примыкающего пола и десять неоднозначных связей не установлены.'
          ],'source_author':'Shebuka','derived_geometry_license':'CC-BY-NC-SA-4.0'})
    print(f'Factory stack: {len(tiles)} blocks, {len(transitions)} paired stairs')


if __name__=='__main__':
    build()
