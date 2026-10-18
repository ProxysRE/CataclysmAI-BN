#include "catch/catch.hpp"
#include "flag.h"
#include "calendar.h"
#include "item_contents.h"
#include "item.h"
#include "item_group.h"
#include "itype.h"
#include "text_snippets.h"
#include "vehicle/veh_type.h"
#include "vehicle/vehicle.h"
#include <string>

TEST_CASE( "eldercare_medical_objects_and_generators_install_all_parts", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "dda_eldercare_bed_small", "dda_eldercare_medical_cart",
                             "dda_eldercare_diesel_generator", "dda_eldercare_military_generator",
                             "dda_eldercare_gasoline_generator", "dda_eldercare_cargo_van" } ) {
        INFO( name );
        const auto id = vproto_id( name );
        REQUIRE( id.is_valid() );
        const auto &prototype = id.obj();
        const int expected = std::string( name ) == "dda_eldercare_cargo_van" ? 101 :
                             std::string( name ).find( "generator" ) != std::string::npos ? 6 : 3;
        REQUIRE( prototype.parts.size() == expected );
        for( const auto &part : prototype.parts ) {
            REQUIRE( part.part.is_valid() );
        }
        REQUIRE( prototype.blueprint != nullptr );
        CHECK( prototype.blueprint->part_count() == expected );
    }
}

TEST_CASE( "eldercare_lab_records_use_real_BN_readable_snippets", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "lab_postit_bio", "lab_postit_blob", "lab_postit_migo", "lab_postit_portal",
                             "lab_postit_tech", "lab_file_bio", "lab_file_portal", "lab_file_psych", "lab_file_sec" } ) {
        INFO( name );
        const auto note = item::spawn( name, calendar::turn );
        REQUIRE( note );
        CHECK( note->has_flag( flag_id( "SNIPPET_NEEDS_LITERACY" ) ) );
        REQUIRE_FALSE( note->snip_id.is_null() );
        REQUIRE( SNIPPET.has_snippet_with_id( note->snip_id ) );
        CHECK_FALSE( SNIPPET.get_snippet_ref_by_id( note->snip_id ).empty() );
    }
    for( int attempt = 0; attempt < 100; ++attempt ) {
        const auto records = item_group::items_from( item_group_id( "lab_files_generic" ), calendar::turn );
        REQUIRE( records.size() == 1 );
        CHECK( SNIPPET.has_snippet_with_id( records.front()->snip_id ) );
    }
}

TEST_CASE( "eldercare_mutation_book_groups_reuse_BN_recipe_books", "[dda_npc][dda_locations]" )
{
    for( const auto *name : { "common_mutation_books", "rare_mutation_books" } ) {
        for( int attempt = 0; attempt < 100; ++attempt ) {
            const auto books = item_group::items_from( item_group_id( name ), calendar::turn );
            REQUIRE( books.size() == 1 );
            CHECK( books.front()->is_book() );
        }
    }
    const auto saline = item_group::items_from( item_group_id( "saline_bottle_random" ), calendar::turn );
    REQUIRE( saline.size() == 1 );
    REQUIRE( saline.front()->typeId() == itype_id( "bottle_plastic_small" ) );
    REQUIRE_FALSE( saline.front()->contents.empty() );
    CHECK( saline.front()->contents.front().typeId() == itype_id( "saline" ) );
    CHECK( saline.front()->contents.front().charges == 5 );
}
