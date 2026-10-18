#include "catch/catch.hpp"
#include "calendar.h"
#include "item.h"
#include "item_contents.h"
#include "item_group.h"
#include "itype.h"
#include "mongroup.h"
#include "mtype.h"
#include "units.h"

TEST_CASE( "eldercare_cigar_boxes_fit_BN_containers_and_single_cigar_charges", "[dda_npc][dda_locations]" )
{
    for( int attempt = 0; attempt < 100; ++attempt ) {
        const auto boxes = item_group::items_from( item_group_id( "cigar_box_opened" ), calendar::turn );
        REQUIRE( boxes.size() == 1 );
        const auto &box = boxes.front();
        REQUIRE( box->typeId() == itype_id( "box_medium" ) );
        REQUIRE( box->type->container != nullptr );
        auto volume = 0_ml;
        for( const auto *content : box->contents.all_items_top() ) {
            volume += content->volume();
            if( content->typeId() == itype_id( "cigar" ) ) {
                CHECK( content->charges <= 25 );
            }
        }
        CHECK( volume <= box->type->container->contains );
    }
}

TEST_CASE( "eldercare_staff_holder_and_loot_use_BN_items", "[dda_npc][dda_locations]" )
{
    const auto holder = item::spawn( "lanyard", calendar::turn );
    REQUIRE( holder->is_armor() );
    CHECK( holder->get_storage() == 150_ml );
    for( const auto *name : { "SUS_science_personal_effects", "feral_sapien_death_drops_spear",
                             "lab_mutagen_ingredients_fridge", "nursing_home_clothes" } ) {
        INFO( name );
        REQUIRE( item_group::group_is_defined( item_group_id( name ) ) );
        for( int attempt = 0; attempt < 25; ++attempt ) {
            const auto stock = item_group::items_from( item_group_id( name ), calendar::turn );
            for( const auto &entry : stock ) {
                REQUIRE( static_cast<bool>( entry ) );
                CHECK_FALSE( entry->is_null() );
                CHECK( entry->typeId().is_valid() );
            }
        }
    }
}

TEST_CASE( "eldercare_pigeon_eggs_hatch_chicks_that_grow_into_pigeons", "[dda_npc][dda_locations]" )
{
    const auto adult = mtype_id( "mon_pigeon" );
    const auto chick = mtype_id( "mon_pigeon_chick" );
    REQUIRE( adult.is_valid() );
    REQUIRE( chick.is_valid() );
    CHECK( adult->baby_egg == itype_id( "egg_pigeon" ) );
    CHECK( adult->baby_count == 3 );
    CHECK( adult->reproduces );
    CHECK( chick->upgrade_into == adult );
    const auto egg = item::spawn( "egg_pigeon", calendar::turn );
    CHECK( egg->volume() == 15_ml );
    const auto hatch = mongroup_id( "GROUP_EGG_PIGEON" );
    REQUIRE( hatch.is_valid() );
    for( int attempt = 0; attempt < 50; ++attempt ) {
        CHECK( MonsterGroupManager::GetResultFromGroup( hatch ).name == chick );
    }
}
