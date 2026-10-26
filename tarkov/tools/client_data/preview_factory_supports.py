#!/usr/bin/env python3
"""Plot sampled supports; height bands are display groupings, never BN floors."""
import argparse
import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def preview(report,path):
    fig,axes=plt.subplots(3,2,figsize=(13,13),layout='constrained')
    bands={}
    titles={'office':'Офис','laboratory':'Лаборатория'}
    for col,(name,p) in enumerate(report['profiles'].items()):
        hist=collections.Counter(round(n['y'],1) for n in p['nodes'] if n['source']['scene']==p['scene'])
        peaks=[]
        for y,_ in hist.most_common():
            if all(abs(y-old)>1.5 for old in peaks):peaks.append(y)
            if len(peaks)==3:break
        bands[name]=sorted(peaks)
        for row in range(3):
            ax=axes[row,col]
            if row>=len(peaks):ax.set_visible(False);continue
            y=sorted(peaks)[row]
            chosen={i for i,n in enumerate(p['nodes']) if abs(n['y']-y)<=.3}
            seg=[[[p['nodes'][a]['x'],p['nodes'][a]['z']],[p['nodes'][b]['x'],p['nodes'][b]['z']]]
                 for a,b in p['edges'] if a in chosen and b in chosen]
            ax.add_collection(LineCollection(seg,colors='#b3c9ce',linewidths=.5))
            nodes=[p['nodes'][i] for i in sorted(chosen)]
            ax.scatter([n['x'] for n in nodes],[n['z'] for n in nodes],s=2,c='#176b69')
            origin=p['grid_origin_xz'];dims=p['grid_dimensions'];pitch=p['parameters']['pitch']
            ax.set(xlim=[origin[0],origin[0]+dims[0]*pitch],ylim=[origin[1],origin[1]+dims[1]*pitch],
                   xlabel='Unity X',ylabel='Unity Z')
            ax.set_aspect('equal');ax.grid(alpha=.15)
            ax.set_title(f"{titles[name]} · Y≈{y:g} ±0.3\n{len(chosen)} опорных точек модели",fontsize=11)
    params=next(iter(report['profiles'].values()))['parameters']
    fig.suptitle('Завод · опоры и связи в геометрической модели\n'
                 f"Шаг {params['pitch']:g} · корпус {2*params['body_square_half_width']:g}×"
                 f"{2*params['body_square_half_width']:g}×{params['body_height']:g} · предварительные Unity-единицы\n"
                 'Диапазоны высот не назначают этажи BN; игровая проходимость не проверена',fontsize=12)
    fig.savefig(path,dpi=160);plt.close(fig)
    return bands


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Output already exists')
    print(json.dumps(preview(json.loads(a.report.read_text()),a.output)))
