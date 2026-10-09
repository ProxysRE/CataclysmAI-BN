#include "artisan_bn_bridge.h"
#include "artisan_items.h"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "condition.h"
#include "dialogue.h"
#include "json.h"
#include "npc.h"
#include "state_helpers.h"

#include <sstream>

TEST_CASE( "artisan_native_timer_and_fractional_prices", "[dda_npc]" ) {
    clear_all_state();
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
