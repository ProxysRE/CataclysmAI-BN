"""Geometric invariants for reference sampling; does not execute BN."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

spec=importlib.util.spec_from_file_location('factory_reference',
    Path(__file__).resolve().parents[2]/'tools/locations/inspect_factory_reference.py')
reference=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


class AreaSampling(unittest.TestCase):
    def test_fractional_last_cell_stays_partial(self):
        image=Image.new('L',(9,4),255)
        result=reference.coverage(image,2.25,1,1,3,1)
        np.testing.assert_allclose(result,[[1,1,.25]],atol=1e-12)

    def test_fractional_corner_area_is_conserved(self):
        image=Image.new('L',(9,6),255)
        result=reference.coverage(image,2.25,1.5,1,3,2)
        self.assertAlmostEqual(result.sum(),2.25*1.5)
        self.assertAlmostEqual(result[1,2],.125)

    def test_padding_is_empty_not_stretched_floor(self):
        image=Image.new('L',(4,4),255)
        result=reference.coverage(image,1,1,.5,4,4)
        np.testing.assert_allclose(result[:2,:2],1)
        np.testing.assert_allclose(result[2:,:],0)
        np.testing.assert_allclose(result[:,2:],0)

    def test_thin_boundary_keeps_its_position(self):
        pixels=np.zeros((4,12),dtype=np.uint8)
        pixels[:,7]=255
        result=reference.coverage(Image.fromarray(pixels),3,1,1,3,1)
        np.testing.assert_allclose(result,[[0,.25,0]],atol=1e-12)


if __name__=='__main__':
    unittest.main()
