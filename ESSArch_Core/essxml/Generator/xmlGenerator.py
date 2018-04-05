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

import copy
import datetime
import logging
import os
import re
import uuid

from django.template import Template, Context
from django.utils.encoding import DjangoUnicodeDecodeError

from lxml import etree

from natsort import natsorted

from django.utils import timezone

from scandir import walk

import six

from ESSArch_Core.essxml.util import parse_file
from ESSArch_Core.fixity.format import FormatIdentifier

from ESSArch_Core.util import (
    get_elements_without_namespace, make_unicode, nested_lookup,
)

logger = logging.getLogger('essarch.essxml.generator')

def parseContent(content, info=None):
    if not content:
        return None

    if info is None:
        info = {}

    if isinstance(content, six.string_types):
        t = Template(content)
        c = Context(info)
        try:
            return t.render(c)
        except DjangoUnicodeDecodeError:
            for k, v in six.iteritems(info):
                info[k] = make_unicode(v)
            return t.render(c)

    arr = []
    for c in content:
        if 'text' in c:
            arr.append(make_unicode(c['text']))
        elif 'var' in c:
            var = c['var']
            val = info.get(var) or info.get(var.split('__')[0])

            if val is None:
                val = c.get('default')

            if val is None and c.get('hide_content_if_missing', False):
                return None

            if var == '_UUID':
                val = str(uuid.uuid4())

            if var == '_NOW':
                val = timezone.now()

            if var.endswith('__LOCALTIME'):
                val = timezone.localtime(val)

            if var.endswith('__DATE'):
                val = val.strftime('%Y-%m-%d')

            if isinstance(val, datetime.datetime):
                val = val.isoformat()

            if val is not None:
                arr.append(make_unicode(val))

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
        self.nestedXMLContent = template.get('-nestedXMLContent')
        self.containsFiles = template.get('-containsFiles', False)
        self.foreach = template.get('-foreach', None)
        self.replace_existing = template.get('-replaceExisting', None)
        self.external = template.get('-external')
        self.fileFilters = template.get('-filters', {})
        self.allowEmpty = template.get('-allowEmpty', False)
        self.hideEmptyContent = template.get('-hideEmptyContent', False)
        self.skipIfNoChildren = template.get('-skipIfNoChildren', False)
        self.requiredParameters = template.get('-requiredParameters', [])
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

        if len(self.el):
            return False

        if getattr(self.el, 'text', None) is not None and len(self.el.text):
            return False

        if parseContent(self.content, info):
            return False

        if self.nestedXMLContent:
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

    def add_element(self, new):
        if new.replace_existing is not None:
            # Get other child elements with the attributes in new.replace_existing
            # set to the same as the attributes in the new element and replace
            # the last of the old elements with the new

            xpath_attributes = []
            for attrib in new.replace_existing:
                if len(new.el.get(attrib, '')) > 0:
                    xpath_attributes.append("@%s='%s'" % (attrib, new.el.get(attrib)))

            attr_string = ""
            if len(xpath_attributes) > 0:
                attr_string = "[%s]" % (' and '.join(xpath_attributes))

            old = self.el.xpath("./*[local-name()='%s']%s" % (new.name, attr_string))

            if len(old) > 0:
                self.el.replace(old[-1], new.el)
                return

        self.el.append(new.el)

    def createLXMLElement(self, info, nsmap={}, files=[], folderToParse='', parent=None):
        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            self.el = etree.Element("{%s}%s" % (full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            self.el = etree.Element("%s" % self.name, nsmap=full_nsmap)

        self.el.text = self.parse(info)

        self.parent = parent

        for req_param in self.requiredParameters:
            if info.get(req_param) is None or len(info.get(req_param, '')) == 0:
                return None

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
                child_el = ptr.createLXMLElement(ptr_info, full_nsmap, folderToParse=folderToParse, parent=self)

                if child_el is not None:
                    self.add_element(ptr)

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
                        child_el = child.createLXMLElement(full_info, full_nsmap, files=files, folderToParse=folderToParse, parent=self)
                        if child_el is not None:
                            self.add_element(child)

            elif child.foreach is not None:
                for v in info[child.foreach]:
                    child_info = copy.deepcopy(info)
                    child_info.update(v)

                    child_el = child.createLXMLElement(child_info, full_nsmap, files=files, folderToParse=folderToParse, parent=self)
                    if child_el is not None:
                        self.add_element(child)

            else:
                child_el = child.createLXMLElement(info, full_nsmap, files=files, folderToParse=folderToParse, parent=self)
                if child_el is not None:
                    self.add_element(child)

        if self.nestedXMLContent:
            # we encode the XML to get around LXML limitation with XML strings
            # containing encoding information.
            # See https://stackoverflow.com/questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
            if self.nestedXMLContent not in info:
                logger.warn("Nested XML '%s' not found in data and will not be created" % self.nestedXMLContent)
                if not self.allowEmpty:
                    return None
            else:
                nested_xml = six.binary_type(bytearray(info[self.nestedXMLContent], encoding='utf-8'))
                parser = etree.XMLParser(remove_blank_text=True)
                self.el.append(etree.fromstring(nested_xml, parser=parser))

        is_empty = self.isEmpty(info)
        if is_empty and self.required:
            raise ValueError("Missing value for required element '%s'" % (self.get_path()))

        if is_empty and not self.allowEmpty:
            return None

        if len(self.el) == 0 and self.skipIfNoChildren:
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
            raise ValueError("Cannot generate attribute with missing name")

        self.namespace = template.get('-namespace')
        self.required = template.get('-req', False)
        self.content = template.get('#content')

    def parse(self, info, nsmap={}):
        name = self.name

        if self.namespace:
            name = "{%s}%s" % (nsmap.get(self.namespace), self.name)

        return name, parseContent(self.content, info), self.required


class XMLGenerator(object):
    def __init__(self, filesToCreate={}, filepath=None, relpath=None):
        parser = etree.XMLParser(remove_blank_text=True)

        if filepath is not None:
            self.tree = etree.parse(filepath, parser=parser)
        else:
            self.tree = None

        self.relpath = relpath
        self.toCreate = []

        for fname, content in filesToCreate.iteritems():
            self.toCreate.append({
                'file': fname,
                'template': content['spec'],
                'data': content.get('data', {}),
                'root': XMLElement(content['spec'])
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
                    dirs.append((x['-file'], x['-dir'], x['-specification'], spec['data']))

        return dirs

    def generate(self, folderToParse=None, extra_paths_to_parse=[], parsed_files=None, algorithm='SHA-256'):
        if parsed_files is None:
            parsed_files = []

        files = parsed_files

        responsible = None

        # See if any profile allows unknown file types.
        # If atleast one does allow it, we allow it for all profiles.
        allow_unknown_file_types = False
        for idx, f in enumerate(self.toCreate):
            allow_unknown_file_types = f.get('data', {}).get('allow_unknown_file_types', False)
            if allow_unknown_file_types:
                break

        fid = FormatIdentifier(allow_unknown_file_types=allow_unknown_file_types)

        if folderToParse:
            folderToParse = folderToParse.rstrip('/')
            folderToParse = unicode(folderToParse)

            external = self.find_external_dirs()

            for ext_file, ext_dir, ext_spec, ext_data in external:
                ext_sub_dirs = next(walk(os.path.join(folderToParse, ext_dir)))[1]
                for sub_dir in ext_sub_dirs:
                    ptr_file_path = os.path.join(ext_dir, sub_dir, ext_file)

                    ext_info = copy.deepcopy(ext_data)
                    ext_info['_EXT'] = sub_dir
                    ext_info['_EXT_HREF'] = ptr_file_path

                    external_gen = XMLGenerator(
                        filesToCreate={
                            os.path.join(folderToParse, ptr_file_path): {'spec': ext_spec, 'data': ext_info}
                        },
                    )
                    external_gen.generate(os.path.join(folderToParse, ext_dir, sub_dir))

                    filepath = os.path.join(folderToParse, ptr_file_path)

                    fileinfo = parse_file(filepath, fid, ptr_file_path, algorithm=algorithm, rootdir=sub_dir)
                    files.append(fileinfo)

            if os.path.isfile(folderToParse):
                filepath = folderToParse
                relpath = os.path.basename(folderToParse)

                fileinfo = parse_file(filepath, fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in walk(folderToParse):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)

                        fileinfo = parse_file(filepath, fid, relpath, algorithm=algorithm)
                        files.append(fileinfo)

        for path in extra_paths_to_parse:
            if os.path.isfile(path):
                relpath = os.path.basename(path)

                fileinfo = parse_file(path, fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(path):
                for root, dirnames, filenames in walk(path):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, path)

                        fileinfo = parse_file(filepath, fid, relpath, algorithm=algorithm, rootdir=path)
                        files.append(fileinfo)



        for idx, f in enumerate(self.toCreate):
            fname = f['file']
            rootEl = f['root']
            data = f.get('data', {})

            data['_XML_FILENAME'] = os.path.basename(fname)

            self.tree = etree.ElementTree(
                rootEl.createLXMLElement(data, files=files, folderToParse=folderToParse)
            )
            self.tree.write(
                fname, pretty_print=True, xml_declaration=True,
                encoding='UTF-8'
            )

            try:
                relfilepath = os.path.relpath(fname, self.relpath)
            except:
                try:
                    relfilepath = os.path.relpath(fname, folderToParse)
                except:
                    relfilepath = fname

            if idx < len(self.toCreate) - 1:
                fileinfo = parse_file(fname, fid, relfilepath, algorithm=algorithm)
                files.append(fileinfo)

    def write(self, filepath):
        self.tree.write(filepath, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def find_element(self, path):
        return findElementWithoutNamespace(self.tree, path)

    def insert(self, target, el, index=None, before=None, after=None):
        if before is not None and after is not None:
            raise ValueError('Both "before" and "after" cannot not be None')

        try:
            if index is not None:
                target.insert(index, el)
            elif before is not None:
                try:
                    reference_el = get_elements_without_namespace(target, before)[0]
                except IndexError:
                    raise ValueError('%s element does not exist in %s element' % (before, self.tree.getpath(target)))

                index = target.index(reference_el)
                target.insert(index, el)
            elif after is not None:
                try:
                    reference_el = get_elements_without_namespace(target, after)[-1]
                except IndexError:
                    raise ValueError('%s element does not exist in %s element' % (after, self.tree.getpath(target)))

                index = target.index(reference_el) + 1
                target.insert(index, el)
            else:
                target.append(el)
        except TypeError:
            if el is None:
                raise TypeError("Can't insert null element into %s" % target)

    def insert_from_specification(self, target, spec, data=None, index=None, before=None, after=None):
        if data is None:
            data = {}

        root_nsmap = {k: v for k, v in target.nsmap.iteritems() if k}
        el = XMLElement(spec, nsmap=root_nsmap).createLXMLElement(data)

        return self.insert(target, el, index=index, before=before, after=after)

    def insert_from_xml_string(self, target, xml, index=None, before=None, after=None):
        parser = etree.XMLParser(remove_blank_text=True)
        el = etree.fromstring(xml, parser)
        return self.insert(target, el, index=index, before=before, after=after)

    def insert_from_xml_file(self, target, xml, index=None, before=None, after=None):
        parser = etree.XMLParser(remove_blank_text=True)
        el = etree.parse(xml, parser).getroot()
        return self.insert(target, el, index=index, before=before, after=after)
