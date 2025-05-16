import logging
import os
import tarfile
import zipfile
from urllib.parse import urljoin

import requests
from celery import states as celery_states
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from ESSArch_Core.auth.models import Notification
from ESSArch_Core.config.celery import app
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.ip.utils import generate_aic_mets, generate_package_mets
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.storage.models import StorageMethod, StorageTarget
from ESSArch_Core.util import zip_directory
from ESSArch_Core.WorkflowEngine.models import ProcessStep

User = get_user_model()


@app.task(bind=True)
def CreateMediumMigrationWorkflow(self, media_migrate_workflow_step_id, ip_ids,
                                  storage_method_ids, temp_path, export_path):
    """
    Create Medium Migration Workflow

    Args:
        media_migrate_workflow_step_id: ID of the media workflow step to be used
        ip_ids: list of information package ids
        storage_method_ids: list of storage method ids
        temp_path: temporary path for migration
        export_path: export path for migration

    Returns:
        None
    """
    logger = logging.getLogger('essarch.storage.tasks.CreateMediumMigrationWorkflow')
    storage_methods = StorageMethod.objects.filter(pk__in=storage_method_ids)
    media_migrate_workflow_step = ProcessStep.objects.get(pk=media_migrate_workflow_step_id)
    logger.info('Start to add {} IPs workflows to step {}'.format(len(ip_ids), media_migrate_workflow_step.label))
    for ip_id in ip_ids:
        ip_obj = InformationPackage.objects.get(pk=ip_id)
        previously_not_completed_steps = []
        for previously_step in ProcessStep.objects.filter(name='Migrate Information Package',
                                                          information_package=ip_obj):
            if previously_step.status in [
                celery_states.PENDING,
                celery_states.STARTED,
            ]:
                previously_not_completed_steps.append(previously_step.id)
        if previously_not_completed_steps:
            logger.warning('Skip to add workflow for IP {} to step {}. Previously not completed migration step \
already exists: {}'.format(ip_obj.object_identifier_value, media_migrate_workflow_step.label,
                           previously_not_completed_steps))
        else:
            storage_methods_dst = storage_methods.filter(
                pk__in=ip_obj.get_migratable_storage_methods())
            ip_obj.create_migration_workflow(
                temp_path=temp_path,
                storage_methods=storage_methods_dst,
                export_path=export_path,
                tar=True,
                extracted=False,
                package_xml=True,
                aic_xml=True,
                diff_check=True,
                responsible=User.objects.get(pk=self.responsible),
                top_root_step=media_migrate_workflow_step,
            )
            logger.info('Added workflow for IP {} to step {}'.format(ip_obj.object_identifier_value,
                                                                     media_migrate_workflow_step.label))
    logger.info('Success to add {} IPs workflows to step {}, flag to run with poller'.format(
        len(ip_ids), media_migrate_workflow_step.label))
    media_migrate_workflow_step.run(poller=True)


@app.task(bind=True)
def StorageMigration(self, storage_method, temp_path):
    ip = self.get_information_package()
    container_format = ip.get_container_format()
    storage_method = StorageMethod.objects.get(pk=storage_method)

    try:
        storage_target = storage_method.enabled_target
    except StorageTarget.DoesNotExist:
        raise ValueError('No writeable target available for {}'.format(storage_method))

    dir_path = os.path.join(temp_path, ip.object_identifier_value)
    container_path = os.path.join(temp_path, ip.object_identifier_value + '.{}'.format(container_format))
    aip_xml_path = os.path.join(temp_path, ip.package_mets_path.split('/')[-1])
    aic_xml = True if ip.aic else False
    if aic_xml:
        aic_xml_path = os.path.join(temp_path, ip.aic.object_identifier_value + '.xml')

    if storage_target.master_server and not storage_target.remote_server:
        # we are on remote host
        src_container = True
    else:
        # we are not on master, access from existing storage object
        storage_object = ip.get_fastest_readable_storage_object()
        if storage_object.container:
            storage_object.read(temp_path, self.get_processtask())
        else:
            storage_object.read(dir_path, self.get_processtask())

        src_container = storage_object.container

    dst_container = storage_method.containers

    # If storage_object is "long term" and storage_method is not (or vice versa),
    # then we have to do some "conversion" before we go any further

    if src_container and not dst_container:
        # extract container
        if container_format == 'tar':
            with tarfile.open(container_path) as tar:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])

                    return prefix == abs_directory

                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")

                    tar.extractall(path, members, numeric_owner=numeric_owner)

                safe_extract(tar, temp_path)
        elif container_format == 'zip':
            with zipfile.ZipFile(container_path) as zipf:
                zipf.extractall(temp_path)
        else:
            raise ValueError('Invalid container format: {}'.format(container_format))

    elif not src_container and dst_container:
        # create container, aip xml and aic xml
        if container_format == 'tar':
            with tarfile.open(container_path, 'w') as new_tar:
                new_tar.format = settings.TARFILE_FORMAT
                new_tar.add(dir_path)
        elif container_format == 'zip':
            zip_directory(dirname=dir_path, zipname=container_path, compress=False)
        else:
            raise ValueError('Invalid container format: {}'.format(container_format))

        generate_package_mets(ip, container_path, aip_xml_path)
        if aic_xml:
            generate_aic_mets(ip, aic_xml_path)

    if dst_container or storage_target.remote_server:
        src = [
            container_path,
            aip_xml_path,
        ]
        if aic_xml:
            src.append(aic_xml_path)
    else:
        src = [dir_path]

    if storage_target.remote_server:
        # we are on master, copy files to remote

        host, user, passw = storage_target.remote_server.split(',')
        dst = urljoin(host, reverse('informationpackage-add-file-from-master'))
        requests_session = requests.Session()
        requests_session.verify = settings.REQUESTS_VERIFY
        requests_session.auth = (user, passw)

        for s in src:
            copy_file(s, dst, requests_session=requests_session)

    obj_id = ip.preserve(src, storage_target, dst_container, self.get_processtask())

    Notification.objects.create(
        message="Migrated {} to {}".format(ip.object_identifier_value, storage_method.name),
        level=logging.INFO,
        user_id=self.responsible,
        refresh=True,
    )

    return obj_id
