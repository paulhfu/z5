import unittest
import os
from shutil import rmtree

import sys
try:
    import z5py
except ImportError:
    sys.path.append('..')
    import z5py


class TestFile(unittest.TestCase):
    def setUp(self):
        self.n5_path = 'array.n5'
        self.zr_path = 'array.zr'
        self.zarr_path = 'array.zarr'

    def tearDown(self):
        if(os.path.exists(self.n5_path)):
            rmtree(self.n5_path)
        if(os.path.exists(self.zr_path)):
            rmtree(self.zr_path)
        if(os.path.exists(self.zarr_path)):
            rmtree(self.zarr_path)

    def test_context_manager_n5(self):
        self.assertFalse(os.path.exists(self.n5_path))

        with z5py.File(self.n5_path, False) as f:
            self.assertIsInstance(f, z5py.File)
            self.assertFalse(f.is_zarr)

        self.assertTrue(os.path.exists(self.n5_path))

    def test_context_manager_zarr(self):
        self.assertFalse(os.path.exists(self.zr_path))

        with z5py.File(self.zr_path, True) as f:
            self.assertIsInstance(f, z5py.File)
            self.assertTrue(f.is_zarr)

        self.assertTrue(os.path.exists(self.zr_path))

    def test_extension_detect_n5(self):
        self.assertFalse(os.path.exists(self.n5_path))

        f = z5py.File(self.n5_path, None)
        self.assertFalse(f.is_zarr)

    def test_extension_detect_zr(self):
        self.assertFalse(os.path.exists(self.zr_path))

        f = z5py.File(self.zr_path, None)
        self.assertTrue(f.is_zarr)

    def test_extension_detect_zarr(self):
        self.assertFalse(os.path.exists(self.zarr_path))

        f = z5py.File(self.zarr_path, None)
        self.assertTrue(f.is_zarr)

    def test_direct_constructor_n5(self):
        self.assertFalse(os.path.exists(self.n5_path))

        f = z5py.N5File(self.n5_path)
        self.assertFalse(f.is_zarr)

    def test_direct_constructor_zarr(self):
        self.assertFalse(os.path.exists(self.zarr_path))

        f = z5py.ZarrFile(self.zarr_path)
        self.assertTrue(f.is_zarr)

    def test_wrong_ext_fails(self):
        with self.assertRaises(RuntimeError):
            z5py.File(self.zarr_path, use_zarr_format=False)

        with self.assertRaises(RuntimeError):
            z5py.File(self.n5_path, use_zarr_format=True)


if __name__ == '__main__':
    unittest.main()
