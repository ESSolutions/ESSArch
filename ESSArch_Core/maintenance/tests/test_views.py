import os
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.views import find_all_files
from ESSArch_Core.util import win_to_posix

User = get_user_model()


class CreateAppraisalRuleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('appraisalrule-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_appraisalrule')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class FindAllFilesTests(TestCase):

    def setUp(self):
        self.datadir = os.path.join(tempfile.mkdtemp(), "datadir")
        self.dir_names = [
            'a_dir', 'b_dir', 'c_dir',
            'aa_dir', 'bb_dir', 'cc_dir',
            'ab_dir', 'ac_dir',
            'ba_dir', 'bc_dir',
            'ca_dir', 'cb_dir',
            'a_dir/ca_dir', 'b_dir/cb_dir',
        ]
        self.ip = InformationPackage.objects.create(
            object_path=self.datadir,
            object_identifier_value="ip_obj_id_value"
        )

    def create_dirs_and_files(self):
        for d in self.dir_names:
            try:
                os.makedirs(os.path.join(self.datadir, d))
            except OSError as e:
                if e.errno != 17:
                    raise

        files = []
        for d in self.dir_names:
            for i in range(3):
                fname = os.path.join(self.datadir, os.path.join(d, f"{i}.txt"))
                with open(fname, 'w') as f:
                    f.write(f"{i}")
                files.append(fname)

        return files

    def normalize_paths(self, expected_file_names):
        return [win_to_posix(f) for f in expected_file_names]

    def test_find_all_files_when_pattern_is_star(self):
        files = self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([fi.replace(os.path.join(self.datadir, ""), "") for fi in files])

        found_files = find_all_files(self.datadir, self.ip, "*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')

        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/0.txt', 'a_dir/1.txt', 'a_dir/2.txt',
            'aa_dir/0.txt', 'aa_dir/1.txt', 'aa_dir/2.txt',
            'ab_dir/0.txt', 'ab_dir/1.txt', 'ab_dir/2.txt',
            'ac_dir/0.txt', 'ac_dir/1.txt', 'ac_dir/2.txt',
            'a_dir/ca_dir/0.txt', 'a_dir/ca_dir/1.txt', 'a_dir/ca_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "a*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_start_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2.txt")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_starts_and_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)
