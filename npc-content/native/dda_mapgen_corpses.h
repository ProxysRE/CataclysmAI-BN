#pragma once

#include "calendar.h"
#include "debug.h"
#include "item.h"
#include "mapgen/mapgen.h"
#include "mapgen/mapgen_constructor.h"
#include "mapgen/mapgendata.h"
#include "mongroup.h"
#include "rng.h"

#include <algorithm>

// Adapted from DDA jmapgen_corpse at the project's pinned source revision.
// BN groups have a default monster rather than recursive subgroup entries.
class jmapgen_corpse : public jmapgen_piece
{
    public:
        mongroup_id group;
        time_duration age;

        explicit jmapgen_corpse( const JsonObject &jsi ) :
            group( jsi.get_string( "group" ) ),
            age( time_duration::from_days( jsi.get_int( "age", 0 ) ) ) {}

        void check( const std::string &context, const mapgen_parameters & ) const override {
            if( !group.is_valid() ) {
                debugmsg( "Invalid corpse monster group %s in %s", group.str(), context );
            }
        }

        void apply( const mapgendata &dat, const jmapgen_int &x,
                    const jmapgen_int &y ) const override {
            if( !group.is_valid() ) {
                return;
            }
            auto candidates = MonsterGroupManager::GetMonstersFromGroup( group );
            // A null default means 'no monster', never a generic human corpse.
            candidates.erase( std::remove_if( candidates.begin(), candidates.end(),
            []( const mtype_id &id ) { return id.is_null() || !id.is_valid(); } ), candidates.end() );
            if( candidates.empty() ) {
                return;
            }
            dat.m.add_item_or_charges( point_omt_ms( x.get(), y.get() ),
                                      item::make_corpse( random_entry( candidates ),
                                              std::max( calendar::turn - age, calendar::start_of_cataclysm ) ) );
        }
};
