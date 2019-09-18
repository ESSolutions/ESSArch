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
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django import forms


class AddTemplateForm(forms.Form):
    template_name = forms.CharField(max_length=50)
    namespace_prefix = forms.CharField(max_length=20)
    root_element = forms.CharField(max_length=55)
    schema = forms.URLField()


class AddExtensionForm(forms.Form):
    namespace_prefix = forms.CharField(max_length=20)
    schema = forms.URLField()
