#include "catch/catch.hpp"
#include "avatar.h"
#include "calendar.h"
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

TEST_CASE( "noncombatant_civilians_are_neutral_humans_with_source_dialogue", "[dda_npc][dda_locations]" )
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
        CHECK( type->age_grow == 1 );
        CHECK( type->half_life == 4 );
        person.setpos( map_local_to_abs( get_map(), tripoint_bub_ms( 68, 60, 0 ) ) );
        CHECK_FALSE( can_chat_with_civilian( person, actor ) );
    }
    const auto &panic = mtype_id( "mon_civilian_panic" )->civilian_dialogue;
    CHECK( panic.next( panic.root, 0 ) == "TALK_CIVILIAN_PANIC_EVAC" );
    CHECK( panic.next( panic.root, 1 ).empty() );
    CHECK( panic.next( "TALK_CIVILIAN_PANIC_EVAC", 0 ).empty() );
    const auto &parent = mtype_id( "mon_civilian_parent" )->civilian_dialogue;
    REQUIRE( parent.find( parent.root ) != nullptr );
    CHECK( parent.find( parent.root )->lines.size() == 3 );
    CHECK( parent.next( parent.root, 0 ) == "TALK_CIVILIAN_PARENT_EVAC" );
    CHECK( mtype_id( "mon_civilian_stationary" )->speed == 20 );
    clear_all_state();
}

TEST_CASE( "civilian_read_only_dialogue_rejects_dangling_links", "[dda_npc][dda_locations]" )
{
    std::istringstream source( R"({"root":"start","pages":[{"id":"start","lines":["Hello"],"responses":[{"text":"Continue","target":"missing"}]}]})" );
    JsonIn input( source );
    civilian_chat graph;
    CHECK_THROWS( graph.load( input.get_object() ) );
}

TEST_CASE( "civilian_evolution_preserves_single_monster_selection", "[dda_npc][dda_locations]" )
{
    const auto group = mongroup_id( "GROUP_CIVILIANS_UPGRADE" );
    REQUIRE( group.is_valid() );
    CHECK( group->freq_total == 90600 );
    CHECK( group->monsters.size() == 11 );
    for( int attempt = 0; attempt < 100; ++attempt ) {
        const auto evolved = MonsterGroupManager::GetRandomMonsterFromGroup( group );
        CHECK( evolved.is_valid() );
        CHECK( evolved != mtype_id( "mon_civilian_panic" ) );
        CHECK( evolved != mtype_id( "mon_civilian_parent" ) );
    }
}
