#!/usr/bin/env python3
"""Promote both complete eldercare locations into their required Civilians mod."""
import argparse
import json
from pathlib import Path
from prepare_eldercare_maps import ROOT, payloads, geometry, prepare as prepare_maps

PAYLOAD = 'data/mods/Civilians/dda_eldercare_locations.json'
NATIVE = ROOT / 'native/dda_eldercare_locations.json'
TEST = ROOT / 'native/dda_eldercare_sites_test.cpp'


def native_data():
    return sum(payloads().values(), [])


def native_test():
    lines = ['''#include "catch/catch.hpp"
#include "avatar.h"
#include "cata_utility.h"
#include "map/map.h"
#include "map_helpers.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include <initializer_list>
#include <set>
#include <utility>

namespace {
struct site_cell { int x; int y; int z; const char *terrain; };
void generate_site( int base, std::initializer_list<site_cell> cells )
{
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
    std::set<std::pair<int, int>> columns;
    for( const auto &cell : cells ) {
        INFO( cell.terrain );
        const oter_id terrain( cell.terrain );
        REQUIRE( terrain.is_valid() );
        buffer.ter_set( tripoint_abs_omt( base + cell.x, base + cell.y, cell.z ), terrain );
        columns.emplace( cell.x, cell.y );
    }
    for( const auto &column : columns ) {
        INFO( "site column=" << column.first << "," << column.second );
        auto generated = map( 2 );
        generated.load( project_to<coords::sm>( point_abs_omt( base + column.first, base + column.second ) ), false );
        for( const auto &cell : cells ) {
            if( cell.x != column.first || cell.y != column.second ) { continue; }
            INFO( "terrain=" << cell.terrain << " z=" << cell.z );
            CHECK( generated.ter( tripoint_bub_ms( 12, 12, cell.z ) ) != ter_id( "t_null" ) );
        }
    }
    clear_all_state();
}
} // namespace
''']
    index = 0
    placed = 0
    for site, entries in payloads().items():
        for special in (e for e in entries if e['type'] == 'overmap_special'):
            name = special['id']
            lines.append(f'\nTEST_CASE( "complete_{name}_generates_every_placed_floor", "[dda_civilians][dda_eldercare_sites]" )\n{{\n    generate_site( {2200 + index*100}, {{\n')
            for cell in special['overmaps']:
                if 'overmap' not in cell:
                    continue  # Constraint-only frontage is covered by its placement regression.
                placed += 1
                x, y, z = cell['point']
                lines.append(f'        {{ {x}, {y}, {z}, {json.dumps(cell["overmap"])} }},\n')
            lines.append('    } );\n}\n')
            index += 1
    assert index == 3 and placed == 219
    return ''.join(lines)


def prepare(check=False):
    prepare_maps(check=True)
    payload = native_data()
    assert len(payload) == 71
    outputs = {NATIVE: json.dumps(payload, indent=2, ensure_ascii=True)+'\n', TEST: native_test()}
    for path, text in outputs.items():
        if check:
            assert path.read_text() == text, path
        else:
            path.write_text(text)
    print('PASS: both complete sites embedded with Civilians; three native fixtures cover all 219 placed cells; runtime pending')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
