#!/usr/bin/env python3
"""Adapt pure DDA terminal story graphs to BN computer menus and save data."""
import argparse
import base64
import copy
import difflib
import gzip
import hashlib
import json
from pathlib import Path
from prepare_regional_locations import build, index_entries, BUILTIN_IDS
from export_bn_ids import read_cache

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / 'terminal_archives'
CORE = ('computer.h', 'computer.cpp', 'computer_session.h', 'computer_session.cpp')
PAYLOAD = 'data/json/dda_terminal_archives.json'
BN_PIN = 'c621aaf42fa182473aad10feea2b55647704dcf1'
MISSING = 'COMP_NURSING_HOME_LEGAL'


def sources():
    manifest = json.loads((FOLDER / 'SOURCE_MANIFEST.json').read_text())
    assert manifest['bn_pin'] == BN_PIN
    raw = gzip.decompress(base64.b64decode((FOLDER / 'SOURCE.part00').read_text(), validate=True))
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    files = json.loads(raw)
    assert set(files) == set(manifest['files'])
    for path, text in files.items():
        assert hashlib.sha256(text.encode()).hexdigest() == manifest['files'][path]
    return files


def stories():
    sites = build()
    entries = [e for name in ('nursing_home', 'retirement_community') for e in sites[name + '.json']]
    topics = {e['id']: e for e in entries if e['type'] == 'talk_topic'}
    eocs = {e['id']: e for e in entries if e['type'] == 'effect_on_condition'}
    terminals = [c for e in entries for c in e.get('object', {}).get('place_computers', []) if 'chat_topics' in c]
    assert len(topics) == 72 and len(terminals) == 6
    for e in topics.values():
        assert set(e) == {'type', 'id', 'dynamic_line', 'responses'}
        assert isinstance(e['dynamic_line'], str)
        assert all(set(r) == {'text', 'topic'} for r in e['responses'])
    for c in terminals:
        assert len(c['eocs']) == len(c['chat_topics']) == 1
        assert eocs[c['eocs'][0]]['effect'] == ['open_dialogue']
    return topics, terminals


def convert_terminal(config):
    topics, _ = stories()
    result = copy.deepcopy(config)
    root, = result.pop('chat_topics')
    result.pop('eocs')
    pending, pages = [root], {}
    while pending:
        key = pending.pop()
        if key in ('TALK_DONE', 'TALK_NONE') or key in pages:
            continue
        if key not in topics:
            assert key == MISSING, key
            page = {'id': key, 'text': 'ERROR: File unavailable.',
                    'links': [{'text': 'Log off', 'target': 'TALK_DONE'}]}
        else:
            topic = topics[key]
            page = {'id': key, 'text': topic['dynamic_line'],
                    'links': [{'text': r['text'], 'target': r['topic']} for r in topic['responses']]}
        pages[key] = page
        pending.extend(r['target'] for r in page['links'])
    result['options'] = [{'name': 'Access archived records', 'action': 'null', 'archive_page': root}]
    result['archive_pages'] = [pages[k] for k in sorted(pages)]
    return result


def adapt_map(entry):
    result = copy.deepcopy(entry)
    obj = result.get('object', {})
    if 'place_computers' in obj:
        obj['place_computers'] = [convert_terminal(c) if 'chat_topics' in c else c for c in obj['place_computers']]
    return result


def native_data():
    _, terminals = stories()
    return [{'type': 'mapgen', 'nested_mapgen_id': 'dda_archive_' + c['chat_topics'][0].lower(),
             'method': 'json', 'object': {'mapgensize': [1, 1], 'place_computers': [convert_terminal(c)]}} for c in terminals]


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def replacements():
    files = sources()
    h = files['src/computer.h']
    h = replace(h, '#include "calendar.h"', '#include "calendar.h"\n#include "computer_archive.h"')
    h = replace(h, '    int security;\n\n    computer_option();', '    int security;\n    std::string archive_page;\n\n    computer_option();')
    h = replace(h, '        // Save/load', '''        void set_archive( const computer_archive &records ) { archive = records; }
        const computer_archive &get_archive() const { return archive; }
        // Save/load''')
    h = replace(h, '        std::vector<computer_option> options;', '        std::vector<computer_option> options;\n        computer_archive archive;')
    cpp = files['src/computer.cpp']
    cpp = replace(cpp, '    jout.member( "security", security );\n    jout.end_object();', '    jout.member( "security", security );\n    jout.member( "archive_page", archive_page );\n    jout.end_object();')
    cpp = replace(cpp, '    security = jo.get_int( "security" );', '    security = jo.get_int( "security" );\n    archive_page = jo.get_string( "archive_page", "" );')
    cpp = replace(cpp, '    options.clear();', '    options.clear();\n    archive = {};')
    cpp = replace(cpp, '    jout.member( "options", options );', '    jout.member( "options", options );\n    jout.member( "archive", archive );')
    cpp = replace(cpp, '        jo.read( "options", options );', '        jo.read( "options", options );\n        archive = {};\n        jo.read( "archive", archive );')
    cpp = replace(cpp, '    return computer_option( name.translated(), action, sec );', '''    computer_option result( name.translated(), action, sec );
    result.archive_page = jo.get_string( "archive_page", "" );
    if( !result.archive_page.empty() && action != COMPACT_NULL ) {
        jo.throw_error( "Archive options cannot execute other actions", "archive_page" );
    }
    return result;''')
    sh = replace(files['src/computer_session.h'], '        void activate_function( computer_action action );', '''        void activate_function( computer_action action );
        void activate_option( const computer_option &option );
        void show_archive( std::string page_id );''')
    session = files['src/computer_session.cpp']
    assert session.count('activate_function( current.action );') == 2
    session = session.replace('activate_function( current.action );', 'activate_option( current );')
    session = replace(session, 'void computer_session::activate_function( computer_action action )', '''void computer_session::activate_option( const computer_option &option )
{
    if( option.archive_page.empty() ) {
        activate_function( option.action );
    } else {
        show_archive( option.archive_page );
    }
}

void computer_session::show_archive( std::string page_id )
{
    size_t offset = 0;
    while( const auto *page = comp.archive.find( page_id ) ) {
        const auto folded = foldstring( _( page->text ), std::max( 10, TERMX - 8 ) );
        const size_t visible = std::max( 3, TERMY - static_cast<int>( page->links.size() ) - 12 );
        if( offset >= folded.size() ) { offset = 0; }
        std::string excerpt;
        for( size_t i = offset; i < folded.size() && i < offset + visible; ++i ) {
            excerpt += folded[i] + "\\n";
        }
        uilist menu;
        menu.text = excerpt;
        const int count = static_cast<int>( page->links.size() );
        for( int i = 0; i < count; ++i ) {
            menu.addentry( i, true, -1, _( page->links[i].text ) );
        }
        if( offset > 0 ) { menu.addentry( count, true, -1, _( "Previous page" ) ); }
        if( offset + visible < folded.size() ) { menu.addentry( count + 1, true, -1, _( "Next page" ) ); }
        menu.addentry( count + 2, true, -1, _( "Close archive" ) );
        menu.query();
        if( menu.ret < 0 || menu.ret == count + 2 ) { return; }
        if( menu.ret == count ) { offset = offset > visible ? offset - visible : 0; }
        else if( menu.ret == count + 1 ) { offset += visible; }
        else { page_id = comp.archive.next( page_id, menu.ret ); offset = 0; }
    }
}

void computer_session::activate_function( computer_action action )''')
    return {'src/computer.h': h, 'src/computer.cpp': cpp, 'src/computer_session.h': sh, 'src/computer_session.cpp': session}


def extend_mapgen(text):
    start = text.index('class jmapgen_computer:')
    end = text.index('class jmapgen_sealed_item:', start)
    part = text[start:end]
    part = replace(part, '    bool target;', '    bool target;\n    computer_archive archive;')
    part = replace(part, '        target = jsi.get_bool("target", false);', '        target = jsi.get_bool("target", false);\n        archive.load(jsi);')
    part = replace(part, '                options.emplace_back(computer_option::from_json(jo));', '''                options.emplace_back(computer_option::from_json(jo));
                if (!options.back().archive_page.empty() && !archive.find(options.back().archive_page)) {
                    jo.throw_error("Unknown archive root", "archive_page");
                }''')
    part = replace(part, '        for (const auto& opt : options)', '        cpu->set_archive(archive);\n        for (const auto& opt : options)')
    return text[:start] + part + text[end:]


def patch_sections():
    return ''.join(''.join(difflib.unified_diff(sources()[path].splitlines(keepends=True), text.splitlines(keepends=True), 'a/' + path, 'b/' + path)) for path, text in replacements().items())


def prepare(check=False, bn_source=None):
    if bn_source:
        for path, text in sources().items():
            assert (bn_source / path).read_text(encoding='utf-8') == text, path
    payload = native_data()
    bn = set(map(tuple, read_cache(ROOT / 'dependency_catalog/BN_ID_INDEX.json')['identifiers']))
    assert not (index_entries(payload) - BUILTIN_IDS) & bn
    path = ROOT / 'native/dda_terminal_archives.json'
    text = json.dumps(payload, ensure_ascii=True, indent=2) + '\n'
    if check:
        assert path.read_text() == text
    else:
        path.write_text(text)
    patch_sections()
    print('PASS: six read-only terminal archives; 72 source pages and one unavailable-file notice')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--bn-source', type=Path)
    a = p.parse_args()
    prepare(a.check, a.bn_source)
