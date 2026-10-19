#!/usr/bin/env python3
"""Reject partial whole-yard transfers, lost cargo outcomes and native mislabeling."""
import json
from prepare_container_yards import FOLDER, ROOT, candidate, sources, prepare

prepare(check=True)
payload=candidate()
report=json.loads((FOLDER/'TRANSFER_REPORT.json').read_text())
assert report['native_embedded'] is False and report['runtime_validated'] is False
assert len([e for e in payload if e['type']=='mapgen'])==155
assert report['nested_layout_count']==121 and report['cargo_choice_count']==119
assert len(report['specials'])==2
assert all(e['placed_cells']==51 and e['levels']==[0,1,2] for e in report['specials'])
assert not report['core_id_overlaps'] and not report['bundled_mod_id_overlaps']
palette=next(e for es in sources().values() for e in es if e['type']=='palette')
cargo=palette['parameters']['contents_nest']
for e in payload:
    if e['type']=='mapgen' and 'contents_nest' in e['object'].get('parameters',{}):
        assert e['object']['parameters']['contents_nest']==cargo
assert cargo['scope']=='nest'
weights=dict(cargo['default']['distribution'])
assert weights['shipping_container_banknotes_1x1']==1
assert weights['null']==20 and weights['shipping_container_food_1x1']==10
assert 'shipping_container_banknotes_1x1' in report['nested_layouts']
# No playable installation claim until the recorded dependencies are closed.
assert report['unresolved_count']==len(report['unresolved_typed_references'])>0
assert 'dda_container_yard' not in (ROOT/'artisan_engine.patch').read_text()
print('PASS: two whole three-level yards / 102 placements, complete cargo weights and nested selection scope; staging only')
