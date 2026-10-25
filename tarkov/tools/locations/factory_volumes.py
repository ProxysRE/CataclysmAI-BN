"""Conservative, explicit volume inference within visually reviewed workshop zones."""
import math


def air_candidates(blueprints, rules):
    if rules['source_sha256'] != blueprints['source_sha256']:
        raise ValueError('Volume rules source differs')
    if rules['svg_units_per_cell'] != blueprints['svg_units_per_cell']:
        raise ValueError('Volume rules scale differs')
    if rules['target_z'] != [1,2]:
        raise ValueError('Volume inference is restricted to upper levels')
    guard = rules['guard_cells']
    if not isinstance(guard,int) or guard < 2:
        raise ValueError('Insufficient obstacle/flight guard')
    grids = {f['z']:f['rows'] for f in blueprints['floors']}
    h,w = len(grids[0]),len(grids[0][0])
    if set(grids) != {-1,0,1,2} or any(len(g)!=h or any(len(row)!=w for row in g) for g in grids.values()):
        raise ValueError('Floor grids must have one shared extent')
    cell = rules['svg_units_per_cell']
    protected = set()
    for y in range(h):
        for x in range(w):
            if grids[0][y][x] in '#XS' or any(grids[z][y][x]=='S' for z in [1,2]):
                for yy in range(max(0,y-guard),min(h,y+guard+1)):
                    for xx in range(max(0,x-guard),min(w,x+guard+1)):
                        protected.add((xx,yy))
    result = {}
    for zone in rules['zones']:
        x0,y0,x1,y1 = zone['svg_bounds']
        if not (0<=x0<x1<=w*cell and 0<=y0<y1<=h*cell):
            raise ValueError('Volume zone outside source grid')
        for y in range(math.floor(y0/cell),math.ceil(y1/cell)):
            for x in range(math.floor(x0/cell),math.ceil(x1/cell)):
                if not (x0<=(x+.5)*cell<x1 and y0<=(y+.5)*cell<y1):continue
                if grids[0][y][x]!='.' or (x,y) in protected:continue
                for z in rules['target_z']:
                    if grids[z][y][x]==' ':
                        result[x,y,z] = zone['id']
    return result
