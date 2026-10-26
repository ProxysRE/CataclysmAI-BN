"""Selection and identity checks for the read-only client exporter."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/client_data'))
from export_factory_colliders import data_directory, factory_scenes, mesh_reference


class ExportTests(unittest.TestCase):
    def test_scene_indices_come_from_this_build(self):
        settings = {'scenes':['Assets/Content/Locations/Factory/Factory.unity',
                              'Assets/Content/Locations/Factory_Rework/Factory_Rework_Areas.unity']}
        self.assertEqual(factory_scenes(settings), [('level1',settings['scenes'][1])])
        with self.assertRaisesRegex(ValueError,'No Factory_Rework'):
            factory_scenes({'scenes':settings['scenes'][:1]})

    def test_file_id_is_one_based_and_path_id_keeps_64_bits(self):
        pid = 2**63-1
        self.assertEqual(mesh_reference('level528',['sharedassets2.assets'],
                                       {'m_FileID':1,'m_PathID':pid}),('sharedassets2.assets',pid))
        self.assertEqual(mesh_reference('level528',[],{'m_FileID':0,'m_PathID':pid}),('level528',pid))
        self.assertIsNone(mesh_reference('level528',[],{'m_FileID':0,'m_PathID':0}))
        with self.assertRaisesRegex(ValueError,'out of range'):
            mesh_reference('level528',[],{'m_FileID':1,'m_PathID':pid})
        with self.assertRaisesRegex(ValueError,'out of range'):
            mesh_reference('level528',[],{'m_FileID':-1,'m_PathID':pid})

    def test_only_known_resource_paths_are_accepted(self):
        p = {'m_FileID':1,'m_PathID':1}
        self.assertEqual(mesh_reference('level528',['Library/unity default resources'],p)[0],
                         'Library/unity default resources')
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            mesh_reference('level528',['../outside.assets'],p)

    def test_only_supplied_game_root_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,'not found'):
                data_directory(root)
            data=root/'EscapeFromTarkov_Data';data.mkdir();(data/'globalgamemanagers').touch()
            self.assertEqual(data_directory(root),data.resolve())
            self.assertEqual(data_directory(data),data.resolve())


if __name__=='__main__':
    unittest.main()
