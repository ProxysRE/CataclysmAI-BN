#include "avatar.h"
#include "catch/catch.hpp"
#include "cata_utility.h"
#include "coordinates.h"
#include "map/map.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"

#include <array>
#include <string>

TEST_CASE( "radio_station_towers_generate_continuous_ladders_in_all_rotations", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto directions = std::array<std::string, 4>{ "north", "east", "south", "west" };
    for( int variant = 0; variant < 2; ++variant ) {
        const auto station = std::string( variant == 0 ? "station_radio" : "station_radio_1" );
        const auto roof = std::string( variant == 0 ? "station_radio_roof" : "station_radio_roof_1" );
        for( int rotation = 0; rotation < 4; ++rotation ) {
            const auto column = tripoint_abs_omt( 620 + rotation * 3, 620 + variant * 3, 0 );
            auto x = variant == 0 ? 18 : 15;
            auto y = variant == 0 ? 4 : 3;
            for( int turn = 0; turn < rotation; ++turn ) {
                const auto old_x = x;
                x = 23 - y;
                y = old_x;
            }
            for( int z = 0; z <= 6; ++z ) {
                const auto name = z == 0 ? station : z == 1 ? roof :
                                  station + "_tower_" + ( z == 6 ? "top" : z % 2 == 0 ? "even" : "odd" );
                const auto terrain = oter_id( name + "_" + directions[rotation] );
                REQUIRE( terrain.is_valid() );
                buffer.ter_set( tripoint_abs_omt( column.xy(), z ), terrain );
            }
            auto generated = map( 2 );
            generated.load( project_to<coords::sm>( column.xy() ), false );
            for( int z = 0; z <= 6; ++z ) {
                INFO( "variant=" << variant << " rotation=" << rotation << " z=" << z );
                const auto pos = tripoint_bub_ms( x, y, z );
                const auto expected = ter_id( z == 0 ? "t_ladder_up" : z == 6 ? "t_ladder_down" : "t_ladder_up_down" );
                CHECK( generated.ter( pos ) == expected );
                CHECK( generated.has_flag( "GOES_UP", pos ) == ( z < 6 ) );
                CHECK( generated.has_flag( "GOES_DOWN", pos ) == ( z > 0 ) );
            }
            auto reloaded = map( 2 );
            reloaded.load( project_to<coords::sm>( column.xy() ), false );
            CHECK( reloaded.ter( tripoint_bub_ms( x, y, 6 ) ) == ter_id( "t_ladder_down" ) );
        }
    }
}

TEST_CASE( "hotel_technical_enclosures_receive_source_roof_caps", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int column = 0; column < 3; ++column ) {
        const auto suffix = std::to_string( 9 - column ) + "_north";
        const auto lower = oter_id( "hotel_tower_roof_1_" + suffix );
        const auto upper = oter_id( "hotel_tower_6_1_" + suffix );
        REQUIRE( lower.is_valid() );
        REQUIRE( upper.is_valid() );
        buffer.ter_set( tripoint_abs_omt( 720 + column, 720, 4 ), lower );
        buffer.ter_set( tripoint_abs_omt( 720 + column, 720, 5 ), upper );
    }
    for( int column = 0; column < 3; ++column ) {
        INFO( "hotel column=" << column );
        auto generated = map( 2 );
        generated.load( project_to<coords::sm>( point_abs_omt( 720 + column, 720 ) ), false );
        CHECK( generated.ter( tripoint_bub_ms( 12, 0, 5 ) ) == ter_id( "t_open_air" ) );
        if( column == 1 ) {
            CHECK( generated.ter( tripoint_bub_ms( 12, 10, 5 ) ) == ter_id( "t_open_air" ) );
        } else {
            const auto x = column == 0 ? 5 : 17;
            CHECK( generated.ter( tripoint_bub_ms( x, 10, 5 ) ) == ter_id( "t_flat_roof" ) );
            CHECK( generated.ter( tripoint_bub_ms( x, 9, 5 ) ) == ter_id( "t_gutter" ) );
            CHECK_FALSE( generated.has_flag( "GOES_UP", tripoint_bub_ms( x, 10, 5 ) ) );
        }
    }
}

TEST_CASE( "shopping_plaza_roofs_generate_over_existing_bn_stores", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int y = 0; y < 2; ++y ) {
        for( int x = 0; x < 6; ++x ) {
            const auto suffix = std::to_string( x + 1 ) + "_north";
            const auto lower = oter_id( std::string( "s_shoppingplaza_" ) + ( y == 0 ? "a" : "b" ) + suffix );
            REQUIRE( lower.is_valid() );
            buffer.ter_set( tripoint_abs_omt( 760 + x, 760 + y, 0 ), lower );
            if( y == 1 || x == 5 ) {
                const auto upper = oter_id( std::string( "s_shoppingplaza_" ) + ( y == 0 ? "A" : "B" ) + suffix );
                REQUIRE( upper.is_valid() );
                buffer.ter_set( tripoint_abs_omt( 760 + x, 760 + y, 1 ), upper );
            }
        }
    }
    for( int y = 0; y < 2; ++y ) {
        for( int x = 0; x < 6; ++x ) {
            if( y == 0 && x != 5 ) {
                continue;
            }
            INFO( "plaza roof=" << x << "," << y );
            auto generated = map( 2 );
            generated.load( project_to<coords::sm>( point_abs_omt( 760 + x, 760 + y ) ), false );
            CHECK( generated.ter( tripoint_bub_ms( 12, 12, 1 ) ) == ter_id( "t_flat_roof" ) );
        }
    }
}
