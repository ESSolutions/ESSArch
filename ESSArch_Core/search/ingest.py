import base64
import os

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.tags.documents import Document
from ESSArch_Core.util import get_tree_size_and_count, timestamp_to_datetime


def index_document(ip, filepath):
    with open(filepath, 'rb') as f:
        content = f.read()

    encoded_content = base64.b64encode(content).decode("ascii")
    ip_object_path = InformationPackage.objects.get(pk=ip).object_path
    href = os.path.relpath(filepath, ip_object_path)
    size, _ = get_tree_size_and_count(filepath)
    modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

    doc = Document(href=href, ip=ip, data=encoded_content, size=size, modified=modified)
    doc.save(pipeline='ingest_attachment')
    return doc
