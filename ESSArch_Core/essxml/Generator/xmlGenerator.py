import os, re
import hashlib
import uuid
import mimetypes

from lxml import etree

from configuration.models import (
    Path,
)

def calculateChecksum(filename):
    """
    calculate the checksum for the selected file, one chunk at a time
    """
    fd = os.open(filename, os.O_RDONLY)
    hashSHA = hashlib.sha256()
    while True:
        data = os.read(fd, 65536)
        if data:
            hashSHA.update(data)
        else:
            break
    os.close(fd)
    return hashSHA.hexdigest()

def parseContent(content, info):
    if not content:
        return None

    arr = []
    for c in content:
        if 'text' in c:
            arr.append(c['text'])
        elif 'var' in c:
            val = info.get(c['var'])

            if val:
                arr.append(val)

    return ''.join(arr)


class XMLElement(object):
    def __init__(self, template, nsmap={}):
        name = template.get('-name')
        try:
            self.name = name.split("#")[0]
        except:
            self.name = name

        self.nsmap = template.get('-nsmap', {})
        self.nsmap.update(nsmap)
        self.namespace = template.get('-namespace')
        self.attr = [XMLAttribute(a) for a in template.get('-attr', [])]
        self.content = template.get('#content', [])
        self.containsFiles = template.get('-containsFiles', False)
        self.fileFilters = template.get('-filters', {})
        self.allowEmpty = template.get('-allowEmpty', False)
        self.children = []

        for child in template.get('-children', []):
            child_el = XMLElement(child)
            self.children.append(child_el)

    def parse(self, info):
        return parseContent(self.content, info)

    def isEmpty(self):
        """
        Simple helper function to check if the tag sould have any contents
        """
        if self.content or self.children or self.containsFiles or self.attr:
            return False

        return True

    def createLXMLElement(self, info, nsmap={}, files=[]):
        if self.isEmpty() and not self.allowEmpty:
            raise ValueError(
                "Element %s does not contain any value, attributes, children or\
                files, and allowEmpty is not set" % self.name
            )

        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            el = etree.Element("{%s}%s" % (full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            el = etree.Element("%s" % self.name, nsmap=full_nsmap)

        el.text = self.parse(info)

        for attr in self.attr:
            name, content = attr.parse(info, nsmap=full_nsmap)
            el.set(name, content)

        for child in self.children:

            if child.containsFiles:
                for fileinfo in files:
                    include = True

                    for key, file_filter in child.fileFilters.iteritems():
                        if not re.search(file_filter, fileinfo.get(key)):
                            include = False

                    if include:
                        full_info = info.copy()
                        full_info.update(fileinfo)
                        el.append(child.createLXMLElement(full_info, full_nsmap, files=files))
            else:
                el.append(child.createLXMLElement(info, full_nsmap, files=files))

        return el

class XMLAttribute(object):
    """
        Args:
            template: The template for the attribute, example:
                {
                    '-name': 'foo',
                    '#content': [
                        {
                            'var': 'foo.bar'
                        },
                        {
                            'text': 'baz'
                        }
                    ]
                }
    """

    def __init__(self, template):
        self.name = template.get('-name')
        self.namespace = template.get('-namespace')
        self.content = template.get('#content')

    def parse(self, info, nsmap={}):
        name = self.name

        if self.namespace:
            name = "{%s}%s" % (nsmap.get(self.namespace), self.name)

        return name, parseContent(self.content, info)

class XMLGenerator(object):
    def __init__(self, filesToCreate, info={}):
        self.info = info
        self.toCreate = []

        for fname, template in filesToCreate.iteritems():
            self.toCreate.append({
                'file': fname,
                'template': template,
                'root': XMLElement(template)
            })

    def generate(self, folderToParse=None):
        files = []

        if folderToParse:
            mimetypes.suffix_map = {}
            mimetypes.encodings_map = {}
            mimetypes.types_map = {}
            mimetypes.common_types = {}
            mimetypes_file = Path.objects.get(
                entity="path_mimetypes_definitionfile"
            ).value
            mimetypes.init(files=[mimetypes_file])

            if os.path.isfile(folderToParse):
                files.append(self.parseFile(folderToParse, mimetypes))
            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in os.walk(folderToParse):
                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)
                        files.append(self.parseFile(filepath, mimetypes, relpath=relpath))

        for f in self.toCreate:
            fname = f['file']
            rootEl = f['root']

            tree = etree.ElementTree(
                rootEl.createLXMLElement(self.info, files=files)
            )
            tree.write(
                fname, pretty_print=True, xml_declaration=True,
                encoding='UTF-8'
            )

    def append(self, filename, elementToAppendTo, template, info={}):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(filename, parser)
        rootEl = tree.getroot()
        rootWithoutNS = etree.QName(rootEl).localname

        if rootWithoutNS == elementToAppendTo:
            elementToAppendTo = rootEl
        else:
            elementToAppendTo = rootEl.find(".//{*}%s" % elementToAppendTo)

        root_nsmap = {k:v for k,v in elementToAppendTo.nsmap.iteritems() if k}

        appendedRootEl = XMLElement(template, nsmap=root_nsmap)

        elementToAppendTo.append(appendedRootEl.createLXMLElement(info))

        tree.write(filename, pretty_print=True)

    def parseFile(self, filepath, mimetypes, relpath=None):
        """
        walk through the choosen folder and parse all the files to their own temporary location
        """
        if not relpath:
            relpath = filepath

        base = os.path.basename(relpath)
        file_name, file_ext = os.path.splitext(base)

        try:
            mimetype = mimetypes.types_map[file_ext]
        except KeyError:
            raise KeyError("Invalid file type: %s" % file_ext)

        fileinfo = {
            'FName': file_name + file_ext,
            'FChecksum': calculateChecksum(filepath),
            'FID': str(uuid.uuid4()),
            'id': str(uuid.uuid4()),
            'daotype': "borndigital",
            'href': relpath,
            'FMimetype': mimetype,
            'FCreated': '2016-02-21T11:18:44+01:00',
            'FFormatName': 'MS word',
            'FSize': str(os.path.getsize(filepath)),
            'FUse': 'DataFile',
            'FChecksumType': 'SHA-256',
            'FLoctype': 'URL',
            'FLinkType': 'simple',
            'FChecksumLib': 'hashlib',
            'FLocationType': 'URI',
            'FIDType': 'UUID',
        }

        return fileinfo
