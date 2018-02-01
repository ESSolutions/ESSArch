"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from __future__ import absolute_import

import errno
import hashlib
import itertools
import json
import mimetypes
import os
import platform
import pyclbr
import re
import shutil
import tarfile
import zipfile

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from django.utils.encoding import smart_text
from django.utils.timezone import get_current_timezone
from django.core.validators import RegexValidator
from django.http.response import HttpResponse

from datetime import datetime

from lxml import etree

from scandir import scandir, walk

from subprocess import Popen, PIPE

from ESSArch_Core.configuration.models import Path

import requests

import six

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


def make_unicode(text):
    try:
        return six.text_type(text, 'utf-8')
    except TypeError:
        if not isinstance(text, six.string_types):
            return six.text_type(text)

        return text


def sliceUntilAttr(iterable, attr, val):
    for i in iterable:
        if getattr(i, attr) == val:
            return
        yield i


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def get_elements_without_namespace(root, path, value=None):
    element_path = []
    splits = path.split("/")
    for idx, split in enumerate(splits):
        if "@" in split:
            el, attr = split.split("@")
            if value is not None:
                split_path = '*[local-name()="{el}" and @*[local-name()="{attr}"]="{value}"]'.format(el=el, attr=attr, value=value)
            else:
                split_path = '*[local-name()="{el}" and @*[local-name()="{attr}"]]'.format(el=el, attr=attr)
        else:
            if idx == len(splits)-1 and value is not None and "@" not in path:
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

    if path is None:
        return None

    if path.startswith('@'):
        attr = path[1:]
        for a, val in six.iteritems(root.attrib):
            if re.sub(r'{.*}', '', a) == attr:
                return val

    try:
        el = get_elements_without_namespace(root, path)[0]
        if root == el:
            return None
    except IndexError:
        return None

    if "@" in path:
        attr = path.split('@')[1]
        try:
            return el.xpath("@*[local-name()='%s'][1]" % attr)[0]
        except IndexError:
            return None

    return el.text


def available_tasks():
    modules = ["preingest.tasks", "ESSArch_Core.WorkflowEngine.tests.tasks"]
    tasks = []
    for m in modules:
        try:
            module_tasks = pyclbr.readmodule(m)
            tasks = tasks + zip(
                [m+"."+t for t in module_tasks],
                module_tasks
            )
        except ImportError:
            continue
    return tasks


def create_event(eventType, eventOutcome, eventOutcomeDetailNote, version, agent, application=None, ip=None):
    """
    Creates a new event and saves it to the database

    Args:
        eventType: The event type
        eventOutcome: Success (0) or Fail (1)
        eventOutcomeDetailNote: The result or traceback of the task depending on the outcome
        agent: The agent creating the event
        ip: The information package connected to the event

    Returns:
        The created event
    """

    from ESSArch_Core.ip.models import EventIP

    try:
        e = EventIP.objects.create(
            eventType=eventType, eventOutcome=eventOutcome, eventVersion=version,
            eventOutcomeDetailNote=eventOutcomeDetailNote,
            linkingAgentIdentifierValue=agent, linkingObjectIdentifierValue=ip,
        )

        if application:
            e.eventApplication = application
            e.save()

    except:
        print application
        raise

    return e


def getSchemas(doc=None, filename=None):
    """
        Creates a schema based on the schemas specified in the provided XML
        file's schemaLocation attribute
    """

    if filename:
        try:
            doc = etree.ElementTree(file=filename)
        except etree.XMLSyntaxError:
            raise
        except IOError:
            raise

    res = []
    root = doc.getroot()
    xsi_NS = "%s" % root.nsmap['xsi']

    xsd_NS = "{%s}" % XSD_NAMESPACE
    NSMAP = {'xsd': XSD_NAMESPACE}

    root = etree.Element(xsd_NS + "schema", nsmap=NSMAP)
    root.attrib["elementFormDefault"] = "qualified"

    schema_locations = set(doc.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': xsi_NS}))
    for schema_location in schema_locations:
        ns_locs = schema_location.split()
        for ns, loc in zip(ns_locs[:-1], ns_locs[1:]):
            res.append([ns, loc])
            etree.SubElement(root, xsd_NS + "import", attrib={
                "namespace": ns,
                "schemaLocation": loc
            })

    return etree.XMLSchema(root)


def move_schema_locations_to_root(tree=None, filename=None):
    """
    Move all schemaLocation attributes in the document to the root element
    """

    if filename:
        tree = etree.parse(filename)

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
        name = content.get('name')
        if content.get('use') == use:
            return path, name

        dest, fname = find_destination(
            use, content.get('children', []), os.path.join(path, name)
        )

        if dest: return dest, fname

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

    if os.path.isfile(path):
        return os.path.getsize(path), 1

    total_size = 0
    count = 0

    for dirpath, dirnames, filenames in walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
            count += 1

    return total_size, count


def win_to_posix(path):
    return path.replace('\\', '/')


def alg_from_str(algname):
    valid = {
        "MD5": hashlib.md5,
        "SHA-1": hashlib.sha1,
        "SHA-224": hashlib.sha224,
        "SHA-256": hashlib.sha256,
        "SHA-384": hashlib.sha384,
        "SHA-512": hashlib.sha512
    }

    try:
        return valid[algname.upper()]
    except:
        raise KeyError("Algorithm %s does not exist" % algname)


def mkdir_p(path):
    """
    http://stackoverflow.com/a/600612/1523238
    """

    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def get_event_spec():
    dirname = os.path.dirname(os.path.realpath(__file__))
    fname = 'templates/JSONPremisEventTemplate.json'
    with open(os.path.join(dirname, fname)) as json_file:
        return json.load(json_file)


def truncate(text, max_len, suffix=' (truncated)'):
    if len(text) > max_len:
        return text[:max_len - len(suffix)] + suffix

    return text


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


def run_shell_command(command, cwd):
    """
    Run command in shell and return results.
    """

    p = Popen(command, shell=True, cwd=cwd, stdout=PIPE)
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


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in six.moves.range(0, len(l), n):
        yield l[i:i + n]


def flatten(l):
    """Flattens a list of lists"""
    return list(itertools.chain(*l))


def nested_lookup(key, document):
    """Finds all occurences of a key in nested dictionaries and lists"""
    if isinstance(document, list):
        for d in document:
            for result in nested_lookup(key, d):
                yield result

    if isinstance(document, dict):
        for k, v in document.iteritems():
            if k == key:
                yield v
            elif isinstance(v, dict):
                for result in nested_lookup(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in nested_lookup(key, d):
                        yield result


def convert_file(path, new_format):
    cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % (new_format, path)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode:
        raise ValueError('%s, return code: %s' % (err, p.returncode))

    return out

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
    regex = '^[a-z][a-z\d.+-]*:\/*(?:[^:@]+(?::[^@]+)?@)?(?:[^\s:/?#,]+|\[[a-f\d:]+])(?::\d+)?(?:\/[^?#]*)?(?:\?[^#]*)?(?:#.*)?,[^,]+,[^,]+$'
    validate = RegexValidator(regex, 'Enter a valid URL with credentials.')
    validate(url)


def generate_file_response(file_obj, content_type, force_download=False):
    response = HttpResponse(file_obj.read(), content_type=content_type)
    response['Content-Disposition'] = 'inline; filename=%s' % os.path.basename(file_obj.name)
    if force_download or content_type is None:
        response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_obj.name)
    return response

def list_files(path, force_download=False, request=None, paginator=None):
    mimetypes.suffix_map = {}
    mimetypes.encodings_map = {}
    mimetypes.types_map = {}
    mimetypes.common_types = {}
    mimetypes_file = Path.objects.get(
        entity="path_mimetypes_definitionfile"
    ).value
    mimetypes.init(files=[mimetypes_file])
    mtypes = mimetypes.types_map

    path = path.rstrip('/ ')
    path = smart_text(path).encode('utf-8')

    if os.path.isfile(path):
        if tarfile.is_tarfile(path):
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

        elif zipfile.is_zipfile(path) and (os.path.splitext(path)[1] not in ('.doc', '.docx')):
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

        content_type = mtypes.get(os.path.splitext(path)[1])
        return generate_file_response(open(path), content_type, force_download)

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
                member = tar.getmember(tar_subpath)

                if not member.isfile():
                    raise NotFound

                f = tar.extractfile(member)
                content_type = mtypes.get(os.path.splitext(tar_subpath)[1])
                return generate_file_response(f, content_type, force_download)
            except KeyError:
                raise NotFound

    if len(path.split('.zip/')) == 2:
        zip_path, zip_subpath = path.split('.zip/')
        tar_path += '.zip'

        with zipfile.open(zip_path) as zipf:
            try:
                f = zipf.open(zip_subpath)
                content_type = mtypes.get(os.path.splitext(zip_subpath)[1])
                return generate_file_response(f, content_type, force_download)
            except KeyError:
                raise NotFound

    raise NotFound


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
