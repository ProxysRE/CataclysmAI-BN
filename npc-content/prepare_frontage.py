#!/usr/bin/env python3
"""Port DDA's constraint-only fixed-special cells to the existing BN loader."""
import argparse
import base64
import difflib
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/'frontage'
TARGET='src/overmap/overmap.cpp'


def sources():
    m=json.loads((FOLDER/'SOURCE_MANIFEST.json').read_text())
    assert m['pins']=={'bn':'c621aaf42fa182473aad10feea2b55647704dcf1','dda':'c19e95bc96d27d8bef8e2e246a63cd4cd6f89974'}
    raw=gzip.decompress(base64.b64decode(''.join((FOLDER/p).read_text() for p in m['parts']),validate=True))
    assert hashlib.sha256(raw).hexdigest()==m['bundle_sha256']
    files=json.loads(raw)
    assert set(files)==set(m['files'])
    for p,text in files.items(): assert hashlib.sha256(text.encode()).hexdigest()==m['files'][p]
    return files


def replacement():
    files=sources()
    dda=files['dda/src/overmap_special_fixed.cpp']
    assert 'if( !( elem.terrain == oter_str_id::NULL_ID() ) )' in dda
    assert 'std::copy( terrains.begin(), terrains.end(), std::back_inserter( result ) );' in dda
    source=files['bn/'+TARGET]
    start=source.index('struct fixed_overmap_special_data:')
    end=source.index('\nstruct mutable_overmap_join',start)
    block=source[start:end]
    old='            if (!oter.is_valid()) {'
    assert block.count(old)==1
    block=block.replace(old,'            if (!oter.is_null() && !oter.is_valid()) {')
    old='        for (const overmap_special_terrain& ter : terrains) { result.push_back(ter.terrain); }'
    assert block.count(old)==1
    block=block.replace(old,'''        for (const overmap_special_terrain& ter : terrains) {
            if (!ter.terrain.is_null()) { result.push_back(ter.terrain); }
        }''')
    old='[](const overmap_special_terrain& terrain) { return terrain.p.z() == 0; }'
    assert block.count(old)==1
    block=block.replace(old,'''[](const overmap_special_terrain& terrain) {
                         return terrain.p.z() == 0 && !terrain.terrain.is_null();
                     }''')
    old='''        for (const auto& elem : terrains) {
            const tripoint_om_omt location = origin + om_direction::rotate(elem.p, dir);'''
    assert block.count(old)==1
    block=block.replace(old,'''        for (const auto& elem : terrains) {
            // A missing terrain constrains placement without changing this cell.
            // Keep it in required_locations(), but never write null terrain.
            if (elem.terrain.is_null()) { continue; }
            const tripoint_om_omt location = origin + om_direction::rotate(elem.p, dir);''')
    return source[:start]+block+source[end:]


def patch_sections():
    return ''.join(difflib.unified_diff(sources()['bn/'+TARGET].splitlines(keepends=True),
                replacement().splitlines(keepends=True),'a/'+TARGET,'b/'+TARGET))


def prepare(bn_source=None):
    files=sources()
    if bn_source:
        for p,text in files.items():
            if p.startswith('bn/'):
                assert (bn_source/p[3:]).read_text(encoding='utf-8')==text,p
    original=files['bn/'+TARGET]
    result=replacement()
    # The same full required_locations() copy must remain: no lost frontage,
    # city constraints, rotation transforms or location validation.
    anchor='''    auto required_locations() const -> std::vector<overmap_special_locations> override {
        std::vector<overmap_special_locations> result;
        std::copy(terrains.begin(), terrains.end(), std::back_inserter(result));
        return result;
    }'''
    assert anchor in original and anchor in result
    assert result.count('struct fixed_overmap_special_data:')==1
    print('PASS: DDA constraint-only placement skip in BN fixed specials; required locations unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn-source',type=Path)
    prepare(p.parse_args().bn_source)
