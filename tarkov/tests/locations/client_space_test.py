"""Geometric intersection invariants, independent of game data."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/client_data'))
from analyze_factory_space import box_triangles, transformed_triangles, plane_segments, horizontal_bins


class GeometryTests(unittest.TestCase):
    def test_cut_wall_at_arbitrary_height(self):
        t=np.array([[[0,0,0],[2,0,0],[0,2,0]]],dtype=float)
        s=plane_segments(t,1)
        self.assertEqual(s.shape,(1,2,2))
        self.assertEqual({tuple(p) for p in s[0]},{(0,0),(1,0)})

    def test_cut_through_vertex_and_edge(self):
        t=np.array([[[0,0,0],[2,-1,0],[2,1,0]],
                    [[4,0,0],[6,0,0],[6,1,0]]],dtype=float)
        s=plane_segments(t,0)
        self.assertEqual({frozenset(tuple(p) for p in seg) for seg in s},
                         {frozenset([(0,0),(2,0)]),frozenset([(4,0),(6,0)])})

    def test_coplanar_and_point_contact_are_not_walls(self):
        t=np.array([[[0,0,0],[1,0,0],[0,0,1]],
                    [[2,0,0],[3,1,0],[2,1,1]]],dtype=float)
        self.assertEqual(plane_segments(t,0).shape,(0,2,2))

    def test_box_transform_preserves_negative_nonuniform_scale(self):
        v,ids=box_triangles({'m_Center':dict(x=1,y=0,z=0),'m_Size':dict(x=2,y=4,z=6)})
        m=[[-2,0,0,10],[0,3,0,1],[0,0,1,0],[0,0,0,1]]
        tr=transformed_triangles(v,ids,m)
        np.testing.assert_allclose(tr.reshape(-1,3).min(0),[6,-5,-3])
        np.testing.assert_allclose(tr.reshape(-1,3).max(0),[10,7,3])
        self.assertEqual(len(plane_segments(tr,1)),8)

    def test_horizontal_bin_keeps_area_and_excludes_vertical_surface(self):
        t=np.array([[[0,2,0],[2,2,0],[0,2,2]],
                    [[0,0,0],[0,3,0],[0,0,3]]],dtype=float)
        self.assertEqual(horizontal_bins(t),[{'y':2.0,'triangle_area_sum':2.0}])

    def test_reversing_winding_does_not_hide_undersides(self):
        t=np.array([[[0,2,0],[2,2,0],[0,2,2]]],dtype=float)
        self.assertEqual(horizontal_bins(t),horizontal_bins(t[:,::-1]))


if __name__=='__main__':
    unittest.main()
