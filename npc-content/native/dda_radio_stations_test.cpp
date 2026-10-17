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
