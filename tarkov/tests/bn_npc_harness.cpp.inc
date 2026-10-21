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
    const auto spawn_guard = [&]() -> character_id {
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
        guard.set_moves(1000);
        data["actor"] = &guard;
        data["destination"] = abs_to_bub(moved_abs);
        probe("npc_step");
        data["actor"] = sol::nil; // Never retain a userdata reference across load/travel.
        return guard.getID();
    };
    probe("npc_enter");
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    const auto first_id = spawn_guard();
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().size() == 1);
    REQUIRE(g->save(false));
    const auto saved_character = save_t::from_save_id(get_avatar().get_save_id());
    REQUIRE(g->load(saved_character));
    const auto tick_scope = action_time_scale::scoped_calendar_turns_this_tick(1);
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
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
    probe("npc_extract");
    CHECK(g->find_npc(first_id) == nullptr);
    CHECK(get_overmapbuffer(home_dim).find_npc(first_id) == nullptr);
    probe("npc_enter");
    CHECK(g->find_npc(first_id) == nullptr);
    REQUIRE(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    const auto second_id = spawn_guard();
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
    CHECK(get_overmapbuffer(raid_dim).get_overmap_npcs().empty());
    probe("npc_extract");
}
