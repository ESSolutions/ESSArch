from django.urls import re_path

from .views import detail, index

app_name = 'docs'
urlpatterns = [
    re_path(r'^$', index, name='index'),
    re_path(r'^(?P<lang>[a-z-]+)/(?P<path>.*)$', detail, name='detail'),
]
