#pragma once

#include "json.h"
#include <cstdint>
#include <map>
#include <string>

namespace dda_port {

// DDA stores nutrients in calories (one thousandth of a kcal), with a raw
// expiration turn. Zero means nonperishable. Keep the complete source ledger.
struct faction_food_lot {
    std::int64_t expires = 0;
    std::int64_t calories = 0;
    std::map<std::string, int> vitamins;

    auto deserialize( JsonIn &input ) -> void {
        auto pair = input.get_array();
        if( pair.size() != 2 ) {
            pair.throw_error( "Faction food stock requires expiry and nutrients" );
        }
        pair.read( 0, expires );
        const auto nutrients = pair.get_object( 1 );
        nutrients.read( "calories", calories, true );
        nutrients.read( "vitamins", vitamins );
        if( calories < 0 ) {
            nutrients.throw_error( "Faction food calories cannot be negative" );
        }
    }

    auto serialize( JsonOut &output ) const -> void {
        output.start_array();
        output.write( expires );
        output.start_object();
        output.member( "calories", calories );
        output.member( "vitamins", vitamins );
        output.end_object();
        output.end_array();
    }
};

} // namespace dda_port
