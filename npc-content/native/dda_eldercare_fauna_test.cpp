#include "catch/catch.hpp"
#include "calendar.h"
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
