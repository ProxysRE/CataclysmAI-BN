#pragma once

#include <cmath>
#include <expected>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace dda_port {

/// Expression IR compiled from pinned DDA artisan dialogue, independent of BN objects.
struct expression {
    std::string op;
    double value = 0;
    std::string name;
    std::vector<expression> args;
};

struct evaluation_context {
    const std::unordered_map<std::string, double> &variables;
    double now_seconds = 0;
};

/// Return an error for malformed or non-finite calculations rather than granting rewards.
inline auto evaluate( const expression &node, const evaluation_context &context )
-> std::expected<double, std::string> {
    const auto valid_number = []( const auto value ) -> std::expected<double, std::string> {
        if( !std::isfinite( value ) ) {
            return std::unexpected( "Non-finite dialogue expression" );
        }
        return value;
    };
    if( node.op == "literal" && node.args.empty() ) {
        return valid_number( node.value );
    }
    if( node.op == "now" && node.args.empty() ) {
        return valid_number( context.now_seconds );
    }
    if( node.op == "variable" && node.args.empty() ) {
        const auto found = context.variables.find( node.name );
        return valid_number( found == context.variables.end() ? 0.0 : found->second );
    }
    if( node.op == "has_var" && node.args.size() == 1 && node.args[0].op == "variable" ) {
        return context.variables.contains( node.args[0].name ) ? 1.0 : 0.0;
    }
    if( node.args.size() == 1 ) {
        const auto argument = evaluate( node.args[0], context );
        if( !argument ) {
            return std::unexpected( argument.error() );
        }
        if( node.op == "ceil" ) {
            return valid_number( std::ceil( *argument ) );
        }
        if( node.op == "negate" ) {
            return valid_number( -*argument );
        }
        if( node.op == "not" ) {
            return *argument == 0 ? 1.0 : 0.0;
        }
    }
    if( node.args.size() == 2 ) {
        const auto lhs = evaluate( node.args[0], context );
        const auto rhs = evaluate( node.args[1], context );
        if( !lhs || !rhs ) {
            return std::unexpected( !lhs ? lhs.error() : rhs.error() );
        }
        if( node.op == "add" ) {
            return valid_number( *lhs + *rhs );
        }
        if( node.op == "subtract" ) {
            return valid_number( *lhs - *rhs );
        }
        if( node.op == "multiply" ) {
            return valid_number( *lhs * *rhs );
        }
        if( node.op == "divide" ) {
            if( *rhs == 0 ) {
                return std::unexpected( "Division by zero in dialogue expression" );
            }
            return valid_number( *lhs / *rhs );
        }
        if( node.op == "equal" ) {
            return *lhs == *rhs ? 1.0 : 0.0;
        }
        if( node.op == "not_equal" ) {
            return *lhs != *rhs ? 1.0 : 0.0;
        }
        if( node.op == "greater" ) {
            return *lhs > *rhs ? 1.0 : 0.0;
        }
        if( node.op == "greater_equal" ) {
            return *lhs >= *rhs ? 1.0 : 0.0;
        }
        if( node.op == "less" ) {
            return *lhs < *rhs ? 1.0 : 0.0;
        }
        if( node.op == "less_equal" ) {
            return *lhs <= *rhs ? 1.0 : 0.0;
        }
    }
    return std::unexpected( "Unknown operation or invalid arity: " + node.op );
}

} // namespace dda_port
