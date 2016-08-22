
from django.db import models

class templatePackage(models.Model):
    structure = models.TextField()
    elements = models.TextField()
    name = models.CharField(max_length = 255, primary_key=True)
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
