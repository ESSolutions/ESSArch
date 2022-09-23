from django.urls import re_path

from . import home

urlpatterns = [
    re_path(r'^$', home, name='home'),
]
