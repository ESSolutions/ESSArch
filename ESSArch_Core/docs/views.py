import mimetypes

from django.conf import settings
from django.shortcuts import redirect
from django.views.static import serve


def detail(request, path, **kwargs):
    lang = kwargs.pop('lang', 'en')
    kwargs['document_root'] = settings.DOCS_ROOT.format(lang=lang)
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('text/css', '.css')
    return serve(request, path, **kwargs)


def index(request):
    return redirect('docs:detail', path='index.html', lang='en')
