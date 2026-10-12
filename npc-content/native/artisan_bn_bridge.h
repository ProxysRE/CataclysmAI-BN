#pragma once

#include "artisan_expression.h"
#include "calendar.h"
#include "json.h"
#include "player.h"

#include <charconv>
#include <array>
#include <ranges>

namespace dda_port {

inline auto read_expression( const JsonObject &object ) -> expression {
    auto result = expression{ .op = object.get_string( "op" ) };
    if( result.op == "literal" ) {
        result.value = object.get_float( "value" );
    }
    if( result.op == "variable" ) {
        result.name = object.get_string( "name" );
        const auto actor = object.get_string( "actor", "player" );
        if( actor != "player" && actor != "npc" ) {
            object.throw_error( "Unknown dialogue variable actor" );
        }
        result.npc_actor = actor == "npc";
    }
    if( object.has_array( "args" ) ) {
        for( const auto entry : object.get_array( "args" ) ) {
            result.args.push_back( read_expression( entry.get_object() ) );
        }
    }
    const auto unary = result.op == "ceil" || result.op == "negate" || result.op == "not" || result.op == "has_var";
    const auto leaf = result.op == "literal" || result.op == "variable" || result.op == "now";
    const auto binary = result.op == "add" || result.op == "subtract" || result.op == "multiply" || result.op == "divide" ||
                        result.op == "equal" || result.op == "not_equal" || result.op == "greater" || result.op == "greater_equal" ||
                        result.op == "less" || result.op == "less_equal";
    if( ( !unary && !leaf && !binary ) || result.args.size() != ( unary ? 1U : binary ? 2U : 0U ) ) {
        object.throw_error( "Invalid artisan expression operation or arity" );
    }
    if( result.op == "has_var" && result.args[0].op != "variable" ) {
        object.throw_error( "has_var requires a variable" );
    }
    return result;
}

struct expression_actors {
    const player &actor;
    const player *npc = nullptr;
};

inline auto collect_values( const expression &node, const expression_actors &actors,
                            std::unordered_map<std::string, double> &values ) -> std::expected<void, std::string> {
    const auto &variable = node.op == "has_var" ? node.args[0] : node;
    const auto *actor = variable.npc_actor ? actors.npc : &actors.actor;
    if( ( node.op == "variable" || node.op == "has_var" ) && !actor ) {
        return std::unexpected( "NPC dialogue variable requires an NPC actor" );
    }
    if( node.op == "has_var" ) {
        const auto &name = node.args[0].name;
        if( !actor->get_value( "npctalk_var_" + name ).empty() ) {
            values.try_emplace( variable.npc_actor ? "@npc:" + name : name, 0 );
        }
        return {};
    }
    if( node.op == "variable" ) {
        const auto raw = actor->get_value( "npctalk_var_" + node.name );
        if( !raw.empty() ) {
            auto number = 0.0;
            const auto parsed = std::from_chars( raw.data(), raw.data() + raw.size(), number );
            if( parsed.ec != std::errc{} || parsed.ptr != raw.data() + raw.size() || !std::isfinite( number ) ) {
                return std::unexpected( "Invalid numeric artisan variable: " + node.name );
            }
            values[node.npc_actor ? "@npc:" + node.name : node.name] = number;
        }
    }
    for( const auto &child : node.args ) {
        const auto collected = collect_values( child, actors, values );
        if( !collected ) {
            return collected;
        }
    }
    return {};
}

inline auto evaluate_for_player( const expression &node, const player &actor, const player *npc = nullptr )
-> std::expected<double, std::string> {
    auto values = std::unordered_map<std::string, double>{};
    const auto collected = collect_values( node, { .actor = actor, .npc = npc }, values );
    if( !collected ) {
        return std::unexpected( collected.error() );
    }
    return evaluate( node, {
        .variables = values,
        .now_seconds = to_seconds<double>( calendar::turn - calendar::turn_zero )
    } );
}

inline auto store_numeric_value( player &actor, const std::string &name, const double value ) -> void {
    auto text = std::array<char, 64>{};
    const auto converted = std::to_chars( text.data(), text.data() + text.size(), value );
    if( converted.ec == std::errc{} ) {
        actor.set_value( "npctalk_var_" + name, std::string( text.data(), converted.ptr ) );
    }
}

} // namespace dda_port
