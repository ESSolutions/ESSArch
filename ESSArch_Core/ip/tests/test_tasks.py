from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class PreserveInformationPackageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='temp', value='temp')

    def setUp(self):
        self.cache_storage = StorageMethod.objects.create()
        self.storage_policy = StoragePolicy.objects.create(
            cache_storage=self.cache_storage,
            ingest_path=Path.objects.create(),
        )

        self.user = User.objects.create()
        self.ip = InformationPackage.objects.create(policy=self.storage_policy, object_path='foo/bar')

    @TaskRunner()
    @mock.patch.object(InformationPackage, 'preserve', return_value=None)
    def test_no_writeable_target(self, mock_preserve):
        storage_method = StorageMethod.objects.create()
        with self.assertRaises(ValueError):
            ProcessTask.objects.create(
                name='ESSArch_Core.ip.tasks.PreserveInformationPackage',
                information_package=self.ip,
                responsible=self.user,
                args=[storage_method.pk]
            ).run().get()

        mock_preserve.assert_not_called()

    @TaskRunner()
    @mock.patch.object(InformationPackage, 'preserve')
    def test_success(self, mock_preserve):
        mock_preserve.return_value = '123'
        storage_method = StorageMethod.objects.create()
        storage_target = StorageTarget.objects.create()
        StorageMethodTargetRelation.objects.create(
            storage_method=storage_method,
            storage_target=storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        self.storage_policy.storage_methods.add(storage_method)

        task = ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.PreserveInformationPackage',
            information_package=self.ip,
            responsible=self.user,
            args=[storage_method.pk]
        )
        task.run().get()

        mock_preserve.assert_called_once_with([self.ip.object_path], storage_target, False, task)
