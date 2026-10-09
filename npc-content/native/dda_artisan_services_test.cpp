#include "activity_type.h"
#include "avatar.h"
#include "calendar.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "dialogue.h"
#include "distraction_manager.h"
#include "faction.h"
#include "json.h"
#include "npc.h"
#include "options_helpers.h"
#include "player_activity.h"
#include "state_helpers.h"

#include <ranges>
#include <sstream>

TEST_CASE( "artisan_measurements_take_calendar_time", "[dda_npc]" ) {
    clear_all_state();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    const auto time_scale = override_option( "TIME_ACTION_SCALE", "100" );
    // Crafting speed must not shorten measurements based on elapsed time.
    const auto progress_scale = override_option( "ACTIVITY_PROGRESS_SCALE", "300" );
    auto &actor = get_avatar();
    auto input = std::istringstream( R"({"effect":{"dda_assign_activity":{"activity":"ACT_MEASURE","duration_seconds":600}}})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    REQUIRE( effect.effects.size() == 1 );
    effect.effects.front()( conversation );
    REQUIRE( actor.activity );
    REQUIRE( actor.activity->id() == activity_id( "ACT_MEASURE" ) );
    CHECK( actor.activity->moves_total == to_moves<int>( 10_minutes ) );
    CHECK( activity_id( "ACT_MEASURE" )->rooted() );
    CHECK( activity_id( "ACT_MEASURE" )->no_resume() );
    CHECK_FALSE( activity_id( "ACT_MEASURE" )->interruptable() );
    CHECK( actor.activity->is_distraction_ignored( distraction_type::hostile_spotted_near ) );
    // DDA's separate keyboard cancellation remains available.
    CHECK( actor.activity->interruptable_with_kb );
    const auto started = calendar::turn;
    for( const auto tick : std::views::iota( 1, 600 ) ) {
        calendar::turn = started + time_duration::from_seconds( tick );
        actor.moves = 100;
        REQUIRE( actor.activity );
        actor.activity->do_turn( actor );
    }
    REQUIRE( actor.activity );
    REQUIRE( actor.activity->id() == activity_id( "ACT_MEASURE" ) );
    CHECK( actor.activity->moves_left == to_moves<int>( 1_seconds ) );
    calendar::turn = started + 10_minutes;
    actor.moves = 100;
    actor.activity->do_turn( actor );
    CHECK( !actor.activity || actor.activity->id().is_null() );
}

TEST_CASE( "artisan_faction_trust_and_public_access_survive_save_load", "[dda_npc]" ) {
    clear_all_state();
    auto &actor = get_avatar();
    auto artisan = npc{};
    artisan.set_fac( faction_id( "free_merchants" ) );
    auto *fac = artisan.get_faction();
    REQUIRE( fac );
    const auto restore_faction = restore_on_out_of_scope<faction>( *fac );
    fac->trusts_u = 4;
    auto input = std::istringstream( R"({"effect":[{"dda_add_faction_trust":1},{"dda_set_faction_relation":{"relation":"share public goods","enabled":true}}]})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &artisan;
    REQUIRE( effect.effects.size() == 2 );
    for( const auto &operation : effect.effects ) { operation( conversation ); }
    CHECK( fac->trusts_u == 5 );
    const auto player_faction = actor.get_faction()->id;
    CHECK( fac->has_relationship( player_faction, npc_factions::share_public_goods ) );
    CHECK_FALSE( fac->has_relationship( player_faction, npc_factions::share_my_stuff ) );
    auto buffer = std::stringstream{};
    auto output = JsonOut( buffer );
    fac->serialize( output );
    auto loaded = faction{};
    auto save_parser = JsonIn( buffer );
    loaded.deserialize( save_parser );
    CHECK( loaded.trusts_u == 5 );
    CHECK( loaded.has_relationship( player_faction, npc_factions::share_public_goods ) );

    auto revoke_input = std::istringstream( R"({"effect":{"dda_set_faction_relation":{"relation":"share public goods","enabled":false}}})" );
    auto revoke_parser = JsonIn( revoke_input );
    const auto revoke = talk_effect_t( revoke_parser.get_object() );
    REQUIRE( revoke.effects.size() == 1 );
    revoke.effects.front()( conversation );
    CHECK_FALSE( fac->has_relationship( player_faction, npc_factions::share_public_goods ) );

    // Missing old-save fields must reset new trust instead of retaining stale data.
    auto legacy_input = std::istringstream( R"({"id":"free_merchants","relations":{}})" );
    auto legacy_parser = JsonIn( legacy_input );
    loaded.deserialize( legacy_parser );
    CHECK( loaded.trusts_u == 0 );
}
