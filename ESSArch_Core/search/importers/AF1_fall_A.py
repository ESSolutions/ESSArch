# -*- coding: utf-8 -*-

import base64
# import errno
import logging
import os
# from os import listdir
# from os.path import isfile, join
import uuid

from django.db import transaction

# from django.db.models import Q
# from lxml import etree
# from elasticsearch_dsl.connections import get_connection as get_es_connection
# from elasticsearch import helpers as es_helpers
from ESSArch_Core.essxml.util import parse_mets
from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.search.ingest import index_document
from ESSArch_Core.tags.documents import File
from ESSArch_Core.tags.models import (
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
    StructureUnitType,
    Structure,
)
from ESSArch_Core.util import (  # remove_prefix,; timestamp_to_datetime,
    get_tree_size_and_count,
)

logger = logging.getLogger('essarch.search.importers.EardErmsImporter')


def get_encoded_content_from_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
        encoded_content = base64.b64encode(content).decode("ascii")
    return encoded_content


def get_sip_mets(ip):
    path = ip.get_path()
    mets = ip.get_content_mets_file_path()
    filepath = os.path.join(path, 'content', str(ip.id), mets)
    return filepath


class AF1_fall_AImporter(BaseImporter):
    def import_content(self, path, rootdir=None, ip=None, **extra_paths):
        if not rootdir:
            if ip is not None:
                rootdir = ip.object_path
            else:
                rootdir = os.path.dirname(path)

            self.indexed_files = []

            logger.debug("Deleting task tags already in database...")
            Tag.objects.filter(task=self.task).delete()

            self.cleanup_elasticsearch(self.task)

            with transaction.atomic():
                self.get_content(rootdir, path, ip)

        return self.indexed_files

    def get_content(self, rootdir, path, ip):

        data = {}
        metadata_folder = 'metadata'
        dirpath = 'content'
        if ip is not None:
            dirpath = os.path.join(ip.object_path, ip.sip_path, 'content')
            metadata_folder = os.path.join(ip.object_path, ip.sip_path, 'metadata')
        elif rootdir is not None:
            metadata_folder = os.path.join(rootdir, 'metadata')

        # exclude metadata files
        metadata_files = os.listdir(metadata_folder)

        for mfile in metadata_files:
            mfilepath = os.path.join(metadata_folder, mfile)
            self.indexed_files.append(mfilepath)

        sip_mets = parse_mets(get_sip_mets(ip))
        alt_rec_reference_code = sip_mets['altrecordids']['REFERENCECODE'][0].split('/')
        archive = TagVersion.objects.get(id=alt_rec_reference_code[0])
        ts = TagStructure.objects.get(tag=archive.tag)
        unit_type = StructureUnitType.objects.get_or_create(name='serie')

        for root, dirs, files in os.walk(dirpath):
            basename = os.path.basename(root)
            if basename != 'content':
                su_name_ref = basename.split(" ")

                try:
                    parent = StructureUnit.objects.get(structure=ts.structure,
                                                       reference_code=su_name_ref[0].rsplit('.', 1)[0])
                except StructureUnit.DoesNotExist:
                    parent = None

                try:
                    structure_unit = StructureUnit.objects.get_or_create(structure=ts.structure, type=unit_type[0],
                                                        reference_code=su_name_ref[0],
                                                        name=su_name_ref[1], parent=parent)
                except:
                    structure_unit = StructureUnit.objects.get_or_create(structure=ts.structure, type=unit_type[0],
                                                                            reference_code=su_name_ref[0]+'_dup',
                                                                            name=su_name_ref[1], parent=parent)
            else:
                pass

            file_reference_code = 1
            for pfile in files:
                filepath = os.path.join(root, pfile)
                href = os.path.dirname(os.path.relpath(filepath, rootdir))
                href = '' if href == '.' else href
                filename = os.path.basename(filepath)
                ext = os.path.splitext(filepath)[1][1:]
                size, _ = get_tree_size_and_count(filepath)

                data['href'] = href
                data['filename'] = filename
                data['ext'] = ext
                data['size'] = size
                data['dirname'] = rootdir

                self.indexed_files.append(filepath)

                tag = Tag.objects.create(information_package=ip, task=self.task)
                tag_version_type, _ = TagVersionType.objects.get_or_create(name='document', archive_type=False)
                tag_version = TagVersion.objects.create(
                    pk=str(uuid.uuid4()),
                    tag=tag,
                    elastic_index='document',
                    name=filename,
                    type=tag_version_type,
                    reference_code=file_reference_code,
                    custom_fields=data,

                )
                encoded_content = get_encoded_content_from_file(filepath)
                d = File.from_obj(tag_version, archive)
                d.data = encoded_content
                d_dict = d.to_dict(include_meta=True)
                d_dict['pipeline'] = 'ingest_attachment'

                TagStructure.objects.create(
                    tag=tag_version.tag,
                    parent=archive.get_active_structure(),
                    structure=ts.structure,
                    structure_unit=structure_unit[0]
                )

                doc, tag_version = index_document(tag_version, filepath)
                tag_version.save()
                file_reference_code += 1

        with transaction.atomic():
            logger.debug("Rebuilding tree...")
            TagStructure.objects.rebuild()

        return 0
