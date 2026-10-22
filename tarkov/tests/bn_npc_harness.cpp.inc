#include "npc_class.h"
#include "map_helpers.h"
#include <vector>
#include <cstdlib>

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
    data["stage"] = "home";
    run_lua_test_script(lua, "trkv_integration_test.lua");
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
    probe("npc_enter");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
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
    probe("npc_extract");
    for (const auto id : live_group) { CHECK(g->find_npc(id) == nullptr); }
    probe("npc_live_depart");
    const auto timeout_group = group_ids();
    for (const auto id : timeout_group) {
        for (const auto old_id : live_group) { CHECK(id != old_id); }
    }
    probe("npc_live_timeout");
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    for (const auto id : timeout_group) { CHECK(g->find_npc(id) == nullptr); }
    probe("npc_live_empty");
    probe("npc_extract");
}
