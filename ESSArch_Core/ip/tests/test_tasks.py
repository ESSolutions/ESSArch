import os
import shutil
import tarfile
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from ESSArch_Core.configuration.models import EventType, Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import Profile, ProfileIP, ProfileIPData
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.util import normalize_path
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask

User = get_user_model()


class CreateContainerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='temp', value='temp')
        EventType.objects.create(eventType=50400, category=EventType.CATEGORY_INFORMATION_PACKAGE)
        cls.user = User.objects.create()

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        self.ip = InformationPackage.objects.create()

    def create_profile(self, data, ip):
        profile = Profile.objects.create(profile_type='transfer_project')
        profile_ip = ProfileIP.objects.create(profile=profile, ip=ip)
        profile_ip_data = ProfileIPData.objects.create(relation=profile_ip, data=data, user=self.user)
        profile_ip.data = profile_ip_data
        profile_ip.save()

        return profile

    @TaskRunner()
    def test_create_tar(self):
        root = tempfile.mkdtemp(dir=self.datadir)
        foo = os.path.join(root, 'foo')
        os.makedirs(foo)
        bar = os.path.join(root, 'bar')
        os.makedirs(bar)
        open(os.path.join(foo, '1.txt'), 'a').close()

        dst = os.path.join(self.datadir, 'container.tar')

        self.create_profile({'container_format': 'tar'}, self.ip)

        task = ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.CreateContainer',
            information_package=self.ip,
            responsible=self.user,
            args=[root, dst]
        )
        task.run().get()

        root_base = os.path.basename(root)
        expected = [
            root_base,
            os.path.join(root_base, 'foo'),
            os.path.join(root_base, 'foo/1.txt'),
            os.path.join(root_base, 'bar'),
        ]
        expected = [normalize_path(x) for x in expected]
        with tarfile.open(dst) as tar:
            self.assertCountEqual(expected, tar.getnames())


class CreateReceiptTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email="user@example.com")
        Path.objects.create(entity="temp")

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        self.ip = InformationPackage.objects.create()

    @TaskRunner()
    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_step(self, MockEmailMessage):
        step = ProcessStep.objects.create()
        ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.CreateReceipt',
            reference='xml1',
            information_package=self.ip,
            responsible=self.user,
            processstep=step,
            processstep_pos=0,
            args=[
                None,
                'xml',
                'receipts/xml.json',
                os.path.join(self.datadir, 'first_{% now "ymdHis" %}.xml'),
                'success',
                'short msg',
                'msg',
            ],
        )
        ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.CreateReceipt',
            reference='xml2',
            information_package=self.ip,
            responsible=self.user,
            processstep=step,
            processstep_pos=1,
            args=[
                None,
                'xml',
                'receipts/xml.json',
                os.path.join(self.datadir, 'second_{% now "ymdHis" %}.xml'),
                'success',
                'short msg',
                'msg'
            ],
        )
        ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.CreateReceipt',
            reference='email',
            information_package=self.ip,
            responsible=self.user,
            processstep=step,
            processstep_pos=2,
            args=[None, 'email', 'receipts/email.txt', None, 'success', 'short msg', 'msg'],
            result_params={
                'attachments': ['xml2', 'xml1']
            }
        )
        step.run().get()
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            [self.user.email],
        )

        MockEmailMessage.return_value.attach_file.assert_has_calls([
            mock.call(ProcessTask.objects.values_list('result', flat=True).get(reference='xml2')),
            mock.call(ProcessTask.objects.values_list('result', flat=True).get(reference='xml1')),
        ])
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)


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
