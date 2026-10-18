#pragma once

#include "civilian_chat.h"
#include "cata_utility.h"
#include "monster.h"
#include "mtype.h"
#include "output.h"
#include "rng.h"
#include "ui.h"
#include "line.h"
#include "character.h"

inline bool can_chat_with_civilian( const monster &person, const Character &speaker )
{
    return !person.is_dead() && !person.type->civilian_dialogue.empty() &&
           person.attitude_to( speaker ) != Attitude::A_HOSTILE &&
           person.bub_pos().z() == speaker.bub_pos().z() &&
           rl_dist( person.bub_pos(), speaker.bub_pos() ) <= 2 && speaker.sees( person.bub_pos() );
}

inline void show_civilian_chat( const monster &person )
{
    const auto &graph = person.type->civilian_dialogue;
    std::string current = graph.root;
    while( const auto *page = graph.find( current ) ) {
        std::string line = random_entry( page->lines ).translated();
        // A leading ampersand marks source narration, not spoken words.
        if( !line.empty() && line.front() == '&' ) {
            line.erase( line.begin() );
        }
        uilist menu;
        menu.title = person.get_name();
        menu.text = line;
        int choice = 0;
        for( const auto &response : page->responses ) {
            menu.addentry( choice++, true, -1, response.text.translated() );
        }
        menu.query();
        if( menu.ret < 0 ) {
            return;
        }
        current = graph.next( current, menu.ret );
    }
}
