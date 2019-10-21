from django.conf.urls import url

from .views import detail, index

app_name = 'docs'
urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^(?P<lang>[a-z-]+)/(?P<path>.*)$', detail, name='detail'),
]
