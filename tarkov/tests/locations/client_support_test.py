"""Geometric support, solid containment and swept-motion regression fixtures."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/client_data'))
from analyze_factory_space import box_triangles, transformed_triangles
from probe_factory_supports import (SceneGeometry,closed_mesh,convex_faces,ray_hits,
                                    triangle_box_overlap,support_probe,segment_supported,attach_sources)


def box(centre,size):
    v,ids=box_triangles({'m_Center':dict(zip('xyz',centre)),'m_Size':dict(zip('xyz',size))})
    return v[ids]


def floor(y=0):
    return np.array([[[0,y,0],[0,y,2],[2,y,2]],[[0,y,0],[2,y,2],[2,y,0]]],float)


def geometry(parts,closed=None,scenes=None):
    return SceneGeometry(np.concatenate(parts),np.concatenate([np.full(len(t),i) for i,t in enumerate(parts)]),
                         np.array(closed or [False]*len(parts)),np.array(scenes or ['region']*len(parts)),
                         np.array([[-2,-2],[4,4]]))


class SupportTests(unittest.TestCase):
    def test_sat_rejects_empty_corner_of_overlapping_bounding_boxes(self):
        t=np.array([[[2,0,0],[0,2,0],[2,2,0]]],float)
        self.assertEqual(len(triangle_box_overlap(t,[0,0,0],[.5,.5,.5])),0)
        self.assertEqual(len(triangle_box_overlap(t,[1,1,0],[.5,.5,.5])),1)

    def test_upward_support_and_lower_side_are_distinct(self):
        g=geometry([floor()])
        self.assertEqual(g.supports(.5,.5),[(0.0,0)])
        reverse=geometry([floor()[:,::-1]])
        self.assertEqual(reverse.supports(.5,.5),[])

    def test_vertical_ray_dedup_does_not_count_shared_triangle_edge_twice(self):
        g=geometry([box([1,1,1],[2,2,2])],[True])
        self.assertFalse(g.clear_box([1,1,1],[.1,.1,.1]))
        self.assertTrue(g.clear_box([1,3,1],[.1,.1,.1]))

    def test_welded_closed_topology_and_convex_face_orientation(self):
        tr=box([0,0,0],[2,2,2]);v=tr.reshape(-1,3);ids=np.arange(len(v)).reshape(-1,3)
        self.assertTrue(closed_mesh(v,ids))
        self.assertFalse(closed_mesh(v,ids[:-1]))
        hull=convex_faces(np.unique(v,axis=0));pts=np.unique(v,axis=0)[hull]
        volume=np.einsum('ij,ij->i',pts[:,0],np.cross(pts[:,1],pts[:,2])).sum()/6
        self.assertAlmostEqual(volume,8)

    def test_low_ceiling_rejects_standing(self):
        g=geometry([floor(),floor(1.5)[:,::-1]])
        p=support_probe(g,'region',np.array([[.5,.5],[1.5,1.5]]))
        self.assertEqual(len(p['nodes']),0)
        self.assertGreater(p['rejected']['body_intersection_or_inside_closed_obstacle'],0)

    def test_swept_body_catches_thin_wall_between_clear_endpoints(self):
        g=geometry([floor(),box([1,1,1],[.02,2,2])],[False,True],['region','wall'])
        p=support_probe(g,'region',np.array([[0,0],[2,1]]),pitch=1,radius=.2)
        self.assertEqual(len(p['nodes']),2)
        self.assertEqual(p['edges'],[])

    def test_bounded_step_path_connects_small_step_but_not_large_step(self):
        for rise,expected in [(.2,1),(.6,0)]:
            g=geometry([box([.5,-.1,.5],[1,.2,1]),box([1.5,rise-.1,.5],[1,.2,1])],[True,True])
            p=support_probe(g,'region',np.array([[0,0],[2,1]]),pitch=1,radius=.2)
            self.assertEqual(len(p['nodes']),2)
            self.assertEqual(len(p['edges']),expected)

    def test_other_scene_can_supply_adjoining_support(self):
        left=box([.5,-.1,.5],[1,.2,1]);right=box([1.5,-.1,.5],[1,.2,1])
        g=geometry([left,right],[True,True],['region','adjoining'])
        frame=np.array([[0,0],[2,1]])
        self.assertEqual(len(support_probe(g,'region',frame,pitch=1,radius=.2)['nodes']),1)
        p=support_probe(g,'region',frame,pitch=1,radius=.2,all_sources=True)
        self.assertEqual(len(p['nodes']),2)
        self.assertEqual(len(p['edges']),1)

    def test_continuous_foot_trace_does_not_bridge_a_floor_gap(self):
        left=floor();left[:,:,0]*=.45
        right=floor();right[:,:,0]=1.1+right[:,:,0]*.45
        gap=np.concatenate([left,right])
        self.assertFalse(segment_supported(gap,[.5,0,1],[1.5,0,1]))
        self.assertTrue(segment_supported(floor(),[.5,0,1],[1.5,0,1]))
        g=geometry([gap])
        p=support_probe(g,'region',np.array([[0,0],[2,1]]),pitch=1,radius=.2)
        self.assertEqual(len(p['nodes']),2)
        self.assertEqual(len(p['edges']),0)

    def test_proxy_shapes_cannot_seed_supports(self):
        g=geometry([floor()]);g.supportable[:]=False
        self.assertEqual(g.supports(.5,.5),[])

    def test_coincident_support_retains_both_sources_and_prefers_region(self):
        g=geometry([floor(),floor()],scenes=['shared','region'])
        metadata=[{'scene':'shared','component_path_id':'1'},{'scene':'region','component_path_id':'2'}]
        p={'nodes':[{'x':.5,'y':0,'z':.5,'source_triangle':0}]}
        attach_sources(p,g,metadata,'region')
        self.assertEqual(p['nodes'][0]['source']['component_path_id'],'2')
        self.assertEqual(len(p['nodes'][0]['coincident_sources']),2)


if __name__=='__main__':
    unittest.main()
