"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
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
from collections import OrderedDict

from ESSArch_Core.essxml.Generator.xmlStructure import (
    xmlElement,
    TYPE_ELEMENT,
    TYPE_CHOISE,
    TYPE_TO,
    TYPE_TO_CHOISE,
)

complexTypes = OrderedDict()
attributeGroups = OrderedDict()
groups = OrderedDict()
elementTypes = {}
pretty = True
eol_ = '\n'
choiseCount = 0
elCount = {}
finishedGroups = OrderedDict()
finishedComplexTypes = OrderedDict()
attributesComplexTypes = {}


def getIndent(level):
    return '   ' * level


def printTag(tag):
    if isinstance(tag, str):
        a = tag.split('}')
        if len(a) > 1:
            return a[1]
        else:
            return tag
    else:
        return 'unknown tag: ' + str(type(tag))


def getPrefix(tag):
    if tag is None:
        return None

    return tag.split(':')[0]


def getSuffix(tag):
    if tag is None:
        return None
    tag = tag.split(':')[-1]


def analyze2(element, tree, usedTypes=[], minC=0, maxC=1, choise=-1):
    global choiseCount
    global elCount
    global complexTypes
    global attributeGroups
    global finishedGroups
    global attributesComplexTypes
    global elementTypes

    tag = printTag(element.tag)
    ref = element.get('ref')
    el_type = element.get('type')

    if tag == 'element':
        minOccurs = element.get('minOccurs')
        maxOccurs = element.get('maxOccurs')

        if minOccurs and int(minOccurs) >= 0:
            minC = int(minOccurs)

        if maxOccurs:
            maxC = -1 if maxOccurs == 'unbounded' else int(maxOccurs)

        if ref:
            key = ref
            if ':' in key:
                key = key.split(':')[1]
            if key not in usedTypes:
                if key in elementTypes:
                    usedTypes.append(key)
                    analyze2(elementTypes[key], tree, usedTypes=usedTypes)
                else:
                    print "type unknown: " +key
        else:
            t = xmlElement(element.get('name'), namespace=tree.namespace)
            t.karMin = minC
            t.karMax = maxC

            if el_type is None:
                tree.addChild(t)
                for child in element:
                    analyze2(child, t, usedTypes=usedTypes)
            elif getPrefix(el_type) in ['xs', 'xsd']:
                att = OrderedDict()
                att['key'] = '#content'
                att['type'] = 'input'
                templateOptions = OrderedDict()
                templateOptions['type'] = 'text' # TODO
                templateOptions['label'] = 'Content'
                templateOptions['placeholder'] = 'Content'
                templateOptions['required'] = True
                att['templateOptions'] = templateOptions
                t.attributes.append(att)
                tree.addChild(t)
            else:
                key = el_type
                if ':' in key:
                    key = key.split(':')[1]
                tpyeDef = element.get('name') + key
                if tpyeDef not in usedTypes:
                    if key in complexTypes:
                        tree.addChild(t)
                        usedTypes.append(tpyeDef)
                        for child in complexTypes[key]:
                            analyze2(child, t, usedTypes=usedTypes)
                        finishedComplexTypes[key] = tree.calculateChildren()
                        attributesComplexTypes[key] = tree.attributes
                    else:
                        print "type unknown: " + el_type
                else:
                    if key in finishedComplexTypes:
                        t.type = TYPE_TO
                        t.attributes = attributesComplexTypes[key]
                        tree.addChild(t)
    elif tag in ['complexType', 'complexContent', 'sequence']:
        for child in element:
            analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'extension':
        if element.get('base'):
            key = element.get('base')
            if key not in usedTypes:
                if key in complexTypes:
                    usedTypes.append(key)
                    for child in complexTypes[key]:
                        analyze2(child, tree, usedTypes=usedTypes, minC=minC, maxC=maxC)
                    finishedComplexTypes[key] = tree.calculateChildren()
                    attributesComplexTypes[key] = tree.attributes
            elif key in finishedComplexTypes:
                t = xmlElement('finishedGroup', namespace=tree.namespace)
                t.type = TYPE_TO_CHOISE
                t.attributes = attributesComplexTypes[key]
                t.children = finishedComplexTypes[key]
                tree.addChild(t)

            for child in element:
                analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'choice':
        t = xmlElement('choice', namespace=tree.namespace)
        t.type = TYPE_CHOISE
        tree.addChild(t)
        for child in element:
            analyze2(child, t, usedTypes=usedTypes, choise=choiseCount)
        choiseCount += 1
    elif tag == 'attribute':
        if ref:
            if ':' in ref:
                ref = ref.split(':')[1]
            if ref in attributeGroups:
                for child in attributeGroups[ref]:
                    analyze2(child, tree, usedTypes=usedTypes)
        else:
            att = parseAttribute(element)
            if att != None:
                tree.attributes.append(att)
            else:
                print 'attribute == none'
    elif tag == 'attributeGroup':
        if ref:
            if ':' in ref:
                ref = ref.split(':')[1]
            if ref in attributeGroups:
                for child in attributeGroups[ref]:
                    analyze2(child, tree, usedTypes=usedTypes)
            else:
                print 'attributegroup not found: ' + ref
    elif tag == 'anyAttribute':
        tree.anyAttribute = True
    elif tag == 'simpleContent':
        att = OrderedDict()
        att['key'] = '#content'
        att['type'] = 'input'
        templateOptions = OrderedDict()
        templateOptions['type'] = 'text' # TODO
        templateOptions['label'] = 'Content'
        templateOptions['placeholder'] = 'Content'
        templateOptions['required'] = True
        att['templateOptions'] = templateOptions
        tree.attributes.append(att)
        for child in element:
            analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'any':
        tree.anyElement = True
    elif tag == 'all':
        if element.get('minOccurs') is not None:
            minC = int(element.get('minOccurs'))
            if minC != 0 and minC != 1:
                minC = 1
        maxC = 1
        for child in element:
            analyze2(child, tree, usedTypes=usedTypes, minC=minC, maxC=maxC)
    elif tag == 'group':
        if ref not in usedTypes:
            if ref in groups:
                usedTypes.append(ref)
                for child in groups[ref]:
                    analyze2(child, tree, usedTypes=usedTypes)
                finishedGroups[ref] = tree.calculateChildren()
        elif ref in finishedGroups:
            t = xmlElement('finishedGroup', namespace=tree.namespace)
            t.type = TYPE_TO_CHOISE
            t.children = finishedGroups[ref]
            tree.addChild(t)

    elif tag == 'annotation':
        pass # comments
    else:
        print 'other: ' + tag


def parseAttribute(element):
    global complexTypes
    global attributeGroups
    att = OrderedDict()
    name = element.get('name')

    if element.get('type') is not None:
        att = OrderedDict()
        att['type'] = 'input'
        att['key'] = name
        templateOptions = OrderedDict()
        templateOptions['type'] = 'text'  #TODO add options
        templateOptions['label'] = name
        use = element.get('use')
        if use is None or use == 'optional':
            templateOptions['required'] = False
        elif use == 'required':
            templateOptions['required'] = True
        else:
            print "Odd use value for attribute. value: " + str(use)
            return None
        att['templateOptions'] = templateOptions
    else:
        if name:
            att['key'] = name
            templateOptions = OrderedDict()
            templateOptions['label'] = name
            use = element.get('use')
            req = False
            if use is None or use == 'optional':
                templateOptions['required'] = False
            elif use == 'required':
                templateOptions['required'] = True
                req = True
            else:
                print "Odd use value for attribute. value: " + str(use)
                return None
            for child in element:
                if printTag(child.tag) == 'simpleType':
                    for ch in child:
                        if printTag(ch.tag) == 'restriction':
                            enumerations = []
                            for c in ch:
                                if printTag(c.tag) == 'enumeration':
                                    att['type'] = 'select'
                                    a = OrderedDict()
                                    a['name'] = c.get('value')
                                    a['value'] = c.get('value')
                                    enumerations.append(a)
                                elif isinstance(c.tag, str):
                                    print "unknown restriction: " + c.tag #TODO handle regex string
                            if len(enumerations) > 0:
                                if not req:
                                    a = OrderedDict()
                                    a['name'] = ' -- None -- '
                                    a['value'] = ''
                                    enumerations.insert(0, a)
                                templateOptions['options'] = enumerations
            att['templateOptions'] = templateOptions
        else:
            print "ERROR: attribute name is none"
            return None

    return att


def generateExtensionRef(schemadoc, namespace):
    global complexTypes
    global attributeGroups
    global groups
    global elementTypes
    schema = '{http://www.w3.org/2001/XMLSchema}'
    thisSchema = ''
    thisVersion = ''

    for key, value in schemadoc.attrib.iteritems():
        if key == 'targetNamespace':
            thisSchema = value
        elif key == 'version':
            thisVersion = value
        elif key == 'id':
            pass # handle id? TODO
        elif key == 'attributeFormDefault':
            pass # handle attributeFormDefault? TODO
        elif key == 'elementFormDefault':
            pass # handle elementFormDefault? TODO
        elif key == 'blockDefault':
            pass # handle blockDefault? TODO
        elif key == 'finalDefault':
            pass # handle finalDefault? TODO
        elif key == 'xmlns':
            pass # handle xmlns? TODO
        else:
            print 'unknown schema attribute: ' + key + ', ' + value

    for child in schemadoc.iterfind(schema + 'complexType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'simpleType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'attributeGroup'):
        if child.get('name'):
            attributeGroups[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'group'):
        if child.get('name'):
            groups[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'element'):
        if child.get('name'):
            elementTypes[child.get('name')] = child

    allElements = {}
    existingElements = {}
    attributes = {}
    for child in schemadoc:
        if child.tag == (schema + 'element'):
            tag = printTag(child.tag)
            if tag != 'complexType' and tag != 'attributeGroup':
                tree = xmlElement(child.get('name'), namespace=namespace)
                analyze2(child, tree)
                if tree is not None:
                    aE, e, a = tree.children[0].listAllElements()
                    allElements.update(aE)
                    existingElements[tree.tagName] = copy.deepcopy(allElements[tree.tagName])
        elif child.tag == (schema + 'attribute'):
            attributes[child.get('name')] = parseAttribute(child)

    return existingElements, allElements, attributes


def generateJsonRes(schemadoc, rootElement, namespace):
    global complexTypes
    global attributeGroups
    global groups
    global elementTypes
    schema = '{http://www.w3.org/2001/XMLSchema}'
    thisSchema = ''
    thisVersion = ''

    for key, value in schemadoc.attrib.iteritems():
        if key == 'targetNamespace':
            thisSchema = value
        elif key == 'version':
            thisVersion = value
        elif key == 'id':
            pass # handle id? TODO
        elif key == 'attributeFormDefault':
            pass # handle attributeFormDefault? TODO
        elif key == 'elementFormDefault':
            pass # handle elementFormDefault? TODO
        elif key == 'blockDefault':
            pass # handle blockDefault? TODO
        elif key == 'finalDefault':
            pass # handle finalDefault? TODO
        elif key == 'xmlns':
            pass # handle xmlns? TODO
        else:
            print 'unknown schema attribute: ' + key + ', ' + value

    for child in schemadoc.iterfind(schema + 'complexType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'simpleType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'attributeGroup'):
        if child.get('name'):
            attributeGroups[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'group'):
        if child.get('name'):
            groups[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'element'):
        if child.get('name'):
            elementTypes[child.get('name')] = child

    for child in schemadoc.iterfind(schema + 'element'):
        if child.get('name') == rootElement:
            tag = printTag(child.tag)
            if tag != 'complexType' and tag != 'attributeGroup':
                tree = xmlElement(child.get('name'), namespace=namespace)
                analyze2(child, tree)
                if tree is not None:
                    allElements, e, a = tree.children[0].listAllElements()
                    existingElements = {}
                    existingElements['root'] = copy.deepcopy(allElements[rootElement])
                    return existingElements, allElements

# a,b,c=generateExtensionRef("/Users/Axenu/Developer/ESSArch_Tools_Producer/ESSArch_TP2/esscore/template/templateGenerator/xlink.xsd", 'ead')
# print c
# for key in c:
#     print key
# print generate(2)
# print generate(3)
# print generate(4)
                    # json.dump(tree.generateJSON(), outfile)
                # with open('test2.txt', 'wb') as outfile:
                #     name, content = tree.generateJSONTemplate()
                #     arr = OrderedDict()
                #     arr[name] = content
                #     json.dump(arr, outfile)
                # tree.printDebug()
                # tree.printXML(xmlFile)
                # print tree.generateJSON()
            # ch = analyze(child)
            # if ch != None:
            #     for c in ch:
            #         c.printXML(xmlFile)
#     for c in child:
#         if printTag(child.tag) == 'complexType':
#             # go deeper
#             for ch in c:
#
#     print printTag(child.tag)

# attribute = {
#     "MIMETYPE": {
#         "type": "string",
#         "use": "optional"
#     },
#     "CHECKSUMTYPE": {
#         "type": "string",
#         "use":"optional",
#         "restrictions": {
#             "enumeration": ["MD5", "SHA-1", "SHA-256"]
#         }
#     }
# }
#
# attribute2 = [
#     {
#         'key': 'ROLE',
#         'type': 'input',
#         'templateOptions': {
#             'type': 'text',
#             'label': 'ROLE',
#             'placeholder': 'string',
#             'required': True
#         }
#     },
#     {
#         'key': 'OTHERROLE',
#         'type': 'select',
#         'templateOptions': {
#             'label': 'OTHERROLE',
#             'options': [
#                 {'name': 'CREATOR', 'value': 'CREATOR'},
#                 {'name': 'EDITOR', 'value': 'EDITOR'},
#                 {'name': 'ARCHIVIST', 'value': 'ARCHIVIST'},
#             ]
#         }
#     },
# ]

# result = {
#     {
#         "name": "mets",
#         "children": [
#             #repeat
#         ],
#         "attributes": [
#             {
#                 'key': 'ROLE',
#                 'type': 'input',
#                 'templateOptions': {
#                     'type': 'text',
#                     'label': 'ROLE',
#                     'placeholder': 'string',
#                     'required': 'True'
#                 }
#             },
#             {
#                 'key': 'OTHERROLE',
#                 'type': 'select',
#                 'templateOptions': {
#                     'label': 'OTHERROLE',
#                     'options': [
#                         {'name': 'CREATOR', 'value': 'CREATOR'},
#                         {'name': 'EDITOR', 'value': 'EDITOR'},
#                         {'name': 'ARCHIVIST', 'value': 'ARCHIVIST'},
#                     ]
#                 }
#             }
#         ],
#         "meta": {
#             "min": "0",
#             "max": "1"
#         }
#     }
# }
