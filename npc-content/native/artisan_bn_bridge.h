#pragma once

#include "artisan_expression.h"
#include "calendar.h"
#include "json.h"
#include "player.h"
#include "npc.h"
#include "game.h"

#include <charconv>
#include <array>
#include <ranges>
#include <limits>

namespace dda_port {

inline auto read_expression( const JsonObject &object ) -> expression {
    auto result = expression{ .op = object.get_string( "op" ) };
    if( result.op == "literal" ) {
        result.value = object.get_float( "value" );
    }
    if( result.op == "npc_opinion" ) {
        result.name = object.get_string( "name" );
        if( result.name != "anger" && result.name != "fear" && result.name != "trust" && result.name != "value" ) {
            object.throw_error( "Unknown NPC opinion field" );
        }
    }
    if( result.op == "variable" ) {
        result.name = object.get_string( "name" );
        const auto actor = object.get_string( "actor", "player" );
        if( actor != "player" && actor != "npc" && actor != "global" ) {
            object.throw_error( "Unknown dialogue variable actor" );
        }
        result.npc_actor = actor == "npc";
        result.global_actor = actor == "global";
    }
    if( object.has_array( "args" ) ) {
        for( const auto entry : object.get_array( "args" ) ) {
            result.args.push_back( read_expression( entry.get_object() ) );
        }
    }
    const auto unary = result.op == "ceil" || result.op == "negate" || result.op == "not" || result.op == "has_var";
    const auto leaf = result.op == "literal" || result.op == "variable" || result.op == "now" || result.op == "npc_opinion";
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
    if( node.op == "npc_opinion" ) {
        const auto *speaker = dynamic_cast<const npc *>( actors.npc );
        if( !speaker ) {
            return std::unexpected( "NPC opinion requires an NPC actor" );
        }
        const auto &opinion = speaker->op_of_u;
        if( node.name == "anger" ) {
            values["@opinion:anger"] = opinion.anger;
        } else if( node.name == "fear" ) {
            values["@opinion:fear"] = opinion.fear;
        } else if( node.name == "trust" ) {
            values["@opinion:trust"] = opinion.trust;
        } else if( node.name == "value" ) {
            values["@opinion:value"] = opinion.value;
        } else {
            return std::unexpected( "Unknown NPC opinion field" );
        }
        return {};
    }
    const auto &variable = node.op == "has_var" ? node.args[0] : node;
    const auto *actor = variable.npc_actor ? actors.npc : &actors.actor;
    if( ( node.op == "variable" || node.op == "has_var" ) && !actor ) {
        return std::unexpected( "NPC dialogue variable requires an NPC actor" );
    }
    if( node.op == "has_var" ) {
        const auto &name = node.args[0].name;
        if( variable.global_actor ) {
            const auto found = g->dda_global_variables.find( name );
            if( found != g->dda_global_variables.end() && !found->second.empty() ) {
                values.try_emplace( "@global:" + name, 0 );
            }
            return {};
        }
        if( !actor->get_value( "npctalk_var_" + name ).empty() ) {
            values.try_emplace( variable.npc_actor ? "@npc:" + name : name, 0 );
        }
        return {};
    }
    if( node.op == "variable" ) {
        auto raw = std::string{};
        if( node.global_actor ) {
            const auto found = g->dda_global_variables.find( node.name );
            if( found != g->dda_global_variables.end() ) {
                raw = found->second;
            }
        } else {
            raw = actor->get_value( "npctalk_var_" + node.name );
        }
        if( !raw.empty() ) {
            auto number = 0.0;
            const auto parsed = std::from_chars( raw.data(), raw.data() + raw.size(), number );
            if( parsed.ec != std::errc{} || parsed.ptr != raw.data() + raw.size() || !std::isfinite( number ) ) {
                return std::unexpected( "Invalid numeric artisan variable: " + node.name );
            }
            values[node.global_actor ? "@global:" + node.name : node.npc_actor ? "@npc:" + node.name : node.name] = number;
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

inline auto store_numeric_value( player &actor, const std::string &name, const double value, const bool global = false ) -> void {
    auto text = std::array<char, 64>{};
    const auto converted = std::to_chars( text.data(), text.data() + text.size(), value );
    if( converted.ec == std::errc{} ) {
        const auto result = std::string( text.data(), converted.ptr );
        if( global ) {
            g->dda_global_variables[name] = result;
        } else {
            actor.set_value( "npctalk_var_" + name, result );
        }
    }
}

inline auto store_npc_opinion( npc &actor, const std::string &name, const double value ) -> bool {
    if( !std::isfinite( value ) || value < std::numeric_limits<int>::min() || value > std::numeric_limits<int>::max() ) {
        return false;
    }
    auto *field = name == "anger" ? &actor.op_of_u.anger :
                  name == "fear" ? &actor.op_of_u.fear :
                  name == "trust" ? &actor.op_of_u.trust :
                  name == "value" ? &actor.op_of_u.value : nullptr;
    if( !field ) {
        return false;
    }
    *field = static_cast<int>( value );
    return true;
}

} // namespace dda_port
