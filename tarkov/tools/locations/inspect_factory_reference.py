"""Inspect pinned Shebuka SVG layers and audit candidate BN rasterizations.

Requires Inkscape CLI, Pillow and NumPy. Never invents passages or runtime stairs.
Output is a reconstruction study, not production BN mapgen.
"""
from collections import Counter, deque
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'locations/factory_01'
SOURCE=OUT/'reference/Factory.svg'
SVG='{http://www.w3.org/2000/svg}'
XLINK='{http://www.w3.org/1999/xlink}'
LAYERS=[('Basement',-1,'Подземная часть'),('Ground_Floor',0,'Основной этаж'),
        ('Second_Floor',1,'Второй этаж'),('Third_Floor',2,'Третий этаж')]
SOURCE_SHA='5a8b6115d1c0cf56f2ebaac1a96fa5ae3074d178'
FILE_SHA='81177ae3aa7757665548f6cb20cdbfb38929f738'
SOURCE_DIGEST='c8e576ca7974e086b78151f9bff532b5a99b2fc4a130b080e5be030236bc07bd'
COLORS=np.array([[21,30,40],[168,177,181],[61,78,90],[31,42,53],[226,183,70]],dtype=np.uint8)
RU={'Office Building':'Офисный блок','Main Office':'Главный офис','Breach Room':'Комната под выбивание',
    'Locked Office':'Закрытый офис','North Stairs':'Северная лестница','South Stairs':'Южная лестница',
    'Sky Bridge':'Верхний переход','Connector':'Соединительный проход','Locker Rooms':'Раздевалки',
    'Sinks':'Умывальники','Hole':'Пролом','Platform':'Платформа','Servers':'Серверная',
    'Med Tent':'Медицинская палатка','Silos':'Силосы','Heli Crash':'Разбитый вертолёт',
    'Pit':'Яма','Underground Stash':'Подземный тайник','Scav Bunker':'Бункер Диких',
    'Blue Containers':'Синие контейнеры','Wood Room':'Помещение с древесиной',
    'Glass Hall':'Стеклянный коридор','Boilers':'Котлы','Pumping Station':'Насосная',
    'East Halls':'Восточные цеха','Forklifts':'Погрузчики','Rafters':'Верхние балки'}


def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def filtered(root,layer,category=None):
    r=deepcopy(root)
    for child in list(r):
        if child.tag==SVG+'g' and child.get('id')!=layer:
            r.remove(child)
    group=next(e for e in r if e.tag==SVG+'g')
    group.set('class','')  # Drop presentation-only shadows; retain geometry.
    if category:
        for child in list(group):
            classes=set(child.get('class','').split())
            keep={'floor':'floor' in classes,
                  'solid':'building' in classes and 'wall' not in classes,
                  'wall':'wall' in classes,
                  'stairs':'stairs' in classes,
                  'ledge':'cement' in classes}[category]
            if not keep:
                group.remove(child)
        style=ET.SubElement(r,SVG+'style')
        style.text='path,use {fill:#fff!important;stroke:none!important;} .shadow {filter:none!important;}'
        if category=='wall':
            style.text='path,use {fill:none!important;stroke:#fff!important;stroke-width:.2!important;} .shadow {filter:none!important;}'
    return r


def render(root,path,width=1308):
    svg=path.with_suffix('.svg')
    ET.ElementTree(root).write(svg,encoding='utf-8',xml_declaration=True)
    subprocess.run(['inkscape',str(svg),'--export-type=png',f'--export-filename={path}',
                    f'--export-width={width}'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return Image.open(path).convert('RGBA')


def components(walkable):
    h,w=walkable.shape
    unseen=set(zip(*np.nonzero(walkable)))
    sizes=[]
    while unseen:
        seed=unseen.pop()
        q=deque([seed]); count=0
        while q:
            y,x=q.popleft(); count+=1
            for n in [(y+1,x),(y-1,x),(y,x+1),(y,x-1)]:
                if n in unseen:
                    unseen.remove(n); q.append(n)
        sizes.append(count)
    return sorted(sizes,reverse=True)


def world_to_svg(position,metadata,width,height):
    """Port of the source application's rotation/CRS and SVG overlay bounds.

    Bounds contain game [x,z], not SVG corners. The default SVG aspect-ratio
    alignment is xMidYMid meet. Never interpret the page's pixel coordinates
    directly as BN cells.
    """
    angle=math.radians(metadata['coordinateRotation'])
    sx,tx,sy,ty=metadata['transform']
    def project(x,z):
        return (sx*(x*math.cos(angle)-z*math.sin(angle))+tx,
                -sy*(x*math.sin(angle)+z*math.cos(angle))+ty)
    bounds=metadata['bounds']
    corners=[project(x,z) for x in [bounds[0][0],bounds[1][0]]
                          for z in [bounds[0][1],bounds[1][1]]]
    x0,y0=min(p[0] for p in corners),min(p[1] for p in corners)
    bw=max(p[0] for p in corners)-x0
    bh=max(p[1] for p in corners)-y0
    scale=min(bw/width,bh/height)
    pad_x,pad_y=(bw-width*scale)/2,(bh-height*scale)/2
    px,py=project(*position)
    return [(px-x0-pad_x)/scale,(py-y0-pad_y)/scale]


def rasterize(masks,width,height,cell):
    # Integrate alpha over exact source-space cells. Resizing the whole image
    # to ceil(width/cell) would silently stretch geometry and shift far edges.
    gw,gh=math.ceil(width/cell),math.ceil(height/cell)
    values={k:coverage(im,width,height,cell,gw,gh) for k,im in masks.items()}
    a=np.zeros((gh,gw),dtype=np.uint8)
    a[(values['floor']>=.35)|(values['ledge']>=.35)]=1
    a[values['solid']>=.20]=2
    # Thin drawn walls need any substantive hit; majority sampling loses them.
    a[values['wall']>=.025]=3
    stair=(values['stairs']>=.20)&(a!=2)&(a!=3)
    a[stair]=4
    padded=np.zeros((math.ceil(gh/24)*24,math.ceil(gw/24)*24),dtype=np.uint8)
    padded[:gh,:gw]=a
    return padded


def coverage(im,width,height,cell,gw,gh):
    arr=np.asarray(im,dtype=np.float64)/255
    ih,iw=arr.shape
    integral=np.pad(arr.cumsum(axis=0).cumsum(axis=1),((1,0),(1,0)))
    xe=np.clip(np.arange(gw+1)*cell/width*iw,0,iw)
    ye=np.clip(np.arange(gh+1)*cell/height*ih,0,ih)
    xi,yi=np.floor(xe).astype(int),np.floor(ye).astype(int)
    xn,yn=np.minimum(xi+1,iw),np.minimum(yi+1,ih)
    xf,yf=xe-xi,ye-yi
    cumulative=(integral[np.ix_(yi,xi)]*(1-yf[:,None])*(1-xf[None,:])
                +integral[np.ix_(yn,xi)]*yf[:,None]*(1-xf[None,:])
                +integral[np.ix_(yi,xn)]*(1-yf[:,None])*xf[None,:]
                +integral[np.ix_(yn,xn)]*yf[:,None]*xf[None,:])
    area=(cell/width*iw)*(cell/height*ih)
    return (cumulative[1:,1:]-cumulative[:-1,1:]-cumulative[1:,:-1]+cumulative[:-1,:-1])/area


def inspect():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_DIGEST:
        raise ValueError('SVG differs from the pinned source; update provenance explicitly')
    root=ET.parse(SOURCE).getroot()
    _,_,width,height=map(float,root.get('viewBox').split())
    source_lock={'source_url':f'https://github.com/the-hideout/tarkov-dev-svg-maps/blob/{SOURCE_SHA}/Factory.svg',
        'repository_commit':SOURCE_SHA,'file_last_commit':FILE_SHA,'file_last_changed':'2024-11-07',
        'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'author':'Shebuka',
        'license':'CC-BY-NC-SA-4.0','retrieved':'2026-10-25',
        'game_patch':'not_declared_by_svg', 'viewbox':[0,0,width,height],
        'orientation':'SVG x-right/y-down; geographic north not established',
        'source_unit_to_meters':'not_calibrated',
        'limits':['Это снимок исходной схемы, не гарантия актуальности всех участков игры на 25.10.2026',
                  'Полноту дворов и дверей проверяем по изображениям; наружные участки добавлены уже в 0.15 (2024)',
                  'Силуэты не определяют материал, прозрачность и пулестойкость объектов']}
    write(OUT/'source_lock.json',source_lock)
    audit={'status':'reference_study_not_runtime','renderer':{
        'inkscape':subprocess.check_output(['inkscape','--version'],text=True).strip(),
        'pillow':PIL.__version__,'numpy':np.__version__},'sampling':{
        'floor_or_ledge_area_fraction':.35,'solid_area_fraction':.20,'wall_area_fraction':.025,
        'stairs_area_fraction':.20,'neighbors':4,'automatic_passage_repair':False,
        'integration':'exact source-space cell rectangles over raster alpha; outside source is zero'},'layers':[]}
    previews=[]; ground_candidate=None; stairs=[]
    metadata=json.loads((OUT/'reference/tarkov_dev_metadata.json').read_text(encoding='utf-8'))['map']
    with tempfile.TemporaryDirectory(prefix='factory-reference-') as temp:
        temp=Path(temp)
        # Give uses stable names so Inkscape reports exact source-space bounds.
        query=deepcopy(root)
        for layer,z,name in LAYERS:
            group=next(g for g in query if g.get('id')==layer)
            parents={c:p for p in group.iter() for c in p}
            for i,use in enumerate(group.iter(SVG+'use')):
                ident=f'landing_{layer}_{i}'
                use.set('id',ident)
                direction='unlabeled'
                p=parents.get(use)
                while p is not None:
                    gid=p.get('id','')
                    if gid.endswith('-down'): direction='down'; break
                    if gid.endswith('-up'): direction='up'; break
                    p=parents.get(p)
                stairs.append({'source_ref':use.get(XLINK+'href').lstrip('#'),'layer':layer,
                               'z':z,'direction':direction,'query_id':ident})
        query_path=temp/'query.svg'
        ET.ElementTree(query).write(query_path,encoding='utf-8',xml_declaration=True)
        result=subprocess.run(['inkscape',str(query_path),'--query-all'],check=True,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        bounds={r[0]:list(map(float,r[1:])) for r in csv.reader(io.StringIO(result.stdout)) if len(r)==5}
        for s in stairs:
            s['svg_bbox']=bounds[s.pop('query_id')]
        for layer,z,name in LAYERS:
            image=render(filtered(root,layer),temp/f'{layer}.png')
            previews.append((name,z,image))
            masks={c:render(filtered(root,layer,c),temp/f'{layer}_{c}.png').getchannel('A')
                   for c in ['floor','solid','wall','stairs','ledge']}
            records=[]
            for cell in [1.0,.75,.5]:
                a=rasterize(masks,width,height,cell)
                sizes=components((a==1)|(a==4))
                records.append({'svg_units_per_cell':cell,'size':[a.shape[1],a.shape[0]],
                    'blocks_24x24':a.shape[0]*a.shape[1]//576,
                    'walkable_cells':sum(sizes),'components':len(sizes),
                    'largest_components':sizes[:12], 'cells_by_class':dict(Counter(map(int,a.flat)))})
                if cell==1.0:
                    chars=np.array(list(' .#XS'))
                    write(OUT/f'candidate_{layer}.json',{'status':'analysis_only','layer':layer,'z':z,
                        'units_per_cell':cell,'size':[a.shape[1],a.shape[0]],
                        'legend':{' ':'не размечено источником','.':'площадка','#':'силуэт препятствия',
                                  'X':'линия стены','S':'графическая область лестницы, не runtime-переход'},
                        'rows':[''.join(row) for row in chars[a]]})
                    if z==0: ground_candidate=Image.fromarray(COLORS[a])
            audit['layers'].append({'layer':layer,'z':z,'name':name,'scales':records})
    write(OUT/'raster_audit.json',audit)
    landmarks=[]
    for label in metadata['labels']:
        landmarks.append({'name':RU[label['text']],'source_name':label['text'],
                          'source_position':label['position'],'svg_position':world_to_svg(label['position'],metadata,width,height),
                          'height_range':[label.get('bottom',-10000),label.get('top',10000)],
                          'status':'reference_label_not_runtime_poi'})
    registration=[]
    for name,ref in [('North Stairs','stair-127'),('South Stairs','stair-128')]:
        p=next(x['svg_position'] for x in landmarks if x['source_name']==name)
        x,y,w,h=next(s['svg_bbox'] for s in stairs if s['source_ref']==ref)
        ok=x<=p[0]<=x+w and y<=p[1]<=y+h
        assert ok, f'Landmark registration failed: {name}'
        registration.append({'source_name':name,'source_ref':ref,'inside_reference_stair_bbox':ok})
    write(OUT/'landmarks.json',{'coordinates':'SVG source units, not BN cells','landmarks':landmarks,
                               'registration_checks':registration,
                               'transform_source':'https://github.com/the-hideout/tarkov-dev/blob/main/src/pages/map/index.jsx'})
    transitions=[]
    for lower in stairs:
        if lower['direction']=='down': continue
        for upper in stairs:
            if upper['z']!=lower['z']+1 or upper['direction']!='down': continue
            if upper['source_ref']!=lower['source_ref']: continue
            transitions.append({'source_ref':lower['source_ref'],'from_z':lower['z'],'to_z':upper['z'],
                                'svg_bbox':lower['svg_bbox'],'status':'candidate_from_svg_not_runtime',
                                'lower_direction_inferred':lower['direction']=='unlabeled'})
    paired_keys={(t['source_ref'],t['from_z'],t['to_z']) for t in transitions}
    ambiguous={}
    for a in stairs:
        for b in stairs:
            key=(a['source_ref'],a['z'],b['z'])
            if b['z']==a['z']+1 and b['source_ref']==a['source_ref'] and key not in paired_keys:
                ambiguous[key]={'source_ref':a['source_ref'],'from_z':a['z'],'to_z':b['z'],
                                'lower_direction':a['direction'],'upper_direction':b['direction'],
                                'status':'shared_geometry_direction_needs_review'}
    used={(t['source_ref'],t['from_z']) for t in transitions}|{(t['source_ref'],t['to_z']) for t in transitions}
    unpaired=[s for s in stairs if (s['source_ref'],s['z']) not in used]
    write(OUT/'vertical_reference.json',{'status':'reference_only','landings':stairs,
        'adjacent_level_candidates':transitions,'ambiguous_shared_adjacent':list(ambiguous.values()),
        'unpaired_or_multispan':unpaired,
        'warning':'Общий SVG ID подтверждает графическую связь; лестницы, шахты и промежуточные площадки требуют сверки в игре.'})
    make_boards(previews,ground_candidate,landmarks)
    print(json.dumps({'source_sha256':source_lock['sha256'],'adjacent_candidates':len(transitions),
                      'unpaired_or_multispan':len(unpaired), 'layers':audit['layers']},ensure_ascii=False))


def make_boards(previews,candidate,landmarks):
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=lambda n:ImageFont.truetype(fontpath,n)
    board=Image.new('RGB',(1600,1900),'#15202b'); d=ImageDraw.Draw(board)
    d.text((24,16),'ЗАВОД · послойный референс',font=font(30),fill='white')
    d.text((24,58),'Shebuka · SVG редакции 07.11.2024 · актуальность поздних изменений проверяется',font=font(17),fill='#c0ceda')
    for i,(name,z,im) in enumerate(previews):
        x,y=20+(i%2)*800,100+(i//2)*860
        d.text((x,y),f'{name} · будущий z={z}',font=font(23),fill='#e2e7eb')
        thumbnail=im.copy();thumbnail.thumbnail((750,790))
        board.paste(thumbnail,(x,y+42),thumbnail)
    d.text((24,1842),'Источник: the-hideout/tarkov-dev-svg-maps · CC BY-NC-SA 4.0 · географический север не установлен',font=font(15),fill='#c0ceda')
    board.save(OUT/'reference_floors.png')
    main=Image.new('RGB',(1600,1100),'#15202b');d=ImageDraw.Draw(main)
    d.text((24,18),'ЗАВОД · пробная дискретизация основного этажа',font=font(28),fill='white')
    d.text((24,60),'Слева — исходные контуры. Справа — кандидат сетки 144×144 при 1 SVG-единице на клетку.',font=font(16),fill='#c0ceda')
    original=previews[1][2].copy();original.thumbnail((750,1650))
    main.paste(original,(20,120),original)
    raw=candidate.resize((candidate.width*5,candidate.height*5),Image.Resampling.NEAREST)
    main.paste(raw,(820,120))
    d.text((24,950),'Это исследование масштаба: материал препятствий, двери и переходы ещё не определены.',font=font(18),fill='#e2e7eb')
    d.text((24,986),'Пустые области означают отсутствие разметки источника; они не объявлены стеной или пропастью.',font=font(16),fill='#c0ceda')
    d.text((24,1020),'Тонкие стены и мостки требуют проверки: автоматического добавления проходов нет.',font=font(16),fill='#c0ceda')
    d.text((24,1060),'Производная от схемы Shebuka · CC BY-NC-SA 4.0 · не изображение игры BN',font=font(16),fill='#c0ceda')
    main.save(OUT/'ground_grid_study.png')
    labels=Image.new('RGB',(1730,1540),'#15202b');d=ImageDraw.Draw(labels)
    d.text((24,16),'ЗАВОД · опорные ориентиры основного этажа',font=font(28),fill='white')
    d.text((24,58),'Размещение подписей восстановлено из преобразований координат tarkov.dev',font=font(17),fill='#c0ceda')
    image=previews[1][2]
    labels.paste(image,(20,95),image)
    ground=[p for p in landmarks if p['height_range'][0]<3 and p['height_range'][1]>-1]
    for i,p in enumerate(ground,1):
        x,y=p['svg_position']; x,y=20+x*image.width/130.81831,95+y*image.height/141.23242
        d.ellipse((x-14,y-14,x+14,y+14),fill='#176a8a',outline='white',width=2)
        d.text((x,y),str(i),anchor='mm',font=font(14),fill='white')
        d.text((1350,110+i*39),f'{i:02}  {p["name"]}',font=font(14),fill='#e2e7eb')
    d.text((24,1500),'Shebuka · CC BY-NC-SA 4.0 · ориентиры не являются готовыми маркерами игрового процесса',font=font(16),fill='#c0ceda')
    labels.save(OUT/'ground_landmarks.png')


if __name__=='__main__':
    inspect()
