import uuid

from django.db import models

from ESSArch_Core.ip.models import InformationPackage


class Validation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    validator = models.CharField(max_length=255)
    time_started = models.DateTimeField(null=True)
    time_done = models.DateTimeField(null=True)
    passed = models.NullBooleanField(null=True)
    message = models.CharField(max_length=255, blank=True)
    information_package = models.ForeignKey(InformationPackage, on_delete=models.CASCADE, null=True)
