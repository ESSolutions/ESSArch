
import base64
from pathlib import Path

from django.conf import settings


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
