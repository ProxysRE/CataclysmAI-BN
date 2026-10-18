#pragma once

#include "json.h"
#include "translations.h"
#include <map>
#include <string>
#include <utility>
#include <vector>

// A deliberately read-only dialogue graph for non-NPC people.
// Effects, trading and follower orders continue to require real NPC dialogue.
struct civilian_chat_response {
    translation text;
    std::string target;
};
struct civilian_chat_page {
    std::vector<translation> lines;
    std::vector<civilian_chat_response> responses;
};
class civilian_chat
{
    public:
        std::string root;
        std::map<std::string, civilian_chat_page> pages;
        static bool is_exit( const std::string &id ) {
            return id.empty() || id == "TALK_DONE" || id == "TALK_NONE";
        }
        const civilian_chat_page *find( const std::string &id ) const {
            const auto it = pages.find( id );
            return it == pages.end() ? nullptr : &it->second;
        }
        bool empty() const {
            return root.empty();
        }
        std::string next( const std::string &id, size_t choice ) const {
            const auto *page = find( id );
            if( !page || choice >= page->responses.size() ) {
                return {};
            }
            const auto &target = page->responses[choice].target;
            return !is_exit( target ) && find( target ) ? target : std::string();
        }
        void load( const JsonObject &jo ) {
            root = jo.get_string( "root" );
            pages.clear();
            for( JsonObject source : jo.get_array( "pages" ) ) {
                const std::string id = source.get_string( "id" );
                if( is_exit( id ) || pages.count( id ) ) {
                    source.throw_error( "Invalid or duplicate civilian dialogue page", "id" );
                }
                civilian_chat_page page;
                source.read( "lines", page.lines );
                if( page.lines.empty() ) {
                    source.throw_error( "Civilian dialogue requires a line", "lines" );
                }
                for( JsonObject response : source.get_array( "responses" ) ) {
                    civilian_chat_response entry;
                    response.read( "text", entry.text );
                    entry.target = response.get_string( "target" );
                    page.responses.push_back( std::move( entry ) );
                }
                if( page.responses.empty() ) {
                    source.throw_error( "Civilian dialogue requires a response", "responses" );
                }
                pages.emplace( id, std::move( page ) );
            }
            if( !find( root ) ) {
                jo.throw_error( "Unknown civilian dialogue root", "root" );
            }
            for( const auto &entry : pages ) {
                for( const auto &response : entry.second.responses ) {
                    if( !is_exit( response.target ) && !find( response.target ) ) {
                        jo.throw_error( "Unknown civilian dialogue response target", "pages" );
                    }
                }
            }
        }
};
