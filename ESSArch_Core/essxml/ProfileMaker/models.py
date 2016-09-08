
from django.db import models
import jsonfield

class templatePackage(models.Model):
    existingElements = jsonfield.JSONField(null=True)
    # treeData = jsonfield.JSONField(null=True)
    allElements = jsonfield.JSONField(null=True)
    # isTreeCreated = models.BooleanField(default=True)
    name = models.CharField(max_length = 255, primary_key=True)
    namespace = models.CharField(max_length=20, default='')
    root_element = models.CharField(max_length=55, default='')
    # generated = models.BooleanField(default=False)
    #creator         = models.CharField( max_length = 255 )
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


# class finishedTemplate(models.Model):
#     name = models.CharField(max_length=255, primary_key=True)
#     template = jsonfield.JSONField(null=True)
#     form = jsonfield.JSONField(null=True)
#     data = jsonfield.JSONField(null=True)
