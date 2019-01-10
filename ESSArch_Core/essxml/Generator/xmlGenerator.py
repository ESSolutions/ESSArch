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

from django.template import Template, Context, TemplateSyntaxError
from django.utils.encoding import DjangoUnicodeDecodeError

from lxml import etree

from natsort import natsorted

from django.utils import timezone

from os import walk

import six

from ESSArch_Core.essxml.util import parse_file
from ESSArch_Core.fixity.format import FormatIdentifier

from ESSArch_Core.util import (
    get_elements_without_namespace, make_unicode, nested_lookup,
)

logger = logging.getLogger('essarch.essxml.generator')
leading_underscore_tag_re = re.compile('%s *_(.*?(?=\}))%s' % (re.escape('{{'), re.escape('}}')))


def parse_content_django(content, info=None, unicode_error=False, syntax_error=False):
    c = Context(info)
    try:
        t = Template(content)
    except TemplateSyntaxError:
        if syntax_error:
            raise

        def remove_underscore_prefix(d):
            new = {}
            for k, v in six.iteritems(d):
                if isinstance(v, dict):
                    v = remove_underscore_prefix(v)
                if k.startswith('_'):
                    new[k[1:]] = v
                else:
                    new[k] = v
            return new
        new_data = remove_underscore_prefix(info)
        regcontent = leading_underscore_tag_re.sub(r'{{\1}}', content)
        return parse_content_django(regcontent, info=new_data, syntax_error=True)

    try:
        return t.render(c)
    except DjangoUnicodeDecodeError:
        if unicode_error:
            raise
        for k, v in six.iteritems(info):
            info[k] = make_unicode(v)
        return parse_content_django(content, info=info, unicode_error=True)


def parseContent(content, info=None):
    if not content:
        return None

    if info is None:
        info = {}


    if isinstance(content, six.string_types):
        return parse_content_django(content, info=info)

    def get_nested_val(dct, key):
        for k in key.split('.'):
            try:
                dct = dct[k]
            except KeyError:
                return None
        return dct

    arr = []
    for c in content:
        if 'text' in c:
            arr.append(make_unicode(c['text']))
        elif 'var' in c:
            var = c['var']
            if '.' in var:
                val = get_nested_val(copy.deepcopy(info), var)
            else:
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
    def __init__(self, template, nsmap=None):
        if nsmap is None:
            nsmap = {}

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
        self.ignore_existing = template.get('-ignoreExisting', None)
        self.external = template.get('-external')
        self.fileFilters = template.get('-filters', {})
        self.allowEmpty = template.get('-allowEmpty', False)
        self.hideEmptyContent = template.get('-hideEmptyContent', False)
        self.skipIfNoChildren = template.get('-skipIfNoChildren', False)
        self.requiredParameters = template.get('-requiredParameters', [])
        self.children = []
        self.el = None
        self.parent = None
        self.parent_pos = 0

        for child in template.get('-children', []):
            child_el = XMLElement(child)
            self.children.append(child_el)

    def parse(self, info):
        return parseContent(self.content, info)

    def contentIsEmpty(self, info=None):
        if info is None:
            info = {}

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

    def isEmpty(self, info=None):
        """
        Simple helper function to check if the tag sould have any contents
        """

        if info is None:
            info = {}

        if not self.contentIsEmpty(info):
            return False

        if len(self.el.attrib.keys()):
            return False

        return True

    def get_path(self, path=None):
        if path is None:
            path = []

        path = '%s[%s]' % (self.name, self.parent_pos)

        if self.parent:
            path = self.parent.get_path(path) + '/' + path
        else:
            path = '/' + path

        return path

    def get_existing_elements(self, new_el, attrs):
        # Get elements that have the same name as new_el and where the attributes
        # in attrs have the same value as new_el

        xpath_attributes = []
        for attrib in attrs:
            if len(new_el.el.get(attrib, '')) > 0:
                xpath_attributes.append("@%s='%s'" % (attrib, new_el.el.get(attrib)))

        attr_string = ""
        if len(xpath_attributes) > 0:
            attr_string = "[%s]" % (' and '.join(xpath_attributes))

        return self.el.xpath("./*[local-name()='%s']%s" % (new_el.name, attr_string))

    def add_element(self, new):
        if new.replace_existing is not None:
            # Get other child elements with the attributes in new.replace_existing
            # set to the same as the attributes in the new element and replace
            # the last of the old elements with the new

            existing = self.get_existing_elements(new, new.replace_existing)
            if len(existing) > 0:
                self.el.replace(existing[-1], new.el)
                return

        if new.ignore_existing:
            # If there exists child elements with the attributes in new.ignore_existing
            # set to the same as the attributes in the new element then we will not create
            # the new element

            existing = self.get_existing_elements(new, new.ignore_existing)
            if len(existing) > 0:
                return

        self.el.append(new.el)

    def createLXMLElement(self, info, nsmap=None, files=None, folderToParse='', parent=None):
        if nsmap is None:
            nsmap = {}

        if files is None:
            files = []

        self.parent = parent
        if parent is not None:
            siblings_same_name = len(parent.el.findall(self.name))
            self.parent_pos = siblings_same_name
        else:
            self.parent_pos = 0

        logger.debug(u'Creating lxml-element for {path}'.format(path=self.get_path()))

        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            self.el = etree.Element(u"{{{}}}{}".format(full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            self.el = etree.Element(u"{}".format(self.name), nsmap=full_nsmap)

        self.el.text = self.parse(info)


        for req_param in self.requiredParameters:
            if info.get(req_param) is None or len(info.get(req_param, '')) == 0:
                return None


        for attr in self.attr:
            name, content, required = attr.parse(info, nsmap=full_nsmap)

            if required and not content:
                raise ValueError(u"Missing value for required attribute '{}' on element '{}'".format(name, self.get_path()))
            elif content or attr.allow_empty:
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

        for child_idx, child in enumerate(self.children):
            child.parent = self
            child.parent_pos = child_idx
            if child.containsFiles:
                for fileinfo in files:
                    include = True

                    for key, file_filter in six.iteritems(child.fileFilters):
                        if not re.search(file_filter, fileinfo.get(key)):
                            include = False

                    if include:
                        logger.debug(u'Creating child element with additional file data: {data}'.format(data=fileinfo))
                        full_info = info.copy()
                        full_info.update(fileinfo)
                        child_el = child.createLXMLElement(full_info, full_nsmap, files=files, folderToParse=folderToParse, parent=self)
                        if child_el is not None:
                            self.add_element(child)

            elif child.foreach is not None:
                try:
                    foreach_el = info[child.foreach]
                except KeyError:
                    msg = u'Foreach key "{key}" for {el} not found in data'.format(key=child.foreach, el=child.get_path())
                    logger.warning(msg)
                    continue

                try:
                    iterator = six.iteritems(foreach_el)
                except AttributeError:
                    iterator = enumerate(foreach_el)

                for idx, v in iterator:
                    child_info = copy.deepcopy(info)
                    child_info.update(v)
                    child_info[u'{foreach}__key'.format(foreach=child.foreach)] = idx

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
                logger.warn(u"Nested XML '{}' not found in data and will not be created".format(self.nestedXMLContent))
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
        self.allow_empty = template.get('-allowEmpty', False)

    def parse(self, info, nsmap=None):
        if nsmap is None:
            nsmap = {}

        name = self.name

        if self.namespace:
            name = "{%s}%s" % (nsmap.get(self.namespace), self.name)

        content = parseContent(self.content, info)
        if content is None and self.allow_empty:
            content = ""

        return name, content, self.required


class XMLGenerator(object):
    def __init__(self, filepath=None):
        self.parser = etree.XMLParser(remove_blank_text=True)
        self.fid = FormatIdentifier(allow_unknown_file_types=False)

        if filepath is not None:
            self.tree = etree.parse(filepath, parser=self.parser)
        else:
            self.tree = None

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

    def generate(self, filesToCreate, folderToParse=None, extra_paths_to_parse=None, parsed_files=None, relpath=None, algorithm='SHA-256'):
        self.toCreate = []
        for fname, content in six.iteritems(filesToCreate):
            self.toCreate.append({
                'file': fname,
                'template': content['spec'],
                'data': content.get('data', {}),
                'root': XMLElement(content['spec'])
            })

        if extra_paths_to_parse is None:
            extra_paths_to_parse = []

        if parsed_files is None:
            parsed_files = []

        files = parsed_files

        # See if any profile allows unknown file types.
        # If atleast one does allow it, we allow it for all profiles.
        allow_unknown_file_types = False
        for idx, f in enumerate(self.toCreate):
            allow_unknown_file_types = f.get('data', {}).get('allow_unknown_file_types', False)
            if allow_unknown_file_types:
                break

        self.fid.allow_unknown_file_types = allow_unknown_file_types

        if folderToParse:
            folderToParse = six.text_type(folderToParse).rstrip('/')

            external = self.find_external_dirs()
            if external:
                external_gen = XMLGenerator()

            for ext_file, ext_dir, ext_spec, ext_data in external:
                ext_sub_dirs = next(walk(os.path.join(folderToParse, ext_dir)))[1]
                for sub_dir in ext_sub_dirs:
                    ptr_file_path = os.path.join(ext_dir, sub_dir, ext_file)

                    ext_info = copy.deepcopy(ext_data)
                    ext_info['_EXT'] = sub_dir
                    ext_info['_EXT_HREF'] = ptr_file_path

                    external_to_create={
                        os.path.join(folderToParse, ptr_file_path): {'spec': ext_spec, 'data': ext_info}
                    }
                    external_gen.generate(external_to_create, os.path.join(folderToParse, ext_dir, sub_dir))

                    filepath = os.path.join(folderToParse, ptr_file_path)

                    fileinfo = parse_file(filepath, self.fid, ptr_file_path, algorithm=algorithm, rootdir=sub_dir)
                    files.append(fileinfo)

            if os.path.isfile(folderToParse):
                filepath = folderToParse
                relpath = os.path.basename(folderToParse)

                fileinfo = parse_file(filepath, self.fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in walk(folderToParse):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)

                        fileinfo = parse_file(filepath, self.fid, relpath, algorithm=algorithm)
                        files.append(fileinfo)

        for path in extra_paths_to_parse:
            if os.path.isfile(path):
                relpath = os.path.basename(path)

                fileinfo = parse_file(path, self.fid, relpath, algorithm=algorithm)
                files.append(fileinfo)

            elif os.path.isdir(path):
                for root, dirnames, filenames in walk(path):
                    dirnames[:] = [d for d in dirnames if d not in [e[1] for e in external]]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, path)

                        fileinfo = parse_file(filepath, self.fid, relpath, algorithm=algorithm, rootdir=path)
                        files.append(fileinfo)

        for idx, f in enumerate(self.toCreate):
            fname = f['file']
            rootEl = f['root']
            data = f.get('data', {})

            data['_XML_FILENAME'] = os.path.basename(fname)

            logger.debug(u'Creating {f} with {d}'.format(f=fname, d=data))

            self.tree = etree.ElementTree(
                rootEl.createLXMLElement(data, files=files, folderToParse=folderToParse)
            )
            self.write(fname)

            if relpath:
                relfilepath = os.path.relpath(fname, relpath)
            elif folderToParse:
                relfilepath = os.path.relpath(fname, folderToParse)
            else:
                relfilepath = fname

            if idx < len(self.toCreate) - 1:
                fileinfo = parse_file(fname, self.fid, relfilepath, algorithm=algorithm)
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

        root_nsmap = {k: v for k, v in six.iteritems(target.nsmap) if k}
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
