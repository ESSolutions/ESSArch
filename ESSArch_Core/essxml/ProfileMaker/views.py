
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, loader, RequestContext
from models import templatePackage, finishedTemplate
#file upload
# import the logging library and get an instance of a logger
import logging
logger = logging.getLogger('code.exceptions')

# import re
import copy
import json
import uuid
from collections import OrderedDict

from django.views.generic import View
from django.http import JsonResponse
from esscore.template.templateGenerator.testXSDToJSON import generate


def constructContent(text):
    res = []
    i = text.find('{{')
    if i > 0:
        d = {}
        d['text'] = text[0:i]
        res.append(d)
        r = constructContent(text[i:])
        for j in range(len(r)):
            res.append(r[j])
    elif i == -1:
        if len(text) > 0:
            d = {}
            d['text'] = text
            res.append(d)
    else:
        d = {};
        v = text[i+2:]
        i = v.find('}}')
        d['var'] = v[0:i]
        res.append(d);
        r = constructContent(v[i+2:])
        for j in range(len(r)):
            res.append(r[j])
    return res

def cloneElement(el, allElements, found=0, begin=''):
    newElement = OrderedDict()
    newElement['name'] = el['name']
    newElement['key'] = uuid.uuid4().__str__()
    newElement['meta'] = copy.deepcopy(el['meta'])
    newElement['path'] = el['path']
    newElement['templateOnly'] = False
    path = newElement['path']
    if found != 0:
        newElement['path'] = path[0:path[:-1].rfind('/')] + '/'+str(found)+'/'
    elif begin != '':
        newElement['path'] = begin + path[path[:path[:-1].rfind('/')].rfind('/')+1:]
    children = []
    for child in el['children']:
        children.append(cloneElement(child, allElements, begin=newElement['path']))
    newElement['children'] = children
    allElements[newElement['key']] = copy.deepcopy(allElements[str(el['key'])])

    return newElement

def generateElement(structure, elements):
    if 'templateOnly' not in structure or structure['templateOnly'] == False:
        el = OrderedDict()
        forms = []
        data = {}
        meta = structure['meta']
        if 'minOccurs' in meta:
            el['-min'] = meta['minOccurs']
        if 'maxOccurs' in meta:
            el['-max'] = meta['maxOccurs']
        if 'allowEmpty' in meta: # TODO save allowEmpty
            el['-allowEmpty'] = meta['allowEmpty']
        # TODO namespace
        a = elements[structure['key']]
        attributes = a['attributes'] + a['userAttributes']
        attributeList = []
        for attrib in attributes:
            # return attrib
            if attrib['key'] == '#content':
                if 'defaultValue' in attrib:
                    el['#content'] = constructContent(attrib['defaultValue'])
                    for part in el['#content']:
                        if 'var' in part:
                            # add form entry for element
                            # ?? add information of parent? example: note for agent with role=Archivist&&typ=organization (probably not needed)
                            # adding text if there occures at least one variable.
                            field = {}
                            field['key'] = part['var'] # check for doubles
                            field['type'] = 'input'
                            to = {}
                            to['type'] = 'text'
                            to['label'] = part['var']
                            field['templateOptions'] = to
                            forms.append(field)
                            data[part['var']] = 's'
                else:
                    el['#content'] = [] # TODO warning, should not be added if it can't contain any value
            else:
                att = OrderedDict()
                att['-name'] = attrib['key']
                if 'required' in attrib['templateOptions']:
                    if attrib['templateOptions']['required']:
                        att['-req'] = 1
                    else:
                        att['-req'] = 0
                else:
                    att['-req'] = 0
                if 'defaultValue' in attrib:
                    att['#content'] = constructContent(attrib['defaultValue'])
                    for part in att['#content']:
                        if 'var' in part:
                            # add form entry for element
                            # ?? add information of parent? example: note for agent with role=Archivist&&typ=organization (probably not needed)
                            # adding text if there occures at least one variable.
                            field = {}
                            field['key'] = part['var'] # check for doubles
                            field['type'] = 'input'
                            to = {}
                            to['type'] = 'text'
                            to['label'] = part['var']
                            field['templateOptions'] = to
                            forms.append(field)
                            data[part['var']] = 's'
                else:
                    att['#content'] = [] # TODO warning, should not be added if it can't contain any value
                attributeList.append(att)
        el['-attr'] = attributeList
        for child in structure['children']:
            e, f, d = generateElement(child, elements)
            if e is not None:
                if child['name'] in el:
                    # cerate array
                    if isinstance(el[child['name']], list):
                        el[child['name']].append(e)
                    else:
                        temp = el[child['name']]
                        el[child['name']] = []
                        el[child['name']].append(temp)
                        el[child['name']].append(e)
                else:
                    el[child['name']] = e
                for field in f:
                    forms.append(field)
                data.update(d)
            # for field in f:
            #     forms.append(field) # data
        return (el, forms, data)
    else:
        return (None, None, None)

def deleteElement(structure, elements):
    del elements[structure['key']]
    for child in structure['children']:
        deleteElement(child, elements)


def index(request):

    return HttpResponse("Hello, world. You're at the polls index.")

#debugg only NEEDS TO BE REMOVED IN FUTURE
def resetData(request):
    existingElements, treeData, allElements = generate();
    t = templatePackage(existingElements=existingElements, allElements=allElements, treeData=treeData, name='test')
    t.save()
    return JsonResponse(allElements, safe=False)

def getStruct(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    return JsonResponse(obj.existingElements, safe=False)

def getElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    # j = json.loads(obj.existingElements, object_pairs_hook=OrderedDict)
    return JsonResponse(obj.allElements, safe=False)

def deleteChild(request, name, uuid):
    # TODO delete children
    obj = get_object_or_404(templatePackage, pk=name)
    existingElements = obj.existingElements
    oldElement = existingElements[uuid]

    parent = existingElements[oldElement['parent']]
    childName = oldElement['name']
    minCount = oldElement['min']
    del existingElements[uuid]

    for childDict in parent['children']:
        count = 0
        if childDict['type'] == 'sequence':
            for child in childDict['elements']:
                if 'uuid' in child:
                    if child['name'] == childName:
                        count += 1
            if count > minCount:
                for child in childDict['elements']:
                    if 'uuid' in child:
                        if child['uuid'] == uuid:
                            del child['uuid']
            else:
                for child in childDict['elements']:
                    if 'uuid' in child:
                        if child['uuid'] == uuid:
                            childDict['elements'].remove(child)
        else:
            for child in childDict['elements']:
                if 'uuid' in child:
                    if child['uuid'] == uuid:
                        childDict['elements'].remove(child)
    deleteChildren(existingElements, oldElement)
    obj.existingElements = existingElements
    obj.save()
    return JsonResponse(existingElements, safe=False)

def deleteChildren(existingElements ,element):
    for childDict in element['children']:
        for child in childDict['elements']:
            if 'uuid' in child:
                deleteChildren(existingElements, existingElements[child['uuid']])
                del existingElements[child['uuid']]

def addChild(request, name, newElementName, elementUuid):
    obj = get_object_or_404(templatePackage, pk=name)
    existingElements = obj.existingElements
    templates = obj.allElements
    newUuid = uuid.uuid4().__str__()
    newElement = copy.deepcopy(templates[newElementName])
    newElement['parent'] = elementUuid
    existingElements[newUuid] = newElement

    found = False
    foundIndex = -1
    index = 0
    for childDict in existingElements[elementUuid]['children']:
        if childDict['type'] == 'sequence':
            for child in childDict['elements']:
                if child['name'] == newElementName:
                    found = True
                    foundIndex = index
                    if 'uuid' not in child:
                        foundIndex -= 1
                index += 1
            if found:
                r = {}
                r['name'] = newElementName
                r['uuid'] = newUuid
                childDict['elements'].insert(foundIndex+1 ,r)
            else:
                return HttpResponse('no child of same type found ERROR')
        else:
            for child in childDict['elements']:
                if child['name'] == newElementName:
                    if 'uuid' in child:
                        return HttpResponse('ERROR: Choise already has one element')
                    else:
                        found = True
                        foundIndex = index
                index += 1
            if found:
                temp = childDict['elements'][foundIndex]
                temp['uuid'] = newUuid
                childDict['elements'] = []
                childDict['elements'].append(temp)
    obj.existingElements = existingElements
    obj.save()
    return JsonResponse(existingElements, safe=False)

def generateTreeStructure(elements, existingElements, addChildren=True):
    res = {}
    res['name'] = elements['name']
    res['key'] = elements['uuid']
    res['templateOnly'] = False
    for child in elements['children']:
        if child['type'] == 'element':
            pass
        else:
            pass


def addUserChild(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    j = json.loads(obj.structure, object_pairs_hook=OrderedDict)
    allElements = json.loads(obj.elements, object_pairs_hook=OrderedDict)
    res = json.loads(request.body)
    t = j;
    p = res['path'].split('/')
    p = p[:-1]
    # name = p[-1:][0]
    # p = p[:-1]
    for i in range(0, len(p), 2):
        found = 0
        for dic in t['children']:
            if dic['name'] == p[i]:
                if found == int(p[i+1]):
                    t = dic
                    break
                else:
                    found += 1
    found = 0
    i = 0
    for dic in t['children']:
        if dic['name'] == res['name']:
            found += 1
        else:
            if found > 0:
                break
        i += 1
    if found > 0:
        res['path'] += res['name'] + '/' + str(found) + '/'
        res['key'] = uuid.uuid4().__str__()
        t['children'].insert(i, res)
    else:
        res['path'] += res['name'] + '/0/'
        res['key'] = uuid.uuid4().__str__()
        t['children'].append(res)
    att = {};
    att['attributes'] = [];
    att['anyAttribute'] = True
    att['anyElement'] = True
    att['userAttributes'] = [];
    att['userCreated'] = True
    allElements[res['key']] = att;
    obj.structure = json.dumps(j)
    obj.elements = json.dumps(allElements)
    obj.save()
    return JsonResponse(obj.structure, safe=False)

def addAttribute(request, name, uuid):
    obj = get_object_or_404(templatePackage, pk=name)
    obj.existingElements[uuid]['userForm'].append(json.loads(request.body))
    obj.save()
    return JsonResponse(obj.existingElements[uuid]['userForm'], safe=False)

def generateTemplate(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    structure = json.loads(obj.structure, object_pairs_hook=OrderedDict)
    elements = json.loads(obj.elements, object_pairs_hook=OrderedDict)
    jsonString = OrderedDict()
    jsonString[structure['name']], forms, data = generateElement(structure, elements)

    t = finishedTemplate(name='test', template=jsonString, form=forms, data=data)
    t.save()
    # return JsonResponse(el, safe=False)
    # return HttpResponse(test)
    return JsonResponse(data, safe=False)

def getForm(request, name):
    obj = get_object_or_404(finishedTemplate, pk=name)
    return JsonResponse(obj.form, safe=False)

def getData(request, name):
    obj = get_object_or_404(finishedTemplate, pk=name)
    return JsonResponse(obj.data, safe=False)

def saveForm(request, name):

    res = json.loads(request.body)
    uuid = res['uuid']
    del res['uuid']

    obj = get_object_or_404(templatePackage, pk=name)
    j = obj.existingElements
    obj.existingElements[uuid]['formData'] = res
    obj.save()
    return JsonResponse(res, safe=False)

class demo(View):
    template_name = 'templateMaker/demo.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        res = json.loads(request.body)

        obj = get_object_or_404(finishedTemplate, pk='test') # TODO not hardcoded
        obj.data = res
        obj.save()

        return JsonResponse(request.body, safe=False)

        # return redirect('/template/demo/')

class create(View):
    template_name = 'templateMaker/create.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # v = add.delay(4,4)
        # logger.log(v.get())
        context = {}
        # context['label'] = 'Prepare new information packages'

        # Get current site_profile and zone
        # site_profile, zone = lat.getSiteZone()

        # Present only prepared IPs
        # ip = InformationPackage.objects.filter(state='Prepared')

        # initialvalues = {}
        # initialvalues['destinationroot'] = lat.getLogFilePath()
        # if site_profile == "SE":
            # form = PrepareFormSE(initial=initialvalues) # Form with defaults
        # if site_profile == "NO":
            # form = PrepareFormNO(initial=initialvalues) # Form with defaults

        # context['form'] = form
        # context['zone'] = zone
        # context['informationpackages'] = ip
        return render(request, self.template_name, context)

class edit(View):
    template_name = 'templateMaker/edit.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # v = add.delay(4,4)
        # logger.log(v.get())
        context = {}
        context['label'] = 'Edit template'

        # Get current site_profile and zone
        # site_profile, zone = lat.getSiteZone()

        # Present only prepared IPs
        # ip = InformationPackage.objects.filter(state='Prepared')

        # initialvalues = {}
        # initialvalues['destinationroot'] = lat.getLogFilePath()
        # if site_profile == "SE":
            # form = PrepareFormSE(initial=initialvalues) # Form with defaults
        # if site_profile == "NO":
            # form = PrepareFormNO(initial=initialvalues) # Form with defaults

        # context['form'] = form
        # context['zone'] = zone
        # context['informationpackages'] = ip
        return render(request, self.template_name, context)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):

        # 1. load elements
        # 2. find with correct uuid
        # 3. update
        # 4. save
        # return HttpResponse(json.dumps(request.POST))
        # return JsonResponse(request.body);
        # name = request.POST['schemaName']
        uuid = request.POST['uuid']
        del request.POST['uuid']

        obj = get_object_or_404(templatePackage, pk=name)
        j = json.loads(obj.existingElements, object_pairs_hook=OrderedDict)
        element = j[uuid]
        element['formData'] = request.POST
        # for key, value in request.POST.iteritems():
        #     if key.startswith('formly_'):
        #         # key has format formly_[form_id]_[type (input | select)]_[key]_[num] Wanted value is [key]
        #         end = key.rfind('_')
        #         k = key[0:end]
        #         start = k.rfind('_')
        #         k = k[start+1:]
        #         for attrib in oldData['attributes']:
        #             if attrib['key'] == k:
        #                 v = value
        #                 if value.startswith('string:'):
        #                     v = v[7:]
        #                 attrib['defaultValue'] = v
        #                 break

        obj.existingElements = json.dumps(j)
        obj.save()
        return redirect('/template/edit/')
