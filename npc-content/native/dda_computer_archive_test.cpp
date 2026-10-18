#include "catch/catch.hpp"
#include "computer.h"
#include "computer_archive.h"
#include "json.h"
#include <fstream>
#include <set>
#include <sstream>

TEST_CASE( "computer_archives_keep_cycles_exits_and_save_data", "[dda_npc][dda_terminal]" )
{
    std::istringstream input( R"({"archive_pages":[
        {"id":"a","text":"Record: 100%\nSecond line","links":[{"text":"Next","target":"b"},{"text":"Exit","target":"TALK_DONE"}]},
        {"id":"b","text":"Other record","links":[{"text":"Back","target":"a"}]}]})" );
    JsonIn parser( input );
    computer_archive records;
    records.load( parser.get_object() );
    CHECK( records.next( "a", 0 ) == "b" );
    CHECK( records.next( "b", 0 ) == "a" );
    CHECK( records.next( "a", 1 ).empty() );
    CHECK( records.next( "a", 99 ).empty() );
    CHECK( records.next( "missing", 0 ).empty() );
    computer cpu( "Archive", 2 );
    cpu.set_archive( records );
    computer_option option( "Read", COMPACT_NULL, 1 );
    option.archive_page = "a";
    cpu.add_option( option );
    std::ostringstream saved;
    JsonOut writer( saved );
    cpu.serialize( writer );
    std::istringstream restore( saved.str() );
    JsonIn reader( restore );
    computer loaded( "Empty", 0 );
    loaded.deserialize( reader );
    REQUIRE( loaded.get_archive().find( "a" ) );
    CHECK( loaded.get_archive().find( "a" )->text == "Record: 100%\nSecond line" );
    std::ostringstream again;
    JsonOut second_writer( again );
    loaded.serialize( second_writer );
    CHECK( again.str() == saved.str() );
    std::istringstream old_save( R"({"name":"Old","security":0,"options":[],"failures":[]})" );
    JsonIn old_reader( old_save );
    loaded.deserialize( old_reader );
    CHECK( loaded.get_archive().pages.empty() );
    std::istringstream old_option( R"({"name":"Old","action":"null","security":0})" );
    JsonIn option_reader( old_option );
    option.deserialize( option_reader );
    CHECK( option.archive_page.empty() );
}

TEST_CASE( "computer_archives_reject_missing_links_and_mixed_actions", "[dda_npc][dda_terminal]" )
{
    std::istringstream input( R"({"archive_pages":[{"id":"a","text":"Record","links":[{"text":"Bad","target":"missing"}]}]})" );
    JsonIn parser( input );
    computer_archive records;
    REQUIRE_THROWS( records.load( parser.get_object() ) );
    std::istringstream duplicate( R"({"archive_pages":[{"id":"a","text":"One","links":[]},{"id":"a","text":"Two","links":[]}]})" );
    JsonIn duplicates( duplicate );
    REQUIRE_THROWS( records.load( duplicates.get_object() ) );
    std::istringstream option( R"({"name":"Bad","action":"open","archive_page":"a"})" );
    JsonIn options( option );
    REQUIRE_THROWS( computer_option::from_json( options.get_object() ) );
}

TEST_CASE( "six_source_terminal_archives_survive_computer_saving", "[dda_npc][dda_terminal]" )
{
    std::ifstream file( "data/json/dda_terminal_archives.json", std::ios::binary );
    REQUIRE( file.good() );
    JsonIn reader( file );
    std::set<std::string> pages;
    int count = 0;
    for( JsonObject definition : reader.get_array() ) {
        definition.allow_omitted_members();
        auto object = definition.get_object( "object" );
        object.allow_omitted_members();
        for( JsonObject config : object.get_array( "place_computers" ) ) {
            config.allow_omitted_members();
            computer_archive archive;
            archive.load( config );
            computer cpu( "Fixture", 0 );
            cpu.set_archive( archive );
            for( JsonObject source_option : config.get_array( "options" ) ) {
                auto option = computer_option::from_json( source_option );
                REQUIRE( archive.find( option.archive_page ) );
                cpu.add_option( option );
            }
            std::ostringstream saved;
            JsonOut writer( saved );
            cpu.serialize( writer );
            std::istringstream input( saved.str() );
            JsonIn parser( input );
            computer loaded( "Empty", 0 );
            loaded.deserialize( parser );
            for( const auto &entry : archive.pages ) {
                pages.insert( entry.first );
                const auto *page = loaded.get_archive().find( entry.first );
                REQUIRE( page );
                CHECK( page->text == entry.second.text );
                REQUIRE( page->links.size() == entry.second.links.size() );
                for( size_t i = 0; i < page->links.size(); ++i ) {
                    CHECK( page->links[i].text == entry.second.links[i].text );
                    CHECK( page->links[i].target == entry.second.links[i].target );
                }
            }
            ++count;
        }
    }
    CHECK( count == 6 );
    CHECK( pages.size() == 73 );
}
