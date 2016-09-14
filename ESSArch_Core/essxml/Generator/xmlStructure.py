import os


debug = False
eol_ = '\n'

def dlog(string):
    if debug:
        print string


def pretty_print(fd, level, pretty):
    """
    Print some tabs to give the xml output a better structure
    """
    if pretty:
        for idx in range(level):
            os.write(fd, '    ')
def pretty_print_string(level, pretty):
    """
    Print some tabs to give the xml output a better structure
    """
    if pretty:
        for idx in range(level):
            print '   ',

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
            print ' ' + self.attrName + '="' + self.value + '"',

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
            pretty_print(fd, level, pretty)
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
                    #pretty_print(fd, level + 1, pretty)
                    os.write(fd, self.value)
                    pretty_print(fd, level, False)
                else:
                    pretty_print(fd, level, True)

                os.write(fd, '</' + self.completeTagName + '>' + eol_)
                self.printed = 2
            else:
                self.printed = 1
                return True
        else:
            os.write(fd, '/>' + eol_)
            self.printed = 2

    def XMLToString(self, level=0, pretty=True):
        """
        Print out the complete element.
        """
        if self.printed == 2:
            return False
        if self.printed == 0:
            pretty_print_string(level, pretty)
            print '<' + self.completeTagName,
            for a in self.attributes:
                a.XMLToString()
        if self.children or self.value is not '' or self.containsFiles:
            if self.printed == 0:
                print '>' + eol_,
            if not self.containsFiles or self.printed == 1:
                for child in self.children:
                    if child.XMLToString(level + 1, pretty):
                        self.printed = 1
                        return True
                if self.value is not '':
                    pretty_print_string(level + 1, pretty)
                    print self.value + eol_,
                pretty_print_string(level, pretty)
                print '</' + self.completeTagName + '>' + eol_,
                self.printed = 2
            else:
                self.printed = 1
                return True
        else:
            print '/>' + eol_,
            self.printed = 2

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
