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

from lxml import etree

from ESSArch_Core.util import getSchemas, get_value_from_path, remove_prefix

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
        "path": "storage/contentLocation/contentLocationValue",
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

    try:
        first = el.xpath(s)[0]
    except IndexError:
        return None

    return {
        'name': first.xpath("*[local-name()='name']")[0].text,
        'notes': [note.text for note in first.xpath("*[local-name()='note']")]
    }


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

    try:
        ip['id'] = root.attrib['OBJID'].split(':')[1]
    except IndexError:
        ip['id'] = root.attrib['OBJID']
    except KeyError:
        ip['id'] = os.path.splitext(os.path.basename(xmlfile))[0]

    ip['object_identifier_value'] = ip['id']
    ip['label'] = root.get('LABEL', '')
    ip['create_date'] = root.find("{*}metsHdr").get('CREATEDATE')

    objpath = get_objectpath(root)

    if objpath:
        ip['object_path'] = os.path.join(srcdir, objpath)
        ip['object_size'] = os.stat(ip['object_path']).st_size

    ip['information_class'] = get_value_from_path(root, '@INFORMATIONCLASS')

    ip['altrecordids'] = get_altrecordids(root)

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

    try:
        ip['creator_organization'] = get_agent(root, ROLE='CREATOR', TYPE='ORGANIZATION')['name']
    except TypeError:
        pass

    try:
        ip['submitter_organization'] = get_agent(root, ROLE='OTHER', OTHERROLE='SUBMITTER', TYPE='ORGANIZATION')['name']
    except TypeError:
        pass

    try:
        ip['submitter_individual'] = get_agent(root, ROLE='OTHER', OTHERROLE='SUBMITTER', TYPE='INDIVIDUAL')['name']
    except TypeError:
        pass

    try:
        ip['producer_organization'] = get_agent(root, ROLE='OTHER', OTHERROLE='PRODUCER', TYPE='ORGANIZATION')['name']
    except TypeError:
        pass

    try:
        ip['producer_individual'] = get_agent(root, ROLE='OTHER', OTHERROLE='PRODUCER', TYPE='INDIVIDUAL')['name']
    except TypeError:
        pass

    try:
        ip['ipowner_organization'] = get_agent(root, ROLE='IPOWNER', TYPE='ORGANIZATION')['name']
    except TypeError:
        pass

    try:
        ip['preservation_organization'] = get_agent(root, ROLE='PRESERVATION', TYPE='ORGANIZATION')['name']
    except TypeError:
        pass

    try:
        ip['system_name'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['name']
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

        if isinstance(other, basestring):
            return self.path == other

        return self.path == other.path

    def __hash__(self):
        return hash(self.path)


def find_pointers(xmlfile):
    doc = etree.ElementTree(file=xmlfile)

    for elname, props in PTR_ELEMENTS.iteritems():
        for ptr in doc.xpath('.//*[local-name()="%s"]' % elname):
            yield XMLFileElement(ptr, props)


def find_files(xmlfile, rootdir='', prefix=''):
    doc = etree.ElementTree(file=xmlfile)
    files = set()

    for elname, props in FILE_ELEMENTS.iteritems():
        for el in doc.xpath('.//*[local-name()="%s"]' % elname):
            file_el = XMLFileElement(el, props)
            file_el.path = os.path.join(prefix, file_el.path)
            files.add(file_el)

    for pointer in find_pointers(xmlfile):
        pointer_prefix = os.path.split(pointer.path)[0]
        files.add(pointer)
        files |= find_files(os.path.join(rootdir, pointer.path), rootdir, pointer_prefix)

    return files


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
