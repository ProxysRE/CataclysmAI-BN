#include "activity_type.h"
#include "avatar.h"
#include "calendar.h"
#include "condition.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "dialogue.h"
#include "distraction_manager.h"
#include "faction.h"
#include "json.h"
#include "npc.h"
#include "npc_class.h"
#include "item_group.h"
#include "item.h"
#include "options_helpers.h"
#include "player_activity.h"
#include "state_helpers.h"

#include <ranges>
#include <sstream>

TEST_CASE( "quest_USB_items_inherit_stock_BN_USB_and_use_normal_inventory_conditions", "[dda_npc]" ) {
    clear_all_state();
    auto &actor = get_avatar();
    actor.reset_all_missions();
    const auto ordinary = item( itype_id( "usb_drive" ), calendar::turn );
    const auto secured = item( itype_id( "usb_drive_nano" ), calendar::turn );
    const auto license = item( itype_id( "nano_fabricator_encryption_code" ), calendar::turn );
    CHECK( secured.weight() == ordinary.weight() );
    CHECK( license.weight() == ordinary.weight() );
    CHECK( secured.volume() == ordinary.volume() );
    CHECK( license.volume() == ordinary.volume() );
    CHECK( license.typeId() == itype_id( "nano_fabricator_encryption_code" ) );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    auto input = std::istringstream( R"({"u_has_item":"nano_fabricator_encryption_code"})" );
    auto parser = JsonIn( input );
    const auto has_license = conditional_t<dialogue>( parser.get_object() );
    CHECK_FALSE( has_license( conversation ) );
    actor.i_add( item( itype_id( "usb_drive" ), calendar::turn ) );
    CHECK_FALSE( has_license( conversation ) );
    actor.i_add( item( itype_id( "nano_fabricator_encryption_code" ), calendar::turn ) );
    CHECK( has_license( conversation ) );
}

TEST_CASE( "dda_faction_food_ledger_preserves_calories_vitamins_and_expiry", "[dda_npc]" ) {
    clear_all_state();
    auto input = std::istringstream( R"({"id":"dda_food_stock_test","name":"Fisherman stock","likes_u":0,"respects_u":0,"known_by_u":false,"description":"Source-format food ledger","size":3,"power":3,"wealth":20000,"relations":{},"fac_food_supply":[[0,{"calories":2700000000,"vitamins":{"iron":86400,"calcium":86400,"vitC":86400}}],[123,{"calories":1000,"vitamins":{"iron":1}}]]})" );
    auto parser = JsonIn( input );
    faction_template::load( parser.get_object() );
    auto manager = faction_manager{};
    const auto *loaded_template = manager.get( faction_id( "dda_food_stock_test" ) );
    REQUIRE( loaded_template );
    auto stock = *loaded_template;
    REQUIRE( stock.dda_food_supply.size() == 2 );
    CHECK( stock.dda_food_supply[0].calories == 2700000000LL );
    CHECK( stock.dda_food_supply[0].vitamins.at( "vitC" ) == 86400 );
    CHECK( stock.dda_food_supply[1].expires == 123 );
    CHECK( stock.food_supply_kcal() == 2700001 );
    auto buffer = std::stringstream{};
    auto output = JsonOut( buffer );
    stock.serialize( output );
    auto saved = faction{};
    auto save_parser = JsonIn( buffer );
    saved.deserialize( save_parser );
    REQUIRE( saved.dda_food_supply.size() == 2 );
    CHECK( saved.dda_food_supply[0].calories == 2700000000LL );
    CHECK( saved.dda_food_supply[0].vitamins == stock.dda_food_supply[0].vitamins );
    CHECK( saved.dda_food_supply[1].expires == 123 );
    auto legacy_input = std::istringstream( R"({"id":"dda_food_stock_test","food_supply":99,"relations":{}})" );
    auto legacy_parser = JsonIn( legacy_input );
    saved.deserialize( legacy_parser );
    CHECK( saved.dda_food_supply.empty() );
    CHECK( saved.food_supply == 99 );
    CHECK( saved.food_supply_kcal() == 99 );
}

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

TEST_CASE( "godco_NPC_interaction_preserves_speaker_elapsed_time_and_saved_progress", "[dda_npc]" ) {
    clear_all_state();
    auto &actor = get_avatar();
    actor.reset_all_missions();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    const auto time_scale = override_option( "TIME_ACTION_SCALE", "100" );
    const auto progress_scale = override_option( "ACTIVITY_PROGRESS_SCALE", "300" );
    auto speaker = npc{};
    speaker.name = "Helena";
    auto input = std::istringstream( R"({"effect":{"dda_assign_activity":{"activity":"ACT_WAIT_NPC","duration_seconds":1800}}})" );
    auto parser = JsonIn( input );
    const auto effect = talk_effect_t( parser.get_object() );
    auto conversation = dialogue{};
    conversation.alpha = &actor;
    conversation.beta = &speaker;
    REQUIRE( effect.effects.size() == 1 );
    effect.effects.front()( conversation );
    REQUIRE( actor.activity );
    CHECK( actor.activity->id() == activity_id( "ACT_WAIT_NPC" ) );
    CHECK( actor.activity->moves_total == to_moves<int>( 30_minutes ) );
    REQUIRE( actor.activity->str_values.size() == 1 );
    CHECK( actor.activity->str_values.front() == "Helena" );
    const auto started = calendar::turn;
    for( const auto tick : std::views::iota( 1, 1800 ) ) {
        calendar::turn = started + time_duration::from_seconds( tick );
        actor.moves = tick % 2 ? 50 : 350;
        REQUIRE( actor.activity );
        actor.activity->do_turn( actor );
        if( tick == 900 ) {
            REQUIRE( actor.activity );
            const auto remaining = actor.activity->moves_left;
            auto data = std::stringstream{};
            auto output = JsonOut( data );
            actor.activity->serialize( output );
            actor.activity->moves_left = 1;
            actor.activity->str_values.clear();
            auto saved = JsonIn( data );
            actor.activity->deserialize( saved );
            CHECK( actor.activity->moves_left == remaining );
            REQUIRE( actor.activity->str_values.size() == 1 );
            CHECK( actor.activity->str_values.front() == "Helena" );
        }
    }
    REQUIRE( actor.activity );
    CHECK( actor.activity->moves_left == to_moves<int>( 1_seconds ) );
    calendar::turn = started + 30_minutes;
    actor.moves = 350;
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
    fac->limited_area_claim = true;
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
    CHECK( loaded.limited_area_claim );
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
    CHECK_FALSE( loaded.limited_area_claim );
}

TEST_CASE( "artisan_rigid_shop_samples_once_and_obeys_restock_interval", "[dda_npc]" ) {
    clear_all_state();
    const auto restore_time = restore_on_out_of_scope<time_point>( calendar::turn );
    const auto delay = override_option( "RESTOCK_DELAY_MULT", "1" );
    auto group_input = std::istringstream( R"({"items":[["2x4",100]]})" );
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
    // Default-constructed actors can share an unassigned ID. BN treats equal
    // character IDs as the same ally and intentionally skips shop restocking.
    merchant.setID( character_id( 123456 ) );
    REQUIRE( merchant.getID() != get_avatar().getID() );
    merchant.myclass = class_id;
    merchant.setpos( get_avatar().bub_pos() );
    merchant.set_fac( faction_id( "free_merchants" ) );
    REQUIRE_FALSE( merchant.is_player_ally() );
    calendar::turn = calendar::turn_zero + 1_days;
    merchant.shop_restock();
    REQUIRE( merchant.charges_of( itype_id( "2x4" ) ) == 1 );
    REQUIRE( item::count_by_charges( itype_id( "2x4" ) ) );
    const auto due = merchant.restock;
    CHECK( due == calendar::turn + 6_days );
    merchant.i_add( item::spawn( itype_id( "2x4" ), calendar::turn ) );
    REQUIRE( merchant.charges_of( itype_id( "2x4" ) ) == 2 );
    calendar::turn = due - 1_seconds;
    merchant.shop_restock();
    CHECK( merchant.charges_of( itype_id( "2x4" ) ) == 2 );
    calendar::turn = due;
    merchant.shop_restock();
    CHECK( merchant.charges_of( itype_id( "2x4" ) ) == 1 );

    auto legacy_input = std::istringstream( R"({"name":"Legacy shop","job_description":"Default policy"})" );
    auto legacy_parser = JsonIn( legacy_input );
    auto legacy = npc_class{};
    legacy.load( legacy_parser.get_object(), "dda_artisan_test" );
    CHECK_FALSE( legacy.is_rigid_shop() );
    CHECK( legacy.shop_restock_interval() == 3_days );
}
