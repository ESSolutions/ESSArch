import errno
import logging
import os
import shutil

from django.db import transaction

from ESSArch_Core.auth.models import Group, GroupMember
from ESSArch_Core.configuration.models import StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.profiles.utils import lowercase_profile_types
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

            storage_policy_name = 'default'
            try:
                storage_policy = StoragePolicy.objects.get(policy_name=storage_policy_name)
            except StoragePolicy.DoesNotExist:
                logger.exception('Storage policy "{}" not found'.format(storage_policy_name))
                raise

            org = Group.objects.get(name='Default')
            role = 'admin'
            responsible = GroupMember.objects.filter(roles__codename=role, group=org).get().member.django_user

            with transaction.atomic():
                ip = InformationPackage.objects.create(
                    object_identifier_value=objid,
                    object_path=subpath,
                    package_type=InformationPackage.SIP,
                    submission_agreement=sa,
                    submission_agreement_locked=True,
                    state='Prepared',
                    responsible=responsible,
                    policy=storage_policy,
                )
                ip.create_profile_rels(lowercase_profile_types, responsible)
                org.add_object(ip)
            yield ip

    def delete_source(self, path, ip):
        path = os.path.join(path, ip.object_identifier_value)
        try:
            shutil.rmtree(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
