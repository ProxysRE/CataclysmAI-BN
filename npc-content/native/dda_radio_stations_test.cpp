#include "avatar.h"
#include "calendar.h"
#include "bodypart.h"
#include "flag.h"
#include "catch/catch.hpp"
#include "cata_utility.h"
#include "coordinates.h"
#include "map/map.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmap_special.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include "map_helpers.h"
#include "map/field_type.h"
#include "map/utils/map_functions.h"
#include "monattack.h"
#include "monster.h"
#include "mtype.h"
#include "item.h"
#include "item_group.h"
#include "itype.h"
#include "vehicle/veh_type.h"
#include "vehicle/vehicle.h"
#include "units.h"
#include "dda_mapgen_corpses.h"
#include "map/mapbuffer_registry.h"

#include <sstream>

#include <algorithm>
#include <array>
#include <string>

TEST_CASE( "farm_material_and_feed_packages_fit_stock_BN_containers", "[dda_npc][dda_locations]" )
{
    for( const auto *group : { "sandbag", "earthbag", "cement_bag", "quicklime_bag",
                              "quicklime_barrel", "saltpeter_canvas_bag_part", "cattlefodder_bag_canvas_50",
                              "birdfood_bag_canvas_60", "box_of_batteries_unopened" } ) {
        INFO( group );
        auto packages = item_group::items_from( item_group_id( group ), calendar::turn );
        REQUIRE( packages.size() == 1 );
        const auto &package = packages.front();
        REQUIRE( package->is_container() );
        REQUIRE( package->type->container != nullptr );
        REQUIRE_FALSE( package->contents.empty() );
        auto volume = 0_ml;
        for( const item &content : package->contents ) {
            volume += content.volume();
        }
        CHECK( volume <= package->type->container->contains );
        if( std::string( group ) == "cement_bag" ) {
            REQUIRE( package->contents.size() == 1 );
            CHECK( package->contents.front().typeId() == itype_id( "material_cement" ) );
            CHECK( package->contents.front().charges == 2800 );
        }
    }
    auto tool = item::spawn( "dremel", calendar::turn );
    REQUIRE( tool->is_tool() );
    REQUIRE( tool->type->tool != nullptr );
    CHECK( tool->type->tool->power_draw == 175000 );
    auto battery = item::spawn( "medium_battery_cell", calendar::turn );
    battery->ammo_set( battery->ammo_default(), 500 );
    tool->put_in( std::move( battery ) );
    CHECK( tool->get_quality( quality_id( "GRIND" ) ) == 2 );
    CHECK( tool->get_quality( quality_id( "SAW_W" ) ) == 1 );
    CHECK( item_group::group_contains_item( item_group_id( "child_hats" ), itype_id( "helmet_bike" ) ) );
    CHECK( furn_id( "f_pallet_brick" ).is_valid() );
    CHECK( furn_id( "f_pallet_cement" ).is_valid() );
    CHECK( furn_id( "f_stack_plank" ).is_valid() );
}

TEST_CASE( "farm_shops_generate_all_quadrants_roofs_ladders_and_source_corpse", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int variant = 0; variant < 2; ++variant ) {
        const int origin_x = 1020 + variant * 6;
        for( int row = 0; row < 2; ++row ) {
            for( int column = 0; column < 2; ++column ) {
                const auto slot = std::to_string( 1 + row * 2 + column );
                const auto name = std::string( variant ? "farm_supply_looted_" : "farm_supply_" ) + slot;
                const auto ground = oter_id( name + "_north" );
                const auto roof = oter_id( "farm_supply_roof_" + slot + "_north" );
                REQUIRE( ground.is_valid() );
                REQUIRE( roof.is_valid() );
                buffer.ter_set( tripoint_abs_omt( origin_x + column, 1020 + row, 0 ), ground );
                buffer.ter_set( tripoint_abs_omt( origin_x + column, 1020 + row, 1 ), roof );
            }
        }
        for( int row = 0; row < 2; ++row ) {
            for( int column = 0; column < 2; ++column ) {
                INFO( "farm variant=" << variant << " row=" << row << " column=" << column );
                auto generated = map( 2 );
                generated.load( project_to<coords::sm>( point_abs_omt( origin_x + column, 1020 + row ) ), false );
                CHECK( generated.ter( tripoint_bub_ms( 0, 0, 0 ) ) != ter_id( "t_null" ) );
                CHECK( generated.ter( tripoint_bub_ms( 0, 0, 1 ) ) != ter_id( "t_null" ) );
                if( row == 0 ) {
                    CHECK( generated.ter( tripoint_bub_ms( 0, 0, 0 ) ) == ter_id( "t_pavement" ) );
                }
                if( row == 1 && column == 1 ) {
                    CHECK( generated.ter( tripoint_bub_ms( 0, 0, 0 ) ) == ter_id( "t_thconc_floor" ) );
                    CHECK( generated.ter( tripoint_bub_ms( 0, 0, 1 ) ) == ter_id( "t_flat_roof" ) );
                }
                if( row == 1 && column == 0 ) {
                    CHECK( generated.ter( tripoint_bub_ms( 0, 21, 0 ) ) == ter_id( "t_ladder_up" ) );
                    CHECK( generated.ter( tripoint_bub_ms( 0, 21, 1 ) ) == ter_id( "t_ladder_down" ) );
                    if( variant == 1 ) {
                        int bodies = 0;
                        for( const item &entry : generated.i_at( tripoint_bub_ms( 7, 18, 0 ) ) ) {
                            bodies += entry.is_corpse();
                        }
                        CHECK( bodies == 1 );
                    }
                }
            }
        }
    }
}

TEST_CASE( "stocked_pond_group_uses_stock_BN_species_and_valid_pack_sizes", "[dda_npc][dda_locations]" )
{
    const auto id = mongroup_id( "GROUP_STOCKED_POND" );
    REQUIRE( id.is_valid() );
    CHECK( id->is_animal );
    const auto species = std::array<mtype_id, 4>{ mtype_id( "mon_fish_rainbow_trout" ),
                         mtype_id( "mon_fish_sbass" ), mtype_id( "mon_fish_perch" ), mtype_id( "mon_fish_salmon" ) };
    for( const auto &fish : species ) {
        REQUIRE( fish.is_valid() );
    }
    const auto restore_turn = restore_on_out_of_scope<time_point>( calendar::turn );
    for( const int hour : { 0, 6, 12, 18 } ) {
        calendar::turn = calendar::start_of_cataclysm + 1_days + time_duration::from_hours( hour );
        for( int attempt = 0; attempt < 100; ++attempt ) {
            const auto spawn = MonsterGroupManager::GetResultFromGroup( id );
            CHECK( std::find( species.begin(), species.end(), spawn.name ) != species.end() );
            CHECK( spawn.pack_size >= 1 );
            CHECK( spawn.pack_size <= ( spawn.name == mtype_id( "mon_fish_salmon" ) ? 6 : 3 ) );
        }
    }
}

TEST_CASE( "source_corpse_mapgen_keeps_species_age_and_empty_groups", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_turn = restore_on_out_of_scope<time_point>( calendar::turn );
    calendar::turn = calendar::start_of_cataclysm + 10_days;
    auto &actor = get_avatar();
    auto scratch = mapgen_constructor( MAPBUFFER_REGISTRY.get( actor.get_dimension() ) );
    scratch.reset_scratch_omt( tripoint_abs_omt( 0, 0, 0 ), ter_id( "t_floor" ),
                              furn_id( "f_null" ), trap_id( "tr_null" ) );
    const auto dat = mapgendata( scratch, mapgendata::dummy_settings );
    const auto group = mongroup_id( "FERAL_HUMANS" );
    REQUIRE( group.is_valid() );
    const auto species = MonsterGroupManager::GetMonstersFromGroup( group );
    for( int age : { 0, 3, 30 } ) {
        scratch.i_clear( point_omt_ms( 7, 18 ) );
        auto input = std::istringstream( "{\"group\":\"FERAL_HUMANS\",\"age\":" +
                                       std::to_string( age ) + "}" );
        auto parser = JsonIn( input );
        const auto piece = jmapgen_corpse( parser.get_object() );
        piece.apply( dat, jmapgen_int( 7 ), jmapgen_int( 18 ) );
        auto stack = scratch.i_at( point_omt_ms( 7, 18 ) );
        REQUIRE( stack.size() == 1 );
        for( const item &body : stack ) {
            REQUIRE( body.is_corpse() );
            REQUIRE( body.get_mtype() != nullptr );
            CHECK( std::find( species.begin(), species.end(), body.get_mtype()->id ) != species.end() );
            CHECK( body.birthday() == std::max( calendar::turn - time_duration::from_days( age ),
                                               calendar::start_of_cataclysm ) );
        }
    }
    for( const auto &name : { "GROUP_NULL", "dda_test_missing_corpse_group" } ) {
        auto input = std::istringstream( std::string( "{\"group\":\"" ) + name + "\"}" );
        auto parser = JsonIn( input );
        const auto piece = jmapgen_corpse( parser.get_object() );
        piece.apply( dat, jmapgen_int( 8 ), jmapgen_int( 18 ) );
        CHECK( scratch.i_at( point_omt_ms( 8, 18 ) ).empty() );
    }
}

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

TEST_CASE( "karting_circuit_generates_source_ramps_and_stairs", "[dda_npc][dda_locations]" )
{
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>( disable_mapgen );
    disable_mapgen = false;
    auto &actor = get_avatar();
    actor.reset_all_missions();
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    for( int row = 0; row < 3; ++row ) {
        for( int column = 0; column < 3; ++column ) {
            for( int z = 0; z < 3; ++z ) {
                const auto name = "karting_" + std::to_string( row ) + "_" +
                                  std::to_string( column ) + "_" + std::to_string( z ) + "_north";
                REQUIRE( oter_id( name ).is_valid() );
                buffer.ter_set( tripoint_abs_omt( 900 + column, 900 + row, z ), oter_id( name ) );
            }
        }
    }
    // Each pair uses the exact same source x/y on the two elevations.
    const auto ramps = std::array<std::array<int, 3>, 48> {{
            {{32, 9, 0}},
            {{33, 9, 1}},
            {{32, 10, 0}},
            {{33, 10, 1}},
            {{32, 11, 0}},
            {{33, 11, 1}},
            {{32, 12, 0}},
            {{33, 12, 1}},
            {{19, 21, 0}},
            {{20, 21, 0}},
            {{21, 21, 0}},
            {{22, 21, 0}},
            {{19, 22, 1}},
            {{20, 22, 1}},
            {{21, 22, 1}},
            {{22, 22, 1}},
            {{39, 22, 1}},
            {{40, 22, 1}},
            {{41, 22, 1}},
            {{42, 22, 1}},
            {{39, 23, 0}},
            {{40, 23, 0}},
            {{41, 23, 0}},
            {{42, 23, 0}},
            {{19, 34, 1}},
            {{20, 34, 1}},
            {{21, 34, 1}},
            {{22, 34, 1}},
            {{19, 35, 0}},
            {{20, 35, 0}},
            {{21, 35, 0}},
            {{22, 35, 0}},
            {{29, 35, 0}},
            {{30, 35, 0}},
            {{31, 35, 0}},
            {{32, 35, 0}},
            {{49, 35, 1}},
            {{50, 35, 1}},
            {{51, 35, 1}},
            {{52, 35, 1}},
            {{29, 36, 1}},
            {{30, 36, 1}},
            {{31, 36, 1}},
            {{32, 36, 1}},
            {{49, 36, 0}},
            {{50, 36, 0}},
            {{51, 36, 0}},
            {{52, 36, 0}},
        }};
    for( int row = 0; row < 3; ++row ) {
        for( int column = 0; column < 3; ++column ) {
            auto generated = map( 2 );
            generated.load( project_to<coords::sm>( point_abs_omt( 900 + column, 900 + row ) ), false );
            for( const auto &ramp : ramps ) {
                if( ramp[0] / 24 != column || ramp[1] / 24 != row ) {
                    continue;
                }
                INFO( "ramp source=" << ramp[0] << "," << ramp[1] );
                CHECK( generated.ter( tripoint_bub_ms( ramp[0] % 24, ramp[1] % 24, 0 ) ) == ter_id( ramp[2] ? "t_ramp_up_high" : "t_ramp_up_low" ) );
                CHECK( generated.ter( tripoint_bub_ms( ramp[0] % 24, ramp[1] % 24, 1 ) ) == ter_id( ramp[2] ? "t_ramp_down_high" : "t_ramp_down_low" ) );
            }
            if( row == 2 && column == 1 ) {
                CHECK( generated.ter( tripoint_bub_ms( 12, 10, 0 ) ) == ter_id( "t_wood_stairs_up" ) );
                CHECK( generated.ter( tripoint_bub_ms( 12, 10, 1 ) ) == ter_id( "t_wood_stairs_down" ) );
            }
        }
    }
}

TEST_CASE( "karting_vehicle_and_cash_dependencies_are_native_bn_definitions", "[dda_npc][dda_locations]" )
{
    REQUIRE( overmap_special_id( "o_karting_l" ).is_valid() );
    CHECK( overmap_special_id( "o_karting_l" )->has_flag( "UNIQUE" ) );
    CHECK_FALSE( overmap_special_id( "o_karting_l" )->has_flag( "OVERMAP_UNIQUE" ) );
    REQUIRE( vproto_id( "go_kart" ).is_valid() );
    const auto &kart = vproto_id( "go_kart" ).obj();
    REQUIRE( kart.parts.size() == 16 );
    for( const auto &part : kart.parts ) {
        CHECK( part.part.is_valid() );
    }
    REQUIRE( kart.blueprint != nullptr );
    CHECK( kart.blueprint->part_count() == 16 );
    for( const auto *name : { "cash_register_full", "cash_register_looted", "cash_register_empty",
                             "cash_register_random" } ) {
        CHECK( item_group::group_is_defined( item_group_id( name ) ) );
    }
    CHECK( itype_id( "cash_register" ).is_valid() );
    CHECK( itype_id( "money_bundle" ).is_valid() );
    auto cash = item::spawn( "cash_register", calendar::start_of_cataclysm );
    CHECK( cash->is_container() );
    for( const auto *name : { "cash_register_full", "cash_register_looted", "cash_register_empty", "cash_register_random" } ) {
        for( int attempt = 0; attempt < 20; ++attempt ) {
            auto registers = item_group::items_from( item_group_id( name ), calendar::turn );
            REQUIRE( registers.size() == 1 );
            CHECK( registers.front()->typeId() == itype_id( "cash_register" ) );
            auto volume = 0_ml;
            for( const item &entry : registers.front()->contents ) {
                volume += entry.volume();
            }
            CHECK( volume <= registers.front()->type->container->contains );
        }
    }
}
