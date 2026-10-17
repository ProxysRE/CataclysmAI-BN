#include "avatar.h"
#include "calendar.h"
#include "bodypart.h"
#include "flag.h"
#include "catch/catch.hpp"
#include "cata_utility.h"
#include "coordinates.h"
#include "map/map.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include "map_helpers.h"
#include "map/field_type.h"
#include "map/utils/map_functions.h"
#include "monattack.h"
#include "monster.h"
#include "mtype.h"
#include "item.h"
#include "units.h"

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

TEST_CASE( "hotel_technical_enclosures_receive_source_roof_caps", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int column = 0; column < 3; ++column ) {
        const auto suffix = std::to_string( 9 - column ) + "_north";
        const auto lower = oter_id( "hotel_tower_roof_1_" + suffix );
        const auto upper = oter_id( "hotel_tower_6_1_" + suffix );
        REQUIRE( lower.is_valid() );
        REQUIRE( upper.is_valid() );
        buffer.ter_set( tripoint_abs_omt( 720 + column, 720, 4 ), lower );
        buffer.ter_set( tripoint_abs_omt( 720 + column, 720, 5 ), upper );
    }
    for( int column = 0; column < 3; ++column ) {
        INFO( "hotel column=" << column );
        auto generated = map( 2 );
        generated.load( project_to<coords::sm>( point_abs_omt( 720 + column, 720 ) ), false );
        CHECK( generated.ter( tripoint_bub_ms( 12, 0, 5 ) ) == ter_id( "t_open_air" ) );
        if( column == 1 ) {
            CHECK( generated.ter( tripoint_bub_ms( 12, 10, 5 ) ) == ter_id( "t_open_air" ) );
        } else {
            const auto x = column == 0 ? 5 : 17;
            CHECK( generated.ter( tripoint_bub_ms( x, 10, 5 ) ) == ter_id( "t_flat_roof" ) );
            CHECK( generated.ter( tripoint_bub_ms( x, 9, 5 ) ) == ter_id( "t_gutter" ) );
            CHECK_FALSE( generated.has_flag( "GOES_UP", tripoint_bub_ms( x, 10, 5 ) ) );
        }
    }
}

TEST_CASE( "shopping_plaza_roofs_generate_over_existing_bn_stores", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int y = 0; y < 2; ++y ) {
        for( int x = 0; x < 6; ++x ) {
            const auto suffix = std::to_string( x + 1 ) + "_north";
            const auto lower = oter_id( std::string( "s_shoppingplaza_" ) + ( y == 0 ? "a" : "b" ) + suffix );
            REQUIRE( lower.is_valid() );
            buffer.ter_set( tripoint_abs_omt( 760 + x, 760 + y, 0 ), lower );
            if( y == 1 || x == 5 ) {
                const auto upper = oter_id( std::string( "s_shoppingplaza_" ) + ( y == 0 ? "A" : "B" ) + suffix );
                REQUIRE( upper.is_valid() );
                buffer.ter_set( tripoint_abs_omt( 760 + x, 760 + y, 1 ), upper );
            }
        }
    }
    for( int y = 0; y < 2; ++y ) {
        for( int x = 0; x < 6; ++x ) {
            if( y == 0 && x != 5 ) {
                continue;
            }
            INFO( "plaza roof=" << x << "," << y );
            auto generated = map( 2 );
            generated.load( project_to<coords::sm>( point_abs_omt( 760 + x, 760 + y ) ), false );
            CHECK( generated.ter( tripoint_bub_ms( 12, 12, 1 ) ) == ter_id( "t_flat_roof" ) );
        }
    }
}

TEST_CASE( "rural_church_generates_basement_steeple_and_real_bell_terminal", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto names = std::array<std::string, 4>{ "rural_church_basement", "rural_church", "rural_church_steeple", "rural_church_steeple_roof" };
    buffer.ter_set( tripoint_abs_omt( 820, 820, 0 ), oter_id( "rural_church_parking_north" ) );
    for( int z = -1; z <= 2; ++z ) {
        const auto terrain = oter_id( names[z + 1] + "_north" );
        REQUIRE( terrain.is_valid() );
        buffer.ter_set( tripoint_abs_omt( 821, 820, z ), terrain );
    }
    auto generated = map( 2 );
    generated.load( project_to<coords::sm>( point_abs_omt( 821, 820 ) ), false );
    CHECK( generated.ter( tripoint_bub_ms( 1, 7, 0 ) ) == ter_id( "t_stairs_up" ) );
    CHECK( generated.ter( tripoint_bub_ms( 1, 7, 1 ) ) == ter_id( "t_stairs_down" ) );
    CHECK( generated.ter( tripoint_bub_ms( 7, 21, 0 ) ) == ter_id( "t_stairs_down" ) );
    CHECK( generated.ter( tripoint_bub_ms( 7, 21, -1 ) ) == ter_id( "t_stairs_up" ) );
    CHECK( generated.ter( tripoint_bub_ms( 4, 6, -1 ) ) == ter_id( "t_stairs_up" ) );
    CHECK( generated.computer_at( tripoint_bub_ms( 4, 6, 1 ) ) != nullptr );
}

TEST_CASE( "XEDRA_creature_profile_and_particles_load_without_changing_legacy_defaults", "[dda_npc][dda_locations]" )
{
    const auto creature = mtype_id( "mon_twisting_mass" );
    REQUIRE( creature.is_valid() );
    const auto &profile = creature.obj();
    CHECK( profile.ranged_pull_range == 5 );
    CHECK( profile.ranged_pull_weight_ratio == Approx( 3.0f ) );
    CHECK( profile.ranged_pull_full_range );
    CHECK( profile.ranged_pull_use_grab_strength );
    CHECK( profile.ranged_pull_respect_seatbelts );
    CHECK( profile.grab_strength == 35 );
    const auto &legacy = mtype_id( "mon_zombie" ).obj();
    CHECK( legacy.ranged_pull_range == 3 );
    CHECK( legacy.ranged_pull_weight_ratio == 0.0f );
    CHECK_FALSE( legacy.ranged_pull_full_range );
    CHECK_FALSE( legacy.ranged_pull_use_grab_strength );
    CHECK_FALSE( legacy.ranged_pull_respect_seatbelts );
    const auto particles = field_type_str_id( "fd_twisting_mass_dust" );
    REQUIRE( particles.is_valid() );
    REQUIRE( particles.obj().intensity_levels.size() == 1 );
    CHECK( particles.obj().intensity_levels.front().light_emitted == 160 );
    CHECK( emit_id( "emit_twisting_mass_dust" ).is_valid() );
    CHECK( item( itype_id( "inert_glowing_string" ), calendar::turn ).typeId() ==
           itype_id( "inert_glowing_string" ) );
}

TEST_CASE( "XEDRA_ranged_pull_rejects_overweight_target_before_movement", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    clear_map();
    build_test_map( ter_id( "t_floor" ) );
    auto &actor = get_avatar();
    actor.setpos( map_local_to_abs( get_map(), tripoint_bub_ms( 60, 60, 0 ) ) );
    auto &critter = spawn_test_monster( "mon_twisting_mass", tripoint_bub_ms( 65, 60, 0 ) );
    critter.set_dest( actor.bub_pos() );
    REQUIRE( critter.attack_target() == &actor );
    auto lightweight = *critter.type;
    const auto restore_type = restore_on_out_of_scope<const mtype *>( critter.type );
    lightweight.weight = units::from_gram( 1 );
    critter.type = &lightweight;
    REQUIRE( actor.get_weight() > critter.get_weight() * 3.0f );
    const auto before = actor.bub_pos();
    const auto moves = critter.moves;
    CHECK_FALSE( mattack::ranged_pull( &critter ) );
    CHECK( actor.bub_pos() == before );
    CHECK( critter.moves == moves );
}

TEST_CASE( "XEDRA_activity_suit_casual_state_reduces_coverage_and_loses_full_body_seals", "[dda_npc][dda_locations]" )
{
    auto suit = item( itype_id( "xedra_enviro_suit" ), calendar::turn );
    const auto torso = bodypart_str_id( "torso" ).id();
    const auto leg = bodypart_str_id( "leg_l" ).id();
    const auto foot = bodypart_str_id( "foot_r" ).id();
    REQUIRE( suit.is_armor() );
    REQUIRE( suit.covers( torso ) );
    REQUIRE( suit.covers( leg ) );
    suit.set_var( "port_state_marker", std::string( "preserve" ) );
    const auto seals = std::array<std::string, 4>{ "RAINPROOF", "GAS_PROOF", "RAD_PROOF", "ELECTRIC_IMMUNE" };
    for( const auto &seal : seals ) {
        REQUIRE( suit.has_flag( flag_id( seal ) ) );
    }
    suit.convert( itype_id( "xedra_enviro_suit_casual" ) );
    CHECK( suit.typeId() == itype_id( "xedra_enviro_suit_casual" ) );
    CHECK_FALSE( suit.covers( torso ) );
    CHECK( suit.covers( leg ) );
    CHECK( suit.covers( foot ) );
    for( const auto &seal : seals ) {
        CHECK_FALSE( suit.has_flag( flag_id( seal ) ) );
    }
    CHECK( suit.get_var( "port_state_marker" ) == "preserve" );
    suit.convert( itype_id( "xedra_enviro_suit" ) );
    CHECK( suit.covers( torso ) );
    for( const auto &seal : seals ) {
        CHECK( suit.has_flag( flag_id( seal ) ) );
    }
    CHECK( suit.get_var( "port_state_marker" ) == "preserve" );
}
