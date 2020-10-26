# -*- coding: utf-8 -*-

import base64
import logging
import os
import uuid
from ESSArch_Core.search.ingest import index_document
from django.db import transaction
from lxml import etree
from ESSArch_Core.essxml.util import parse_mets
from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import Component
from ESSArch_Core.tags.models import (
    StructureUnit,
    StructureUnitType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
    Rendering
)
from ESSArch_Core.util import (
    get_tree_size_and_count,
    # remove_prefix,
    # timestamp_to_datetime,
)

logger = logging.getLogger('essarch.search.importers.EardErmsImporter')


def get_encoded_content_from_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
        encoded_content = base64.b64encode(content).decode("ascii")
    return encoded_content


def get_treserva_path(dirpath):
    for f in os.listdir(dirpath):
        if f.endswith('.xml'):
            filepath = f
    return filepath


def parse_treserva(xmlfile):
    data = {}
    with open(xmlfile, 'rb') as treserva_xml:
        parser = etree.XMLParser()
        tree = etree.fromstring(treserva_xml.read(), parser)
        nsmap = {"Treserva": "http://www.cgi.com/ns/Treserva"}

        creation_date = tree.xpath('//Treserva:Treserva/Treserva:SkapatDatum', namespaces=nsmap)
        pers_nr = tree.xpath('//Treserva:Treserva/Treserva:Person/Treserva:PersonNr', namespaces=nsmap)

        #data['creation_date'] = creation_date[0].text
        data['personal_identification_number'] = pers_nr[0].text

    return data


def get_sip_mets(ip):
    path = ip.get_path()
    mets = ip.get_content_mets_file_path()
    filepath = os.path.join(path, 'content', str(ip.sip_objid), mets)
    return filepath


class TreservaImporter(BaseImporter):
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
        metadata_folder = 'System'
        dirpath = 'Content'
        if ip is not None:
            dirpath = os.path.join(ip.object_path, ip.sip_path, 'Content')
            metadata_folder = os.path.join(ip.object_path, ip.sip_path, 'System')
        elif rootdir is not None:
            metadata_folder = os.path.join(rootdir, 'System')

        # exclude metadata files
        metadata_files = os.listdir(metadata_folder)

        for mfile in metadata_files:
            mfilepath = os.path.join(metadata_folder, mfile)
            self.indexed_files.append(mfilepath)

        sip_mets = parse_mets(get_sip_mets(ip))
        archivist_note = sip_mets['agents']['ARCHIVIST_ORGANIZATION']['notes'][0]

        # Parse Treserva XML and map to custom_fields
        tp = get_treserva_path(dirpath)
        pt = parse_treserva(os.path.join(dirpath, tp))

        # Get TV and TS for archive
        archive = TagVersion.objects.get(reference_code=archivist_note)
        ts = TagStructure.objects.get(tag=archive.tag)

        # Create StructureUnit - serie
        structure_unit_type = StructureUnitType.objects.get(name='serie')
        serie, _ = StructureUnit.objects.get_or_create(
            structure=ts.structure,
            name='TRESERVA',
            reference_code='F3C',
            type=structure_unit_type
        )

        # Create TV and TS for akt / arende
        akt = Tag.objects.create(information_package=ip, task=self.task)
        akt_version_type, _ = TagVersionType.objects.get_or_create(name='Treserva', archive_type=False,
                                                                   information_package_type=False)
        akt_version = TagVersion.objects.create(
            pk=ip.id,
            tag=akt,
            elastic_index='component',
            name=ip.label,
            type=akt_version_type,
            reference_code=str(uuid.uuid4()),
            custom_fields=pt
        )
        logger.debug("Created TV - akt_version: %s" % repr(akt_version))

        akt_repr = TagStructure.objects.create(
            tag=akt,
            parent=ts,
            structure=ts.structure,
            structure_unit=serie
        )
        logger.debug("Created TS - akt_repr: %s with parent: %s" % (repr(akt_repr), repr(akt_repr.parent)))

        akt_version_doc = Component.from_obj(akt_version, archive)
        akt_version_doc.save()
        logger.debug("Saved TV - akt_version_doc to index Component: %s" % repr(akt_version_doc))

        dir_reference_code = 1
        for root, dirs, files in os.walk(dirpath):
            basename = os.path.basename(root)
            if basename != 'Content':

                # Create TV and TS for directorys
                tag = Tag.objects.create(information_package=ip, task=self.task)
                tag_version_type, _ = TagVersionType.objects.get_or_create(name='directory', archive_type=False)
                tag_version = TagVersion.objects.create(
                    pk=str(uuid.uuid4()),
                    tag=tag,
                    elastic_index='component',
                    name=basename,
                    type=tag_version_type,
                    reference_code=dir_reference_code
                )
                logger.debug("Created TV - tag_version: %s" % repr(tag_version))

                dir_tag_repr = TagStructure.objects.create(
                    tag=tag_version.tag,
                    parent=akt_repr,
                    structure=ts.structure
                )
                logger.debug("Created TS - dir_tag_repr: %s with parent: %s" %
                             (repr(dir_tag_repr), repr(dir_tag_repr.parent)))

                tag_version_doc = Component.from_obj(tag_version, archive)
                tag_version_doc.save()
                logger.debug("Saved TV - tag_version_doc to index Component: %s" % repr(tag_version_doc))

                dir_reference_code += 1
            else:
                dir_tag_repr = akt_repr

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
                if filename.endswith('.xml'):
                    xslt = Rendering.objects.get(name='treserva')
                else:
                    xslt = None

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
                    rendering=xslt,
                    custom_fields=data,
                )
                logger.debug("Created TV - tag_version: %s" % repr(tag_version))

                file_tag_repr = TagStructure.objects.create(
                    tag=tag_version.tag,
                    parent=dir_tag_repr,
                    structure=ts.structure,
                )
                logger.debug("Created TS - file_tag_repr: %s with parent: %s" %
                             (repr(file_tag_repr), repr(file_tag_repr.parent)))

                doc, tag_version = index_document(tag_version, filepath)
                logger.debug("Saved TV - tag_version: %s and index filepath: %s to index File" %
                             (repr(akt_version_doc), filepath))

                file_reference_code += 1
        return 0
