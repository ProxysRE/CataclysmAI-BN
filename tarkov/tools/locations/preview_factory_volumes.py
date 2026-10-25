"""Render exact upper-floor JSON classes; no inferred perspective geometry."""
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from build_factory_stack import OUT,load


def main():
    geometry=load(OUT/'stack_geometry.json')
    colors={' ':(19,28,38),'.':(179,188,190),'#':(70,81,92),'X':(231,218,190),
            'S':(145,108,50),'<':(65,220,150),'>':(255,144,75),'~':(28,85,111)}
    board=Image.new('RGB',(1510,1130),'#131c26');draw=ImageDraw.Draw(board)
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    draw.text((24,18),'ЗАВОД · объёмы вокруг верхних мостков',font=font(28),fill='white')
    draw.text((24,64),'Два выбранных цеха · исходные полы и контуры сохранены · крыша пока не задана',font=font(17),fill='#c1cdd8')
    for index,z in enumerate([1,2]):
        floor=next(f for f in geometry['floors'] if f['z']==z)
        ox,oy=24+index*750,120
        draw.text((ox,oy),f'Уровень z={z}',font=font(23),fill='white')
        arr=np.array([[colors[c] for c in row] for row in floor['rows']],dtype=np.uint8)
        # Uniform scaling of the full shared extent, including padding.
        im=Image.fromarray(arr).resize((660,720),Image.Resampling.NEAREST)
        board.paste(im,(ox,oy+44))
        count=Counter(''.join(floor['rows']))
        draw.text((ox,oy+790),f'Воздух без пола: {count["~"]:,} клеток'.replace(',',' '),font=font(18),fill='#c1ddeb')
    for i,(c,label) in enumerate([('~','Воздух: NO_FLOOR'),('.','Пол / мостки'),('S','Лестничный символ'),(' ','Пока закрыто')]):
        x=24+i*370
        draw.rectangle((x,1000,x+22,1022),fill=colors[c],outline='#c1cdd8')
        draw.text((x+32,998),label,font=font(16),fill='#dce6ec')
    draw.text((24,1046),'Схема из JSON, не скриншот BN. Воздух не включён в граф обычной ходьбы.',font=font(18),fill='#dce6ec')
    draw.text((24,1088),'Геометрия по Shebuka · CC BY-NC-SA 4.0 · зоны сверены визуально с картой re3mr 1.7C',font=font(16),fill='#c1cdd8')
    board.save(OUT/'workshop_volumes.png')


if __name__=='__main__':main()
