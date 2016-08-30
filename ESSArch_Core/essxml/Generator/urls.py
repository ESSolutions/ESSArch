from django.conf.urls import url
from views import (
    demo,
    demo2,
    testing,
#     edit,
#     demo,
#     # SubmitIPCreate,
)
# from views import {
#     create,
# }
from . import views

urlpatterns = [
    # url(r'^make-old/$', views.index, name='make_template'),
    # url(r'^reset/$', views.resetData, name='reset_data_template'),
    # url(r'^generate/(?P<name>[A-z]+)/$', views.generateTemplate, name='generate_template'),
    # url(r'^struct/addChild/(?P<name>[A-z]+)/(?P<path>[A-z0-9-]+)/$', views.addChild, name='add_data_template'),
    # url(r'^struct/addUserChild/(?P<name>[A-z]+)/$', views.addUserChild, name='add_userdata_template'),
    # url(r'^struct/removeChild/(?P<name>[A-z]+)/$', views.deleteChild, name='add_data_template'),
    # url(r'^struct/addAttrib/(?P<name>[A-z]+)/(?P<uuid>[A-z0-9-]+)/$', views.addAttribute, name='add_attrib_template'),
    # url(r'^struct/(?P<name>[A-z]+)/$', views.getStruct, name='get_data_template'),
    # url(r'^struct/(?P<name>[A-z0-9-]+)/(?P<uuid>[A-z0-9-]+)/$', views.getElement, name='get_element_template'),
    # url(r'^make/$', create.as_view(), name='create_template'),
    # url(r'^edit/(?P<name>[A-z0-9-]+)/$', views.saveForm, name='update_template'),
    # url(r'^edit/$', edit.as_view(), name='edit_template'),
    url(r'^$', demo.as_view(), name='demo'),
    url(r'^other/$', demo2.as_view(), name='demo2'),
    url(r'^test/$', testing.as_view(), name='testing'),
    # url(r'^gen/$', views.gen, name='gen'),
    # url(r'^data/(?P<name>[A-z0-9-]+)/$', views.getData, name='get_demo_data'),
    # url(r'^submitipcreate/(?P<id>\d+)$', SubmitIPCreate.as_view(), name='submit_submitipcreate'),
]
