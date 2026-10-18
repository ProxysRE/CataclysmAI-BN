#pragma once

#include "json.h"
#include <map>
#include <string>
#include <utility>
#include <vector>

struct computer_archive_link {
    std::string text;
    std::string target;
};
struct computer_archive_page {
    std::string id;
    std::string text;
    std::vector<computer_archive_link> links;
};

// Read-only records use BN's computer security and menus. No dialogue effects.
class computer_archive
{
    public:
        std::map<std::string, computer_archive_page> pages;
        static bool is_exit( const std::string &id ) {
            return id.empty() || id == "TALK_DONE" || id == "TALK_NONE";
        }
        const computer_archive_page *find( const std::string &id ) const {
            const auto it = pages.find( id );
            return it == pages.end() ? nullptr : &it->second;
        }
        std::string next( const std::string &id, size_t choice ) const {
            const auto *page = find( id );
            if( !page || choice >= page->links.size() ) {
                return {};
            }
            const auto &target = page->links[choice].target;
            return !is_exit( target ) && find( target ) ? target : std::string();
        }
        void load( const JsonObject &jo ) {
            pages.clear();
            if( !jo.has_array( "archive_pages" ) ) {
                return;
            }
            for( JsonObject source : jo.get_array( "archive_pages" ) ) {
                computer_archive_page page;
                page.id = source.get_string( "id" );
                page.text = source.get_string( "text" );
                if( is_exit( page.id ) || pages.count( page.id ) ) {
                    source.throw_error( "Invalid or duplicate archive page", "id" );
                }
                for( JsonObject link : source.get_array( "links" ) ) {
                    page.links.push_back( { link.get_string( "text" ), link.get_string( "target" ) } );
                }
                const auto id = page.id;
                pages.emplace( id, std::move( page ) );
            }
            for( const auto &entry : pages ) {
                for( const auto &link : entry.second.links ) {
                    if( !is_exit( link.target ) && !find( link.target ) ) {
                        jo.throw_error( "Unresolved archive link", "archive_pages" );
                    }
                }
            }
        }
        void serialize( JsonOut &out ) const {
            out.start_object();
            out.member( "archive_pages" );
            out.start_array();
            for( const auto &entry : pages ) {
                const auto &page = entry.second;
                out.start_object();
                out.member( "id", page.id );
                out.member( "text", page.text );
                out.member( "links" );
                out.start_array();
                for( const auto &link : page.links ) {
                    out.start_object();
                    out.member( "text", link.text );
                    out.member( "target", link.target );
                    out.end_object();
                }
                out.end_array();
                out.end_object();
            }
            out.end_array();
            out.end_object();
        }
        void deserialize( JsonIn &in ) {
            load( in.get_object() );
        }
};
