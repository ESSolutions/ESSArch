import errno
import os
import shutil
import tempfile
import uuid
from unittest import mock

import pyfakefs.fake_filesystem as fake_fs
import requests
from django.test import SimpleTestCase

from ESSArch_Core.storage.copy import copy_chunk_remotely, copy_dir, copy_file


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
    @mock.patch('ESSArch_Core.storage.copy.copy_file_remotely')
    @mock.patch('ESSArch_Core.storage.copy.copy_file_locally')
    def test_copy_file(self, mock_local, mock_remote):
        src = 'foo'
        dst = 'bar'
        copy_file(src, dst)
        mock_local.assert_called_once_with(src, dst)

        session = requests.Session()
        copy_file(src, dst, requests_session=session)
        mock_remote.assert_called_once_with(src, dst, session, block_size=mock.ANY)


class CopyDirTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

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
