import errno
import os
import shutil
import tempfile
import uuid
from collections import namedtuple
from filecmp import cmp
from unittest import mock

import pyfakefs.fake_filesystem as fake_fs
import requests
from django.test import SimpleTestCase

from ESSArch_Core.storage.copy import copy_chunk_remotely, copy_dir, copy_file
from ESSArch_Core.storage.exceptions import NoSpaceLeftError


class CopyChunkTestCase(SimpleTestCase):
    fs = fake_fs.FakeFilesystem()
    fake_open = fake_fs.FakeFileOpen(fs)

    def setUp(self):
        self.src = 'src.txt'
        self.dst = 'dst.txt'
        self.fs.create_file(self.src)

        with self.fake_open(self.src, 'w') as f:
            f.write('foo')

    def tearDown(self):
        self.fs.remove(self.src)

        try:
            self.fs.remove(self.dst)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    @mock.patch('requests.Session.post')
    def test_copy_chunk_remotely(self, mock_post):
        dst = "http://remote.destination/upload"
        session = requests.Session()
        session.params = {'dst': 'foo'}

        attrs = {'json.return_value': {'upload_id': uuid.uuid4().hex},
                 'elapsed': mock.PropertyMock(**{'total_seconds.return_value': 1})}
        mock_response = mock.Mock()
        mock_response.configure_mock(**attrs)

        mock_post.return_value = mock_response

        upload_id = uuid.uuid4().hex

        copy_chunk_remotely(self.src, dst, 1, 3, upload_id=upload_id, requests_session=session, block_size=1)

        mock_post.assert_called_once_with(
            dst, files={'file': ('src.txt', b'o')},
            data={'upload_id': upload_id, 'dst': 'foo'},
            headers={'Content-Range': 'bytes 1-1/3'},
            timeout=60,
        )

    @mock.patch('ESSArch_Core.storage.copy.copy_chunk_remotely.retry.sleep')
    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    @mock.patch('requests.Session.post')
    def test_copy_chunk_remotely_server_error(self, mock_post, mock_sleep):
        attrs = {'raise_for_status.side_effect': requests.exceptions.HTTPError}
        mock_response = mock.Mock()
        mock_response.configure_mock(**attrs)

        mock_post.return_value = mock_response

        dst = "http://remote.destination/upload"
        session = requests.Session()

        upload_id = uuid.uuid4().hex

        with self.assertRaises(requests.exceptions.HTTPError):
            copy_chunk_remotely(self.src, dst, 1, 3, upload_id=upload_id, requests_session=session, block_size=1)

        calls = [mock.call(
            dst, files={'file': ('src.txt', b'o')},
            data={'upload_id': upload_id, 'dst': None},
            headers={'Content-Range': 'bytes 1-1/3'},
            timeout=60,
        ) if x % 2 == 0 else mock.call().raise_for_status() for x in range(10)]

        mock_post.assert_has_calls(calls)


class CopyFileTestCase(SimpleTestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_copy_file_locally(self):
        src = os.path.join(self.datadir, 'foo.txt')
        with open(src, 'w') as f:
            f.write('test')

        dst = os.path.join(self.datadir, 'bar.txt')
        copy_file(src, dst)

        self.assertTrue(os.path.isfile(src))
        self.assertTrue(os.path.isfile(dst))
        self.assertTrue(cmp(src, dst, shallow=False))

    @mock.patch('ESSArch_Core.storage.copy._send_completion_request')
    @mock.patch('ESSArch_Core.storage.copy.copy_chunk_remotely', return_value='test_upload_id')
    def test_copy_file_remotely(self, mock_copy, _mock_req):
        src = os.path.join(self.datadir, 'foo.txt')
        with open(src, 'w') as f:
            f.write('test')
        dst = 'bar'
        session = requests.Session()

        copy_file(src, dst, requests_session=session, block_size=1)
        mock_copy.assert_has_calls(
            [mock.call(src, dst, 0, block_size=1, file_size=4, requests_session=session)]
            + [mock.call(src, dst, i, block_size=1, file_size=4, requests_session=session, upload_id='test_upload_id')
               for i in range(1, 5)]
        )

    def test_copy_with_not_enough_space_at_dst(self):
        src = os.path.join(self.datadir, 'foo.txt')
        with open(src, 'w') as f:
            f.write('test')

        dst = os.path.join(self.datadir, 'bar.txt')

        mock_size = mock.patch('ESSArch_Core.storage.copy.get_tree_size_and_count', return_value=(10, 1))

        ntuple_free = namedtuple('usage', 'free')
        mock_free = mock.patch('ESSArch_Core.storage.copy.shutil.disk_usage', return_value=ntuple_free(free=5))

        with mock_size, mock_free:
            with self.assertRaises(NoSpaceLeftError):
                copy_file(src, dst)


class CopyDirTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_copy_directory_onto_file(self):
        src = tempfile.mkdtemp(dir=self.root)
        dstf, dst = tempfile.mkstemp(dir=self.root)
        os.close(dstf)

        msg = f'Cannot overwrite non-directory {dst} with directory {src}'
        with self.assertRaisesMessage(ValueError, msg):
            copy_dir(src, dst)

    def test_copy_trees(self):
        src = os.path.join(self.root, 'src')
        os.makedirs(os.path.join(src, 'a'))
        os.makedirs(os.path.join(src, 'b'))

        open(os.path.join(src, 'a', 'foo.txt'), 'a').close()
        open(os.path.join(src, 'b', 'bar.txt'), 'a').close()

        dst = os.path.join(self.root, 'dst')
        copy_dir(src, dst)

        self.assertTrue(os.path.isfile(os.path.join(dst, 'a/foo.txt')))
        self.assertTrue(os.path.isfile(os.path.join(dst, 'b/bar.txt')))

        # ensure source still exists
        self.assertTrue(os.path.isfile(os.path.join(src, 'a/foo.txt')))
        self.assertTrue(os.path.isfile(os.path.join(src, 'b/bar.txt')))

    def test_copy_empty_subdirs(self):
        src = os.path.join(self.root, 'src')
        os.makedirs(os.path.join(src, 'a'))
        os.makedirs(os.path.join(src, 'b'))

        dst = os.path.join(self.root, 'dst')
        copy_dir(src, dst)

        self.assertTrue(os.path.isdir(os.path.join(dst, 'a')))
        self.assertTrue(os.path.isdir(os.path.join(dst, 'b')))

        # ensure source still exists
        self.assertTrue(os.path.isdir(os.path.join(src, 'a')))
        self.assertTrue(os.path.isdir(os.path.join(src, 'b')))

    def test_copy_with_not_enough_space_at_dst(self):
        src = tempfile.mkdtemp(dir=self.root)
        with open(os.path.join(src, 'foo.txt'), 'w') as f:
            f.write('test')
        dst = tempfile.mkdtemp(dir=self.root)

        mock_size = mock.patch('ESSArch_Core.storage.copy.get_tree_size_and_count', return_value=(10, 1))

        ntuple_free = namedtuple('usage', 'free')
        mock_free = mock.patch('ESSArch_Core.storage.copy.shutil.disk_usage', return_value=ntuple_free(free=5))

        with mock_size, mock_free:
            with self.assertRaises(NoSpaceLeftError):
                copy_dir(src, dst)
