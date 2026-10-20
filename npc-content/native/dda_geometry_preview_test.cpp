#include "catch/catch.hpp"
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
            if( std::string( cell.terrain ).find( "dda_geo_" ) == 0 ) {
                for( int x = 0; x < 24; ++x ) {
                    for( int y = 0; y < 24; ++y ) {
                        const tripoint_bub_ms p( x, y, cell.z );
                        CHECK( generated.ter( p ) != ter_id( "t_null" ) );
                        CHECK( generated.i_at( p ).empty() );
                    }
                }
            }
        }
    }
    clear_all_state();
}
} // namespace

TEST_CASE( "dda_geo_island_prison_all_floors_without_loot", "[dda_geometry]" )
{
    generate_site( 4200, {
        { -1, -1, 0, "lake_surface" },
        { 0, -1, 0, "lake_surface" },
        { 1, -1, 0, "lake_surface" },
        { 2, -1, 0, "lake_surface" },
        { 3, -1, 0, "lake_surface" },
        { 4, -1, 0, "lake_surface" },
        { 5, -1, 0, "lake_surface" },
        { 5, 0, 0, "lake_surface" },
        { 5, 1, 0, "lake_surface" },
        { 5, 2, 0, "lake_surface" },
        { 5, 3, 0, "lake_surface" },
        { 4, 3, 0, "lake_surface" },
        { 3, 3, 0, "lake_surface" },
        { 2, 3, 0, "lake_surface" },
        { 1, 3, 0, "lake_surface" },
        { 0, 3, 0, "lake_surface" },
        { -1, 3, 0, "lake_surface" },
        { -1, 2, 0, "lake_surface" },
        { -1, 1, 0, "lake_surface" },
        { -1, 0, 0, "lake_surface" },
        { 0, 0, 0, "dda_geo_prison_island_1_1_north" },
        { 1, 0, 0, "dda_geo_prison_island_1_2_north" },
        { 2, 0, 0, "dda_geo_prison_island_1_3_north" },
        { 3, 0, 0, "dda_geo_prison_island_1_4_north" },
        { 4, 0, 0, "dda_geo_prison_island_1_5_north" },
        { 0, 1, 0, "dda_geo_prison_island_1_6_north" },
        { 1, 1, 0, "dda_geo_prison_island_1_7_north" },
        { 2, 1, 0, "dda_geo_prison_island_1_8_north" },
        { 3, 1, 0, "dda_geo_prison_island_1_9_north" },
        { 4, 1, 0, "dda_geo_prison_island_1_10_north" },
        { 0, 2, 0, "dda_geo_prison_island_1_11_north" },
        { 1, 2, 0, "dda_geo_prison_island_1_12_north" },
        { 2, 2, 0, "dda_geo_prison_island_1_13_north" },
        { 3, 2, 0, "dda_geo_prison_island_1_14_north" },
        { 4, 2, 0, "dda_geo_prison_island_1_15_north" },
        { 0, 0, 1, "dda_geo_prison_island_1_2f_1_north" },
        { 1, 0, 1, "dda_geo_prison_island_1_2f_2_north" },
        { 2, 0, 1, "dda_geo_prison_island_1_2f_3_north" },
        { 3, 0, 1, "dda_geo_prison_island_1_2f_4_north" },
        { 4, 0, 1, "dda_geo_prison_island_1_2f_5_north" },
        { 0, 1, 1, "dda_geo_prison_island_1_2f_6_north" },
        { 1, 1, 1, "dda_geo_prison_island_1_2f_7_north" },
        { 2, 1, 1, "dda_geo_prison_island_1_2f_8_north" },
        { 3, 1, 1, "dda_geo_prison_island_1_2f_9_north" },
        { 4, 1, 1, "dda_geo_prison_island_1_2f_10_north" },
        { 0, 2, 1, "dda_geo_prison_island_1_2f_11_north" },
        { 1, 2, 1, "dda_geo_prison_island_1_2f_12_north" },
        { 2, 2, 1, "dda_geo_prison_island_1_2f_13_north" },
        { 3, 2, 1, "dda_geo_prison_island_1_2f_14_north" },
        { 4, 2, 1, "dda_geo_prison_island_1_2f_15_north" },
        { 0, 0, 2, "dda_geo_prison_island_1_3f_1_north" },
        { 3, 0, 2, "dda_geo_prison_island_1_3f_4_north" },
        { 4, 0, 2, "dda_geo_prison_island_1_3f_5_north" },
        { 0, 2, 2, "dda_geo_prison_island_1_3f_11_north" },
        { 3, 2, 2, "dda_geo_prison_island_1_3f_14_north" },
        { 0, 0, -1, "dda_geo_prison_island_1_ug_1_north" },
        { 1, 0, -1, "dda_geo_prison_island_1_ug_2_north" },
        { 2, 0, -1, "dda_geo_prison_island_1_ug_3_north" },
        { 3, 0, -1, "dda_geo_prison_island_1_ug_4_north" },
        { 4, 0, -1, "dda_geo_prison_island_1_ug_5_north" },
        { 0, 1, -1, "dda_geo_prison_island_1_ug_6_north" },
        { 1, 1, -1, "dda_geo_prison_island_1_ug_7_north" },
        { 2, 1, -1, "dda_geo_prison_island_1_ug_8_north" },
        { 3, 1, -1, "dda_geo_prison_island_1_ug_9_north" },
        { 4, 1, -1, "dda_geo_prison_island_1_ug_10_north" },
        { 0, 2, -1, "dda_geo_prison_island_1_ug_11_north" },
        { 1, 2, -1, "dda_geo_prison_island_1_ug_12_north" },
        { 2, 2, -1, "dda_geo_prison_island_1_ug_13_north" },
        { 3, 2, -1, "dda_geo_prison_island_1_ug_14_north" },
        { 4, 2, -1, "dda_geo_prison_island_1_ug_15_north" },
        { 0, 0, -2, "empty_rock" },
        { 1, 0, -2, "empty_rock" },
        { 2, 0, -2, "empty_rock" },
        { 3, 0, -2, "empty_rock" },
        { 4, 0, -2, "empty_rock" },
        { 0, 1, -2, "empty_rock" },
        { 1, 1, -2, "empty_rock" },
        { 2, 1, -2, "empty_rock" },
        { 3, 1, -2, "empty_rock" },
        { 4, 1, -2, "empty_rock" },
        { 0, 2, -2, "empty_rock" },
        { 1, 2, -2, "empty_rock" },
        { 2, 2, -2, "empty_rock" },
        { 3, 2, -2, "empty_rock" },
        { 4, 2, -2, "empty_rock" },
        { 0, 0, -3, "empty_rock" },
        { 1, 0, -3, "empty_rock" },
        { 2, 0, -3, "empty_rock" },
        { 3, 0, -3, "empty_rock" },
        { 4, 0, -3, "empty_rock" },
        { 0, 1, -3, "empty_rock" },
        { 1, 1, -3, "empty_rock" },
        { 2, 1, -3, "empty_rock" },
        { 3, 1, -3, "empty_rock" },
        { 4, 1, -3, "empty_rock" },
        { 0, 2, -3, "empty_rock" },
        { 1, 2, -3, "empty_rock" },
        { 2, 2, -3, "empty_rock" },
        { 3, 2, -3, "empty_rock" },
        { 4, 2, -3, "empty_rock" },
        { 0, 0, -4, "empty_rock" },
        { 1, 0, -4, "empty_rock" },
        { 2, 0, -4, "empty_rock" },
        { 3, 0, -4, "empty_rock" },
        { 4, 0, -4, "empty_rock" },
        { 0, 1, -4, "empty_rock" },
        { 1, 1, -4, "empty_rock" },
        { 2, 1, -4, "empty_rock" },
        { 3, 1, -4, "empty_rock" },
        { 4, 1, -4, "empty_rock" },
        { 0, 2, -4, "empty_rock" },
        { 1, 2, -4, "empty_rock" },
        { 2, 2, -4, "empty_rock" },
        { 3, 2, -4, "empty_rock" },
        { 4, 2, -4, "empty_rock" },
        { 0, 0, -5, "empty_rock" },
        { 1, 0, -5, "empty_rock" },
        { 2, 0, -5, "empty_rock" },
        { 3, 0, -5, "empty_rock" },
        { 4, 0, -5, "empty_rock" },
        { 0, 1, -5, "empty_rock" },
        { 1, 1, -5, "empty_rock" },
        { 2, 1, -5, "empty_rock" },
        { 3, 1, -5, "empty_rock" },
        { 4, 1, -5, "empty_rock" },
        { 0, 2, -5, "empty_rock" },
        { 1, 2, -5, "empty_rock" },
        { 2, 2, -5, "empty_rock" },
        { 3, 2, -5, "empty_rock" },
        { 4, 2, -5, "empty_rock" },
    } );
}

TEST_CASE( "dda_geo_xedra_church_rural_all_floors_without_loot", "[dda_geometry]" )
{
    generate_site( 4300, {
        { 1, 0, 0, "dda_geo_xedra_rural_church_parking_north" },
        { 2, 0, 0, "dda_geo_xedra_rural_church_north" },
        { 2, 0, -1, "dda_geo_xedra_rural_church_basement_north" },
        { 2, 0, 1, "dda_geo_xedra_rural_church_steeple_north" },
        { 2, 0, 2, "dda_geo_xedra_rural_church_steeple_roof_north" },
    } );
}
