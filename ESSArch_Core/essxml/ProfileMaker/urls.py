"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django.conf.urls import url
from views import (
    create,
    edit,
    index,
    add,
    addExtension,
    generate,
    # SubmitIPCreate,
)
# from views import {
#     create,
# }
from . import views

urlpatterns = [
    url(r'^$', index.as_view(), name='template_index'),
    url(r'^edit/(?P<name>[A-z0-9]+)/$', edit.as_view(), name='template_edit'),
    url(r'^add/$', add.as_view(), name='template_add'),
    url(r'^add-extension/(?P<name>[A-z0-9]+)/$', addExtension.as_view(), name='template_add_extension'),
    # url(r'^reset/$', views.resetData, name='reset_data_template'),
    url(r'^generate/(?P<name>[A-z0-9]+)/$', generate.as_view(), name='generate_template'),
    url(r'^delete/(?P<name>[A-z0-9]+)/$', views.deleteTemplate, name='delete_template'),
    url(r'^struct/addChild/(?P<name>[A-z0-9]+)/(?P<newElementName>[A-z0-9]+)/(?P<elementUuid>[A-z0-9-]+)/$', views.addChild, name='add_data_template'),
    url(r'^struct/addUserChild/(?P<name>[A-z0-9]+)/$', views.addUserChild, name='add_userdata_template'),
    url(r'^struct/addExtensionChild/(?P<name>[A-z0-9]+)/$', views.addExtensionElement, name='add_userdata_template'),
    url(r'^struct/removeChild/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/$', views.removeChild, name='remove_child_template'),
    url(r'^struct/addAttrib/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/$', views.addAttribute, name='add_attrib_template'),
    url(r'^getAttributes/(?P<name>[A-z0-9]+)/$', views.getAttributes, name='add_attrib_template'),
    url(r'^getElements/(?P<name>[A-z0-9]+)/$', views.getElements, name='add_attrib_template'),

    url(r'^struct/setContainsFiles/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/(?P<containsFiles>[0-1])/$', views.setContainsFiles, name='setContainsFiles_template'),
    url(r'^struct/(?P<name>[A-z0-9]+)/$', views.getExistingElements, name='get_existing_elements'),
    url(r'^struct/elements/(?P<name>[A-z0-9-]+)/$', views.getAllElements, name='get_all_elements'),
    url(r'^make/$', create.as_view(), name='create_template'),
    # url(r'^edit/(?P<name>[A-z0-9-]+)/$', views.saveForm, name='update_template'),
    # url(r'^edit/$', edit.as_view(), name='edit_template'),
    # url(r'^submitipcreate/(?P<id>\d+)$', SubmitIPCreate.as_view(), name='submit_submitipcreate'),
]
