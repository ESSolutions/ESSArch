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

import os
import uuid

from lxml import etree

import six

from ESSArch_Core.configuration.models import Parameter
from ESSArch_Core.fixity import checksum, format, validation

from ESSArch_Core.util import (
    creation_date,
    get_value_from_path,
    getSchemas,
    remove_prefix,
    timestamp_to_datetime,
    win_to_posix,
)

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

# File elements in different metadata standards
FILE_ELEMENTS = {
    "file": {
        "path": "FLocat@href",
        "pathprefix": ["file:///", "file:"],
        "checksum": "@CHECKSUM",
        "checksumtype": "@CHECKSUMTYPE",
        "format": "@FILEFORMATNAME",
    },
    "mdRef": {
        "path": "@href",
        "pathprefix": ["file:///", "file:"],
        "checksum": "@CHECKSUM",
        "checksumtype": "@CHECKSUMTYPE",
    },
    "object": {
        "path": "objectIdentifier/objectIdentifierValue",
        "pathprefix": ["file:///", "file:"],
        "including_root": True,
        "checksum": "objectCharacteristics/fixity/messageDigest",
        "checksumtype": "objectCharacteristics/fixity/messageDigestAlgorithm",
        "format": "objectCharacteristics/format/formatDesignation/formatName",
    },
}

PTR_ELEMENTS = {
    "mptr": {
        "path": "@href",
        "pathprefix": ["file:///", "file:"]
    }
}


def get_agent(el, ROLE=None, OTHERROLE=None, TYPE=None, OTHERTYPE=None):
    s = ".//*[local-name()='agent']"

    if ROLE:
        s += "[@ROLE='%s']" % ROLE

    if OTHERROLE:
        s += "[@OTHERROLE='%s']" % OTHERROLE

    if TYPE:
        s += "[@TYPE='%s']" % TYPE

    if OTHERTYPE:
        s += "[@OTHERTYPE='%s']" % OTHERTYPE

    try:
        first = el.xpath(s)[0]
    except IndexError:
        return None

    return {
        'name': first.xpath("*[local-name()='name']")[0].text,
        'notes': [note.text for note in first.xpath("*[local-name()='note']")]
    }


def get_agents(el):
    agent_els = el.xpath(".//*[local-name()='agent']")
    agents = []

    for agent_el in agent_els:
        agent = {
            '_AGENTS_NAME': agent_el.xpath("*[local-name()='name']")[0].text,
            '_AGENTS_NOTES': [{'_AGENTS_NOTE': note.text} for note in agent_el.xpath("*[local-name()='note']")],
        }
        for key, val in six.iteritems(agent_el.attrib):
            agent['_AGENTS_%s' % key.upper()] = val

        agents.append(agent)

    return agents


def get_altrecordids(el):
    dct = {}
    for i in el.xpath(".//*[local-name()='altRecordID']"):
        try:
            dct[i.get('TYPE')].append(i.text)
        except KeyError:
            dct[i.get('TYPE')] = [i.text]

    return dct


def get_altrecordid(el, TYPE):
    return [e.text for e in el.xpath(".//*[local-name()='altRecordID'][@TYPE='%s']" % TYPE)]


def get_objectpath(el):
    try:
        e = el.xpath('.//*[local-name()="%s"]' % "FLocat")[0]
        if e is not None:
            val = get_value_from_path(e, "@href")
            try:
                return val.split('file:///')[1]
            except IndexError:
                return val
    except IndexError:
        return None


def parse_reference_code(code):
    return code.strip('/ ').split('/')


def parse_submit_description(xmlfile, srcdir=''):
    ip = {}
    doc = etree.parse(xmlfile)
    root = doc.getroot()

    if root.xpath('local-name()').lower() != 'mets':
        raise ValueError('%s is not a valid mets file' % xmlfile)

    try:
        # try getting objid with prefix
        ip['id'] = root.attrib['OBJID'].split(':')[1]
    except IndexError:
        # no prefix, try getting objid without prefix
        ip['id'] = root.attrib['OBJID']
    except KeyError:
        # no objid available, use the name of the xml file
        ip['id'] = os.path.splitext(os.path.basename(xmlfile))[0]

    ip['object_identifier_value'] = ip['id']
    ip['label'] = root.get('LABEL', '')

    try:
        ip['create_date'] = root.find("{*}metsHdr").get('CREATEDATE')
        ip['entry_date'] = ip['create_date']
    except AttributeError:
        pass

    objpath = get_objectpath(root)

    if objpath:
        ip['object_path'] = os.path.join(srcdir, objpath)
        ip['object_size'] = os.stat(ip['object_path']).st_size

    ip['information_class'] = get_value_from_path(root, '@INFORMATIONCLASS')

    ip['altrecordids'] = get_altrecordids(root)

    ip['start_date'] = ip['altrecordids'].get('STARTDATE', [None])[0]
    ip['end_date'] = ip['altrecordids'].get('ENDDATE', [None])[0]

    codes = ip['altrecordids'].get('REFERENCECODE', [])
    ip['reference_codes'] = [parse_reference_code(code) for code in codes]

    if ip['information_class'] is None:
        try:
            ip['information_class'] = ip['altrecordids'].get('INFORMATIONCLASS')[0]
        except TypeError:
            ip['information_class'] = None

    try:
        ip['information_class'] = [int(s) for s in ip['information_class'].split() if s.isdigit()][0]
    except (KeyError, AttributeError):
        ip['information_class'] = 0

    try:
        ip['archivist_organization'] = {
            'name': get_agent(root, ROLE='ARCHIVIST', TYPE='ORGANIZATION')['name']
        }
    except TypeError:
        pass

    ip['_AGENTS'] = get_agents(root)

    agents = {
        'creator_organization': {
            'ROLE': 'CREATOR', 'TYPE': 'ORGANIZATION',
        },
        'submitter_organization': {
            'ROLE': 'OTHER', 'OTHERROLE': 'SUBMITTER', 'TYPE': 'ORGANIZATION',
        },
        'submitter_individual': {
            'ROLE': 'OTHER', 'OTHERROLE': 'SUBMITTER', 'TYPE': 'INDIVIDUAL',
        },
        'producer_organization': {
            'ROLE': 'OTHER', 'OTHERROLE': 'PRODUCER', 'TYPE': 'ORGANIZATION',
        },
        'producer_individual': {
            'ROLE': 'OTHER', 'OTHERROLE': 'PRODUCER', 'TYPE': 'INDIVIDUAL',
        },
        'ipowner_organization': {
            'ROLE': 'IPOWNER', 'TYPE': 'ORGANIZATION',
        },
        'preservation_organization': {
            'ROLE': 'PRESERVATION', 'TYPE': 'ORGANIZATION',
        },
        'system_name': {
            'ROLE': 'ARCHIVIST', 'TYPE': 'OTHER', 'OTHERTYPE': 'SOFTWARE',
        },
    }


    for key, value in agents.iteritems():
        try:
            ip[key] = get_agent(root, **value)['name']
        except TypeError:
            pass

    try:
        ip['system_version'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][0],
    except TypeError:
        pass

    try:
        ip['system_type'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][1],
    except TypeError:
        pass

    return ip


class XMLFileElement():
    def __init__(self, el, props):
        '''
        args:
            el: lxml.etree._Element
            props: 'dict with properties from FILE_ELEMENTS'
        '''

        self.path = get_value_from_path(el, props.get('path', ''))
        self.path_prefix = props.get('pathprefix', [])
        for prefix in sorted(self.path_prefix, key=len, reverse=True):
            no_prefix = remove_prefix(self.path, prefix)

            if no_prefix != self.path:
                self.path = no_prefix
                break

        self.path = self.path.lstrip('/ ')

        self.checksum = get_value_from_path(el, props.get('checksum', ''))
        self.checksum_type = get_value_from_path(el, props.get('checksumtype', ''))

        self.format = get_value_from_path(el, props.get('format', ''))

    def __eq__(self, other):
        '''
        Two objects are equal if their paths are equal. If other is a
        string, we assume its a path and compares it as is
        '''

        if isinstance(other, six.string_types):
            return self.path == other

        return self.path == other.path

    def __hash__(self):
        return hash(self.path)


def find_pointers(xmlfile):
    doc = etree.ElementTree(file=xmlfile)

    for elname, props in PTR_ELEMENTS.iteritems():
        for ptr in doc.xpath('.//*[local-name()="%s"]' % elname):
            yield XMLFileElement(ptr, props)


def find_files(xmlfile, rootdir='', prefix='', skip_files=None):
    doc = etree.ElementTree(file=xmlfile)
    files = set()

    if skip_files is None:
        skip_files = []

    for elname, props in FILE_ELEMENTS.iteritems():
        file_elements = doc.xpath('.//*[local-name()="%s"]' % elname)

        # Remove first object in premis file if it is a "fake" entry describing the tar
        if len(file_elements) and file_elements[0].get('{%s}type' % XSI_NAMESPACE) == 'premis:file':
            if len(file_elements[0].xpath('.//*[local-name()="formatName"][. = "TAR"]')):
                file_elements.pop(0)

        for el in file_elements:
            file_el = XMLFileElement(el, props)
            file_el.path = os.path.join(prefix, file_el.path)
            if props.get('including_root', False):
                path_arr = file_el.path.split('/')
                path_arr.pop(0)
                file_el.path = '/'.join(path_arr)

            if file_el.path in skip_files:
                continue

            files.add(file_el)

    for pointer in find_pointers(xmlfile):
        pointer_prefix = os.path.split(pointer.path)[0]
        files.add(pointer)
        files |= find_files(os.path.join(rootdir, pointer.path), rootdir, pointer_prefix)

    return files


def parse_file(filepath, mimetype, fid, relpath=None, algorithm='SHA-256', rootdir=''):
    if not relpath:
        relpath = filepath

    relpath = win_to_posix(relpath)

    timestamp = creation_date(filepath)
    createdate = timestamp_to_datetime(timestamp)

    digest = checksum.calculate_checksum(filepath, algorithm)
    (format_name, format_version, format_registry_key) = fid.identify_file_format(filepath)

    fileinfo = {
        'FName': os.path.basename(relpath),
        'FExtension': os.path.splitext(relpath)[1],
        'FDir': rootdir,
        'FParentDir': os.path.basename(os.path.dirname(filepath)),
        'FChecksum': digest,
        'FID': str(uuid.uuid4()),
        'daotype': "borndigital",
        'href': relpath,
        'FMimetype': mimetype,
        'FCreated': createdate.isoformat(),
        'FFormatName': format_name,
        'FFormatVersion': format_version,
        'FFormatRegistryKey': format_registry_key,
        'FSize': str(os.path.getsize(filepath)),
        'FUse': 'Datafile',
        'FChecksumType': algorithm,
        'FLoctype': 'URL',
        'FLinkType': 'simple',
        'FChecksumLib': 'ESSArch',
        'FIDType': 'UUID',
    }

    return fileinfo


def validate_against_schema(xmlfile, schema=None, rootdir=None):
    doc = etree.ElementTree(file=xmlfile)

    if schema:
        xmlschema = etree.XMLSchema(etree.parse(schema))
    else:
        xmlschema = getSchemas(doc=doc)

    xmlschema.assertValid(doc)

    if rootdir is None:
        rootdir = os.path.split(xmlfile)[0]

    for ptr in find_pointers(xmlfile):
        if not validate_against_schema(os.path.join(rootdir, ptr.path), schema):
            return False

    return xmlschema.validate(doc)
