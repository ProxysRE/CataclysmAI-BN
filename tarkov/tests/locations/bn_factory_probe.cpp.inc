// Test-only translation unit; no engine or production raid modifications.
#include "calendar.h"
#include "cata_utility.h"
#include "catch/catch.hpp"
#include "coordinates.h"
#include "game.h"
#include "map/mapbuffer.h"
#include "map/mapbuffer_registry.h"
#include "map/mapdata.h"
#include "map/submap.h"
#include "mapgen/mapgen_constructor.h"
#include "mapgen/mapgen_functions.h"
#include "overmap/overmapbuffer.h"
#include "overmap/overmapbuffer_registry.h"
#include "state_helpers.h"
#include "trap.h"
#include "type_id.h"
#include "worldfactory.h"

#include <array>
#include <string>
#include <string_view>

namespace {
#include "trkv_factory_fixture.inc"
} // namespace

TEST_CASE("factory ground draft generates matching BN tiles", "[trkv_factory]") {
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    const auto dim = dimension_id("trkv_factory_constructor_probe");
    auto* const world = g->get_active_world();
    REQUIRE(world != nullptr);
    REQUIRE_FALSE(world->has_dimension_data(dim.str()));
    const auto cleanup = on_out_of_scope([&]() {
        MAPBUFFER_REGISTRY.unload_dimension(dim);
        unload_overmapbuffer_dimension(dim);
        CHECK(world->delete_dimension_data(dim.str()));
    });
    auto& buffer = MAPBUFFER_REGISTRY.get(dim);
    auto& overmap = get_overmapbuffer(dim);
    const auto origin = tripoint_abs_omt(60, 60, 0);
    for (auto by = 0; by < factory_height / 24; ++by) {
        for (auto bx = 0; bx < factory_width / 24; ++bx) {
            const auto id = oter_id("trkv_loc_factory_01_g_" + std::to_string(bx) + "_"
                                    + std::to_string(by));
            REQUIRE(id.is_valid());
            overmap.ter_set(origin + point(bx, by), id);
        }
    }
    auto walkable_count = 0;
    for (auto by = 0; by < factory_height / 24; ++by) {
        for (auto bx = 0; bx < factory_width / 24; ++bx) {
            const auto omt = origin + point(bx, by);
            auto tile = mapgen_constructor(buffer);
            REQUIRE(tile.generate(omt, calendar::turn).is_generated());
            REQUIRE(tile.get_vehicles().empty());
            for (auto y = 0; y < 24; ++y) {
                for (auto x = 0; x < 24; ++x) {
                    const auto gx = bx * 24 + x;
                    const auto gy = by * 24 + y;
                    const auto p = point_omt_ms(x, y);
                    const auto symbol = factory_rows[gy][gx];
                    CAPTURE(gx, gy, symbol);
                    CHECK(tile.ter(p).id().str() == factory_terrain(symbol));
                    CHECK(tile.furn(p).id().str() == "f_null");
                    CHECK(tile.tr_at(p).is_null());
                    CHECK(tile.i_at(p).empty());
                    const auto expected_passable = symbol == '.' || symbol == 'S';
                    CHECK(tile.passable(p) == expected_passable);
                    if (tile.passable(p)) { ++walkable_count; }
                }
            }
            const auto base_sm = project_to<coords::sm>(omt);
            for (const auto offset : {point_zero, point_east, point_south, point_south_east}) {
                const auto* sm = buffer.lookup_submap_in_memory(base_sm + offset);
                REQUIRE(sm != nullptr);
                CHECK(sm->spawns.empty());
                CHECK(sm->field_count == 0);
            }
        }
    }
    CHECK(walkable_count > 0);
    CHECK(overmap.get_overmap_npcs().empty());
    // No claim of a connected multi-level raid, NPC routes, lighting or Windows UI.
}
