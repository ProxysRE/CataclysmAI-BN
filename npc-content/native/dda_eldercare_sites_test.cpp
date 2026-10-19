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
        }
    }
    clear_all_state();
}
} // namespace

TEST_CASE( "complete_nursing_home_sh_generates_every_placed_floor", "[dda_civilians][dda_eldercare_sites]" )
{
    generate_site( 2200, {
        { 0, 0, 0, "nursing_home_sh1_north" },
        { 1, 0, 0, "nursing_home_sh2_north" },
        { 2, 0, 0, "nursing_home_sh3_north" },
        { 3, 0, 0, "nursing_home_sh4_north" },
        { 0, 1, 0, "nursing_home_sh5_north" },
        { 1, 1, 0, "nursing_home_sh6_north" },
        { 2, 1, 0, "nursing_home_sh7_north" },
        { 3, 1, 0, "nursing_home_sh8_north" },
        { 0, 2, 0, "nursing_home_sh9_north" },
        { 1, 2, 0, "nursing_home_sh10_north" },
        { 2, 2, 0, "nursing_home_sh11_north" },
        { 3, 2, 0, "nursing_home_sh12_north" },
        { 0, 0, 1, "nursing_home_1_roof_north" },
        { 1, 0, 1, "nursing_home_2_roof_north" },
        { 2, 0, 1, "nursing_home_3_roof_north" },
        { 0, 1, 1, "nursing_home_4_roof_north" },
        { 1, 1, 1, "nursing_home_5_roof_north" },
        { 2, 1, 1, "nursing_home_6_roof_north" },
        { 0, 0, -1, "nursing_home_b1_north" },
        { 1, 0, -1, "nursing_home_b2_north" },
        { 2, 0, -1, "nursing_home_b3_north" },
        { 3, 0, -1, "nursing_home_b4_north" },
        { 0, 1, -1, "nursing_home_b5_north" },
        { 1, 1, -1, "nursing_home_b6_north" },
        { 2, 1, -1, "nursing_home_b7_north" },
        { 3, 1, -1, "nursing_home_b8_north" },
        { 0, 2, -1, "nursing_home_b9_north" },
        { 1, 2, -1, "nursing_home_b10_north" },
        { 2, 2, -1, "nursing_home_b11_north" },
        { 3, 2, -1, "nursing_home_b12_north" },
        { 0, 0, -2, "nursing_home_bb1_north" },
        { 1, 0, -2, "nursing_home_bb2_north" },
        { 2, 0, -2, "nursing_home_bb3_north" },
        { 3, 0, -2, "nursing_home_bb4_north" },
        { 0, 1, -2, "nursing_home_bb5_north" },
        { 1, 1, -2, "nursing_home_bb6_north" },
        { 2, 1, -2, "nursing_home_bb7_north" },
        { 3, 1, -2, "nursing_home_bb8_north" },
        { 0, 2, -2, "nursing_home_bb9_north" },
        { 1, 2, -2, "nursing_home_bb10_north" },
        { 2, 2, -2, "nursing_home_bb11_north" },
        { 3, 2, -2, "nursing_home_bb12_north" },
        { 0, 0, -3, "nursing_home_lab1_north" },
        { 1, 0, -3, "nursing_home_lab2_north" },
        { 2, 0, -3, "nursing_home_lab3_north" },
        { 3, 0, -3, "nursing_home_lab4_north" },
        { 0, 1, -3, "nursing_home_lab5_north" },
        { 1, 1, -3, "nursing_home_lab6_north" },
        { 2, 1, -3, "nursing_home_lab7_north" },
        { 3, 1, -3, "nursing_home_lab8_north" },
        { 0, 2, -3, "nursing_home_lab9_north" },
        { 1, 2, -3, "nursing_home_lab10_north" },
        { 2, 2, -3, "nursing_home_lab11_north" },
        { 3, 2, -3, "nursing_home_lab12_north" },
    } );
}

TEST_CASE( "complete_nursing_home_generates_every_placed_floor", "[dda_civilians][dda_eldercare_sites]" )
{
    generate_site( 2300, {
        { 0, 0, 0, "nursing_home_1_north" },
        { 1, 0, 0, "nursing_home_2_north" },
        { 2, 0, 0, "nursing_home_3_north" },
        { 3, 0, 0, "nursing_home_4_north" },
        { 0, 1, 0, "nursing_home_5_north" },
        { 1, 1, 0, "nursing_home_6_north" },
        { 2, 1, 0, "nursing_home_7_north" },
        { 3, 1, 0, "nursing_home_8_north" },
        { 0, 2, 0, "nursing_home_9_north" },
        { 1, 2, 0, "nursing_home_10_north" },
        { 2, 2, 0, "nursing_home_11_north" },
        { 3, 2, 0, "nursing_home_12_north" },
        { 0, 0, 1, "nursing_home_1_roof_north" },
        { 1, 0, 1, "nursing_home_2_roof_north" },
        { 2, 0, 1, "nursing_home_3_roof_north" },
        { 0, 1, 1, "nursing_home_4_roof_north" },
        { 1, 1, 1, "nursing_home_5_roof_north" },
        { 2, 1, 1, "nursing_home_6_roof_north" },
    } );
}

TEST_CASE( "complete_retirement_community_generates_every_placed_floor", "[dda_civilians][dda_eldercare_sites]" )
{
    generate_site( 2400, {
        { 0, 0, 0, "retirement_community_1_north" },
        { 0, 0, -1, "retirement_community_b_1_north" },
        { 0, 0, 1, "retirement_community_2f_1_north" },
        { 0, 0, 2, "retirement_community_3f_1_north" },
        { 1, 0, 0, "retirement_community_2_north" },
        { 1, 0, -1, "retirement_community_b_2_north" },
        { 1, 0, 1, "retirement_community_2f_2_north" },
        { 1, 0, 2, "retirement_community_3f_2_north" },
        { 2, 0, 0, "retirement_community_3_north" },
        { 2, 0, -1, "retirement_community_b_3_north" },
        { 2, 0, 1, "retirement_community_2f_3_north" },
        { 2, 0, 2, "retirement_community_3f_3_north" },
        { 3, 0, 0, "retirement_community_4_north" },
        { 3, 0, -1, "retirement_community_b_4_north" },
        { 3, 0, 1, "retirement_community_2f_4_north" },
        { 3, 0, 2, "retirement_community_3f_4_north" },
        { 4, 0, 0, "retirement_community_5_north" },
        { 4, 0, -1, "retirement_community_b_5_north" },
        { 4, 0, 1, "retirement_community_2f_5_north" },
        { 4, 0, 2, "retirement_community_3f_5_north" },
        { 5, 0, 0, "retirement_community_6_north" },
        { 5, 0, -1, "retirement_community_b_6_north" },
        { 5, 0, 1, "retirement_community_2f_6_north" },
        { 5, 0, 2, "retirement_community_3f_6_north" },
        { 6, 0, 0, "retirement_community_7_north" },
        { 6, 0, -1, "retirement_community_b_7_north" },
        { 6, 0, 1, "retirement_community_2f_7_north" },
        { 6, 0, 2, "retirement_community_3f_7_north" },
        { 0, 1, 0, "retirement_community_8_north" },
        { 0, 1, 1, "retirement_community_2f_8_north" },
        { 1, 1, 0, "retirement_community_9_north" },
        { 1, 1, 1, "retirement_community_2f_9_north" },
        { 2, 1, 0, "retirement_community_10_north" },
        { 2, 1, 1, "retirement_community_2f_10_north" },
        { 3, 1, 0, "retirement_community_11_north" },
        { 3, 1, 1, "retirement_community_2f_11_north" },
        { 4, 1, 0, "retirement_community_12_north" },
        { 4, 1, 1, "retirement_community_2f_12_north" },
        { 5, 1, 0, "retirement_community_13_north" },
        { 5, 1, 1, "retirement_community_2f_13_north" },
        { 6, 1, 0, "retirement_community_14_north" },
        { 6, 1, 1, "retirement_community_2f_14_north" },
        { 0, 2, 0, "retirement_community_15_north" },
        { 0, 2, -1, "retirement_community_b_15_north" },
        { 0, 2, 1, "retirement_community_2f_15_north" },
        { 0, 2, 2, "retirement_community_3f_15_north" },
        { 1, 2, 0, "retirement_community_16_north" },
        { 0, 3, 0, "retirement_community_19_north" },
        { 0, 3, -1, "retirement_community_b_19_north" },
        { 0, 3, 1, "retirement_community_2f_19_north" },
        { 0, 3, 2, "retirement_community_3f_19_north" },
        { 1, 3, 0, "retirement_community_20_north" },
        { 0, 4, 0, "retirement_community_23_north" },
        { 0, 4, -1, "retirement_community_b_23_north" },
        { 0, 4, 1, "retirement_community_2f_23_north" },
        { 0, 4, 2, "retirement_community_3f_23_north" },
        { 1, 4, 0, "retirement_community_24_north" },
        { 5, 2, 0, "retirement_community_17_north" },
        { 6, 2, 0, "retirement_community_18_north" },
        { 6, 2, -1, "retirement_community_b_18_north" },
        { 6, 2, 1, "retirement_community_2f_18_north" },
        { 6, 2, 2, "retirement_community_3f_18_north" },
        { 5, 3, 0, "retirement_community_21_north" },
        { 6, 3, 0, "retirement_community_22_north" },
        { 6, 3, -1, "retirement_community_b_22_north" },
        { 6, 3, 1, "retirement_community_2f_22_north" },
        { 6, 3, 2, "retirement_community_3f_22_north" },
        { 5, 4, 0, "retirement_community_25_north" },
        { 6, 4, 0, "retirement_community_26_north" },
        { 6, 4, -1, "retirement_community_b_26_north" },
        { 6, 4, 1, "retirement_community_2f_26_north" },
        { 6, 4, 2, "retirement_community_3f_26_north" },
        { 0, 5, 0, "retirement_community_27_north" },
        { 0, 5, 1, "retirement_community_2f_27_north" },
        { 1, 5, 0, "retirement_community_28_north" },
        { 1, 5, 1, "retirement_community_2f_28_north" },
        { 2, 5, 0, "retirement_community_29_north" },
        { 2, 5, 1, "retirement_community_2f_29_north" },
        { 3, 5, 0, "retirement_community_30_north" },
        { 3, 5, 1, "retirement_community_2f_30_north" },
        { 4, 5, 0, "retirement_community_31_north" },
        { 4, 5, 1, "retirement_community_2f_31_north" },
        { 5, 5, 0, "retirement_community_32_north" },
        { 5, 5, 1, "retirement_community_2f_32_north" },
        { 6, 5, 0, "retirement_community_33_north" },
        { 6, 5, 1, "retirement_community_2f_33_north" },
        { 0, 6, 0, "retirement_community_34_north" },
        { 0, 6, 1, "retirement_community_2f_34_north" },
        { 1, 6, 0, "retirement_community_35_north" },
        { 1, 6, 1, "retirement_community_2f_35_north" },
        { 2, 6, 0, "retirement_community_36_north" },
        { 2, 6, 1, "retirement_community_2f_36_north" },
        { 3, 6, 0, "retirement_community_37_north" },
        { 3, 6, -1, "retirement_community_b_37_north" },
        { 3, 6, 1, "retirement_community_2f_37_north" },
        { 4, 6, 0, "retirement_community_38_north" },
        { 4, 6, -1, "retirement_community_b_38_north" },
        { 4, 6, 1, "retirement_community_2f_38_north" },
        { 5, 6, 0, "retirement_community_39_north" },
        { 5, 6, 1, "retirement_community_2f_39_north" },
        { 6, 6, 0, "retirement_community_40_north" },
        { 6, 6, 1, "retirement_community_2f_40_north" },
        { 2, 2, 0, "retirement_community_park_1_north" },
        { 2, 2, -1, "retirement_community_park_b_1_north" },
        { 3, 2, 0, "retirement_community_park_2_north" },
        { 3, 2, -1, "retirement_community_park_b_2_north" },
        { 3, 2, 1, "retirement_community_park_2f_2_north" },
        { 4, 2, 0, "retirement_community_park_3_north" },
        { 4, 2, -1, "retirement_community_park_b_3_north" },
        { 2, 3, 0, "retirement_community_park_4_north" },
        { 2, 3, -1, "retirement_community_park_b_4_north" },
        { 3, 3, 0, "retirement_community_park_5_north" },
        { 3, 3, -1, "retirement_community_park_b_5_north" },
        { 3, 3, 1, "retirement_community_park_2f_5_north" },
        { 4, 3, 0, "retirement_community_park_6_north" },
        { 4, 3, -1, "retirement_community_park_b_6_north" },
        { 2, 4, 0, "retirement_community_park_7_north" },
        { 2, 4, -1, "retirement_community_park_b_7_north" },
        { 3, 4, 0, "retirement_community_park_8_north" },
        { 3, 4, -1, "retirement_community_park_b_8_north" },
        { 4, 4, 0, "retirement_community_park_9_north" },
        { 4, 4, -1, "retirement_community_park_b_9_north" },
        { 3, 7, 0, "retirement_community_road_north" },
        { 4, 7, 0, "sub_station_west" },
        { 4, 7, 1, "sub_station_roof_west" },
        { 4, 7, -1, "sewer_sub_station_west" },
        { 4, 7, -2, "underground_sub_station_west" },
        { 2, 7, 0, "s_lot" },
        { 1, 1, -1, "sewer_es" },
        { 2, 1, -1, "sewer_ew" },
        { 3, 1, -1, "sewer_esw" },
        { 4, 1, -1, "sewer_ew" },
        { 5, 1, -1, "sewer_sw" },
        { 1, 2, -1, "sewer_ns" },
        { 5, 2, -1, "sewer_ns" },
        { 1, 3, -1, "sewer_nes" },
        { 5, 3, -1, "sewer_nsw" },
        { 1, 4, -1, "sewer_ns" },
        { 5, 4, -1, "sewer_ns" },
        { 1, 5, -1, "sewer_ne" },
        { 2, 5, -1, "sewer_esw" },
        { 3, 5, -1, "sewer_new" },
        { 4, 5, -1, "sewer_esw" },
        { 5, 5, -1, "sewer_wn" },
        { 2, 6, -1, "sewer_ns" },
        { 2, 7, -1, "sewer_ne" },
        { 3, 7, -1, "retirement_community_sewer_north" },
    } );
}

TEST_CASE( "complete_eldercare_specials_place_in_four_rotations", "[dda_civilians][dda_eldercare_sites]" )
{
    for( const auto *name : { "nursing_home_sh", "nursing_home", "retirement_community" } ) {
        for( const auto dir : { om_direction::type::north, om_direction::type::east,
                               om_direction::type::south, om_direction::type::west } ) {
            clear_all_state();
            INFO( name );
            auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
            buffer.clear();
            const overmap_special_id id( name );
            CHECK_FALSE( buffer.contains_unique_special( id ) );
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
