from django.conf import settings
from lxml import etree
import os
import json
import copy
import uuid, weakref
from collections import OrderedDict

complexTypes = OrderedDict()
attributeGroups = OrderedDict()
groups = OrderedDict()
pretty = True
eol_ = '\n'
choiseCount = 0
elCount = {}
finishedGroups = OrderedDict()
finishedComplexTypes = OrderedDict()
attributesComplexTypes = {}

TYPE_ELEMENT = 0
TYPE_CHOISE = 1
TYPE_TO = 2
TYPE_TO_CHOISE = 3

def getIndent(level):
    indent = ''
    for i in range(level):
        indent += '   '
    return indent

def pretty_print(fd, level, pretty):
    if pretty:
        for idx in range(level):
            os.write(fd, '    ')

class xmlAttribute(object):
    '''
    dsf.
    '''
    attrName = ''
    req = False
    value = ''

    def __init__(self, attrName, value=''):
        self.attrName = attrName
        self.value = value

    def printXML(self, fd):
        if self.value is not '':
            os.write(fd, ' ' + self.attrName + '="' + self.value + '"')

class xmlElement():

    def __init__(self, name, path):
        self.name = name
        self.path = path + ':' + self.name
        self.children = []
        # self.tagName = tagName
        # self.children = []
        # self.attributes = []
        self.attrib = []
        self.value = ''
        self.karMin = 0
        self.karMax = -1
        self.meta = OrderedDict()
        self.uuid = uuid.uuid4().__str__()
        self.anyAttribute = False
        self.anyElement = False
        self.choise = -1
        self.type = 0
        # self.namespace = namespace
        # self.completeTagName = ''
        # self.containsFiles = False
        # self.printed = 0
        # if self.namespace != '':
            # self.completeTagName += self.namespace + ':'
        # self.completeTagName += str(self.tagName)

    def printXML(self, fd, level=0):
        # if self.containsFiles:
            # print "contaions iles: " + self.tagName
        pretty_print(fd, level, pretty)
        os.write(fd, '<' + self.name)
        for a in self.attributes:
            a.printXML(fd)
        if self.children or self.value is not '':
            os.write(fd, '>' + eol_)
            for child in self.children:
                if child.printXML(fd, level + 1):
                    return True
            if self.value is not '':
                pretty_print(fd, level + 1, pretty)
                os.write(fd, self.value + eol_)
            pretty_print(fd, level, pretty)
            os.write(fd, '</' + self.name + '>' + eol_)
        else:
            os.write(fd, '/>' + eol_)

        # for att in self.attrib:
            # print self.name + ': ' + att + ': ' + str(self.attrib[att])

    # def generateJSON(self):
    #     result = OrderedDict()
    #     result['name'] = self.name
    #     result['key'] = uuid.uuid4().__str__()
    #     path = self.path
    #     result['path'] = path
    #     children = []
    #     for child in self.children:
    #         children.append(child.generateJSON())
    #     result['children'] = children
    #     result['attributes'] = self.attrib
    #     result['meta'] = self.meta
    #     return result

    # def generateStruct(self, addChildren=True):
    #     result = OrderedDict()
    #     result['name'] = self.name
    #     result['key'] = self.uuid
    #     result['templateOnly'] = False
    #     # result['meta'] = self.meta
    #     # result['path'] = self.path
    #     # result['templateOnly'] = False
    #     arr = []
    #     cElement = []
    #     currentChoise = -1
    #     if addChildren:
    #         for child in self.children:
    #             if child.choise == -1:
    #                 arr.append(child.generateStruct())
    #             else:
    #                 if currentChoise == child.choise:
    #                     cElement.append(child.generateStruct(addChildren=False))
    #                 else:
    #                     cElement = []
    #                     currentChoise = child.choise
    #                     cElement.append(child.generateStruct(addChildren=False))
    #                     r = {}
    #                     r['key'] = 'choise:'+str(uuid.uuid4().__str__())
    #                     r['name'] = 'Choose one of'
    #                     r['children'] = cElement
    #                     arr.append(r)
    #     else:
    #         result['templateOnly'] = True
    #
    #     result['children'] = arr
    #     return result

    def listAllElements(self, parent='none'):
        res = {}
        if self.type == TYPE_ELEMENT:
            element = {}
            element['name'] = self.name
            element['min'] = self.karMin
            element['max'] = self.karMax
            element['form'] = self.attrib
            element['userForm'] = []
            element['formData'] = {}
            element['userCreated'] = False
            element['anyAttribute'] = self.anyAttribute
            element['anyElement'] = self.anyElement
            element['containsFiles'] = False
            element['parent'] = parent
            element['children'] = [];
            children = []
            for child in self.children:
                r, c, a = child.listAllElements(self.name)
                children = children + c
                element['form'] = element['form'] + a
                res.update(r)
            element['avaliableChildren'] = children
            res[self.name] = element
            el = {}
            el['type'] = 'element'
            el['name'] = self.name
            return res, [el], []
        elif self.type == TYPE_CHOISE:
            el = {}
            el['type'] = 'choise'
            children = []
            for child in self.children:
                r, c, a = child.listAllElements(parent)
                children = children + c
                res.update(r)
            el['elements'] = children
            return res, [el], []
        elif self.type == TYPE_TO:
            el = {}
            el['type'] = 'element'
            el['name'] = self.name
            return {}, [el], self.attrib
        elif self.type == TYPE_TO_CHOISE:
            # for child in self.children:
                # print child.type
            # print self.children
            return {}, self.children, self.attrib

        # res = {}
        # el = {}
        # el['name'] = self.name
        # el['min'] = self.karMin
        # el['max'] = self.karMax
        # #form
        # el['form'] = self.attrib
        # el['userForm'] = []
        # el['formData'] = {}
        # el['userCreated'] = False
        # el['anyAttribute'] = self.anyAttribute
        # el['anyElement'] = self.anyElement
        # el['containsFiles'] = False
        # children = []
        # currentChoise = -1
        # cElement = OrderedDict()
        # elements = None
        #
        #
        # for child in self.children:
        #     if child.choise == -1:
        #         if elements == None:
        #             elements = []
        #         c = {}
        #         c['type'] = 'element'
        #         c['name'] = child.name
        #         elements.append(c)
        #     else:
        #         if elements != None:
        #             r = {}
        #             r['type'] = 'sequence'
        #             r['elements'] = elements
        #             children.append(r)
        #             elements = None
        #         if currentChoise == child.choise:
        #             #add to last choise element
        #             e = OrderedDict()
        #             e['name'] = child.name
        #             cElement['elements'].append(e)
        #         else:
        #             # create choise element
        #             cElement = OrderedDict()
        #             cElement['type'] = 'choise'
        #             e = OrderedDict()
        #             e['name'] = child.name
        #             cElement['elements'] = []
        #             cElement['elements'].append(e)
        #             children.append(cElement)
        #             currentChoise = child.choise
        # if elements != None:
        #     r = {}
        #     r['type'] = 'sequence'
        #     r['elements'] = elements
        #     children.append(r)
        #
        # el['children'] = children
        #
        # for child in self.children:
        #     arr = child.listAllElements(parent=self.name)
        #     res.update(arr)
        # res[self.name] = el
        # return res

    def listAllElementTypes(self, parent='none'):
        res = {}
        # el = {}
        # el['name'] = self.name
        # el['min'] = self.karMin
        # el['max'] = self.karMax
        # el['parent'] = parent
        # #form
        # el['form'] = self.attrib
        # el['userForm'] = []
        # el['formData'] = {}
        # el['userCreated'] = False
        # el['anyAttribute'] = self.anyAttribute
        # el['anyElement'] = self.anyElement
        # el['containsFiles'] = False
        # children = []
        # currentChoise = -1
        # cElement = OrderedDict()
        # elements = None
        # for child in self.children:
        #     if child.choise == -1:
        #         if elements == None:
        #             elements = []
        #         c = {}
        #         c['type'] = 'element'
        #         c['uuid'] = child.uuid
        #         c['name'] = child.name
        #         elements.append(c)
        #     else:
        #         if elements != None:
        #             r = {}
        #             r['type'] = 'sequence'
        #             r['elements'] = elements
        #             children.append(r)
        #             elements = None
        #         if currentChoise == child.choise:
        #             #add to last choise element
        #             e = OrderedDict()
        #             e['name'] = child.name
        #             cElement['elements'].append(e)
        #         else:
        #             # create choise element
        #             cElement = OrderedDict()
        #             cElement['type'] = 'choise'
        #             e = OrderedDict()
        #             e['name'] = child.name
        #             cElement['elements'] = []
        #             cElement['elements'].append(e)
        #             children.append(cElement)
        #             currentChoise = child.choise
        # if elements != None:
        #     r = {}
        #     r['type'] = 'sequence'
        #     r['elements'] = elements
        #     children.append(r)
        #
        # el['children'] = children
        # childsParent = self.uuid
        # if parent == 'none':
        #     childsParent = 'root'
        # res[childsParent] = el
        #
        # for child in self.children:
        #     if child.choise == -1:
        #         arr = child.listAllElementTypes(parent=childsParent)
        #         res.update(arr)
        return res

    # def generateJSONTemplate(self):
    #     content = OrderedDict()
    #     content['-min'] = self.karMin
    #     content['-max'] = self.karMax
    #     attr = []
    #     for a in self.attrib:
    #         to = a['templateOptions']
    #         b = OrderedDict()
    #         b['-name'] = to['label']
    #         b['-req'] = int(to['required'])
    #         b['#content'] = []
    #         attr.append(b)
    #     content['-attr'] = attr
    #     for child in self.children:
    #         name, con = child.generateJSONTemplate()
    #         if name in content:
    #             if isinstance(content[name], list):
    #                 content[name].append(con)
    #             else:
    #                 c = content[name]
    #                 content[name] = []
    #                 content[name].append(c)
    #                 content[name].append(con)
    #         else:
    #             content[name] = con
    #     return self.name, content

    def isEmpty(self):
        if self.value != '' or self.children:
            return False
        else:
            return True

    def addChild(self, child):
        # print 'child: ' + child
        self.children.append(child)

    def printDebug(self, level = 0):
        print getIndent(level) + self.name
        for child in self.children:
            child.printDebug(level+1)

    def delete(self):
        self.name = ''
        for child in self.children:
            child.delete()
        self.children = []
        # for att in self.attrib:
        #     att = None
        self.attrib = []
        self.value = ''
        self.karMin = 0
        self.karMax = -1
        self.meta = OrderedDict()
        self.path = ''

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
    tag = tag.split(':')
    if len(tag) > 0:
        return tag[0]
    else:
        return ''

def getPostfix(tag):
    if tag is None:
        return None
    tag = tag.split(':')
    if len(tag) > 1:
        return tag[1]
    else:
        return ''

def analyze2(element, tree, usedTypes=[], minC=0, maxC=1, choise=-1):
    global choiseCount
    global elCount
    # print element.local-name()
    global complexTypes
    global attributeGroups
    global finishedGroups
    global attributesComplexTypes
    tag = printTag(element.tag)
    if tag == 'element':
        meta = OrderedDict()
        if element.get('minOccurs') is not None and int(element.get('minOccurs')) >= 0:
            minC = int(element.get('minOccurs'))
        if element.get('maxOccurs') is None:
            pass
        elif element.get('maxOccurs') == 'unbounded':
            maxC = -1
        else:
            maxC = int(element.get('maxOccurs'))

        if element.get('type') is None:
            t = xmlElement(element.get('name'))
            t.karMin = minC
            t.karMax = maxC
            tree.addChild(t)
            for child in element:
                analyze2(child, t, usedTypes=usedTypes)
        elif getPrefix(element.get('type')) == 'xs' or getPrefix(element.get('type')) == 'xsd':
            t = xmlElement(element.get('name'))
            t.karMin = minC
            t.karMax = maxC
            att = OrderedDict()
            att['key'] = '#content'
            att['type'] = 'input'
            templateOptions = OrderedDict()
            templateOptions['type'] = 'text' # TODO
            templateOptions['label'] = 'Content'
            templateOptions['placeholder'] = 'Content'
            templateOptions['required'] = True
            att['templateOptions'] = templateOptions
            t.attrib.append(att)
            tree.addChild(t)
        else:
            t = xmlElement(element.get('name'), tree.path)
            t.karMin = minC
            t.karMax = maxC
            key = element.get('type')
            tpyeDef = element.get('name') + key
            if tpyeDef not in usedTypes:
                if key in complexTypes:
                    tree.addChild(t)
                    usedTypes.append(tpyeDef)
                    for child in complexTypes[key]:
                        analyze2(child, t, usedTypes=usedTypes)
                    finishedComplexTypes[key] = calculateChildren(tree)
                    attributesComplexTypes[key] = tree.attrib
                else:
                    print "type unknown: " + element.get('type')
            else:
                if key in finishedComplexTypes:
                    t.type = TYPE_TO
                    t.attrib = attributesComplexTypes[key]
                    tree.addChild(t)
    elif tag == 'complexType':
        for child in element:
            analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'complexContent':
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
                    finishedComplexTypes[key] = calculateChildren(tree)
                    attributesComplexTypes[key] = tree.attrib
            else:
                if key in finishedComplexTypes:
                    t = xmlElement('finishedGroup', '')
                    t.type = TYPE_TO_CHOISE
                    t.attrib = attributesComplexTypes[key]
                    t.children = finishedComplexTypes[key]
                    tree.addChild(t)
            for child in element:
                analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'sequence':
        for child in element:
            analyze2(child, tree, usedTypes=usedTypes)
    elif tag == 'choice':
        t = xmlElement('choice', '')
        t.type = TYPE_CHOISE
        tree.addChild(t)
        for child in element:
            analyze2(child, t, usedTypes=usedTypes, choise=choiseCount)
        choiseCount += 1
    elif tag == 'attribute':
        att = parseAttribute(element)
        if att != None:
            tree.attrib.append(att)
        else:
            print 'attribute == none'
    elif tag == 'attributeGroup':
        if element.get('ref'):
            ref = element.get('ref')
            if ref in attributeGroups:
                for child in attributeGroups[ref]:
                    analyze2(child, tree, usedTypes=usedTypes)
            else:
                print 'attributegroup not found'
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
        tree.attrib.append(att)
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
        if element.get('ref') not in usedTypes:
            if element.get('ref') in groups:
                usedTypes.append(element.get('ref'))
                for child in groups[element.get('ref')]:
                    analyze2(child, tree, usedTypes=usedTypes)
                finishedGroups[element.get('ref')] = calculateChildren(tree)
        else:

            if element.get('ref') in finishedGroups:
                t = xmlElement('finishedGroup', '')
                t.type = TYPE_TO_CHOISE
                t.children = finishedGroups[element.get('ref')]
                tree.addChild(t)
    elif tag == 'annotation':
        pass # comments
    else:
        print 'other: ' + tag

def calculateChildren(tree):
    res = []
    for child in tree.children:
        if child.type == TYPE_CHOISE:
            el = {}
            el['type'] = 'choise'
            el['elements'] = calculateChildren(child)
            res.append(el)
        elif child.type == TYPE_ELEMENT:
            el = {}
            el['name'] = child.name
            el['type'] = 'element'
            res.append(el)
        elif child.type == TYPE_TO:
            el = {}
            el['type'] = 'element'
            el['name'] = child.name
            res.append(el)
        elif child.type == TYPE_TO_CHOISE:
            res = res + child.children
    return res

def parseAttribute(element):
    global complexTypes
    global attributeGroups
    att = OrderedDict()
    if element.get('type') is not None:
        att = OrderedDict()
        att['type'] = 'input'
        att['key'] = element.get('name')
        templateOptions = OrderedDict()
        templateOptions['type'] = 'text'  #TODO add options
        templateOptions['label'] = element.get('name')
        use = element.get('use')
        if use is None or use == 'optional':
            templateOptions['required'] = False
        elif use == 'required':
            templateOptions['required'] = True
        else:
            print "Odd use value for attribute. value: " + str(use)
            return None
        att['templateOptions'] = templateOptions
        # print att
    else:
        if element.get('name') is not None:
            att['key'] = element.get('name')
            templateOptions = OrderedDict()
            templateOptions['label'] = element.get('name')
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
                                else:
                                    if isinstance(c.tag, str):
                                        print "unknown restriction: " + c.tag #TODO handle regex string
                                    pass
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

def generateJsonRes(schemaName):
    global complexTypes
    global attributeGroups
    global groups
    # pars = etree.parse("esscore/template/templateGenerator/CSPackageMETS.xsd")
    # pars = etree.parse(os.path.join(settings.BASE_DIR,"esscore/template/templateGenerator/CSPackageMETS.xsd"))
    parser = etree.XMLParser(remove_comments=True)
    pars = etree.parse(schemaName, parser=parser)
    schema = '{http://www.w3.org/2001/XMLSchema}'

    root = pars.getroot()

    for child in root.iterfind(schema + 'complexType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in root.iterfind(schema + 'attributeGroup'):
        if child.get('name'):
            attributeGroups[child.get('name')] = child

    for child in root.iterfind(schema + 'group'):
        if child.get('name'):
            groups[child.get('name')] = child

    for child in root.iterfind(schema + 'element'):
        tag = printTag(child.tag)
        if tag != 'complexType' and tag != 'attributeGroup':
            tree = xmlElement(child.get('name'), '')
            for ch in child:
                analyze2(ch, tree, [])
            if tree is not None:
                # with open('test.txt', 'wb') as outfile: print
                # tree.generateJSON(); struc = tree.generateStruct() el =
                # tree.listAllElements() treeData = tree.generateStruct()
                # existingElements = tree.listAllElementTypes()
                allElements, e, a = tree.listAllElements()
                # temp = tree.listAllElementTypes()
                # j = json.dumps(tree.generateJSON())
                # tree.delete()
                # print json.dumps(allElements['odd'])
                # print allElements['c01']['form']
                existingElements = {}
                existingElements['root'] = copy.deepcopy(allElements[tree.name])
                # print existingElements
                return existingElements, allElements
    # pars = None
    # root = None
    # tree = None
    # complexTypes = OrderedDict()
    # attributeGroups = OrderedDict()

# generateJsonRes("/Users/Axenu/Developer/ESSArch_Tools_Producer/ESSArch_TP2/esscore/template/templateGenerator/CSPackageMETS.xsd")
# print generate()
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
