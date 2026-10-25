// Test-only translation unit. Installed into a disposable pinned BN checkout.
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
#include <queue>
#include <string>
#include <string_view>

namespace {

#include "trkv_location_fixture.inc"

struct generated_cell {
    bool passable = false;
};

struct route_options {
    point from;
    point to;
    bool exclude_west = false;
    bool exclude_hall = false;
};

auto reachable(const std::array<generated_cell, 72 * 72>& cells, const route_options& opts)
    -> bool {
    auto visited = std::array<bool, 72 * 72>{};
    auto pending = std::queue<point>{};
    pending.push(opts.from);
    visited[opts.from.y * 72 + opts.from.x] = true;
    while (!pending.empty()) {
        const auto current = pending.front();
        pending.pop();
        if (current == opts.to) { return true; }
        for (const auto delta : {point_north, point_south, point_east, point_west}) {
            const auto next = current + delta;
            if (next.x < 0 || next.x >= 72 || next.y < 0 || next.y >= 72) { continue; }
            const auto index = next.y * 72 + next.x;
            const auto in_body = next.y >= 5 && next.y < 60;
            if ((opts.exclude_west && next.x < 28 && in_body)
                || (opts.exclude_hall && next.x >= 27 && in_body)) {
                continue;
            }
            if (visited[index] || !cells[index].passable) { continue; }
            visited[index] = true;
            pending.push(next);
        }
    }
    return false;
}

} // namespace

TEST_CASE("industrial location generates nine matching BN tiles", "[trkv_locations]") {
    clear_all_state();
    const auto restore_mapgen = restore_on_out_of_scope<bool>(disable_mapgen);
    disable_mapgen = false;
    const auto dim = dimension_id("trkv_location_constructor_probe");
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
    auto actual = std::array<generated_cell, 72 * 72>{};

    // Set all nine IDs before generation so neighboring blocks see the layout.
    for (auto by = 0; by < 3; ++by) {
        for (auto bx = 0; bx < 3; ++bx) {
            const auto id = oter_id("trkv_loc_industrial_01_" + std::to_string(bx) + "_"
                                    + std::to_string(by));
            REQUIRE(id.is_valid());
            overmap.ter_set(origin + point(bx, by), id);
        }
    }
    for (auto by = 0; by < 3; ++by) {
        for (auto bx = 0; bx < 3; ++bx) {
            const auto omt = origin + point(bx, by);
            auto tile = mapgen_constructor(buffer);
            REQUIRE(tile.generate(omt, calendar::turn).is_generated());
            REQUIRE(tile.get_vehicles().empty());
            for (auto y = 0; y < 24; ++y) {
                for (auto x = 0; x < 24; ++x) {
                    const auto gx = bx * 24 + x;
                    const auto gy = by * 24 + y;
                    const auto p = point_omt_ms(x, y);
                    const auto symbol = fixture_rows[gy][gx];
                    CAPTURE(gx, gy, symbol);
                    CHECK(tile.ter(p).id().str() == fixture_terrain(symbol));
                    CHECK(tile.furn(p).id().str() == fixture_furniture(symbol));
                    CHECK(tile.tr_at(p).is_null());
                    CHECK(tile.i_at(p).empty());
                    actual[gy * 72 + gx].passable = tile.passable(p);
                    if (tile.furn(p).id().str() == "f_olight_nogrid") {
                        CHECK(tile.furn(p)->light_emitted == 120);
                    }
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
    CHECK(overmap.get_overmap_npcs().empty());
    // Closed-door topology comes from real generated BN movement costs.
    for (const auto entry : fixture_entries) {
        REQUIRE(actual[entry.y * 72 + entry.x].passable);
        for (const auto exit : fixture_exits) {
            CHECK(reachable(actual, {.from = entry, .to = exit}));
        }
        for (const auto poi : fixture_pois) {
            CHECK(reachable(actual, {.from = entry, .to = poi}));
        }
    }
    CHECK(reachable(actual, {.from = point(24, 65), .to = point(24, 3), .exclude_west = true}));
    CHECK(reachable(actual, {.from = point(24, 65), .to = point(24, 3), .exclude_hall = true}));
    // This probe does not claim engine NPC pathfinding, opening doors or a lightmap.
}
