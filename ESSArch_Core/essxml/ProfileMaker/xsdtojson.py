
from lxml import etree
import os
import json
import copy
import uuid, weakref
from collections import OrderedDict

complexTypes = OrderedDict()
attributeGroups = OrderedDict()
pretty = True
eol_ = '\n'

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

    def __init__(self, name, path=''):
        self.name = name
        self.children = []
        # self.tagName = tagName
        # self.children = []
        # self.attributes = []
        self.attrib = []
        self.value = ''
        self.karMin = 0
        self.karMax = -1
        self.meta = OrderedDict()
        self.path = path + self.name + '/'
        self.uuid = uuid.uuid4().__str__()
        self.anyAttribute = False
        self.anyElement = False
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

    def generateJSON(self):
        result = OrderedDict()
        result['name'] = self.name
        result['key'] = uuid.uuid4().__str__()
        path = self.path
        result['path'] = path
        children = []
        for child in self.children:
            children.append(child.generateJSON())
        result['children'] = children
        result['attributes'] = self.attrib
        result['meta'] = self.meta
        return result

    def generateStruct(self):
        result = OrderedDict()
        result['name'] = self.name
        result['key'] = self.uuid
        result['meta'] = self.meta
        result['path'] = self.path
        result['templateOnly'] = False
        arr = []
        for child in self.children:
            arr.append(child.generateStruct())
        result['children'] = arr
        return result

    def listAllElements(self):
        res = {}
        result = OrderedDict()
        # result['name'] = self.name
        # result['key'] = self.uuid
        for child in self.children:
            a = child.listAllElements()
            res.update(a)
        result['attributes'] = self.attrib
        result['anyAttribute'] = self.anyAttribute
        result['anyElement'] = self.anyElement
        result['userAttributes'] = []
        res[self.uuid] = result
        return res

    def generateJSONTemplate(self):
        content = OrderedDict()
        content['-min'] = self.karMin
        content['-max'] = self.karMax
        attr = []
        for a in self.attrib:
            to = a['templateOptions']
            b = OrderedDict()
            b['-name'] = to['label']
            b['-req'] = int(to['required'])
            b['#content'] = []
            attr.append(b)
        content['-attr'] = attr
        for child in self.children:
            name, con = child.generateJSONTemplate()
            if name in content:
                if isinstance(content[name], list):
                    content[name].append(con)
                else:
                    c = content[name]
                    content[name] = []
                    content[name].append(c)
                    content[name].append(con)
            else:
                content[name] = con
        return self.name, content

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

def analyze2(element, tree, usedTypes=[], minC=0, maxC=1):
    # print element.local-name()
    global complexTypes
    global attributeGroups
    tag = printTag(element.tag)
    if tag == 'element':
        meta = OrderedDict()
        if element.get('minOccurs') is None or int(element.get('minOccurs')) < 0:
            meta['minOccurs'] = 0
        else:
            meta['minOccurs'] = int(element.get('minOccurs'))
        if element.get('maxOccurs') is None:
            meta['maxOccurs'] = 1
        elif element.get('maxOccurs') == 'unbounded':
            meta['maxOccurs'] = -1
        else:
            meta['maxOccurs'] = int(element.get('maxOccurs'))

        if element.get('type') is None:
            t = xmlElement(element.get('name'), tree.path)
            t.karMin = minC
            t.karMax = maxC
            path = t.path
            t.path += '0/'
            if 'minOccurs' in meta:
                t.karMin = meta['minOccurs']
            if 'maxOccurs' in meta:
                t.karMax = meta['maxOccurs']
            t.meta = meta
            tree.addChild(t)
            for child in element:
                analyze2(child, t, usedTypes)
            if t.karMin > 1:
                for i in range(1, t.karMin):
                    ti = xmlElement(t.name, tree.path)
                    ti.path = path + str(i) + '/'
                    ti.meta = meta
                    tree.addChild(ti)
                    for child in element:
                        analyze2(child, ti, usedTypes)
        elif getPrefix(element.get('type')) == 'xsd':
            t = xmlElement(element.get('name'), tree.path)
            t.karMin = minC
            t.karMax = maxC
            path = t.path
            t.path += '0/'
            if 'minOccurs' in meta:
                t.karMin = meta['minOccurs']
            if 'maxOccurs' in meta:
                t.karMax = meta['maxOccurs']
            t.meta = meta
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
            if t.karMin > 1:
                for i in range(1, t.karMin):
                    ti = xmlElement(t.name, tree.path)
                    ti.path = path + str(i) + '/'
                    ti.meta = meta
                    a = copy.deepcopy(t.attrib)
                    ti.attrib = a
                    tree.addChild(ti)
        else:
            t = xmlElement(element.get('name'), tree.path)
            t.karMin = minC
            t.karMax = maxC
            path = t.path
            t.path += '0/'
            if 'minOccurs' in meta:
                t.karMin = meta['minOccurs']
            if 'maxOccurs' in meta:
                t.karMax = meta['maxOccurs']
            t.meta = meta
            tree.addChild(t)
            key = element.get('type')
            if key not in usedTypes:
                if key in complexTypes:
                    usedTypes.append(key)
                    for child in complexTypes[key]:
                        analyze2(child, t, usedTypes)
                else:
                    print "type unknown: " + element.get('type')
            if t.karMin > 1:
                for i in range(1, t.karMin):
                    ti = xmlElement(t.name, tree.path)
                    ti.path = path + str(i) + '/'
                    ti.meta = meta
                    a = copy.deepcopy(t.attrib)
                    ti.attrib = a
                    tree.addChild(ti)
                    if key in complexTypes:
                        for child in complexTypes[key]:
                            analyze2(child, ti, usedTypes)
                    else:
                        print "type unknown: " + element.get('type')
    elif tag == 'complexType':
        for child in element:
            analyze2(child, tree, usedTypes)
    elif tag == 'complexContent':
        for child in element:
            analyze2(child, tree, usedTypes)
    elif tag == 'extension':
        if element.get('base'):
            t = element.get('base')
            # print t
            if t not in usedTypes:
                if t in complexTypes:
                    usedTypes.append(t)
                    for child in complexTypes[t]:
                        analyze2(child, tree, usedTypes, minC, maxC)
    elif tag == 'sequence':
        for child in element:
            analyze2(child, tree, usedTypes)
    elif tag == 'choice':
        for child in element:
            analyze2(child, tree, usedTypes)
    elif tag == 'attribute':
        att = parseAttribute(element)
        if att != None:
            tree.attrib.append(att)
    elif tag == 'attributeGroup':
        if element.get('ref'):
            ref = element.get('ref')
            if ref in attributeGroups:
                for child in attributeGroups[ref]:
                    analyze2(child, tree, usedTypes)
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
    elif tag == 'any':
        tree.anyElement = True
    elif tag == 'all':
        minC = 1
        if element.get('minOccurs') is not None:
            minC = int(element.get('minOccurs'))
            if minC != 0 or minC != 1:
                minC = 1
        maxC = 1
        for child in element:
            analyze2(child, tree, usedTypes, minC=minC, maxC=maxC)
    else:
        print 'other: ' + tag

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

## TODO list:

# 1. text content of elements

# 2. required or not (All other information)

# 3. save the model to a jsonTemplate (might prioritate this)
def generate():
    global complexTypes
    global attributeGroups
    # pars = etree.parse("CSPackageMETS.xsd")
    pars = etree.parse("esscore/template/templateGenerator/CSPackageMETS.xsd")
    # rootEl = create2(pars.getroot())
    schema = '{http://www.w3.org/2001/XMLSchema}'

    root = pars.getroot()

    # print root.tag
    # analyze(root)

    # def changeName(tree):
    #     tree.name = 'test'

    for child in root.iterfind(schema + 'complexType'):
        if child.get('name'):
            complexTypes[child.get('name')] = child

    for child in root.iterfind(schema + 'attributeGroup'):
        if child.get('name'):
            attributeGroups[child.get('name')] = child

    # print complexTypes
    # t = None

    # xmlFile = os.open('test.txt',os.O_RDWR|os.O_CREAT)

    # el = xmlElement('not test')

    for child in root.iterfind(schema + 'element'):
        tag = printTag(child.tag)
        if tag != 'complexType' and tag != 'attributeGroup':
            tree = xmlElement(child.get('name'))
            tree.path += '0/'
            for ch in child:
                analyze2(ch, tree, [])
            if tree is not None:
                # with open('test.txt', 'wb') as outfile:
                # print tree.generateJSON();
                struc = tree.generateStruct()
                el = tree.listAllElements()
                # j = json.dumps(tree.generateJSON())
                # tree.delete()
                return json.dumps(struc), json.dumps(el)
    # pars = None
    # root = None
    # tree = None
    # complexTypes = OrderedDict()
    # attributeGroups = OrderedDict()

generate()
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
