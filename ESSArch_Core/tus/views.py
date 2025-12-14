import ast
import os
import uuid

from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes

from .utils import meta_path, move_uploaded_file, parse_metadata, upload_path


# -------------------------------
# POST — create a new upload
# -------------------------------
@api_view(["POST"])
@permission_classes([])  # no DRF permissions applied
def tus_create_view(request):
    upload_length = request.headers.get("Upload-Length")
    metadata_header = request.headers.get("Upload-Metadata", "")

    if not upload_length:
        return HttpResponse("Missing Upload-Length", status=400)

    upload_id = str(uuid.uuid4())
    file_path = upload_path(upload_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)

    # Metadata from client
    meta = parse_metadata(metadata_header)

    # Save metadata including total length
    meta['upload_length'] = int(upload_length)
    # print('meta:', meta)
    meta['ip_id'] = meta.get('ip_id')
    meta['relativePath'] = meta.get('relativePath') if not meta.get('relativePath') == 'null' else meta.get('filename')
    meta_path(upload_id).write_text(str(meta))

    cache.set(f'tus_upload_{upload_id}', 'PENDING', timeout=3600)  # 1 hour

    response = HttpResponse(status=201)
    response["Location"] = f"/tus/{upload_id}"  # no trailing slash needed
    response["Tus-Resumable"] = "1.0.0"
    response["Tus-Extension"] = "creation,termination"
    return response


# -------------------------------
# PATCH / HEAD / OPTIONS — upload chunks
# -------------------------------
@api_view(["PATCH", "HEAD", "OPTIONS", "DELETE"])
@permission_classes([])  # no DRF permissions applied
def tus_upload_view(request, upload_id):
    file_path = upload_path(upload_id)
    m_path = meta_path(upload_id)
    method = request.method

    # OPTIONS — Tus handshake
    if method == "OPTIONS":
        response = HttpResponse()
        response["Tus-Resumable"] = "1.0.0"
        response["Tus-Version"] = "1.0.0"
        response["Tus-Extension"] = "creation,termination"
        return response

    # HEAD — report current offset
    if method == "HEAD":
        if not file_path.exists():
            return HttpResponse(status=404)

        status = cache.get(f'tus_upload_{upload_id}')
        if status is None or status == 'ERROR':
            return HttpResponse(status=404)

        offset = file_path.stat().st_size

        # Read total length from stored metadata
        meta = ast.literal_eval(m_path.read_text())
        upload_length = meta.get("upload_length")

        # ⚠ Check for zero-byte file
        # if offset == 0 and (upload_length and not upload_length == 0):
        if offset == 0 and not upload_length == 0:
            # if offset == 0:
            # Either delete or flag for retry
            file_path.unlink(missing_ok=True)
            m_path.unlink(missing_ok=True)
            return HttpResponse(status=404)

        response = HttpResponse()
        response["Upload-Offset"] = str(offset)
        response["Upload-Length"] = str(upload_length)
        response["Tus-Resumable"] = "1.0.0"
        return response

    # PATCH — append chunk
    if method == "PATCH":
        if not file_path.exists():
            return HttpResponse(status=404)

        upload_offset = int(request.headers.get("Upload-Offset", 0))
        current_size = file_path.stat().st_size

        if upload_offset != current_size:
            file_path.unlink(missing_ok=True)
            m_path.unlink(missing_ok=True)
            return HttpResponse("Offset mismatch", status=409)

        # Append chunk
        with open(file_path, "ab") as f:
            f.write(request.body)
            f.flush()              # Flush Python buffer
            os.fsync(f.fileno())   # Flush OS buffer to disk

        new_offset = file_path.stat().st_size

        # Read total length from stored metadata
        meta = ast.literal_eval(m_path.read_text())
        upload_length = meta.get("upload_length")

        # ⚠ Check for zero-byte file
        if new_offset == 0 and not upload_length == 0:
            # if new_offset == 0:
            # Either delete or flag for retry
            file_path.unlink(missing_ok=True)
            m_path.unlink(missing_ok=True)
            return HttpResponse("File empty, retry upload", status=409)

        # Trigger signal if upload is complete
        if upload_length and new_offset >= upload_length:
            res = move_uploaded_file(file_path, m_path, meta)
            if res == "Success":
                cache.set(f'tus_upload_{upload_id}', 'DONE', timeout=3600)  # 1 hour
            else:
                cache.set(f'tus_upload_{upload_id}', 'ERROR', timeout=3600)  # 1 hour
                return HttpResponse(f"Error finalizing upload: {res}", status=409)

        response = HttpResponse(status=204)
        response["Upload-Offset"] = str(new_offset)
        response["Tus-Resumable"] = "1.0.0"
        return response

    # ---- DELETE (cancel upload) ----
    if request.method == "DELETE":

        if file_path.exists():
            file_path.unlink()

        if m_path.exists():
            m_path.unlink()

        return HttpResponse(status=204)

    return HttpResponse(status=405)
