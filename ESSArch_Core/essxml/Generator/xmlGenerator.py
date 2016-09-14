import os, re
import hashlib
import uuid
import json
import copy
from collections import OrderedDict
import fileinput
import mimetypes
from django.conf import settings

from xmlStructure import xmlElement, xmlAttribute, fileInfo, fileObject, dlog

sortedFiles = []
foundFiles = 0

def calculateChecksum(filename):
    """
    calculate the checksum for the selected file, one chunk at a time
    """
    fd = os.open(filename, os.O_RDONLY)
    hashSHA = hashlib.sha256()
    while True:
        data = os.read(fd, 65536)
        if data:
            hashSHA.update(data)
        else:
            break
    os.close(fd)
    return hashSHA.hexdigest()

def parseFiles(filename='/SIP/huge', level=3, resultFile=[]):
    """
    walk through the choosen folder and parse all the files to their own temporary location
    """
    fileInfo = {}
    mimetypes.init(files=[os.path.join(settings.BASE_DIR), 'demo/mime.types'])

    for dirname, dirnames, filenames in os.walk(filename):
        # print dirname
        for file in filenames:
            found = False
            for key, value in resultFile.iteritems():
                if dirname+'/'+file == key:
                    found = True

            if found == False:
            # populate dictionary



                fileInfo['FName'] = os.path.relpath(dirname+'/'+file, filename)
                fileInfo['FChecksum'] = calculateChecksum(dirname+'/'+file)
                fileInfo['FID'] = uuid.uuid4().__str__()
                if '.'+file.split('.')[-1] in mimetypes.types_map:
                    fileInfo['FMimetype'] = mimetypes.types_map['.'+file.split('.')[-1]]
                else:
                    fileInfo['FMimetype'] = 'unknown'
                fileInfo['FCreated'] = '2016-02-21T11:18:44+01:00'
                fileInfo['FFormatName'] = 'MS word'
                fileInfo['FSize'] = str(os.path.getsize(dirname+'/'+file))
                fileInfo['FUse'] = 'DataFile'
                fileInfo['FChecksumType'] = 'SHA-256'
                fileInfo['FLoctype'] = 'URL'
                fileInfo['FLinkType'] = 'simple'
                fileInfo['FChecksumLib'] = 'hashlib'
                fileInfo['FLocationType'] = 'URI'
                fileInfo['FIDType'] = 'UUID'
                # write to file

                for fi in sortedFiles:
                    # print 'fi: %s (xmlFileName: %s, template: %s, namespace: %s, fid: %s, files: %s' % (
                    #                                                                                    repr(fi),
                    #                                                                                    fi.xmlFileName, 
                    #                                                                                    fi.template, 
                    #                                                                                    fi.namespace, 
                    #                                                                                    fi.fid, 
                    #                                                                                    fi.files)
                    for fil in fi.files:
                        if not fil.arguments:
                            for key, value in fil.element.iteritems():
                                # print 'create 1 key: %s, value: %s, fileInfo: %s' % (key, value, fileInfo)
                                t = createXMLStructure(key, value, fileInfo, namespace=fi.namespace)
                                t.printXML(fil.fid,fil.level)
                        else:
                            found = True
                            for key, value in fil.arguments.iteritems():
                                if re.search(value, fileInfo[key]) is None:
                                    found = False
                                    break
                            if found:
                                for key, value in fil.element.iteritems():
                                    # print 'create 2 key: %s, value: %s, fileInfo: %s' % (key, value, fileInfo)
                                    t = createXMLStructure(key, value, fileInfo, namespace=fi.namespace)
                                    t.printXML(fil.fid,fil.level)

def getValue(key, info):
    """
    remove excess of whitespaces and check if the key exists in the dictionary
    """
    if key is not None:
        text = key.rstrip()
        if text != '':
            # print tree.text.replace('\n', '').replace(' ','')
            if text in info:
                return info[text]
    return None

def parseChild(name, content, info, namespace, t, fob, level=0):
    """
    Parse a child to get the correct values even if the values are in an array
    """
    if '-arr' not in content:
        c = createXMLStructure(name, content, info, fob, namespace, level+1)
        if c is not None:
            t.addChild(c)
    else:
        occurrences = 1
        if '-max' in content:
            occurrences = content['-max']
            if occurrences == -1:
                occurrences = 10000000000 # unlikely to surpass this
        #parse array string and pass info
        arguments = content['-arr']
        testArgs = arguments['arguments']
        dictionaries = copy.deepcopy(info[arguments['arrayName']])
        for used in xrange(0, occurrences):
            dic = findMatchingSubDict(dictionaries, testArgs)
            if dic is not None:
                #done, found matching entries
                c = createXMLStructure(name, content, dic, fob, namespace, level+1)
                if c is not None:
                    t.addChild(c)
                    dictionaries.remove(dic)
                else:
                    break
            else:
                break


def createXMLStructure(name, content, info, fob=None, namespace='', level=1):
    """
    The main XML element creator where the json structure is broken down and converted into a xml.
    """
    global foundFiles
    t = xmlElement(name, namespace)
    # loop through all attribute and children
    if '-containsFiles' in content and fob is not None:
        t.containsFiles = True
        c = content['-containsFiles']
        arg = None
        if isinstance(c, OrderedDict):
            con = {}
            for key, value in c.iteritems():
                if key[:1] != '-' and key[:1] != '#':
                    con[key] = value
            if '-sortby' in c:
                arg = c['-sortby']
            f = fileInfo(con, "tmp" + str(foundFiles)+".txt", arg)
            f.fid = os.open(f.filename,os.O_RDWR|os.O_CREAT)
            f.level = level
            fob.files.append(f)
            foundFiles += 1

        elif isinstance(c, list):
            for co in c:
                con = {}
                for key, value in co.iteritems():
                    if key[:1] != '-' and key[:1] != '#':
                        con[key] = value
                if '-sortby' in co:
                    arg = co['-sortby']
                f = fileInfo(con, "tmp" + str(foundFiles)+".txt", arg)
                f.fid = os.open(f.filename,os.O_RDWR|os.O_CREAT)
                f.level = level
                fob.files.append(f)
                foundFiles += 1
    for key, value in content.iteritems():
        if key == '#content':
            for c in value:
                if 'text' in c:
                    t.value += c['text']
                elif 'var' in c:
                    text = getValue(c['var'], info)
                    if text is not None:
                        t.value += text
        elif key == '-attr':
            #parse attrib children
            for attrib in value:
                attribute = parseAttribute(attrib, info)
                if attribute is None:
                    if '-req' in attrib:
                        if attrib['-req'] == 1:
                            print "ERROR: missing required value for element: " + name + " and attribute: " + attrib['-name']
                        else:
                            dlog("INFO: missing optional value for: " + attrib['-name'])
                    else:
                        dlog("INFO: missing optional value for: " + attrib['-name'])
                else:
                    t.addAttribute(attribute)
        elif key == '-namespace':
            t.setNamespace(value)
            namespace = value
        elif key[:1] != '-':
            #child
            if isinstance(value, OrderedDict) or isinstance(value, dict):
                parseChild(key, value, info, namespace, t, fob, level)
            elif isinstance(value, list):
                for l in value:
                    parseChild(key, l, info, namespace, t, fob, level)

    if t.isEmpty():
        if  '-allowEmpty' in content:
            if content['-allowEmpty'] != 1:
                return None
            else:
                return t
        else:
            return None
    else:
        return t

def findMatchingSubDict(dictionaries, arguments):
    """
    test if all the arguments are present and correct in the selected dictionary
    """
    for dic in dictionaries:
        # compare agent dicts
        found = True
        for key, value in arguments.iteritems():
            if key in dic:
                if dic[key] != value:
                    found = False
            else:
                found = False
        if found:
            return dic
    return None

def parseAttribute(content, info):
    """
    parse the content of an attribute and return it
    """
    text = ''
    name = content['-name']
    for c in content['#content']:
        if 'text' in c:
            text += c['text']
        elif 'var' in c:
            t = getValue(c['var'], info)
            if t is not None:
                text += t
    if text is not '':
        return xmlAttribute(name, text)
    else:
        return None

def createXML(info, filesToCreate, folderToParse):
    """
    The task method for executing the xmlGenerator and completing the xml files
    This is also the TASK to be run in the background.
    """

    global sortedFiles
    global foundFiles

    sortedFiles = []
    foundFiles = 0

    for key, value in filesToCreate.iteritems():
        json_data=open(value).read()
        try:
            data = json.loads(json_data, object_pairs_hook=OrderedDict)
        except ValueError as err:
            print err # implement logger
            return  False
        name, rootE = data.items()[0] # root element
        xmlFile = os.open(key,os.O_RDWR|os.O_CREAT)
        os.write(xmlFile, '<?xml version="1.0" encoding="UTF-8"?>\n')
        namespace = rootE.get('-namespace', None)
        fob = fileObject(key, value, namespace, xmlFile)
        sortedFiles.append(fob)
        rootEl = createXMLStructure(name, rootE, info, fob)
        rootEl.printXML(xmlFile)
        fob.rootElement = rootEl
        #print 'namespace: %s' % rootE['-namespace']

    parseFiles(folderToParse, resultFile=filesToCreate)

    # add the tmp files to the bottom of the appropriate file and write out the next section of xml until it's done
    for fob in sortedFiles:
        for fin in fob.files:
            f = os.open(fin.filename, os.O_RDONLY)
            while True:
                data = os.read(f, 65536)
                if data:
                    os.write(fob.fid, data)
                else:
                    break
            # print more XML
            fob.rootElement.printXML(fob.fid)
            os.close(f)
            os.remove(fin.filename)

def appendXML(inputData):
    """
    Searches throught the file for the expected tag and appends the new element before the end (appending it to the end)
    """
    for line in fileinput.FileInput(inputData['path'],inplace=1):
        if "</"+inputData['elementToAppendTo']+">" in line:
            name, rootE = inputData['template'].items()[0]
            rootEl = createXMLStructure(name, rootE, inputData['data'])
            level = (len(line) - len(line.lstrip(' ')))/4
            rootEl.XMLToString(level+1)
        print line,

#############################
# example of input for appendXML

inputD = {
    "path": "/SIP/sip2.txt",
    "elementToAppendTo": "mets:fileGrp",
    "template": {
        "event": {
            "-min": 1,
            "-max": 1,
            "-allowEmpty": 1,
            "-namespace": "premis",
            "-attr": [{
                "-name": "xmlID",
                "-req": 1,
                "#content": [{"var": "xmlID"}]
            }],
            "eventIdentifierType": {
                "-min": 1,
                "-max": 1,
                "#content": [{"var":"eventIdentifierType"}]
            },
            "eventIdentifierValue": {
                "-min": 1,
                "-max": 1,
                "-allowEmpty": 1,
                "#content": [{"var": "eventIdentifierValue"}]
            }
        }
    },
    "data": {
        "xmlID": "some id",
        "eventIdentifierType": "some event type",
        "eventIdentifierValue": "some event value thing"
    }

}

# appendXML(inputD)

#############################
# Example of info, filesToCreate, folderToParse:

info = {
        "xmlns:mets": "http://www.loc.gov/METS/",
                "xmlns:ext": "ExtensionMETS",
                "xmlns:xlink": "http://www.w3.org/1999/xlink",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://www.loc.gov/METS/ http://xml.ra.se/e-arkiv/METS/CSPackageMETS.xsd "
                "ExtensionMETS http://xml.ra.se/e-arkiv/METS/CSPackageExtensionMETS.xsd",
                "xsi:schemaLocationPremis": "http://www.loc.gov/premis/v3 https://www.loc.gov/standards/premis/premis.xsd",
                "PROFILE": "http://xml.ra.se/e-arkiv/METS/CommonSpecificationSwedenPackageProfile.xmll",
                "LABEL": "Test of SIP 1",
                "TYPE": "Personnel",
                "OBJID": "UUID:9bc10faa-3fff-4a8f-bf9a-638841061065",
                "ext:CONTENTTYPESPECIFICATION": "FGS Personal, version 1",
                "CREATEDATE": "2016-06-08T10:44:00+02:00",
                "RECORDSTATUS": "NEW",
                "ext:OAISTYPE": "SIP",
                "agentName": "name",
                "agentNote": "note",
                "REFERENCECODE": "SE/RA/123456/24/F",
                "SUBMISSIONAGREEMENT": "RA 13-2011/5329, 2012-04-12",
                "MetsIdentifier": "sip.xml",
                "filename":"sip.txt",
                "SMLabel":"Profilestructmap",
                "amdLink":"IDce745fec-cfdd-4d14-bece-d49e867a2487",
                "digiprovLink":"IDa32a20cb-5ff8-4d36-8202-f96519154de2",
                "LOCTYPE":"URL",
                "MDTYPE":"PREMIS",
                "xlink:href":"file:///metadata/premis.xml",
                "xlink:type":"simple",
                "ID":"ID31e51159-9280-44d1-b26c-014077f8eeb5",
                "agents":[{
                        "ROLE":"ARCHIVIST",
                        "TYPE":"ORGANIZATION",
                        "name":"Arkivbildar namn",
                        "note":"VAT:SE201345098701"
                    },{
                        "ROLE":"ARCHIVIST",
                        "TYPE":"OTHER",
                        "OTHERTYPE":"SOFTWARE",
                        "name":"By hand Systems",
                        "note":"1.0.0"
                    },{
                        "ROLE":"ARCHIVIST",
                        "TYPE":"OTHER",
                        "OTHERTYPE":"SOFTWARE",
                        "name":"Other By hand Systems",
                        "note":"1.2.0"
                    },{
                        "ROLE":"CREATOR",
                        "TYPE":"ORGANIZATION",
                        "name":"Arkivbildar namn",
                        "note":"HSA:SE2098109810-AF87"
                    },{
                        "ROLE":"OTHER",
                        "OTHERROLE":"PRODUCER",
                        "TYPE":"ORGANIZATION",
                        "name":"Sydarkivera",
                        "note":"HSA:SE2098109810-AF87"
                    },{
                        "ROLE":"OTHER",
                        "OTHERROLE":"SUBMITTER",
                        "TYPE":"ORGANIZATION",
                        "name":"Arkivbildare",
                        "note":"HSA:SE2098109810-AF87"
                    },{
                        "ROLE":"IPOWNER",
                        "TYPE":"ORGANIZATION",
                        "name":"Informations agare",
                        "note":"HSA:SE2098109810-AF87"
                    },{
                        "ROLE":"EDITOR",
                        "TYPE":"ORGANIZATION",
                        "name":"Axenu",
                        "note":"VAT:SE9512114233"
                    },{
                        "ROLE":"CREATOR",
                        "TYPE":"INDIVIDUAL",
                        "name":"Simon Nilsson",
                        "note":"0706758942, simonseregon@gmail.com"
                    }],
}

filesToCreate = {
    "sip.txt":"templates/JSONTemplate.json",
    # "premis.txt":"templates/JSONPremisTemplate.json",
    # "sip2.txt":"templates/JSONTemplate.json"
}

folderToParse = "/SIP/huge/csv/000"

# createXML(info, filesToCreate, folderToParse)


## TODO

# 1. enable -attr tag to contain dict only

# Idea: format varaibles to be like

#1. agents[0].name
#2. agents{ROLE=CREATOR;TYPE=INDIVIDUAL}.name
#3. dict1.dict2.arr[2].dict3.name
