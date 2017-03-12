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
import mimetypes

from celery import states as celery_states
from celery.result import allow_join_result

from lxml import etree

from django.conf import settings
from django.utils import timezone

from scandir import walk

from ESSArch_Core.configuration.models import (
    Path,
)

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask

from ESSArch_Core.util import (
    creation_date,
    find_destination,
    nested_lookup,
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
        self.attr = [XMLAttribute(a) for a in template.get('-attr', [])]
        self.content = template.get('#content', [])
        self.containsFiles = template.get('-containsFiles', False)
        self.external = template.get('-external')
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

    def isEmpty(self, info={}):
        """
        Simple helper function to check if the tag sould have any contents
        """

        if self.el is None:
            return True

        if len(self.el) == 0 and self.skipIfNoChildren:
            return True

        if len(self.el):
            return False

        any_attribute_with_value = any(value for value in self.el.attrib.values())
        any_children_not_empty = any(not child.isEmpty(info) or (child.isEmpty(info) and child.allowEmpty) for child in self.children)

        if parseContent(self.content, info) or any_children_not_empty or self.containsFiles or any_attribute_with_value:
            return False

        return True

    def createLXMLElement(self, info, nsmap={}, files=[], folderToParse=''):
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

        if self.external:
            ext_dirs = next(walk(os.path.join(folderToParse, self.external['-dir'])))[1]
            for ext_dir in ext_dirs:
                ptr = XMLElement(self.external['-pointer'])
                ptr_file_path = os.path.join(self.external['-dir'], ext_dir, self.external['-file'])

                ptr_info = info
                ptr_info['_EXT'] = ext_dir
                ptr_info['_EXT_HREF'] = ptr_file_path
                self.el.append(ptr.createLXMLElement(ptr_info, full_nsmap, folderToParse=folderToParse))

                external_gen = XMLGenerator(
                    filesToCreate={
                        os.path.join(folderToParse, ptr_file_path): self.external['-specification']
                    },
                    info=info
                )
                external_gen.generate(os.path.join(folderToParse, self.external['-dir'], ext_dir))

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
                        self.el.append(child.createLXMLElement(full_info, full_nsmap, files=files, folderToParse=folderToParse))
            else:
                child_el = child.createLXMLElement(info, full_nsmap, files=files, folderToParse=folderToParse)
                if child_el is not None:
                    self.el.append(child_el)

        if self.isEmpty(info) and not self.allowEmpty:
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
        dirs = set()

        for spec in self.toCreate:
            res = nested_lookup('-external', spec['template'])
            dirs |= set([x['-dir'] for x in res])

        return dirs

    def get_mimetype(self, mtypes, fname):
        file_name, file_ext = os.path.splitext(fname)

        if not file_ext:
            file_ext = file_name

        try:
            return mtypes[file_ext]
        except KeyError:
            raise KeyError("Invalid file type: %s" % file_ext)

    def generate(self, folderToParse=None, algorithm='SHA-256'):
        files = []

        mimetypes.suffix_map = {}
        mimetypes.encodings_map = {}
        mimetypes.types_map = {}
        mimetypes.common_types = {}
        mimetypes_file = Path.objects.get(
            entity="path_mimetypes_definitionfile"
        ).value
        mimetypes.init(files=[mimetypes_file])
        mtypes = mimetypes.types_map

        responsible = None

        if folderToParse:
            step = ProcessStep.objects.create(
                name="File Operations",
                parallel=True,
            )

            tasks = []

            if self.task is not None and self.task.step is not None:
                responsible = self.task.responsible
                step.parent_step_id = self.task.step
                step.save()

            folderToParse = unicode(folderToParse)

            exclude = self.find_external_dirs()

            if os.path.isfile(folderToParse):
                tasks.append(ProcessTask(
                    name="ESSArch_Core.tasks.ParseFile",
                    params={
                        'filepath': folderToParse,
                        'mimetype': self.get_mimetype(mtypes, folderToParse),
                        'relpath': os.path.basename(folderToParse),
                        'algorithm': algorithm
                    },
                    processstep=step,
                    responsible_id=responsible,
                ))
            elif os.path.isdir(folderToParse):
                for root, dirnames, filenames in walk(folderToParse):
                    dirnames[:] = [d for d in dirnames if d not in exclude]

                    for fname in filenames:
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, folderToParse)
                        tasks.append(ProcessTask(
                            name="ESSArch_Core.tasks.ParseFile",
                            params={
                                'filepath': filepath,
                                'mimetype': self.get_mimetype(mtypes, filepath),
                                'relpath': relpath,
                                'algorithm': algorithm
                            },
                            responsible_id=responsible,
                            processstep=step,
                        ))

            ProcessTask.objects.bulk_create(tasks)

            with allow_join_result():
                for fileinfo in step.chunk():
                    files.append(fileinfo)

        for idx, f in enumerate(self.toCreate):
            fname = f['file']
            rootEl = f['root']

            self.info['_XML_FILENAME'] = os.path.basename(fname)

            tree = etree.ElementTree(
                rootEl.createLXMLElement(self.info, files=files, folderToParse=folderToParse)
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
                parsefile_task = ProcessTask.objects.create(
                    name="ESSArch_Core.tasks.ParseFile",
                    params={
                        'filepath': fname,
                        'mimetype': self.get_mimetype(mtypes, fname),
                        'relpath': relpath,
                        'algorithm': algorithm
                    },
                    responsible_id=responsible,
                    processstep_id=self.task.step if self.task else None
                )

                with allow_join_result():
                    files.append(parsefile_task.run().get())

    def insert(self, filename, elementToAppendTo, template, info={}, index=None):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(filename, parser)
        elementToAppendTo = findElementWithoutNamespace(tree, elementToAppendTo)
        root_nsmap = {k: v for k, v in elementToAppendTo.nsmap.iteritems() if k}
        appendedRootEl = XMLElement(template, nsmap=root_nsmap)

        try:
            el = appendedRootEl.createLXMLElement(info)
            if index is not None:
                elementToAppendTo.insert(index, el)
            else:
                elementToAppendTo.append(el)
        except TypeError:
            if el is None:
                raise "Can't insert null element into %s" % appendedRootEl


        tree.write(
            filename, pretty_print=True, xml_declaration=True,
            encoding='UTF-8'
        )
