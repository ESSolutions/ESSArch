"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2023 ES Solutions AB

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

import django  # noqa isort:skip
django.setup()  # noqa isort:skip
import logging  # noqa isort:skip
from urllib.parse import urljoin  # noqa isort:skip

import requests  # noqa isort:skip
from django.conf import settings  # noqa isort:skip
from django.urls import reverse  # noqa isort:skip
from requests import RequestException  # noqa isort:skip
from tenacity import (  # noqa isort:skip
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.configuration.serializers import StoragePolicySerializer  # noqa isort:skip
from ESSArch_Core.profiles.models import SubmissionAgreement  # noqa isort:skip
from ESSArch_Core.profiles.serializers import (  # noqa isort:skip
    ProfileDetailSerializer,
    SubmissionAgreementSerializer,
)


host = 'https://essarch-media.org'
# org_name = 'Default'
user = 'superuser'
passw = 'superuser'
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()
session.verify = settings.REQUESTS_VERIFY
session.auth = (user, passw)


def update_profile(profile_obj):
    logger = logging.getLogger('essarch.ip')
    data = ProfileDetailSerializer(instance=profile_obj).data
    remote_url = urljoin(host, 'api/profiles/')
    response = session.post(remote_url, json=data, timeout=10)
    try:
        response.raise_for_status()
    except RequestException:
        logger.exception(
            "Problem to add/update profile: {} to remote server. Response: {}".format(profile_obj, response.text))
        raise


def update_storage_policy(storage_policy_obj):
    logger = logging.getLogger('essarch.ip')
    data = StoragePolicySerializer(instance=storage_policy_obj).data
    # Blank remote_server if match host
    for sm_obj in data['storage_methods']:
        for smtr_obj in sm_obj['storage_method_target_relations']:
            if smtr_obj['storage_target']['remote_server']:
                if smtr_obj['storage_target']['remote_server'].split(',')[0] == host:
                    smtr_obj['storage_target']['remote_server'] = ""
    remote_url = urljoin(host, 'api/storage-policies/')
    response = session.post(remote_url, json=data, timeout=10)
    try:
        response.raise_for_status()
    except RequestException:
        logger.exception(
            "Problem to add/update Storage Policy: {} to remote server. Response: {}".format(
                storage_policy_obj, response.text))
        raise


# @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
#        wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
def update_sa(id):
    logger = logging.getLogger('essarch.ip')
    sa_obj = SubmissionAgreement.objects.get(id=id)
    sa_obj_data = SubmissionAgreementSerializer(instance=sa_obj).data

    if sa_obj.profile_transfer_project:
        update_profile(sa_obj.profile_transfer_project)
    if sa_obj.profile_content_type:
        update_profile(sa_obj.profile_content_type)
    if sa_obj.profile_data_selection:
        update_profile(sa_obj.profile_data_selection)
    if sa_obj.profile_authority_information:
        update_profile(sa_obj.profile_authority_information)
    if sa_obj.profile_archival_description:
        update_profile(sa_obj.profile_archival_description)
    if sa_obj.profile_import:
        update_profile(sa_obj.profile_import)
    if sa_obj.profile_submit_description:
        update_profile(sa_obj.profile_submit_description)
    if sa_obj.profile_sip:
        update_profile(sa_obj.profile_sip)
    if sa_obj.profile_aic_description:
        update_profile(sa_obj.profile_aic_description)
    if sa_obj.profile_aip:
        update_profile(sa_obj.profile_aip)
    if sa_obj.profile_dip:
        update_profile(sa_obj.profile_dip)
    if sa_obj.profile_aip_description:
        update_profile(sa_obj.profile_aip_description)
    if sa_obj.profile_workflow:
        update_profile(sa_obj.profile_workflow)
    if sa_obj.profile_preservation_metadata:
        update_profile(sa_obj.profile_preservation_metadata)
    if sa_obj.profile_event:
        update_profile(sa_obj.profile_event)
    if sa_obj.profile_validation:
        update_profile(sa_obj.profile_validation)
    if sa_obj.profile_action_workflow:
        update_profile(sa_obj.profile_action_workflow)
    if sa_obj.policy:
        update_storage_policy(sa_obj.policy)

    remote_url = urljoin(host, 'api/submission-agreements/')
    response = session.post(remote_url, json=sa_obj_data, timeout=10)
    try:
        response.raise_for_status()
    except RequestException:
        logger.exception(
            "Problem to add/update Submission Agreement: {} to remote server. Response: {}".format(
                sa_obj, response.text))
        raise


# python -c 'from ESSArch_Core.install import update_remote as ur; ur.update_sa("id")'
if __name__ == '__main__':
    update_sa("3328d5b1-7519-41bd-81ee-c3195055f00a")
