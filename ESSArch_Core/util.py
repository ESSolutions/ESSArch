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
import os
import platform
import pyclbr
import re
import shutil

from rest_framework.exceptions import ValidationError
from django.utils.timezone import get_current_timezone
from django.core.validators import RegexValidator

from datetime import datetime

from lxml import etree

from scandir import scandir

from subprocess import Popen, PIPE

import requests

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"


def sliceUntilAttr(iterable, attr, val):
    for i in iterable:
        if getattr(i, attr) == val:
            return
        yield i


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def get_elements_without_namespace(root, path):
    els = path.split("/")
    return root.xpath(".//" + "/".join(["*[local-name()='%s']" % e for e in els]))


def get_value_from_path(el, path):
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

    if "@" in path:
        try:
            nested, attr = path.split('@')
            try:
                el = get_elements_without_namespace(el, nested)[0]
            except IndexError:
                pass

            if el is None:
                return None
        except (ValueError, SyntaxError):
            attr = path[1:]

        for a, val in el.attrib.iteritems():
            if re.sub(r'{.*}', '', a) == attr:
                return val
    else:
        try:
            el = get_elements_without_namespace(el, path)[0]
        except IndexError:
            pass

        try:
            return el.text
        except AttributeError:
            pass


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


def get_tree_size_and_count(path='.'):
    """Return total size and count of files in given path and subdirs."""

    if os.path.isfile(path):
        return os.path.getsize(path), 1

    total_size = 0
    count = 0

    for dirpath, dirnames, filenames in os.walk(path):
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
        return valid[algname]
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
    for i in range(0, len(l), n):
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
