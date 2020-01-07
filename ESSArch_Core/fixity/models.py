import uuid

from django.contrib.auth import get_user_model
from django.db import models

from ESSArch_Core.fields import JSONField

User = get_user_model()


class Validation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    validator = models.CharField(max_length=255)
    specification = JSONField(null=True)
    time_started = models.DateTimeField(null=True)
    time_done = models.DateTimeField(null=True)
    passed = models.NullBooleanField(null=True)
    required = models.BooleanField(default=True)
    message = models.TextField(max_length=255, blank=True)
    information_package = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.CASCADE,
        null=True,
        related_name='validations',
    )
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
