import os, uuid

TYPE_ELEMENT = 0
TYPE_CHOISE = 1
TYPE_TO = 2
TYPE_TO_CHOISE = 3

debug = False
eol_ = '\n'

def dlog(string):
    if debug:
        print string


def pretty_print(fd, level, pretty):
    """
    Print some tabs to give the xml output a better structure
    """

    os.write(fd, '    ' * level)

class xmlAttribute(object):
    '''
    A class to contain and handle each attribute of a XML element
    '''
    attrName = ''
    req = False
    value = ''

    def __init__(self, attrName, value=''):
        self.attrName = attrName
        self.value = value

    def printXML(self, fd):
        """
        Print out the attribute
        """
        if self.value is not '':
            os.write(fd, ' ' + self.attrName + '="' + self.value + '"')

    def XMLToString(self):
        """
        Print out the attribute
        """
        if self.value is not '':
            return self.attrName + '="' + self.value + '"'

class xmlElement(object):
    '''
    A class containing a complete XML element, a list of attributes and a list of children
    '''

    def __init__(self, tagName='', namespace=''):
        self.tagName = tagName
        self.children = []
        self.attributes = []
        self.value = ''
        self.karMin = 0
        self.karMax = -1
        self.uuid = str(uuid.uuid4())
        self.anyAttribute = False
        self.anyElement = False
        self.type = 0
        self.namespace = namespace
        self.completeTagName = ''
        self.containsFiles = False
        self.printed = 0
        if self.namespace != '':
            self.completeTagName += self.namespace + ':'
        self.completeTagName += str(self.tagName)

    def setNamespace(self, namespace):
        """
        Changes the namespace of the element and updates the combined string
        """
        self.namespace = namespace
        self.completeTagName = ''
        if self.namespace != '':
            self.completeTagName += self.namespace + ':'
        self.completeTagName += self.tagName

    def printXML(self, fd, level=0, pretty=True):
        """
        Print out the complete element.
        """
        if self.printed == 2:
            return False
        if self.printed == 0:
            if pretty:
                pretty_print(fd, level)

            os.write(fd, '<' + self.completeTagName)
            for a in self.attributes:
                a.printXML(fd)
        if self.children or self.value is not '' or self.containsFiles:
            if self.printed == 0:
                if self.value is not '':
                    os.write(fd, '>')
                else:
                    os.write(fd, '>' + eol_)
            if not self.containsFiles or self.printed == 1:
                for child in self.children:
                    if child.printXML(fd, level + 1, pretty):
                        self.printed = 1
                        return True
                if self.value is not '':
                    os.write(fd, self.value)
                else:
                    pretty_print(fd, level)

                os.write(fd, '</' + self.completeTagName + '>' + eol_)
                self.printed = 2
            else:
                self.printed = 1
                return True
        else:
            os.write(fd, '/>' + eol_)
            self.printed = 2

    def listAllElements(self, parent='none'):
        res = {}
        if self.type == TYPE_ELEMENT:
            element = {}
            element['name'] = self.tagName
            element['min'] = self.karMin
            element['max'] = self.karMax
            element['form'] = self.attributes
            element['userForm'] = []
            element['formData'] = {}
            element['userCreated'] = False
            element['anyAttribute'] = self.anyAttribute
            element['anyElement'] = self.anyElement
            element['containsFiles'] = False
            element['parent'] = parent
            element['children'] = [];
            element['namespace'] = self.namespace
            children = []
            for child in self.children:
                r, c, a = child.listAllElements(self.tagName)
                children = children + c
                element['form'] = element['form'] + a
                res.update(r)
            element['avaliableChildren'] = children
            res[self.tagName] = element
            el = {}
            el['type'] = 'element'
            el['name'] = self.tagName
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
            el['name'] = self.tagName
            return {}, [el], self.attributes
        elif self.type == TYPE_TO_CHOISE:
            return {}, self.children, self.attributes

    def calculateChildren(self):
        res = []
        for child in self.children:
            el = {}
            if child.type == TYPE_CHOISE:
                el['type'] = 'choise'
                el['elements'] = child.calculateChildren()
                res.append(el)
            elif child.type == TYPE_ELEMENT:
                el['name'] = child.tagName
                el['type'] = 'element'
                res.append(el)
            elif child.type == TYPE_TO:
                el['type'] = 'element'
                el['name'] = child.tagName
                res.append(el)
            elif child.type == TYPE_TO_CHOISE:
                res = res + child.children
        return res

    def isEmpty(self):
        """
        Simple helper function to check if the tag sould have any contents
        """
        if self.value != '' or self.children or self.containsFiles:
            return False
        else:
            return True

    def printDebug(self):
        """
        Method for debugging only, prints out the name of the element and all children
        """
        print self.tagName
        for child in self.children:
            child.printDebug()

    def addAttribute(self, attribute):
        """
        Add an attribute to the element
        """
        self.attributes.append(attribute)

    def addChild(self, el):
        """
        Add a child to the element and test if it should have the same namespace
        """
        if el.namespace == '':
            el.setNamespace(self.namespace)
        self.children.append(el)

    def delete(self):
        self.tagName = ''
        for child in self.children:
            child.delete()
        self.children = []
        self.attributes = []
        self.value = ''
        self.karMin = 0
        self.karMax = -1

class fileInfo():
    """
    A way to contain the temporary files which are created
    """
    def __init__(self, element, filename, arguments={}, level=0):
        self.element = element
        self.filename = filename
        self.arguments = arguments
        self.level = level

class fileObject():
    """
    A container class for all the files in the xml
    """
    def __init__(self, xmlFileName, template, namespace, fid):
        self.xmlFileName = xmlFileName
        self.template = template
        self.namespace = namespace
        self.fid = fid
        self.files = []
        self.rootElement = None
