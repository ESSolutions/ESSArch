import base64
import os
import uuid

from ESSArch_Core.tags.documents import Directory, File
from ESSArch_Core.tags.models import Tag, TagStructure, TagVersion
from ESSArch_Core.util import get_tree_size_and_count, normalize_path, timestamp_to_datetime


def index_document(ip, filepath, id):
    with open(filepath, 'rb') as f:
        content = f.read()

    encoded_content = base64.b64encode(content).decode("ascii")
    filename = os.path.basename(filepath)
    extension = os.path.splitext(filename)[1][1:]
    dirname = os.path.dirname(filepath)
    href = normalize_path(os.path.relpath(dirname, ip.object_path))
    href = '' if href == '.' else href
    size, _ = get_tree_size_and_count(filepath)
    modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

    doc = File(
        _id=id, name=filename, type="document", filename=filename, extension=extension, href=href, ip=str(ip.pk),
        data=encoded_content, size=size, modified=modified, current_version=True
    )
    doc.save(pipeline='ingest_attachment')
    return doc


def index_directory(ip, dirpath, id):
    dirname = os.path.basename(dirpath)
    parent_dir = os.path.dirname(dirpath)
    href = normalize_path(os.path.relpath(parent_dir, ip.object_path))
    href = '' if href == '.' else href

    doc = Directory(_id=id, name=dirname, href=href, ip=str(ip.pk), current_version=True)
    doc.save()
    return doc


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

    if isfile:
        tag_version.elastic_index = 'document'
        tag_version.type = 'document'
        tag_version.save()
        return index_document(ip, path, id)
    else:
        tag_version.elastic_index = 'directory'
        tag_version.type = 'directory'
        tag_version.save()
        return index_directory(ip, path, id)
