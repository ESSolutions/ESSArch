"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2024 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import datetime
import itertools
import json
import logging
import time
from urllib.parse import urljoin

import click
import requests
import urllib3
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from requests import RequestException

from ESSArch_Core.config.decorators import initialize


@initialize
def import_globally():
    global StoragePolicySerializer, SubmissionAgreement, ProfileDetailSerializer, SubmissionAgreementSerializer
    from ESSArch_Core.configuration.serializers import StoragePolicySerializer
    from ESSArch_Core.profiles.models import SubmissionAgreement
    from ESSArch_Core.profiles.serializers import (
        ProfileDetailSerializer,
        SubmissionAgreementSerializer,
    )


@click.command()
@click.option("--sa_id", type=str, help="The submission agrement ID to update.")
@click.option("--sa_name", type=str, help="The submission agrement Name to update.")
@click.option('--host', default='https://remote-essarch.xxx', help='Remote server host URL')
@click.option('--user', default='', help='Username for authentication')
@click.option('--passw', default='', help='Password for authentication')
@click.option('--token', default='', help='Token for authentication')
@click.option('--verify', default=True, type=bool, help='SSL certificate verification')
def update_sa(sa_id, sa_name, host, user, passw, token, verify):
    """Update Submission Agreement and profiles/policies on remote server."""
    import_globally()
    if sa_id is None and sa_name is None:
        print("You must specify either a sa_id or a sa_name.")
        exit(1)
    if host is None:
        print("You must specify a host.")
        exit(1)

    remote_instance = Remote(host=host, user=user, passw=passw, token=token, verify=verify)
    remote_instance.update_sa(id=sa_id, name=sa_name)
    remote_instance.logout()


@initialize
def import_globally_storageMedium():
    global StorageMediumWriteSerializer, StoragePolicy
    from ESSArch_Core.configuration.models import StoragePolicy
    from ESSArch_Core.storage.serializers import StorageMediumWriteSerializer


@click.command()
@click.option("--policy_id", type=str, help="The storage policy ID to update.")
@click.option("--medium_id", type=str, help="The medium_id to update.")
@click.option("--days", type=int, help="Days back in time (DAYS: 1)")
@click.option("--start_datetime", type=str, help="start_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--stop_datetime", type=str, help="stop_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--preview", is_flag=True, help="Preview the medium_id to update.")
@click.option("--force", is_flag=True, help="Force the medium_id to update.")
@click.option('--host', default='https://remote-essarch.xxx', help='Remote server host URL')
@click.option('--user', default='', help='Username for authentication')
@click.option('--passw', default='', help='Password for authentication')
@click.option('--token', default='', help='Token for authentication')
@click.option('--verify', default=True, type=bool, help='SSL certificate verification')
def update_storageMedium(days, start_datetime, stop_datetime, policy_id, medium_id, preview, force,
                         host, user, passw, token, verify):
    """Update storageMedium on remote server."""
    import_globally_storageMedium()
    if policy_id is None:
        print("You must specify a policy_id.")
        exit(1)
    if host is None:
        print("You must specify a host.")
        exit(1)
    optionflag = 1

    if days:
        optionflag = 0
        start_datetime = timezone.now() - datetime.timedelta(days=days)
    elif start_datetime:
        optionflag = 0
        try:
            naive_dt = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
            start_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid start_datetime")
    else:
        start_datetime = timezone.now()

    if optionflag:
        print("incorrect options, you must specify either --days or --start_datetime")
        exit(1)

    if stop_datetime:
        try:
            naive_dt = datetime.datetime.strptime(stop_datetime, "%Y-%m-%d %H:%M:%S")
            stop_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid stop_datetime")
    else:
        stop_datetime = timezone.now()

    remote_instance = Remote(host=host, user=user, passw=passw, token=token, verify=verify)
    remote_instance.update_storageMedium(startDateTime=start_datetime, stopDateTime=stop_datetime,
                                         PolicyID=policy_id, storageMediumID=medium_id, preview=preview,
                                         ForceFlag=force)
    remote_instance.logout()


@initialize
def import_globally_storage():
    global StorageObjectSerializer, StoragePolicy
    from ESSArch_Core.configuration.models import StoragePolicy
    from ESSArch_Core.storage.serializers import StorageObjectSerializer


@click.command()
@click.option("--policy_id", type=str, help="The storage policy ID to update.")
@click.option("--medium_id", type=str, help="The medium_id to update.")
@click.option("--days", type=int, help="Days back in time (DAYS: 1)")
@click.option("--start_datetime", type=str, help="start_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--stop_datetime", type=str, help="stop_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--preview", is_flag=True, help="Preview the medium_id to update.")
@click.option("--force", is_flag=True, help="Force the medium_id to update.")
@click.option('--host', default='https://remote-essarch.xxx', help='Remote server host URL')
@click.option('--user', default='', help='Username for authentication')
@click.option('--passw', default='', help='Password for authentication')
@click.option('--token', default='', help='Token for authentication')
@click.option('--verify', default=True, type=bool, help='SSL certificate verification')
def update_storage(days, start_datetime, stop_datetime, policy_id, medium_id, preview, force,
                   host, user, passw, token, verify):
    """Update storageMedium on remote server."""
    import_globally_storage()
    if policy_id is None:
        print("You must specify a policy_id.")
        exit(1)
    if host is None:
        print("You must specify a host.")
        exit(1)
    optionflag = 1

    if days:
        optionflag = 0
        start_datetime = timezone.now() - datetime.timedelta(days=days)
    elif start_datetime:
        optionflag = 0
        try:
            naive_dt = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
            start_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid start_datetime")
    else:
        start_datetime = timezone.now()

    if optionflag:
        print("incorrect options, you must specify either --days or --start_datetime")
        exit(1)

    if stop_datetime:
        try:
            naive_dt = datetime.datetime.strptime(stop_datetime, "%Y-%m-%d %H:%M:%S")
            stop_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid stop_datetime")
    else:
        stop_datetime = timezone.now()

    remote_instance = Remote(host=host, user=user, passw=passw, token=token, verify=verify)
    remote_instance.update_storage(startDateTime=start_datetime, stopDateTime=stop_datetime,
                                   PolicyID=policy_id, storageMediumID=medium_id, preview=preview,
                                   ForceFlag=force)
    remote_instance.logout()


@initialize
def import_globally_ip():
    global InformationPackageFromMasterSerializer, StoragePolicy
    from ESSArch_Core.configuration.models import StoragePolicy
    from ESSArch_Core.ip.serializers import (
        InformationPackageFromMasterSerializer,
    )


@click.command()
@click.option("--policy_id", type=str, help="The storage policy ID to update.")
@click.option("--ip_id", type=str, help="The ip_id (object_identifier_value) to update.")
@click.option("--medium_id", type=str, help="The medium_id to update.")
@click.option("--days", type=int, help="Days back in time (DAYS: 1)")
@click.option("--start_datetime", type=str, help="start_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--stop_datetime", type=str, help="stop_datetime (TIMESTAMP: '2009-01-01 00:00:00')")
@click.option("--preview", is_flag=True, help="Preview the medium_id to update.")
@click.option("--force", is_flag=True, help="Force the medium_id to update.")
@click.option('--host', default='https://remote-essarch.xxx', help='Remote server host URL')
@click.option('--user', default='', help='Username for authentication')
@click.option('--passw', default='', help='Password for authentication')
@click.option('--token', default='', help='Token for authentication')
@click.option('--verify', default=True, type=bool, help='SSL certificate verification')
def update_ip(days, start_datetime, stop_datetime, policy_id, medium_id, ip_id, preview, force,
              host, user, passw, token, verify):
    """Update storageMedium on remote server."""
    import_globally_ip()
    if policy_id is None:
        print("You must specify a policy_id.")
        exit(1)
    if host is None:
        print("You must specify a host.")
        exit(1)
    optionflag = 1

    if days:
        optionflag = 0
        start_datetime = timezone.now() - datetime.timedelta(days=days)
    elif start_datetime:
        optionflag = 0
        try:
            naive_dt = datetime.datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
            start_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid start_datetime")
    else:
        start_datetime = timezone.now()

    if optionflag:
        print("incorrect options, you must specify either --days or --start_datetime")
        exit(1)

    if stop_datetime:
        try:
            naive_dt = datetime.datetime.strptime(stop_datetime, "%Y-%m-%d %H:%M:%S")
            stop_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            print("Invalid stop_datetime")
    else:
        stop_datetime = timezone.now()

    remote_instance = Remote(host=host, user=user, passw=passw, token=token, verify=verify)
    remote_instance.update_ip(startDateTime=start_datetime, stopDateTime=stop_datetime,
                              PolicyID=policy_id, storageMediumID=medium_id, ObjectIdentifierValue=ip_id,
                              preview=preview, ForceFlag=force)
    remote_instance.logout()


def chunks(iterable, size):
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, size))


class Remote:
    """
    Remote module for ESSArch to update profiles and storage policies on a remote server.
    """

    def __init__(self, host='https://remote-essarch.xxx', user='', passw='', token='', verify=None):
        self.host = host
        self.user = user
        self.passw = passw
        self.token = token
        self.session = requests.Session()
        self.session.verify = verify if verify is not None else settings.REQUESTS_VERIFY
        if self.session.verify is False:
            # Disable only the InsecureRequestWarning
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if self.user and self.passw:
            token = self.session.post(
                urljoin(self.host, reverse('knox_login')),
                json={'username': self.user, 'password': self.passw},
                timeout=10
            ).json().get('token')
            if not token:
                print("Authentication failed. Please check your username and password.")
                exit(1)
        elif not token:
            token = getattr(settings, 'REMOTE_API_TOKEN', '')
            if not token:
                print("No API token provided. Please set REMOTE_API_TOKEN in settings or provide user/passw.")
                exit(1)
        self.session.headers['Authorization'] = 'Token %s' % token
        self.token = token

    def logout(self):
        """
        Logout from the remote server.
        """
        if self.user and self.passw:
            logger = logging.getLogger('essarch.ip')
            remote_url = urljoin(self.host, reverse('knox_logout'))
            response = self.session.post(remote_url, timeout=10)
            try:
                response.raise_for_status()
            except RequestException:
                logger.exception("Problem to logout from remote server. Response: {}".format(response.text))
                raise

    def update_profile(self, profile_obj):
        logger = logging.getLogger('essarch.ip')
        data = ProfileDetailSerializer(instance=profile_obj).data
        remote_url = urljoin(self.host, 'api/profiles/')
        response = self.session.post(remote_url, json=data, timeout=10)
        try:
            response.raise_for_status()
        except RequestException:
            logger.exception(
                "Problem to add/update profile: {} to remote server. Response: {}".format(profile_obj, response.text))
            raise

    def update_storage_policy(self, storage_policy_obj):
        logger = logging.getLogger('essarch.ip')
        data = StoragePolicySerializer(instance=storage_policy_obj).data
        # Blank remote_server if match host
        for sm_obj in data['storage_methods']:
            for smtr_obj in sm_obj['storage_method_target_relations']:
                if smtr_obj['storage_target']['remote_server']:
                    if smtr_obj['storage_target']['remote_server'].split(',')[0] == self.host:
                        smtr_obj['storage_target']['remote_server'] = ""
        remote_url = urljoin(self.host, 'api/storage-policies/')
        response = self.session.post(remote_url, json=data, timeout=10)
        try:
            response.raise_for_status()
        except RequestException:
            logger.exception(
                "Problem to add/update Storage Policy: {} to remote server. Response: {}".format(
                    storage_policy_obj, response.text))
            raise

    def update_sa(self, id=None, name=None):
        logger = logging.getLogger('essarch.ip')
        if id:
            sa_obj = SubmissionAgreement.objects.get(id=id)
        else:
            sa_obj = SubmissionAgreement.objects.get(name=name)
        sa_obj_data = SubmissionAgreementSerializer(instance=sa_obj).data

        if sa_obj.profile_transfer_project:
            self.update_profile(sa_obj.profile_transfer_project)
        if sa_obj.profile_content_type:
            self.update_profile(sa_obj.profile_content_type)
        if sa_obj.profile_data_selection:
            self.update_profile(sa_obj.profile_data_selection)
        if sa_obj.profile_authority_information:
            self.update_profile(sa_obj.profile_authority_information)
        if sa_obj.profile_archival_description:
            self.update_profile(sa_obj.profile_archival_description)
        if sa_obj.profile_import:
            self.update_profile(sa_obj.profile_import)
        if sa_obj.profile_submit_description:
            self.update_profile(sa_obj.profile_submit_description)
        if sa_obj.profile_sip:
            self.update_profile(sa_obj.profile_sip)
        if sa_obj.profile_aic_description:
            self.update_profile(sa_obj.profile_aic_description)
        if sa_obj.profile_aip:
            self.update_profile(sa_obj.profile_aip)
        if sa_obj.profile_dip:
            self.update_profile(sa_obj.profile_dip)
        if sa_obj.profile_aip_description:
            self.update_profile(sa_obj.profile_aip_description)
        if sa_obj.profile_workflow:
            self.update_profile(sa_obj.profile_workflow)
        if sa_obj.profile_preservation_metadata:
            self.update_profile(sa_obj.profile_preservation_metadata)
        if sa_obj.profile_event:
            self.update_profile(sa_obj.profile_event)
        if sa_obj.profile_validation:
            self.update_profile(sa_obj.profile_validation)
        if sa_obj.profile_action_workflow:
            self.update_profile(sa_obj.profile_action_workflow)
        if sa_obj.policy:
            self.update_storage_policy(sa_obj.policy)

        remote_url = urljoin(self.host, 'api/submission-agreements/')
        response = self.session.post(remote_url, json=sa_obj_data, timeout=10)
        try:
            response.raise_for_status()
        except RequestException:
            logger.exception(
                "Problem to add/update Submission Agreement: {} to remote server. Response: {}".format(
                    sa_obj, response.text))
            raise

    def update_storageMedium(self, startDateTime, stopDateTime, PolicyID='', storageMediumID='',
                             preview=False, ForceFlag=False):
        """Update storageMedium on remote server."""
        m_filter = Q(create_date__range=(startDateTime, stopDateTime))
        if storageMediumID:
            m_filter &= Q(medium_id__startswith=storageMediumID)
        p_filter = Q()
        if PolicyID:
            p_filter = Q(policy_id=PolicyID)
        for policy_obj in StoragePolicy.objects.filter(p_filter):
            for storagemethod_obj in policy_obj.storage_methods.all():
                for storagetarget_obj in storagemethod_obj.targets.all():
                    for storageMedium_obj in storagetarget_obj.storagemedium_set.filter(
                            m_filter).order_by('medium_id'):
                        if not storageMedium_obj.check_db_sync() or ForceFlag:
                            data = StorageMediumWriteSerializer(instance=storageMedium_obj).data
                            if preview:
                                print(f"Preview: Add/update medium_id: {storageMedium_obj.medium_id} in \
storage policy: {policy_obj.policy_id} ({policy_obj.policy_name}).")
                                print(json.dumps(data, indent=4))
                                continue
                            print(f"Add/update medium_id: {storageMedium_obj.medium_id} in \
storage policy: {policy_obj.policy_id} ({policy_obj.policy_name}).")
                            remote_url = urljoin(self.host, 'api/storage-mediums/')
                            response = self.session.post(remote_url, json=data, timeout=10)
                            try:
                                response.raise_for_status()
                            except RequestException:
                                print(f"Problem to add/update medium_id: {storageMedium_obj.medium_id} in \
storage policy: {policy_obj.policy_id} ({policy_obj.policy_name}). Response: {response.text}")
                                print(json.dumps(data, indent=4))
                                raise
                            else:
                                storageMedium_obj.last_changed_external = storageMedium_obj.last_changed_local
                                storageMedium_obj.save(
                                    update_fields=['last_changed_external'])

    def update_storage(self, startDateTime, stopDateTime, PolicyID='', storageMediumID='',
                       preview=False, ForceFlag=False):
        """Update storage on remote server."""
        m_filter = Q()
        if storageMediumID:
            m_filter &= Q(medium_id__startswith=storageMediumID)
        p_filter = Q()
        if PolicyID:
            p_filter = Q(policy_id=PolicyID)
        for policy_obj in StoragePolicy.objects.filter(p_filter):
            for storagemethod_obj in policy_obj.storage_methods.all():
                for storagetarget_obj in storagemethod_obj.targets.all():
                    for storageMedium_obj in storagetarget_obj.storagemedium_set.filter(
                            m_filter).order_by('medium_id'):
                        num = 0
                        start_time = time.time()
                        data_list = []
                        for storage_obj in storageMedium_obj.storage.filter(
                                last_changed_local__range=(startDateTime, stopDateTime)).natural_sort():
                            if not storage_obj.check_db_sync() or ForceFlag:
                                # Add StorageObject
                                num += 1
                                remote_ip = urljoin(
                                    self.host, 'api/storage-objects/')
                                serializer_start_time = time.time()
                                data = StorageObjectSerializer(
                                    instance=storage_obj).data
                                serializer_time_elapsed = round(
                                    time.time() - serializer_start_time, 3)
                                print('Prepare to add storage for IP: %s on StorageMedium: %s location: %s \
policy: %s (%s) serializer_time: %s' % (storage_obj.ip.object_identifier_value,
                                        storage_obj.storage_medium.medium_id, storage_obj.content_location_value,
                                        policy_obj.policy_id, policy_obj.policy_name,
                                        serializer_time_elapsed))
                                data_list.append(data)
                        chunk_num = 1
                        if data_list:
                            for data_chunk in chunks(data_list, 100):
                                if preview:
                                    print('Preview: Start to add storage for StorageMedium: %s policy: %s (%s) \
chunk: %s' % (storage_obj.storage_medium.medium_id, policy_obj.policy_id, policy_obj.policy_name, chunk_num))
                                    print(json.dumps(data_chunk, indent=4))
                                    continue
                                post_start_time = time.time()
                                print('Start to add storage for StorageMedium: %s policy: %s (%s) \
chunk: %s' % (storage_obj.storage_medium.medium_id, policy_obj.policy_id, policy_obj.policy_name, chunk_num))
                                response = self.session.post(
                                    remote_ip, json=data_chunk, timeout=300)
                                post_time_elapsed = round(
                                    time.time() - post_start_time, 3)
                                print('Add storage for StorageMedium: %s policy: %s (%s) \
chunk: %s post_time: %s' % (storage_obj.storage_medium.medium_id,
                                    policy_obj.policy_id, policy_obj.policy_name,
                                    chunk_num, post_time_elapsed))
                                try:
                                    response.raise_for_status()
                                except RequestException:
                                    print('Problem to add storage for StorageMedium: %s policy: %s (%s) \
chunk: %s post_time: %s. Response: %s' % (storage_obj.storage_medium.medium_id,
                                          policy_obj.policy_id, policy_obj.policy_name,
                                          chunk_num, post_time_elapsed, response.text))
                                    print(json.dumps(data, indent=4))
                                    raise
                                chunk_num += 1

                        if not preview:
                            for storage_obj in storageMedium_obj.storage.filter(
                                    ip__last_changed_local__range=(startDateTime, stopDateTime)).natural_sort():
                                if not storage_obj.check_db_sync() or ForceFlag:
                                    storage_obj.last_changed_external = storage_obj.last_changed_local
                                    storage_obj.save(
                                        update_fields=['last_changed_external'])

                        time_elapsed = time.time() - start_time
                        ip_per_sec = round(num / time_elapsed, 3)
                        if data_list:
                            if preview:
                                print('Preview: Success to add storage %s IPs/second for StorageMedium: %s \
policy: %s (%s)' % (ip_per_sec, storageMedium_obj.medium_id, policy_obj.policy_id, policy_obj.policy_name))
                            else:
                                print('Success to add storage %s IPs/second for StorageMedium: %s \
policy: %s (%s)' % (ip_per_sec, storageMedium_obj.medium_id, policy_obj.policy_id, policy_obj.policy_name))

    def update_ip(self, startDateTime, stopDateTime, PolicyID='', storageMediumID='', ObjectIdentifierValue='',
                  preview=False, ForceFlag=False):
        """Update ip on remote server."""
        m_filter = Q(last_changed_local__range=(startDateTime, stopDateTime))
        if storageMediumID:
            m_filter &= Q(medium_id__startswith=storageMediumID)
        p_filter = Q()
        if PolicyID:
            p_filter = Q(policy_id=PolicyID)
        ip_done = []
        ip_done2 = []
        for policy_obj in StoragePolicy.objects.filter(p_filter):
            if ObjectIdentifierValue:
                for sa_obj in policy_obj.submission_agreements.all():
                    ip_filter = Q(last_changed_local__range=(startDateTime, stopDateTime))
                    ip_filter &= Q(object_identifier_value__startswith=ObjectIdentifierValue)
                    for ip_obj in sa_obj.information_packages.filter(ip_filter):
                        if not ip_obj.check_db_sync() or ForceFlag:
                            data = InformationPackageFromMasterSerializer(instance=ip_obj).data
                            # Add ArchiveObject
                            if preview:
                                print('Preview: Add IP: %s policy: %s (%s)' % (ip_obj.object_identifier_value,
                                                                               policy_obj.policy_id,
                                                                               policy_obj.policy_name))
                                print(json.dumps(data, indent=4))
                                continue
                            print('Add IP: %s policy: %s (%s)' % (ip_obj.object_identifier_value,
                                                                  policy_obj.policy_id,
                                                                  policy_obj.policy_name))
                            remote_ip = urljoin(
                                self.host, 'api/information-packages/add-from-master/')
                            response = self.session.post(
                                remote_ip, json=data, timeout=120)
                            try:
                                response.raise_for_status()
                            except RequestException:
                                print('Problem to add IP: %s policy: %s (%s). Response: %s' % (
                                    ip_obj.object_identifier_value, policy_obj.policy_id,
                                    policy_obj.policy_name, response.text))
                                print(json.dumps(data, indent=4, default=str))
                                raise
                            else:
                                ip_obj.last_changed_external = ip_obj.last_changed_local
                                ip_obj.save(
                                    update_fields=['last_changed_external'])
            else:
                for storagemethod_obj in policy_obj.storage_methods.all():
                    for storagetarget_obj in storagemethod_obj.targets.all():
                        for storageMedium_obj in storagetarget_obj.storagemedium_set.filter(
                                m_filter).order_by('medium_id'):
                            num = 0
                            start_time = time.time()
                            data_list = []
                            for storage_obj in storageMedium_obj.storage.filter(
                                    ip__last_changed_local__range=(startDateTime, stopDateTime)).natural_sort():
                                if storage_obj.ip.id in ip_done:
                                    continue
                                if not storage_obj.ip.check_db_sync() or ForceFlag:
                                    # Add ArchiveObject
                                    num += 1
                                    remote_ip = urljoin(
                                        self.host, 'api/information-packages/add-from-master/')
                                    serializer_start_time = time.time()
                                    data = InformationPackageFromMasterSerializer(
                                        instance=storage_obj.ip).data
                                    serializer_time_elapsed = round(
                                        time.time() - serializer_start_time, 3)
                                    print('Prepare to add IP: %s on StorageMedium: %s location: %s policy: %s (%s) \
serializer_time: %s' % (storage_obj.ip.object_identifier_value,
                                        storage_obj.storage_medium.medium_id, storage_obj.content_location_value,
                                        policy_obj.policy_id, policy_obj.policy_name,
                                        serializer_time_elapsed))
                                    data_list.append(data)
                                    ip_done.append(storage_obj.ip.id)
                            chunk_num = 1
                            if data_list:
                                for data_chunk in chunks(data_list, 100):
                                    if preview:
                                        print('Preview: Start to add IPs for StorageMedium: %s policy: %s (%s) \
chunk: %s' % (storage_obj.storage_medium.medium_id, policy_obj.policy_id, policy_obj.policy_name, chunk_num))
                                        print(json.dumps(data_chunk, indent=4))
                                        continue
                                    post_start_time = time.time()
                                    print('Start to add IPs for StorageMedium: %s policy: %s (%s) \
chunk: %s' % (storage_obj.storage_medium.medium_id, policy_obj.policy_id, policy_obj.policy_name, chunk_num))
                                    response = self.session.post(
                                        remote_ip, json=data_chunk, timeout=300)
                                    post_time_elapsed = round(
                                        time.time() - post_start_time, 3)
                                    print('Add IPs for StorageMedium: %s policy: %s (%s) \
chunk: %s post_time: %s' % (storage_obj.storage_medium.medium_id,
                                        policy_obj.policy_id, policy_obj.policy_name,
                                        chunk_num, post_time_elapsed))
                                    try:
                                        response.raise_for_status()
                                    except RequestException:
                                        print('Problem to add IPs for StorageMedium: %s policy: %s (%s) \
chunk: %s post_time: %s. Response: %s' % (storage_obj.storage_medium.medium_id,
                                          policy_obj.policy_id, policy_obj.policy_name,
                                          chunk_num, post_time_elapsed, response.text))
                                        print(json.dumps(data, indent=4))
                                        raise
                                    chunk_num += 1
                            if not preview:
                                for storage_obj in storageMedium_obj.storage.filter(
                                        ip__last_changed_local__range=(startDateTime, stopDateTime)).natural_sort():
                                    if storage_obj.ip.id in ip_done2:
                                        continue
                                    if not storage_obj.ip.check_db_sync() or ForceFlag:
                                        storage_obj.ip.last_changed_external = storage_obj.ip.last_changed_local
                                        storage_obj.ip.save(
                                            update_fields=['last_changed_external'])
                                        ip_done2.append(storage_obj.ip.id)

                            time_elapsed = time.time() - start_time
                            ip_per_sec = round(num / time_elapsed, 3)
                            if data_list:
                                if preview:
                                    print('Preview: Success to add %s IPs/second for StorageMedium: %s \
policy: %s (%s)' % (ip_per_sec, storageMedium_obj.medium_id, policy_obj.policy_id, policy_obj.policy_name))
                                else:
                                    print('Success to add %s IPs/second for StorageMedium: %s \
policy: %s (%s)' % (ip_per_sec, storageMedium_obj.medium_id, policy_obj.policy_id, policy_obj.policy_name))
