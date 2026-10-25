"""Construction-plan invariants; these tests do not generate BN or prove stairs."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/locations'))
import plan_factory_vertical as planner


class VerticalPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprints = json.loads((planner.OUT/'floor_blueprints.json').read_text())
        cls.source = json.loads((planner.OUT/'vertical_reference.json').read_text())
        cls.result = planner.plan(cls.blueprints['floors'],cls.source)

    def test_all_floors_share_ground_registration(self):
        ground = json.loads((planner.OUT/'ground_geometry.json').read_text())
        self.assertEqual(self.blueprints['source_sha256'],planner.SOURCE_DIGEST)
        self.assertEqual([g['z'] for g in self.blueprints['floors']],[-1,0,1,2])
        for g in self.blueprints['floors']:
            self.assertEqual(g['size'],ground['size'])
            self.assertEqual(len(g['rows']),288)
            self.assertTrue(all(len(r)==264 for r in g['rows']))
        self.assertEqual(self.blueprints['floors'][1]['rows'],ground['rows'])

    def test_supported_pairs_are_shared_stair_cells_inside_source_bounds(self):
        grids = {g['z']:g['rows'] for g in self.blueprints['floors']}
        endpoints = set()
        self.assertEqual(len(self.result['direction_supported_candidates']),34)
        for record in self.result['direction_supported_candidates']:
            self.assertEqual(record['status'],'direction_supported_candidate')
            x,y = record['proposed_position']
            self.assertEqual(record['to_z'],record['from_z']+1)
            sx,sy,w,h = record['svg_bbox']
            self.assertTrue(sx <= (x+.5)*planner.CELL < sx+w)
            self.assertTrue(sy <= (y+.5)*planner.CELL < sy+h)
            for z in [record['from_z'],record['to_z']]:
                self.assertEqual(grids[z][y][x],'S')
                self.assertNotIn((z,x,y),endpoints)
                endpoints.add((z,x,y))
            self.assertFalse(record['runtime_enabled'])

    def test_bidirectional_repeated_symbol_is_one_landing_per_level(self):
        relations = [r for r in self.result['direction_supported_candidates'] if r['source_ref']=='stair-140']
        self.assertEqual([(r['from_z'],r['to_z']) for r in relations],[(-1,0),(0,1)])
        self.assertNotEqual(relations[0]['proposed_position'],relations[1]['proposed_position'])
        self.assertFalse(any(r['source_ref']=='stair-140' for r in self.result['direction_ambiguous']))

    def test_missing_intermediate_floor_never_becomes_a_shortcut(self):
        missing = self.result['missing_intermediate_landings']
        self.assertEqual([(r['source_ref'],r['from_z'],r['to_z']) for r in missing],[('stair-134',-1,1)])
        self.assertFalse(any(r['source_ref']=='stair-134' for r in self.result['direction_supported_candidates']))

    def test_ambiguous_direction_stays_out_of_supported_graph(self):
        self.assertEqual(len(self.result['direction_ambiguous']),10)
        ambiguous = {(r['source_ref'],r['from_z'],r['to_z']) for r in self.result['direction_ambiguous']}
        supported = {(r['source_ref'],r['from_z'],r['to_z']) for r in self.result['direction_supported_candidates']}
        self.assertFalse(ambiguous & supported)
        self.assertIn(('stair-127',0,1),ambiguous)
        self.assertIn(('stair-128',0,1),ambiguous)

    def test_wall_or_unknown_never_becomes_a_stair_endpoint(self):
        lower = ['SS','SS']
        for upper in [['XX','XX'],['  ','  '],['..','..']]:
            self.assertEqual(planner.shared_cells(lower,upper,[0,0,1,1]),[])

    def test_stair_cells_outside_exact_bbox_are_rejected(self):
        self.assertEqual(planner.shared_cells(['SS'],['SS'],[0,0,.2,.5]),[])
        self.assertEqual(planner.shared_cells(['SS'],['SS'],[0,0,.5,.5]),[(0,0)])

    def test_floating_stair_symbols_are_flagged_for_flight_review(self):
        flagged = [r for r in self.result['direction_supported_candidates']
                   if r['requires_intermediate_flight_review']]
        self.assertEqual(len(flagged),7)
        self.assertIn('stair-135',[r['source_ref'] for r in flagged])
        self.assertTrue(all(not r['runtime_enabled'] for r in flagged))

    def test_stored_plan_matches_recalculation(self):
        committed = json.loads((planner.OUT/'vertical_plan.json').read_text())
        self.assertEqual(committed,self.result)


if __name__=='__main__':
    unittest.main()
