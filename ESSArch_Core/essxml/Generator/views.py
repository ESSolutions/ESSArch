from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, loader, RequestContext
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


def hate(request):
    from xmlGenerator import createXML

    res = json.loads(request.body)
    # return JsonResponse(res, safe=False)
    infoData = {}
    infoData['info'] = res
    ftc = {}
    ftc[res['DOCUMENTID']] = 'demo/info.json'
    infoData['filesToCreate'] = ftc
    infoData['folderToParse'] = res['INPUTFILE']

    response = createXML(infoData)

    return JsonResponse(request.body, safe=False)

class demo2(View):
    template_name = 'demo/demo2.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'

        return render(request, self.template_name, context)

class demo(View):
    template_name = 'demo/demo.html'

    def get(self, request, *args, **kwargs):
        context = {}
        context['label'] = 'Edit template'

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        # res = json.loads(request.body)

        # obj = get_object_or_404(finishedTemplate, pk='test') # TODO not hardcoded
        # obj.data = res
        # obj.save()

        # return JsonResponse(request.body, safe=False)

        from xmlGenerator import createXML

        res = json.loads(request.body)

        # inputData = {
        #     "filesToCreate": {
        #     "info.txt":"templates/info.json",
        #     # "premis.txt":"templates/JSONPremisTemplate.txt",
        #     # "sip2.txt":"templates/JSONTemplate.txt"
        #     },
        #     "folderToParse":"/SIP"
        # }
        # inputData['info'] = request.body ####

        # print calculateChecksum('/SIP/tar.dmg')
        return HttpResponse(res)

        createXML(res, {"info.xml":"info.json"}, '/SIP') #info, filesToCreate, folderToParse


        return JsonResponse(request.body, safe=False)
        # return redirect('/demo/')

    # def post(self, request, *args, **kwargs):
    #
    #     res = json.loads(request.body)
    #
    #     obj = get_object_or_404(finishedTemplate, pk='test') # TODO not hardcoded
    #     obj.data = res
    #     obj.save()
    #
    #     return JsonResponse(request.body, safe=False)
