try:
    from django.core.urlresolvers import reverse
except ModuleNotFoundError:
    # Django 2.x
    from django.urls import reverse

from django.conf import settings
from django.shortcuts import redirect
from django.views.static import serve

try:
    DOCS_ROOT = settings.DOCS_ROOT
except AttributeError:
    raise ValueError('Missing DOCS_ROOT in settings')

def detail(request, path, **kwargs):
    lang = kwargs.pop('lang', 'en')
    kwargs['document_root'] = DOCS_ROOT.format(lang=lang)
    return serve(request, path, **kwargs)

def index(request):
    return redirect('docs:detail', path='index.html', lang='en')
