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

import copy
import datetime
import logging
import os
import re
import uuid
from os import walk

from django.template import Context, Template, TemplateSyntaxError
from django.utils import timezone
from lxml import etree
from natsort import natsorted

from ESSArch_Core.essxml.util import parse_file
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.util import (
    get_elements_without_namespace,
    in_directory,
    make_unicode,
    nested_lookup,
    normalize_path,
)

leading_underscore_tag_re = re.compile(r'%s *_(.*?(?=\}))%s' % (re.escape('{{'), re.escape('}}')))


def parse_content_django(content, info=None, unicode_error=False, syntax_error=False):
    info_copy = {**info}
    for k, v in info_copy.items():
        if (isinstance(v, (str, bytes))):
            info[k] = make_unicode(v)

    c = Context(info)
    try:
        t = Template(content)
    except TemplateSyntaxError:
        if syntax_error:
            raise

        def remove_underscore_prefix(d):
            new = {}
            for k, v in d.items():
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

    return t.render(c)


def parseContent(content, info=None):
    if not content:
        return None

    if info is None:
        info = {}

    if isinstance(content, str):
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


def extNatsort(dirs, submission='submission'):
    sorted_dirs = []
    dirs_without_submission = []
    for d in dirs:
        if submission == d:
            sorted_dirs.append(d)
        else:
            dirs_without_submission.append(d)
    sorted_dirs.extend(natsorted(dirs_without_submission))

    return sorted_dirs


class XMLElement:
    def __init__(self, template, nsmap=None, fid=None):
        if nsmap is None:
            nsmap = {}

        name = template.get('-name')
        try:
            self.name = name.split("#")[0]
        except BaseException:
            self.name = name

        self.nsmap = template.get('-nsmap', {})
        self.nsmap.update(nsmap)
        self.namespace = template.get('-namespace')
        self.required = template.get('-req', False)
        self.attr = [XMLAttribute(a) for a in template.get('-attr', [])]
        self.content = template.get('#content', [])
        self.nestedXMLContent = template.get('-nestedXMLContent')
        self.CDATAContent = template.get('-CDATAContent')
        self.containsFiles = template.get('-containsFiles', False)
        self.foreach = template.get('-foreach', None)
        self.foreachdir = template.get('-foreachdir', None)
        self.enable_FILEGROUPID = template.get('-enable_FILEGROUPID', False)
        self.replace_existing = template.get('-replaceExisting', None)
        self.ignore_existing = template.get('-ignoreExisting', None)
        self.external = template.get('-external')
        self.fileFilters = template.get('-filters', {})
        self.allowEmpty = template.get('-allowEmpty', False)
        self.hideEmptyContent = template.get('-hideEmptyContent', False)
        self.skipIfNoChildren = template.get('-skipIfNoChildren', False)
        self.condition = template.get('-if', None)
        self.requiredParameters = template.get('-requiredParameters', [])
        self.children = []
        self.el = None
        self.parent = None
        self.parent_pos = 0

        self._fid = fid

        for child in template.get('-children', []):
            child_el = XMLElement(child)
            self.children.append(child_el)

    @ property
    def fid(self):
        if self._fid is not None:
            return self._fid

    def createExternalElement(self, info, nsmap=None, files=None, folderToParse='', algorithm=None, external=None):
        logger = logging.getLogger('essarch.essxml.generator')
        external_elements = []
        if external is None:
            external = self.external
        ext_root = os.path.join(folderToParse, external['-dir'])
        try:
            ext_dirs = next(walk(ext_root))[1]
        except StopIteration:
            logger.info('No directories found in ext_root {}'.format(ext_root))
        else:
            for ext_dir in extNatsort(ext_dirs):
                if '-pointer' in external:
                    ext_files = []
                    ptr = XMLElement(external['-pointer'], fid=self.fid)
                    ptr_file_path = os.path.join(external['-dir'], ext_dir, external['-file'])
                    ptr_file_path = normalize_path(ptr_file_path)
                    ptr_info = info.copy()
                    ptr_info['_EXT'] = ext_dir
                    ptr_info['_EXT_HREF'] = ptr_file_path
                    ptr_fileinfo = None

                    for fileinfo in files:
                        if fileinfo.get('href') == ptr_file_path:
                            ptr_fileinfo = fileinfo
                            break

                    if ptr_fileinfo is None:
                        filepath = os.path.join(folderToParse, ptr_file_path)
                        ptr_fileinfo = parse_file(
                            filepath, self.fid, ptr_file_path, algorithm=algorithm, rootdir=ext_dir
                        )

                    ext_files.append(ptr_fileinfo)
                    child_el = ptr.createLXMLElement(
                        ptr_info,
                        nsmap,
                        files=ext_files,
                        folderToParse=folderToParse,
                        parent=self,
                        algorithm=algorithm,
                    )

                    if child_el is not None:
                        external_elements.append(ptr)
        return external_elements

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

        if self.CDATAContent:
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

    def get_root_element(self, parent=None):
        if parent is None:
            parent = self.parent

        if parent.parent:
            el = self.get_root_element(parent.parent)
        else:
            el = parent.el

        return el

    def get_path(self, path=None):
        if path is None:
            path = []

        path = '%s[%s]' % (self.name, self.parent_pos)

        if self.parent:
            path = self.parent.get_path(path) + '/' + path
        else:
            path = '/' + path

        return path

    def get_FILEGROUPID(self, child, child_info):
        logger = logging.getLogger('essarch.essxml.generator')
        id = None
        attr_label = None
        for attr in child.attr:
            if attr.name == 'LABEL':
                attr_label = attr.parse(child_info)[1]
        if attr_label:
            root_element = child.get_root_element()
            groups = root_element.xpath(
                ".//*[local-name()='{el}'][@USE='{USE}']".format(el='fileGrp', USE=attr_label))
            if len(groups) == 1:
                id = groups[0].get('ID')
            elif len(groups) > 1:
                logger.warning('More then one fileGrp with USE attribute "{}"'.format(attr_label))

        return id

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

    def createLXMLElement(self, info, nsmap=None, files=None, folderToParse='', parent=None, algorithm=None):
        logger = logging.getLogger('essarch.essxml.generator')
        if nsmap is None:
            nsmap = {}

        if files is None:
            files = []

        self.parent = parent
        if parent is not None and self.name is not None:
            siblings_same_name = len(parent.el.findall(self.name))
            self.parent_pos = siblings_same_name
        else:
            self.parent_pos = 0

        full_nsmap = nsmap.copy()
        full_nsmap.update(self.nsmap)

        if self.namespace:
            self.el = etree.Element("{{{}}}{}".format(full_nsmap[self.namespace], self.name), nsmap=full_nsmap)
        else:
            self.el = etree.Element("{}".format(self.name), nsmap=full_nsmap)

        self.el.text = self.parse(info)

        for req_param in self.requiredParameters:
            if info.get(req_param) is None or info.get(req_param, '') == '':
                return None

        if self.condition is not None:
            condition = parseContent(self.condition, info)
            if condition == 'False':
                return None

        for attr in self.attr:
            name, content, required = attr.parse(info, nsmap=full_nsmap)

            if required and not content:
                raise ValueError(
                    "Missing value for required attribute '{}' on element '{}'".format(
                        name, self.get_path()
                    )
                )
            elif content or attr.allow_empty:
                self.el.set(name, content)

        for child_idx, child in enumerate(self.children):
            child.parent = self
            child.parent_pos = child_idx
            if child.containsFiles:
                for fileinfo in files:
                    include = True

                    for key, file_filter_raw in child.fileFilters.items():
                        file_filter = parseContent(file_filter_raw, info)
                        if not re.search(file_filter, fileinfo.get(key, '')):
                            include = False

                    if include:
                        full_info = info.copy()
                        full_info.update(fileinfo)
                        child_el = child.createLXMLElement(
                            full_info,
                            full_nsmap,
                            files=files,
                            folderToParse=folderToParse,
                            parent=self,
                            algorithm=algorithm,
                        )
                        if child_el is not None:
                            self.add_element(child)

            elif child.foreach is not None:
                try:
                    foreach_el = info[child.foreach]
                except KeyError:
                    msg = 'Foreach key "{key}" for {el} not found in data'.format(
                        key=child.foreach, el=child.get_path()
                    )
                    logger.warning(msg)
                    continue

                try:
                    iterator = foreach_el.items()
                except AttributeError:
                    iterator = enumerate(foreach_el)

                for idx, v in iterator:
                    child_info = copy.deepcopy(info)
                    child_info.update(v)
                    child_info['{foreach}__key'.format(foreach=child.foreach)] = idx

                    child_el = child.createLXMLElement(
                        child_info,
                        full_nsmap,
                        files=files,
                        folderToParse=folderToParse,
                        parent=self,
                        algorithm=algorithm,
                    )
                    if child_el is not None:
                        self.add_element(child)

            elif child.foreachdir is not None:
                foreachdir_root = os.path.join(folderToParse, child.foreachdir)
                try:
                    foreach_dirs = next(walk(foreachdir_root))[1]
                except StopIteration:
                    logger.info('No directories found in foreachdir_root {}'.format(foreachdir_root))
                else:
                    for foreach_dir in extNatsort(foreach_dirs):
                        child_info = info.copy()
                        child_info['_DIR'] = foreach_dir
                        if child.enable_FILEGROUPID:
                            child_info['_FILEGROUPID'] = self.get_FILEGROUPID(child, child_info)

                        child_el = child.createLXMLElement(
                            child_info,
                            full_nsmap,
                            files=files,
                            folderToParse=folderToParse,
                            parent=self,
                            algorithm=algorithm,
                        )
                        if child_el is not None:
                            self.add_element(child)

            elif child.external is not None:
                external_elements = self.createExternalElement(info, nsmap=full_nsmap, files=files,
                                                               folderToParse=folderToParse, algorithm=algorithm,
                                                               external=child.external)
                for external_element in external_elements:
                    self.add_element(external_element)

            else:
                if child.enable_FILEGROUPID:
                    child_info = info.copy()
                    child_info['_FILEGROUPID'] = self.get_FILEGROUPID(child, child_info)
                else:
                    child_info = info
                child_el = child.createLXMLElement(
                    child_info,
                    full_nsmap,
                    files=files,
                    folderToParse=folderToParse,
                    parent=self,
                    algorithm=algorithm,
                )
                if child_el is not None:
                    self.add_element(child)

        if self.nestedXMLContent:
            # we encode the XML to get around LXML limitation with XML strings
            # containing encoding information.
            #
            # See:
            # https://stackoverflow.com/questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
            if self.nestedXMLContent not in info:
                logger.warning(
                    "Nested XML '{}' not found in data and will not be created".format(self.nestedXMLContent)
                )
                if not self.allowEmpty:
                    return None
            else:
                try:
                    nested_xml = info[self.nestedXMLContent].decode().encode('utf-8')
                except (UnicodeDecodeError, AttributeError):
                    nested_xml = bytes(bytearray(info[self.nestedXMLContent], encoding='utf-8'))
                parser = etree.XMLParser(remove_blank_text=True)
                self.el.append(etree.fromstring(nested_xml, parser=parser))

        if self.CDATAContent:
            # we encode the XML to get around LXML limitation with XML strings
            # containing encoding information.
            #
            # See:
            # https://stackoverflow.com/questions/15830421/xml-unicode-strings-with-encoding-declaration-are-not-supported
            if self.CDATAContent not in info:
                logger.warning(
                    "CDATA '{}' not found in data and will not be created".format(self.CDATAContent)
                )
                if not self.allowEmpty:
                    return None
            else:
                nested_xml = info[self.CDATAContent]
                self.el.text = etree.CDATA(nested_xml)

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


class XMLAttribute:
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


def find_files_in_path_not_in_external_dirs(fid, path, external, algorithm, rootdir=""):
    files = []
    external = [e[0] for e in external]
    for root, _dirnames, filenames in walk(path):
        for fname in filenames:
            filepath = os.path.join(root, fname)
            relpath = os.path.relpath(filepath, path)

            in_external = False
            for e in external:
                if in_directory(relpath, e):
                    in_external = True
            if in_external:
                continue

            fileinfo = parse_file(filepath, fid, relpath, algorithm=algorithm, rootdir=rootdir)
            files.append(fileinfo)
    return files


def parse_files(fid, path, external, algorithm, rootdir):
    files = []
    if os.path.isfile(path):
        relpath = os.path.basename(path)

        file_info = parse_file(path, fid, relpath, algorithm=algorithm)
        files.append(file_info)

    elif os.path.isdir(path):
        found_files = find_files_in_path_not_in_external_dirs(fid, path, external, algorithm, rootdir)
        files.extend(found_files)
    return files


class XMLGenerator:
    def __init__(self, filepath=None, allow_unknown_file_types=False, allow_encrypted_files=False):
        self.parser = etree.XMLParser(remove_blank_text=True)
        self.fid = FormatIdentifier(
            allow_unknown_file_types=allow_unknown_file_types,
            allow_encrypted_files=allow_encrypted_files,
        )

        if filepath is not None:
            self.tree = etree.parse(filepath, parser=self.parser)
        else:
            self.tree = None

    def find_external_dirs(self):
        dirs = []
        found_paths = []
        found_dirs = {}

        for spec in self.toCreate:
            res = nested_lookup('-external', spec['template'])

            for x in res:
                _filters = x.get('-filters', {})
                _file = x.get('-file')
                _dir = x.get('-dir')
                _specification = x.get('-specification')
                if _specification:
                    path = os.path.join(_dir, _file)

                    external_nsmap = spec['template'].get('-nsmap', {}).copy()
                    external_nsmap.update(_specification.get('-nsmap', {}))
                    _specification['-nsmap'] = external_nsmap

                    if path not in found_paths:
                        found_paths.append(path)
                        if _dir not in found_dirs:
                            found_dirs[_dir] = {'file': _file, 'filters': _filters}
                        dirs.append((_dir, _file, _specification, x.get('-pointer'), spec['data'], _filters))
                else:
                    if _dir not in found_dirs.keys():
                        found_dirs[_dir] = {'file': _file, 'filters': _filters}

            for found_dir in found_dirs.keys():
                if found_dir not in [d[0] for d in dirs]:
                    dirs.append((found_dir, found_dirs[found_dir]['file'], None,
                                 None, None, found_dirs[found_dir]['filters']))

        return dirs

    def generate(self, filesToCreate, folderToParse=None, extra_paths_to_parse=None,
                 parsed_files=None, relpath=None, algorithm='SHA-256'):

        logger = logging.getLogger('essarch.essxml.generator')
        self.toCreate = []
        for fname, content in filesToCreate.items():
            self.toCreate.append({
                'file': fname,
                'template': content['spec'],
                'data': content.get('data', {}),
                'root': XMLElement(content['spec'], fid=self.fid)
            })

        if extra_paths_to_parse is None:
            extra_paths_to_parse = []

        if parsed_files is None:
            parsed_files = []

        files = parsed_files

        # See if any profile allows unknown file types.
        # If atleast one does allow it, we allow it for all profiles.
        allow_unknown_file_types = False
        for _idx, f in enumerate(self.toCreate):
            allow_unknown_file_types = f.get('data', {}).get('allow_unknown_file_types', False)
            if allow_unknown_file_types:
                break

        self.fid.allow_unknown_file_types = allow_unknown_file_types

        if folderToParse:
            folderToParse = str(folderToParse).rstrip('/')

            external_dirs_files_to_create = {}
            external = self.find_external_dirs()
            if external:
                external_gen = XMLGenerator()

            for ext_dir, ext_file, ext_spec, ext_pointer, ext_data, ext_filters in external:
                if ext_file:
                    ext_root = os.path.join(folderToParse, ext_dir)
                    try:
                        ext_sub_dirs = next(walk(ext_root))[1]
                    except StopIteration:
                        logger.info('No directories found in {}'.format(ext_root))
                    else:
                        for sub_dir in ext_sub_dirs:
                            generate_content_metadata_flag = True

                            for key, file_filter in ext_filters.items():
                                if key == 'GenerateContentMetadata' and not re.search(file_filter, sub_dir):
                                    generate_content_metadata_flag = False

                            ptr_file_path = os.path.join(ext_dir, sub_dir, ext_file)
                            ptr_file_path = normalize_path(ptr_file_path)

                            ext_info = copy.deepcopy(ext_data)
                            ext_info['_EXT'] = sub_dir
                            ext_info['_EXT_HREF'] = ptr_file_path

                            full_xml_path = os.path.join(folderToParse, ptr_file_path)
                            try:
                                external_dirs_files_to_create[sub_dir][0][full_xml_path] = {
                                    'spec': ext_spec, 'data': ext_info, 'ext_pointer': ext_pointer}
                            except KeyError:
                                external_dirs_files_to_create[sub_dir] = [{
                                    full_xml_path: {
                                        'spec': ext_spec, 'data': ext_info, 'ext_pointer': ext_pointer
                                    }
                                }, folderToParse, ext_dir, generate_content_metadata_flag]
                            if generate_content_metadata_flag:
                                try:
                                    os.remove(full_xml_path)
                                except FileNotFoundError:
                                    pass

            for sub_dir in sorted(external_dirs_files_to_create.keys()):
                (external_files_to_create, folderToParse, ext_dir, generate_content_metadata_flag
                 ) = external_dirs_files_to_create[sub_dir]
                if generate_content_metadata_flag:
                    external_gen.generate(external_files_to_create,
                                          folderToParse=os.path.join(folderToParse, ext_dir, sub_dir))

                for external_file_to_create in external_files_to_create.keys():
                    if external_files_to_create[external_file_to_create]['ext_pointer'] is not None:
                        ptr_file_path = os.path.relpath(external_file_to_create, folderToParse)
                        fileinfo = parse_file(
                            external_file_to_create, self.fid, ptr_file_path, algorithm=algorithm, rootdir=sub_dir,
                        )
                        files.append(fileinfo)

            for file_to_append in parse_files(self.fid, folderToParse, external, algorithm, rootdir=""):
                file_alreay_exists = False
                for file_in_list in files:
                    if file_in_list['href'] == file_to_append['href']:
                        file_alreay_exists = True
                if not file_alreay_exists:
                    files.append(file_to_append)

        for path in extra_paths_to_parse:
            files.extend(parse_files(self.fid, path, external, algorithm, rootdir=path))

        for idx, f in enumerate(self.toCreate):
            fname = f['file']
            rootEl = f['root']
            data = f.get('data', {})

            data['_XML_FILENAME'] = os.path.basename(fname)

            self.tree = etree.ElementTree(
                rootEl.createLXMLElement(data, files=files, folderToParse=folderToParse, algorithm=algorithm)
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

        root_nsmap = {k: v for k, v in target.nsmap.items() if k}
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
