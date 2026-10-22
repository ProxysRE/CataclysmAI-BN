#include "world_type.h"
// Test-only cold restart probes, appended to BN's catalua_test.cpp.
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include "dimension_info.h"
#include "path_info.h"
#include "worldfactory.h"
#include "npc.h"
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
static auto trkv_cold_check_npcs(sol::table& data, bool resume) -> void {
    const sol::table ids = data["cold_npc_ids"];
    REQUIRE(ids.size() == 3);
    REQUIRE(get_overmapbuffer(dimension_id("trkv_dev01_raid")).get_overmap_npcs().size() == 2);
    for (auto i = 1; i <= 3; ++i) {
        const auto id = character_id(ids[i].get<int>());
        auto* actor = g->find_npc(id);
        if (i == 3) {
            REQUIRE(actor == nullptr);
            REQUIRE(get_overmapbuffer(dimension_id("trkv_dev01_raid")).find_npc(id) == nullptr);
            continue;
        }
        REQUIRE(actor != nullptr);
        CHECK(actor->get_dimension() == dimension_id("trkv_dev01_raid"));
        CHECK(actor->get_attitude() == NPCATT_NULL);
        REQUIRE(actor->abs_pos() == tripoint_abs_ms(i == 1 ? 398 : 400, 399, 0));
        if (i == 1) {
            const auto head = bodypart_str_id("head").id();
            CHECK(actor->get_part_hp_max(head) == 35);
            CHECK(actor->get_part_hp_cur(head) == 21);
            actor->recalc_hp();
            CHECK(actor->get_part_hp_max(head) == 35);
            CHECK(actor->get_part_hp_cur(head) == 21);
            const auto& gun = actor->primary_weapon();
            CHECK(gun.get_var("trkv_cold_npc") == "rifle");
            CHECK(gun.typeId().str() == "ar15");
            CHECK(gun.ammo_remaining() == 11);
            CHECK(gun.damage() == 901);
            if (resume) {
                actor->set_moves(1000);
                actor->move(); // Production TRKV_PATROL after a fresh-process load.
                CHECK(actor->abs_pos() == tripoint_abs_ms(398, 400, 0));
                CHECK(actor->get_moves() < 1000);
                CHECK(actor->primary_weapon().ammo_remaining() == 11);
            }
        }
    }
    auto corpses = 0;
    auto dropped = 0;
    for (const auto* value : g->m.i_at(abs_to_bub(tripoint_abs_ms(404, 399, 0)))) {
        if (value->is_corpse()) { ++corpses; }
        if (value->get_var("trkv_cold_npc") == "dropped") { ++dropped; }
    }
    REQUIRE(corpses == 1);
    REQUIRE(dropped == 1);
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
    {
        const sol::table ids = data["cold_npc_ids"];
        REQUIRE(ids.size() == 3);
        for (auto i = 1; i <= 3; ++i) {
            auto* actor = g->find_npc(character_id(ids[i].get<int>()));
            REQUIRE(actor != nullptr);
            actor->set_moves(1000);
            actor->move();
            REQUIRE(actor->get_moves() < 1000);
            if (i == 1) {
                actor->remove_primary_weapon();
                auto gun = item::spawn("ar15");
                auto mag = item::spawn("stanag30");
                mag->ammo_set(itype_id("223"), 11);
                gun->put_in(std::move(mag));
                gun->set_damage(901);
                gun->set_var("trkv_cold_npc", "rifle");
                auto& equipped = actor->i_add(std::move(gun));
                REQUIRE(actor->wield(equipped));
                // Probe saved HP overrides across processes independently of
                // the combat-class creation test in the NPC harness.
                actor->set_value("npc_profile_hp_head", "35");
                actor->recalc_hp();
                actor->set_part_hp_cur(bodypart_str_id("head").id(), 21);
            } else if (i == 3) {
                auto dropped = item::spawn("rock");
                dropped->set_var("trkv_cold_npc", "dropped");
                actor->i_add(std::move(dropped));
                actor->set_all_parts_hp_cur(0);
            }
        }
        g->cleanup_dead();
    }
    trkv_cold_check_npcs(data, false);
    data["stage"] = "cold_npc_saved";
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
    CHECK_FALSE(info->world_type->allow_random_npcs);
    std::fprintf(stderr, "Tarkov cold: dimension info checked\n");
    // setup() replaced Lua: obtain all Lua references only AFTER the world load.
    auto& lua = DynamicDataLoader::get_instance().lua->lua;
    auto data = lua.create_table();
    lua.globals()["test_data"] = data;
    std::fprintf(stderr, "Tarkov cold: Lua test context created\n");
    data["stage"] = stage + "_loaded";
    run_lua_test_script(lua, "trkv_integration_test.lua");
    std::fprintf(stderr, "Tarkov cold: loaded state checked, invoking first tick\n");
    if (stage == "cold_read_active") { trkv_cold_check_npcs(data, false); }
    const auto tick_scope = action_time_scale::scoped_calendar_turns_this_tick(1);
    cata::run_on_every_x_hooks(*DynamicDataLoader::get_instance().lua);
    if (stage == "cold_read_active") {
        data["stage"] = "cold_npc_restored";
        run_lua_test_script(lua, "trkv_integration_test.lua");
        trkv_cold_check_npcs(data, true);
    }
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
    {
        const sol::table ids = data["cold_npc_ids"];
        for (auto i = 1; i <= 3; ++i) {
            const auto id = character_id(ids[i].get<int>());
            CHECK(g->find_npc(id) == nullptr);
            CHECK(get_overmapbuffer(dimension_id("trkv_dev01_raid")).find_npc(id) == nullptr);
            CHECK(get_overmapbuffer(dimension_id("trkv_dev01_home")).find_npc(id) == nullptr);
        }
    }
    std::fprintf(stderr, "Tarkov cold: reader scenario completed\n");
    trkv_cold_manifest();
}
