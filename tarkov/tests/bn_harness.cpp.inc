// TRKV_DEV01_TEST_BEGIN
TEST_CASE("tarkov raid lifecycle uses real BN maps and save storage", "[tarkov]") {
    clear_all_state();
    initialize_dimension_test_storage();
    const auto cleanup = dimension_test_cleanup({
        dimension_id("trkv_dev01_home"), dimension_id("trkv_dev01_raid")
    });
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto test_data = lua.create_table();
    lua.globals()["test_data"] = test_data;
    test_data["stage"] = "enter";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    REQUIRE(g->save(false));

    // Round-trip the actual on-disk mod state through BN's own deserializer.
    auto restored_root = lua.create_table();
    auto* const active_world = g->get_active_world();
    REQUIRE(active_world != nullptr);
    REQUIRE(active_world->read_from_file("lua_state.json", [&](std::istream& input) {
        auto jsin = JsonIn(input);
        auto saved = jsin.get_object();
        saved.allow_omitted_members();
        auto mod_data = saved.get_object("trkv_raid_core");
        cata::deserialize_lua_table(restored_root, mod_data);
    }, false));
    REQUIRE(restored_root["raid"].is<sol::table>());
    test_data["restored"] = restored_root["raid"].get<sol::table>();
    test_data["stage"] = "restore";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    CHECK(test_data["passed"].get<bool>());
}
// TRKV_DEV01_TEST_END
