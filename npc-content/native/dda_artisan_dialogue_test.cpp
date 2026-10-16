#include "artisan_bn_bridge.h"
#include "artisan_items.h"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "condition.h"
#include "dialogue.h"
#include "json.h"
#include "lighthouse_quest_updates.h"
#include "map/map.h"
#include "mission.h"
#include "mapgen/mapgen_functions.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "npc.h"
#include "state_helpers.h"
#include "vehicle/vehicle.h"

#include <sstream>
#include <limits>

TEST_CASE( "community_chance_conditions_read_current_world_values", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto previous = g->dda_global_variables;
    const auto restore_globals = on_out_of_scope( [previous]() { g->dda_global_variables = previous; } );
    auto &actor = get_avatar();
    auto speaker = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto input = std::istringstream( R"({"dda_one_in_chance":{"op":"variable","name":"exodii_mission_wh_chance","actor":"global"}})" );
    auto parser = JsonIn( input );
    const auto chance = conditional_t<dialogue>( parser.get_object() );
    g->dda_global_variables["exodii_mission_wh_chance"] = "1";
    CHECK( chance( conversation ) );
    g->dda_global_variables["exodii_mission_wh_chance"] = "0";
    CHECK( chance( conversation ) );
    g->dda_global_variables["exodii_mission_wh_chance"] = "1.9";
    CHECK( chance( conversation ) );
    g->dda_global_variables["exodii_mission_wh_chance"] = "2147483648";
    CHECK_FALSE( chance( conversation ) );
    conversation.alpha = nullptr;
    CHECK_FALSE( chance( conversation ) );
}

TEST_CASE( "conditional_community_effects_choose_one_branch_at_execution", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto speaker = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto input = std::istringstream( R"({"effect":{"dda_if":{"condition":{"u_has_var":"ready","value":"yes"},"then":{"effect":[{"u_add_var":"selected","value":"true"},{"dda_set_npc_opinion":{"target":"trust","expression":{"op":"add","args":[{"op":"npc_opinion","name":"trust"},{"op":"literal","value":1}]}}}]},"else":{"effect":{"u_add_var":"selected","value":"false"}}}}})" );
    auto parser = JsonIn( input );
    const auto conditional = talk_effect_t( parser.get_object() );
    REQUIRE( conditional.effects.size() == 1 );
    speaker.op_of_u.trust = 0;
    conditional.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ) == "false" );
    CHECK( speaker.op_of_u.trust == 0 );
    actor.set_value( "npctalk_var_ready", "yes" );
    conditional.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ) == "true" );
    CHECK( speaker.op_of_u.trust == 1 );
    actor.set_value( "npctalk_var_ready", "no" );
    conditional.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ) == "false" );
    CHECK( speaker.op_of_u.trust == 1 );
}

TEST_CASE( "community_cataclysm_age_uses_world_calendar_origin", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    calendar::turn = calendar::start_of_cataclysm + 60_days;
    auto input = std::istringstream( R"({"op":"divide","args":[{"op":"subtract","args":[{"op":"now"},{"op":"cataclysm"}]},{"op":"literal","value":86400}]})" );
    auto parser = JsonIn( input );
    const auto age = dda_port::read_expression( parser.get_object() );
    CHECK( dda_port::evaluate_for_player( age, get_avatar() ) == 60.0 );
}

TEST_CASE( "community_location_conditions_match_rotated_overmap_types", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto speaker = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto input = std::istringstream( R"({"dda_at_om_location":{"actor":"npc","terrain":"lighthouse_ground"}})" );
    auto parser = JsonIn( input );
    const auto arrived = conditional_t<dialogue>( parser.get_object() );
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto location = actor.abs_omt_pos() + tripoint_rel_omt( 3, 0, 0 );
    speaker.set_fake( true );
    speaker.setpos( project_to<coords::ms>( location ) );
    for( const auto *name : { "lighthouse_ground_north", "lighthouse_ground_east", "lighthouse_ground_south", "lighthouse_ground_west" } ) {
        const auto terrain = oter_id( name );
        REQUIRE( terrain.is_valid() );
        buffer.ter_set( location, terrain );
        CHECK( arrived( conversation ) );
    }
    buffer.ter_set( location, oter_id( "field" ) );
    CHECK_FALSE( arrived( conversation ) );
    conversation.beta = nullptr;
    CHECK_FALSE( arrived( conversation ) );
}

TEST_CASE( "community_global_variables_are_shared_and_saved_with_the_world", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto previous = g->dda_global_variables;
    const auto restore_globals = on_out_of_scope( [previous]() {
        g->dda_global_variables = previous;
    } );
    g->dda_global_variables.clear();
    auto &actor = get_avatar();
    auto first = npc{};
    auto second = npc{};
    actor.set_value( "npctalk_var_hub01_shared", "999" );
    first.set_value( "npctalk_var_hub01_shared", "888" );
    const auto shared = dda_port::expression{ .op = "variable", .name = "hub01_shared", .global_actor = true };
    CHECK( dda_port::evaluate_for_player( shared, actor, &first ) == 0.0 );
    CHECK( g->dda_global_variables.empty() );
    auto input = std::istringstream( R"({"effect":{"dda_set_variable":{"target":"hub01_shared","actor":"global","expression":{"op":"literal","value":3.5}}}})" );
    auto parser = JsonIn( input );
    const auto assignment = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &first;
    REQUIRE( assignment.effects.size() == 1 );
    assignment.effects.front()( conversation );
    CHECK( dda_port::evaluate_for_player( shared, actor, &first ) == 3.5 );
    CHECK( dda_port::evaluate_for_player( shared, actor, &second ) == 3.5 );
    CHECK( actor.get_value( "npctalk_var_hub01_shared" ) == "999" );
    CHECK( first.get_value( "npctalk_var_hub01_shared" ) == "888" );
    auto string_input = std::istringstream( R"({"effect":{"dda_set_global_string":{"target":"hub01_trade","value":"yes"}}})" );
    auto string_parser = JsonIn( string_input );
    const auto string_assignment = talk_effect_t( string_parser.get_object() );
    REQUIRE( string_assignment.effects.size() == 1 );
    string_assignment.effects.front()( conversation );
    auto line_input = std::istringstream( R"({"dda_global_string":{"name":"hub01_trade","value":"yes"},"yes":"unlocked","no":"locked"})" );
    auto line_parser = JsonIn( line_input );
    const auto line = dynamic_line_t( line_parser.get_object() );
    conversation.beta = &second;
    CHECK( line( conversation ) == "unlocked" );
    g->dda_global_variables["hub01_trade"] = "no";
    CHECK( line( conversation ) == "locked" );
    const auto exists = dda_port::expression{ .op = "has_var", .args = { shared } };
    CHECK( dda_port::evaluate_for_player( exists, actor ) == 1.0 );
    auto saved = std::stringstream{};
    g->serialize_master( saved );
    const auto saved_text = saved.str();
    REQUIRE( saved_text.find( "dda_global_variables" ) != std::string::npos );
    g->dda_global_variables["stale"] = "discard me";
    g->unserialize_master( saved );
    CHECK( g->dda_global_variables.size() == 2 );
    CHECK( g->dda_global_variables.at( "hub01_shared" ) == "3.5" );
    CHECK( g->dda_global_variables.at( "hub01_trade" ) == "no" );
    auto legacy_text = saved_text;
    legacy_text.replace( legacy_text.find( "dda_global_variables" ), std::string( "dda_global_variables" ).size(), "unknown_legacy_field" );
    auto legacy = std::istringstream( legacy_text );
    g->unserialize_master( legacy );
    CHECK( g->dda_global_variables.empty() );
    CHECK( dda_port::evaluate_for_player( exists, actor ) == 0.0 );
}

TEST_CASE( "community_opinion_expressions_use_real_npc_relationships", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto speaker = npc{};
    speaker.op_of_u.anger = 4;
    speaker.op_of_u.fear = -2;
    speaker.op_of_u.trust = 6;
    speaker.op_of_u.value = 3;
    speaker.set_value( "npctalk_var_anger", "999" );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto input = std::istringstream( R"({"dda_expression":{"op":"greater_equal","args":[{"op":"npc_opinion","name":"anger"},{"op":"literal","value":5}]}})" );
    auto parser = JsonIn( input );
    const auto angry = conditional_t<dialogue>( parser.get_object() );
    CHECK_FALSE( angry( conversation ) );
    auto increment_input = std::istringstream( R"({"effect":{"dda_set_npc_opinion":{"target":"anger","expression":{"op":"add","args":[{"op":"npc_opinion","name":"anger"},{"op":"literal","value":1}]}}}})" );
    auto increment_parser = JsonIn( increment_input );
    const auto increment = talk_effect_t( increment_parser.get_object() );
    REQUIRE( increment.effects.size() == 1 );
    increment.effects.front()( conversation );
    CHECK( speaker.op_of_u.anger == 5 );
    CHECK( angry( conversation ) );
    CHECK( speaker.get_value( "npctalk_var_anger" ) == "999" );
    CHECK( speaker.op_of_u.fear == -2 );
    CHECK( speaker.op_of_u.trust == 6 );
    CHECK( speaker.op_of_u.value == 3 );
    for( const auto &field : { "fear", "trust", "value" } ) {
        const auto expression = dda_port::expression{ .op = "npc_opinion", .name = field };
        CHECK( dda_port::evaluate_for_player( expression, actor, &speaker ).has_value() );
        CHECK_FALSE( dda_port::evaluate_for_player( expression, actor ).has_value() );
    }
    CHECK( dda_port::store_npc_opinion( speaker, "value", 7.9 ) );
    CHECK( speaker.op_of_u.value == 7 );
    CHECK( dda_port::store_npc_opinion( speaker, "fear", -3.9 ) );
    CHECK( speaker.op_of_u.fear == -3 );
    CHECK_FALSE( dda_port::store_npc_opinion( speaker, "anger", std::numeric_limits<double>::infinity() ) );
    CHECK_FALSE( dda_port::store_npc_opinion( speaker, "anger", 2147483648.0 ) );
    CHECK_FALSE( dda_port::store_npc_opinion( speaker, "unknown", 2 ) );
    CHECK( speaker.op_of_u.anger == 5 );
}

static auto spawn_lighthouse_fisherman( overmapbuffer &buffer, const tripoint_abs_omt &location )
-> shared_ptr_fast<npc> {
    buffer.ter_set( location, oter_id( "field" ) );
    auto input = std::istringstream( R"({"place_nested":[{"chunks":[["NPC_lighthouse_man_spawn",1]],"x":12,"y":21}]})" );
    auto parser = JsonIn( input );
    auto defer = false;
    const auto spawn = add_mapgen_update_func( parser.get_object(), defer );
    REQUIRE_FALSE( defer );
    spawn( location, nullptr );
    const auto people = buffer.get_npcs_near_omt( location, 0 );
    REQUIRE( people.size() == 1 );
    REQUIRE( people.front()->chatbin.first_topic == "TALK_lighthouse_man_1" );
    return people.front();
}

TEST_CASE( "lighthouse_family_spawns_underground_and_returns_through_dialogue", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    const auto original_id = actor.getID();
    const auto restore_id = on_out_of_scope( [&actor, original_id]() {
        actor.setID( original_id, true );
    } );
    actor.setID( character_id( 424245 ), true );
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto giver = spawn_lighthouse_fisherman( buffer, tripoint_abs_omt( 362, 350, 0 ) );
    const auto remove_giver = on_out_of_scope( [&buffer, giver]() {
        buffer.remove_npc( giver->getID() );
    } );
    auto basement = actor.abs_omt_pos() + tripoint_rel_omt( 2, 0, 0 );
    basement.z() = -1;
    const auto basement_type = oter_id( "house_04_basement_north" );
    REQUIRE( basement_type.is_valid() );
    buffer.ter_set( basement, basement_type );
    const auto home = actor.abs_omt_pos() + tripoint_rel_omt( 3, 0, 0 );
    buffer.ter_set( home, oter_id( "lighthouse_ground_north" ) );
    auto *job = mission::reserve_new( mission_type_id( "MISSION_lighthouse_man_3" ), giver->getID() );
    REQUIRE( job );
    giver->chatbin.missions_assigned.push_back( job );
    giver->chatbin.mission_selected = job;
    job->assign( actor );
    REQUIRE( job->get_target() == basement );
    CHECK( giver->chatbin.first_topic == "TALK_lighthouse_man_family" );
    const auto family = buffer.get_npcs_near_omt( basement, 0 );
    REQUIRE( family.size() == 2 );
    const auto remove_family = on_out_of_scope( [&buffer, family]() {
        for( const auto &person : family ) {
            if( person->is_active() ) {
                g->erase_npc( person->getID() );
            }
            buffer.remove_npc( person->getID() );
        }
    } );
    auto father_dialogue = dialogue{};
    father_dialogue.alpha = &actor;
    father_dialogue.beta = giver.get();
    father_dialogue.missions_assigned.push_back( job );
    const auto has_success = [&]() {
        father_dialogue.responses.clear();
        father_dialogue.gen_responses( talk_topic( "TALK_lighthouse_man_family" ) );
        for( const auto &response : father_dialogue.responses ) {
            if( response.success.next_topic.id == "TALK_MISSION_SUCCESS" ) {
                return true;
            }
        }
        return false;
    };
    CHECK_FALSE( has_success() );
    for( const auto &person : family ) {
        CHECK( person->get_fac_id() == faction_id( "fisherman_family" ) );
        const auto start = person->chatbin.first_topic;
        REQUIRE( ( start == "TALK_lighthouse_woman_start" || start == "TALK_lighthouse_girl_start" ) );
        auto conversation = dialogue{};
        conversation.alpha = &actor;
        conversation.beta = person.get();
        conversation.apply_speaker_effects( talk_topic( start ) );
        REQUIRE( person->chatbin.missions_assigned.size() == 1 );
        auto *protection = person->chatbin.missions_assigned.front();
        // The normal conversation setup selects the speaker's assigned mission.
        person->chatbin.mission_selected = protection;
        conversation.missions_assigned.push_back( protection );
        conversation.apply_speaker_effects( talk_topic( start ) );
        CHECK( person->chatbin.missions_assigned.size() == 1 );
        person->setpos( project_to<coords::ms>( home ) );
        conversation.gen_responses( talk_topic( start ) );
        auto returned = false;
        for( const auto &response : conversation.responses ) {
            if( response.success.next_topic.id == "TALK_lighthouse_woman_safe" ||
                response.success.next_topic.id == "TALK_lighthouse_girl_safe" ) {
                response.success.apply( conversation );
                returned = true;
                break;
            }
        }
        REQUIRE( returned );
        CHECK_FALSE( protection->in_progress() );
        CHECK( person->chatbin.missions_assigned.empty() );
    }
    CHECK( actor.get_value( "npctalk_var_flag_safe_lighthouse_woman" ) == "yes" );
    CHECK( actor.get_value( "npctalk_var_flag_safe_lighthouse_girl" ) == "yes" );
    CHECK_FALSE( job->is_complete( giver->getID() ) );
    REQUIRE( has_success() );
    for( const auto &response : father_dialogue.responses ) {
        if( response.success.next_topic.id == "TALK_MISSION_SUCCESS" ) {
            response.success.apply( father_dialogue );
            break;
        }
    }
    CHECK_FALSE( job->in_progress() );
    CHECK( actor.get_value( "npctalk_var_flag_help_lighthouse_family_safe" ) == "yes" );
    CHECK( giver->chatbin.first_topic == "TALK_lighthouse_man_1" );
    CHECK( job->get_follow_up() == mission_type_id( "MISSION_lighthouse_man_4" ) );
}

TEST_CASE( "lighthouse_cleanup_mission_runs_real_start_and_end", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    const auto original_id = actor.getID();
    const auto restore_id = on_out_of_scope( [&actor, original_id]() {
        actor.setID( original_id, true );
    } );
    actor.setID( character_id( 424243 ), true );
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto giver = spawn_lighthouse_fisherman( buffer, tripoint_abs_omt( 358, 350, 0 ) );
    const auto destination = actor.abs_omt_pos() + tripoint_rel_omt( 2, 0, 0 );
    buffer.ter_set( destination, oter_id( "lighthouse_ground_north" ) );
    auto *job = mission::reserve_new( mission_type_id( "MISSION_lighthouse_man_2" ), giver->getID() );
    REQUIRE( job );
    giver->chatbin.missions_assigned.push_back( job );
    actor.set_value( "npctalk_var_count_cleaning_lighthouse_man", "123" );
    job->assign( actor );
    CHECK( giver->chatbin.first_topic == "TALK_lighthouse_man_cleaning" );
    CHECK( giver->get_value( "npctalk_var_count_cleaning_lighthouse_man" ) == "0" );
    CHECK( actor.get_value( "npctalk_var_count_cleaning_lighthouse_man" ) == "123" );
    giver->set_value( "npctalk_var_count_cleaning_lighthouse_man", "6" );
    CHECK_FALSE( job->is_complete( giver->getID() ) );
    giver->set_value( "npctalk_var_count_cleaning_lighthouse_man", "7" );
    REQUIRE( job->is_complete( giver->getID() ) );
    job->wrap_up();
    CHECK_FALSE( job->in_progress() );
    CHECK( giver->chatbin.first_topic == "TALK_lighthouse_man_1" );
    CHECK( giver->get_value( "npctalk_var_count_cleaning_lighthouse_man" ).empty() );
    CHECK( job->get_follow_up() == mission_type_id( "MISSION_lighthouse_man_3" ) );
    buffer.remove_npc( giver->getID() );
}

TEST_CASE( "lighthouse_repair_mission_turn_in_updates_flags_and_lights", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    const auto original_id = actor.getID();
    const auto restore_id = on_out_of_scope( [&actor, original_id]() {
        actor.setID( original_id, true );
    } );
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    actor.setID( character_id( 424244 ), true );
    calendar::turn = calendar::turn_zero + 10_days;
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto giver = spawn_lighthouse_fisherman( buffer, tripoint_abs_omt( 360, 350, 0 ) );
    auto destination = actor.abs_omt_pos() + tripoint_rel_omt( 2, 0, 0 );
    destination.z() = 5;
    buffer.ter_set( destination, oter_id( "lighthouse_z5_north" ) );
    auto *job = mission::reserve_new( mission_type_id( "MISSION_lighthouse_man_5" ), giver->getID() );
    REQUIRE( job );
    giver->chatbin.missions_assigned.push_back( job );
    job->assign( actor );
    actor.set_value( "npctalk_var_global_safe_space_lighthouse_fixed", "yes" );
    CHECK_FALSE( job->is_complete( giver->getID() ) );
    actor.set_value( "npctalk_var_global_safe_space_lighthouse_fixed", "ready" );
    REQUIRE( job->is_complete( giver->getID() ) );
    job->wrap_up();
    CHECK_FALSE( job->in_progress() );
    CHECK( actor.get_value( "npctalk_var_global_safe_space_lighthouse_fixed" ) == "yes" );
    CHECK( giver->get_value( "npctalk_var_time_survivors_wait" ) == "864000" );
    auto target_map = map( 2 );
    target_map.load( project_to<coords::sm>( destination.xy() ), false );
    CHECK( target_map.ter( tripoint_bub_ms( 11, 12, 5 ) ) == ter_id( "t_floor_olight" ) );
    CHECK( target_map.ter( tripoint_bub_ms( 13, 13, 5 ) ) == ter_id( "t_floor_olight" ) );
    buffer.remove_npc( giver->getID() );
}

TEST_CASE( "lighthouse_boat_mission_assignment_save_and_turn_in", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    const auto original_id = actor.getID();
    const auto restore_id = on_out_of_scope( [&actor, original_id]() {
        actor.setID( original_id, true );
    } );
    actor.setID( character_id( 424242 ), true );
    auto &buffer = get_overmapbuffer( actor.get_dimension() );
    const auto spawn_location = tripoint_abs_omt( 356, 350, 0 );
    buffer.ter_set( spawn_location, oter_id( "field" ) );
    auto spawn_input = std::istringstream( R"({"place_nested":[{"chunks":[["NPC_lighthouse_man_spawn",1]],"x":12,"y":21}]})" );
    auto spawn_parser = JsonIn( spawn_input );
    auto defer = false;
    const auto spawn = add_mapgen_update_func( spawn_parser.get_object(), defer );
    REQUIRE_FALSE( defer );
    spawn( spawn_location, nullptr );
    const auto givers = buffer.get_npcs_near_omt( spawn_location, 0 );
    REQUIRE( givers.size() == 1 );
    auto &giver = *givers.front();
    REQUIRE( giver.get_fac_id() == faction_id( "fisherman_family" ) );
    REQUIRE( giver.chatbin.first_topic == "TALK_lighthouse_man_1" );
    const auto destination = actor.abs_omt_pos() + tripoint_rel_omt( 2, 0, 0 );
    buffer.ter_set( destination, oter_id( "lighthouse_ground_north" ) );
    auto *job = mission::reserve_new( mission_type_id( "MISSION_lighthouse_man_4" ), giver.getID() );
    REQUIRE( job );
    giver.chatbin.missions_assigned.push_back( job );
    job->assign( actor );
    CHECK( job->get_assigned_player_id() == actor.getID() );
    CHECK_FALSE( job->is_complete( giver.getID() ) );
    auto nails = item::spawn( itype_id( "nail" ), calendar::turn );
    nails->charges = 249;
    actor.i_add( std::move( nails ) );
    REQUIRE( actor.charges_of( itype_id( "nail" ) ) == 249 );
    actor.invalidate_crafting_inventory();
    CHECK_FALSE( job->is_complete( giver.getID() ) );
    auto saved_data = std::stringstream{};
    auto saved_output = JsonOut( saved_data );
    job->serialize( saved_output );
    auto restored = mission{};
    auto saved_input = JsonIn( saved_data );
    restored.deserialize( saved_input );
    CHECK( restored.get_type().id == job->get_type().id );
    CHECK( restored.get_npc_id() == giver.getID() );
    CHECK( restored.get_assigned_player_id() == actor.getID() );
    CHECK_FALSE( restored.is_complete( giver.getID() ) );
    auto last_nail = item::spawn( itype_id( "nail" ), calendar::turn );
    last_nail->charges = 1;
    actor.i_add( std::move( last_nail ) );
    actor.invalidate_crafting_inventory();
    REQUIRE( job->is_complete( giver.getID() ) );
    CHECK( restored.is_complete( giver.getID() ) );
    job->wrap_up();
    CHECK_FALSE( job->in_progress() );
    CHECK( actor.charges_of( itype_id( "nail" ) ) == 0 );
    CHECK( giver.get_value( "npctalk_var_flag_help_helped_lighthouse_man" ) == "yes" );
    CHECK( job->get_follow_up() == mission_type_id( "MISSION_lighthouse_man_5" ) );
    auto destination_map = map( 2 );
    destination_map.load( project_to<coords::sm>( destination.xy() ), false );
    auto canoes = 0;
    for( const auto &entry : destination_map.get_vehicles() ) {
        if( entry.v->type == vproto_id( "canoe" ) ) {
            ++canoes;
        }
    }
    CHECK( canoes == 1 );
    buffer.remove_npc( giver.getID() );
}

TEST_CASE( "lighthouse_actual_quest_updates_create_boat_and_working_lights", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
    const auto boat_location = tripoint_abs_omt( 352, 350, 0 );
    buffer.ter_set( boat_location, oter_id( "field" ) );
    auto boat_input = std::istringstream( dda_port::boat_update );
    auto boat_parser = JsonIn( boat_input );
    auto defer = false;
    const auto boat_update = add_mapgen_update_func( boat_parser.get_object(), defer );
    REQUIRE_FALSE( defer );
    boat_update( boat_location, nullptr );
    auto boat_map = map( 2 );
    boat_map.load( project_to<coords::sm>( boat_location.xy() ), false );
    auto canoes = 0;
    for( const auto &entry : boat_map.get_vehicles() ) {
        if( entry.v->type == vproto_id( "canoe" ) ) {
            ++canoes;
        }
    }
    CHECK( canoes == 1 );
    const auto light_location = tripoint_abs_omt( 354, 350, 0 );
    buffer.ter_set( light_location, oter_id( "field" ) );
    auto light_input = std::istringstream( dda_port::repair_update );
    auto light_parser = JsonIn( light_input );
    const auto repair_update = add_mapgen_update_func( light_parser.get_object(), defer );
    REQUIRE_FALSE( defer );
    repair_update( light_location, nullptr );
    auto light_map = map( 2 );
    light_map.load( project_to<coords::sm>( light_location.xy() ), false );
    CHECK( light_map.ter( tripoint_bub_ms( 11, 12, 0 ) ) == ter_id( "t_floor_olight" ) );
    CHECK( light_map.ter( tripoint_bub_ms( 13, 13, 0 ) ) == ter_id( "t_floor_olight" ) );
}

TEST_CASE( "lighthouse_actual_family_dialogue_keeps_loss_and_survival_branches", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto mother = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &mother;
    const auto topic = talk_topic( "TALK_lighthouse_woman_safe" );
    actor.set_value( "npctalk_var_flag_death_lighthouse_girl_dead", "no" );
    CHECK( conversation.dynamic_line( topic ) == "Hello." );
    actor.set_value( "npctalk_var_flag_death_lighthouse_girl_dead", "yes" );
    CHECK( conversation.dynamic_line( topic ) == "Poor, poor Angelina…" );
}

TEST_CASE( "lighthouse_survivor_update_places_real_npc", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &buffer = get_overmapbuffer( get_avatar().get_dimension() );
    const auto location = tripoint_abs_omt( 350, 350, 0 );
    buffer.ter_set( location, oter_id( "field" ) );
    REQUIRE( buffer.get_npcs_near_omt( location, 0 ).empty() );
    REQUIRE( run_mapgen_update_func( "lighthouse_man_survivor", location, nullptr, false ) );
    const auto survivors = buffer.get_npcs_near_omt( location, 0 );
    REQUIRE( survivors.size() == 1 );
    CHECK( survivors.front()->get_fac_id() == faction_id( "fisherman_family" ) );
    CHECK( survivors.front()->chatbin.first_topic == "TALK_LIGHTHOUSE_SURVIVOR" );
    CHECK( survivors.front()->abs_omt_pos() == location );
    CHECK( survivors.front()->mission == NPC_MISSION_GUARD );
    survivors.front()->set_value( "npctalk_var_time_lighthouse_wait", "123456" );
    survivors.front()->set_value( "npctalk_var_count_cleaning_lighthouse_man", "6" );
    auto saved_data = std::stringstream{};
    auto saved_output = JsonOut( saved_data );
    survivors.front()->serialize( saved_output );
    auto restored = npc{};
    auto saved_input = JsonIn( saved_data );
    restored.deserialize( saved_input );
    CHECK( restored.getID() == survivors.front()->getID() );
    CHECK( restored.abs_omt_pos() == location );
    CHECK( restored.get_fac_id() == faction_id( "fisherman_family" ) );
    CHECK( restored.chatbin.first_topic == "TALK_LIGHTHOUSE_SURVIVOR" );
    CHECK( restored.get_value( "npctalk_var_time_lighthouse_wait" ) == "123456" );
    CHECK( restored.get_value( "npctalk_var_count_cleaning_lighthouse_man" ) == "6" );
    buffer.remove_npc( survivors.front()->getID() );
}

TEST_CASE( "lighthouse_survivor_story_joins_independent_random_fragments", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto survivor = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &survivor;
    auto input = std::istringstream( R"({"and":[["A","B"],["1","2","3"]]})" );
    auto parser = JsonIn( input );
    const auto story = dynamic_line_t( parser.get_object() );
    for( auto index = 0; index < 20; ++index ) {
        const auto text = story( conversation );
        REQUIRE( text.size() == 2 );
        CHECK( ( text[0] == 'A' || text[0] == 'B' ) );
        CHECK( ( text[1] == '1' || text[1] == '2' || text[1] == '3' ) );
    }
}

TEST_CASE( "lighthouse_actual_missions_and_npc_templates_load", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    for( const auto *name : { "NPC_lighthouse_man", "NPC_lighthouse_woman", "NPC_lighthouse_girl", "NPC_survivor_lighthouse" } ) {
        REQUIRE( string_id<npc_template>( name ).is_valid() );
    }
    const auto *arrival = mission_type::get( mission_type_id( "MISSION_lighthouse_man_1" ) );
    const auto *cleanup = mission_type::get( mission_type_id( "MISSION_lighthouse_man_2" ) );
    const auto *family = mission_type::get( mission_type_id( "MISSION_lighthouse_man_3" ) );
    const auto *boat = mission_type::get( mission_type_id( "MISSION_lighthouse_man_4" ) );
    const auto *repair = mission_type::get( mission_type_id( "MISSION_lighthouse_man_5" ) );
    REQUIRE( arrival );
    REQUIRE( cleanup );
    REQUIRE( family );
    REQUIRE( boat );
    REQUIRE( repair );
    CHECK( boat->item_id == itype_id( "nail" ) );
    CHECK( boat->item_count == 250 );
    CHECK( arrival->follow_up == cleanup->id );
    CHECK( cleanup->follow_up == family->id );
    CHECK( family->follow_up == boat->id );
    CHECK( boat->follow_up == repair->id );
    REQUIRE( mission_type::get( mission_type_id( "MISSION_lighthouse_woman_0" ) ) );
    REQUIRE( mission_type::get( mission_type_id( "MISSION_lighthouse_girl_0" ) ) );
    auto &actor = get_avatar();
    auto giver = npc{};
    auto context = mission_goal_condition_context{};
    context.alpha = &actor;
    context.beta = &giver;
    giver.set_value( "npctalk_var_count_cleaning_lighthouse_man", "6" );
    CHECK_FALSE( cleanup->test_goal_condition( context ) );
    giver.set_value( "npctalk_var_count_cleaning_lighthouse_man", "7" );
    CHECK( cleanup->test_goal_condition( context ) );
    CHECK_FALSE( repair->test_goal_condition( context ) );
    actor.set_value( "npctalk_var_global_safe_space_lighthouse_fixed", "ready" );
    CHECK( repair->test_goal_condition( context ) );
}

TEST_CASE( "lighthouse_engineering_claims_can_be_real_or_false", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto engineer = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &engineer;
    auto claim_input = std::istringstream( R"({"npc_has_any_trait":["Exp_Eng_Electrical2","Exp_Eng_Electrical1Fake2","Exp_Eng_Electrical0Fake2"]})" );
    auto claim_parser = JsonIn( claim_input );
    const auto claims_expertise = conditional_t<dialogue>( claim_parser.get_object() );
    auto success_input = std::istringstream( R"({"not":{"npc_has_any_trait":["Exp_Eng_Electrical1Fake2","Exp_Eng_Electrical0Fake2"]}})" );
    auto success_parser = JsonIn( success_input );
    const auto honest = conditional_t<dialogue>( success_parser.get_object() );
    CHECK_FALSE( claims_expertise( conversation ) );
    const auto fake = trait_id( "Exp_Eng_Electrical0Fake2" );
    const auto expert = trait_id( "Exp_Eng_Electrical2" );
    REQUIRE( fake.is_valid() );
    REQUIRE( expert.is_valid() );
    engineer.set_mutation( fake );
    CHECK( claims_expertise( conversation ) );
    CHECK_FALSE( honest( conversation ) );
    engineer.unset_mutation( fake );
    engineer.set_mutation( expert );
    CHECK( claims_expertise( conversation ) );
    CHECK( honest( conversation ) );
}

TEST_CASE( "lighthouse_topic_extensions_keep_bn_responses", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto speaker = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto base_input = std::istringstream( R"({"dynamic_line":"Original BN greeting","responses":[{"text":"Original BN answer","topic":"TALK_DONE"}]})" );
    auto base_parser = JsonIn( base_input );
    auto topic = json_talk_topic{};
    topic.load( base_parser.get_object() );
    auto extension_input = std::istringstream( R"({"responses":[{"text":"Lighthouse repair","topic":"TALK_DONE"}]})" );
    auto extension_parser = JsonIn( extension_input );
    topic.load( extension_parser.get_object() );
    CHECK( topic.get_dynamic_line( conversation ) == "Original BN greeting" );
    CHECK_FALSE( topic.gen_responses( conversation ) );
    CHECK( conversation.responses.size() == 2 );
}

TEST_CASE( "ported_dynamic_lines_preserve_both_text_branches", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto speaker = npc{};
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    auto input = std::istringstream( R"({"dda_expression":{"op":"equal","args":[{"op":"variable","name":"done","actor":"npc"},{"op":"literal","value":1}]},"yes":"finished","no":"working"})" );
    auto parser = JsonIn( input );
    const auto numeric = dynamic_line_t( parser.get_object() );
    speaker.set_value( "npctalk_var_done", "0" );
    CHECK( numeric( conversation ) == "working" );
    speaker.set_value( "npctalk_var_done", "1" );
    CHECK( numeric( conversation ) == "finished" );
    auto string_input = std::istringstream( R"({"u_has_var":"done","value":"yes","yes":"accepted","no":"waiting"})" );
    auto string_parser = JsonIn( string_input );
    const auto textual = dynamic_line_t( string_parser.get_object() );
    CHECK( textual( conversation ) == "waiting" );
    actor.set_value( "npctalk_var_done", "yes" );
    CHECK( textual( conversation ) == "accepted" );
}

TEST_CASE( "lighthouse_cleanup_goal_reads_mission_giver_counter", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto giver = npc{};
    actor.set_value( "npctalk_var_count_cleaning_lighthouse_man", "7" );
    giver.set_value( "npctalk_var_count_cleaning_lighthouse_man", "6" );
    auto input = std::istringstream( R"({"dda_expression":{"op":"equal","args":[{"op":"variable","name":"count_cleaning_lighthouse_man","actor":"npc"},{"op":"literal","value":7}]}})" );
    auto parser = JsonIn( input );
    const auto goal = conditional_t<mission_goal_condition_context>( parser.get_object() );
    auto context = mission_goal_condition_context{};
    context.alpha = &actor;
    context.beta = &giver;
    CHECK_FALSE( goal( context ) );
    giver.set_value( "npctalk_var_count_cleaning_lighthouse_man", "7" );
    CHECK( goal( context ) );
}

TEST_CASE( "lighthouse_timer_belongs_to_the_npc", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    auto &actor = get_avatar();
    auto engineer = npc{};
    actor.set_value( "npctalk_var_time_lighthouse_wait", "999" );
    calendar::turn = calendar::turn_zero + 1_days;
    auto input = std::istringstream( R"({"effect":{"dda_set_variable":{"target":"time_lighthouse_wait","actor":"npc","expression":{"op":"now"}}}})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &engineer;
    REQUIRE( effect.effects.size() == 1 );
    effect.effects.front()( conversation );
    CHECK( engineer.get_value( "npctalk_var_time_lighthouse_wait" ) == "86400" );
    CHECK( actor.get_value( "npctalk_var_time_lighthouse_wait" ) == "999" );
    auto condition_input = std::istringstream( R"({"dda_expression":{"op":"greater","args":[{"op":"subtract","args":[{"op":"now"},{"op":"variable","name":"time_lighthouse_wait","actor":"npc"}]},{"op":"literal","value":172800}]}})" );
    auto condition_parser = JsonIn( condition_input );
    const auto ready = conditional_t<dialogue>( condition_parser.get_object() );
    calendar::turn += 2_days;
    CHECK_FALSE( ready( conversation ) );
    calendar::turn += 1_seconds;
    CHECK( ready( conversation ) );
}

TEST_CASE( "prisoner_mission_reward_preserves_its_container", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    actor.wear_item( item::spawn( itype_id( "backpack" ), calendar::turn ), false );
    auto input = std::istringstream( R"({"effect":{"dda_give_item":{"item":{"id":"can_beans"},"count":{"op":"literal","value":1},"container":"can_medium"}}})" );
    auto parser = JsonIn( input );
    const auto reward = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    REQUIRE( reward.effects.size() == 1 );
    reward.effects.front()( conversation );
    auto containers = actor.all_items_with_id( itype_id( "can_medium" ) );
    REQUIRE( containers.size() == 1 );
    REQUIRE_FALSE( containers.front()->contents.empty() );
    CHECK( containers.front()->contents.front().typeId() == itype_id( "can_beans" ) );
    CHECK( containers.front()->contents.front().charges == 1 );
}

TEST_CASE( "artisan_native_timer_and_fractional_prices", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    auto &actor = get_avatar();
    actor.set_value( "npctalk_var_timer_started", "100" );
    actor.set_value( "npctalk_var_wait_weeks", "3" );
    auto input = std::istringstream( R"({"dda_expression":{"op":"greater_equal","args":[{"op":"subtract","args":[{"op":"now"},{"op":"variable","name":"timer_started"}]},{"op":"multiply","args":[{"op":"variable","name":"wait_weeks"},{"op":"literal","value":604800}]}]}})" );
    // Three weeks expressed as a variable times one week.
    auto parser = JsonIn( input );
    const auto condition = conditional_t<dialogue>( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    calendar::turn = calendar::turn_zero + 100_seconds + 21_days - 1_seconds;
    CHECK_FALSE( condition( conversation ) );
    calendar::turn += 1_seconds;
    CHECK( condition( conversation ) );

    auto price_input = std::istringstream( R"({"dda_expression":{"op":"greater_equal","args":[{"op":"variable","name":"credit"},{"op":"divide","args":[{"op":"literal","value":77},{"op":"literal","value":2}]}]}})" );
    auto price_parser = JsonIn( price_input );
    const auto affordable = conditional_t<dialogue>( price_parser.get_object() );
    actor.set_value( "npctalk_var_credit", "38" );
    CHECK_FALSE( affordable( conversation ) );
    actor.set_value( "npctalk_var_credit", "38.5" );
    CHECK( affordable( conversation ) );
}

TEST_CASE( "artisan_native_variable_assignment", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    actor.set_value( "npctalk_var_credit", "39" );
    auto input = std::istringstream( R"({"effect":{"dda_set_variable":{"target":"credit","expression":{"op":"subtract","args":[{"op":"variable","name":"credit"},{"op":"divide","args":[{"op":"literal","value":77},{"op":"literal","value":2}]}]}}}})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    REQUIRE( effect.effects.size() == 1 );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    effect.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_credit" ) == "0.5" );
    auto adjustment_input = std::istringstream( R"({"effect":{"dda_set_variable":{"target":"credit","expression":{"op":"add","args":[{"op":"variable","name":"credit"},{"op":"literal","value":12}]}}}})" );
    auto adjustment_parser = JsonIn( adjustment_input );
    const auto adjustment = talk_effect_t( adjustment_parser.get_object() );
    REQUIRE( adjustment.effects.size() == 1 );
    adjustment.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_credit" ) == "12.5" );
}

TEST_CASE( "artisan_dynamic_reward_and_payment", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    actor.wear_item( item::spawn( itype_id( "backpack" ), calendar::turn ), false );
    actor.set_value( "npctalk_var_ordered_ammo", "9mm" );
    actor.set_value( "npctalk_var_wait", "3" );
    auto input = std::istringstream( R"({"effect":{"dda_give_item":{"item":{"variable":"ordered_ammo"},"count":{"op":"ceil","args":[{"op":"multiply","args":[{"op":"variable","name":"wait"},{"op":"literal","value":8.333}]}]}}}})" );
    auto parser = JsonIn( input );
    const auto reward = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    REQUIRE( reward.effects.size() == 1 );
    reward.effects.front()( conversation );
    CHECK( actor.charges_of( itype_id( "9mm" ) ) == 25 );

    actor.set_value( "npctalk_var_price", "26" );
    auto condition_input = std::istringstream( R"({"dda_has_items":{"item":{"id":"9mm"},"count":{"op":"variable","name":"price"}}})" );
    auto condition_parser = JsonIn( condition_input );
    const auto affordable = conditional_t<dialogue>( condition_parser.get_object() );
    CHECK_FALSE( affordable( conversation ) );
    auto recipient = npc{};
    recipient.set_fac( faction_id( "your_followers" ) );
    const auto payment = dda_port::resolved_item{ .id = itype_id( "9mm" ), .count = 26 };
    CHECK_FALSE( dda_port::transfer_items( actor, recipient, payment ) );
    CHECK( actor.charges_of( itype_id( "9mm" ) ) == 25 );

    actor.set_value( "npctalk_var_price", "17" );
    CHECK( affordable( conversation ) );
    auto payment_input = std::istringstream( R"({"effect":{"dda_transfer_item":{"item":{"id":"9mm"},"count":{"op":"variable","name":"price"}}}})" );
    auto payment_parser = JsonIn( payment_input );
    const auto transfer = talk_effect_t( payment_parser.get_object() );
    conversation.beta = &recipient;
    REQUIRE( transfer.effects.size() == 1 );
    transfer.effects.front()( conversation );
    CHECK( actor.charges_of( itype_id( "9mm" ) ) == 8 );
    CHECK( recipient.charges_of( itype_id( "9mm" ) ) == 17 );
}

TEST_CASE( "artisan_item_resolution_rejects_invalid_orders", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    const auto specification = dda_port::item_specification{
        .variable = "ordered_item",
        .count = { .op = "variable", .name = "quantity" }
    };
    actor.set_value( "npctalk_var_ordered_item", "9mm" );
    for( const auto value : { "-1", "0.5", "2147483648", "nan", "not_a_number" } ) {
        actor.set_value( "npctalk_var_quantity", value );
        CHECK_FALSE( dda_port::resolve_item( specification, actor ).has_value() );
    }
    actor.set_value( "npctalk_var_quantity", "12" );
    REQUIRE( dda_port::resolve_item( specification, actor ).has_value() );
    actor.set_value( "npctalk_var_ordered_item", "missing_artisan_item" );
    CHECK_FALSE( dda_port::resolve_item( specification, actor ).has_value() );
}

TEST_CASE( "artisan_switch_uses_last_qualifying_threshold", "[dda_npc]" ) {
    clear_all_state();
    get_avatar().reset_all_missions();
    auto &actor = get_avatar();
    auto input = std::istringstream( R"({"effect":{"dda_switch":{"expression":{"op":"variable","name":"thickness"},"cases":[{"threshold":{"op":"literal","value":1.2},"effect":{"u_add_var":"selected","value":"thin"}},{"threshold":{"op":"literal","value":6},"effect":{"u_add_var":"selected","value":"heavy"}},{"threshold":{"op":"literal","value":2},"effect":{"u_add_var":"selected","value":"last"}}]}}})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    REQUIRE( effect.effects.size() == 1 );
    actor.set_value( "npctalk_var_thickness", "1.19" );
    effect.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ).empty() );
    actor.set_value( "npctalk_var_thickness", "1.2" );
    effect.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ) == "thin" );
    actor.set_value( "npctalk_var_thickness", "1.99" );
    effect.effects.front()( conversation );
    CHECK( actor.get_value( "npctalk_var_selected" ) == "thin" );
    actor.set_value( "npctalk_var_thickness", "6" );
    effect.effects.front()( conversation );
    // Source order wins even when thresholds are not sorted.
    CHECK( actor.get_value( "npctalk_var_selected" ) == "last" );
}
