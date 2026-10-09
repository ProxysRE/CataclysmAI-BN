#include "artisan_expression.h"

#include <cassert>
#include <limits>

auto main() -> int {
    using dda_port::expression;
    const auto literal = []( const auto value ) { return expression{ .op = "literal", .value = value }; };
    const auto variable = []( const auto &name ) { return expression{ .op = "variable", .name = name }; };
    const auto binary = []( const auto &op, const auto &lhs, const auto &rhs ) {
        return expression{ .op = op, .args = { lhs, rhs } };
    };
    auto variables = std::unordered_map<std::string, double>{
        { "timer_started", 100 }, { "wait_weeks", 3 }, { "credit", 38 }
    };
    const auto elapsed = binary( "subtract", expression{ .op = "now" }, variable( "timer_started" ) );
    const auto wait_seconds = binary( "multiply", variable( "wait_weeks" ), literal( 7 * 86400.0 ) );
    const auto ready = binary( "greater_equal", elapsed, wait_seconds );
    assert( dda_port::evaluate( ready, { .variables = variables, .now_seconds = 100 + 21 * 86400 - 1 } ) == 0 );
    assert( dda_port::evaluate( ready, { .variables = variables, .now_seconds = 100 + 21 * 86400 } ) == 1 );
    const auto context = dda_port::evaluation_context{ .variables = variables, .now_seconds = 0 };
    const auto cost = binary( "divide", literal( 77.0 ), literal( 2.0 ) );
    const auto affordable = binary( "greater_equal", variable( "credit" ), cost );
    assert( dda_port::evaluate( cost, context ) == 38.5 );
    assert( dda_port::evaluate( affordable, context ) == 0 );
    variables["credit"] = 39;
    assert( dda_port::evaluate( affordable, context ) == 1 );
    assert( dda_port::evaluate( expression{ .op = "ceil", .args = { cost } }, context ) == 39 );
    assert( dda_port::evaluate( expression{ .op = "has_var", .args = { variable( "missing" ) } }, context ) == 0 );
    variables["missing"] = 0;
    assert( dda_port::evaluate( expression{ .op = "has_var", .args = { variable( "missing" ) } }, context ) == 1 );
    assert( !dda_port::evaluate( binary( "divide", literal( 1.0 ), literal( 0.0 ) ), context ) );
    assert( !dda_port::evaluate( literal( std::numeric_limits<double>::infinity() ), context ) );
    assert( !dda_port::evaluate( expression{ .op = "add", .args = { literal( 1.0 ) } }, context ) );
    assert( !dda_port::evaluate( expression{ .op = "unknown" }, context ) );
}
