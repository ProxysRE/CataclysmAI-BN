"""Corruption and reference-integrity checks for exported geometry."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/client_data'))
from validate_factory_export import validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mesh={'file':'sharedassets1.assets','path_id':str(2**63-1),
                   'vertices':[[0,0,0],[1,0,0],[0,0,1]],'triangles':[[0,1,2]]}
        self.collider={'scene':'level1','component_path_id':'10','gameobject_path_id':'2',
                       'world_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
                       'layer':18,'type':'MeshCollider','mesh':{'file':self.mesh['file'],'path_id':self.mesh['path_id']},
                       'active_in_hierarchy':True,'enabled':True,'is_trigger':False}
        self.report={'schema_version':1,'complete_for_selected_serialized_colliders':True,
                     'issues':[],'selected_scenes':{'level1':'example'},'scene_counts':{'level1':{'colliders':1}},
                     'mesh_counts':{'decoded':1,'vertices':3,'triangles':1},'source_files':{'level1':{'bytes':1,'sha256':'a'*64}}}

    def run_fixture(self,mesh=None,collider=None,report=None):
        p=Path(self.tmp.name)/'fixture.zip'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('report.json',json.dumps(self.report if report is None else report))
            z.writestr('meshes.jsonl',json.dumps(self.mesh if mesh is None else mesh)+'\n')
            z.writestr('colliders.jsonl',json.dumps(self.collider if collider is None else collider)+'\n')
        return p

    def test_valid_export_keeps_large_ids_and_totals(self):
        result=validate(self.run_fixture(),{'files':self.report['source_files']})
        self.assertEqual(result['resolved_mesh_references'],1)
        self.assertEqual(result['prior_source_hashes_matched'],1)

    def test_bad_triangle_fails(self):
        m=copy.deepcopy(self.mesh);m['triangles']=[[0,1,3]]
        with self.assertRaisesRegex(ValueError,'triangle index'):
            validate(self.run_fixture(mesh=m))

    def test_broken_external_reference_fails(self):
        c=copy.deepcopy(self.collider);c['mesh']['path_id']='999'
        with self.assertRaisesRegex(ValueError,'Unresolved Mesh'):
            validate(self.run_fixture(collider=c))

    def test_nonfinite_transform_fails(self):
        c=copy.deepcopy(self.collider);c['world_matrix'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'world transform'):
            validate(self.run_fixture(collider=c))

    def test_truncated_scene_count_fails(self):
        r=copy.deepcopy(self.report);r['scene_counts']['level1']['colliders']=2
        with self.assertRaisesRegex(ValueError,'Collider totals'):
            validate(self.run_fixture(report=r))

    def test_partial_flag_and_changed_sources_fail(self):
        r=copy.deepcopy(self.report);r['complete_for_selected_serialized_colliders']=False
        with self.assertRaisesRegex(ValueError,'partial'):
            validate(self.run_fixture(report=r))
        with self.assertRaisesRegex(ValueError,'differs from baseline'):
            validate(self.run_fixture(),{'files':{'level1':{'bytes':2,'sha256':'b'*64}}})


if __name__=='__main__':
    unittest.main()
