#pragma once

#include "character.h"
#include "type_id.h"

#include <optional>

namespace dda_port
{

// Authorization and destination selection are shared by the real examine
// handlers and their native regression tests. Transportation remains BN's.
inline auto hub_elevator_destination( const Character &actor, int current, int direction,
                                     int bottom, int top ) -> std::optional<int>
{
    if( !actor.has_trait( trait_id( "PROF_HUB01_ANCILLIARY" ) ) ||
        current < bottom || current > top ) {
        return std::nullopt;
    }
    if( direction == 1 && current < top ) {
        return current + 1;
    }
    if( direction == -1 && current > bottom ) {
        return current - 1;
    }
    return std::nullopt;
}

} // namespace dda_port
