from django.conf.urls import url
from .views import DocsView, serve_docs


urlpatterns = [
    url(r'^$', DocsView.as_view(permanent=True), name='docs-root'),
    url(r'^(?P<path>.*)$', serve_docs, name='docs-files'),
]
