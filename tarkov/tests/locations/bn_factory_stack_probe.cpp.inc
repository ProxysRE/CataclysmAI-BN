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
#include <queue>
#include <vector>

namespace {
#include "trkv_factory_stack_fixture.inc"
} // namespace

TEST_CASE("factory stack generates matching levels and paired stairs", "[trkv_factory_stack]") {
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    const auto dim = dimension_id("trkv_factory_stack_constructor_probe");
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
    auto cells = std::vector<unsigned char>(stack_levels * stack_width * stack_height, 0);
    const auto index = [](const tripoint& p) -> int {
        return (p.z * stack_height + p.y) * stack_width + p.x;
    };
    for (auto level = 0; level < stack_levels; ++level) {
        for (auto by = 0; by < stack_height / 24; ++by) {
            for (auto bx = 0; bx < stack_width / 24; ++bx) {
                const auto id = oter_id("trkv_loc_factory_stack_" + std::to_string(level) + "_" + std::to_string(bx) + "_"
                                        + std::to_string(by));
                REQUIRE(id.is_valid());
                overmap.ter_set(tripoint_abs_omt(60 + bx, 60 + by, level - 1), id);
            }
        }
    }
    for (auto level = 0; level < stack_levels; ++level) {
        for (auto by = 0; by < stack_height / 24; ++by) {
            for (auto bx = 0; bx < stack_width / 24; ++bx) {
                const auto omt = tripoint_abs_omt(60 + bx, 60 + by, level - 1);
                auto tile = mapgen_constructor(buffer);
                REQUIRE(tile.generate(omt, calendar::turn).is_generated());
                REQUIRE(tile.get_vehicles().empty());
                for (auto y = 0; y < 24; ++y) {
                    for (auto x = 0; x < 24; ++x) {
                        const auto gx = bx * 24 + x;
                        const auto gy = by * 24 + y;
                        const auto p = point_omt_ms(x, y);
                        const auto symbol = stack_rows[level * stack_height + gy][gx];
                        CAPTURE(level, gx, gy, symbol);
                        CHECK(tile.ter(p).id().str() == stack_terrain(symbol));
                        CHECK(tile.furn(p).id().str() == "f_null");
                        if (symbol == '~') {
                            CHECK(tile.tr_at(p).id.str() == "tr_ledge");
                            CHECK(tile.has_flag("TRANSPARENT", p));
                        } else {
                            CHECK(tile.tr_at(p).is_null());
                        }
                        CHECK(tile.has_flag("NO_FLOOR", p) == (symbol == '~'));
                        CHECK(tile.i_at(p).empty());
                        const auto expected_passable = symbol == '.' || symbol == 'S' || symbol == '<' || symbol == '>' || symbol == '~';
                        CHECK(tile.passable(p) == expected_passable);
                        CHECK(tile.has_flag("GOES_UP", p) == (symbol == '<'));
                        CHECK(tile.has_flag("GOES_DOWN", p) == (symbol == '>'));
                        cells[index(tripoint(gx, gy, level))] = static_cast<unsigned char>(
                            (tile.passable(p) && !tile.has_flag("NO_FLOOR", p) ? 1 : 0) | (tile.has_flag("GOES_UP", p) ? 2 : 0)
                            | (tile.has_flag("GOES_DOWN", p) ? 4 : 0));
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
    }
    auto visited = std::vector<bool>(cells.size(), false);
    auto pending = std::queue<tripoint>{};
    REQUIRE((cells[index(stack_anchor)] & 1) != 0);
    pending.push(stack_anchor);
    visited[index(stack_anchor)] = true;
    auto reached = 0;
    while (!pending.empty()) {
        const auto p = pending.front();
        pending.pop();
        ++reached;
        const auto bits = cells[index(p)];
        for (const auto delta : {tripoint(1, 0, 0), tripoint(-1, 0, 0), tripoint(0, 1, 0),
                                  tripoint(0, -1, 0), tripoint(0, 0, 1), tripoint(0, 0, -1)}) {
            const auto n = p + delta;
            if (n.x < 0 || n.x >= stack_width || n.y < 0 || n.y >= stack_height
                || n.z < 0 || n.z >= stack_levels) { continue; }
            const auto next_bits = cells[index(n)];
            if (delta.z == 1 && ((bits & 2) == 0 || (next_bits & 4) == 0)) { continue; }
            if (delta.z == -1 && ((bits & 4) == 0 || (next_bits & 2) == 0)) { continue; }
            if (visited[index(n)] || (next_bits & 1) == 0) { continue; }
            visited[index(n)] = true;
            pending.push(n);
        }
    }
    CHECK(reached == stack_expected_main_size);
    CHECK(overmap.get_overmap_npcs().empty());
    // Graph uses generated movement/transition flags; no actor climbing or NPC pathfinding claim.
}
