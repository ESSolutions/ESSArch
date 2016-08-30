from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, loader, RequestContext
import os
# from models import templatePackage, finishedTemplate
#file upload
# import the logging library and get an instance of a logger
# import logging
# logger = logging.getLogger('code.exceptions')

# import re
import copy
import json
import uuid
from collections import OrderedDict

from django.views.generic import View
from django.http import JsonResponse
# from esscore.template.templateGenerator.testXSDToJSON import generate

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
        infoData = {}
        infoData['info'] = res
        ftc = {}
        ftc[res['INPUTFILE'] + '/' + res['DOCUMENTID']] = 'demo/info.json'
        infoData['filesToCreate'] = ftc
        infoData['folderToParse'] = res['INPUTFILE']

        response = createXML(infoData)

        return JsonResponse(request.body, safe=False)

class testing(View):
    def get(self, request, *args, **kwargs):
        # test 1
        json_data=open('demo/info.json').read()
        return JsonResponse(json_data, safe=False)
        #test 2
        xmlFile = os.open('info.xml',os.O_RDWR|os.O_CREAT)
        os.write(xmlFile, '<?xml version="1.0" encoding="UTF-8"?>\n')
        return HttpResponse('Creating xml file working?')
        #test 3
        fid = os.open('tmp0.txt',os.O_RDWR|os.O_CREAT)
        return HttpResponse('Creating tmp file working?')


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
        infoData = {}
        infoData['info'] = res
        ftc = {}
        ftc[res['INPUTFILE'] + '/' + res['DOCUMENTID']] = 'demo/info.json'
        infoData['filesToCreate'] = ftc
        infoData['folderToParse'] = res['INPUTFILE']

        response = createXML(infoData)

        return JsonResponse(request.body, safe=False)
