// TRKV_DEV01_TEST_BEGIN
#include "item.h"

TEST_CASE("tarkov raid lifecycle uses real BN maps and save storage", "[tarkov]") {
    clear_all_state();
    initialize_dimension_test_storage();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    const auto cleanup = dimension_test_cleanup({
        dimension_id("trkv_dev01_home"), dimension_id("trkv_dev01_raid")
    });
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto test_data = lua.create_table();
    lua.globals()["test_data"] = test_data;
    test_data["stage"] = "enter";
    run_lua_test_script(lua, "trkv_integration_test.lua");

    auto rifle = item::spawn("ar15");
    auto magazine = item::spawn("stanag30");
    magazine->ammo_set(itype_id("223"), 17);
    rifle->put_in(std::move(magazine));
    auto strap = item::spawn("shoulder_strap");
    REQUIRE(rifle->is_gunmod_compatible(*strap).success());
    rifle->put_in(std::move(strap));
    rifle->set_damage(1375);
    rifle->set_var("trkv_fixture", "rifle");
    auto& carried_rifle = get_avatar().i_add(std::move(rifle));
    REQUIRE(carried_rifle.ammo_remaining() == 17);

    auto pack = item::spawn("backpack");
    auto bottle = item::spawn("bottle_plastic");
    bottle->put_in(item::spawn("water_clean", calendar::turn, 2));
    pack->put_in(std::move(bottle));
    pack->set_var("trkv_fixture", "nested_container");
    auto& carried_pack = get_avatar().i_add(std::move(pack));
    const auto snapshot = [](const item& value) -> std::string {
        auto output = std::ostringstream{};
        auto json = JsonOut(output);
        value.serialize(json);
        return output.str();
    };
    const auto rifle_before = snapshot(carried_rifle);
    const auto pack_before = snapshot(carried_pack);
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
    auto found_rifle = false;
    auto found_pack = false;
    for (const auto* value : get_avatar().all_items(false)) {
        if (value->get_var("trkv_fixture") == "rifle") {
            CHECK(snapshot(*value) == rifle_before);
            CHECK(value->ammo_remaining() == 17);
            found_rifle = true;
        } else if (value->get_var("trkv_fixture") == "nested_container") {
            CHECK(snapshot(*value) == pack_before);
            found_pack = true;
        }
    }
    REQUIRE(found_rifle);
    REQUIRE(found_pack);
    test_data["stage"] = "continue";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    CHECK(test_data["passed"].get<bool>());
    for (const auto* value : get_avatar().all_items(false)) {
        CHECK_FALSE(value->has_var("trkv_fixture"));
    }
    test_data["stage"] = "prepare_death";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    get_avatar().set_all_parts_hp_cur(0);
    CHECK_FALSE(get_avatar().is_dead_state());
    test_data["stage"] = "verify_death";
    run_lua_test_script(lua, "trkv_integration_test.lua");
}
// TRKV_DEV01_TEST_END
