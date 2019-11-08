from django.shortcuts import render

default_app_config = 'ESSArch_Core.frontend.apps.FrontendConfig'


def home(req):
    return render(req, 'essarch_core_frontend/main.html')
