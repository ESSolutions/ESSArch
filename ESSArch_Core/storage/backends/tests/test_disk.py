# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
from unittest import mock

from django.test import TestCase

from ESSArch_Core.storage.backends.disk import DiskStorageBackend
from ESSArch_Core.storage.copy import DEFAULT_BLOCK_SIZE


class DiskStorageBackendTests(TestCase):

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root_dir)

        self.datadir = os.path.join(self.root_dir, "datadir")

        os.makedirs(self.datadir)

    def create_file(self, name, ext, content="dummy_content"):
        fname = os.path.join(self.datadir, f'{name}.{ext}')
        with open(fname, 'w') as f:
            f.write(content)

        return fname

    def create_container_files(self, archive_filename, archive_format):
        archive_file_full_path = os.path.join(self.datadir, archive_filename)

        return shutil.make_archive(archive_file_full_path, archive_format, self.datadir)

    @mock.patch("ESSArch_Core.storage.models.StorageMethod")
    @mock.patch("ESSArch_Core.storage.models.StorageMedium")
    def test_write_destination_not_a_dir_should_raise_exception(self, mock_storage_medium, mock_storage_method):
        disk_storage_backend = DiskStorageBackend()
        mock_storage_medium.storage_target.target = "some_bad_destination"

        with self.assertRaisesRegexp(ValueError, "{} is not a directory".format("some_bad_destination")):
            disk_storage_backend.write(
                src="some_src",
                ip=mock.ANY,
                storage_method=mock_storage_method,
                storage_medium=mock_storage_medium
            )

        with self.assertRaisesRegexp(ValueError, "{} is not a directory".format("some_bad_destination")):
            disk_storage_backend.write(
                src=["some_src"],
                ip=mock.ANY,
                storage_method=mock_storage_method,
                storage_medium=mock_storage_medium
            )

    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    @mock.patch("ESSArch_Core.storage.models.StorageObject.objects.create")
    @mock.patch("ESSArch_Core.storage.models.StorageMethod")
    @mock.patch("ESSArch_Core.storage.models.StorageMedium")
    def test_write_dest_is_path_to_container(self, mock_st_medium, mock_st_method, mock_st_obj, mock_copy):
        disk_storage_backend = DiskStorageBackend()
        mock_st_medium.storage_target.target = self.datadir
        mock_st_method.containers = True

        disk_storage_backend.write(
            src="some_src",
            ip=mock.ANY,
            storage_method=mock_st_method,
            storage_medium=mock_st_medium
        )

        mock_copy.assert_called_once()
        mock_st_obj.assert_called_once()

    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    @mock.patch("ESSArch_Core.storage.models.StorageObject.objects.create")
    @mock.patch("ESSArch_Core.storage.models.StorageMethod")
    @mock.patch("ESSArch_Core.storage.models.StorageMedium")
    def test_write_src_with_multi_files(self, mock_st_medium, mock_st_method, mock_st_obj, mock_copy):
        disk_storage_backend = DiskStorageBackend()
        mock_st_medium.storage_target.target = self.datadir
        mock_st_method.containers = True
        src_list = ["some_src", "some_src2", "some_src3"]

        disk_storage_backend.write(
            src=src_list,
            ip=mock.ANY,
            storage_method=mock_st_method,
            storage_medium=mock_st_medium
        )

        expected_dest = self.datadir
        expected_copy_calls = [mock.call(src, expected_dest, block_size=DEFAULT_BLOCK_SIZE) for src in src_list]

        self.assertEqual(mock_copy.call_count, 3)
        mock_copy.assert_has_calls(expected_copy_calls)
        mock_st_obj.assert_called_once()

    @mock.patch("ESSArch_Core.ip.models.InformationPackage")
    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    @mock.patch("ESSArch_Core.storage.models.StorageObject.objects.create")
    @mock.patch("ESSArch_Core.storage.models.StorageMethod")
    @mock.patch("ESSArch_Core.storage.models.StorageMedium")
    def test_write_src_with_multi_files_not_container(self, st_medium, mock_st_method, mock_st_obj, mock_copy, ip):
        disk_storage_backend = DiskStorageBackend()
        st_medium.storage_target.target = self.datadir
        mock_st_method.containers = False
        ip.object_identifier_value = "some/object/path"
        src_list = ["some_src", "some_src2", "some_src3"]

        disk_storage_backend.write(
            src=src_list,
            ip=ip,
            storage_method=mock_st_method,
            storage_medium=st_medium
        )

        expected_dest = os.path.join(self.datadir, "some/object/path")
        expected_copy_calls = [mock.call(src, expected_dest, block_size=DEFAULT_BLOCK_SIZE) for src in src_list]

        self.assertEqual(mock_copy.call_count, 3)
        mock_copy.assert_has_calls(expected_copy_calls)
        mock_st_obj.assert_called_once()

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    def test_read_not_container_should_call_copy(self, mock_copy, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()

        mock_storage_obj.container = False
        mock_storage_obj.get_full_path.return_value = "the_full_path"

        disk_storage_backend.read(
            storage_object=mock_storage_obj,
            dst="some_dest"
        )

        mock_copy.assert_called_once_with("the_full_path", "some_dest", block_size=DEFAULT_BLOCK_SIZE)

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    @mock.patch("ESSArch_Core.ip.models.InformationPackage")
    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    def test_read_container_default(self, mock_copy, mock_ip, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()
        full_path_to_src = "the/full/path/to/src"
        container_path = "container/path"

        mock_storage_obj.container = True
        mock_storage_obj.get_full_path.return_value = full_path_to_src
        mock_storage_obj.storage_medium.storage_target.target = container_path
        mock_storage_obj.ip = mock_ip
        mock_ip.aic.pk = 1234

        disk_storage_backend.read(
            storage_object=mock_storage_obj,
            dst="some_dest"
        )

        expected_copy_calls = [
            mock.call(f"{full_path_to_src}.xml", "some_dest", block_size=DEFAULT_BLOCK_SIZE),
            mock.call(os.path.join(container_path, "1234.xml"), "some_dest", block_size=DEFAULT_BLOCK_SIZE),
            mock.call(f"{full_path_to_src}", "some_dest", block_size=DEFAULT_BLOCK_SIZE)
        ]

        self.assertEqual(mock_copy.call_count, 3)
        mock_copy.assert_has_calls(expected_copy_calls)

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    @mock.patch("ESSArch_Core.ip.models.InformationPackage")
    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    def test_read_container_no_xml(self, mock_copy, mock_ip, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()
        full_path_to_src = "the/full/path/to/src"
        container_path = "container/path"

        mock_storage_obj.container = True
        mock_storage_obj.get_full_path.return_value = full_path_to_src
        mock_storage_obj.storage_medium.storage_target.target = container_path
        mock_storage_obj.ip = mock_ip
        mock_ip.aic.pk = 1234

        disk_storage_backend.read(
            storage_object=mock_storage_obj,
            dst="some_dest",
            include_xml=False
        )

        mock_copy.assert_called_once_with(f"{full_path_to_src}", "some_dest", block_size=DEFAULT_BLOCK_SIZE)

    @mock.patch("ESSArch_Core.storage.backends.disk.DiskStorageBackend._extract")
    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    @mock.patch("ESSArch_Core.ip.models.InformationPackage")
    @mock.patch("ESSArch_Core.storage.backends.disk.copy")
    def test_read_container_extract(self, mock_copy, mock_ip, mock_storage_obj, mock_extract):
        disk_storage_backend = DiskStorageBackend()
        full_path_to_src = "the/full/path/to/src"
        container_path = "container/path"

        mock_storage_obj.container = True
        mock_storage_obj.get_full_path.return_value = full_path_to_src
        mock_storage_obj.storage_medium.storage_target.target = container_path
        mock_storage_obj.ip = mock_ip
        mock_ip.aic.pk = 1234

        disk_storage_backend.read(
            storage_object=mock_storage_obj,
            dst="some_dest",
            extract=True
        )

        expected_copy_calls = [
            mock.call(f"{full_path_to_src}.xml", "some_dest", block_size=DEFAULT_BLOCK_SIZE),
            mock.call(os.path.join(container_path, "1234.xml"), "some_dest", block_size=DEFAULT_BLOCK_SIZE),
        ]

        self.assertEqual(mock_copy.call_count, 2)
        mock_copy.assert_has_calls(expected_copy_calls)
        mock_extract.assert_called_once_with(mock_storage_obj, "some_dest")

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    def test_delete(self, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()
        mock_storage_obj.container = False
        mock_storage_obj.content_location_value = self.datadir

        self.assertTrue(os.path.exists(self.datadir))

        disk_storage_backend.delete(mock_storage_obj)

        self.assertFalse(os.path.exists(self.datadir))

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    def test_delete_container(self, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()

        aic_pk = 1234
        archive_filename = "archive_file"
        xml_file = self.create_file(archive_filename, "xml")
        aic_xml = self.create_file(aic_pk, "xml")
        tar_path = self.create_container_files(archive_filename, "tar")

        mock_storage_obj.container = True
        mock_storage_obj.ip.aic.pk = aic_pk
        mock_storage_obj.content_location_value = tar_path

        self.assertTrue(os.path.exists(xml_file))
        self.assertTrue(os.path.exists(aic_xml))
        self.assertTrue(os.path.exists(tar_path))

        disk_storage_backend.delete(mock_storage_obj)

        self.assertFalse(os.path.exists(xml_file))
        self.assertFalse(os.path.exists(aic_xml))
        self.assertFalse(os.path.exists(tar_path))

    @mock.patch("ESSArch_Core.storage.models.StorageObject")
    def test_extract(self, mock_storage_obj):
        disk_storage_backend = DiskStorageBackend()

        self.create_file(1234, "xml", "aic_xml content")
        self.create_file("dummy", "xml", "xml_file content")
        self.create_file("dummy", "txt", "dummy text content")
        tar_path = self.create_container_files("archive_file", "tar")
        mock_storage_obj.get_full_path.return_value = tar_path

        dst = os.path.join(self.datadir, "extract_to_path")
        self.assertFalse(os.path.exists(dst))
        os.makedirs(dst)
        self.assertTrue(os.path.exists(dst))

        self.assertTrue(os.listdir(dst) == [])

        disk_storage_backend._extract(mock_storage_obj, dst)

        expected_extracted_file_paths = [os.path.join(dst, f) for f in ["1234.xml", "dummy.xml", "dummy.txt"]]
        for file_path in expected_extracted_file_paths:
            self.assertTrue(os.path.exists(file_path) and os.path.isfile(file_path))
