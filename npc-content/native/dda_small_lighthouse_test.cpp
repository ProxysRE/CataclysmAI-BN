#include "catch/catch.hpp"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "item.h"
#include "item_group.h"
#include "itype.h"
#include "map/map.h"
#include "map_helpers.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include "units.h"

TEST_CASE( "small_lighthouse_generates_all_six_levels_with_continuous_ladders", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
    const int base = 2700;
    const char *levels[] = { "lighthouse_small_ground_north", "lighthouse_small_z1_north",
                            "lighthouse_small_z2_north", "lighthouse_small_z3_north",
                            "lighthouse_small_z4_north", "lighthouse_small_roof_north" };
    for( int y = 0; y < 3; ++y ) {
        for( int x = 0; x < 3; ++x ) {
            buffer.ter_set( tripoint_abs_omt( base + x, base + y, 0 ), oter_id( "lake_surface" ) );
        }
    }
    for( int z = 0; z < 6; ++z ) {
        REQUIRE( oter_id( levels[z] ).is_valid() );
        buffer.ter_set( tripoint_abs_omt( base + 1, base + 1, z ), oter_id( levels[z] ) );
    }
    auto generated = map( 2 );
    generated.load( project_to<coords::sm>( point_abs_omt( base + 1, base + 1 ) ), false );
    for( int z = 0; z < 6; ++z ) {
        INFO( "small lighthouse floor=" << z );
        CHECK( generated.ter( tripoint_bub_ms( 13, 19, z ) ) != ter_id( "t_null" ) );
    }
    CHECK( generated.ter( tripoint_bub_ms( 14, 19, 0 ) ) == ter_id( "t_ladder_up" ) );
    for( int z = 1; z <= 3; ++z ) {
        CHECK( generated.ter( tripoint_bub_ms( 14, 19, z ) ) == ter_id( "t_ladder_up_down" ) );
    }
    CHECK( generated.ter( tripoint_bub_ms( 14, 19, 4 ) ) == ter_id( "t_ladder_down" ) );
    CHECK( generated.ter( tripoint_bub_ms( 13, 21, 4 ) ) == ter_id( "t_ladder_up" ) );
    CHECK( generated.ter( tripoint_bub_ms( 13, 21, 5 ) ) == ter_id( "t_ladder_down" ) );
    CHECK( generated.furn( tripoint_bub_ms( 14, 17, 4 ) ) == furn_id( "f_grid_floodlight_off" ) );
    clear_all_state();
}

TEST_CASE( "small_lighthouse_supplies_fit_their_BN_containers", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "lighthouse_rainwater", "lighthouse_fuel", "lighthouse_food" } ) {
        REQUIRE( item_group::group_is_defined( item_group_id( name ) ) );
        for( int draw = 0; draw < 32; ++draw ) {
            INFO( name << " draw=" << draw );
            auto packages = item_group::items_from( item_group_id( name ), calendar::turn );
            REQUIRE_FALSE( packages.empty() );
            for( const auto &package : packages ) {
                REQUIRE( package->type->container != nullptr );
                auto volume = 0_ml;
                for( const item *content : package->contents.all_items_top() ) { volume += content->volume(); }
                CHECK( volume <= package->type->container->contains );
            }
        }
    }
}
