#include "catch/catch.hpp"
#include "avatar.h"
#include "cata_utility.h"
#include "dialogue.h"
#include "game.h"
#include "item_group.h"
#include "map/map.h"
#include "map_helpers.h"
#include "npc.h"
#include "npctalk.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"

TEST_CASE( "grey_moose_trader_and_guard_load_with_source_roles", "[dda_npc][dda_militia]" )
{
    clear_all_state();
    get_avatar().reset_all_missions();
    for( const auto *id : { "MILITIA_MERCHANT", "MILITIA_GUARD1" } ) {
        REQUIRE( string_id<npc_template>( id ).is_valid() );
    }
    npc merchant;
    merchant.load_npc_template( string_id<npc_template>( "MILITIA_MERCHANT" ) );
    CHECK( merchant.mission == NPC_MISSION_SHOPKEEP );
    CHECK( merchant.get_fac_id() == faction_id( "GM_militia_faction" ) );
    npc guard;
    guard.load_npc_template( string_id<npc_template>( "MILITIA_GUARD1" ) );
    CHECK( guard.mission == NPC_MISSION_GUARD_PATROL );
    CHECK( guard.get_fac_id() == merchant.get_fac_id() );
    REQUIRE( item_group::group_is_defined( item_group_id( "MILITIA_MERCHANT_misc" ) ) );
    auto conversation = dialogue{};
    conversation.alpha = &get_avatar();
    conversation.beta = &merchant;
    const auto first = conversation.dynamic_line( talk_topic( "TALK_MILITIA_MAIN" ) );
    CHECK( first.find( "Welcome to our camp" ) != std::string::npos );
    get_avatar().set_value( "npctalk_var_dialogue_first_meeting_talked_to_MILITIAMAIN", "yes" );
    CHECK( conversation.dynamic_line( talk_topic( "TALK_MILITIA_MAIN" ) ) == "Hello again." );
    clear_all_state();
}

TEST_CASE( "grey_moose_lodge_generates_two_floors_roof_and_seven_community_npcs", "[dda_npc][dda_militia][dda_civilians]" )
{
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
    const int base = 1700;
    for( int y = 0; y < 4; ++y ) {
        for( int x = 0; x < 4; ++x ) {
            const auto name = "GMLODGE" + std::to_string( y + 1 ) + "_" + std::to_string( x + 1 );
            const auto terrain = oter_id( name + "_north" );
            REQUIRE( terrain.is_valid() );
            buffer.ter_set( tripoint_abs_omt( base + x, base + y, 0 ), terrain );
        }
    }
    for( int y = 1; y <= 2; ++y ) {
        for( int x = 1; x <= 2; ++x ) {
            const auto stem = "GMLODGE" + std::to_string( y + 1 );
            buffer.ter_set( tripoint_abs_omt( base + x, base + y, 1 ),
                            oter_id( stem + "_" + std::to_string( x + 1 ) + "_2_north" ) );
            buffer.ter_set( tripoint_abs_omt( base + x, base + y, 2 ),
                            oter_id( stem + "_roof_" + std::to_string( x + 1 ) + "_north" ) );
        }
    }
    for( int y = 0; y < 4; ++y ) {
        for( int x = 0; x < 4; ++x ) {
            INFO( "lodge cell=" << x << "," << y );
            auto generated = map( 2 );
            generated.load( project_to<coords::sm>( point_abs_omt( base + x, base + y ) ), false );
            CHECK( generated.ter( tripoint_bub_ms( 12, 12, 0 ) ) != ter_id( "t_null" ) );
            if( x >= 1 && x <= 2 && y >= 1 && y <= 2 ) {
                CHECK( generated.ter( tripoint_bub_ms( 12, 12, 1 ) ) != ter_id( "t_null" ) );
                CHECK( generated.ter( tripoint_bub_ms( 12, 12, 2 ) ) != ter_id( "t_null" ) );
            }
        }
    }
    int merchants = 0;
    int guards = 0;
    for( int z = 0; z <= 2; ++z ) {
        int floor_merchants = 0;
        int floor_guards = 0;
        // BN's nearby-OMT query filters by the requested Z level.
        for( const auto &person : buffer.get_npcs_near_omt( tripoint_abs_omt( base + 2, base + 2, z ), 4 ) ) {
            if( person->get_fac_id() != faction_id( "GM_militia_faction" ) ) { continue; }
            if( person->mission == NPC_MISSION_SHOPKEEP ) { ++floor_merchants; }
            if( person->mission == NPC_MISSION_GUARD_PATROL ) { ++floor_guards; }
        }
        INFO( "lodge population z=" << z );
        CHECK( floor_merchants == ( z == 1 ? 1 : 0 ) );
        CHECK( floor_guards == ( z == 0 ? 4 : z == 1 ? 2 : 0 ) );
        merchants += floor_merchants;
        guards += floor_guards;
    }
    CHECK( merchants == 1 );
    CHECK( guards == 6 );
    clear_all_state();
}
