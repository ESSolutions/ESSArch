import base64
import logging
import os
import uuid

from elasticsearch.exceptions import ElasticsearchException

from ESSArch_Core.tags.documents import Directory, File
from ESSArch_Core.tags.models import (
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)
from ESSArch_Core.util import (
    get_tree_size_and_count,
    normalize_path,
    timestamp_to_datetime,
)

logger = logging.getLogger('essarch.search.ingest')


def index_document(tag_version, filepath):
    with open(filepath, 'rb') as f:
        content = f.read()

    ip = tag_version.tag.information_package
    encoded_content = base64.b64encode(content).decode("ascii")
    extension = os.path.splitext(tag_version.name)[1][1:]
    dirname = os.path.dirname(filepath)
    href = normalize_path(os.path.relpath(dirname, ip.object_path))
    href = '' if href == '.' else href
    size, _ = get_tree_size_and_count(filepath)
    modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

    tag_version.custom_fields = {
        'extension': extension,
        'dirname': dirname,
        'href': href,
        'filename': tag_version.name,
        'size': size,
        'modified': modified,
    }

    doc = File.from_obj(tag_version)
    doc.data = encoded_content

    try:
        doc.save(pipeline='ingest_attachment')
    except ElasticsearchException:
        logger.exception('Failed to index {}'.format(filepath))
        raise
    return doc, tag_version


def index_directory(tag_version, dirpath):
    ip = tag_version.tag.information_package
    parent_dir = os.path.dirname(dirpath)
    href = normalize_path(os.path.relpath(parent_dir, ip.object_path))
    href = '' if href == '.' else href

    tag_version.custom_fields = {
        'href': href,
    }

    doc = Directory.from_obj(tag_version)
    doc.save()
    return doc, tag_version


def index_path(ip, path, parent=None):
    """
    Indexes the file or directory at path to elasticsearch

    :param ip: The IP the path belongs to
    :type ip: InformationPackage
    :param path: The path of the file or directory
    :type path: str
    :param parent: The parent of the tag
    :type parent: TagStructure
    :return: The indexed elasticsearch document
    :rtype: File or Directory
    """

    isfile = os.path.isfile(path)
    id = str(uuid.uuid4())

    tag = Tag.objects.create(information_package=ip)
    tag_version = TagVersion(pk=id, tag=tag, name=os.path.basename(path))
    if parent:
        TagStructure.objects.create(tag=tag, parent=parent, structure=parent.structure)

    logger.debug('indexing {}'.format(path))

    if isfile:
        tag_version.elastic_index = 'document'
        # TODO: minimize db queries
        tag_version.type = TagVersionType.objects.get_or_create(name='document', archive_type=False)[0]
        doc, tag_version = index_document(tag_version, path)
        tag_version.save()
    else:
        tag_version.elastic_index = 'directory'
        # TODO: minimize db queries
        tag_version.type = TagVersionType.objects.get_or_create(name='directory', archive_type=False)[0]
        doc, tag_version = index_directory(tag_version, path)
        tag_version.save()
