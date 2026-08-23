param(
    [Parameter(Mandatory=$true)]
    [string]$BnRoot
)

$ErrorActionPreference = "Stop"
$target = Join-Path $BnRoot "src\catalua_bindings.cpp"

if (-not (Test-Path $target)) {
    throw "catalua_bindings.cpp not found at $target"
}

function Convert-ToLf([string]$Value) {
    return $Value.Replace("`r`n", "`n").Replace("`r", "`n")
}

# Both the upstream C++ file and this PowerShell script are checked out with
# CRLF on GitHub's Windows runner. Canonicalize both sides of every guarded
# replacement so the patch is independent of checkout line-ending policy.
$text = Convert-ToLf ([IO.File]::ReadAllText($target))

function Replace-Once([string]$Needle, [string]$Replacement, [string]$Name) {
    $Needle = Convert-ToLf $Needle
    $Replacement = Convert-ToLf $Replacement
    $count = ([regex]::Matches($script:text, [regex]::Escape($Needle))).Count
    if ($count -ne 1) {
        throw "Patch guard '$Name' expected exactly 1 match, found $count. Upstream BN changed."
    }
    $script:text = $script:text.Replace($Needle, $Replacement)
}

Replace-Once `
'#include <cstdint>
#include <ctime>
#include <chrono>' `
'#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <chrono>
#include <fstream>
#include <sstream>
#include <thread>' `
"standard includes"

Replace-Once `
'#include "npc.h"
#include "player.h"
#include "rng.h"' `
'#include "npc.h"
#include "player.h"
#include "path_info.h"
#include "rng.h"' `
"path_info include"

$bridge = @'

static std::string cataclysm_ai_exchange_impl( const std::string &request, int timeout_ms )
{
    static constexpr std::size_t max_message_size = 1024 * 1024;
    static const std::string error_prefix = "CATAI_ERROR: ";

    if( request.size() > max_message_size ) {
        return error_prefix + "request exceeds 1 MiB";
    }

    if( timeout_ms < 250 ) {
        timeout_ms = 250;
    } else if( timeout_ms > 300000 ) {
        timeout_ms = 300000;
    }

    const std::string base = PATH_INFO::config_dir();
    const std::string request_path = base + "cataclysm_ai_request.txt";
    const std::string request_tmp = base + "cataclysm_ai_request.tmp";
    const std::string response_path = base + "cataclysm_ai_response.txt";

    std::remove( request_tmp.c_str() );
    std::remove( request_path.c_str() );
    std::remove( response_path.c_str() );

    {
        std::ofstream out( request_tmp, std::ios::binary | std::ios::trunc );
        if( !out ) {
            return error_prefix + "could not open request temp file";
        }
        out.write( request.data(), static_cast<std::streamsize>( request.size() ) );
        out.close();
        if( !out ) {
            std::remove( request_tmp.c_str() );
            return error_prefix + "could not write request";
        }
    }

    if( std::rename( request_tmp.c_str(), request_path.c_str() ) != 0 ) {
        std::remove( request_tmp.c_str() );
        return error_prefix + "could not publish request";
    }

    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::milliseconds( timeout_ms );

    while( std::chrono::steady_clock::now() < deadline ) {
        std::ifstream in( response_path, std::ios::binary );
        if( in ) {
            std::ostringstream buffer;
            buffer << in.rdbuf();
            if( in.bad() ) {
                in.close();
                std::remove( response_path.c_str() );
                std::remove( request_path.c_str() );
                return error_prefix + "could not read response";
            }

            std::string response = buffer.str();
            in.close();

            // Windows will not delete a file while an open stream still owns it.
            std::remove( response_path.c_str() );
            std::remove( request_path.c_str() );

            if( response.size() > max_message_size ) {
                return error_prefix + "response exceeds 1 MiB";
            }
            if( response.empty() ) {
                return error_prefix + "external process returned an empty response";
            }
            return response;
        }
        std::this_thread::sleep_for( std::chrono::milliseconds( 50 ) );
    }

    std::remove( request_path.c_str() );
    std::remove( request_tmp.c_str() );
    return error_prefix + "timeout waiting for external process";
}

static void reg_cataclysm_ai_api( sol::state &lua )
{
    DOC( "Narrow synchronous bridge to the external Cataclysm AI sidecar." );
    luna::userlib lib = luna::begin_lib( lua, "cataclysm_ai" );
    luna::set_fx( lib, "exchange",
    []( const std::string & request, int timeout_ms ) {
        return cataclysm_ai_exchange_impl( request, timeout_ms );
    } );
    luna::finalize_lib( lib );
}
'@

# Insert at a unique, stable function boundary instead of depending on the
# formatting of the preceding debug binding block.
Replace-Once `
'static tm *local_time_impl()' `
((Convert-ToLf $bridge).TrimEnd("`n") + "`n`nstatic tm *local_time_impl()") `
"bridge insertion"

Replace-Once `
'    reg_debug_api( lua );
    reg_game_api( lua );' `
'    reg_debug_api( lua );
    reg_cataclysm_ai_api( lua );
    reg_game_api( lua );' `
"bridge registration"

[IO.File]::WriteAllText($target, $text, (New-Object Text.UTF8Encoding($false)))
Write-Host "Cataclysm AI bridge applied to $target"
