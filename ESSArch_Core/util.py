"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import errno
import glob
import io
import itertools
import json
import logging
import os
import platform
import re
import shutil
import sys
import tarfile
import time
import urllib.request
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from os import scandir, walk
from pathlib import Path
from subprocess import PIPE, Popen
from time import sleep
from urllib.parse import quote

import chardet
import requests
from celery import states as celery_states
from django.conf import settings
from django.core.cache import cache
from django.core.validators import RegexValidator
from django.http.response import FileResponse
from django.utils.timezone import get_current_timezone
from lxml import etree
from natsort import natsorted
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from ESSArch_Core._version import get_versions
from ESSArch_Core.crypto import decrypt_remote_credentials
from ESSArch_Core.exceptions import NoFileChunksFound
from ESSArch_Core.fixity.format import FormatIdentifier

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
VERSION = get_versions()['version']


def make_unicode(text):
    try:
        return str(text, 'utf-8')
    except TypeError:
        if not isinstance(text, str):
            return str(text)
        return text
    except UnicodeDecodeError:
        return str(text.decode('iso-8859-1'))


def sliceUntilAttr(iterable, attr, val):
    for i in iterable:
        if getattr(i, attr) == val:
            return
        yield i


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def stable_path(path):
    logger = logging.getLogger('essarch')
    current_size, current_count = get_tree_size_and_count(path)
    cache_size_key = 'path_size_{}'.format(path)
    cache_count_key = 'path_count_{}'.format(path)
    cached_size = cache.get(cache_size_key)
    cached_count = cache.get(cache_count_key)

    new = cached_size is None
    updated_size = cached_size != current_size
    updated_count = cached_count != current_count
    if new or updated_size or updated_count:
        if new:
            logger.info('New path: {}, size: {}, count: {}'.format(path, current_size, current_count))
        elif updated_size or updated_count:
            logger.info(
                'Updated path: {}, size: {} => {}, count: {} => {}'.format(
                    path, cached_size, current_size, cached_count, current_count
                )
            )
        cache.set(cache_size_key, current_size, 60 * 60)
        cache.set(cache_count_key, current_count, 60 * 60)
        return False

    logger.info('Stable path: {}, size: {}, count: {}'.format(path, current_size, current_count))
    return True


def get_elements_without_namespace(root, path, value=None):
    element_path = []
    splits = path.split("/")
    for idx, split in enumerate(splits):
        if "@" in split:
            el, attr = split.split("@")
            if value is not None:
                split_path = '*[local-name()="{el}" and @*[local-name()="{attr}"]="{value}"]'.format(
                    el=el, attr=attr, value=value
                )
            else:
                split_path = '*[local-name()="{el}" and @*[local-name()="{attr}"]]'.format(el=el, attr=attr)
        else:
            if idx == len(splits) - 1 and value is not None and "@" not in path:
                split_path = '*[local-name()="{el}" and text()="{value}"]'.format(el=split, value=value)
            else:
                split_path = '*[local-name()="{el}"]'.format(el=split)

        element_path.append(split_path)

    path_string = ".//" + "/".join(element_path)
    return root.xpath(path_string)


def get_value_from_path(root, path):
    """
    Gets the text or attribute from the given attribute using the given path.

    Examples:
        * Return the text of "element":
            get_value_from_path(element, ".")

        * Return the attribute "foo" of "element":
            get_value_from_path(element, "@foo")

        * Return the text of "element" > "foo" > "bar":
            get_value_from_path(element, "foo/bar")

        * Return the attribute "baz" of "element" > "foo" > "bar":
            get_value_from_path(element, "foo/bar@baz")

    attr:
        el: A lxml Element
        path: The path to the text or attribute
    """

    logger = logging.getLogger('essarch')
    if path is None:
        return None

    if path.startswith('@'):
        attr = path[1:]
        for a, val in root.attrib.items():
            if re.sub(r'{.*}', '', a) == attr:
                return val

    try:
        el = get_elements_without_namespace(root, path)[0]
    except IndexError:
        logger.debug('{path} not found in {root}'.format(path=path, root=root.getroottree().getpath(root)))
        return None

    if "@" in path:
        attr = path.split('@')[1]
        return el.xpath("@*[local-name()='%s'][1]" % attr)[0]

    return el.text


def getSchemas(doc=None, filename=None, base_url=None, visited=None):
    """
        Creates a schema based on the schemas specified in the provided XML
        file's schemaLocation attribute
    """
    logger = logging.getLogger('essarch')
    if visited is None:
        visited = set()

    if filename:
        if base_url is None:
            base_url = os.path.dirname(os.path.abspath(filename))
        parser = etree.XMLParser(resolve_entities=False)
        doc = etree.parse(filename, parser=parser)

    if doc is None:
        raise ValueError("Must provide either doc or filename")

    root_doc = doc.getroot()
    xsi_NS = root_doc.nsmap.get('xsi')
    if xsi_NS is None:
        raise ValueError("No xsi namespace found in document")

    xsd_NS = "{%s}" % XSD_NAMESPACE
    NSMAP = {'xsd': XSD_NAMESPACE}
    schema_root = etree.Element(xsd_NS + "schema", nsmap=NSMAP)
    schema_root.attrib["elementFormDefault"] = "qualified"

    def process_schema_location(ns, loc, current_base_url):
        # Resolve schemaLocation against current base URL
        if current_base_url and not (loc.startswith('http://') or loc.startswith('https://') or os.path.isabs(loc)):
            resolved_loc = os.path.abspath(os.path.join(current_base_url, loc))
        else:
            resolved_loc = loc

        if resolved_loc in visited:
            logger.debug(f"Skipping already visited schema: {resolved_loc}")
            return

        logger.debug(f"Processing schema: namespace={ns}, location={loc} (resolved: {resolved_loc})")
        visited.add(resolved_loc)

        etree.SubElement(schema_root, xsd_NS + "import", attrib={
            "namespace": ns,
            "schemaLocation": loc
        })

        # Attempt to load and parse the schema to find nested imports/includes
        try:
            if resolved_loc.startswith('http://') or resolved_loc.startswith('https://'):
                with urllib.request.urlopen(resolved_loc) as response:
                    imported_doc = etree.parse(response)
                new_base_url = resolved_loc.rsplit('/', 1)[0]
            else:
                imported_doc = etree.parse(resolved_loc)
                new_base_url = os.path.dirname(resolved_loc)
        except Exception as e:
            logger.warning(f"Warning: Could not load schema at {resolved_loc}: {e}")
            return

        imported_root = imported_doc.getroot()

        # Find nested imports and includes
        nested_imports = imported_root.findall(f".//{xsd_NS}import")
        nested_includes = imported_root.findall(f".//{xsd_NS}include")

        for elem in nested_imports:
            nested_ns = elem.get("namespace")
            nested_loc = elem.get("schemaLocation")
            if nested_loc:
                process_schema_location(nested_ns, nested_loc, new_base_url)

        for elem in nested_includes:
            # <xsd:include> usually does NOT have a namespace attribute
            nested_loc = elem.get("schemaLocation")
            if nested_loc:
                # includes are from the same namespace as the including schema
                process_schema_location(ns, nested_loc, new_base_url)

    # Get all xsi:schemaLocation attributes in the original doc
    schema_locations = set(doc.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': xsi_NS}))

    for schema_location in schema_locations:
        ns_locs = schema_location.split()
        for ns, loc in zip(ns_locs[::2], ns_locs[1::2]):
            process_schema_location(ns, loc, base_url)

    return schema_root


def move_schema_locations_to_root(tree=None, filename=None):
    """
    Move all schemaLocation attributes in the document to the root element
    """

    if filename:
        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(filename, parser=parser)

    root = tree.getroot()
    xsi_ns = "{%s}" % root.nsmap['xsi']

    # Get root schema locations
    root_schema_locations = list(chunks(root.attrib["%sschemaLocation" % xsi_ns].split(), 2))

    # Get all other schema locations
    other_schema_locations = []
    schema_location_elements = tree.findall(".//*[@%sschemaLocation]" % xsi_ns)
    for el in schema_location_elements:
        other_schema_locations += list(chunks(el.attrib["%sschemaLocation" % xsi_ns].split(), 2))

        # Delete schemaLocation attribute
        del el.attrib["%sschemaLocation" % xsi_ns]

    # Append all missing schema locations to root_schema_locations
    for schema_location in other_schema_locations:
        if schema_location not in root_schema_locations:
            root_schema_locations.append(schema_location)

    # Convert root_schema_locations to schemaLocation attrib
    schema_location = ' '.join(flatten(root_schema_locations))

    # Update scehamLocation attrib
    root.attrib[xsi_ns + "schemaLocation"] = schema_location

    return tree


def assign_stylesheet(xml, xslt):
    parser = etree.XMLParser(resolve_entities=False)
    xml_doc = etree.parse(xml, parser=parser).getroot()
    xslt_doc = etree.parse(xslt)
    transform = etree.XSLT(xslt_doc)
    new_doc = transform(xml_doc)

    return etree.tostring(new_doc)


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def timestamp_to_datetime(timestamp):
    tz = get_current_timezone()
    return datetime.fromtimestamp(timestamp, tz)


def find_destination(use, structure, path=""):
    for content in structure:
        name = content.get('name', '')
        if content.get('use') == use:
            return path, name

        dest, fname = find_destination(
            use, content.get('children', []), (Path(path) / name).as_posix()
        )

        if dest:
            return dest, fname

    return None, None


def get_files_and_dirs(path):
    """Return all files and directories at a given path"""

    if os.path.isdir(path):
        return scandir(path)

    return []


def get_immediate_subdirectories(path):
    """Return immediate subdirectories at a given path"""

    return filter(lambda x: x.is_dir(), get_files_and_dirs(path))


def get_tree_size_and_count(path='.'):
    """Return total size and count of files in given path and subdirs."""

    path = Path(path)

    if path.is_file():
        return path.stat().st_size, 1

    total_size = 0
    count = 0
    for f in path.rglob('*'):
        if f.is_file():
            total_size += f.stat().st_size
            count += 1

    return total_size, count


def win_to_posix(path):
    return path.replace('\\', '/')


def normalize_path(path):
    sep = os.sep
    if sep != '/':
        return path.replace(sep, '/')
    return path


def get_event_spec():
    dirname = os.path.dirname(os.path.realpath(__file__))
    fname = 'templates/JSONPremisEventTemplate.json'
    with open(os.path.join(dirname, fname)) as json_file:
        return json.load(json_file)


def get_event_element_spec():
    dirname = os.path.dirname(os.path.realpath(__file__))
    fname = 'templates/PremisEventElementTemplate.json'
    with open(os.path.join(dirname, fname)) as json_file:
        return json.load(json_file)


def get_premis_ip_object_element_spec():
    dirname = os.path.dirname(os.path.realpath(__file__))
    fname = 'templates/PremisIPObjectElementTemplate.json'
    with open(os.path.join(dirname, fname)) as json_file:
        return json.load(json_file)


def delete_path(path, remote_host=None, remote_credentials=None, task=None):
    logger = logging.getLogger('essarch')
    session = None
    if remote_credentials:
        session = requests.Session()
        session.verify = settings.REQUESTS_VERIFY
        credential_list = decrypt_remote_credentials(remote_credentials)
        if len(credential_list) == 1:
            token = credential_list[0]
            session.headers['Authorization'] = 'Token %s' % token
        else:
            user, passw = credential_list
            token = None
            session.auth = (user, passw)

        r = task.get_remote_copy(session, remote_host)
        if r.status_code == 404:
            # the task does not exist
            task.create_remote_copy(session, remote_host)
            task.run_remote_copy(session, remote_host)
        else:
            remote_data = r.json()
            task.status = remote_data['status']
            task.progress = remote_data['progress']
            task.result = remote_data['result']
            task.traceback = remote_data['traceback']
            task.exception = remote_data['exception']
            task.save()

            if task.status == celery_states.PENDING:
                task.run_remote_copy(session, remote_host)
            elif task.status != celery_states.SUCCESS:
                logger.debug('task.status: {}'.format(task.status))
                task.retry_remote_copy(session, remote_host)
                task.status = celery_states.PENDING

        while task.status not in celery_states.READY_STATES:
            session = requests.Session()
            session.verify = settings.REQUESTS_VERIFY
            if token:
                session.headers['Authorization'] = 'Token %s' % token
            else:
                session.auth = (user, passw)
            r = task.get_remote_copy(session, remote_host)

            remote_data = r.json()
            task.status = remote_data['status']
            task.progress = remote_data['progress']
            task.result = remote_data['result']
            task.traceback = remote_data['traceback']
            task.exception = remote_data['exception']
            task.save()

            sleep(5)

        if task.status in celery_states.EXCEPTION_STATES:
            task.reraise()
    else:
        try:
            shutil.rmtree(path)
        except NotADirectoryError:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            if os.name == 'nt':
                if e.errno == 267:
                    os.remove(path)
                elif e.errno != 3:
                    raise
            else:
                raise


def delete_content(folder):
    for entry in scandir(folder):
        if entry.is_file():
            os.remove(entry.path)
        elif entry.is_dir():
            shutil.rmtree(entry.path)


def find_and_replace_in_file(fname, old, new):
    filedata = None
    with open(fname, 'r') as f:
        filedata = f.read()

    # Replace the target string
    filedata = filedata.replace(old, new)

    # Write the file out again
    with open(fname, 'w') as f:
        f.write(filedata)
        f.flush()              # Flush Python buffer
        os.fsync(f.fileno())   # Flush OS buffer to disk


def run_shell_command(command, cwd):
    """
    Run command in shell and return results.
    """

    p = Popen(command, cwd=cwd, stdout=PIPE)
    stdout = p.communicate()[0]
    if stdout:
        stdout = stdout.strip()
    return stdout


def parse_content_range_header(header):
    content_range_pattern = re.compile(
        r'^bytes (?P<start>\d+)-(?P<end>\d+)/(?P<total>\d+)$'
    )

    match = content_range_pattern.match(header)

    if match:
        start = int(match.group('start'))
        end = int(match.group('end'))
        total = int(match.group('total'))

        return (start, end, total)
    else:
        raise ValidationError(detail="Invalid Content-Range header")


def chunks(chunks, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(chunks), n):
        yield chunks[i:i + n]


def flatten(flatten_list):
    """Flattens a list of lists"""
    return list(itertools.chain(*flatten_list))


def nested_lookup(key, document):
    """Finds all occurences of a key in nested dictionaries and lists"""
    if isinstance(document, list):
        for d in document:
            for result in nested_lookup(key, d):
                yield result

    if isinstance(document, dict):
        for k, v in document.items():
            if k == key:
                yield v
            elif isinstance(v, dict):
                for result in nested_lookup(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in nested_lookup(key, d):
                        yield result


def mptt_to_dict(node, serializer, context=None):
    result = serializer(instance=node, context=context).data
    children = [mptt_to_dict(c, serializer, context=context) for c in node.get_children()]
    if children:
        result['children'] = children
    return result


def get_script_directory():
    path = os.path.realpath(sys.argv[0])
    if os.path.isdir(path):
        return path
    else:
        return os.path.dirname(path)


def convert_file(path, new_format):
    logger = logging.getLogger('essarch')
    if sys.platform == "win32":
        cmd = ['python.exe', os.path.join(get_script_directory(), 'unoconv.py')]
    else:
        cmd = ['unoconv']
    cmd.extend(['-f', new_format, '-eSelectPdfVersion=1', path])
    logger.info(''.join(cmd))
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode:
        msg = '%s, return code: %s' % (err, p.returncode)
        raise ValueError(msg)

    new_path = os.path.splitext(path)[0] + '.' + new_format
    new_path = normalize_path(new_path)
    if not os.path.isfile(new_path):
        raise ValueError('No file created')

    if out:
        msg = '%s, return code: %s' % (out, p.returncode)
    else:
        msg = 'return code: %s' % (p.returncode,)

    logger.info('unoconv completed without error: %s' % (msg,))
    return new_path


def in_directory(path, directory):
    '''
    Checks if path is in directory

    See http://stackoverflow.com/questions/3812849/
    '''

    if path.rstrip('/ ') == directory.rstrip('/ '):
        return True

    directory = os.path.join(os.path.realpath(directory), '')
    path = os.path.join(os.path.realpath(path), '')

    return os.path.commonprefix([path, directory]) == directory


def validate_remote_url(url):
    regex = (r'''
        ^[a-z][a-z\d.+-]*:\/*(?:[^:@]+(?::[^@]+)?@)?(?:[^\s:/?#,]+|\[[a-f\d:]+])
        (?::\d+)?(?:\/[^?#]*)?(?:\?[^#]*)?(?:#.*)?,[^,]+,[^,]+$''')
    validate = RegexValidator(regex, 'Enter a valid URL with credentials.')
    validate(url)


def get_charset(byte_str):
    logger = logging.getLogger('essarch')
    decoded_flag = False
    guess = chardet.detect(byte_str)
    charsets = [settings.DEFAULT_CHARSET, 'utf-8', 'windows-1252']
    if guess['encoding'] is not None:
        charsets.append(guess['encoding'])
    for c in sorted(set(charsets), key=charsets.index):
        logger.debug('Trying to decode response in {}'.format(c))
        try:
            byte_str.decode(c)
            decoded_flag = True
            break
        except UnicodeDecodeError:
            continue

    if decoded_flag:
        logger.debug('Decoded response in {}'.format(c))
        return c
    else:
        logger.warning('Failed to decode response in {}'.format(sorted(set(charsets))))
        return None


def get_filename_from_file_obj(file_obj, name):
    filename = getattr(file_obj, 'name', None)
    filename = filename if (isinstance(filename, str) and filename) else name
    filename = os.path.basename(filename) if filename is not None else name
    return filename


def generate_file_response(file_obj, content_type, force_download=False, name=None):
    charset = get_charset(file_obj.read(128))
    file_obj.seek(0)

    content_type = '{}; charset={}'.format(content_type, charset)
    response = FileResponse(
        file_obj,
        content_type=content_type,
        as_attachment=force_download,
        filename=name,
    )

    if not force_download:
        filename = get_filename_from_file_obj(file_obj, name)

        if filename:
            try:
                filename.encode('ascii')
                file_expr = 'filename="{}"'.format(filename)
            except (UnicodeEncodeError, UnicodeDecodeError):
                file_expr = "filename*=utf-8''{}".format(quote(filename))
            response['Content-Disposition'] = 'inline; {}'.format(file_expr)

    # disable caching, required for Firefox to be able to load large files multiple times
    # see https://bugzilla.mozilla.org/show_bug.cgi?id=1436593
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"  # HTTP 1.1.
    response["Pragma"] = "no-cache"  # HTTP 1.0.
    response["Expires"] = "0"  # Proxies.

    return response


def list_files(path, force_download=False, expand_container=False, request=None, paginator=None):
    if isinstance(path, list):
        if paginator is not None:
            paginated = paginator.paginate_queryset(path, request)
            return paginator.get_paginated_response(paginated)
        return Response(path)

    fid = FormatIdentifier(allow_unknown_file_types=True)
    path = path.rstrip('/ ')

    if os.path.isfile(path):
        if expand_container and tarfile.is_tarfile(path):
            with tarfile.open(path) as tar:
                entries = []
                for member in tar.getmembers():
                    if not member.isfile():
                        continue

                    entries.append({
                        "name": member.name,
                        "type": 'file',
                        "size": member.size,
                        "modified": timestamp_to_datetime(member.mtime),
                    })
                if paginator is not None:
                    paginated = paginator.paginate_queryset(entries, request)
                    return paginator.get_paginated_response(paginated)
                return Response(entries)

        elif expand_container and zipfile.is_zipfile(path) and os.path.splitext(path)[1] == '.zip':
            with zipfile.ZipFile(path) as zipf:
                entries = []
                for member in zipf.filelist:
                    if member.filename.endswith('/'):
                        continue

                    entries.append({
                        "name": member.filename,
                        "type": 'file',
                        "size": member.file_size,
                        "modified": datetime(*member.date_time),
                    })
                if paginator is not None:
                    paginated = paginator.paginate_queryset(entries, request)
                    return paginator.get_paginated_response(paginated)
                return Response(entries)

        content_type = fid.get_mimetype(path)
        return generate_file_response(open(path, 'rb'), content_type, force_download)

    if os.path.isdir(path):
        entries = []
        for entry in sorted(get_files_and_dirs(path), key=lambda x: x.name):
            entry_type = "dir" if entry.is_dir() else "file"
            size, _ = get_tree_size_and_count(entry.path)

            entries.append(
                {
                    "name": os.path.basename(entry.path),
                    "type": entry_type,
                    "size": size,
                    "modified": timestamp_to_datetime(entry.stat().st_mtime),
                }
            )

        if paginator is not None and request is not None:
            paginated = paginator.paginate_queryset(entries, request)
            return paginator.get_paginated_response(paginated)

    if len(path.split('.tar/')) == 2:
        tar_path, tar_subpath = path.split('.tar/')
        tar_path += '.tar'

        with tarfile.open(tar_path) as tar:
            try:
                f = io.BytesIO(tar.extractfile(tar_subpath).read())
                content_type = fid.get_mimetype(tar_subpath)
                return generate_file_response(f, content_type, force_download, name=tar_subpath)
            except KeyError:
                raise NotFound

    if len(path.split('.zip/')) == 2:
        zip_path, zip_subpath = path.split('.zip/')
        zip_path += '.zip'

        with zipfile.ZipFile(zip_path) as zipf:
            try:
                f = io.BytesIO(zipf.read(zip_subpath))
                content_type = fid.get_mimetype(zip_subpath)
                return generate_file_response(f, content_type, force_download, name=zip_subpath)
            except KeyError:
                raise NotFound

    raise NotFound


def wait_for_chunks(chunks_path, timeout=2.0):
    """Wait up to `timeout` seconds for chunks to appear after last upload."""
    end = time.time() + timeout

    while time.time() < end:
        if glob.glob(chunks_path + "_*"):
            return True
        time.sleep(0.05)  # 50 ms

    return False


def merge_file_chunks(chunks_path, filepath):
    chunks = natsorted(glob.glob('%s_*' % re.sub(r'([\[\]])', '[\\1]', chunks_path)))
    if len(chunks) == 0:
        raise NoFileChunksFound

    with open(filepath, 'wb') as f:
        for chunk in chunks:
            with open(chunk, 'rb') as cf:
                f.write(cf.read())
            os.remove(chunk)
        f.flush()              # Flush Python buffer
        os.fsync(f.fileno())   # Flush OS buffer to disk


def turn_off_auto_now(ModelClass, field_name):
    def auto_now_off(field):
        field.auto_now = False
    do_to_model(ModelClass, field_name, auto_now_off)


def turn_on_auto_now(ModelClass, field_name):
    def auto_now_on(field):
        field.auto_now = True
    do_to_model(ModelClass, field_name, auto_now_on)


def turn_off_auto_now_add(ModelClass, field_name):
    def auto_now_add_off(field):
        field.auto_now_add = False
    do_to_model(ModelClass, field_name, auto_now_add_off)


def turn_on_auto_now_add(ModelClass, field_name):
    def auto_now_add_on(field):
        field.auto_now_add = True
    do_to_model(ModelClass, field_name, auto_now_add_on)


def do_to_model(ModelClass, field_name, func):
    field = ModelClass._meta.get_field(field_name)
    func(field)


def zip_directory(dirname=None, zipname=None, compress=False, arcroot=''):
    """
    Creates a ZIP file from the specified directory

    Args:
        dirname: The directory to create a ZIP from
        zipname: The name of the zip file
        compress: Compresses the zip file if true
    """
    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(zipname, 'w', compression) as new_zip:
        for root, dirs, files in walk(dirname):
            for d in dirs:
                filepath = os.path.join(root, d)
                arcname = os.path.join(arcroot, os.path.relpath(filepath, dirname))
                new_zip.write(filepath, arcname)
            for f in files:
                filepath = os.path.join(root, f)
                arcname = os.path.join(arcroot, os.path.relpath(filepath, dirname))
                new_zip.write(filepath, arcname)


def has_write_access(directory):
    if os.name == 'nt':
        try:
            # We want to use tempfile but there is a bug on Windows: https://bugs.python.org/issue22107
            # See also Stackoverflow link:
            # https://stackoverflow.com/questions/55109076/python-tempfile-temporaryfile-hangs-on-windows-when-no-write-privilege

            tmp_file = os.path.join(directory, str(uuid.uuid4()))
            with open(tmp_file, 'a') as f:
                f.write("")
            os.remove(tmp_file)
            return True
        except PermissionError:
            return False
    else:
        return os.access(directory, os.W_OK)


def open_file(path='', *args, container=None, container_prefix='', **kwargs):
    logger = logging.getLogger('essarch')
    if container is None:
        return open(path, *args, **kwargs)

    if container is not None and path:
        try:
            with tarfile.open(container) as tar:
                try:
                    f = tar.extractfile(path)
                except KeyError:
                    full_path = normalize_path(os.path.join(container_prefix, path))
                    f = tar.extractfile(full_path)
                return io.BytesIO(f.read())
        except tarfile.ReadError:
            logger.debug('Invalid tar file, trying zipfile instead')
            try:
                with zipfile.ZipFile(container) as zipf:
                    try:
                        f = zipf.open(path)
                    except KeyError:
                        full_path = normalize_path(os.path.join(container_prefix, path))
                        f = zipf.open(full_path)
                    return io.BytesIO(f.read())
            except zipfile.BadZipfile:
                logger.debug('Invalid zip file')
        except KeyError:
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), os.path.join(container, path))

    return open(os.path.join(container, path), *args, **kwargs)


def add_preservation_agent(generator, target=None, software_name='ESSArch', software_version=VERSION):
    if target is None:
        target = generator.find_element('metsHdr')

    template = {
        "-name": "agent",
        "-namespace": "mets",
        "-hideEmptyContent": True,
        "-attr": [
            {
                "-name": "ROLE",
                "-req": True,
                "#content": [{"text": "PRESERVATION"}]
            },
            {
                "-name": "TYPE",
                "-req": True,
                "#content": [{"text": "OTHER"}]
            },
            {
                "-name": "OTHERTYPE",
                "-req": True,
                "#content": [{"text": "SOFTWARE"}]
            }
        ],
        "-children": [
            {
                "-name": "name",
                "-namespace": "mets",
                "-req": True,
                "#content": [{"var": "preservation_software_name"}]
            },
            {
                "-name": "note",
                "-namespace": "mets",
                "-req": True,
                "#content": [{"var": "preservation_software_note"}]
            }
        ]
    }
    data = {
        "preservation_software_name": software_name,
        "preservation_software_note": 'VERSION={}'.format(software_version)
    }

    generator.insert_from_specification(
        target, template, data, before='altRecordID')


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if isinstance(val, bool):
        return val
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def dict_deep_merge(a: dict, b: dict):
    result = deepcopy(a)
    for bk, bv in b.items():
        av = result.get(bk)
        if isinstance(av, dict) and isinstance(bv, dict):
            result[bk] = dict_deep_merge(av, bv)
        else:
            result[bk] = deepcopy(bv)
    return result


def pretty_time_to_sec(time_in_sec):
    """
    Converts time in seconds to a human-readable string

    :param time_in_sec: Time in seconds
    :return: Human-readable string
    """
    if time_in_sec > 1:
        return round(time_in_sec, 2)
    else:
        return format(Decimal(time_in_sec), ".2g")


def pretty_size(bytes, unit=''):
    """
    Get human-readable file sizes.
    """

    units = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'KB'),
        (1, ('byte', 'bytes')),
    ]

    if unit and unit not in ('MB', 'GB', 'TB', 'PB'):
        raise ValueError('Invalid unit: {}'.format(unit))
    for factor, suffix in units:
        if unit:
            if suffix == unit:
                break
        elif bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple

    return '{} {}'.format(amount, suffix)


def pretty_mb_per_sec(mb_per_sec):
    """
    Converts MB/s to a human-readable string

    :param mb_per_sec: Speed in MB/s
    :return: Human-readable string
    """
    if mb_per_sec > 1:
        return round(mb_per_sec, 2)
    else:
        return format(Decimal(mb_per_sec), ".2g")


def natural_key(value):
    """
    Safely return a tuple for sorting that handles:
    - strings (natural sort)
    - datetime (sorted chronologically)
    - int, float
    - None (comes last)
    Ensures consistent types in all comparisons.
    """

    if value is None:
        return (1, [float('inf')])  # Sort None values to end

    # Try parsing datetime strings (e.g. "2021-01-01")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return (0, [parsed])
        except ValueError:
            pass  # Not a datetime string, treat as text

        # Natural sort for strings with numbers
        parts = re.split(r'(\d+)', value)
        return (0, [int(p) if p.isdigit() else p.lower() for p in parts])

    if isinstance(value, datetime):
        return (0, [value])

    if isinstance(value, (int, float)):
        return (0, [value])

    # Fallback: coerce to string
    return (0, [str(value).lower()])
