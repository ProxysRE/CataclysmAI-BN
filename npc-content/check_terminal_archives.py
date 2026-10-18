#!/usr/bin/env python3
"""Check exact source stories, graph closure and native archive integration."""
from prepare_terminal_archives import prepare, stories, native_data, replacements, MISSING

topics, terminals = stories()
payload = native_data()
all_pages = {}
for config, entry in zip(terminals, payload):
    target, = entry['object']['place_computers']
    pages = {p['id']: p for p in target['archive_pages']}
    assert target['options'][0]['archive_page'] == config['chat_topics'][0]
    assert set(target) == {'x', 'y', 'name', 'options', 'archive_pages'}
    for key, page in pages.items():
        if key != MISSING:
            assert page['text'] == topics[key]['dynamic_line']
            assert page['links'] == [{'text': r['text'], 'target': r['topic']} for r in topics[key]['responses']]
        else:
            assert page['text'] == 'ERROR: File unavailable.'
        assert all(r['target'] in pages or r['target'] in ('TALK_DONE', 'TALK_NONE') for r in page['links'])
        if key in all_pages:
            assert all_pages[key] == page
        all_pages[key] = page
assert set(all_pages) == set(topics) | {MISSING}
assert sorted(len(e['object']['place_computers'][0]['archive_pages']) for e in payload) == [6, 7, 10, 14, 17, 19]
patched = replacements()
assert patched['src/computer_session.cpp'].count('activate_option( current );') == 2
assert 'activate_function( option.action );' in patched['src/computer_session.cpp']
assert 'foldstring(' in patched['src/computer_session.cpp']
assert 'archive = {};\n        jo.read( "archive", archive );' in patched['src/computer.cpp']
prepare(check=True)
print('PASS: 72 unchanged source pages, closed graphs, six roots, safe legacy dispatch and save handling')
