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

import logging
from urllib.parse import urljoin

import click
import requests
from django.conf import settings
from django.urls import reverse
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
@click.option('--host', default='https://remote-essarch.xxx', help='Remote server host URL')
@click.option('--user', default='', help='Username for authentication')
@click.option('--passw', default='', help='Password for authentication')
@click.option('--token', default='', help='Token for authentication')
@click.option('--verify', default=True, type=bool, help='SSL certificate verification')
def update_sa(sa_id, host, user, passw, token, verify):
    """Update Submission Agreement and profiles/policies on remote server."""
    import_globally()
    if sa_id is None:
        print("You must specify either a sa_id.")
        exit(1)
    if host is None:
        print("You must specify a host.")
        exit(1)

    remote_instance = Remote(host=host, user=user, passw=passw, token=token, verify=verify)
    remote_instance.update_sa(sa_id)
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

    def update_sa(self, id):
        logger = logging.getLogger('essarch.ip')
        sa_obj = SubmissionAgreement.objects.get(id=id)
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
