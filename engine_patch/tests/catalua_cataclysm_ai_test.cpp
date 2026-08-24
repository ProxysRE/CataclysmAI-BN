#include "catalua_impl.h"
#include "catalua_sol.h"
#include "catch/catch.hpp"

#include <string>

TEST_CASE( "cataclysm_ai_lua_binding_is_callable", "[lua][cataclysm_ai]" )
{
    auto lua = make_lua_state();
    const auto result = lua.safe_script(
                            R"(return cataclysm_ai.exchange(string.rep("x", 1048577), 1000))",
                            sol::script_pass_on_error );

    REQUIRE( result.valid() );
    CHECK( result.get<std::string>() == "CATAI_ERROR: request exceeds 1 MiB" );
}
