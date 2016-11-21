import os, re
import uuid
import mimetypes

from lxml import etree

from django.utils import timezone

from ESSArch_Core.configuration.models import (
    Path,
)

from ESSArch_Core.WorkflowEngine.models import ProcessTask

from ESSArch_Core.util import (
    creation_date,
    download_file,
    find_destination,
    timestamp_to_datetime,
    win_to_posix,
)

def parseContent(content, info):
    if not content:
        return None

    arr = []
    for c in content:
        if 'text' in c:
            arr.append(c['text'])
        elif 'var' in c:
            var = c['var']
            val = info.get(var)

            if var == '_UUID':
                val = str(uuid.uuid4())

            if var == '_NOW':
                now = timezone.now()
                local = timezone.localtime(now)
                val = local.replace(microsecond=0).isoformat()

            if val:
                arr.append(val)

    return ''.join(arr)

def downloadSchemas(template, dirname, structure=[], root=""):
    schemaPreserveLoc = template.get('-schemaPreservationLocation')

    if schemaPreserveLoc and structure:
        dirname, _ = find_destination(
            schemaPreserveLoc, structure
        )
        dirname = os.path.join(root, dirname)

    for schema in template.get('-schemasToPreserve', []):
        dst = os.path.join(dirname, os.path.basename(schema))
        download_file(schema, dst)


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
        self.skipIfNoChildren = template.get('-skipIfNoChildren', False)
        self.children = []
        self.el = None

        for child in template.get('-children', []):
            child_el = XMLElement(child)
            self.children.append(child_el)

    def parse(self, info):
        return parseContent(self.content, info)

    def isEmpty(self):
        """
        Simple helper function to check if the tag sould have any contents
        """

        if self.el is None:
            return True

        if len(self.el) == 0 and self.skipIfNoChildren:
            return True

        any_attribute_with_value = any(value for value in self.el.attrib.values())
        any_children_not_empty = any(not child.isEmpty() or (child.isEmpty() and child.allowEmpty) for child in self.children)

        if self.content or any_children_not_empty or self.containsFiles or any_attribute_with_value:
            return False

        return True

    def createLXMLElement(self, info, nsmap={}, files=[]):
        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            self.el = etree.Element("{%s}%s" % (full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            self.el = etree.Element("%s" % self.name, nsmap=full_nsmap)

        self.el.text = self.parse(info)

        for attr in self.attr:
            name, content, required = attr.parse(info, nsmap=full_nsmap)

            if required and not content:
                raise ValueError("Missing value for required attribute '%s' on element '%s'" % (name, self.name))
            elif content:
                self.el.set(name, content)

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
                        self.el.append(child.createLXMLElement(full_info, full_nsmap, files=files))
            else:
                child_el = child.createLXMLElement(info, full_nsmap, files=files)
                if child_el is not None:
                    self.el.append(child_el)

        if self.isEmpty() and not self.allowEmpty:
            return None

        return self.el

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
        try:
            self.name = template['-name']
        except KeyError:
            raise KeyError("Attribute missing name")

        self.namespace = template.get('-namespace')
        self.required = template.get('-req', False)
        self.content = template.get('#content')

    def parse(self, info, nsmap={}):
        name = self.name

        if self.namespace:
            name = "{%s}%s" % (nsmap.get(self.namespace), self.name)

        return name, parseContent(self.content, info), self.required

class XMLGenerator(object):
    def __init__(self, filesToCreate={}, info={}):
        self.info = info
        self.toCreate = []

        for fname, template in filesToCreate.iteritems():
            self.toCreate.append({
                'file': fname,
                'template': template,
                'root': XMLElement(template)
            })

    def generate(self, folderToParse=None, algorithm='SHA-256', ip=None):
        files = []

        mimetypes.suffix_map = {}
        mimetypes.encodings_map = {}
        mimetypes.types_map = {}
        mimetypes.common_types = {}
        mimetypes_file = Path.objects.get(
            entity="path_mimetypes_definitionfile"
        ).value
        mimetypes.init(files=[mimetypes_file])

        if folderToParse:
            if os.path.isfile(folderToParse):
                files.append(self.parseFile(
                    folderToParse, mimetypes,
                    relpath=os.path.basename(folderToParse),
                    algorithm=algorithm, ip=ip
                ))
            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in os.walk(folderToParse):
                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)
                        files.append(self.parseFile(
                            filepath, mimetypes, relpath=relpath,
                            algorithm=algorithm, ip=ip
                        ))

        for f in self.toCreate:
            fname = f['file']
            rootEl = f['root']

            self.info['_XML_FILENAME'] = os.path.basename(fname)

            tree = etree.ElementTree(
                rootEl.createLXMLElement(self.info, files=files)
            )
            tree.write(
                fname, pretty_print=True, xml_declaration=True,
                encoding='UTF-8'
            )

            try:
                relpath = os.path.relpath(fname, folderToParse)
            except:
                relpath = fname

            files.append(self.parseFile(fname, mimetypes, relpath, algorithm=algorithm, ip=ip))

    def insert(self, filename, elementToAppendTo, template, info={}, index=None):
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

        if index is not None:
            elementToAppendTo.insert(index, appendedRootEl.createLXMLElement(info))
        else:
            elementToAppendTo.append(appendedRootEl.createLXMLElement(info))

        tree.write(
            filename, pretty_print=True, xml_declaration=True,
            encoding='UTF-8'
        )

    def parseFile(self, filepath, mimetypes, relpath=None, algorithm='SHA-256', ip=None):
        """
        walk through the choosen folder and parse all the files to their own temporary location
        """
        if not relpath:
            relpath = filepath

        relpath = win_to_posix(relpath)

        base = os.path.basename(relpath)
        file_name, file_ext = os.path.splitext(base)
        timestamp = creation_date(filepath)
        createdate = timestamp_to_datetime(timestamp)

        try:
            mimetype = mimetypes.types_map[file_ext]
        except KeyError:
            raise KeyError("Invalid file type: %s" % file_ext)

        checksum = ProcessTask(
            name="preingest.tasks.CalculateChecksum",
            params={
                "filename": filepath,
                "algorithm": algorithm
            },
            information_package=ip
        ).run_eagerly()

        fileformat = ProcessTask(
            name="preingest.tasks.IdentifyFileFormat",
            params={
                "filename": filepath,
            },
            information_package=ip
        ).run_eagerly()

        fileinfo = {
            'FName': file_name + file_ext,
            'FChecksum': checksum,
            'FID': str(uuid.uuid4()),
            'daotype': "borndigital",
            'href': relpath,
            'FMimetype': mimetype,
            'FCreated': createdate.isoformat(),
            'FFormatName': fileformat,
            'FSize': str(os.path.getsize(filepath)),
            'FUse': 'Datafile',
            'FChecksumType': algorithm,
            'FLoctype': 'URL',
            'FLinkType': 'simple',
            'FChecksumLib': 'hashlib',
            'FLocationType': 'URI',
            'FIDType': 'UUID',
        }

        return fileinfo
