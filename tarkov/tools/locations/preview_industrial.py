"""Exact cell preview of generated JSON, not an in-game screenshot. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from check_industrial import grid, LOCATION


def render():
    m, cells = grid()
    scale, ox, oy = 16, 42, 86
    im = Image.new('RGB', (1510, 1290), '#111923')
    d = ImageDraw.Draw(im)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    def font(size):
        return ImageFont.truetype(font_path, size)
    title, normal, small = font(27), font(18), font(13)
    d.text((ox, 19), 'ПРОМЫШЛЕННЫЙ УЗЕЛ · макет 0.1', font=title, fill='#edf1f5')
    d.text((ox, 54), '72 × 72 клетки · z = 0 · север сверху · превью JSON, не снимок игры', font=normal, fill='#a8b4c3')
    colors = {'t_concrete_wall': '#344555', 't_thconc_floor': '#b4b1a5',
              't_pavement': '#687779', 't_door_c': '#bd7b3e'}
    fcolors = {'f_rack':'#597278','f_locker':'#556a98','f_counter':'#927853','f_olight_nogrid':'#f8e2a0'}
    for (x,y), (tid,fid) in cells.items():
        xx, yy = ox+x*scale, oy+y*scale
        d.rectangle((xx,yy,xx+scale-1,yy+scale-1), fill=colors[tid])
        if fid:
            if fid == 'f_olight_nogrid':
                d.ellipse((xx+5,yy+5,xx+11,yy+11), fill=fcolors[fid], outline='#6b511a')
            else:
                d.rectangle((xx+2,yy+2,xx+13,yy+13), fill=fcolors[fid], outline='#364247')
    for v in [0,24,48,72]:
        d.line((ox+v*scale,oy,ox+v*scale,oy+72*scale), fill='#798c9b', width=1)
        d.line((ox,oy+v*scale,ox+72*scale,oy+v*scale), fill='#798c9b', width=1)
        if v < 72:
            d.text((ox+v*scale+3,oy+3), str(v), font=small, fill='#fafafa', stroke_width=1, stroke_fill='#152432')
    # Labels are numbered to preserve legibility of the actual cell layout.
    for i,z in enumerate(m['zones'],1):
        lo, hi = z['area']['min'], z['area']['max']
        x = ox + (lo[0]+hi[0])*scale/2
        y = oy + (lo[1]+hi[1])*scale/2
        d.rounded_rectangle((x-15,y-12,x+15,y+12), radius=4, fill='#14222d')
        d.text((x,y), str(i), anchor='mm', font=normal, fill='white')
    for i,s in enumerate(m['spawn_areas'],1):
        x,y,_ = s['primary'][0]
        x,y = ox+x*scale+8,oy+y*scale+8
        d.ellipse((x-13,y-13,x+13,y+13),fill='#2c8bb0',outline='white',width=2)
        d.text((x,y), str(i),anchor='mm',font=small,fill='white')
    for e in m['extraction_areas']:
        lo,hi=e['area']['min'],e['area']['max']
        d.rectangle((ox+lo[0]*scale,oy+lo[1]*scale,ox+hi[0]*scale,oy+hi[1]*scale),outline='#147449',width=4)
        d.text((ox+lo[0]*scale+5,oy+lo[1]*scale+5),'Э',font=normal,fill='#083d26')
    for p in m['pois']:
        x,y,_=p['position']
        x,y=ox+x*scale+8,oy+y*scale+8
        d.polygon([(x,y-6),(x+6,y),(x,y+6),(x-6,y)],fill='#b84945',outline='#fff0de')
    lx, ly = 1230, 100
    d.text((lx,ly),'ЗОНЫ',font=normal,fill='#edf1f5')
    for i,z in enumerate(m['zones'],1):
        d.text((lx,ly+38+i*32),f'{i:02}  {z["name"]}',font=small,fill='#dde3e7')
    for i,line in enumerate(['Синий круг — входная группа', 'Зелёная рамка — будущий выход',
                              'Красный ромб — место интереса', 'Светлая точка — лампа BN',
                              'Линии 24/48 — стыки блоков', '',
                              'Связность проверена статически.', 'Генерация, свет и бой в BN',
                              'ещё не проверены.']):
        d.text((lx,600+i*26),line,font=small,fill='#b6c4ce')
    im.save(LOCATION/'overview.png')
    # Export enlarged junctions directly from the same drawing.
    for name,box in [('crossing_detail',(18,28,54,42)),('sorting_detail',(48,22,70,40))]:
        x0,y0,x1,y1=box
        crop=im.crop((ox+x0*scale,oy+y0*scale,ox+x1*scale,oy+y1*scale))
        crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST).save(LOCATION/f'{name}.png')
    print(LOCATION/'overview.png')


if __name__=='__main__':
    render()
