from django.shortcuts import render
import os
import json
import uuid
from django.conf import settings
from django.views.generic import View
from django.http import JsonResponse
# from esscore.template.templateGenerator.testXSDToJSON import generate

def get_ip_identification(folderToParse):
    ip_identification = 'unknown'
    dir_list = os.listdir(folderToParse)
    id_list = []
    for item in dir_list:
        item_path = os.path.join(folderToParse, item)
        if os.path.isfile(item_path):
            root, ext = os.path.splitext(item)
            if ext.lower() in ['.tar', '.zip']:
                id_list.append(root)
    
    if len(id_list) == 1:
        ip_identification = id_list[0]

    return ip_identification

class demo2(View):
    template_name = 'demo/demo2.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from xmlGenerator import createXML

        res = json.loads(request.body)
        # return JsonResponse(res, safe=False)
        info = res
        filesToCreate = {}
        filesToCreate[res['INPUTFILE'] + '/' + res['DOCUMENTID']] = os.path.join(settings.BASE_DIR,'demo/info.json')
        folderToParse = res['INPUTFILE']
        # update MetsOBJID and MetsId
        info['MetsOBJID'] = 'UUID:%s' % get_ip_identification(folderToParse)
        info['MetsId'] = str(uuid.uuid4())

        response = createXML(info, filesToCreate, folderToParse)

        return JsonResponse(request.body, safe=False)

class demo(View):
    template_name = 'demo/demo.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from xmlGenerator import createXML

        res = json.loads(request.body)
        # return JsonResponse(res, safe=False)
        info = res
        filesToCreate = {}
        filesToCreate[res['INPUTFILE'] + '/' + res['DOCUMENTID']] = os.path.join(settings.BASE_DIR,'demo/info.json')
        folderToParse = res['INPUTFILE']
        # update MetsOBJID and MetsId
        info['MetsOBJID'] = 'UUID:%s' % get_ip_identification(folderToParse)
        info['MetsId'] = str(uuid.uuid4())

        response = createXML(info, filesToCreate, folderToParse)

        return JsonResponse(request.body, safe=False)
