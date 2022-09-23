"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django.urls import re_path

from . import views
from .views import add, addExtension, create, edit, generate, index

urlpatterns = [
    re_path(r'^$', index.as_view(), name='template_index'),
    re_path(r'^edit/(?P<name>[A-z0-9]+)/$', edit.as_view(), name='template_edit'),
    re_path(r'^add/$', add.as_view(), name='template_add'),
    re_path(r'^add-extension/(?P<name>[A-z0-9]+)/$', addExtension.as_view(), name='template_add_extension'),
    # re_path(r'^reset/$', views.resetData, name='reset_data_template'),
    re_path(r'^generate/(?P<name>[A-z0-9]+)/$', generate.as_view(), name='generate_template'),
    re_path(r'^delete/(?P<name>[A-z0-9]+)/$', views.deleteTemplate, name='delete_template'),
    re_path(
        r'^struct/addChild/(?P<name>[A-z0-9]+)/(?P<newElementName>[A-z0-9]+)/(?P<elementUuid>[A-z0-9-]+)/$',
        views.addChild, name='add_data_template'
    ),
    re_path(r'^struct/addUserChild/(?P<name>[A-z0-9]+)/$', views.addUserChild, name='add_userdata_template'),
    re_path(r'^struct/addExtensionChild/(?P<name>[A-z0-9]+)/$',
            views.addExtensionElement, name='add_userdata_template'),
    re_path(
        r'^struct/removeChild/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/$',
        views.removeChild, name='remove_child_template'
    ),
    re_path(
        r'^struct/addAttrib/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/$',
        views.addAttribute, name='add_attrib_template'
    ),
    re_path(r'^getAttributes/(?P<name>[A-z0-9]+)/$', views.getAttributes, name='add_attrib_template'),
    re_path(r'^getElements/(?P<name>[A-z0-9]+)/$', views.getElements, name='add_attrib_template'),

    re_path(
        r'^struct/setContainsFiles/(?P<name>[A-z0-9]+)/(?P<uuid>[A-z0-9-]+)/(?P<containsFiles>[0-1])/$',
        views.setContainsFiles, name='setContainsFiles_template'
    ),
    re_path(r'^struct/(?P<name>[A-z0-9]+)/$', views.getExistingElements, name='get_existing_elements'),
    re_path(r'^struct/elements/(?P<name>[A-z0-9-]+)/$', views.getAllElements, name='get_all_elements'),
    re_path(r'^make/$', create.as_view(), name='create_template'),
    # re_path(r'^edit/(?P<name>[A-z0-9-]+)/$', views.saveForm, name='update_template'),
    # re_path(r'^edit/$', edit.as_view(), name='edit_template'),
    # re_path(r'^submitipcreate/(?P<id>\d+)$', SubmitIPCreate.as_view(), name='submit_submitipcreate'),
]
