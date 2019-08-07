# -*- coding: utf-8 -*-

import errno
import uuid
from unittest import mock

import pyfakefs.fake_filesystem as fake_fs
import requests
from django.test import TestCase

from ESSArch_Core.storage.copy import (
    copy_chunk,
    copy_chunk_locally,
    copy_chunk_remotely,
    copy_file,
    copy_file_locally,
)


class CopyChunkTestCase(TestCase):
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

    @mock.patch('ESSArch_Core.storage.copy.copy_chunk_remotely')
    def test_copy_chunk_with_session(self, mock_copy_chunk_remotely):
        dst = "http://remote.destination/upload"
        session = requests.Session()

        upload_id = uuid.uuid4().hex

        copy_chunk(self.src, dst, 1, file_size=3, upload_id=upload_id, requests_session=session, block_size=1)

        mock_copy_chunk_remotely.assert_called_once_with(
            self.src, dst, 1, 3, upload_id=upload_id,
            requests_session=session, block_size=1
        )

    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    def test_copy_chunk_locally(self):
        fsize = self.fs.stat(self.src).st_size
        self.dst = "dst.txt"

        copy_chunk_locally(self.src, self.dst, 1, fsize, block_size=1)

        with self.fake_open(self.dst) as dstf:
            self.assertEqual(dstf.read(), 'o')

    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    @mock.patch('requests.Session.post')
    def test_copy_chunk_remotely(self, mock_post):
        dst = "http://remote.destination/upload"
        session = requests.Session()

        attrs = {'json.return_value': {'upload_id': uuid.uuid4().hex},
                 'elapsed': mock.PropertyMock(**{'total_seconds.return_value': 1})}
        mock_response = mock.Mock()
        mock_response.configure_mock(**attrs)

        mock_post.return_value = mock_response

        upload_id = uuid.uuid4().hex

        copy_chunk_remotely(self.src, dst, 1, 3, upload_id=upload_id, requests_session=session, block_size=1)

        mock_post.assert_called_once_with(
            dst, files={'file': ('src.txt', b'o')},
            data={'upload_id': upload_id},
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
            data={'upload_id': upload_id},
            headers={'Content-Range': 'bytes 1-1/3'},
            timeout=60,
        ) if x % 2 == 0 else mock.call().raise_for_status() for x in range(10)]

        mock_post.assert_has_calls(calls)

    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    def test_local_non_ascii_file_name(self):
        src = 'åäö.txt'
        dst = 'öäå.txt'

        self.fs.create_file(src)
        self.fs.create_file(dst)

        with self.fake_open(src, 'w') as f:
            f.write('foo')

        fsize = self.fs.stat(src).st_size
        copy_chunk_locally(src, dst, 1, fsize, block_size=1)

        with self.fake_open(dst) as dstf:
            self.assertEqual(dstf.read(), 'o')


class CopyFileTestCase(TestCase):
    fs = fake_fs.FakeFilesystem()
    fake_open = fake_fs.FakeFileOpen(fs)
    fake_os = fake_fs.FakeOsModule(fs)

    def setUp(self):
        self.src = 'src.txt'
        self.dst = 'dst.txt'
        self.fs.create_file(self.src)

    def tearDown(self):
        self.fs.remove(self.src)

        try:
            self.fs.remove(self.dst)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @mock.patch('ESSArch_Core.storage.copy.os', fake_os)
    @mock.patch('ESSArch_Core.storage.copy.copy_file_locally')
    def test_copy_file(self, mock_copy_file_locally):
        copy_file(self.src, self.dst)
        mock_copy_file_locally.assert_called_once_with(self.src, self.dst, block_size=mock.ANY)

    @mock.patch('ESSArch_Core.storage.copy.os', fake_os)
    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    @mock.patch('ESSArch_Core.storage.copy.copy_chunk')
    def test_local_empty(self, mock_copy_chunk):
        copy_file_locally(self.src, self.dst)
        fsize = self.fs.stat(self.src).st_size
        mock_copy_chunk.assert_called_once_with(self.src, self.dst, 0, fsize, block_size=mock.ANY)

    @mock.patch('ESSArch_Core.storage.copy.os', fake_os)
    @mock.patch('ESSArch_Core.storage.copy.open', fake_open)
    @mock.patch('ESSArch_Core.storage.copy.copy_chunk')
    def test_local_non_empty_small_block_size(self, mock_copy_chunk):
        content = 'foo'
        with self.fake_open(self.src, 'w') as f:
            f.write(content)

        copy_file_locally(self.src, self.dst, block_size=1)

        fsize = self.fs.stat(self.src).st_size
        calls = [mock.call(self.src, self.dst, x, fsize, block_size=1) for x in range(len(content))]
        mock_copy_chunk.assert_has_calls(calls)
