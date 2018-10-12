from django.conf.urls import url

from . import home

urlpatterns = [
    url(r'^$', home, name='home'),
]
