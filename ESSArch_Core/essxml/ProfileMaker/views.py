
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
from forms import AddTemplateForm


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

def generateElement(elements, currentUuid, takenNames=[], containsFiles=False):
    element = elements[currentUuid]
    el = OrderedDict()
    forms = []
    data = {}
    el['-min'] = element['min']
    el['-max'] = element['max']
    # if 'allowEmpty' in meta: # TODO save allowEmpty
        # el['-allowEmpty'] = meta['allowEmpty']
    # TODO namespace
    # a = elements[structure['key']]
    attributes = element['form'] + element['userForm']
    attributeList = []
    for attrib in attributes:
        # return attrib
        if attrib['key'] == '#content':
            if attrib['key'] in element['formData']:
                el['#content'] = constructContent(element['formData'][attrib['key']])
                if not containsFiles:
                    for part in el['#content']:
                        if 'var' in part:
                            # add form entry for element
                            # ?? add information of parent? example: note for agent with role=Archivist&&typ=organization (probably not needed)
                            # adding text if there occures at least one variable.
                            field = {}
                            key = part['var'] # check for doubles
                            if key in takenNames:
                                index = 0
                                while (key + str(index)) in takenNames:
                                    index += 1
                                field['key'] = (key + str(index))
                                takenNames.append((key + str(index)))
                            else:
                                field['key'] = key
                                takenNames.append(key)
                            field['type'] = 'input'
                            to = {}
                            to['type'] = 'text'
                            to['label'] = part['var']
                            field['templateOptions'] = to
                            forms.append(field)
                            data[field['key']] = ''
            else:
                el['#content'] = [] # TODO warning, should not be added if it can't contain any value
        else:
            att = OrderedDict()
            att['-name'] = attrib['key']
            att['-req'] = 0
            if 'required' in attrib['templateOptions']:
                if attrib['templateOptions']['required']:
                    att['-req'] = 1
            if attrib['key'] in element['formData']:
                att['#content'] = constructContent(element['formData'][attrib['key']])
                if not containsFiles:
                    for part in att['#content']:
                        if 'var' in part:
                            # add form entry for element
                            # ?? add information of parent? example: note for agent with role=Archivist&&typ=organization (probably not needed)
                            # adding text if there occures at least one variable.
                            field = {}
                            key = part['var'] # check for doubles
                            if key in takenNames:
                                index = 0
                                while (key + str(index)) in takenNames:
                                    index += 1
                                field['key'] = (key + str(index))
                                takenNames.append((key + str(index)))
                            else:
                                field['key'] = key
                                takenNames.append(key)
                            field['type'] = 'input'
                            to = {}
                            to['type'] = 'text'
                            to['label'] = part['var']
                            field['templateOptions'] = to
                            forms.append(field)
                            data[field['key']] = ''
            else:
                att['#content'] = [] # TODO warning, should not be added if it can't contain any value
            attributeList.append(att)
    el['-attr'] = attributeList
    for childDict in element['children']:
        if childDict['type'] == 'sequence':
            for child in childDict['elements']:
                if 'uuid' in child:
                    if not elements[child['uuid']]['containsFiles']:
                        e, f, d = generateElement(elements, child['uuid'], takenNames, containsFiles=containsFiles)
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
                    else:
                        #containsFiles
                        cf = []
                        elDict = OrderedDict()
                        e, f, d = generateElement(elements, child['uuid'], takenNames, containsFiles=True)
                        if e is not None:
                            if child['name'] in elDict:
                                # cerate array
                                if isinstance(elDict[child['name']], list):
                                    elDict[child['name']].append(e)
                                else:
                                    temp = elDict[child['name']]
                                    elDict[child['name']] = []
                                    elDict[child['name']].append(temp)
                                    elDict[child['name']].append(e)
                            else:
                                elDict[child['name']] = e
                        cf.append(elDict)
                        el['-containsFiles'] = cf

        else:
            found = False
            for child in childDict['elements']:
                if 'uuid' in child:
                    if found:
                        # TODO ERROR Should only find one
                        print 'ERROR'
                    else:
                        found = True
                        if not elements[child['uuid']]['containsFiles']:
                            e, f, d = generateElement(elements, child['uuid'], takenNames, containsFiles=containsFiles)
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
                        else:
                            #containsFiles
                            cf = []
                            elDict = OrderedDict()
                            e, f, d = generateElement(elements, child['uuid'], takenNames, containsFiles=True)
                            if e is not None:
                                if child['name'] in elDict:
                                    # cerate array
                                    if isinstance(elDict[child['name']], list):
                                        elDict[child['name']].append(e)
                                    else:
                                        temp = elDict[child['name']]
                                        elDict[child['name']] = []
                                        elDict[child['name']].append(temp)
                                        elDict[child['name']].append(e)
                                else:
                                    elDict[child['name']] = e
                            cf.append(elDict)
                            el['-containsFiles'] = cf
    return (el, forms, data)

def generateTemplate(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    existingElements = obj.existingElements
    jsonString = OrderedDict()
    jsonString[existingElements['root']['name']], forms, data = generateElement(existingElements, 'root')

    t = finishedTemplate(name='test', template=jsonString, form=forms, data=data)
    t.save()
    return JsonResponse(jsonString, safe=False)

def getExistingElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    return JsonResponse(obj.existingElements, safe=False)

def getAllElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    return JsonResponse(obj.allElements, safe=False)

def removeChild(request, name, uuid):
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
    removeChildren(existingElements, oldElement)
    obj.existingElements = existingElements
    obj.save()
    return JsonResponse(existingElements, safe=False)

def removeChildren(existingElements ,element):
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

def addAttribute(request, name, uuid):
    obj = get_object_or_404(templatePackage, pk=name)
    obj.existingElements[uuid]['userForm'].append(json.loads(request.body))
    obj.save()
    return JsonResponse(obj.existingElements[uuid]['userForm'], safe=False)

def setContainsFiles(request, name, uuid, containsFiles):
    obj = get_object_or_404(templatePackage, pk=name)
    if containsFiles == '1':
        obj.existingElements[uuid]['containsFiles'] = True
    else:
        obj.existingElements[uuid]['containsFiles'] = False
    obj.save()
    return JsonResponse(obj.existingElements, safe=False)

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

class index(View):
    template_name = 'templateMaker/index.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'hello World'
        objs = templatePackage.objects.all()#.values('name')
        context['templates'] = objs

        return render(request, self.template_name, context)

class add(View):
    template_name = 'templateMaker/add.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Add template'
        context['form'] = AddTemplateForm()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        form = AddTemplateForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponse(request.FILES['file'])
            # handle_uploaded_file(request.FILES['file'])
            pass

        name = request.POST['template_name']
        if templatePackage.objects.filter(pk=name).exists():
            return HttpResponse('ERROR: templatePackage with name "' + name + '" already exists!')

        existingElements, allElements = generate(request.FILES['file']);
        t = templatePackage(existingElements=existingElements, allElements=allElements, name=name)
        t.save()
        return redirect('/template/edit/' + name)

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
        context['templateName'] = kwargs['name']

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

        res = json.loads(request.body)
        uuid = res['uuid']
        del res['uuid']

        obj = get_object_or_404(templatePackage, pk=kwargs['name'])
        j = obj.existingElements
        obj.existingElements[uuid]['formData'] = res
        obj.save()
        return JsonResponse(res, safe=False)
