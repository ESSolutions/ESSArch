import os
import tarfile
import zipfile
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from ESSArch_Core.ip.utils import generate_aic_mets, generate_package_mets
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.storage.models import StorageMethod, StorageTarget
from ESSArch_Core.util import zip_directory
from ESSArch_Core.WorkflowEngine.dbtask import DBTask

User = get_user_model()


class StorageMigration(DBTask):
    def run(self, storage_method, temp_path):
        ip = self.get_information_package()
        container_format = ip.get_container_format()
        storage_method = StorageMethod.objects.get(pk=storage_method)

        try:
            storage_target = storage_method.enabled_target
        except StorageTarget.DoesNotExist:
            raise ValueError('No writeable target available for {}'.format(storage_method))

        if storage_target.master_server and not storage_target.remote_server:
            # we are on remote host
            src_container = True
        else:
            # we are not on master, access from existing storage object
            storage_object = ip.get_fastest_readable_storage_object()
            storage_object.read(os.path.join(temp_path, ip.object_identifier_value), self.get_processtask())
            src_container = storage_object.container

        dst_container = storage_method.containers

        dir_path = os.path.join(temp_path, ip.object_identifier_value)
        container_path = os.path.join(temp_path, ip.object_identifier_value + '.{}'.format(container_format))
        aip_xml_path = os.path.join(temp_path, ip.object_identifier_value + '.xml')
        aic_xml_path = os.path.join(temp_path, ip.aic.object_identifier_value + '.xml')

        # If storage_object is "long term" and storage_method is not (or vice versa),
        # then we have to do some "conversion" before we go any further

        if src_container and not dst_container:
            # extract container
            if container_format == 'tar':
                with tarfile.open(container_path) as tar:
                    tar.extractall(temp_path)
            elif container_format == 'zip':
                with zipfile.ZipFile(container_path) as zipf:
                    zipf.extractall(temp_path)
            else:
                raise ValueError('Invalid container format: {}'.format(container_format))

        elif not src_container and dst_container:
            # create container, aip xml and aic xml
            if container_format == 'tar':
                with tarfile.open(container_path, 'w') as new_tar:
                    new_tar.add(dir_path)
            elif container_format == 'zip':
                zip_directory(dirname=dir_path, zipname=container_path, compress=False)
            else:
                raise ValueError('Invalid container format: {}'.format(container_format))

            generate_package_mets(ip, container_path, aip_xml_path)
            generate_aic_mets(ip, aic_xml_path)

        if storage_method.containers or storage_target.remote_server:
            src = [
                container_path,
                aip_xml_path,
                aic_xml_path,
            ]
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

        return ip.preserve(src, storage_target, storage_method.containers, self.get_processtask())
