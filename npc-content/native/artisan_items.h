#pragma once

#include "artisan_bn_bridge.h"
#include "item.h"

#include <limits>

namespace dda_port {

struct item_specification {
    std::string id;
    std::string variable;
    expression count;
};

struct resolved_item {
    itype_id id;
    int count;
};

inline auto read_item_specification( const JsonObject &object ) -> item_specification {
    const auto reference = object.get_object( "item" );
    if( reference.has_string( "id" ) == reference.has_string( "variable" ) ) {
        reference.throw_error( "An artisan item requires exactly one ID or variable" );
    }
    return {
        .id = reference.get_string( "id", "" ),
        .variable = reference.get_string( "variable", "" ),
        .count = read_expression( object.get_object( "count" ) )
    };
}

inline auto resolve_item( const item_specification &specification, const player &actor )
-> std::expected<resolved_item, std::string> {
    const auto id = itype_id( specification.variable.empty() ? specification.id :
                             actor.get_value( "npctalk_var_" + specification.variable ) );
    if( id.is_null() || !id.is_valid() ) {
        return std::unexpected( "Unknown artisan item: " + id.str() );
    }
    const auto count = evaluate_for_player( specification.count, actor );
    if( !count ) {
        return std::unexpected( count.error() );
    }
    if( *count < 0 || *count > std::numeric_limits<int>::max() || std::trunc( *count ) != *count ) {
        return std::unexpected( "Artisan item count must be a nonnegative integer" );
    }
    return resolved_item{ .id = id, .count = static_cast<int>( *count ) };
}

inline auto has_items( const player &actor, const resolved_item &request ) -> bool {
    return item::count_by_charges( request.id ) ? actor.has_charges( request.id, request.count ) :
           actor.has_amount( request.id, request.count );
}

/// DDA rewards use exact charges, load default ammunition, and drop overflow nearby.
inline auto give_items( player &actor, const resolved_item &request ) -> void {
    if( request.count == 0 ) {
        return;
    }
    if( item::count_by_charges( request.id ) ) {
        auto reward = item::spawn( request.id, calendar::turn );
        reward->charges = request.count;
        actor.i_add_or_drop( std::move( reward ) );
        return;
    }
    for( const auto index : std::views::iota( 0, request.count ) ) {
        static_cast<void>( index );
        auto reward = item::spawn( request.id, calendar::turn );
        if( !reward->ammo_default().is_null() ) {
            reward->ammo_set( reward->ammo_default() );
        }
        actor.i_add_or_drop( std::move( reward ) );
    }
}

/// Validate before removing anything so an insufficient payment leaves inventory intact.
inline auto transfer_items( player &sender, player &recipient, const resolved_item &request ) -> bool {
    if( !has_items( sender, request ) ) {
        return false;
    }
    auto payment = item::count_by_charges( request.id ) ? sender.use_charges( request.id, request.count ) :
                   sender.use_amount( request.id, request.count );
    for( auto &entry : payment ) {
        entry->set_owner( recipient );
        recipient.i_add( std::move( entry ) );
    }
    return true;
}

} // namespace dda_port
