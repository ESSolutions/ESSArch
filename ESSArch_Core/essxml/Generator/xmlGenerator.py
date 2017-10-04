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

import os
import re
import uuid

from lxml import etree

from natsort import natsorted

from django.utils import timezone

from scandir import walk

from ESSArch_Core.exceptions import (
    FileFormatNotAllowed
)

from ESSArch_Core.essxml.util import parse_file
from ESSArch_Core.fixity.format import FormatIdentifier

from ESSArch_Core.util import (
    nested_lookup,
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

            if val is not None:
                arr.append(unicode(val))

    return ''.join(arr)


def findElementWithoutNamespace(tree, el_name):
    root = tree.getroot()
    rootWithoutNS = etree.QName(root).localname

    if rootWithoutNS == el_name:
        return root
    else:
        return root.find(".//{*}%s" % el_name)


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
        self.required = template.get('-req', False)
        self.attr = [XMLAttribute(a) for a in template.get('-attr', [])]
        self.content = template.get('#content', [])
        self.containsFiles = template.get('-containsFiles', False)
        self.external = template.get('-external')
        self.fileFilters = template.get('-filters', {})
        self.allowEmpty = template.get('-allowEmpty', False)
        self.hideEmptyContent = template.get('-hideEmptyContent', False)
        self.skipIfNoChildren = template.get('-skipIfNoChildren', False)
        self.children = []
        self.el = None

        for child in template.get('-children', []):
            child_el = XMLElement(child)
            self.children.append(child_el)

    def parse(self, info):
        return parseContent(self.content, info)

    def contentIsEmpty(self, info={}):
        if self.containsFiles:
            return False

        if self.el is None:
            return True

        if len(self.el) == 0 and self.skipIfNoChildren:
            return True

        if len(self.el):
            return False

        if parseContent(self.content, info):
            return False

        return True

    def isEmpty(self, info={}):
        """
        Simple helper function to check if the tag sould have any contents
        """

        if not self.contentIsEmpty(info):
            return False

        any_attribute_with_value = any(value for value in self.el.attrib.values())

        if any_attribute_with_value:
            return False

        return True

    def get_path(self, path=[]):
        path = '%s[%s]' % (self.name, self.parent_pos)

        if self.parent:
            path = self.parent.get_path(path) + '/' + path
        else:
            path = '/' + path

        return path

    def createLXMLElement(self, info, nsmap={}, files=[], folderToParse='', task=None, parent=None):
        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            self.el = etree.Element("{%s}%s" % (full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            self.el = etree.Element("%s" % self.name, nsmap=full_nsmap)

        self.el.text = self.parse(info)

        self.parent = parent

        if parent is not None:
            siblings_same_name = len(parent.el.findall(self.name))
            self.parent_pos = siblings_same_name
        else:
            self.parent_pos = 0

        for attr in self.attr:
            name, content, required = attr.parse(info, nsmap=full_nsmap)

            if required and not content:
                raise ValueError("Missing value for required attribute '%s' on element '%s'" % (name, self.get_path()))
            elif content:
                self.el.set(name, content)

        if self.external:
            ext_dirs = next(walk(os.path.join(folderToParse, self.external['-dir'])))[1]
            for ext_dir in natsorted(ext_dirs):
                ptr = XMLElement(self.external['-pointer'])
                ptr_file_path = os.path.join(self.external['-dir'], ext_dir, self.external['-file'])

                ptr_info = info
                ptr_info['_EXT'] = ext_dir
                ptr_info['_EXT_HREF'] = ptr_file_path
                self.el.append(ptr.createLXMLElement(ptr_info, full_nsmap, folderToParse=folderToParse, task=task, parent=self))

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
                        self.el.append(child.createLXMLElement(full_info, full_nsmap, files=files, folderToParse=folderToParse, task=task, parent=self))
            else:
                child_el = child.createLXMLElement(info, full_nsmap, files=files, folderToParse=folderToParse, task=task, parent=self)
                if child_el is not None:
                    self.el.append(child_el)

        if self.isEmpty(info) and self.required:
            raise ValueError("Missing value for required element '%s'" % (self.get_path()))

        if self.isEmpty(info) and not self.allowEmpty:
            return None

        if self.contentIsEmpty(info) and self.hideEmptyContent:
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
    def __init__(self, filesToCreate={}, info={}, task=None):
        self.info = info
        self.toCreate = []
        self.task = task

        for fname, template in filesToCreate.iteritems():
            self.toCreate.append({
                'file': fname,
                'template': template,
                'root': XMLElement(template)
            })

    def find_external_dirs(self):
        dirs = []
        found_paths = []

        for spec in self.toCreate:
            res = nested_lookup('-external', spec['template'])
            for x in res:
                path = os.path.join(x['-dir'], x['-file'])

                external_nsmap = spec['template'].get('-nsmap', {}).copy()
                external_nsmap.update(x['-specification'].get('-nsmap', {}))
                x['-specification']['-nsmap'] = external_nsmap

                if path not in found_paths:
                    found_paths.append(path)
                    dirs.append((x['-file'], x['-dir'], x['-specification']))

        return dirs

    def get_mimetype(self, mtypes, fname):
        file_name, file_ext = os.path.splitext(fname)

        if not file_ext:
            file_ext = file_name

        try:
            return mtypes[file_ext]
        except KeyError:
            if self.info.get('allow_unknown_file_types', False):
                return 'application/octet-stream'

            raise FileFormatNotAllowed("File format '%s' is not allowed" % file_ext)

    def generate(self, folderToParse=None, extra_paths_to_parse=[], parsed_files=None, algorithm='SHA-256'):
        fid = FormatIdentifier()

        if parsed_files is None:
            parsed_files = []

        files = parsed_files

        responsible = None

        if folderToParse:
            folderToParse = folderToParse.rstrip('/')
            folderToParse = unicode(folderToParse)

            external = self.find_external_dirs()

            for ext_file, ext_dir, ext_spec in external:
                ext_sub_dirs = next(walk(os.path.join(folderToParse, ext_dir)))[1]
                for sub_dir in ext_sub_dirs:
                    ptr_file_path = os.path.join(ext_dir, sub_dir, ext_file)

                    ext_info = self.info
                    ext_info['_EXT'] = sub_dir
                    ext_info['_EXT_HREF'] = ptr_file_path

                    external_gen = XMLGenerator(
                        filesToCreate={
                            os.path.join(folderToParse, ptr_file_path): ext_spec
                        },
                        info=ext_info,
                        task=self.task,
                    )
                    external_gen.generate(os.path.join(folderToParse, ext_dir, sub_dir))

                    filepath = os.path.join(folderToParse, ptr_file_path)
                    mimetype = self.get_mimetype(fid.mimetypes, ptr_file_path)

                    fileinfo = parse_file(filepath, mimetype, fid, ptr_file_path, algorithm=algorithm, rootdir=sub_dir)
                    files.append(fileinfo)

            if os.path.isfile(folderToParse):
                filepath = folderToParse
                mimetype = self.get_mimetype(fid.mimetypes, filepath)
                relpath = os.path.basename(folderToParse)

                fileinfo = parse_file(filepath, mimetype, fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in walk(folderToParse):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)
                        mimetype = self.get_mimetype(fid.mimetypes, filepath)

                        fileinfo = parse_file(filepath, mimetype, fid, relpath, algorithm=algorithm)
                        files.append(fileinfo)

        for path in extra_paths_to_parse:
            if os.path.isfile(path):
                mimetype = self.get_mimetype(fid.mimetypes, path)
                relpath = os.path.basename(path)

                fileinfo = parse_file(path, mimetype, fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(path):
                for root, dirnames, filenames in walk(path):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, path)
                        mimetype = self.get_mimetype(fid.mimetypes, filepath)

                        fileinfo = parse_file(filepath, mimetype, fid, relpath, algorithm=algorithm, rootdir=path)
                        files.append(fileinfo)



        for idx, f in enumerate(self.toCreate):
            fname = f['file']
            rootEl = f['root']

            self.info['_XML_FILENAME'] = os.path.basename(fname)

            tree = etree.ElementTree(
                rootEl.createLXMLElement(self.info, files=files, folderToParse=folderToParse, task=self.task)
            )
            tree.write(
                fname, pretty_print=True, xml_declaration=True,
                encoding='UTF-8'
            )

            try:
                relpath = os.path.relpath(fname, folderToParse)
            except:
                relpath = fname

            if idx < len(self.toCreate) - 1:
                mimetype = self.get_mimetype(fid.mimetypes, filepath)
                fileinfo = parse_file(fname, mimetype, fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

    def insert(self, filename, elementToAppendTo, template, info={}, index=None):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(filename, parser)
        elementToAppendTo = findElementWithoutNamespace(tree, elementToAppendTo)
        root_nsmap = {k: v for k, v in elementToAppendTo.nsmap.iteritems() if k}
        appendedRootEl = XMLElement(template, nsmap=root_nsmap)

        try:
            el = appendedRootEl.createLXMLElement(info, task=self.task)
            if index is not None:
                elementToAppendTo.insert(index, el)
            else:
                elementToAppendTo.append(el)
        except TypeError:
            if el is None:
                raise TypeError("Can't insert null element into %s" % appendedRootEl)


        tree.write(
            filename, pretty_print=True, xml_declaration=True,
            encoding='UTF-8'
        )
