# -*- coding: utf-8 -*-

import base64
# import errno
import logging
import os
# from os import listdir
# from os.path import isfile, join
import uuid
from ESSArch_Core.search.ingest import index_document
from django.db import transaction
# from django.db.models import Q
from lxml import etree
from elasticsearch_dsl.connections import get_connection as get_es_connection
from elasticsearch import helpers as es_helpers
from ESSArch_Core.essxml.util import parse_mets, get_altrecordid
from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import Component, File
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


def save_to_elasticsearch(components):
    logger.info("Saving to Elasticsearch...")
    conn = get_es_connection()
    count = 0

    for ok, result in es_helpers.streaming_bulk(conn, components):
        action, result = result.popitem()
        doc_id = result['_id']
        doc = '/%s/%s' % (result['_index'], doc_id)

        if not ok:
            logger.error('Failed to %s document %s: %r' % (action, doc, result))
        else:
            logger.debug('Saved document %s: %r' % (doc, result))
            count += 1

        yield ok, count

    logger.info("Documents saved to Elasticsearch")

def get_encoded_content_from_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
        encoded_content = base64.b64encode(content).decode("ascii")
    return encoded_content


from lxml import etree


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

        tp = get_treserva_path(dirpath)
        pt = parse_treserva(os.path.join(dirpath,tp))


        archive = TagVersion.objects.get(reference_code=archivist_note)
        ts = TagStructure.objects.get(tag=archive.tag)
        structure_unit_type = StructureUnitType.objects.get(name='serie')
        serie,_ = StructureUnit.objects.get_or_create(structure=ts.structure, name='TRESERVA',
                                                    reference_code='F3C', type=structure_unit_type)
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
            custom_fields = pt
        )

        akt_repr = TagStructure.objects.create(
            tag=akt,
            parent=ts,
            structure=ts.structure,
            structure_unit=serie
        )





        dir_reference_code = 1
        for root, dirs, files in os.walk(dirpath):
            basename = os.path.basename(root)
            if basename != 'Content':

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

                dir_tag_repr = TagStructure.objects.create(
                    tag=tag_version.tag,
                    parent=akt_repr,
                    structure=ts.structure
                )

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
                encoded_content = get_encoded_content_from_file(filepath)
                d = File.from_obj(tag_version, archive)
                d.data = encoded_content
                d_dict = d.to_dict(include_meta=True)
                d_dict['pipeline'] = 'ingest_attachment'

                TagStructure.objects.create(
                    tag=tag_version.tag,
                    parent=dir_tag_repr,
                    structure=ts.structure,
                )

                doc, tag_version = index_document(tag_version, filepath)
                tag_version.save()
                file_reference_code += 1
        save_to_elasticsearch(akt_version)
        akt_version.save()
        return 0
