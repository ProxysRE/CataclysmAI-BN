#include "catch/catch.hpp"
#include "calendar.h"
#include "cata_utility.h"
#include "game.h"
#include "map/map.h"
#include "map_helpers.h"
#include "monster.h"
#include "state_helpers.h"
#include "item.h"
#include "item_group.h"
#include "mongroup.h"
#include "mtype.h"

TEST_CASE( "eldercare_ferals_use_BN_weapon_groups", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "mon_feral_cop", "mon_feral_sapien_spear" } ) {
        INFO( name );
        const auto type = mtype_id( name );
        REQUIRE( type.is_valid() );
        REQUIRE( item_group::group_is_defined( type->monster_weapon ) );
        const auto stock = item_group::items_from( type->monster_weapon, calendar::turn );
        REQUIRE( stock.size() == 1 );
        CHECK( stock.front()->typeId() == itype_id( type == mtype_id( "mon_feral_cop" ) ?
                "tonfa" : "spear_knife" ) );
        CHECK( type->special_attacks.count( "PARROT_AT_DANGER" ) == 1 );
    }
    REQUIRE( item_group::group_is_defined( item_group_id( "dda_feral_spear_outfit" ) ) );
}

TEST_CASE( "eldercare_unique_mutants_load_BN_attack_actors", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "mon_mutant_antler", "mon_mutant_arthropod",
                             "mon_mutant_camouflaged", "mon_mutant_mollusk" } ) {
        INFO( name );
        const auto type = mtype_id( name );
        REQUIRE( type.is_valid() );
        CHECK_FALSE( type->upgrades );
        CHECK_FALSE( type->special_attacks.empty() );
    }
    CHECK( mtype_id( "mon_mutant_antler" )->special_attacks.count( "dda_mutant_antler" ) == 1 );
    CHECK( mtype_id( "mon_mutant_arthropod" )->special_attacks.count( "dda_mutant_stinger" ) == 1 );
    CHECK( mtype_id( "mon_mutant_mollusk" )->special_attacks.count( "RANGED_PULL" ) == 1 );
    CHECK( mtype_id( "mon_mutant_mollusk" )->armor_bash == 22 );
}

TEST_CASE( "eldercare_direct_spawn_groups_resolve_monsters", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "GROUP_FERAL", "GROUP_MUTANT_EVOLVED", "GROUP_NURSING_HOME_LAB" } ) {
        INFO( name );
        const auto group = mongroup_id( name );
        REQUIRE( group.is_valid() );
        for( int attempt = 0; attempt < 100; ++attempt ) {
            CHECK( MonsterGroupManager::GetResultFromGroup( group ).name.is_valid() );
        }
    }
}

TEST_CASE( "eldercare_cellar_spider_brood_uses_native_death_spawns", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    clear_map();
    build_test_map( ter_id( "t_floor" ) );
    auto &mother = spawn_test_monster( "mon_spider_cellar_mom", tripoint_bub_ms( 65, 60, 0 ) );
    REQUIRE_FALSE( mother.type->on_death.empty() );
    mother.die( nullptr );
    int juveniles = 0;
    for( const monster &entry : g->all_monsters() ) {
        if( entry.type->id == mtype_id( "mon_spider_cellar_giant_s" ) ) {
            ++juveniles;
        }
    }
    CHECK( juveniles == 6 );
    CHECK( mtype_id( "mon_spider_cellar_mega" )->hp == 420 );
    CHECK( mtype_id( "mon_spider_cellar_mega" )->special_attacks.count( "GRAB" ) == 1 );
    clear_all_state();
}

TEST_CASE( "eldercare_cellar_spider_groups_keep_age_windows", "[dda_npc][dda_locations]" )
{
    const auto group = mongroup_id( "GROUP_SPIDER_BASEMENT" );
    REQUIRE( group.is_valid() );
    REQUIRE( group->monsters.size() == 5 );
    CHECK( group->freq_total == 90 );
    const auto &first = group->monsters.front();
    CHECK( first.frequency == 30 );
    CHECK( first.starts > 0_turns );
    CHECK( first.ends == first.starts * 4 );
    const auto restore_turn = restore_on_out_of_scope<time_point>( calendar::turn );
    calendar::turn = calendar::start_of_cataclysm + first.starts - 1_turns;
    for( int attempt = 0; attempt < 50; ++attempt ) {
        CHECK( MonsterGroupManager::GetResultFromGroup( group ).name ==
               mtype_id( "mon_spider_cellar_giant_s" ) );
    }
    calendar::turn = calendar::start_of_cataclysm + group->monsters.back().starts + 1_days;
    for( int attempt = 0; attempt < 200; ++attempt ) {
        const auto name = MonsterGroupManager::GetResultFromGroup( group ).name;
        CHECK( ( name == mtype_id( "mon_spider_cellar_giant_s" ) ||
                 name == mtype_id( "mon_spider_cellar_giant" ) ||
                 name == mtype_id( "mon_spider_cellar_mom" ) ||
                 name == mtype_id( "mon_spider_cellar_mega" ) ) );
    }
}
