import datetime
import os
import shutil
import tempfile
import uuid

from unittest import mock
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from celery import states as celery_state

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.ip.models import InformationPackage, Agent, Workarea
from ESSArch_Core.util import normalize_path, timestamp_to_datetime


class InformationPackageListFilesTests(TestCase):
    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.textdir = os.path.join(self.datadir, "textdir")
        self.addCleanup(shutil.rmtree, self.datadir)
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

    def create_files(self):
        try:
            os.makedirs(self.textdir)
        except OSError as e:
            if e.errno != 17:
                raise

        files = []
        for i in range(3):
            fname = os.path.join(self.textdir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        return files

    def create_archive_file(self, archive_format):
        self.create_files()

        output_filename = "archive_file"
        archive_file_full_path = os.path.join(self.datadir, output_filename)

        return shutil.make_archive(archive_file_full_path, archive_format, self.textdir)

    def create_mets_xml_file(self, filename):
        dirname = os.path.join(self.datadir, os.path.dirname(filename))
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fname = os.path.join(self.datadir, '%s' % filename)
        with open(fname, 'w') as f:
            f.write("I'm a mets_xml")

        return fname

    def test_list_file(self):
        fd, path = tempfile.mkstemp(dir=self.datadir)
        os.close(fd)
        self.assertEqual(
            self.ip.list_files(),
            [{
                'type': 'file',
                'name': os.path.basename(path),
                'size': 0,
                'modified': timestamp_to_datetime(os.stat(path).st_mtime)
            }]
        )

    def test_list_folder(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        self.assertEqual(
            self.ip.list_files(),
            [{
                'type': 'dir',
                'name': os.path.basename(path),
                'size': 0,
                'modified': timestamp_to_datetime(os.stat(path).st_mtime)
            }]
        )

    def test_list_folder_content(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        fd, filepath = tempfile.mkstemp(dir=path)
        os.close(fd)
        self.assertEqual(
            self.ip.list_files(path=path),
            [{
                'type': 'file',
                'name': os.path.basename(filepath),
                'size': os.stat(filepath).st_size,
                'modified': timestamp_to_datetime(os.stat(filepath).st_mtime)
            }]
        )

    def test_list_files_tar_file_should_return_entries(self):
        archive_path = self.create_archive_file('tar')
        self.ip.object_path = archive_path
        self.ip.save()

        entries = self.ip.list_files(path='archive_file.tar')
        self.assertEqual(len(entries), 3)

        # FIXME: remove ./ when issue is fixed https://bugs.python.org/issue35964
        file_names = ['./0.txt', './1.txt', './2.txt']

        for e in entries:
            self.assertIn(e['name'], file_names)
            file_names.remove(e['name'])
            self.assertEqual(e['type'], 'file')
            self.assertEqual(e['size'], 1)
            self.assertEqual(type(e['modified']), datetime.datetime)

    def test_list_files_zip_file_should_return_entries(self):
        archive_path = self.create_archive_file('zip')
        self.ip.object_path = archive_path
        self.ip.save()

        entries = self.ip.list_files(path='archive_file.zip')
        self.assertEqual(len(entries), 3)

        file_names = ['0.txt', '1.txt', '2.txt']

        for e in entries:
            self.assertIn(e['name'], file_names)
            file_names.remove(e['name'])
            self.assertEqual(e['type'], 'file')
            self.assertEqual(e['size'], 1)
            self.assertEqual(type(e['modified']), datetime.datetime)

    def test_list_root_folder_with_no_params(self):
        archive_path = self.create_archive_file('tar')
        self.ip.object_path = archive_path
        self.ip.save()

        entries = self.ip.list_files(path='')

        self.assertEqual(
            entries,
            [{
                'type': 'file',
                'name': os.path.basename(archive_path),
                'size': os.path.getsize(archive_path),
                'modified': timestamp_to_datetime(os.stat(archive_path).st_mtime)
            }]
        )

    def test_list_root_folder_when_xml_exists_with_no_params(self):
        archive_path = self.create_archive_file('tar')
        xml_path = self.create_mets_xml_file('archive_file.xml')
        self.ip.object_path = archive_path
        self.ip.save()

        entries = self.ip.list_files(path='')

        self.assertEqual(
            entries,
            [{
                'type': 'file',
                'name': os.path.basename(archive_path),
                'size': os.path.getsize(archive_path),
                'modified': timestamp_to_datetime(os.stat(archive_path).st_mtime)
            }, {
                'type': 'file',
                'name': os.path.basename(xml_path),
                'size': os.path.getsize(xml_path),
                'modified': timestamp_to_datetime(os.stat(xml_path).st_mtime)
            }]
        )

    def test_list_multiple_files_in_folder(self):
        archive_path = self.create_archive_file('tar')
        self.ip.object_path = archive_path
        self.ip.save()

        files = [f for f in os.listdir(self.textdir) if os.path.isfile(os.path.join(self.textdir, f))]
        expected_entries = []
        for f in files:
            expected_entries.append(
                {
                    'type': 'file',
                    'name': f,
                    'size': 1,
                    'modified': timestamp_to_datetime(os.stat(os.path.join(self.textdir, f)).st_mtime)
                }
            )

        entries = self.ip.list_files(path=self.textdir)

        self.assertCountEqual(entries, expected_entries)
        self.assertEqual(len(entries), 3)


class GetPathResponseTests(TestCase):
    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.ip = InformationPackage.objects.create(object_path=self.datadir)
        self.request = APIRequestFactory()

        self.addCleanup(shutil.rmtree, self.datadir)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.generate_file_response')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_file(self, mock_fid, mock_gen_file_resp, mock_open_file):
        fd, path = tempfile.mkstemp(dir=self.datadir)
        os.close(fd)
        relpath = os.path.relpath(path, self.datadir)

        response = self.ip.get_path_response(relpath, self.request)
        response.close()

        mocked_file = mock_open_file.return_value
        mocked_mimetype = mock_fid.return_value.get_mimetype.return_value
        mock_gen_file_resp.assert_called_once_with(mocked_file, mocked_mimetype, force_download=False, name=relpath)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.list_files')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_folder(self, mock_fid, mock_list_files):
        path = tempfile.mkdtemp(dir=self.datadir)

        relpath = os.path.basename(path)
        response = self.ip.get_path_response(relpath, self.request)
        response.close()
        mock_list_files.assert_called_once_with(relpath)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.generate_file_response')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_file_in_folder(self, mock_fid, mock_gen_file_resp, mock_open_file):
        path = tempfile.mkdtemp(dir=self.datadir)
        fd, filepath = tempfile.mkstemp(dir=path)
        os.close(fd)
        relpath = os.path.relpath(filepath, self.datadir)

        response = self.ip.get_path_response(os.path.relpath(filepath, self.datadir), self.request)
        response.close()

        mocked_file = mock_open_file.return_value
        mocked_mimetype = mock_fid.return_value.get_mimetype.return_value
        mock_gen_file_resp.assert_called_once_with(mocked_file, mocked_mimetype, force_download=False, name=relpath)


class GetPathResponseContainerTests(TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(delete=False)
        self.file.close()
        self.file = normalize_path(self.file.name)
        self.ip = InformationPackage.objects.create(object_path=self.file)
        self.request = APIRequestFactory()

        self.addCleanup(os.remove, self.file)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.InformationPackage.list_files')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_list_files_in_ip_container(self, mock_fid, mock_list_files, mock_open_file):
        path = os.path.basename(self.file)
        response = self.ip.get_path_response(path, self.request)
        response.close()

        mock_open_file.return_value
        mock_fid.return_value.get_mimetype.return_value
        mock_list_files.assert_called_once_with(path)


class StatusTest(TestCase):

    def setUp(self):
        self.ip = InformationPackage.objects.create()

    def test_status_is_100_when_state_is_any_completed_state(self):
        completed_states = ["Prepared", "Uploaded", "Created", "Submitted", "Received", "Transferred", 'Archived']

        for state in completed_states:
            self.ip.state = state
            self.assertEqual(self.ip.status(), 100)

    def test_status_is_33_when_state_is_preparing_and_submission_agreement_is_not_locked(self):
        self.ip.state = 'Preparing'
        self.ip.submission_agreement_locked = False

        self.assertEqual(self.ip.status(), 33)

    def test_status_is_between_66_and_100_when_state_is_preparing_and_submission_agreement_is_locked(self):
        self.ip.state = 'Preparing'
        self.ip.submission_agreement_locked = True

        status = self.ip.status()
        self.assertGreaterEqual(status, 66)
        self.assertLessEqual(status, 100)

    def test_status_is_100_if_state_is_None(self):
        self.ip.state = None

        self.assertEqual(self.ip.status(), 100)

    def test_status_is_100_if_state_is_an_unhandled_type(self):
        self.ip.state = uuid.uuid4()

        self.assertEqual(self.ip.status(), 100)


class InformationPackageOpenFileTests(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.textdir = os.path.join(self.datadir, "textdir")
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.textdir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.ip = InformationPackage.objects.create()

    def create_files(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.textdir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        return files

    def create_mets_xml_file(self, filename):
        dirname = os.path.join(self.textdir, os.path.dirname(filename))
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fname = os.path.join(self.textdir, '%s' % filename)
        with open(fname, 'w') as f:
            f.write("I'm a mets_xml")

    def create_archive_file(self, archive_format):
        self.create_files()

        output_filename = "archive_file"
        archive_file_full_path = os.path.join(self.datadir, output_filename)

        return shutil.make_archive(archive_file_full_path, archive_format, self.textdir)

    @mock.patch('ESSArch_Core.ip.models.open')
    def test_open_file_with_default_params_should_call_open_of_object_path(self, mock_open):
        self.ip.object_path = os.path.join(self.datadir, "")

        self.ip.open_file()

        mock_open.assert_called_once_with(self.ip.object_path)

    def test_open_file_with_default_params_and_object_path_is_not_set_should_raise_FileNotFoundError(self):
        with self.assertRaises(FileNotFoundError):
            self.ip.open_file()

    @mock.patch('ESSArch_Core.ip.models.open')
    def test_open_file_when_object_path_is_a_file_and_equal_to_path_then_open_it(self, mock_open):
        archive_file = self.create_archive_file('tar')
        self.ip.object_path = archive_file
        self.ip.save()

        self.ip.open_file(archive_file)

        mock_open.assert_called_once_with(archive_file)

    @mock.patch('ESSArch_Core.ip.models.open')
    def test_open_file_when_xml_mets_exists_then_open_it(self, mock_open):
        archive_file = self.create_archive_file('tar')
        self.ip.object_path = archive_file
        self.ip.package_mets_path = os.path.join(os.path.dirname(archive_file), 'mets.xml')
        self.ip.save()

        self.ip.open_file(self.ip.package_mets_path)

        mock_open.assert_called_once_with(self.ip.package_mets_path)

    @mock.patch('ESSArch_Core.ip.models.open')
    def test_open_file_when_mets_path_not_set_then_generate_path_from_identifier_value(self, mock_open):
        archive_file = self.create_archive_file('tar')
        self.ip.object_path = archive_file
        self.ip.object_identifier_value = "mets"
        self.ip.save()
        path_to_mets_xml = os.path.join(os.path.dirname(archive_file), 'mets.xml')

        self.ip.open_file(path_to_mets_xml)

        mock_open.assert_called_once_with(path_to_mets_xml)

    @mock.patch('ESSArch_Core.ip.models.io')
    def test_open_file_when_mets_path_not_set_then_read_mets_xml_from_tar(self, mocked_io):
        self.create_mets_xml_file("mets.xml")
        archive_file = self.create_archive_file('tar')
        self.ip.object_path = archive_file
        self.ip.object_identifier_value = "identifier_value_that_does_not_match_mets_file_name"
        self.ip.save()

        self.ip.open_file('./mets.xml')

        mocked_io.BytesIO.assert_called_once()

    @mock.patch('ESSArch_Core.ip.models.io')
    def test_open_file_when_mets_path_not_set_then_read_mets_xml_from_tar_with_identifier(self, mocked_io):
        self.create_mets_xml_file("mets_folder/mets.xml")
        archive_file = self.create_archive_file('tar')
        self.ip.object_path = archive_file
        self.ip.object_identifier_value = "./mets_folder/"
        self.ip.save()

        self.ip.open_file('mets.xml')

        mocked_io.BytesIO.assert_called_once()

    @mock.patch('ESSArch_Core.ip.models.io')
    def test_open_file_when_mets_path_not_set_then_read_mets_xml_from_zip(self, mocked_io):
        self.create_mets_xml_file("mets_folder/mets.xml")
        archive_file = self.create_archive_file('zip')
        self.ip.object_path = archive_file
        self.ip.object_identifier_value = "mets_folder/"
        self.ip.save()

        self.ip.open_file('mets.xml')

        mocked_io.BytesIO.assert_called_once()


class InformationPackageStepStateTests(TestCase):

    def create_information_package(self, num, aic, package_type=InformationPackage.AIP):
        ip_set = set()
        for i in range(num):
            ip_set.add(
                InformationPackage.objects.create(label=i, package_type=package_type, aic=aic)
            )

        return ip_set

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.related_ips')
    def test_step_state_when_its_an_AIC_with_no_related_IPs_then_success(self, mocked_related_ips):
        self.ip = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        mocked_related_ips.return_value = set()
        state = self.ip.step_state

        self.assertEqual(state, celery_state.SUCCESS)
        mocked_related_ips.assert_called_once()

    def test_step_state_when_its_an_AIC_with_3_related_IPs_then_success(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        ip_set = self.create_information_package(3, aic)
        for ip in ip_set:
            ProcessTask.objects.create(information_package=ip, status=celery_state.SUCCESS)

        state = aic.step_state
        self.assertEqual(state, celery_state.SUCCESS)

    def test_step_state_when_its_an_AIC_with_3_related_IPs_with_one_task_started_then_started(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        ip_set = self.create_information_package(3, aic)
        statuses = [celery_state.SUCCESS, celery_state.STARTED, celery_state.SUCCESS]

        for idx, ip in enumerate(ip_set):
            ProcessTask.objects.create(information_package=ip, status=statuses[idx])

        state = aic.step_state
        self.assertEqual(state, celery_state.STARTED)

    def test_step_state_when_its_an_AIC_with_3_related_IPs_with_one_task_pending_then_pending(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        ip_set = self.create_information_package(3, aic)
        statuses = [celery_state.SUCCESS, celery_state.PENDING, celery_state.SUCCESS]

        for idx, ip in enumerate(ip_set):
            ProcessTask.objects.create(information_package=ip, status=statuses[idx])

        state = aic.step_state
        self.assertEqual(state, celery_state.PENDING)

    def test_step_state_when_its_an_AIC_with_3_related_IPs_with_one_task_failure_then_failure(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        ip_set = self.create_information_package(3, aic)
        statuses = [celery_state.SUCCESS, celery_state.FAILURE, celery_state.SUCCESS]

        for idx, ip in enumerate(ip_set):
            ProcessTask.objects.create(information_package=ip, status=statuses[idx])

        state = aic.step_state
        self.assertEqual(state, celery_state.FAILURE)

    def test_step_state_when_its_an_AIP_with_no_tasks_then_success(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        state = aip.step_state
        self.assertEqual(state, celery_state.SUCCESS)

    def test_step_state_when_its_an_AIP_with_all_success_tasks_then_success(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        for i in range(3):
            ProcessTask.objects.create(information_package=aip, status=celery_state.SUCCESS)

        state = aip.step_state
        self.assertEqual(state, celery_state.SUCCESS)

    def test_step_state_when_its_an_AIP_with_one_task_started_then_started(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        statuses = [celery_state.SUCCESS, celery_state.STARTED, celery_state.SUCCESS]
        for status in statuses:
            ProcessTask.objects.create(information_package=aip, status=status)

        state = aip.step_state
        self.assertEqual(state, celery_state.STARTED)

    def test_step_state_when_its_an_AIP_with_one_task_pending_then_pending(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        statuses = [celery_state.SUCCESS, celery_state.PENDING, celery_state.SUCCESS]
        for status in statuses:
            ProcessTask.objects.create(information_package=aip, status=status)

        state = aip.step_state
        self.assertEqual(state, celery_state.PENDING)

    def test_step_state_when_its_an_AIP_with_one_task_failure_then_failure(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        statuses = [celery_state.SUCCESS, celery_state.FAILURE, celery_state.SUCCESS]
        for status in statuses:
            ProcessTask.objects.create(information_package=aip, status=status)

        state = aip.step_state
        self.assertEqual(state, celery_state.FAILURE)


class InformationPackageGetAgentTests(TestCase):

    def test_get_agent_when_role_does_not_exists_should_return_None(self):
        agent = Agent.objects.create(role="role_1", type="type_1", name="name_1", code="code_1")
        ip = InformationPackage.objects.create()
        ip.agents.add(agent)
        ip.save()

        self.assertEqual(ip.get_agent("non existent role", "type_1"), None)

    def test_get_agent_when_type_does_not_exists_should_return_None(self):
        agent = Agent.objects.create(role="role_1", type="type_1", name="name_1", code="code_1")
        ip = InformationPackage.objects.create()
        ip.agents.add(agent)
        ip.save()

        self.assertEqual(ip.get_agent("role_1", "non existing type"), None)

    def test_get_agent_when_exists_return_agent(self):
        agent = Agent.objects.create(role="role_1", type="type_1", name="name_1", code="code_1")
        ip = InformationPackage.objects.create()
        ip.agents.add(agent)
        ip.save()

        self.assertEqual(ip.get_agent("role_1", "type_1"), agent)

    def test_get_agent_when_multiple_agents_exists_return_agent(self):
        agent_1 = Agent.objects.create(role="role_1", type="type_1", name="name_1", code="code_1")
        agent_2 = Agent.objects.create(role="role_2", type="type_1", name="name_1", code="code_1")
        ip = InformationPackage.objects.create()
        ip.agents.add(agent_1)
        ip.agents.add(agent_2)
        ip.save()

        self.assertEqual(ip.get_agent("role_1", "type_1"), agent_1)
        self.assertEqual(ip.get_agent("role_2", "type_1"), agent_2)


class InformationPackageGetLockKeyTests(TestCase):

    def test_get_lock_key_success(self):
        ip = InformationPackage.objects.create()
        pk = ip.pk

        self.assertIsNotNone(ip.pk)
        self.assertEqual(ip.get_lock_key(), f'lock_ip_{pk}')


class InformationPackageIsLockedTests(TestCase):

    def test_is_locked_not_in_cache_should_return_False(self):
        ip = InformationPackage.objects.create()
        self.assertEqual(ip.is_locked(), False)


class InformationPackageGetChecksumAlgorithmTests(TestCase):

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_checksum_algorithm_when_SIP_then_get_from_profile_data(self, mock_profile_data):
        sip = InformationPackage.objects.create(package_type=InformationPackage.SIP)
        sip.profile_type = InformationPackage.SIP

        mock_profile_data.return_value = {'checksum_algorithm': 'DUMMY_ALGORITHM'}

        self.assertEqual(sip.get_checksum_algorithm(), "DUMMY_ALGORITHM")

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_checksum_algorithm_when_SIP_and_key_missing_in_profile_data_then_default(self, mock_profile_data):
        sip = InformationPackage.objects.create(package_type=InformationPackage.SIP)
        sip.profile_type = InformationPackage.SIP

        mock_profile_data.return_value = {}

        self.assertEqual(sip.get_checksum_algorithm(), "SHA-256")

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_checksum_algorithm_when_SIP_and_profile_data_is_None(self, mock_profile_data):
        sip = InformationPackage.objects.create(package_type=InformationPackage.SIP)
        sip.profile_type = InformationPackage.SIP

        mock_profile_data.return_value = None

        self.assertEqual(sip.get_checksum_algorithm(), "SHA-256")

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.policy')
    def test_get_checksum_algorithm_when_AIP_then_get_from_checksum_algo_display(self, mock_policy):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)
        aip.profile_type = None

        mock_policy.get_checksum_algorithm_display.return_value = "sho-257"

        self.assertEqual(aip.get_checksum_algorithm(), "SHO-257")

    def test_get_checksum_algorithm_when_profile_type_not_set_return_default(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        self.assertEqual(aip.get_checksum_algorithm(), "SHA-256")


class InformationPackageGetEmailRecipientTests(TestCase):

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_email_recipient_not_in_profile_data_should_return_None(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = {}

        self.assertEqual(ip.get_email_recipient(), None)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_email_recipient_when_profile_data_is_None_return_None(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = None

        self.assertEqual(ip.get_email_recipient(), None)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_email_recipient_get_from_profile_data(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = {'preservation_organization_receiver_email': 'some@email.com'}

        self.assertEqual(ip.get_email_recipient(), "some@email.com")


class InformationPackageGetContainerFormatTests(TestCase):

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_container_format_not_in_profile_return_tar(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = {}

        self.assertEqual(ip.get_container_format(), 'tar')

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_container_format_when_profile_data_is_None_return_tar(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = None

        self.assertEqual(ip.get_container_format(), 'tar')

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_profile_data')
    def test_get_container_format_get_from_profile_data(self, mock_profile_data):
        ip = InformationPackage.objects.create()
        mock_profile_data.return_value = {'container_format': "jar"}

        self.assertEqual(ip.get_container_format(), 'jar')


class InformationPackageGetPathTests(TestCase):

    def test_get_path_should_return_object_path(self):
        ip = InformationPackage.objects.create(object_path="path/to/the/object.tar")

        self.assertEqual(ip.get_path(), "path/to/the/object.tar")


class InformationPackageGenerationTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.user = User.objects.create(username='user')

    def test_is_first_generation_aic_is_None_should_return_True(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP, generation=0)

        self.assertEqual(aip.is_first_generation(), True)

    def test_is_first_generation_aic_with_single_aip_should_return_True(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        self.assertEqual(aip.is_first_generation(), True)

    def test_is_first_generation_aic_with_multiple_aips(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip_1 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        aip_2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=13)
        aip_1.save()
        aip_2.save()

        self.assertEqual(aip_1.is_first_generation(), False)
        self.assertEqual(aip_2.is_first_generation(), True)

    def test_is_first_generation_aic_with_multiple_aips_when_workarea_read_only_is_False_should_be_filtered(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip_1 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        aip_2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=13)
        Workarea.objects.create(ip=aip_2, read_only=False, user=self.user)
        aip_1.save()
        aip_2.save()

        self.assertEqual(aip_1.is_first_generation(), True)
        self.assertEqual(aip_2.is_first_generation(), False)

    def test_is_first_generation_aic_when_workarea_read_only_is_False_should_be_filtered(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        Workarea.objects.create(ip=aip, read_only=False, user=self.user)
        aip.save()

        self.assertEqual(aip.is_first_generation(), False)

    def test_is_last_generation_aic_is_None_should_return_True(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP, generation=0)

        self.assertEqual(aip.is_last_generation(), True)

    def test_is_last_generation_aic_with_single_aip_should_return_True(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        self.assertEqual(aip.is_last_generation(), True)

    def test_is_last_generation_aic_with_multiple_aips(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip_1 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        aip_2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=13)
        aip_1.save()
        aip_2.save()

        self.assertEqual(aip_1.is_last_generation(), True)
        self.assertEqual(aip_2.is_last_generation(), False)

    def test_is_last_generation_aic_with_multiple_aips_when_workarea_read_only_is_False_should_be_filtered(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip_1 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        aip_2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=13)
        Workarea.objects.create(ip=aip_1, read_only=False, user=self.user)
        aip_1.save()
        aip_2.save()

        self.assertEqual(aip_1.is_last_generation(), False)
        self.assertEqual(aip_2.is_last_generation(), True)

    def test_is_last_generation_aic_when_workarea_read_only_is_False_should_be_filtered(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=42)
        Workarea.objects.create(ip=aip, read_only=False, user=self.user)
        aip.save()

        self.assertEqual(aip.is_last_generation(), False)
