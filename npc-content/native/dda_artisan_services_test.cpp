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
#include "npc_class.h"
#include "item_group.h"
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
    CHECK( ( !actor.activity || actor.activity->id().is_null() ) );
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

TEST_CASE( "artisan_rigid_shop_samples_once_and_obeys_restock_interval", "[dda_npc]" ) {
    clear_all_state();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    const auto delay = override_option( "RESTOCK_DELAY_MULT", "1" );
    auto group_input = std::istringstream( R"({"items":[["plank",100]]})" );
    auto group_parser = JsonIn( group_input );
    const auto group_id = item_group_id( "dda_artisan_test_rigid_stock" );
    item_group::load_item_group( group_parser.get_object(), group_id, "collection" );
    auto class_input = std::istringstream( R"({"id":"dda_artisan_test_rigid_class","name":"Test artisan","job_description":"Native shop regression","common":false,"shopkeeper_item_group":"dda_artisan_test_rigid_stock","dda_shop_rigid":true,"dda_shop_restock_interval":"6 days","shopkeeper_consumption_rates":"basic_shop_rates"})" );
    auto class_parser = JsonIn( class_input );
    npc_class::load_npc_class( class_parser.get_object(), "dda_artisan_test" );
    const auto class_id = npc_class_id( "dda_artisan_test_rigid_class" );
    REQUIRE( class_id.is_valid() );
    CHECK( class_id->is_rigid_shop() );
    CHECK( class_id->shop_restock_interval() == 6_days );
    auto merchant = npc{};
    merchant.myclass = class_id;
    merchant.setpos( get_avatar().bub_pos() );
    merchant.set_fac( faction_id( "free_merchants" ) );
    calendar::turn = calendar::turn_zero + 1_days;
    merchant.shop_restock();
    REQUIRE( merchant.amount_of( itype_id( "plank" ) ) == 1 );
    const auto due = merchant.restock;
    CHECK( due == calendar::turn + 6_days );
    merchant.i_add( item::spawn( itype_id( "plank" ), calendar::turn ) );
    calendar::turn = due - 1_seconds;
    merchant.shop_restock();
    CHECK( merchant.amount_of( itype_id( "plank" ) ) == 2 );
    calendar::turn = due;
    merchant.shop_restock();
    CHECK( merchant.amount_of( itype_id( "plank" ) ) == 1 );

    auto legacy_input = std::istringstream( R"({"name":"Legacy shop","job_description":"Default policy"})" );
    auto legacy_parser = JsonIn( legacy_input );
    auto legacy = npc_class{};
    legacy.load( legacy_parser.get_object(), "dda_artisan_test" );
    CHECK_FALSE( legacy.is_rigid_shop() );
    CHECK( legacy.shop_restock_interval() == 3_days );
}
