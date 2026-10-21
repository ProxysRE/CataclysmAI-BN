// Test-only cold restart probes, appended to BN's catalua_test.cpp.
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include "dimension_info.h"
#include "path_info.h"
#include "worldfactory.h"
#include "../src/map/mapbuffer_registry.h"

static auto trkv_cold_env(const char* name) -> std::string {
    const auto* value = std::getenv(name);
    REQUIRE(value != nullptr);
    REQUIRE(std::string(value).size() > 0);
    return value;
}
static auto trkv_cold_manifest() -> void {
    std::ofstream out(trkv_cold_env("TRKV_COLD_MANIFEST"));
    REQUIRE(out.good());
    out << std::filesystem::absolute(g->get_active_world()->info->folder_path()).string();
    out.close();
    REQUIRE(out.good());
}
TEST_CASE("tarkov cold writer saves a live raid", "[tarkov_cold_write]") {
    clear_all_state();
    initialize_dimension_test_storage();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto data = lua.create_table();
    lua.globals()["test_data"] = data;
    data["stage"] = "home";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    auto rifle = item::spawn("ar15");
    auto magazine = item::spawn("stanag30");
    magazine->ammo_set(itype_id("223"), 17);
    rifle->put_in(std::move(magazine));
    rifle->set_damage(1375);
    rifle->set_var("trkv_cold", "rifle");
    auto& carried = get_avatar().i_add(std::move(rifle));
    REQUIRE(get_avatar().wield(carried));
    data["stage"] = "cold_write";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    REQUIRE(g->save(false));
    trkv_cold_manifest();
    // No dimension cleanup: the next OS process must load these saved spaces.
}
TEST_CASE("tarkov cold reader loads a closed world's save", "[tarkov_cold_read]") {
    const auto source = std::filesystem::path(trkv_cold_env("TRKV_COLD_SOURCE"));
    const auto stage = trkv_cold_env("TRKV_COLD_STAGE");
    REQUIRE((stage == "cold_read_active" || stage == "cold_read_cleanup"));
    const auto destination = std::filesystem::path(PATH_INFO::savedir()) / "TRKV_COLD_FIXTURE";
    REQUIRE(std::filesystem::is_directory(source));
    REQUIRE_FALSE(std::filesystem::exists(destination));
    std::fprintf(stderr, "Tarkov cold: copying closed fixture\n");
    std::filesystem::copy(source, destination, std::filesystem::copy_options::recursive);
    std::fprintf(stderr, "Tarkov cold: fixture copied\n");
    // Follow the normal return-to-menu teardown before loading another world.
    // clear_all_state() only wipes the test bubble; setup() reloads item types,
    // so resident scratch submaps outside that bubble can keep dangling itype*.
    std::fprintf(stderr, "Tarkov cold: closing scratch session through normal teardown\n");
    REQUIRE(g->cleanup_at_end());
    for (const auto& id : MAPBUFFER_REGISTRY.active_dimension_ids()) {
        REQUIRE_FALSE(MAPBUFFER_REGISTRY.has_any_loaded(id));
    }
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    // test_main initialized a scratch world. Detach it before init() replaces
    // WORLDINFO entries, or options_manager keeps a dangling WORLD_OPTIONS pointer.
    world_generator->set_active_world(nullptr);
    std::fprintf(stderr, "Tarkov cold: loading world from menu state\n");
    REQUIRE(g->load(std::string("TRKV_COLD_FIXTURE")));
    std::fprintf(stderr, "Tarkov cold: world loaded\n");
    std::fprintf(stderr, "Tarkov cold: reading dimension info\n");
    const auto* info = g->get_current_dimension_info();
    REQUIRE(info != nullptr);
    CHECK(info->world_type.str() == "trkv_raid_space");
    std::fprintf(stderr, "Tarkov cold: dimension info checked\n");
    // setup() replaced Lua: obtain all Lua references only AFTER the world load.
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto data = lua.create_table();
    lua.globals()["test_data"] = data;
    std::fprintf(stderr, "Tarkov cold: Lua test context created\n");
    data["stage"] = stage + "_loaded";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    std::fprintf(stderr, "Tarkov cold: loaded state checked, invoking first tick\n");
    const auto tick_scope = action_time_scale::scoped_calendar_turns_this_tick(1);
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    std::fprintf(stderr, "Tarkov cold: first tick completed, checking equipment\n");
    bool found = false;
    for (const auto* value : get_avatar().all_items(false)) {
        if (value->get_var("trkv_cold") == "rifle") {
            CHECK(value->typeId().str() == "ar15");
            CHECK(value->ammo_remaining() == 17);
            CHECK(value->damage() == 1375);
            CHECK(get_avatar().is_wielding(*value));
            found = true;
        }
    }
    REQUIRE(found);
    std::fprintf(stderr, "Tarkov cold: equipment checked, invoking reader scenario\n");
    data["stage"] = stage;
    run_lua_test_script(lua, "trkv_integration_test.lua");
    std::fprintf(stderr, "Tarkov cold: reader scenario completed\n");
    trkv_cold_manifest();
}
