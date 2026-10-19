#!/usr/bin/env python3
"""Close used glyph gaps in shared DDA/BN palettes without replacing BN palettes."""
import copy
import hashlib
import json
import unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def sources():
    m=json.loads((ROOT/'palette_compat/SOURCE_EVIDENCE.json').read_text())
    assert m['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    out={}
    for n,r in m['files'].items():
        b=r['text'].encode()
        assert hashlib.sha256(b).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['blob_sha']
        out[n]=json.loads(r['text'])
    return out


def used_glyphs(obj):
    glyphs=[]
    for row in obj.get('rows',[]):
        for c in row:
            if unicodedata.combining(c):glyphs[-1]+=c
            else:glyphs.append(c)
    return set(glyphs)


def repair(obj):
    result=copy.deepcopy(obj)
    files=sources()
    used=used_glyphs(obj)
    # Fill only missing bindings. Existing BN meanings and local overrides stay intact.
    for name,filename in (('roof_palette','roof_palette.json'),('sewers','sewers_palette.json')):
        if name not in obj.get('palettes',[]):continue
        original=files['dda/'+filename][0]
        baseline=files['bn/'+filename][0]
        bound={k for v in result.values() if isinstance(v,dict) for k in v}
        bound|={k for v in baseline.values() if isinstance(v,dict) for k in v}
        for glyph in sorted(used-bound-{' '}):
            found=False
            for field,bindings in original.items():
                if isinstance(bindings,dict) and glyph in bindings:
                    result.setdefault(field,{})[glyph]=copy.deepcopy(bindings[glyph]);found=True
            assert found,(name,glyph)
    return result


def native_support():
    result=[]
    for e in sources()['dda/nested_chunks_roof.json']:
        if not e.get('nested_mapgen_id','').startswith(('residential_6kW_solar','residential_7kW_solar','residential_8kW_solar')):continue
        e=copy.deepcopy(e);e['method']='json'
        # BN has coarser native removal. Use explicit glyph removal so nested
        # chunks do not depend on propagation of flags through mapgen args.
        # Only occupied solar cells are cleared; blank margins stay untouched.
        obj=e['object']
        if 'ERASE_ITEMS_BEFORE_PLACING_TERRAIN' in obj.get('flags',[]):
            obj['flags'].remove('ERASE_ITEMS_BEFORE_PLACING_TERRAIN')
            if not obj['flags']:obj.pop('flags')
            assert 'remove_all' not in obj
            obj['remove_all']={glyph:{} for glyph in obj['terrain']}
        result.append(e)
    assert len(result)==9
    return result
