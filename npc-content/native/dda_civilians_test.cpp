#include "catch/catch.hpp"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "civilian_chat.h"
#include "civilian_chat_ui.h"
#include "game.h"
#include "map/map.h"
#include "map_helpers.h"
#include "monster.h"
#include "mongroup.h"
#include "mtype.h"
#include "state_helpers.h"

#include <sstream>

TEST_CASE( "noncombatant_civilians_are_neutral_humans_with_source_dialogue", "[dda_civilians]" )
{
    clear_all_state();
    clear_map();
    build_test_map( ter_id( "t_floor" ) );
    auto &actor = get_avatar();
    actor.setpos( map_local_to_abs( get_map(), tripoint_bub_ms( 60, 60, 0 ) ) );
    monster zombie( mtype_id( "mon_zombie" ), tripoint_bub_ms( 64, 60, 0 ) );
    for( const auto *name : { "mon_civilian_panic", "mon_civilian_stationary", "mon_civilian_parent" } ) {
        INFO( name );
        const auto type = mtype_id( name );
        REQUIRE( type.is_valid() );
        monster person( type, tripoint_bub_ms( 61, 60, 0 ) );
        CHECK( person.attitude_to( actor ) != Attitude::A_HOSTILE );
        CHECK( zombie.attitude_to( person ) == Attitude::A_HOSTILE );
        CHECK_FALSE( type->civilian_dialogue.empty() );
        CHECK( type->upgrade_group == mongroup_id( "GROUP_CIVILIANS_UPGRADE" ) );
        CHECK( type->age_grow == -1 );
        CHECK( type->half_life == 1 );
        monster distant_person( type, tripoint_bub_ms( 68, 60, 0 ) );
        CHECK_FALSE( can_chat_with_civilian( distant_person, actor ) );
    }
    const auto &panic = mtype_id( "mon_civilian_panic" )->civilian_dialogue;
    CHECK( panic.next( panic.root, 0 ) == "TALK_CIVILIAN_PANIC_EVAC" );
    CHECK( panic.next( panic.root, 1 ).empty() );
    CHECK( panic.next( "TALK_CIVILIAN_PANIC_EVAC", 0 ).empty() );
    const auto &parent = mtype_id( "mon_civilian_parent" )->civilian_dialogue;
    REQUIRE( parent.find( parent.root ) != nullptr );
    CHECK( parent.find( parent.root )->lines.size() == 3 );
    CHECK( parent.next( parent.root, 0 ) == "TALK_CIVILIAN_PARENT_EVAC" );
    CHECK( mtype_id( "mon_civilian_stationary" )->speed == 0 );
    clear_all_state();
}

TEST_CASE( "civilian_read_only_dialogue_rejects_dangling_links", "[dda_npc][dda_civilians]" )
{
    std::istringstream source( R"({"root":"start","pages":[{"id":"start","lines":["Hello"],"responses":[{"text":"Continue","target":"missing"}]}]})" );
    JsonIn input( source );
    civilian_chat graph;
    CHECK_THROWS( graph.load( input.get_object() ) );
}

TEST_CASE( "existing_Civilians_keep_their_evolution_and_opt_in_dialogue", "[dda_civilians]" )
{
    const auto group = mongroup_id( "GROUP_CIVILIANS_UPGRADE" );
    REQUIRE( group.is_valid() );
    CHECK( group->freq_total == 1000 );
    REQUIRE( group->monsters.size() == 8 );
    CHECK( group->monsters.front().name == mtype_id( "mon_civilian_survivor_bow" ) );
    CHECK( group->monsters.front().frequency == 16 );
    for( const auto *name : { "mon_civilian_police", "mon_civilian_zombiefighter", "mon_civilian_icu" } ) {
        const auto type = mtype_id( name );
        REQUIRE( type.is_valid() );
        CHECK_FALSE( type->civilian_dialogue.empty() );
    }
    CHECK( mtype_id( "mon_civilian_survivor_pistol" )->civilian_dialogue.empty() );
    CHECK( mtype_id( "mon_civilian_child" )->civilian_dialogue.empty() );
}

TEST_CASE( "core_game_does_not_duplicate_optional_Civilians_content", "[dda_npc]" )
{
    CHECK_FALSE( mtype_id( "mon_civilian_panic" ).is_valid() );
    CHECK_FALSE( mtype_id( "mon_civilian_parent" ).is_valid() );
    CHECK_FALSE( mongroup_id( "GROUP_CIVILIANS_UPGRADE" ).is_valid() );
    CHECK_FALSE( mongroup_id( "GROUP_CIVILIANS_STANDARD" ).is_valid() );
    CHECK_FALSE( mongroup_id( "GROUP_NURSING_HOME" ).is_valid() );
    CHECK_FALSE( mongroup_id( "GROUP_RETIREMENT_COMMUNITY" ).is_valid() );
}

TEST_CASE( "eldercare_optional_groups_use_BN_civilian_counterparts_and_timing", "[dda_civilians]" )
{
    const auto restore_turn = restore_on_out_of_scope<time_point>( calendar::turn );
    const auto civilians = mongroup_id( "GROUP_CIVILIANS_STANDARD" );
    REQUIRE( civilians.is_valid() );
    CHECK( civilians->freq_total == 266 );
    REQUIRE( civilians->monsters.size() == 10 );
    CHECK( civilians->monsters[2].name == mtype_id( "mon_civilian_survivor_pistol" ) );
    CHECK( civilians->monsters[3].name == mtype_id( "mon_civilian_police" ) );
    CHECK( civilians->monsters[3].cost_multiplier == 3 );
    CHECK( civilians->monsters[7].pack_maximum == 5 );
    CHECK_FALSE( mtype_id( "mon_civilian_police_rifle" ).is_valid() );
    CHECK_FALSE( mtype_id( "mon_civilian_zombiegunner" ).is_valid() );
    calendar::turn = calendar::start_of_cataclysm + civilians->monsters.back().ends + 1_days;
    for( int i = 0; i < 100; ++i ) {
        int budget = 20;
        const auto result = MonsterGroupManager::GetResultFromGroup( civilians, &budget );
        CHECK( result.name == mtype_id( "mon_civilian_panic" ) );
        CHECK( result.pack_size == 1 );
        CHECK( budget == 19 );
    }
    for( const auto *name : { "GROUP_NURSING_HOME", "GROUP_RETIREMENT_COMMUNITY" } ) {
        const auto group = mongroup_id( name );
        REQUIRE( group.is_valid() );
        CHECK( group->freq_total == ( group == mongroup_id( "GROUP_NURSING_HOME" ) ?
                                     27398 : 27930 ) );
        REQUIRE( group->monsters.size() >= 10 );
        CHECK( group->monsters.front().frequency == 300 );
        for( int i = 0; i < 100; ++i ) {
            const auto result = MonsterGroupManager::GetResultFromGroup( group );
            CHECK( result.name.is_valid() );
            CHECK_FALSE( result.name.str().find( "mon_civilian_" ) == 0 );
        }
    }
}
