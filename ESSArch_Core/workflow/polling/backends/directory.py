import errno
import logging
import os
import shutil

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import exceptions

from ESSArch_Core.auth.models import Group, GroupMember
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import ProfileIP, SubmissionAgreement
from ESSArch_Core.util import stable_path
from ESSArch_Core.WorkflowEngine.polling.backends.base import (
    BaseWorkflowPoller,
)

logger = logging.getLogger('essarch.workflow.polling.DirectoryWorkflowPoller')


class DirectoryWorkflowPoller(BaseWorkflowPoller):
    def poll(self, path, sa=None):
        for entry in os.listdir(path):
            subpath = os.path.join(path, entry)

            if os.path.isfile(subpath):
                continue

            objid = os.path.basename(subpath)
            if InformationPackage.objects.filter(object_identifier_value=objid).exists():
                logger.debug('Information package with object identifier value "{}" already exists'.format(objid))
                continue

            if not stable_path(subpath):
                continue

            sa = SubmissionAgreement.objects.get(name=sa)
            if sa.profile_workflow is None:
                logger.debug('No workflow profile in SA, skipping')
                continue

            # storage_policy_name = 'default'
            # try:
            #    storage_policy = StoragePolicy.objects.get(policy_name=storage_policy_name)
            # except StoragePolicy.DoesNotExist:
            #    logger.exception('Storage policy "{}" not found'.format(storage_policy_name))
            #    raise

            org = Group.objects.get(name='Default')
            role = 'Administrator'
            responsible = GroupMember.objects.filter(roles__codename=role, group=org).get().member.django_user

            with transaction.atomic():
                ip = InformationPackage.objects.create(
                    object_identifier_value=objid,
                    object_path=subpath,
                    package_type=InformationPackage.SIP,
                    submission_agreement=sa,
                    state='Prepared',
                    responsible=responsible,
                )
                org.add_object(ip)
                sa.lock_to_information_package(ip, responsible)
                for profile_ip in ProfileIP.objects.filter(ip=ip).iterator():
                    try:
                        profile_ip.clean()
                    except ValidationError as e:
                        raise exceptions.ParseError('%s: %s' % (profile_ip.profile.name, str(e)))

                    profile_ip.lock(responsible)
            yield ip

    def delete_source(self, path, ip):
        path = os.path.join(path, ip.object_identifier_value)
        try:
            shutil.rmtree(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
