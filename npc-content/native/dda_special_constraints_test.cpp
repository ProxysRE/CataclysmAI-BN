#include "catch/catch.hpp"
#include "json.h"
#include "debug.h"
#include "overmap/om_direction.h"
#include "overmap/overmap.h"
#include "overmap/overmap_special.h"

#include <memory>
#include <utility>
#include <sstream>

TEST_CASE( "fixed_special_frontage_constraints_do_not_replace_terrain", "[dda_npc][dda_locations]" )
{
    std::istringstream source( R"({"type":"overmap_special","id":"dda_frontage_fixture","locations":["land"],"occurrences":[0,0],"overmaps":[{"point":[0,0,0],"overmap":"forest"},{"point":[1,0,0],"locations":["land","road"]}]})" );
    JsonIn input( source );
    // Placement stores this ID and later resolves it through the factory.
    // Register the fixture exactly as loaded game data before exercising placement.
    overmap_specials::load( input.get_object(), "test" );
    const overmap_special_id fixture_id( "dda_frontage_fixture" );
    REQUIRE( fixture_id.is_valid() );
    // Finalize only this new fixture, as the factory finalizer does for its entries.
    auto &special = const_cast<overmap_special &>( fixture_id.obj() );
    special.finalize();
    special.check();
    special.finalize_mapgen_parameters();
    REQUIRE( special.required_locations().size() == 2 );
    REQUIRE( special.all_terrains().size() == 1 );
    CHECK( special.all_terrains().front() == oter_str_id( "forest" ) );
    REQUIRE( special.preview_terrains().size() == 1 );
    CHECK( special.get_terrain_at( tripoint_rel_omt( 1, 0, 0 ) ).is_null() );

    auto om = std::make_unique<overmap>( point_abs_om( 0, 0 ) );
    const tripoint_om_omt origin( 40, 40, 0 );
    const oter_id field( "field" );
    const oter_id water( "river_center" );
    REQUIRE( field.is_valid() );
    REQUIRE( water.is_valid() );
    for( const auto dir : { om_direction::type::north, om_direction::type::east,
                           om_direction::type::south, om_direction::type::west } ) {
        const auto frontage = origin + om_direction::rotate( tripoint_rel_omt( 1, 0, 0 ), dir );
        om->ter_set( origin, field );
        om->ter_set( frontage, water );
        CHECK_FALSE( om->can_place_special( special, origin, dir, false ) );
        om->ter_set( frontage, field );
        REQUIRE( om->can_place_special( special, origin, dir, false ) );
        const auto used = om->place_special( special, origin, dir, city(), false, false );
        REQUIRE( used.size() == 1 );
        CHECK( used.front() == origin );
        CHECK( om->ter( origin ) == oter_id( "forest" ) );
        CHECK( om->ter( frontage ) == field );
    }
}

TEST_CASE( "constraint_only_support_keeps_fixed_special_validation", "[dda_npc][dda_locations]" )
{
    for( const auto &fixture : {
        std::pair<std::string, std::string>(
            R"([{"point":[0,0,0],"overmap":"dda_missing_terrain"}])", "is invalid" ),
        std::pair<std::string, std::string>(
            R"([{"point":[0,0,0],"overmap":"forest"},{"point":[0,0,0],"locations":["land"]}])", "is duplicated" ),
        std::pair<std::string, std::string>(
            R"([{"point":[0,0,0],"overmap":"forest"},{"point":[1,0,0],"locations":["dda_missing_location"]}])", "location" )
    } ) {
        std::istringstream source( std::string( R"({"type":"overmap_special","locations":["land"],"occurrences":[0,0],"overmaps":)" ) + fixture.first + "}" );
        JsonIn input( source );
        overmap_special special;
        special.id = overmap_special_id( "dda_bad_frontage_fixture" );
        special.load( input.get_object(), "test" );
        special.finalize();
        const auto message = capture_debugmsg_during( [&special]() { special.check(); } );
        CHECK( message.find( fixture.second ) != std::string::npos );
    }
}
