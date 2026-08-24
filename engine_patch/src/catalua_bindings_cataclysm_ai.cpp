#include "catalua_bindings.h"
#include "catalua_luna.h"
#include "catalua_luna_doc.h"
#include "path_info.h"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>

namespace
{

constexpr auto max_message_size = std::size_t{ 1024 * 1024 };

auto error_result( const std::string &message ) -> std::string { return "CATAI_ERROR: " + message; }

auto cataclysm_ai_exchange( const std::string &request, const int timeout_ms ) -> std::string
{
    if( request.size() > max_message_size ) {
        return error_result( "request exceeds 1 MiB" );
    }

    const auto timeout = std::clamp( timeout_ms, 250, 300000 );
    const auto base = PATH_INFO::config_dir();
    const auto request_path = base + "cataclysm_ai_request.txt";
    const auto request_tmp = base + "cataclysm_ai_request.tmp";
    const auto response_path = base + "cataclysm_ai_response.txt";

    std::remove( request_tmp.c_str() );
    std::remove( request_path.c_str() );
    std::remove( response_path.c_str() );

    {
        auto out = std::ofstream{ request_tmp, std::ios::binary | std::ios::trunc };
        if( !out ) {
            return error_result( "could not open request temp file" );
        }
        out.write( request.data(), static_cast<std::streamsize>( request.size() ) );
        out.close();
        if( !out ) {
            std::remove( request_tmp.c_str() );
            return error_result( "could not write request" );
        }
    }

    if( std::rename( request_tmp.c_str(), request_path.c_str() ) != 0 ) {
        std::remove( request_tmp.c_str() );
        return error_result( "could not publish request" );
    }

    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds( timeout );
    while( std::chrono::steady_clock::now() < deadline ) {
        auto in = std::ifstream{ response_path, std::ios::binary };
        if( in ) {
            auto buffer = std::ostringstream{};
            buffer << in.rdbuf();
            if( in.bad() ) {
                in.close();
                std::remove( response_path.c_str() );
                std::remove( request_path.c_str() );
                return error_result( "could not read response" );
            }

            auto response = buffer.str();
            in.close();
            std::remove( response_path.c_str() );
            std::remove( request_path.c_str() );

            if( response.size() > max_message_size ) {
                return error_result( "response exceeds 1 MiB" );
            }
            if( response.empty() ) {
                return error_result( "external process returned an empty response" );
            }
            return response;
        }
        std::this_thread::sleep_for( std::chrono::milliseconds( 50 ) );
    }

    std::remove( request_path.c_str() );
    std::remove( request_tmp.c_str() );
    return error_result( "timeout waiting for external process" );
}

} // namespace

auto cata::detail::reg_cataclysm_ai_api( sol::state &lua ) -> void
{
    DOC( "Synchronous bridge to the external Cataclysm AI sidecar process." );
    auto lib = luna::begin_lib( lua, "cataclysm_ai" );

    DOC( "Exchange one UTF-8 request with the sidecar and return its UTF-8 response or CATAI_ERROR." );
    luna::set_fx( lib, "exchange", &cataclysm_ai_exchange );

    luna::finalize_lib( lib );
}
