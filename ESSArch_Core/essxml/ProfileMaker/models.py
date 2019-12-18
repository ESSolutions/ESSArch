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


from django.db import models

from ESSArch_Core.fields import JSONField


class extensionPackage(models.Model):
    id = models.AutoField(primary_key=True)
    allElements = JSONField(null=True)
    existingElements = JSONField(null=True)
    allAttributes = JSONField(null=True)

    prefix = models.CharField(max_length=20)
    schemaURL = models.URLField()
    targetNamespace = models.CharField(max_length=255)
    nsmap = JSONField(default={})


class templatePackage(models.Model):
    existingElements = JSONField(null=True)
    # treeData = JSONField(null=True)
    allElements = JSONField(null=True)
    structure = JSONField(default=[])
    # isTreeCreated = models.BooleanField(default=True)
    name = models.CharField(max_length=255, primary_key=True)
    root_element = models.CharField(max_length=55, default='')
    extensions = models.ManyToManyField(extensionPackage)

    prefix = models.CharField(max_length=20)
    schemaURL = models.URLField()
    targetNamespace = models.CharField(max_length=255)
    nsmap = JSONField(default={})
    # generated = models.BooleanField(default=False)
    # creator         = models.CharField( max_length = 255 )
#     archivist_organization  = models.CharField( max_length = 255 )
#     label                   = models.CharField( max_length = 255 )
# #    startdate               = models.CharField( max_length = 255 )
# #    enddate                 = models.CharField( max_length = 255 )
#     createdate              = models.CharField( max_length = 255 )
#     iptype                  = models.CharField( max_length = 255 )
#     uuid                    = models.CharField( max_length = 255 )
#     directory               = models.CharField( max_length = 255 )
#     site_profile            = models.CharField( max_length = 255 )
#     state                   = models.CharField( max_length = 255 )
#     zone                    = models.CharField( max_length = 70 )
#     progress                = models.IntegerField()
    # class Meta:
    #     permissions = (
    #         ("Can_view_ip_menu", "Can_view_ip_menu"),
    #     )
