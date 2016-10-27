
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from models import templatePackage, extensionPackage
from profiles.models import Profile
import requests
from lxml import etree
import os
from django.conf import settings
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
from esscore.template.templateGenerator.testXSDToJSON import generateJsonRes, generateExtensionRef
from forms import AddTemplateForm, AddExtensionForm


def constructContent(text):
    res = []
    i = text.find('{{')
    if i > 0: # default text followed by variable
        d = {}
        d['text'] = text[0:i]
        res.append(d)
        r = constructContent(text[i:])
        for j in range(len(r)):
            res.append(r[j])
    elif i == -1: # no variable found, only eventual default text
        if len(text) > 0:
            d = {}
            d['text'] = text
            res.append(d)
    else: # variable followed by eventual default text
        d = {};
        v = text[i+2:]
        i = v.find('}}')
        d['var'] = v[0:i]
        res.append(d);
        r = constructContent(v[i+2:])
        for j in range(len(r)):
            res.append(r[j])
    return res

def getTrail(elementTree, element, trail=[]):
    """
    Gets the path to the specified element via its parents.

    Example:
        Foo
        |
        --Bar
            |
            --Baz

    When specifiing Baz as the element, this would return [Foo, Bar, Baz]

    Args:
        elementTree: The tree of elements to traverse
        element: The element to get the trail for
        trail: The trail so far

    Returns:
        A list containing the ancestors of the specified element
    """

    parent = element.get('parent')
    trail.insert(0, element.get('name'))

    if parent:
        return getTrail(elementTree, elementTree[parent], trail)
    else:
        return trail

def generateElement(elements, currentUuid, takenNames=[], containsFiles=False, namespace=''):
    element = elements[currentUuid]
    el = OrderedDict()
    forms = []
    data = {}
    el['-name'] = element['name']
    el['-min'] = element['min']
    el['-max'] = element['max']
    el['-containsFiles'] = element.get('containsFiles')
    el['-nsmap'] = element.get('nsmap')
    if 'namespace' in element:
        if element['namespace'] != namespace:
            namespace = element['namespace']
            el['-namespace'] = namespace
    # TODO namespace
    attributes = element['form'] + element['userForm']
    attributeList = []

    if not containsFiles and not element.get('children'):
        el['#content'] = []

    for attrib in attributes:
        trail = getTrail(elements, element, [])
        trailstr = '.'.join(trail)
        var = trailstr + '.' + attrib['key']

        att = OrderedDict()

        if attrib['key'] in element['formData']: # if custom value has been entered
            content = constructContent(element['formData'][attrib['key']])
            att['#content'] = content
        else:
            att['#content'] = [{
                'var': var
            }]

        if attrib['key'] == '#content':
            el['#content'] = att['#content']
        else:
            att['-name'] = attrib['key']
            att['-req'] = 1 if attrib['templateOptions'].get('required') else 0

            to = {
                'label': var,
                'type': 'text',
            }

            if 'desc' in attrib:
                to['desc'] = attrib['desc']

            if 'readonly' in attrib:
                to['readonly'] = attrib['readonly']

            field = {
                'key': var,
                'type': 'input',
                'templateOptions': to,
            }

            if 'hideExpression' in attrib:
                field['hideExpression'] = str(attrib['hideExpression']).lower()

            forms.append(field)
            data[field['key']] = ''

            attributeList.append(att)
    el['-attr'] = attributeList

    el['-children'] = []

    for child in element['children']:
        e, f, d = generateElement(elements, child['uuid'], takenNames, containsFiles=containsFiles, namespace=namespace)
        if e:
            el['-children'].append(e)
            for field in f:
                forms.append(field)
            data.update(d)

    return (el, forms, data)

def getExistingElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    return JsonResponse(obj.existingElements, safe=False)

def getAllElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    return JsonResponse(obj.allElements, safe=False)

def getElements(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    res = []
    for extension in obj.extensions.all():
        if extension.existingElements != None and len(extension.existingElements) > 0:
            r = {}
            r['name'] = extension.namespace
            children = []
            for child in extension.existingElements:
                c = {}
                c['name'] = child
                c['data'] = extension.existingElements[child]
                children.append(c)
            r['children'] = children
            res.append(r)
    return JsonResponse(res, safe=False)

def removeChild(request, name, uuid):
    obj = get_object_or_404(templatePackage, pk=name)
    existingElements = obj.existingElements
    oldElement = existingElements[uuid]

    parent = existingElements[oldElement['parent']]
    index = 0
    copy_idx = None
    deleted_name = None
    for child in parent['children']:

        if child['uuid'] == uuid:
            try:
                name = child['name'].split('#')[0]
            except:
                name = child['name']

            deleted_name = name
            del parent['children'][index]
            break;

        index += 1

    if deleted_name:
        for child in parent['children'][index:]:
            try:
                name, copy_idx = child['name'].split('#')
                copy_idx = int(copy_idx)
            except:
                name = child['name']

            if deleted_name == name:
                if copy_idx and copy_idx == 1:
                    child['name'] = name
                else:
                    child['name'] = name + "#" + str(copy_idx-1)

                existingElements[child["uuid"]]["name"] = child["name"]



    removeChildren(existingElements, oldElement)
    del existingElements[uuid]
    obj.save()
    return JsonResponse(existingElements, safe=False)

def removeChildren(existingElements ,element):
    for child in element['children']:
        removeChildren(existingElements, existingElements[child['uuid']])
        del existingElements[child['uuid']]

def addUserChild(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    newUuid = uuid.uuid4().__str__()
    res = json.loads(request.body)
    parent = obj.existingElements[res['parent']]
    element = {}
    element['anyAttribute'] = True
    element['anyElement'] = True
    element['availableChildren'] = []
    element['children'] = []
    element['containsFiles'] = False
    element['form'] = []
    element['formData'] = []
    element['max'] = res['max']
    element['min'] = res['min']
    element['name'] = res['name']
    element['namespace'] = parent['namespace']
    element['parent'] = res['parent']
    element['userForm'] = []
    obj.existingElements[newUuid] = element
    e = {}
    e['name'] = res['name']
    e['uuid'] = newUuid
    obj.existingElements[res['parent']]['children'].append(e)
    obj.save()
    return JsonResponse(obj.existingElements, safe=False)

def addExtensionElement(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    newUuid = uuid.uuid4().__str__()
    res = json.loads(request.body)
    parent = obj.existingElements[res['parent']]
    element = {}
    element['anyAttribute'] = True
    element['anyElement'] = True
    element['availableChildren'] = []
    if 'availableChildren' in res:
        element['availableChildren'] = res['availableChildren']
    element['children'] = []
    element['containsFiles'] = False
    element['form'] = []
    if 'form' in res:
        element['form'] = res['form']
    element['formData'] = []
    if 'formData' in res:
        element['formData'] = res['formData']
    element['max'] = res['max']
    element['min'] = res['min']
    element['name'] = res['name']
    if 'namespace' not in res:
        element['namespace'] = parent['namespace']
    else:
        element['namespace'] = res['namespace']
    element['parent'] = res['parent']
    element['userForm'] = []
    obj.existingElements[newUuid] = element
    e = {}
    e['name'] = res['name']
    e['uuid'] = newUuid
    obj.existingElements[res['parent']]['children'].append(e)
    obj.save()
    return JsonResponse(obj.existingElements, safe=False)

def addChild(request, name, newElementName, elementUuid):
    obj = get_object_or_404(templatePackage, pk=name)
    existingElements = obj.existingElements
    templates = obj.allElements
    newUuid = uuid.uuid4().__str__()
    if newElementName in templates:
        newElement = copy.deepcopy(templates[newElementName])
    else:
        for extension in obj.extensions.all():
            if newElementName in extension.allElements:
                newElement = copy.deepcopy(extension.allElements[newElementName])
    newElement['parent'] = elementUuid
    existingElements[newUuid] = newElement

    #calculate which elements should be before
    cb = calculateChildrenBefore(existingElements[elementUuid]['availableChildren'], newElementName)

    index = 0

    for idx, child in enumerate(existingElements[elementUuid]['children']):
        try:
            name = child['name'].split('#')[0]
        except:
            name = child['name']

        if name == newElementName:
            index = idx+1

    if index > 0:
        newElementName += "#" + str(index)
        newElement['name'] = newElementName
    else:
        for child in existingElements[elementUuid]['children']:
            if child['name'] not in cb:
                break
            else:
                index += 1

    e = {}
    e['name'] = newElementName
    e['uuid'] = newUuid
    existingElements[elementUuid]['children'].insert(index, e)
    obj.save()
    return JsonResponse(existingElements, safe=False)

def calculateChildrenBefore(children, newElementName):
    arr = []
    for child in children:
        if child['type'] == 'element':
            if child['name'] != newElementName:
                arr.append(child['name'])
            else:
                return arr
        elif child['type'] == 'choise':
            arr = arr + calculateChildrenBefore(child['elements'], newElementName)
    return arr

def getAttributes(request, name):
    obj = get_object_or_404(templatePackage, pk=name)
    res = []
    for extension in obj.extensions.all():
        if extension.allAttributes != None and len(extension.allAttributes) > 0:
            r = {}
            r['name'] = extension.prefix
            children = []
            for child in extension.allAttributes:
                c = {}
                c['name'] = child
                c['data'] = extension.allAttributes[child]
                children.append(c)
            r['children'] = children
            res.append(r)
    return JsonResponse(res, safe=False)

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

def saveForm(request, name):

    res = json.loads(request.body)
    uuid = res['uuid']
    del res['uuid']

    obj = get_object_or_404(templatePackage, pk=name)
    obj.existingElements[uuid]['formData'] = res
    obj.save()
    return JsonResponse(res, safe=False)

def deleteTemplate(request, name):
    if request.method == 'POST':
        templatePackage.objects.get(pk=name).delete()
        return HttpResponse('deleted')
    else:
        return HttpResponse('Error this page is only available as post')

class index(View):
    template_name = 'templateMaker/index.html'

    def get(self, request, *args, **kwargs):
        objs = templatePackage.objects.all()#.values('name')
        context = {
            'templates': objs
        }

        return render(request, self.template_name, context)

class add(View):
    template_name = 'templateMaker/add.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Add template'
        context['form'] = AddTemplateForm()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        form = AddTemplateForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data.get('template_name')
            prefix = form.cleaned_data.get('namespace_prefix')
            root = form.cleaned_data.get('root_element')
            schema = form.cleaned_data.get('schema')

            if templatePackage.objects.filter(pk=name).exists():
                return HttpResponse('ERROR: templatePackage with name "' + name + '" already exists!')

            from requests.packages.urllib3.exceptions import (
                InsecureRequestWarning, InsecurePlatformWarning
            )

            requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

            schema_request = requests.get(schema)
            schema_request.raise_for_status()

            schemadoc = etree.fromstring(schema_request.content)
            targetNamespace = schemadoc.get('targetNamespace')
            nsmap = {k:v for k,v in schemadoc.nsmap.iteritems() if k and v != "http://www.w3.org/2001/XMLSchema"}

            existingElements, allElements = generateJsonRes(schemadoc, root, prefix);
            existingElements["root"]["nsmap"] = nsmap

            templatePackage.objects.create(
                existingElements=existingElements, allElements=allElements,
                name=name, prefix=prefix, schemaURL=schema,
                targetNamespace=targetNamespace, root_element=root
            )

            return redirect('/template/edit/' + name)

        return render(request, self.template_name, {'form': form})

class addExtension(View):
    template_name = 'templateMaker/add.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Add template'
        context['form'] = AddExtensionForm()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        obj = get_object_or_404(templatePackage, pk=kwargs['name'])

        form = AddExtensionForm(request.POST)

        if form.is_valid():
            prefix = form.cleaned_data.get('namespace_prefix')
            schema = form.cleaned_data.get('schema')

            from requests.packages.urllib3.exceptions import (
                InsecureRequestWarning, InsecurePlatformWarning
            )

            requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

            schema_request = requests.get(schema)
            schema_request.raise_for_status()

            schemadoc = etree.fromstring(schema_request.content)
            nsmap = {k:v for k,v in schemadoc.nsmap.iteritems() if k and v != "http://www.w3.org/2001/XMLSchema"}
            targetNamespace = schemadoc.get('targetNamespace')

            extensionElements, extensionAll, attributes = generateExtensionRef(schemadoc, prefix)

            e = extensionPackage.objects.create(
                prefix=prefix, schemaURL=schema,
                targetNamespace=targetNamespace, allElements=extensionAll,
                existingElements=extensionElements, allAttributes=attributes
            )
            obj.extensions.add(e)
            obj.existingElements["root"]["nsmap"].update(nsmap)
            obj.save()

            return HttpResponse('Success: Added extension schema')

        return render(request, self.template_name, {'form': form})

class generate(View):
    template_name = 'templateMaker/generate.html'

    def get(self, request, *args, **kwargs):

        context = {}
        context['templateName'] = kwargs['name']

        return render(request, self.template_name, context)

    def addExtraAttribute(self, field, data, attr):
        """
        Adds extra attrbute to field if it exists in data

        Args:
            field: The field to add to
            data: The data dictionary to look in
            attr: The name of the attribute to add

        Returns:
            The new field with the attribute added to it if the attribute
            exists in data. Otherwise the original field.
        """

        field_attr = field['key'] + '_' + attr

        if field_attr in data:
            field[attr] = data[field_attr]

        return field

    def post(self, request, *args, **kwargs):
        # return JsonResponse(request.body, safe=False)
        obj = get_object_or_404(templatePackage, pk=kwargs['name'])
        existingElements = obj.existingElements

        form = existingElements['root']['form']
        formData = existingElements['root']['formData']

        for idx, field in enumerate(form):
            field = self.addExtraAttribute(field, formData, 'desc')
            field = self.addExtraAttribute(field, formData, 'hideExpression')
            field = self.addExtraAttribute(field, formData, 'readonly')

            form[idx] = field


        existingElements['root']['form'] = form

        jsonString, forms, data = generateElement(existingElements, 'root')
        schemaLocation = ['%s %s' % (obj.targetNamespace, obj.schemaURL)]

        XSI = 'http://www.w3.org/2001/XMLSchema-instance'

        if not jsonString["-nsmap"].get("xsi"):
            jsonString["-nsmap"]["xsi"] = XSI

        if not jsonString["-nsmap"].get(obj.prefix):
            jsonString["-nsmap"][obj.prefix] = obj.targetNamespace

        for ext in obj.extensions.all():
            jsonString["-nsmap"][ext.prefix] = ext.targetNamespace

            schemaLocation.append('%s %s' % (ext.targetNamespace, ext.schemaURL))

        schemaLocation = ({
            '-name': 'schemaLocation',
            '-namespace': 'xsi',
            '#content': [{
                'text': ' '.join(schemaLocation)
            }]
        })

        jsonString['-attr'].append(schemaLocation)

        j = json.loads(request.body)
        t = Profile(profile_type=j['profile_type'],
                    name=j['name'], type=j['type'],
                    status=j['status'], label=j['label'],
                    representation_info=j['representation_info'],
                    preservation_descriptive_info=j['preservation_descriptive_info'],
                    supplemental=j['supplemental'],
                    access_constraints=j['access_constraints'],
                    datamodel_reference=j['datamodel_reference'],
                    additional=j['additional'],
                    submission_method=j['submission_method'],
                    submission_schedule=j['submission_schedule'],
                    submission_data_inventory=j['submission_data_inventory'],
                    template=forms, specification=jsonString, specification_data=data)
        t.save()
        return JsonResponse(t.specification_data, safe=False)


class create(View):
    template_name = 'templateMaker/create.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, self.template_name, context)

class edit(View):
    template_name = 'templateMaker/edit.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'
        context['templateName'] = kwargs['name']
        return render(request, self.template_name, context)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):

        res = json.loads(request.body)
        uuid = res['uuid']
        del res['uuid']

        obj = get_object_or_404(templatePackage, pk=kwargs['name'])
        obj.existingElements[uuid]['formData'] = res
        obj.save()
        return JsonResponse(res, safe=False)
