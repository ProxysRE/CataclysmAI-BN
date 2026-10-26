"""Geometric invariants for the client audit; no client files required."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE = Path(__file__).resolve().parents[2] / 'tools/client_data/audit_factory_scenes.py'
SPEC = importlib.util.spec_from_file_location('scene_audit', MODULE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def transform(go, parent=0, position=(0,0,0), scale=(1,1,1), rotation=(0,0,0,1)):
    return {'m_GameObject':{'m_FileID':0,'m_PathID':go},
            'm_Father':{'m_FileID':0,'m_PathID':parent},
            'm_LocalPosition':dict(zip('xyz',position)),
            'm_LocalScale':dict(zip('xyz',scale)),
            'm_LocalRotation':dict(zip('xyzw',rotation))}


class TransformTests(unittest.TestCase):
    def test_dependency_archives_reject_duplicate_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/'a.zip', Path(directory)/'b.zip'
            with zipfile.ZipFile(a,'w') as z:
                z.writestr('level528',b'scene')
            with zipfile.ZipFile(b,'w') as z:
                z.writestr('sharedassets5.assets',b'meshes')
            self.assertEqual([n for n,_ in audit.selected_files([a,b])],
                             ['level528','sharedassets5.assets'])
            with self.assertRaisesRegex(ValueError,'Duplicate selected file'):
                list(audit.selected_files([a,a]))

    def test_selected_file_names_cannot_escape_flat_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory)/'a.zip'
            with zipfile.ZipFile(a,'w') as z:
                z.writestr('../level528',b'scene')
            with self.assertRaisesRegex(ValueError,'Expected flat ZIP'):
                list(audit.selected_files([a]))

    def test_parent_rotation_scale_and_translation(self):
        # Parent turns local +X into world -Z, with a two-unit X scale.
        s = math.sqrt(0.5)
        ts = {10:transform(1,position=(10,2,20),scale=(2,3,4),rotation=(0,s,0,s)),
              20:transform(2,parent=10,position=(1,1,0))}
        world = audit.hierarchy(ts,{1:{'m_IsActive':True},2:{'m_IsActive':True}})
        for got, expected in zip(audit.transform_point(world[20][0],[0,0,0]),[10,5,18]):
            self.assertAlmostEqual(got,expected)

    def test_nonuniform_parent_preserves_child_rotated_axes(self):
        # Do not decompose matrices into a guessed world rotation and scale.
        s = math.sqrt(0.5)
        ts = {10:transform(1,scale=(-2,3,4)),
              20:transform(2,parent=10,rotation=(0,0,s,s))}
        world = audit.hierarchy(ts,{1:{'m_IsActive':False},2:{'m_IsActive':True}})
        point = audit.transform_point(world[20][0],[1,0,0])
        self.assertAlmostEqual(point[0],0)
        self.assertAlmostEqual(point[1],3)
        self.assertFalse(world[20][1])

    def test_broken_parent_graphs_fail(self):
        gos = {1:{'m_IsActive':True},2:{'m_IsActive':True}}
        with self.assertRaisesRegex(ValueError,'cycle'):
            audit.hierarchy({10:transform(1,20),20:transform(2,10)},gos)
        with self.assertRaises(KeyError):
            audit.hierarchy({10:transform(1,999)},gos)
        t = transform(1)
        t['m_Father']['m_FileID'] = 1
        with self.assertRaisesRegex(ValueError,'External parent'):
            audit.hierarchy({10:t},gos)


if __name__ == '__main__':
    unittest.main()
