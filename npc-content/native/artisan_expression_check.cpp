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
    const auto opinion = expression{ .op = "npc_opinion", .name = "anger" };
    assert( !dda_port::evaluate( opinion, context ) );
    variables["@opinion:anger"] = 5;
    assert( dda_port::evaluate( binary( "greater_equal", opinion, literal( 5.0 ) ), context ) == 1 );
    variables["shared"] = 999;
    variables["@global:shared"] = 2.5;
    const auto shared = expression{ .op = "variable", .name = "shared", .global_actor = true };
    assert( dda_port::evaluate( shared, context ) == 2.5 );
    assert( dda_port::evaluate( expression{ .op = "has_var", .args = { shared } }, context ) == 1 );
    assert( dda_port::evaluate( binary( "max", literal( -3.0 ), literal( 1.0 ) ), context ) == 1 );
    assert( dda_port::evaluate( binary( "min", literal( -3.0 ), literal( 1.0 ) ), context ) == -3 );
    assert( dda_port::evaluate( expression{ .op = "clamp", .args = { literal( 300.0 ), literal( 0.0 ), literal( 200.0 ) } }, context ) == 200 );
    assert( !dda_port::evaluate( expression{ .op = "clamp", .args = { literal( 3.0 ), literal( 10.0 ), literal( 0.0 ) } }, context ) );
    const auto origin = expression{ .op = "cataclysm" };
    assert( dda_port::evaluate( origin, { .variables = variables, .cataclysm_seconds = 100 } ) == 100 );
}
