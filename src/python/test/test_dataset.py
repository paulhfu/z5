import unittest
import sys
import numpy as np
import os
from shutil import rmtree
from six import add_metaclass
from abc import ABCMeta

try:
    import z5py
except ImportError:
    sys.path.append('..')
    import z5py


@add_metaclass(ABCMeta)
class DatasetTestMixin(object):
    def setUp(self):
        self.shape = (100, 100, 100)
        self.root_file = z5py.File('array.' + self.data_format,
                                   use_zarr_format=self.data_format == 'zarr')

        self.base_dtypes = [
            'int8', 'int16', 'int32', 'int64',
            'uint8', 'uint16', 'uint32', 'uint64',
            'float32', 'float64'
        ]
        self.dtypes = tuple(
            self.base_dtypes +
            [np.dtype(s) for s in self.base_dtypes] +
            [
                '<i1', '<i2', '<i4', '<i8',
                '<u1', '<u2', '<u4', '<u8',
                '<f4', '<f8'
            ] +
            [
                np.int8, np.int16, np.int32, np.int64,
                np.uint8, np.uint16, np.uint32, np.uint64,
                np.float32, np.float64
            ]
        )

    def tearDown(self):
        try:
            rmtree('array.' + self.data_format)
        except OSError:
            pass

    def check_array(self, result, expected, msg=None):
        self.assertEqual(result.shape, expected.shape, msg)
        self.assertTrue(np.allclose(result, expected), msg)

    def test_ds_open_empty(self):
        self.root_file.create_dataset('test',
                                      dtype='float32',
                                      shape=self.shape,
                                      chunks=(10, 10, 10))
        ds = self.root_file['test']
        out = ds[:]
        self.check_array(out, np.zeros(self.shape))

    def test_ds_dtypes(self):
        for dtype in self.dtypes:
            ds = self.root_file.create_dataset('data_%s' % hash(dtype),
                                               dtype=dtype,
                                               shape=self.shape,
                                               chunks=(10, 10, 10))
            in_array = np.random.rand(*self.shape).astype(dtype)
            ds[:] = in_array
            out_array = ds[:]
            self.check_array(out_array, in_array,
                             'datatype %s failed for format %s' % (self.data_format.title(),
                                                                   dtype))

    def check_ones(self, sliced_ones, expected_shape, msg=None):
        self.check_array(sliced_ones, np.ones(expected_shape, dtype=np.uint8), msg)

    def test_ds_simple_write(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = np.ones(self.shape, np.uint8)

    def test_ds_indexing(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = np.ones(self.shape, np.uint8)

        self.check_ones(ds[:], self.shape, 'full index failed')

        self.check_ones(ds[1, ...], (1, 100, 100), 'trailing ellipsis failed')
        self.check_ones(ds[..., 1], (100, 100, 1), 'leading ellipsis failed')
        self.check_ones(ds[1], (1, 100, 100), 'implicit ellipsis failed')
        self.check_ones(ds[:, :, :, ...], self.shape, 'superfluous ellipsis failed')
        self.check_ones(ds[500:501, :, :], (0, 100, 100), 'out-of-bounds slice failed')
        self.check_ones(ds[-501:500, :, :], (0, 100, 100), 'negative out-of-bounds slice failed')

        self.check_ones(ds[1, :, :], (1, 100, 100), 'integer index failed')
        self.check_ones(ds[-20:, :, :], (20, 100, 100), 'negative slice failed')

        self.assertEqual(ds[1, 1, 1], 1, 'point index failed')

        with self.assertRaises(ValueError):
            ds[500, :, :]
        with self.assertRaises(ValueError):
            ds[-500, :, :]
        with self.assertRaises(ValueError):
            ds[..., :, ...]
        with self.assertRaises(ValueError):
            ds[1, 1, slice(0, 100, 2)]
        with self.assertRaises(TypeError):
            ds[[1, 1, 1]]  # explicitly test behaviour different to h5py

        class NotAnIndex(object):
            pass

        with self.assertRaises(TypeError):
            ds[1, 1, NotAnIndex()]

    def test_ds_scalar_broadcast(self):
        for dtype in self.base_dtypes:
            ds = self.root_file.create_dataset('ones_%s' % dtype,
                                               dtype=dtype,
                                               shape=self.shape,
                                               chunks=(10, 10, 10))
            ds[:] = 1
            self.check_ones(ds[:], self.shape)

    def test_ds_scalar_broadcast_from_float(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = float(1)
        self.check_ones(ds[:], self.shape)

    def test_ds_scalar_broadcast_from_bool(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = True
        self.check_ones(ds[:], self.shape)

    def test_ds_set_with_arraylike(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[0, :2, :2] = [[1, 1], [1, 1]]
        self.check_ones(ds[0, :2, :2], (1, 2, 2))

    def test_ds_set_from_float(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = np.ones(self.shape, dtype=float)
        self.check_ones(ds[:], self.shape)

    def test_ds_set_from_bool(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        ds[:] = np.ones(self.shape, dtype=bool)
        self.check_ones(ds[:], self.shape)

    def test_ds_fancy_broadcast_fails(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        with self.assertRaises(ValueError):
            ds[0, :10, :10] = np.ones(10, dtype=np.uint8)

    def test_ds_write_object_fails(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))

        class ArbitraryObject(object):
            pass

        with self.assertRaises(OSError):
            ds[0, 0, :2] = [ArbitraryObject(), ArbitraryObject()]

    def test_ds_write_flexible_fails(self):
        ds = self.root_file.create_dataset('ones', dtype=np.uint8,
                                           shape=self.shape, chunks=(10, 10, 10))
        with self.assertRaises(TypeError):
            ds[0, 0, 0] = "hey, you're not a number"

    def test_readwrite_multithreaded(self):
        for n_threads in (1, 2, 4, 8):
            ds = self.root_file.create_dataset('data_mthread_%i' % n_threads,
                                               dtype='float64',
                                               shape=self.shape,
                                               chunks=(10, 10, 10),
                                               n_threads=n_threads)
            in_array = np.random.rand(*self.shape)
            ds[:] = in_array
            out_array = ds[:]
            self.check_array(out_array, in_array)

    def test_create_nested_dataset(self):
        ds = self.root_file.create_dataset('group/sub_group/data',
                                           shape=self.shape,
                                           dtype='float64',
                                           chunks=(10, 10, 10))
        self.assertEqual(ds.path, os.path.join(self.root_file.path, 'group/sub_group/data'))

    def test_create_with_data(self):
        in_array = np.random.rand(*self.shape)
        ds = self.root_file.create_dataset('data', data=in_array)
        out_array = ds[:]
        self.check_array(out_array, in_array)

    def test_require_dataset(self):
        in_array = np.random.rand(*self.shape)
        self.root_file.require_dataset('data', data=in_array,
                                       shape=in_array.shape,
                                       dtype=in_array.dtype)
        ds = self.root_file.require_dataset('data',
                                            shape=in_array.shape,
                                            dtype=in_array.dtype)
        out_array = ds[:]
        self.check_array(out_array, in_array)

    def test_non_contiguous(self):
        ds = self.root_file.create_dataset('test',
                                           dtype='float32',
                                           shape=self.shape,
                                           chunks=(10, 10, 10))
        # make a non-contiguous 3d array of the correct shape (100)^3
        vol = np.arange(200**3).astype('float32').reshape((200, 200, 200))
        in_array = vol[::2, ::2, ::2]
        ds[:] = in_array
        out_array = ds[:]
        self.check_array(out_array, in_array, 'failed for non-contiguous data')

    def test_empty_chunk(self):
        ds = self.root_file.create_dataset('test',
                                           dtype='float32',
                                           shape=self.shape,
                                           chunks=(10, 10, 10))
        bb = np.s_[:10, :10, :10]
        if ds.is_zarr:
            chunk_path = os.path.join(ds.path, '0.0.0')
        else:
            chunk_path = os.path.join(ds.path, '0', '0', '0')
        ds[bb] = 0
        self.assertFalse(os.path.exists(chunk_path))
        ds[bb] = 1
        self.assertTrue(os.path.exists(chunk_path))
        ds[bb] = 0
        self.assertFalse(os.path.exists(chunk_path))

    def test_invalid_options(self):
        with self.assertRaises(RuntimeError):
            self.root_file.create_dataset('test1', shape=self.shape, dtype='float32',
                                          chunks=(10, 10, 10), compression='raw',
                                          level=5)
        with self.assertRaises(RuntimeError):
            self.root_file.create_dataset('test2', shape=self.shape, dtype='float32',
                                          chunks=(10, 10, 10), compression='bzip2',
                                          level=5, blub='blob')

    def test_readwrite_chunk(self):
        shape = (100, 100)
        chunks = (10, 10)
        for dtype in self.base_dtypes:
            ds = self.root_file.create_dataset('test_%s' % dtype, dtype=dtype,
                                               shape=shape, chunks=chunks,
                                               compression='raw')
            # test empty chunk
            out = ds.read_chunk((0, 0))
            self.assertEqual(out, None)

            # test read/write
            chunks_per_dim = ds.chunks_per_dimension
            for x in range(chunks_per_dim[0]):
                for y in range(chunks_per_dim[1]):
                    data = np.random.rand(*chunks)
                    if dtype not in ('float32', 'float64'):
                        data *= 128
                    data = data.astype(dtype)
                    ds.write_chunk((x, y), data)
                    out = ds.read_chunk((x, y))
                    self.assertEqual(data.shape, out.shape)
                    self.assertTrue(np.allclose(data, out))


class TestZarrDataset(DatasetTestMixin, unittest.TestCase):
    data_format = 'zarr'

    def test_varlen(self):
        shape = (100, 100)
        chunks = (10, 10)
        ds = self.root_file.create_dataset('varlen', dtype='float64',
                                           shape=shape, chunks=chunks,
                                           compression='raw')
        with self.assertRaises(RuntimeError):
            ds.write_chunk((0, 0), np.random.rand(10), True)



class TestN5Dataset(DatasetTestMixin, unittest.TestCase):
    data_format = 'n5'

    @unittest.skipIf(sys.version_info.major < 3, "This fails in python 2")
    def test_ds_array_to_format(self):
        for dtype in self.base_dtypes:
            ds = self.root_file.create_dataset('data_%s' % hash(dtype),
                                               dtype=dtype,
                                               shape=self.shape,
                                               chunks=(10, 10, 10))
            in_array = 42 * np.ones((10, 10, 10), dtype=dtype)
            ds[:10, :10, :10] = in_array

            path = os.path.join(os.path.dirname(ds.attrs.path), '0', '0', '0')
            with open(path, 'rb') as f:
                read_from_file = np.array([byte for byte in f.read()], dtype='int8')

            converted_data = ds.array_to_format(in_array)

            self.assertEqual(len(read_from_file), len(converted_data))
            self.assertTrue(np.allclose(read_from_file, converted_data))

    def test_varlen(self):
        shape = (100, 100)
        chunks = (10, 10)
        ds = self.root_file.create_dataset('varlen', dtype='float64',
                                           shape=shape, chunks=chunks,
                                           compression='raw')

        # max_len = 100
        max_len = 10
        chunks_per_dim = ds.chunks_per_dimension
        for x in range(chunks_per_dim[0]):
            for y in range(chunks_per_dim[1]):
                test_data = np.random.rand(np.random.randint(0, max_len))
                ds.write_chunk((x, y), test_data, True)
                out = ds.read_chunk((x, y))
                self.assertEqual(test_data.shape, out.shape)
                self.assertTrue(np.allclose(test_data, out))



if __name__ == '__main__':
    unittest.main()
