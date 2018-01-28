import base64
import os

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.tags.documents import Directory, Document
from ESSArch_Core.util import get_tree_size_and_count, timestamp_to_datetime


def index_document(ip, filepath):
    with open(filepath, 'rb') as f:
        content = f.read()

    encoded_content = base64.b64encode(content).decode("ascii")
    filename = os.path.basename(filepath)
    extension = os.path.splitext(filename)[1][1:]
    dirname = os.path.dirname(filepath)
    href = os.path.relpath(dirname, ip.object_path)

    if href == '.':
        href = ''

    size, _ = get_tree_size_and_count(filepath)
    modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

    doc = Document(name=filename, extension=extension, href=href, ip=str(ip.pk), data=encoded_content, size=size, modified=modified)
    doc.save(pipeline='ingest_attachment')
    return doc


def index_directory(ip, dirpath):
    dirname = os.path.basename(dirpath)
    parent_dir = os.path.dirname(dirpath)
    href = os.path.relpath(parent_dir, ip.object_path)

    if href == '.':
        href = ''

    doc = Directory(name=dirname, href=href, ip=str(ip.pk))
    doc.save()
    return doc


def index_path(ip, path):
    if os.path.isfile(path):
        return index_document(ip, path)

    return index_directory(ip, path)
