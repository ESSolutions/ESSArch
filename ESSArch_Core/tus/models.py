from django.db import models


class TusUpload(models.Model):
    upload_id = models.CharField(max_length=64, unique=True)
    ip_id = models.CharField(max_length=64, null=True, blank=True)
    filename = models.CharField(max_length=255)
    temp_path = models.CharField(max_length=500)

    # Processing tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("PROCESSING", "Processing"),
            ("DONE", "Done"),
            ("ERROR", "Error"),
        ],
        default="PENDING",
    )

    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
