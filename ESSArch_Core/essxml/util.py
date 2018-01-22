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
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.fixity import checksum, format, validation

from ESSArch_Core.util import (
    creation_date,
    get_elements_without_namespace,
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
        "path": ["objectIdentifier/objectIdentifierValue", "storage/contentLocation/contentLocationValue"],
        "pathprefix": ["file:///", "file:"],
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

    first = el.xpath(s)[0]
    return {
        'name': first.xpath("*[local-name()='name']")[0].text,
        'notes': [note.text for note in first.xpath("*[local-name()='note']")]
    }


def get_agents(el):
    agent_els = el.xpath(".//*[local-name()='agent']")
    agents = []

    for agent_el in agent_els:
        try:
            agent = {
                '_AGENTS_NAME': agent_el.xpath("*[local-name()='name']")[0].text,
                '_AGENTS_NOTES': [{'_AGENTS_NOTE': note.text} for note in agent_el.xpath("*[local-name()='note']")],
            }
        except IndexError:
            # agent without name, skip to next
            continue
        else:
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

    ip['_AGENTS'] = get_agents(root)

    agents = {
        'archivist_organization': {
            'ROLE': 'ARCHIVIST', 'TYPE': 'ORGANIZATION',
        },
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
        except IndexError:
            pass

    try:
        ip['system_version'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][0],
    except IndexError:
        pass

    try:
        ip['system_type'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][1],
    except IndexError:
        pass

    return ip


def parse_event(el):
    '''
    Parses a Premis event element

    Args:
        el: A lxml etree element

    Returns:
        An EventIP object describing the event
    '''

    def from_path(p):
        return '/'.join([("*[local-name()='%s']" % part) for part in p.split('/')])

    event_dict = {
        'identifier': {
            'type': el.xpath(from_path('eventIdentifier/eventIdentifierType'))[0].text,
            'value': el.xpath(from_path('eventIdentifier/eventIdentifierValue'))[0].text
        },
        'type': el.xpath(from_path('eventType'))[0].text,
        'datetime': el.xpath(from_path('eventDateTime'))[0].text,
        'detail': el.xpath(from_path('eventDetailInformation/eventDetail'))[0].text,
        'outcome_information': {
            'outcome': el.xpath(from_path('eventOutcomeInformation/eventOutcome'))[0].text,
            'outcome_detail_note': el.xpath(from_path('eventOutcomeInformation/eventOutcomeDetail/eventOutcomeDetailNote'))[0].text,
        },
        'linking_agent_identifier': {
            'type': el.xpath(from_path('linkingAgentIdentifier/linkingAgentIdentifierType'))[0].text,
            'value': el.xpath(from_path('linkingAgentIdentifier/linkingAgentIdentifierValue'))[0].text
        },
        'linking_object_identifier': {
            'type': el.xpath(from_path('linkingObjectIdentifier/linkingObjectIdentifierType'))[0].text,
            'value': el.xpath(from_path('linkingObjectIdentifier/linkingObjectIdentifierValue'))[0].text
        },
    }

    objid = event_dict['linking_object_identifier']['value']
    username = event_dict['linking_agent_identifier']['value']

    try:
        ip = str(InformationPackage.objects.get(object_identifier_value=objid).pk)
    except InformationPackage.DoesNotExist:
        ip = objid

    return EventIP(
        eventIdentifierValue=event_dict['identifier']['value'],
        eventType_id=event_dict['type'],
        eventDateTime=event_dict['datetime'],
        eventOutcome=event_dict['outcome_information']['outcome'],
        eventOutcomeDetailNote=event_dict['outcome_information']['outcome_detail_note'],
        linkingAgentIdentifierValue=username,
        linkingObjectIdentifierValue=ip,
    )

def parse_event_file(xmlfile):
    root = etree.parse(xmlfile).getroot()
    return [parse_event(el) for el in root.xpath("./*[local-name()='event']")]

class XMLFileElement():
    def __init__(self, el, props, path=None, rootdir=None):
        '''
        args:
            el: lxml.etree._Element
            props: 'dict with properties from FILE_ELEMENTS'
        '''

        self.path = path
        if self.path is None:
            self.paths = props.get('path', [''])

            if isinstance(self.paths, six.string_types):
                self.paths = [self.paths]

            for path in self.paths:
                self.path = get_value_from_path(el, path)

                if self.path is not None:
                    break

            self.path_prefix = props.get('pathprefix', [])
            for prefix in sorted(self.path_prefix, key=len, reverse=True):
                no_prefix = remove_prefix(self.path, prefix)

                if no_prefix != self.path:
                    self.path = no_prefix
                    break

            if rootdir is not None:
                self.path = remove_prefix(self.path, os.path.basename(rootdir))

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


def find_pointers(xmlfile=None, tree=None):
    if xmlfile is None and tree is None:
        raise ValueError("Need xmlfile or tree, both can't be None")

    if xmlfile is not None:
        tree = etree.ElementTree(file=xmlfile)

    for elname, props in PTR_ELEMENTS.iteritems():
        for ptr in tree.xpath('.//*[local-name()="%s"]' % elname):
            yield XMLFileElement(ptr, props)


def find_file(filepath, xmlfile=None, tree=None, rootdir='', prefix=''):
    if xmlfile is None and tree is None:
        raise ValueError("Need xmlfile or tree, both can't be None")

    if xmlfile is not None:
        tree = etree.ElementTree(file=xmlfile)

    root = tree.getroot()

    for elname, props in six.iteritems(FILE_ELEMENTS):
        for prefix in props.get('pathprefix', []) + ['']:
            fullpath = prefix + filepath

            props_paths = props.get('path')
            if isinstance(props_paths, six.string_types):
                props_paths = [props_paths]

            for props_path in props_paths:
                el = get_elements_without_namespace(root, '%s/%s' % (elname, props_path), fullpath)
                if len(el) > 0:
                    el = el[0]
                    while el.xpath('local-name()') != elname:
                        el = el.getparent()
                    xml_el = XMLFileElement(el, props, path=filepath)
                    return xml_el, el

    for pointer in find_pointers(tree=tree):
        pointer_prefix = os.path.split(pointer.path)[0]
        xml_el, el = find_file(filepath, xmlfile=os.path.join(rootdir, pointer.path), rootdir=rootdir, prefix=pointer_prefix)
        if xml_el is not None:
            return xml_el, el


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
            file_el = XMLFileElement(el, props, rootdir=rootdir)
            file_el.path = os.path.join(prefix, file_el.path)

            if file_el.path in skip_files:
                continue

            files.add(file_el)

    for pointer in find_pointers(xmlfile=xmlfile):
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
        validate_against_schema(os.path.join(rootdir, ptr.path), schema)
