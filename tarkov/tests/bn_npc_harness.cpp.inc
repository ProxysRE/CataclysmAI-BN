#include "npc_class.h"
#include "skill.h"
#include "world_type.h"
#include "options_helpers.h"
#include "map_helpers.h"
#include <vector>
#include <map>
#include <utility>
#include <cstdlib>
#include <sstream>

// The installer declares this friend only in --tests checkouts.
struct trkv_npc_spawn_probe {
    static void run(game& instance) { instance.perhaps_add_random_npc(); }
    static void starting(game& instance) { instance.create_starting_npcs(); }
    static void profession(game& instance) {
        instance.create_profession_npcs({npc_class_id("TRKV_COMBAT_TEST")});
    }
};

// Test-only first step of layer 2. Does not spawn opponents in normal player raids.
TEST_CASE("tarkov NPC survives reload and is removed by raid reset", "[tarkov_npc]") {
    clear_all_state();
    initialize_dimension_test_storage();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    const auto cleanup = dimension_test_cleanup({
        dimension_id("trkv_dev01_home"), dimension_id("trkv_dev01_raid")
    });
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto data = lua.create_table();
    lua.globals()["test_data"] = data;
    const auto check_starting_npcs_blocked = [&]() {
        const override_option static_npcs("STATIC_NPC", "true");
        const override_option starting_npcs("STARTING_NPC", "always");
        const auto dimension = g->get_current_dimension_id();
        const auto before = get_overmapbuffer(dimension).get_overmap_npcs().size();
        const auto followers = g->get_follower_list();
        trkv_npc_spawn_probe::starting(*g);
        trkv_npc_spawn_probe::profession(*g);
        CHECK(get_overmapbuffer(dimension).get_overmap_npcs().size() == before);
        CHECK(g->get_follower_list() == followers);
    };
    check_starting_npcs_blocked();
    data["stage"] = "home";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    check_starting_npcs_blocked();
    const auto probe = [&](const std::string& stage) {
        data["stage"] = stage;
        run_lua_test_script(lua, "trkv_npc_probe.lua");
    };
    const auto raid_dim = dimension_id("trkv_dev01_raid");
    const auto home_dim = dimension_id("trkv_dev01_home");
    const auto start_abs = tripoint_abs_ms(16 * 24 + 18, 16 * 24 + 8, 0);
    const auto moved_abs = tripoint_abs_ms(16 * 24 + 18, 16 * 24 + 9, 0);
    const auto spawn_guard = [&](const std::string& side) -> character_id {
        // BN's own test template avoids adding experimental NPC definitions to
        // shipped data. The equipment below is deterministic and test-only.
        auto& guard = spawn_npc(abs_to_bub(start_abs), "test_talker");
        REQUIRE(guard.get_dimension() == raid_dim);
        guard.set_attitude(NPCATT_KILL);
        guard.remove_primary_weapon();
        auto gun = item::spawn("ar15");
        auto magazine = item::spawn("stanag30");
        magazine->ammo_set(itype_id("223"), 17);
        gun->put_in(std::move(magazine));
        gun->set_damage(1375);
        gun->set_var("trkv_npc_probe", "rifle");
        auto& carried = guard.i_add(std::move(gun));
        REQUIRE(guard.wield(carried));
        guard.myclass = npc_class_id("TRKV_PATROL_PROBE");
        guard.set_attitude(NPCATT_NULL);
        data["actor_id"] = guard.getID().get_value();
        data["actor_side"] = side;
        probe("npc_patrol_setup");
        // Use BN's real dispatch, including regen_ai_cache before lua_ai.
        for (auto step = 0; step < 3; ++step) {
            guard.set_moves(1000);
            guard.move();
            REQUIRE(data["patrol_reason"].get<std::string>() == "patrol");
            REQUIRE(guard.get_moves() < 1000);
            REQUIRE(guard.abs_pos() == (step % 2 == 0 ? moved_abs : start_abs));
        }
        REQUIRE(data["dispatches"].get<int>() == 3);
        guard.set_attitude(NPCATT_KILL);
        // Keep the existing bound-object movement assertion too.
        guard.setpos(abs_to_bub(start_abs));
        guard.set_moves(1000);
        data["actor"] = &guard;
        data["destination"] = abs_to_bub(moved_abs);
        probe("npc_step");
        data["actor"] = sol::nil; // Never retain a userdata reference across load/travel.
        return guard.getID();
    };
    const auto check_random_spawn_blocked = [&]() {
        const auto* info = g->get_current_dimension_info();
        REQUIRE(info != nullptr);
        REQUIRE(info->world_type == world_type_id("trkv_raid_space"));
        REQUIRE_FALSE(info->world_type->allow_random_npcs);
        REQUIRE(world_types::get_default()->allow_random_npcs);
        const override_option random_npcs("RANDOM_NPC", "true");
        const override_option density("NPC_DENSITY", "100.00");
        REQUIRE(get_option<bool>("RANDOM_NPC"));
        REQUIRE(get_option<float>("NPC_DENSITY") >= 24.0f);
        const auto tick = action_time_scale::scoped_calendar_turns_this_tick(1);
        const auto restore_time = restore_on_out_of_scope<time_point>(calendar::turn);
        const auto count = get_overmapbuffer(raid_dim).get_overmap_npcs().size();
        calendar::turn = calendar::turn_zero;
        for (auto hour = 0; hour < 12; ++hour) {
            calendar::turn += 1_hours;
            REQUIRE(action_time_scale::once_every_this_tick(1_hours));
            // With this density and few NPCs the vanilla probability is exactly 1.
            // Invoke its actual entry point, without running the raid timer hooks.
            trkv_npc_spawn_probe::run(*g);
            CHECK(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == count);
        }
    };
    probe("npc_enter");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    check_random_spawn_blocked();
    check_starting_npcs_blocked();
    const auto check_mapgen_npcs_blocked = [&]() {
        const override_option static_npcs("STATIC_NPC", "true");
        REQUIRE(get_option<bool>("STATIC_NPC"));
        REQUIRE(world_types::infer_from_dimension(raid_dim) == world_type_id("trkv_raid_space"));
        REQUIRE_FALSE(world_types::infer_from_dimension(raid_dim)->allow_mapgen_npcs);
        REQUIRE(world_types::infer_from_dimension(dimension_id()) == world_types::get_default());
        REQUIRE(world_types::get_default()->allow_mapgen_npcs);
        const auto count = get_overmapbuffer(raid_dim).get_overmap_npcs().size();
        const auto placed = g->m.place_npc(abs_to_bub(start_abs), string_id<npc_template>("trkv_combat_tester"));
        CHECK(placed == character_id());
        CHECK(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == count);
    };
    check_mapgen_npcs_blocked();
    const auto first_id = spawn_guard("usec");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 1);
    REQUIRE(g->save(false));
    const auto saved_character = save_t::from_save_id(get_avatar().get_save_id());
    REQUIRE(g->load(saved_character));
    const auto tick_scope = action_time_scale::scoped_calendar_turns_this_tick(1);
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_patrol_restored");
    {
        const auto* guard = g->find_npc(first_id);
        REQUIRE(guard != nullptr);
        CHECK(guard->get_dimension() == raid_dim);
        CHECK(guard->abs_pos() == moved_abs);
        CHECK(guard->get_attitude() == NPCATT_KILL);
        REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 1);
        auto rifles = 0;
        for (const auto* value : guard->all_items(false)) {
            if (value->get_var("trkv_npc_probe") != "rifle") { continue; }
            ++rifles;
            CHECK(value->typeId().str() == "ar15");
            CHECK(value->ammo_remaining() == 17);
            CHECK(value->damage() == 1375);
            CHECK(guard->is_wielding(*value));
        }
        CHECK(rifles == 1);
    }
    {
        auto* guard = g->find_npc(first_id);
        REQUIRE(guard != nullptr);
        guard->set_attitude(NPCATT_NULL);
        guard->set_moves(1000);
        guard->move();
        REQUIRE(data["patrol_reason"].get<std::string>() == "patrol");
        CHECK(guard->abs_pos() == start_abs);
        CHECK(guard->get_moves() < 1000);
        probe("npc_patrol_resumed");
    }
    {
        auto* guard = g->find_npc(first_id);
        REQUIRE(guard != nullptr);
        auto& player = get_avatar();
        // The persistence assertions above used the original damaged rifle.
        // Use a serviceable rifle and a competent shooter for this separate probe.
        guard->primary_weapon().set_damage(0);
        guard->set_skill_level(skill_id("gun"), 8);
        guard->set_skill_level(skill_id("rifle"), 8);
        guard->personality.bravery = 10;
        auto rifle = item::spawn("ar15");
        auto magazine = item::spawn("stanag30");
        magazine->ammo_set(itype_id("223"), 30);
        rifle->put_in(std::move(magazine));
        auto& carried = player.i_add(std::move(rifle));
        REQUIRE(player.wield(carried));
        guard->set_attitude(NPCATT_KILL);
        player.setpos(abs_to_bub(tripoint_abs_ms(16 * 24 + 3, 16 * 24 + 8, 0)));
        set_time(calendar::turn); // Rebuild light/visibility caches without aging the raid.
        REQUIRE_FALSE(guard->sees(player));
        guard->set_moves(1000);
        guard->move();
        REQUIRE(data["patrol_reason"].get<std::string>() == "patrol");
        REQUIRE_FALSE(data["patrol_target"].get<bool>());
        CHECK(guard->abs_pos() == moved_abs);
        REQUIRE(guard->primary_weapon().ammo_remaining() == 17);

        // Expose a genuine hostile target. No target or danger is injected into AI cache.
        player.setpos(abs_to_bub(tripoint_abs_ms(16 * 24 + 18, 16 * 24 + 6, 0)));
        set_time(calendar::turn);
        REQUIRE(guard->sees(player));
        const auto initial_ammo = guard->primary_weapon().ammo_remaining();
        auto fired = false;
        for (auto decision = 0; decision < 20; ++decision) {
            INFO("Combat decision " << decision);
            player.set_all_parts_hp_to_max();
            guard->set_moves(100);
            guard->move(); // BN decides whether to aim, reposition or fire.
            REQUIRE(guard->current_target() == static_cast<Creature*>(&player));
            probe("npc_combat_handoff");
            REQUIRE(guard->get_moves() < 100);
            REQUIRE(guard->primary_weapon().get_var("trkv_npc_probe") == "rifle");
            REQUIRE(guard->primary_weapon().typeId().str() == "ar15");
            if (guard->primary_weapon().ammo_remaining() < initial_ammo) {
                fired = true;
                break;
            }
        }
        CHECK(fired); // A false Lua return alone is not evidence of actual gunfire.
        player.setpos(abs_to_bub(tripoint_abs_ms(387, 392, 0)));
        set_time(calendar::turn);
        REQUIRE_FALSE(guard->sees(player));
        probe("npc_memory_hidden");
        player.set_all_parts_hp_to_max();
        player.clear_effects();
    }
    probe("npc_extract");
    CHECK(g->find_npc(first_id) == nullptr);
    CHECK(get_overmapbuffer(home_dim).find_npc(first_id) == nullptr);
    probe("npc_enter");
    CHECK(g->find_npc(first_id) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    const auto second_id = spawn_guard("bear");
    CHECK(second_id != first_id);
    probe("npc_defeat");
    CHECK(g->find_npc(second_id) == nullptr);
    CHECK(get_overmapbuffer(home_dim).find_npc(second_id) == nullptr);
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    CHECK(g->find_npc(first_id) == nullptr);
    CHECK(g->find_npc(second_id) == nullptr);
    probe("npc_enter");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    auto group_spawns = 0;
    const auto install_group_spawner = [&]() {
        data["spawn_member"] = [&](const std::string& slot, int x, int y, int sequence) -> int {
            auto& actor = spawn_npc(abs_to_bub(tripoint_abs_ms(x, y, 0)), "test_talker");
            actor.myclass = npc_class_id("TRKV_PATROL_PROBE");
            actor.set_attitude(NPCATT_NULL);
            actor.set_value("trkv_spawn_slot", slot);
            actor.set_value("trkv_spawn_sequence", std::to_string(sequence));
            ++group_spawns;
            return actor.getID().get_value();
        };
    };
    const auto group_ids = [&]() {
        std::vector<character_id> result;
        const sol::table ids = data["group_ids"];
        REQUIRE(ids.size() == 3);
        for (auto i = 1; i <= 3; ++i) {
            result.emplace_back(ids[i].get<int>());
        }
        return result;
    };
    install_group_spawner();
    probe("npc_group_deploy");
    data["spawn_member"] = sol::nil;
    const auto first_group = group_ids();
    REQUIRE(group_spawns == 3);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 3);
    probe("npc_group_deploy"); // Must not call the now-absent spawner again.
    REQUIRE(group_spawns == 3);
    for (auto step = 0; step < 3; ++step) {
        for (const auto id : first_group) {
            auto* actor = g->find_npc(id);
            REQUIRE(actor != nullptr);
            actor->set_moves(1000);
            actor->move();
            REQUIRE(data["patrol_reason"].get<std::string>() == "patrol");
            CHECK(actor->get_moves() < 1000);
            CHECK(actor->abs_pos().y() == (step % 2 == 0 ? 399 : 398));
        }
    }
    data["expected_index"] = 2;
    probe("npc_group_routes");
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 3);
    probe("npc_group_routes");
    probe("npc_group_recover");
    REQUIRE(group_ids() == first_group);
    REQUIRE(group_spawns == 3);
    const std::vector<int> expected_x = {398, 400, 404};
    for (auto i = 0; i < 3; ++i) {
        auto* actor = g->find_npc(first_group[i]);
        REQUIRE(actor != nullptr);
        CHECK(actor->abs_pos() == tripoint_abs_ms(expected_x[i], 399, 0));
        actor->set_moves(1000);
        actor->move();
        REQUIRE(data["patrol_reason"].get<std::string>() == "patrol");
        CHECK(actor->abs_pos() == tripoint_abs_ms(expected_x[i], 398, 0));
    }
    data["expected_index"] = 1;
    probe("npc_group_routes");
    probe("npc_extract");
    for (const auto id : first_group) {
        CHECK(g->find_npc(id) == nullptr);
        CHECK(get_overmapbuffer(home_dim).find_npc(id) == nullptr);
    }
    probe("npc_enter");
    install_group_spawner();
    probe("npc_group_deploy");
    data["spawn_member"] = sol::nil;
    const auto second_group = group_ids();
    REQUIRE(group_spawns == 6);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 3);
    for (const auto id : second_group) {
        for (const auto old_id : first_group) { CHECK(id != old_id); }
    }
    probe("npc_defeat");
    for (const auto id : second_group) {
        CHECK(g->find_npc(id) == nullptr);
        CHECK(get_overmapbuffer(home_dim).find_npc(id) == nullptr);
    }
    probe("npc_enter");
    CHECK(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    probe("npc_extract");
    // Actual game encounter: no injected spawner, test templates or test lua_ai.
    probe("npc_live_depart");
    const auto live_group = group_ids();
    for (const auto id : live_group) {
        auto* actor = g->find_npc(id);
        REQUIRE(actor != nullptr);
        REQUIRE(actor->myclass == npc_class_id("TRKV_PATROL"));
        actor->set_moves(1000);
        actor->move();
        CHECK(actor->abs_pos().y() == 399);
        CHECK(actor->get_moves() < 1000);
    }
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_live_restored");
    for (const auto id : live_group) {
        auto* actor = g->find_npc(id);
        REQUIRE(actor != nullptr);
        actor->set_moves(1000);
        actor->move();
        CHECK(actor->abs_pos().y() == 400);
        CHECK(actor->get_moves() < 1000);
    }
    data["door_actor_id"] = live_group.front().get_value();
    probe("npc_live_door_setup");
    {
        auto* actor = g->find_npc(live_group.front());
        REQUIRE(actor != nullptr);
        const auto before_door = tripoint_abs_ms(393, 391, 0);
        actor->setpos(abs_to_bub(before_door));
        set_time(calendar::turn);
        actor->set_moves(1000);
        actor->move();
        CHECK(actor->abs_pos() == before_door); // Opening is an action, not a teleport.
        CHECK(actor->get_moves() < 1000);
        probe("npc_live_door_open");
    }
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_live_door_open");
    {
        auto* actor = g->find_npc(live_group.front());
        REQUIRE(actor != nullptr);
        const auto destination = tripoint_abs_ms(396, 391, 0);
        REQUIRE(actor->abs_pos() == tripoint_abs_ms(393, 391, 0));
        for (auto step = 0; step < 12 && actor->abs_pos() != destination; ++step) {
            const auto before = actor->abs_pos();
            actor->set_moves(1000);
            actor->move();
            CHECK(std::abs(actor->abs_pos().x() - before.x()) <= 1);
            CHECK(std::abs(actor->abs_pos().y() - before.y()) <= 1);
            REQUIRE(actor->get_moves() < 1000);
        }
        REQUIRE(actor->abs_pos() == destination);
        probe("npc_live_path_blocked");
    }
    probe("npc_live_detour_setup");
    {
        auto* actor = g->find_npc(live_group.front());
        REQUIRE(actor != nullptr);
        actor->setpos(abs_to_bub(tripoint_abs_ms(400, 395, 0)));
        const auto destination = tripoint_abs_ms(400, 397, 0);
        auto went_around = false;
        for (auto step = 0; step < 24 && actor->abs_pos() != destination; ++step) {
            const auto before = actor->abs_pos();
            actor->set_moves(1000);
            actor->move();
            const auto after = actor->abs_pos();
            CHECK(std::abs(after.x() - before.x()) <= 1);
            CHECK(std::abs(after.y() - before.y()) <= 1);
            REQUIRE(actor->get_moves() < 1000);
            if (after.y() == 396) {
                REQUIRE((after.x() < 397 || after.x() > 402));
                went_around = true;
            }
        }
        REQUIRE(actor->abs_pos() == destination);
        CHECK(went_around);
        probe("npc_live_detour_intact");
    }
    probe("npc_live_wait_setup");
    {
        auto* first = g->find_npc(live_group[0]);
        auto* second = g->find_npc(live_group[1]);
        REQUIRE(first != nullptr);
        REQUIRE(second != nullptr);
        first->setpos(abs_to_bub(tripoint_abs_ms(398, 402, 0)));
        second->setpos(abs_to_bub(tripoint_abs_ms(399, 402, 0)));
        set_time(calendar::turn);
        second->set_moves(777);
        first->set_moves(1000);
        first->move();
        // An occupied waypoint is a paid wait, never a push or vanilla fallback.
        CHECK(first->abs_pos() == tripoint_abs_ms(398, 402, 0));
        CHECK(first->get_moves() == 900);
        CHECK(second->abs_pos() == tripoint_abs_ms(399, 402, 0));
        CHECK(second->get_moves() == 777);
    }
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_live_wait_restored");
    {
        auto* first = g->find_npc(live_group[0]);
        auto* second = g->find_npc(live_group[1]);
        REQUIRE(first != nullptr);
        REQUIRE(second != nullptr);
        REQUIRE(first->abs_pos() == tripoint_abs_ms(398, 402, 0));
        REQUIRE(second->abs_pos() == tripoint_abs_ms(399, 402, 0));
        first->set_moves(1000);
        second->set_moves(1000);
        second->move();
        CHECK(second->abs_pos() == tripoint_abs_ms(400, 402, 0));
        CHECK(second->get_moves() < 1000);
        CHECK(first->get_moves() == 1000);
        first->move();
        CHECK(first->abs_pos() == tripoint_abs_ms(399, 402, 0));
        CHECK(first->get_moves() < 1000);
    }
    probe("npc_live_crossing_setup");
    {
        auto* first = g->find_npc(live_group[0]);
        auto* second = g->find_npc(live_group[1]);
        REQUIRE(first != nullptr);
        REQUIRE(second != nullptr);
        first->setpos(abs_to_bub(tripoint_abs_ms(398, 400, 0)));
        second->setpos(abs_to_bub(tripoint_abs_ms(401, 400, 0)));
        set_time(calendar::turn);
        const auto first_goal = tripoint_abs_ms(402, 400, 0);
        const auto second_goal = tripoint_abs_ms(397, 400, 0);
        auto detoured = false;
        for (auto round = 0; round < 16; ++round) {
            for (auto index = 0; index < 2; ++index) {
                auto* actor = index == 0 ? first : second;
                auto* other = index == 0 ? second : first;
                const auto goal = index == 0 ? first_goal : second_goal;
                if (actor->abs_pos() == goal) { continue; }
                const auto before = actor->abs_pos();
                const auto other_before = other->abs_pos();
                other->set_moves(777);
                actor->set_moves(1000);
                actor->move();
                const auto after = actor->abs_pos();
                CHECK(std::abs(after.x() - before.x()) <= 1);
                CHECK(std::abs(after.y() - before.y()) <= 1);
                CHECK(after.z() == before.z());
                REQUIRE(actor->get_moves() < 1000);
                REQUIRE(other->abs_pos() == other_before);
                REQUIRE(other->get_moves() == 777);
                REQUIRE(after != other->abs_pos());
                detoured = detoured || after.y() != 400;
            }
            if (first->abs_pos() == first_goal && second->abs_pos() == second_goal) { break; }
        }
        REQUIRE(first->abs_pos() == first_goal);
        REQUIRE(second->abs_pos() == second_goal);
        CHECK(detoured);
    }
    // Actual fatal HP -> NPC death hook -> corpse and gear -> engine cleanup.
    // Keep one dropped item on the map and take another into the refuge.
    const auto casualty_abs = tripoint_abs_ms(404, 400, 0);
    probe("npc_live_casualty_before");
    {
        auto* victim = g->find_npc(live_group[2]);
        REQUIRE(victim != nullptr);
        victim->setpos(abs_to_bub(casualty_abs));
        victim->remove_primary_weapon();
        auto rifle = item::spawn("ar15");
        auto magazine = item::spawn("stanag30");
        magazine->ammo_set(itype_id("223"), 17);
        rifle->put_in(std::move(magazine));
        rifle->set_damage(1375);
        rifle->set_var("trkv_casualty", "rifle");
        auto& carried = victim->i_add(std::move(rifle));
        REQUIRE(victim->wield(carried));
        auto abandoned = item::spawn("rock");
        abandoned->set_var("trkv_casualty", "left_behind");
        victim->i_add(std::move(abandoned));
        victim->set_all_parts_hp_cur(0);
        g->cleanup_dead(); // Invalidates victim: do not keep it beyond this block.
    }
    REQUIRE(g->find_npc(live_group[2]) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).find_npc(live_group[2]) == nullptr);
    probe("npc_live_casualty_check");
    const auto ground_counts = [&]() {
        auto corpses = 0;
        auto rifles = 0;
        auto abandoned = 0;
        for (const auto* value : g->m.i_at(abs_to_bub(casualty_abs))) {
            if (value->is_corpse()) { ++corpses; }
            if (value->get_var("trkv_casualty") == "rifle") {
                ++rifles;
                CHECK(value->typeId().str() == "ar15");
                CHECK(value->ammo_remaining() == 17);
                CHECK(value->damage() == 1375);
            }
            if (value->get_var("trkv_casualty") == "left_behind") { ++abandoned; }
        }
        return std::vector<int>{corpses, rifles, abandoned};
    };
    const auto check_looted_rifle = [&]() {
        auto count = 0;
        for (const auto* value : get_avatar().all_items(false)) {
            if (value->get_var("trkv_casualty") != "rifle") { continue; }
            ++count;
            CHECK(value->typeId().str() == "ar15");
            CHECK(value->ammo_remaining() == 17);
            CHECK(value->damage() == 1375);
            CHECK(get_avatar().is_wielding(*value));
        }
        REQUIRE(count == 1);
    };
    REQUIRE((ground_counts() == std::vector<int>{1, 1, 1}));
    probe("npc_live_casualty_checkpoint");
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_live_casualty_check");
    REQUIRE(g->find_npc(live_group[2]) == nullptr);
    REQUIRE((ground_counts() == std::vector<int>{1, 1, 1}));
    {
        item* rifle = nullptr;
        for (auto* value : g->m.i_at(abs_to_bub(casualty_abs))) {
            if (value->get_var("trkv_casualty") == "rifle") { rifle = value; }
        }
        REQUIRE(rifle != nullptr);
        auto taken = g->m.i_rem(abs_to_bub(casualty_abs), rifle);
        REQUIRE(taken);
        auto& carried = get_avatar().i_add(std::move(taken));
        REQUIRE(get_avatar().wield(carried));
    }
    REQUIRE((ground_counts() == std::vector<int>{1, 0, 1}));
    check_looted_rifle();
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_live_casualty_check");
    REQUIRE((ground_counts() == std::vector<int>{1, 0, 1}));
    check_looted_rifle();
    probe("npc_extract");
    for (const auto id : live_group) { CHECK(g->find_npc(id) == nullptr); }
    check_looted_rifle();
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    check_looted_rifle();
    probe("npc_live_depart");
    REQUIRE((ground_counts() == std::vector<int>{0, 0, 0}));
    check_looted_rifle();
    const auto timeout_group = group_ids();
    for (const auto id : timeout_group) {
        for (const auto old_id : live_group) { CHECK(id != old_id); }
    }
    probe("npc_live_timeout");
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    for (const auto id : timeout_group) { CHECK(g->find_npc(id) == nullptr); }
    probe("npc_live_empty");
    probe("npc_extract");
    // Player-selectable hostile encounter: equipment and attitude come from
    // shipped JSON, not from the test's spawn/equipment adapters.
    probe("npc_combat_depart");
    const auto combat_id = character_id(data["combat_id"].get<int>());
    const std::string selected_loadout = data["combat_loadout"];
    const std::string selected_profile = data["combat_profile"];
    const std::string selected_equipment = data["combat_equipment"];
    REQUIRE((selected_profile == "rifle_trained_v1" || selected_profile == "rifle_recruit_v1"));
    REQUIRE((selected_equipment == "civilian_v1" || selected_equipment == "field_v1"));
    const auto recruit = selected_profile == "rifle_recruit_v1";
    const auto field_loadout = selected_equipment == "field_v1";
    const std::string expected_class = recruit
        ? (field_loadout ? "TRKV_COMBAT_RECRUIT_FIELD" : "TRKV_COMBAT_RECRUIT")
        : (field_loadout ? "TRKV_COMBAT_FIELD" : "TRKV_COMBAT_TEST");
    const auto initial_ammo = field_loadout ? 30 : 17;
    const std::string combat_weapon = field_loadout ? "m4a1" : "ar15";
    const std::map<std::string, int> expected_hp = {
        {"head", 35}, {"torso", 85}, {"arm_l", 60}, {"arm_r", 60}, {"leg_l", 65}, {"leg_r", 65}
    };
    const auto check_combat_actor = [&](int ammo, int barter = 0, int arm_hp = 60, int shooting_gain = 0) {
        const auto* actor = g->find_npc(combat_id);
        REQUIRE(actor != nullptr);
        CHECK(actor->myclass == npc_class_id(expected_class));
        CHECK(actor->get_value("trkv_loadout") == selected_loadout);
        CHECK(actor->is_wearing(itype_id(field_loadout ? "pants_cargo" : "jeans")));
        CHECK(actor->is_wearing(itype_id(field_loadout ? "hoodie" : "tshirt")));
        auto spare_magazines = 0;
        for (const auto* value : actor->all_items(false)) {
            if (value->typeId().str() == "stanag30" && value != actor->primary_weapon().magazine_current()) {
                ++spare_magazines;
                CHECK(value->ammo_remaining() == 30);
            }
        }
        CHECK(spare_magazines == (field_loadout ? 2 : 0));
        CHECK(actor->get_attitude() == NPCATT_KILL);
        CHECK(actor->get_str_base() == (recruit ? 8 : 10));
        CHECK(actor->get_dex_base() == (recruit ? 8 : 10));
        CHECK(actor->get_int_base() == 8);
        CHECK(actor->get_per_base() == (recruit ? 8 : 10));
        CHECK(actor->personality.aggression == 5);
        CHECK(actor->personality.bravery == 10);
        CHECK(actor->personality.collector == 0);
        CHECK(actor->personality.altruism == 0);
        CHECK(actor->get_skill_level(skill_id("barter")) == barter);
        CHECK(actor->get_skill_level(skill_id("gun")) == (recruit ? 3 : 6) + shooting_gain);
        CHECK(actor->get_skill_level(skill_id("rifle")) == (recruit ? 3 : 6) + shooting_gain);
        CHECK(actor->primary_weapon().typeId().str() == combat_weapon);
        CHECK(actor->primary_weapon().damage() == 0);
        CHECK(actor->primary_weapon().ammo_remaining() == ammo);
        for (const auto& part : actor->get_all_body_parts()) {
            CHECK(actor->get_part_hp_max(part) == expected_hp.at(part->main_part.str()));
        }
        CHECK(actor->get_part_hp_cur(bodypart_str_id("arm_l").id()) == arm_hp);
    };
    check_combat_actor(initial_ammo);
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_combat_restored");
    check_combat_actor(initial_ammo);
    check_random_spawn_blocked();
    check_starting_npcs_blocked(); // Policy must also survive save/load.
    check_mapgen_npcs_blocked();
    auto remaining_ammo = initial_ammo;
    {
        auto* actor = g->find_npc(combat_id);
        REQUIRE(actor != nullptr);
        auto& player = get_avatar();
        // Keep random critical damage from interrupting this shooting probe.
        player.set_mutation(trait_id("DEBUG_NODMG"));
        const auto restore_damage = on_out_of_scope([&]() {
            player.unset_mutation(trait_id("DEBUG_NODMG"));
            player.set_all_parts_hp_to_max();
            player.clear_effects();
        });
        actor->set_moves(1000);
        actor->move(); // Player is still behind the wall: production patrol runs.
        REQUIRE(actor->abs_pos() == tripoint_abs_ms(402, 393, 0));
        REQUIRE(actor->primary_weapon().ammo_remaining() == initial_ammo);
        // Vanilla gun use is gated by perceived danger. Use an armed target,
        // as in the earlier combat probe, without altering the tested NPC.
        auto target_rifle = item::spawn("ar15");
        auto target_magazine = item::spawn("stanag30");
        target_magazine->ammo_set(itype_id("223"), 30);
        target_rifle->put_in(std::move(target_magazine));
        auto& target_weapon = player.i_add(std::move(target_rifle));
        REQUIRE(player.wield(target_weapon));
        player.setpos(abs_to_bub(tripoint_abs_ms(402, 388, 0)));
        set_time(calendar::turn);
        REQUIRE(actor->sees(player));
        for (auto decision = 0; decision < 30; ++decision) {
            INFO("Production combat decision " << decision);
            actor->set_moves(100);
            actor->move();
            INFO("NPC danger " << actor->danger_assessment() << ", position " << actor->abs_pos().x()
                 << "," << actor->abs_pos().y() << "," << actor->abs_pos().z() << ", weapon " << actor->primary_weapon().typeId().str()
                 << ", ammo " << actor->primary_weapon().ammo_remaining());
            REQUIRE(actor->get_moves() < 100);
            REQUIRE(actor->current_target() == static_cast<Creature*>(&player));
            REQUIRE(actor->primary_weapon().typeId().str() == combat_weapon);
            remaining_ammo = actor->primary_weapon().ammo_remaining();
            if (remaining_ammo < initial_ammo) { break; }
        }
        REQUIRE(remaining_ammo < initial_ammo);
        actor->set_skill_level(skill_id("barter"), 2); // Saved progress, not a new spawn.
        actor->set_skill_level(skill_id("gun"), (recruit ? 3 : 6) + 1);
        actor->set_skill_level(skill_id("rifle"), (recruit ? 3 : 6) + 1);
        actor->set_part_hp_cur(bodypart_str_id("arm_l").id(), 17);
        for (auto repeat = 0; repeat < 5; ++repeat) { actor->recalc_hp(); }
        CHECK(actor->get_part_hp_cur(bodypart_str_id("arm_l").id()) == 17);
    }
    probe("npc_combat_checkpoint");
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_combat_restored");
    check_combat_actor(remaining_ammo, 2, 17, 1);
    g->find_npc(combat_id)->recalc_hp();
    check_combat_actor(remaining_ammo, 2, 17, 1);
    probe("npc_extract");
    CHECK(g->find_npc(combat_id) == nullptr);
    CHECK(get_overmapbuffer(home_dim).find_npc(combat_id) == nullptr);
    // Force only the preset choice for this additional encounter. The kit comes
    // from shipped JSON; actual npc::move must decide to reload and then fire.
    const auto run_reload_probe = [&](bool ak) {
        const std::string weapon_type = ak ? "ak47" : "m4a1";
        const std::string magazine_type = ak ? "akmag30" : "stanag30";
        const std::string ammo_type = ak ? "762_m43" : "223";
        probe(ak ? "npc_varied_reload_depart" : "npc_reload_depart");
        const auto reload_id = character_id(data["combat_id"].get<int>());
        REQUIRE(data["combat_loadout"].get<std::string>() == (ak ? "rifle_ak_v1" : "rifle_field_v1"));
        using magazine_state = std::map<std::string, std::pair<int, bool>>;
        const auto magazine_snapshot = [&]() {
            const auto* actor = g->find_npc(reload_id);
            REQUIRE(actor != nullptr);
            magazine_state result;
            const auto* installed = actor->primary_weapon().magazine_current();
            const auto record = [&](const item* value, bool in_weapon) {
                if (!value || value->typeId().str() != magazine_type) { return; }
                if (value->ammo_remaining() > 0) { REQUIRE(value->ammo_current() == itype_id(ammo_type)); }
                const auto marker = value->get_var("trkv_reload_probe");
                REQUIRE_FALSE(marker.empty());
                REQUIRE(result.emplace(marker, std::make_pair(value->ammo_remaining(), in_weapon)).second);
            };
            // visit_internal deliberately does not descend into guns or magazines.
            // all_items covers carried spares; the fitted magazine needs its accessor.
            record(installed, true);
            for (const auto* value : actor->all_items(false)) {
                if (value != installed) { record(value, false); }
            }
            return result;
        };
        {
            auto* actor = g->find_npc(reload_id);
            REQUIRE(actor != nullptr);
            REQUIRE(actor->myclass == npc_class_id(ak ? "TRKV_COMBAT_AK" : "TRKV_COMBAT_FIELD"));
            REQUIRE(actor->primary_weapon().typeId().str() == weapon_type);
            REQUIRE(actor->primary_weapon().ammo_remaining() == 30);
            auto* loaded = actor->primary_weapon().magazine_current();
            REQUIRE(loaded != nullptr);
            loaded->set_var("trkv_reload_probe", "initial");
            auto spares = 0;
            for (auto* value : actor->all_items(false)) {
                if (value->typeId().str() == magazine_type && value != loaded) {
                    REQUIRE(value->ammo_remaining() == 30);
                    value->set_var("trkv_reload_probe", "spare_" + std::to_string(++spares));
                }
            }
            REQUIRE(spares == 2);
            const auto before_drain = magazine_snapshot();
            REQUIRE(before_drain.size() == 3);
            REQUIRE(before_drain.at("initial").second);
            auto issued_rounds = 0;
            for (const auto& entry : before_drain) { issued_rounds += entry.second.first; }
            REQUIRE(issued_rounds == 90);
            // Drain only the original loaded magazine; no rounds or reload items are
            // supplied by the test. The two original spare magazines remain intact.
            REQUIRE(actor->primary_weapon().ammo_consume(30, actor->bub_pos()) == 30);
            REQUIRE(actor->primary_weapon().ammo_remaining() == 0);
            auto rounds_after_drain = 0;
            for (const auto& entry : magazine_snapshot()) { rounds_after_drain += entry.second.first; }
            REQUIRE(rounds_after_drain == 60);
            auto& player = get_avatar();
            player.set_mutation(trait_id("DEBUG_NODMG"));
            const auto restore_damage = on_out_of_scope([&]() {
                player.unset_mutation(trait_id("DEBUG_NODMG"));
                player.set_all_parts_hp_to_max();
                player.clear_effects();
            });
            REQUIRE(player.primary_weapon().is_gun()); // Kept from the previous encounter.
            // Varied entry is south of the arena's horizontal wall (y=396).
            // Keep the target on that side; the legacy single actor is north.
            const auto target_position = ak ? tripoint_abs_ms(398, 400, 0)
                                         : tripoint_abs_ms(402, 388, 0);
            player.setpos(abs_to_bub(target_position));
            INFO("Reload weapon " << weapon_type << ", NPC " << actor->abs_pos().x()
                 << "," << actor->abs_pos().y() << ", target " << target_position.x()
                 << "," << target_position.y());
            set_time(calendar::turn);
            REQUIRE(actor->sees(player));
            auto reloaded = false;
            for (auto decision = 0; decision < 30; ++decision) {
                INFO("Production magazine reload decision " << decision);
                actor->set_moves(100);
                actor->move();
                REQUIRE(actor->get_moves() < 100);
                REQUIRE(actor->primary_weapon().typeId().str() == weapon_type);
                if (actor->primary_weapon().ammo_remaining() > 0) { reloaded = true; break; }
            }
            REQUIRE(reloaded);
            REQUIRE(actor->primary_weapon().ammo_remaining() == 30);
            loaded = actor->primary_weapon().magazine_current();
            REQUIRE(loaded != nullptr);
            const auto marker = loaded->get_var("trkv_reload_probe");
            REQUIRE((marker == "spare_1" || marker == "spare_2"));
            auto total_rounds = 0;
            for (const auto& entry : magazine_snapshot()) { total_rounds += entry.second.first; }
            REQUIRE(total_rounds == 60);
            auto fired = false;
            for (auto decision = 0; decision < 30; ++decision) {
                actor->set_moves(100);
                actor->move();
                REQUIRE(actor->get_moves() < 100);
                REQUIRE(actor->primary_weapon().typeId().str() == weapon_type);
                if (actor->primary_weapon().ammo_remaining() < 30) { fired = true; break; }
            }
            REQUIRE(fired);
            const auto spent = 30 - actor->primary_weapon().ammo_remaining();
            total_rounds = 0;
            for (const auto& entry : magazine_snapshot()) { total_rounds += entry.second.first; }
            REQUIRE(total_rounds == 60 - spent);
            REQUIRE(actor->is_wearing(itype_id(ak ? "tshirt" : "hoodie")));
            REQUIRE(actor->is_wearing(itype_id("pants_cargo")));
            actor->set_part_hp_cur(bodypart_str_id("arm_l").id(), 17);
            actor->recalc_hp();
            REQUIRE(actor->get_part_hp_cur(bodypart_str_id("arm_l").id()) == 17);
        }
        const auto magazines_after_combat = magazine_snapshot();
        probe(ak ? "npc_varied_checkpoint" : "npc_combat_checkpoint");
        REQUIRE(g->save(false));
        REQUIRE(g->load(saved_character));
        cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
        probe(ak ? "npc_varied_restored" : "npc_combat_restored");
        REQUIRE(magazine_snapshot() == magazines_after_combat);
        REQUIRE(g->find_npc(reload_id)->get_part_hp_cur(bodypart_str_id("arm_l").id()) == 17);
        REQUIRE(g->find_npc(reload_id)->get_part_hp_max(bodypart_str_id("arm_l").id()) == 60);
        REQUIRE(g->find_npc(reload_id)->primary_weapon().typeId().str() == weapon_type);
        std::vector<character_id> varied_ids;
        if (ak) {
            const sol::table ids = data["varied_ids"];
            for (auto i = 1; i <= 3; ++i) { varied_ids.emplace_back(ids[i].get<int>()); }
            for (auto i = 1; i < 3; ++i) {
                const auto* other = g->find_npc(varied_ids[i]);
                REQUIRE(other != nullptr);
                CHECK(other->myclass == npc_class_id(i == 1 ? "TRKV_COMBAT_RECRUIT_FIELD" : "TRKV_COMBAT_RECRUIT_AK"));
                CHECK(other->primary_weapon().typeId().str() == (i == 1 ? "m4a1" : "ak47"));
                CHECK(other->primary_weapon().ammo_remaining() == 30);
                CHECK(other->get_skill_level(skill_id("rifle")) == 3);
            }
        }
        probe("npc_extract");
        for (const auto id : varied_ids) {
            CHECK(g->find_npc(id) == nullptr);
            CHECK(get_overmapbuffer(home_dim).find_npc(id) == nullptr);
        }
        CHECK(g->find_npc(reload_id) == nullptr);
        CHECK(get_overmapbuffer(home_dim).find_npc(reload_id) == nullptr);
    };
    run_reload_probe(false);
    // Player-selectable group uses the two restricted role pools together.
    probe("npc_hostile_group_depart");
    const sol::table hostile_id_table = data["hostile_ids"];
    const sol::table hostile_choice_table = data["hostile_choices"];
    std::vector<character_id> hostile_ids;
    std::vector<std::string> hostile_choices;
    for (auto i = 1; i <= 3; ++i) {
        hostile_ids.emplace_back(hostile_id_table[i].get<int>());
        hostile_choices.emplace_back(hostile_choice_table[i].get<std::string>());
    }
    REQUIRE(hostile_ids[0] != hostile_ids[1]);
    REQUIRE(hostile_ids[0] != hostile_ids[2]);
    REQUIRE(hostile_ids[1] != hostile_ids[2]);
    const auto check_hostile_group = [&](bool changed, bool casualty) {
        CHECK(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == (casualty ? 2 : 3));
        for (auto i = 0; i < 3; ++i) {
            const auto* actor = g->find_npc(hostile_ids[i]);
            if (casualty && i == 2) {
                CHECK(actor == nullptr);
                CHECK(get_overmapbuffer(raid_dim).find_npc(hostile_ids[i]) == nullptr);
                continue;
            }
            REQUIRE(actor != nullptr);
            const auto trained = i == 0;
            const auto& choice = hostile_choices[i];
            const auto field = choice == "rifle_field_v1" || choice == "rifle_recruit_field_v1";
            if (trained) {
                REQUIRE((choice == "rifle_civilian_v1" || choice == "rifle_field_v1"));
            } else {
                REQUIRE((choice == "rifle_recruit_civilian_v1" || choice == "rifle_recruit_field_v1"));
            }
            const std::string npc_class_name = trained
                ? (field ? "TRKV_COMBAT_FIELD" : "TRKV_COMBAT_TEST")
                : (field ? "TRKV_COMBAT_RECRUIT_FIELD" : "TRKV_COMBAT_RECRUIT");
            CHECK(actor->myclass == npc_class_id(npc_class_name));
            CHECK(actor->get_value("trkv_loadout") == choice);
            CHECK(actor->get_attitude() == NPCATT_KILL);
            CHECK(actor->get_skill_level(skill_id("gun")) == (trained ? 6 : 3));
            CHECK(actor->get_skill_level(skill_id("rifle")) == (trained ? 6 : 3));
            CHECK(actor->get_str_base() == (trained ? 10 : 8));
            CHECK(actor->get_dex_base() == (trained ? 10 : 8));
            CHECK(actor->get_per_base() == (trained ? 10 : 8));
            CHECK(actor->primary_weapon().typeId().str() == (field ? "m4a1" : "ar15"));
            CHECK(actor->primary_weapon().ammo_remaining() == (field ? 30 : 17) - (changed && trained ? 3 : 0));
            CHECK(actor->get_part_hp_max(bodypart_str_id("arm_l").id()) == 60);
            CHECK(actor->get_part_hp_cur(bodypart_str_id("arm_l").id()) == (changed && trained ? 17 : 60));
            CHECK(actor->is_wearing(itype_id(field ? "hoodie" : "tshirt")));
        }
    };
    check_hostile_group(false, false);
    {
        auto* actor = g->find_npc(hostile_ids[0]);
        REQUIRE(actor != nullptr);
        REQUIRE(actor->primary_weapon().ammo_consume(3, actor->bub_pos()) == 3);
        actor->set_part_hp_cur(bodypart_str_id("arm_l").id(), 17);
        auto* victim = g->find_npc(hostile_ids[2]);
        REQUIRE(victim != nullptr);
        victim->set_all_parts_hp_cur(0);
        g->cleanup_dead();
    }
    data["hostile_dead_id"] = hostile_ids[2].get_value();
    check_hostile_group(true, true);
    probe("npc_hostile_group_checkpoint");
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_hostile_group_restored");
    check_hostile_group(true, true);
    probe("npc_extract");
    for (const auto id : hostile_ids) {
        CHECK(g->find_npc(id) == nullptr);
        CHECK(get_overmapbuffer(home_dim).find_npc(id) == nullptr);
    }
    // Occupy a fresh group entry with the avatar, including a real saved reload.
    probe("npc_reserved_enter");
    get_avatar().setpos(abs_to_bub(tripoint_abs_ms(398, 398, 0)));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_reserved_check");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 2);
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_reserved_check");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 2);
    get_avatar().setpos(abs_to_bub(tripoint_abs_ms(387, 387, 0)));
    // Replace the former avatar blocker with real impassable terrain. The same
    // choice stays reserved across another save/load, then creates after repair.
    probe("npc_reserved_wall");
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_reserved_check");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 2);
    character_id waiting_dead_id;
    {
        const sol::table waiting_ids = data["waiting_ids"];
        waiting_dead_id = character_id(waiting_ids[3].get<int>());
        auto* victim = g->find_npc(waiting_dead_id);
        REQUIRE(victim != nullptr);
        victim->set_all_parts_hp_cur(0);
        g->cleanup_dead();
    }
    data["waiting_dead_id"] = waiting_dead_id.get_value();
    probe("npc_reserved_check");
    REQUIRE(g->find_npc(waiting_dead_id) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).find_npc(waiting_dead_id) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 1);
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_reserved_check");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 1);
    REQUIRE(g->find_npc(waiting_dead_id) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).find_npc(waiting_dead_id) == nullptr);
    probe("npc_reserved_floor");
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    probe("npc_reserved_released");
    hostile_ids.clear();
    hostile_choices.clear();
    const sol::table released_ids = data["hostile_ids"];
    const sol::table released_choices = data["hostile_choices"];
    for (auto i = 1; i <= 3; ++i) {
        hostile_ids.emplace_back(released_ids[i].get<int>());
        hostile_choices.emplace_back(released_choices[i].get<std::string>());
    }
    REQUIRE(hostile_ids[2] == waiting_dead_id);
    check_hostile_group(false, true);
    probe("npc_extract");
    for (const auto id : hostile_ids) {
        CHECK(g->find_npc(id) == nullptr);
        CHECK(get_overmapbuffer(home_dim).find_npc(id) == nullptr);
    }
    for (auto sample_index = 0; sample_index < 12; ++sample_index) {
        npc sample;
        const auto sample_field = sample_index % 3 == 1;
        const auto sample_ak = sample_index % 3 == 2;
        const auto sample_recruit = sample_index % 6 >= 3;
        const std::string sample_class = sample_recruit
            ? (sample_ak ? "TRKV_COMBAT_RECRUIT_AK" : sample_field ? "TRKV_COMBAT_RECRUIT_FIELD" : "TRKV_COMBAT_RECRUIT")
            : (sample_ak ? "TRKV_COMBAT_AK" : sample_field ? "TRKV_COMBAT_FIELD" : "TRKV_COMBAT_TEST");
        sample.randomize(npc_class_id(sample_class));
        CHECK(sample.get_mutations().empty());
        CHECK(sample.get_bionics().empty());
        CHECK(sample.get_str_base() == (sample_recruit ? 8 : 10));
        CHECK(sample.get_dex_base() == (sample_recruit ? 8 : 10));
        CHECK(sample.get_int_base() == 8);
        CHECK(sample.get_per_base() == (sample_recruit ? 8 : 10));
        CHECK(sample.personality.aggression == 5);
        CHECK(sample.personality.bravery == 10);
        CHECK(sample.personality.collector == 0);
        CHECK(sample.personality.altruism == 0);
        CHECK(sample.get_skill_level(skill_id("barter")) == 0);
        for (const auto& skill : Skill::skills) {
            const auto shooting = skill.ident() == skill_id("gun") || skill.ident() == skill_id("rifle");
            CHECK(sample.get_skill_level(skill.ident()) == (shooting ? (sample_recruit ? 3 : 6) : 0));
        }
        CHECK(sample.primary_weapon().typeId().str() == (sample_ak ? "ak47" : sample_field ? "m4a1" : "ar15"));
        CHECK(sample.primary_weapon().ammo_remaining() == (sample_field || sample_ak ? 30 : 17));
        CHECK(sample.is_wearing(itype_id(sample_field ? "hoodie" : "tshirt")));
        auto spares = 0;
        for (const auto* value : sample.all_items(false)) {
            if (value->typeId().str() == (sample_ak ? "akmag30" : "stanag30") && value != sample.primary_weapon().magazine_current()) {
                ++spares;
                CHECK(value->ammo_remaining() == 30);
            }
        }
        CHECK(spares == (sample_field || sample_ak ? 2 : 0));
        for (const auto& part : sample.get_all_body_parts()) {
            const auto maximum = expected_hp.at(part->main_part.str());
            CHECK(sample.get_part_hp_max(part) == maximum);
            CHECK(sample.get_part_hp_cur(part) == maximum);
        }
    }
    const auto load_attributes = [](const std::string& text) {
        std::istringstream input(text);
        JsonIn json(input);
        const JsonObject object = json.get_object();
        npc_class definition;
        definition.load(object, "tarkov native profile test");
    };
    const std::string profile_json = R"({"name":"Profile test","job_description":"Profile test",
      "attribute_profile":{"stats":{"strength":10,"dexterity":10,"intelligence":8,"perception":10},
      "personality":{"aggression":5,"bravery":10,"collector":0,"altruism":0}}})";
    REQUIRE_NOTHROW(load_attributes(profile_json));
    auto invalid = profile_json;
    invalid.replace(invalid.find("\"strength\":10"), std::string("\"strength\":10").size(), "\"strength\":0");
    REQUIRE_THROWS_AS(load_attributes(invalid), JsonError);
    invalid = profile_json;
    invalid.replace(invalid.find("\"bravery\":10"), std::string("\"bravery\":10").size(), "\"bravery\":101");
    REQUIRE_THROWS_AS(load_attributes(invalid), JsonError);
    invalid = profile_json;
    invalid.erase(invalid.find(",\"perception\":10"), std::string(",\"perception\":10").size());
    REQUIRE_THROWS_AS(load_attributes(invalid), JsonError);
    auto hp_json = profile_json;
    const auto hp_position = hp_json.find("\"personality\"");
    const std::string hp_fields = R"("hit_points":{"head":35,"torso":85,"arm_l":60,"arm_r":60,"leg_l":65,"leg_r":65},)";
    hp_json.insert(hp_position, hp_fields);
    REQUIRE_NOTHROW(load_attributes(hp_json));
    invalid = hp_json;
    invalid.replace(invalid.find("\"head\":35"), std::string("\"head\":35").size(), "\"head\":0");
    REQUIRE_THROWS_AS(load_attributes(invalid), JsonError);
    invalid = hp_json;
    invalid.erase(invalid.find(",\"leg_r\":65"), std::string(",\"leg_r\":65").size());
    REQUIRE_THROWS_AS(load_attributes(invalid), JsonError);
    // An independent map bound to the primary world must retain ordinary
    // template creation while the player is in the restricted project space.
    {
        const override_option static_npcs("STATIC_NPC", "true");
        REQUIRE(g->get_current_dimension_info() != nullptr);
        REQUIRE_FALSE(g->get_current_dimension_info()->world_type->allow_mapgen_npcs);
        map elsewhere;
        elsewhere.bind_dimension(dimension_id());
        const auto control = elsewhere.place_npc(tripoint_bub_ms(10, 10, 0),
            string_id<npc_template>("trkv_combat_tester"));
        REQUIRE(control != character_id());
        REQUIRE(get_overmapbuffer(dimension_id()).find_npc(control) != nullptr);
        REQUIRE(get_overmapbuffer(dimension_id()).remove_npc(control) != nullptr);
    }

    run_reload_probe(true); // New AK kit after legacy combat checks to preserve their RNG.

    // A registered vanilla follower stays in its original dimension. Exercise
    // production travel and raid cleanup, including a save/load while away.
    character_id follower_id;
    tripoint_abs_ms follower_position;
    {
        auto& follower = spawn_npc(abs_to_bub(tripoint_abs_ms(395, 396, 0)), "test_talker");
        follower.set_fac(faction_id("your_followers"));
        follower.set_attitude(NPCATT_FOLLOW);
        g->add_npc_follower(follower.getID());
        REQUIRE(follower.is_player_ally());
        REQUIRE(follower.is_following());
        follower.set_value("trkv_home_follower", "stay_home");
        follower_id = follower.getID();
        follower_position = follower.abs_pos();
        REQUIRE(follower.get_dimension() == home_dim);
    }
    const auto check_home_follower = [&]() {
        const auto follower = get_overmapbuffer(home_dim).find_npc(follower_id);
        REQUIRE(follower != nullptr);
        CHECK(follower->get_dimension() == home_dim);
        CHECK(follower->abs_pos() == follower_position);
        CHECK(follower->get_value("trkv_home_follower") == "stay_home");
        CHECK(follower->is_following());
        CHECK(g->get_follower_list().count(follower_id) == 1);
        CHECK(get_overmapbuffer(raid_dim).find_npc(follower_id) == nullptr);
    };
    probe("npc_follower_enter");
    REQUIRE_FALSE(g->get_current_dimension_info()->world_type->allow_npc_travel);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    check_home_follower();
    REQUIRE(g->save(false));
    REQUIRE(g->load(saved_character));
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    REQUIRE_FALSE(g->get_current_dimension_info()->world_type->allow_npc_travel);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    check_home_follower();
    probe("npc_extract");
    check_home_follower();
    REQUIRE(g->find_npc(follower_id) != nullptr);
    g->remove_npc_follower(follower_id);

}
