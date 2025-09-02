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
import logging
from urllib.parse import urljoin

import click
import requests
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
    global StoragePolicy, StoragePolicySerializer, SubmissionAgreement, ProfileDetailSerializer
    from ESSArch_Core.configuration.models import StoragePolicy
    from ESSArch_Core.configuration.serializers import StoragePolicySerializer
    from ESSArch_Core.profiles.models import SubmissionAgreement
    from ESSArch_Core.profiles.serializers import (  # SubmissionAgreementSerializer,
        ProfileDetailSerializer,
    )


@click.command()
@click.option("--policy_id", type=str, help="The storage policy ID to update.")
# @click.option("--ip_id", type=str, help="The ip_id (object_identifier_value) to update.")
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
    # if medium_id is None:
    #     print("You must specify a medium_id.")
    #     exit(1)
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
                            print('Add or update medium_id: %s in storage policy: %s (%s)' % (
                                storageMedium_obj.medium_id, policy_obj.policy_id, policy_obj.policy_name))
                            # remote_ip = urljoin(host, 'api/storage-mediums/')
                            # data = StorageMediumSerializer_essarch(
                            #     instance=storageMedium_obj).data
                            # response = session.post(
                            #     remote_ip, json=data, timeout=120)
                            # try:
                            #     response.raise_for_status()
                            # except requests.RequestException as e:
                            #     logger.error(json.dumps(data, indent=4))
                            #     logger.error('Error: ' + response.content +
                            #                  ' Data: ' + repr(data))
                            #     raise e
                            # else:
                            #     storageMedium_obj.ExtDBdatetime = storageMedium_obj.LocalDBdatetime
                            #     storageMedium_obj.save(
                            #         update_fields=['ExtDBdatetime'])
