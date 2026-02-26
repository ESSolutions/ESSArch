import logging
import os
import uuid

from django.conf import settings
from elasticsearch import ConnectionError, RequestError, TransportError

from ESSArch_Core.fixity.format import FormatIdentifier
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


def index_document(tag_version, filepath, index_file_content=True):
    logger = logging.getLogger('essarch.search.ingest')
    exclude_file_format_from_indexing_content = settings.EXCLUDE_FILE_FORMAT_FROM_INDEXING_CONTENT

    fid = FormatIdentifier()
    (format_name, format_version, format_registry_key) = fid.identify_file_format(filepath)
    if format_registry_key in exclude_file_format_from_indexing_content:
        index_file_content = False

    ip = tag_version.tag.information_package
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
        'formatname': format_name,
        'formatversion': format_version,
        'formatkey': format_registry_key,
    }

    doc = File.from_obj(tag_version)

    MAX_INDEX_SIZE = getattr(settings, 'ELASTICSEARCH_MAX_INDEX_SIZE', None)

    if index_file_content and MAX_INDEX_SIZE and size > MAX_INDEX_SIZE:
        logger.info(f'Skipping content indexing due to size for {filepath}')
        index_file_content = False

    try:
        if index_file_content:
            with open(filepath, 'rb') as f:
                doc = File.enrich_with_content(doc, file_obj=f)
        else:
            logger.debug(f'Skip to index file content for {filepath}')
        doc.save()

    except TransportError as e:
        if e.status_code == 413:
            logger.error(f'Document too large to index: {filepath}')
            RETRY_WITHOUT_CONTENT_IF_TOO_LARGE = getattr(settings,
                                                         'ELASTICSEARCH_RETRY_WITHOUT_CONTENT_IF_TOO_LARGE',
                                                         False)
            if index_file_content and RETRY_WITHOUT_CONTENT_IF_TOO_LARGE:
                logger.info(f'Retrying without file content for {filepath}')
                try:
                    doc = File.from_obj(tag_version)
                    doc.save()
                except Exception:
                    logger.exception(f'Retry without content also failed for {filepath}')
                    raise
            else:
                logger.error(f'Not retrying without content for {filepath} due to settings')
                raise
        else:
            logger.exception(f'Elasticsearch transport error indexing {filepath}')
            raise

    except (ConnectionError, RequestError):
        logger.exception(f'Elasticsearch connection/request error indexing {filepath}')
        raise

    except Exception:
        logger.exception(f'Unexpected error indexing {filepath}')
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


def generate_tag_id(ip, rel_path):
    normalized = os.path.normpath(rel_path).replace("\\", "/").lower()
    base_string = f"{ip.pk}:{normalized}"
    return uuid.uuid5(uuid.NAMESPACE_URL, base_string)


def index_path(ip, path, parent=None, group=None, index_file_content=True):
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

    logger = logging.getLogger('essarch.search.ingest')
    isfile = os.path.isfile(path)

    name = os.path.basename(path)
    rel_path = os.path.relpath(path, ip.object_path)

    tag_id = generate_tag_id(ip, rel_path)

    tag, _ = Tag.objects.get_or_create(id=tag_id, defaults={"information_package": ip})
    tag_version, _ = TagVersion.objects.get_or_create(
        tag=tag,
        name=name,
        defaults={
            "elastic_index": "document" if isfile else "directory",
            "type": TagVersionType.objects.get_or_create(name="document" if isfile else "directory",
                                                         archive_type=False)[0]
        }
    )

    if parent:
        TagStructure.objects.get_or_create(tag=tag, parent=parent, structure=parent.structure)

    logger.debug('indexing {}'.format(path))

    if isfile:
        doc, tag_version = index_document(tag_version, path, index_file_content)
    else:
        doc, tag_version = index_directory(tag_version, path)

    tag_version.save()

    if group:
        group.add_object(tag_version)
