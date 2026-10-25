"""Reject unjustified volume expansion and walking on air; no BN runtime."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/locations'))
from factory_volumes import air_candidates
from check_factory_stack import graph


class Volumes(unittest.TestCase):
    def setUp(self):
        self.blueprints={'source_sha256':'test','svg_units_per_cell':1,
                         'floors':[{'z':z,'rows':['.'*7 if z==0 else ' '*7 for _ in range(7)]}
                                   for z in [-1,0,1,2]]}
        self.rules={'source_sha256':'test','svg_units_per_cell':1,'target_z':[1,2],
                    'guard_cells':2,'zones':[{'id':'test','svg_bounds':[1,1,6,6]}]}

    def change(self,z,x,y,c):
        floor=next(f for f in self.blueprints['floors'] if f['z']==z)
        row=list(floor['rows'][y]);row[x]=c;floor['rows'][y]=''.join(row)

    def test_only_upper_unknown_cells_with_explicit_ground_floor(self):
        self.change(0,3,3,' ')
        result=air_candidates(self.blueprints,self.rules)
        self.assertTrue(result)
        self.assertEqual({z for x,y,z in result},{1,2})
        self.assertNotIn((3,3,1),result)
        self.assertNotIn((3,3,2),result)
        self.assertTrue(all(1<=x<6 and 1<=y<6 for x,y,z in result))

    def test_drawn_upper_floor_wall_obstacle_or_stair_cannot_be_removed(self):
        for c in '.#XS':
            with self.subTest(symbol=c):
                self.setUp();self.change(1,3,3,c)
                self.assertNotIn((3,3,1),air_candidates(self.blueprints,self.rules))

    def test_two_cell_guard_protects_equipment_and_flight_approaches(self):
        for z,c in [(0,'#'),(0,'X'),(0,'S'),(1,'S'),(2,'S')]:
            with self.subTest(z=z,symbol=c):
                self.setUp();self.change(z,3,3,c)
                result=air_candidates(self.blueprints,self.rules)
                self.assertFalse(any(abs(x-3)<=2 and abs(y-3)<=2 for x,y,z in result))

    def test_fractional_zone_uses_cell_centers_not_rounded_envelope(self):
        self.rules['zones'][0]['svg_bounds']=[1.4,1.4,5.4,5.4]
        result=air_candidates(self.blueprints,self.rules)
        self.assertIn((1,1,1),result)
        self.assertNotIn((5,5,1),result)

    def test_wrong_source_scale_level_or_guard_is_rejected(self):
        for key,value in [('source_sha256','other'),('svg_units_per_cell',.5),('target_z',[0,1]),('guard_cells',0)]:
            with self.subTest(key=key):
                rules=deepcopy(self.rules);rules[key]=value
                with self.assertRaises(ValueError):air_candidates(self.blueprints,rules)

    def test_misaligned_floor_extents_are_rejected(self):
        self.blueprints['floors'][0]['rows'][0]=' '
        with self.assertRaises(ValueError):air_candidates(self.blueprints,self.rules)

    def test_out_of_bounds_zone_is_rejected(self):
        self.rules['zones'][0]['svg_bounds']=[-1,0,5,5]
        with self.assertRaises(ValueError):air_candidates(self.blueprints,self.rules)

    def test_positive_move_cost_does_not_make_air_a_standing_route(self):
        # A one-cell gap between floors: engine air costs movement, but has NO_FLOOR.
        standing_costs={'.':2,'~':0}
        result=graph({0:['.~.']},standing_costs)
        self.assertEqual(result['component_sizes'],[1,1])


if __name__=='__main__':unittest.main()
