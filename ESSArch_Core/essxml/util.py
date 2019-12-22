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

import logging
import os
import pathlib
import re
import tempfile
import uuid
from urllib.parse import urlparse

from lxml import etree

from ESSArch_Core.fixity import checksum
from ESSArch_Core.util import (
    creation_date,
    get_elements_without_namespace,
    get_value_from_path,
    getSchemas,
    normalize_path,
    remove_prefix,
    timestamp_to_datetime,
    win_to_posix,
)

logger = logging.getLogger('essarch')

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
        "size": "@SIZE",
    },
    "mdRef": {
        "path": "@href",
        "pathprefix": ["file:///", "file:"],
        "checksum": "@CHECKSUM",
        "checksumtype": "@CHECKSUMTYPE",
        "size": "@SIZE",
    },
    "object": {
        "path_includes_root": True,
        "path": ["objectIdentifier/objectIdentifierValue", "storage/contentLocation/contentLocationValue"],
        "pathprefix": ["file:///", "file:"],
        "checksum": "objectCharacteristics/fixity/messageDigest",
        "checksumtype": "objectCharacteristics/fixity/messageDigestAlgorithm",
        "size": "objectCharacteristics/size",
        "format": "objectCharacteristics/format/formatDesignation/formatName",
    },
    "Bilaga": {
        "path": ["@Lank"],
        "pathprefix": ["file:///", "file:"],
        "checksum": "@Checksumma",
        "checksumtype": "@ChecksummaMetod",
        "size": "@Storlek",
    },
}

PTR_ELEMENTS = {
    "mptr": {
        "path": "@href",
        "pathprefix": ["file:///", "file:"]
    }
}


def get_premis_ref(tree):
    elname = 'mdRef'
    props = FILE_ELEMENTS[elname]
    for ptr in tree.xpath('.//*[local-name()="%s"]' % elname):
        return XMLFileElement(ptr, props)

    return None


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
    return el.xpath(".//*[local-name()='agent']")


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


def parse_mets(xmlfile):
    data = {}
    doc = etree.parse(xmlfile)
    root = doc.getroot()

    if root.xpath('local-name()').lower() != 'mets':
        raise ValueError('%s is not a valid mets file' % xmlfile)

    # save root attributes without namespace prefix
    localname_pattern = re.compile(r'^(?:{[^{}]*})?(.*)$')
    for k, v in root.attrib.items():
        data[re.search(localname_pattern, k).group(1)] = v

    data['agents'] = {}
    for a in get_agents(root):
        other_role = a.get("ROLE") == 'OTHER'
        other_type = a.get("TYPE") == 'OTHER'
        agent_role = a.get("OTHERROLE") if other_role else a.get("ROLE")
        agent_type = a.get("OTHERTYPE") if other_type else a.get("TYPE")
        name = a.xpath('*[local-name()="name"]')[0].text
        notes = [n.text for n in a.xpath('*[local-name()="note"]')]
        data['agents']['{role}_{type}'.format(role=agent_role, type=agent_type)] = {'name': name, 'notes': notes}

    return data


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
        if ip['information_class'] is not None:
            raise

    ip['agents'] = {}
    for a in get_agents(root):
        other_role = a.get("ROLE") == 'OTHER'
        other_type = a.get("TYPE") == 'OTHER'
        agent_role = a.get("OTHERROLE") if other_role else a.get("ROLE")
        agent_type = a.get("OTHERTYPE") if other_type else a.get("TYPE")
        name = a.xpath('*[local-name()="name"]')[0].text
        notes = [n.text for n in a.xpath('*[local-name()="note"]')]
        ip['agents']['{role}_{type}'.format(role=agent_role, type=agent_type)] = {'name': name, 'notes': notes}

    try:
        ip['system_version'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][0],
    except IndexError:
        pass

    try:
        ip['system_type'] = get_agent(root, ROLE='ARCHIVIST', TYPE='OTHER', OTHERTYPE='SOFTWARE')['notes'][1],
    except IndexError:
        pass

    return ip


class XMLFileElement:
    def __init__(self, el, props, path=None, rootdir=None):
        '''
        args:
            el: lxml.etree._Element
            props: 'dict with properties from FILE_ELEMENTS'
        '''

        self.el = el
        self.props = props
        self.path = path
        self.checksum = get_value_from_path(el, props.get('checksum', ''))
        self.checksum = self.checksum.lower() if self.checksum is not None else self.checksum
        self.checksum_type = get_value_from_path(el, props.get('checksumtype', ''))
        self.checksum_type = self.checksum_type.lower() if self.checksum_type is not None else self.checksum_type
        self.size = get_value_from_path(el, props.get('size', ''))
        self.size = int(self.size) if self.size is not None else None
        self.format = get_value_from_path(el, props.get('format', ''))

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        if path is None:
            self.paths = self.props.get('path', [''])

            if isinstance(self.paths, str):
                self.paths = [self.paths]

            for path in self.paths:
                path = get_value_from_path(self.el, path)

                if path is not None:
                    break

            self.path_prefix = self.props.get('pathprefix', [])
            for prefix in sorted(self.path_prefix, key=len, reverse=True):
                no_prefix = remove_prefix(path, prefix)

                if no_prefix != path:
                    path = no_prefix
                    break

            if self.props.get('path_includes_root', False):
                path = path.split('/', 1)[-1]

            path = path.lstrip('/ ')

        self._path = normalize_path(path)

    def __eq__(self, other):
        '''
        Two objects are equal if their paths are equal. If other is a
        string, we assume its a path and compares it as is
        '''

        if isinstance(other, str):
            return self.path == other

        return self.path == other.path

    def __hash__(self):
        return hash(self.path)


def find_pointer(tree, elname, props):
    for ptr in tree.xpath('.//*[local-name()="%s"]' % elname):
        yield XMLFileElement(ptr, props)


def find_pointers(xmlfile=None, tree=None):
    if xmlfile is None and tree is None:
        raise ValueError("Need xmlfile or tree, both can't be None")

    if xmlfile is not None:
        tree = etree.ElementTree(file=xmlfile)

    for elname, props in PTR_ELEMENTS.items():
        yield from find_pointer(tree, elname, props)


def find_file(filepath, xmlfile=None, tree=None, rootdir='', prefix=''):
    if xmlfile is None and tree is None:
        raise ValueError("Need xmlfile or tree, both can't be None")

    if xmlfile is not None:
        tree = etree.ElementTree(file=xmlfile)

    root = tree.getroot()

    for elname, props in FILE_ELEMENTS.items():
        for prefix in props.get('pathprefix', []) + ['']:
            fullpath = prefix + filepath

            props_paths = props.get('path')
            if isinstance(props_paths, str):
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
        xml_el, el = find_file(
            filepath,
            xmlfile=os.path.join(rootdir, pointer.path),
            rootdir=rootdir,
            prefix=pointer_prefix
        )
        if xml_el is not None:
            return xml_el, el


def find_files(xmlfile, rootdir='', prefix='', skip_files=None, recursive=True, current_dir=None):
    doc = etree.ElementTree(file=xmlfile)
    files = set()

    if skip_files is None:
        skip_files = []

    if current_dir is None:
        current_dir = rootdir

    for elname, props in FILE_ELEMENTS.items():
        file_elements = doc.xpath('.//*[local-name()="%s"]' % elname)

        # Remove first object in premis file if it is a "fake" entry describing the tar
        if len(file_elements) and file_elements[0].get('{%s}type' % XSI_NAMESPACE) == 'premis:file':
            # In XPath 1 we use translate() to make a case insensitive comparison
            xpath_upper = 'translate(.,"abcdefghijklmnopqrstuvwxyz","ABCDEFGHIJKLMNOPQRSTUVWXYZ")'
            xpath_query = './/*[local-name()="formatName"][{up} = "TAR" or {up} = "ZIP"]'.format(up=xpath_upper)
            if len(file_elements[0].xpath(xpath_query)):
                file_elements.pop(0)

        for el in file_elements:
            file_el = XMLFileElement(el, props, rootdir=rootdir)
            file_el.path = win_to_posix(os.path.join(prefix, file_el.path))

            if file_el.path in skip_files:
                continue

            files.add(file_el)

    if recursive:
        for pointer in find_pointers(xmlfile=xmlfile):
            current_dir = os.path.join(current_dir, os.path.dirname(pointer.path))
            pointer_path = os.path.join(current_dir, os.path.basename(pointer.path))

            if pointer.path not in skip_files:
                pointer.path = os.path.join(prefix, pointer.path)
                files.add(pointer)

            prefix = os.path.relpath(current_dir, rootdir)
            if prefix == '.':
                prefix = ''

            files |= find_files(
                pointer_path,
                rootdir,
                prefix,
                recursive=recursive,
                current_dir=current_dir,
            )

    return files


def parse_file(filepath, fid, relpath=None, algorithm='SHA-256', rootdir='', provided_data=None):
    if not relpath:
        relpath = filepath

    if provided_data is None:
        provided_data = {}

    relpath = win_to_posix(relpath)

    fileinfo = {
        'FName': os.path.basename(relpath),
        'FExtension': os.path.splitext(relpath)[1][1:],
        'FDir': rootdir,
        'FParentDir': os.path.basename(os.path.dirname(filepath)),
        'FID': str(uuid.uuid4()),
        'daotype': "borndigital",
        'href': relpath,
        'FMimetype': fid.get_mimetype(filepath),
        'FSize': str(os.path.getsize(filepath)),
        'FUse': 'Datafile',
        'FChecksumType': algorithm,
        'FLoctype': 'URL',
        'FLinkType': 'simple',
        'FChecksumLib': 'ESSArch',
        'FIDType': 'UUID',
    }

    # We only do heavy computations if their values aren't included in
    # provided_data

    if 'FCreated' not in provided_data:
        timestamp = creation_date(filepath)
        createdate = timestamp_to_datetime(timestamp)
        fileinfo['FCreated'] = createdate.isoformat()

    if 'FChecksum' not in provided_data:
        fileinfo['FChecksum'] = checksum.calculate_checksum(filepath, algorithm)

    if 'FEncrypted' not in provided_data:
        fileinfo['FEncrypted'] = fid.identify_file_encryption(filepath)

    if any(x not in provided_data for x in ['FFormatName', 'FFormatVersion', 'FFormatRegistryKey']):
        (format_name, format_version, format_registry_key) = fid.identify_file_format(filepath)

        fileinfo['FFormatName'] = format_name
        fileinfo['FFormatVersion'] = format_version
        fileinfo['FFormatRegistryKey'] = format_registry_key

    for key, value in provided_data.items():
        fileinfo[key] = value

    return fileinfo


def download_imported_https_schemas(schema, dst):
    from ESSArch_Core.ip.utils import download_schema
    for url in schema.xpath('//*[local-name()="import"]/@schemaLocation'):
        protocol = urlparse(url)
        if protocol == 'http':
            continue
        new_path = download_schema(dst, logger, url)
        new_path = pathlib.Path(new_path)
        el = url.getparent()
        el.attrib['schemaLocation'] = new_path.as_uri()

    return schema


def validate_against_schema(xmlfile, schema=None, rootdir=None):
    doc = etree.ElementTree(file=xmlfile)

    if schema:
        xmlschema = etree.parse(schema)
    else:
        xmlschema = getSchemas(doc=doc)

    with tempfile.TemporaryDirectory() as tempdir:
        xmlschema = download_imported_https_schemas(xmlschema, tempdir)
        xmlschema = etree.XMLSchema(xmlschema)
        xmlschema.assertValid(doc)

    if rootdir is None:
        rootdir = os.path.split(xmlfile)[0]

    for ptr in find_pointers(xmlfile):
        validate_against_schema(os.path.join(rootdir, ptr.path), schema)
