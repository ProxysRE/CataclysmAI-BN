#!/usr/bin/env python3
"""Compose DDA corpse placement with BN's mapgen constructor and item ownership."""
import argparse
import difflib
from pathlib import Path
from prepare_karting import sources

ROOT = Path(__file__).resolve().parent
CORE = ('mapgen/mapgen.cpp',)


def replacement():
    text = sources()['bn/src/mapgen/mapgen.cpp']
    for old, new in (
        ('#include "debug.h"', '#include "debug.h"\n#include "dda_mapgen_corpses.h"'),
        ('    new_pal.load_place_mapings<jmapgen_item_group>(jo, "items", format_placings);',
         '    new_pal.load_place_mapings<jmapgen_corpse>(jo, "corpses", format_placings);\n'
         '    new_pal.load_place_mapings<jmapgen_item_group>(jo, "items", format_placings);'),
        ('    objects.load_objects<jmapgen_loot>(jo, "place_loot");',
         '    objects.load_objects<jmapgen_loot>(jo, "place_loot");\n'
         '    objects.load_objects<jmapgen_corpse>(jo, "place_corpses");'),
    ):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    from prepare_terminal_archives import extend_mapgen
    return extend_mapgen(text)


def patch_sections():
    path = 'src/mapgen/mapgen.cpp'
    return ''.join(difflib.unified_diff(sources()['bn/' + path].splitlines(keepends=True),
                   replacement().splitlines(keepends=True), 'a/' + path, 'b/' + path))


def prepare(bn_source=None):
    if bn_source:
        assert (bn_source / 'src/mapgen/mapgen.cpp').read_text(encoding='utf-8') == sources()['bn/src/mapgen/mapgen.cpp']
    assert patch_sections().count('+++ b/src/mapgen/mapgen.cpp\n') == 1
    print('PASS: corpse action and palette mapping compose against pinned BN mapgen')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bn-source', type=Path)
    prepare(parser.parse_args().bn_source)
