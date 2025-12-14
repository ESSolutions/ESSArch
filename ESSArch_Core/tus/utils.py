import base64
import shutil
from pathlib import Path

from django.conf import settings

from ESSArch_Core.ip.models import InformationPackage, Workarea


def upload_path(upload_id):
    return Path(settings.TUS_UPLOAD_DIR) / upload_id


def meta_path(upload_id):
    return upload_path(upload_id).with_suffix(".meta")


def parse_metadata(header: str):
    """
    Converts:
      Upload-Metadata: key1 base64, key2 base64
    Into:
      {"key1": "value", "key2": "value"}
    """
    if not header:
        return {}

    pairs = header.split(",")
    decoded = {}

    for pair in pairs:
        pair_list = pair.strip().split(" ", 1)
        if len(pair_list) < 2:
            key = pair_list[0]
            b64val = ''
        else:
            key, b64val = pair_list
        decoded[key] = base64.b64decode(b64val).decode("utf-8")

    return decoded


def move_uploaded_file(temp_file, metadata_path, meta):
    ip_id = meta.get("ip_id")
    ip_type = meta.get("ip_type")
    user_id = meta.get("user_id")
    filename = meta.get("filename")
    relativePath = meta.get("relativePath", filename)
    destination = meta.get("destination", '')

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
                # print(f'ip.object_path: {ip.object_path} destination: {destination} relativePath: {relativePath}')
                dest_path = Path(ip.object_path) / destination / relativePath

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            # raise ValueError(f'Moved file to {dest_path}')
            shutil.move(str(temp_file), dest_path.as_posix())

            # CLEANUP — Remove metadata file
            metadata_path.unlink(missing_ok=True)
            # print(f"Removed metadata file for {upload_id} - {metadata_path}")
            return "Success"
        else:
            # print(f"InformationPackage {ip_id} not found; upload {upload_id} remains in temp")
            return "Missing ip_id"
    except Exception as e:
        # print(f"Error upload {upload_id} remains in temp, error: {e}")
        return str(e)
