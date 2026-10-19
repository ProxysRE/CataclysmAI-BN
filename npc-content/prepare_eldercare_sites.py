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
#include "overmap/overmap.h"
#include "overmap/overmap_special.h"
#include "overmap/om_direction.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include <initializer_list>
#include <algorithm>
#include <memory>
#include <vector>
#include <set>
#include <string>
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
    lines.append(r'''
TEST_CASE( "complete_eldercare_specials_place_in_four_rotations", "[dda_civilians][dda_eldercare_sites]" )
{
    for( const auto *name : { "nursing_home_sh", "nursing_home", "retirement_community" } ) {
        for( const auto dir : { om_direction::type::north, om_direction::type::east,
                               om_direction::type::south, om_direction::type::west } ) {
            clear_all_state();
            INFO( name );
            const overmap_special_id id( name );
            REQUIRE( id.is_valid() );
            const auto &special = id.obj();
            const auto required = special.required_locations();
            auto om = std::make_unique<overmap>( point_abs_om( 0, 0 ) );
            const tripoint_om_omt origin( 60, 60, 0 );
            std::vector<tripoint_om_omt> frontage;
            for( const auto &cell : required ) {
                const auto pos = origin + om_direction::rotate( cell.p, dir );
                om->ter_set( pos, oter_id( "field" ) );
                if( special.get_terrain_at( cell.p ).is_null() ) { frontage.push_back( pos ); }
            }
            REQUIRE( frontage.size() == 1 );
            const auto expected = std::string( name ) == "nursing_home_sh" ? 54u :
                                  std::string( name ) == "nursing_home" ? 18u : 147u;
            REQUIRE( required.size() == expected + 1 );
            om->ter_set( frontage.front(), oter_id( "river_center" ) );
            CHECK_FALSE( om->can_place_special( special, origin, dir, false ) );
            om->ter_set( frontage.front(), oter_id( "field" ) );
            REQUIRE( om->can_place_special( special, origin, dir, false ) );
            const auto used = om->place_special( special, origin, dir, city(), false, false );
            CHECK( used.size() == expected );
            CHECK( std::find( used.begin(), used.end(), frontage.front() ) == used.end() );
            for( const auto &pos : used ) {
                CHECK( om->ter( pos ).id() != oter_str_id::NULL_ID() );
            }
        }
    }
    clear_all_state();
}
''')
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
    print('PASS: both complete sites embedded with Civilians; four native fixtures cover 219 cells and twelve full-special placements; runtime pending')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    prepare(parser.parse_args().check)
