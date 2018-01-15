try:
    from django.core.urlresolvers import reverse
except ModuleNotFoundError:
    # Django 2.x
    from django.urls import reverse

from django.conf import settings
from django.views.generic import RedirectView
from django.views.static import serve

try:
    DOCS_ROOT = settings.DOCS_ROOT
except AttributeError:
    raise ValueError('Missing DOCS_ROOT in settings')

def serve_docs(request, path, **kwargs):
    kwargs['document_root'] = DOCS_ROOT
    return serve(request, path, **kwargs)

class DocsView(RedirectView):
    def get_redirect_url(self, **kwargs):
        return reverse('docs-files', kwargs={'path': 'index.html'})
