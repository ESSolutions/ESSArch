import os
import shutil
import tempfile
import uuid
from unittest import TestCase, mock

from ESSArch_Core.configuration.models import Parameter
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.models import (
    DISK,
    TAPE,
    CAS,
    get_storage_type_from_medium_type,
    medium_type_CHOICES,
    StorageTarget,
    StorageMedium, TapeSlot, Robot, StorageObject)
from ESSArch_Core.util import normalize_path


class GetStorageTypeFromMediumTypeTests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.medium_choices = [e[0] for e in medium_type_CHOICES]

    def test_all_medium_types_for_storage_type_DISK(self):

        for medium_type in range(200, 300):
            if medium_type in self.medium_choices:
                self.assertEqual(get_storage_type_from_medium_type(medium_type), DISK)

    def test_all_medium_types_for_storage_type_TAPE(self):
        for medium_type in range(300, 400):
            if medium_type in self.medium_choices:
                self.assertEqual(get_storage_type_from_medium_type(medium_type), TAPE)

    def test_all_medium_types_for_storage_type_CAS(self):
        for medium_type in range(0, 200):
            if medium_type in self.medium_choices:
                self.assertEqual(get_storage_type_from_medium_type(medium_type), CAS)
        for medium_type in range(400, 500):
            if medium_type in self.medium_choices:
                self.assertEqual(get_storage_type_from_medium_type(medium_type), CAS)


class StorageTargetCreateStorageMediumTests(TestCase):

    def setUp(self):
        self.medium_location_param = Parameter.objects.create(entity='medium_location', value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity='agent_identifier_value', value="dummy_agent_id")

    def tearDown(self):
        self.medium_location_param.delete()
        self.agent_id_param.delete()

    def test_when_no_storage_medium_exists_should_create_new_StorageMedium_for_DISK(self):
        storage_target_name = f'dummy_st_name_{uuid.uuid4()}'
        storage_target = StorageTarget.objects.create(
            type=DISK,
            name=storage_target_name
        )

        medium = storage_target._create_storage_medium()

        # Make sure its persisted
        persisted_storage_medium = StorageMedium.objects.filter(storage_target=storage_target).first()
        self.assertEqual(persisted_storage_medium, medium)

        self.assertEqual(medium.location, 'dummy_medium_location')
        self.assertEqual(medium.agent, 'dummy_agent_id')
        self.assertEqual(medium.tape_slot, None)
        self.assertEqual(medium.medium_id, storage_target_name)

    def test_when_no_storage_medium_exists_should_create_new_StorageMedium_for_TAPE(self):
        robot = Robot.objects.create(device='slot_robot_device')
        tape_slot = TapeSlot.objects.create(slot_id=12, robot=robot, medium_id='st_target_with_more_chars')
        storage_target_name = f'dummy_st_name_{uuid.uuid4()}'
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=storage_target_name,
            target='st_target'
        )

        medium = storage_target._create_storage_medium()

        # Make sure its persisted
        persisted_storage_medium = StorageMedium.objects.filter(storage_target=storage_target).first()
        self.assertEqual(persisted_storage_medium, medium)

        self.assertEqual(medium.location, 'dummy_medium_location')
        self.assertEqual(medium.agent, 'dummy_agent_id')
        self.assertEqual(medium.tape_slot, tape_slot)
        self.assertEqual(medium.medium_id, 'st_target_with_more_chars')

    def test_when_no_StorageMedium_nor_Slot_exists_for_TAPE_should_raise_exception(self):
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )

        with self.assertRaisesRegex(ValueError, "No tape available for allocation"):
            storage_target.get_or_create_storage_medium()

    def test_when_support_for_storage_type_is_not_implemented_should_raise_NotImplementedError_exception(self):
        storage_target = StorageTarget.objects.create(
            type=CAS,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )

        with self.assertRaises(NotImplementedError):
            storage_target.get_or_create_storage_medium()


class StorageTargetGetOrCreateStorageMediumTests(TestCase):

    def setUp(self):
        self.medium_location_param = Parameter.objects.create(entity='medium_location', value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity='agent_identifier_value', value="dummy_agent_id")

    def tearDown(self):
        self.medium_location_param.delete()
        self.agent_id_param.delete()
        StorageMedium.objects.all().delete()

    def create_storage_medium(self, storage_target):
        return StorageMedium.objects.create(
            medium_id=f"some_name_{uuid.uuid4()}",
            storage_target=storage_target,
            status=20,
            location_status=50,
            location=self.medium_location_param.value,
            block_size=storage_target.default_block_size,
            format=storage_target.default_format,
            agent=self.agent_id_param.value,
        )

    @mock.patch('ESSArch_Core.storage.models.StorageTarget._create_storage_medium')
    def test_when_qs_is_None_and_no_StorageMedium_exists_then_create(self, mock_create_storage_medium):
        mock_create_storage_medium.return_value = "Dummy_medium"
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )

        medium, created = storage_target.get_or_create_storage_medium(None)

        self.assertEqual(medium, "Dummy_medium")
        self.assertEqual(created, True)

    @mock.patch('ESSArch_Core.storage.models.StorageTarget._create_storage_medium')
    def test_when_called_with_no_params_and_no_StorageMedium_exists_then_create(self, mock_create_storage_medium):
        mock_create_storage_medium.return_value = "Dummy_medium"
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )

        medium, created = storage_target.get_or_create_storage_medium()

        self.assertEqual(medium, "Dummy_medium")
        self.assertEqual(created, True)

    def test_when_qs_is_None_but_StorageMedium_exists_and_found_then_return_medium_from_DB(self):
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )
        storage_medium = self.create_storage_medium(storage_target)

        medium, created = storage_target.get_or_create_storage_medium()

        self.assertEqual(medium, storage_medium)
        self.assertEqual(created, False)

    @mock.patch('ESSArch_Core.storage.models.StorageTarget._create_storage_medium')
    def test_when_qs_is_None_and_StorageMedium_is_not_found_then_return_medium_from_DB(self, mock_create_sm):
        mock_create_sm.return_value = "dummy_medium"
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )
        some_other_storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target_2'
        )
        self.create_storage_medium(some_other_storage_target)
        medium, created = storage_target.get_or_create_storage_medium()

        self.assertEqual(medium, "dummy_medium")
        self.assertEqual(created, True)

    def test_when_qs_is_passed_as_parameter_then_return_medium_from_DB(self):
        storage_target = StorageTarget.objects.create(
            type=TAPE,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target='st_target'
        )
        storage_medium = self.create_storage_medium(storage_target)

        qs = StorageMedium.objects.all()
        medium, created = storage_target.get_or_create_storage_medium(qs)

        self.assertEqual(medium, storage_medium)
        self.assertEqual(created, False)


class StorageTargetGetStorageBackendTests(TestCase):

    def test_get_storage_backend(self):
        storage_target_disk = StorageTarget.objects.create(type=DISK, name=f'dummy_st_name_{uuid.uuid4()}')
        storage_target_tape = StorageTarget.objects.create(type=TAPE, name=f'dummy_st_name_{uuid.uuid4()}')
        storage_target_cas = StorageTarget.objects.create(type=CAS, name=f'dummy_st_name_{uuid.uuid4()}')

        self.assertEqual(type(storage_target_disk.get_storage_backend()).__name__, 'DiskStorageBackend')
        self.assertEqual(type(storage_target_tape.get_storage_backend()).__name__, 'TapeStorageBackend')

        # TODO: Currently we need to set the AWS configurations before importing the s3 package.
        from django.conf import settings
        settings.AWS = {
            'ACCESS_KEY_ID': 'some_access_key_id',
            'SECRET_ACCESS_KEY': 'some_access_key_secret',
            'ENDPOINT_URL': 'https://some.aws.endpoint/'
        }
        self.assertEqual(type(storage_target_cas.get_storage_backend()).__name__, 'S3StorageBackend')


class StorageTargetStrTests(TestCase):

    def test_get_str_when_name_is_empty_string_should_return_id_as_string(self):
        storage_target_disk = StorageTarget.objects.create(name="")

        self.assertEqual(storage_target_disk.__str__(), str(storage_target_disk.pk))

    def test_get_str_when_name_is_non_empty_string_should_return_it(self):
        storage_target_disk = StorageTarget.objects.create(name="some_name")

        self.assertEqual(storage_target_disk.__str__(), "some_name")


class StorageObjectGetRootTests(TestCase):

    def setUp(self):
        self.medium_location_param = Parameter.objects.create(entity='medium_location', value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity='agent_identifier_value', value="dummy_agent_id")
        self.ip = InformationPackage.objects.create()
        self.storage_target = StorageTarget.objects.create(
            type=DISK,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target="my_storage_target"
        )
        self.storage_medium = StorageMedium.objects.create(
            medium_id=f"some_name_{uuid.uuid4()}",
            storage_target=self.storage_target,
            status=20,
            location_status=50,
            location=self.medium_location_param.value,
            block_size=self.storage_target.default_block_size,
            format=self.storage_target.default_format,
            agent=self.agent_id_param.value,
        )

    def tearDown(self):
        self.medium_location_param.delete()
        self.agent_id_param.delete()

    def test_when_content_location_value_is_empty_string_and_not_container(self):
        storage_object = StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value='',
            container=False,
        )

        expected_root_path = os.path.join("my_storage_target", self.ip.object_identifier_value)
        self.assertEqual(storage_object.get_root(), expected_root_path)

    def test_when_content_location_value_is_empty_string_and_its_a_container(self):
        storage_object = StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value='',
            container=True,
        )

        expected_root_path = os.path.join("my_storage_target", self.ip.object_identifier_value) + ".tar"
        self.assertEqual(storage_object.get_root(), expected_root_path)

    def test_when_content_location_value_is_not_empty_string(self):
        storage_object = StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value='the_content_location_value',
            container=False,
        )

        expected_root_path = os.path.join("my_storage_target", "the_content_location_value")
        self.assertEqual(storage_object.get_root(), expected_root_path)


class StorageObjectOpenTests(TestCase):

    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.datadir)

        self.medium_location_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_agent_id")

        self.ip = InformationPackage.objects.create()
        self.storage_target = StorageTarget.objects.create(
            type=DISK,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target="my_storage_target",
        )
        self.storage_medium = StorageMedium.objects.create(
            medium_id=f"some_name_{uuid.uuid4()}",
            storage_target=self.storage_target,
            status=20,
            location_status=50,
            location=self.medium_location_param.value,
            block_size=self.storage_target.default_block_size,
            format=self.storage_target.default_format,
            agent=self.agent_id_param.value,
        )

    def create_storage_object(self, is_container):
        return StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value=self.datadir,
            container=is_container,
        )

    def create_file_with_content(self, file_name, content):
        with open(os.path.join(self.datadir, file_name), 'w') as f:
            f.write(content)
        return f.name

    def test_open_if_its_not_a_container_then_open_from_backend(self):
        file_name = self.create_file_with_content("some_file_to_read", "the content")
        storage_object = self.create_storage_object(False)

        res = storage_object.open(file_name)

        self.assertEqual(res.name, file_name)

    @mock.patch("ESSArch_Core.storage.models.StorageObject.extract")
    def test_open_if_its_a_container_then_extract_and_open(self, mock_extract):
        file_name = self.create_file_with_content("some_file_to_read", "the content")
        storage_object_container = self.create_storage_object(True)
        storage_object = self.create_storage_object(False)
        storage_object_container.extract.return_value = storage_object

        res = storage_object_container.open(file_name)

        self.assertEqual(res.name, file_name)
        mock_extract.assert_called_once()


class StorageObjectReadTests(TestCase):

    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.datadir)

        self.medium_location_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_agent_id")

        self.ip = InformationPackage.objects.create()
        self.storage_target = StorageTarget.objects.create(
            type=DISK,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target="my_storage_target",
        )
        self.storage_medium = StorageMedium.objects.create(
            medium_id=f"some_name_{uuid.uuid4()}",
            storage_target=self.storage_target,
            status=20,
            location_status=50,
            location=self.medium_location_param.value,
            block_size=self.storage_target.default_block_size,
            format=self.storage_target.default_format,
            agent=self.agent_id_param.value,
        )

    def create_storage_object(self, is_container):
        return StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value=self.datadir,
            container=is_container,
        )

    def create_file_with_content(self, file_name, content):
        with open(os.path.join(self.datadir, file_name), 'w') as f:
            f.write(content)
        return f.name

    def test_read_if_its_not_a_container_then_read_file(self):
        file_name = self.create_file_with_content("some_file_to_read", "the content")

        storage_object = self.create_storage_object(False)

        res = storage_object.read(file_name)
        self.assertEqual(res, "the content")

    @mock.patch("ESSArch_Core.storage.models.StorageObject.extract")
    def test_read_if_its_a_container_then_extract_and_then_read_file(self, mock_extract):
        file_name = self.create_file_with_content("some_file_to_read", "the content")
        storage_object_container = self.create_storage_object(True)
        storage_object = self.create_storage_object(False)
        storage_object_container.extract.return_value = storage_object

        res = storage_object_container.read(file_name)
        self.assertEqual(res, "the content")

        mock_extract.assert_called_once()


class StorageObjectDeleteFilesTests(TestCase):

    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.subdir = os.path.join(self.datadir, "subdir")
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.subdir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.medium_location_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_medium_location")
        self.agent_id_param = Parameter.objects.create(entity=str(uuid.uuid4()), value="dummy_agent_id")

        self.ip = InformationPackage.objects.create()
        self.storage_target = StorageTarget.objects.create(
            type=DISK,
            name=f'dummy_st_name_{uuid.uuid4()}',
            target="my_storage_target",
        )
        self.storage_medium = StorageMedium.objects.create(
            medium_id=f"some_name_{uuid.uuid4()}",
            storage_target=self.storage_target,
            status=20,
            location_status=50,
            location=self.medium_location_param.value,
            block_size=self.storage_target.default_block_size,
            format=self.storage_target.default_format,
            agent=self.agent_id_param.value,
        )

    def create_storage_object(self, is_container):
        return StorageObject.objects.create(
            content_location_type=DISK,
            ip=self.ip,
            storage_medium=self.storage_medium,
            content_location_value=self.subdir,
            container=is_container,
        )

    def create_file_with_content(self, file_name, content):
        with open(os.path.join(self.subdir, file_name), 'w') as f:
            f.write(content)
        return f.name

    def test_delete_file_success(self):
        file_name = self.create_file_with_content("some_file_to_delete", "the content")
        storage_object = self.create_storage_object(False)

        self.assertTrue(os.path.isfile(file_name))

        storage_object.delete_files()

        self.assertFalse(os.path.isfile(file_name))
