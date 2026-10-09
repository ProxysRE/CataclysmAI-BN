#include "artisan_bn_bridge.h"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "condition.h"
#include "dialogue.h"
#include "json.h"
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
}
