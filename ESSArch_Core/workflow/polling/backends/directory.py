# -*- coding: utf-8 -*-

import errno
import logging
import os
import shutil

from django.conf import settings
from lxml import etree

from ESSArch_Core.WorkflowEngine.polling.backends.base import BaseWorkflowPoller
from ESSArch_Core.auth.models import Group, GroupMember
from ESSArch_Core.essxml.util import get_altrecordids
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.profiles.utils import profile_types
from ESSArch_Core.util import stable_path

logger = logging.getLogger('essarch.epp.workflow.polling.DirectoryWorkflowPoller')
p_types = [p_type.lower().replace(' ', '_') for p_type in profile_types]
proj = settings.PROJECT_SHORTNAME


class DirectoryWorkflowPoller(BaseWorkflowPoller):
    def poll(self, path, sa=None):
        for entry in os.listdir(path):
            subpath = os.path.join(path, entry)

            if os.path.isdir(subpath):
                continue

            entryname, entryext = os.path.splitext(entry)
            entryext = entryext[1:]

            if entryext != 'tar':
                continue

            objid = os.path.basename(entryname)
            if InformationPackage.objects.filter(object_identifier_value=objid).exists():
                logger.debug(u'Information package with object identifier value "{}" already exists'.format(objid))
                continue

            if not stable_path(subpath):
                continue

            xmlfile = os.path.splitext(subpath)[0] + '.xml'

            if sa is None:
                logger.info(u'No SA specified, get from submit description instead')
                tree = etree.parse(xmlfile)
                root = tree.getroot()
                altrecordids = get_altrecordids(root)
                sa_id = altrecordids['SUBMISSIONAGREEMENT'][0]
                logger.info(u'Found SA in submit description: {}'.format(sa_id))
                sa = SubmissionAgreement.objects.get(pk=sa_id)
            else:
                logger.info(u'Using specified sa: {}'.format(sa))
                sa = SubmissionAgreement.objects.get(name=sa)

            if sa.profile_workflow is None:
                logger.debug(u'No workflow profile in SA, skipping')
                continue
            if proj not in sa.profile_workflow.specification:
                logger.debug(
                    'No workflow specified in {} for current project {}, skipping'.format(
                        sa.profile_workflow, proj
                    )
                )
                continue

            org = Group.objects.get(name='Default')
            role = 'admin'
            responsible = GroupMember.objects.filter(roles__codename=role, group=org).get().member.django_user

            ip = InformationPackage.objects.create(
                object_identifier_value=objid,
                sip_objid=objid,
                object_path=subpath,
                package_type=InformationPackage.AIP,
                submission_agreement=sa,
                submission_agreement_locked=True,
                state='Prepared',
                responsible=responsible,
                package_mets_path=xmlfile,
            )
            ip.create_profile_rels(p_types, responsible)
            org.add_object(ip)
            yield ip

    def delete_source(self, path, ip):
        base_path = os.path.join(path, ip.object_identifier_value)
        paths = [
            base_path + '.tar',
            base_path + '.xml',
            base_path + '_ipevents.xml',
        ]

        for path in paths:
            try:
                os.remove(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise


# TODO: these are moved here from ETA and should be merged with above
logger = logging.getLogger('essarch.eta.workflow.polling.DirectoryWorkflowPoller')
class DirectoryWorkflowPoller(BaseWorkflowPoller):
    def poll(self, path, sa=None):
        for entry in os.listdir(path):
            subpath = os.path.join(path, entry)

            if os.path.isdir(subpath):
                continue

            entryname, entryext = os.path.splitext(entry)
            entryext = entryext[1:]

            if entryext != 'tar':
                continue

            objid = os.path.basename(entryname)
            if InformationPackage.objects.filter(object_identifier_value=objid).exists():
                logger.debug(u'Information package with object identifier value "{}" already exists'.format(objid))
                continue

            if not stable_path(subpath):
                continue

            xmlfile = os.path.splitext(subpath)[0] + '.xml'

            if sa is None:
                logger.info(u'No SA specified, get from submit description instead')
                tree = etree.parse(xmlfile)
                root = tree.getroot()
                altrecordids = get_altrecordids(root)
                sa_id = altrecordids['SUBMISSIONAGREEMENT'][0]
                logger.info(u'Found SA in submit description: {}'.format(sa_id))
                sa = SubmissionAgreement.objects.get(pk=sa_id)
            else:
                logger.info(u'Using specified sa: {}'.format(sa))
                sa = SubmissionAgreement.objects.get(name=sa)

            if sa.profile_workflow is None:
                logger.debug(u'No workflow profile in SA, skipping')
                continue
            if proj not in sa.profile_workflow.specification:
                logger.debug(
                    'No workflow specified in {} for current project {}, skipping'.format(
                        sa.profile_workflow, proj
                    )
                )
                continue

            org = Group.objects.get(name='Default')
            role = 'admin'
            responsible = GroupMember.objects.filter(roles__codename=role, group=org).get().member.django_user

            ip = InformationPackage.objects.create(
                object_identifier_value=objid,
                object_path=subpath,
                package_type=InformationPackage.SIP,
                submission_agreement=sa,
                submission_agreement_locked=True,
                state='Prepared',
                responsible=responsible,
                package_mets_path=xmlfile,
            )
            ip.create_profile_rels(p_types, responsible)
            org.add_object(ip)
            yield ip

    def delete_source(self, path, ip):
        base_path = os.path.join(path, ip.object_identifier_value)
        paths = [
            base_path + '.tar',
            base_path + '.xml',
            base_path + '_ipevents.xml',
        ]

        for path in paths:
            try:
                os.remove(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise


#TODO: these are moved here from ETP and should be merged with above
logger = logging.getLogger('essarch.etp.workflow.polling.DirectoryWorkflowPoller')
class DirectoryWorkflowPoller(BaseWorkflowPoller):
    def poll(self, path, sa=None):
        for entry in os.listdir(path):
            subpath = os.path.join(path, entry)

            if os.path.isfile(subpath):
                continue

            objid = os.path.basename(subpath)
            if InformationPackage.objects.filter(object_identifier_value=objid).exists():
                logger.debug(u'Information package with object identifier value "{}" already exists'.format(objid))
                continue

            if not stable_path(subpath):
                continue

            sa = SubmissionAgreement.objects.get(name=sa)
            if sa.profile_workflow is None:
                logger.debug(u'No workflow profile in SA, skipping')
                continue
            if proj not in sa.profile_workflow.specification:
                logger.debug(
                    'No workflow specified in {} for current project {}, skipping'.format(
                        sa.profile_workflow, proj
                    )
                )
                continue

            org = Group.objects.get(name='Default')
            role = 'admin'
            responsible = GroupMember.objects.filter(roles__codename=role, group=org).get().member.django_user

            ip = InformationPackage.objects.create(
                object_identifier_value=objid,
                object_path=subpath,
                package_type=InformationPackage.SIP,
                submission_agreement=sa,
                submission_agreement_locked=True,
                state='Prepared',
                responsible=responsible,
            )
            ip.create_profile_rels(p_types, responsible)
            org.add_object(ip)
            yield ip

    def delete_source(self, path, ip):
        path = os.path.join(path, ip.object_identifier_value)
        try:
            shutil.rmtree(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
