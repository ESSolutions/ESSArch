import ast
import shutil
from pathlib import Path

from django.dispatch import Signal, receiver

from ESSArch_Core.ip.models import InformationPackage, Workarea

from .models import TusUpload
from .utils import upload_path

# Tus upload complete signal
tus_complete = Signal()


@receiver(tus_complete)
def move_uploaded_file(sender, upload_id, metadata_path, **kwargs):
    # print(f"Tus upload complete signal received: {upload_id}")

    try:
        upload = TusUpload.objects.get(upload_id=upload_id)
    except TusUpload.DoesNotExist:
        # print(f"TusUpload record missing for {upload_id}")
        return

    upload.status = "PROCESSING"
    upload.save(update_fields=["status"])

    meta = ast.literal_eval(metadata_path.read_text())
    ip_id = meta.get("ip_id")
    ip_type = meta.get("ip_type")
    user_id = meta.get("user_id")
    filename = meta.get("filename", upload_id)
    relativePath = meta.get("relativePath", filename)
    destination = meta.get("destination", '')

    temp_file = upload_path(upload_id)
    if not temp_file.exists():
        # print(f"Upload file {upload_id} not found in temp")
        return

    try:
        if ip_id:
            if ip_type == 'workarea':
                workarea_obj = Workarea.objects.get(ip__id=ip_id, user__id=user_id)
                dest_path = Path(workarea_obj.path) / destination / relativePath
            else:
                ip = InformationPackage.objects.get(pk=ip_id)
                dest_path = Path(ip.object_path) / destination / relativePath

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp_file), dest_path.as_posix())
            upload.status = "DONE"
            upload.save(update_fields=["status"])

            # CLEANUP — Remove metadata file
            metadata_path.unlink(missing_ok=True)
            # print(f"Removed metadata file for {upload_id} - {metadata_path}")
        else:
            # print(f"InformationPackage {ip_id} not found; upload {upload_id} remains in temp")
            upload.status = "ERROR"
            upload.error_message = "Missing ip_id"
            upload.save(update_fields=["status", "error_message"])
    except Exception as e:
        # print(f"Error upload {upload_id} remains in temp, error: {e}")
        upload.status = "ERROR"
        upload.error_message = str(e)
        upload.save(update_fields=["status", "error_message"])
