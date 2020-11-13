# -*- coding: utf-8 -*-

import base64
import logging
import os
import uuid

from django.db import transaction
from django.db.utils import IntegrityError

from ESSArch_Core.essxml.util import parse_mets
from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.search.ingest import index_document
from ESSArch_Core.tags.documents import File
from ESSArch_Core.tags.models import (
    StructureUnit,
    StructureUnitType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
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
    filepath = os.path.join(path, 'content', str(ip.object_identifier_value), mets)
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

        # Get TV and TS for archive
        archive = TagVersion.objects.get(id=alt_rec_reference_code[0])
        ts = TagStructure.objects.get(tag=archive.tag)
        unit_type = StructureUnitType.objects.get_or_create(name='serie')

        for root, _dirs, files in os.walk(dirpath):
            basename = os.path.basename(root)
            if basename != 'content':
                su_name_ref = basename.split(" ")
                logger.debug("root: %s, basename: %s, su_name_ref: %s" %
                             (repr(root), repr(basename), repr(su_name_ref)))

                if not len(su_name_ref) > 1:
                    parent_basename = os.path.basename(os.path.dirname(root))
                    su_name_ref_parent = parent_basename.split(" ")
                    su_name_ref.insert(0, su_name_ref_parent[0] + '.unknown_' + str(uuid.uuid4())[:8])

                if su_name_ref[0].endswith('.'):
                    su_name_ref[0] = su_name_ref[0][:-1]

                # Create StructureUnit - serie
                try:
                    parent = StructureUnit.objects.get(structure=ts.structure,
                                                       reference_code=su_name_ref[0].rsplit('.', 1)[0])
                    logger.debug("found parent: %s for reference_code: %s" % (repr(parent), repr(su_name_ref)))
                except StructureUnit.DoesNotExist:
                    parent = None
                    logger.debug("parent: %s for reference_code: %s" % (repr(parent), repr(su_name_ref)))

                try:
                    structure_unit = StructureUnit.objects.get_or_create(structure=ts.structure, type=unit_type[0],
                                                                         reference_code=su_name_ref[0],
                                                                         name=su_name_ref[1], parent=parent)
                    logger.debug("create structure_unit with reference_code: %s, parent: %s" %
                                 (repr(su_name_ref), repr(parent)))
                except IntegrityError as e:
                    logger.error('IntegrityError when try to get or create reference_code %s, error: %s' %
                                 (repr(su_name_ref), str(e)))
                    structure_unit = StructureUnit.objects.get_or_create(structure=ts.structure, type=unit_type[0],
                                                                         reference_code=su_name_ref[0] +
                                                                         '_dup_' + str(uuid.uuid4())[:8],
                                                                         name=su_name_ref[1], parent=parent)
                    logger.debug("create structure_unit _dup with reference_code: %s + _dup, parent: %s" %
                                 (repr(su_name_ref), repr(parent)))
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

                # Create TV and TS for files
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
