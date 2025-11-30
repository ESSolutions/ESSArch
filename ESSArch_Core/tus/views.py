# ESSArch_Core/tus/views.py
import ast
import os
import uuid

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import TusUpload
from .signals import tus_complete
from .utils import meta_path, parse_metadata, upload_path


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

    # Create DB record
    TusUpload.objects.create(
        upload_id=upload_id,
        ip_id=meta.get("ip_id"),
        filename=meta.get("filename", upload_id),
        temp_path=str(file_path),
        status="PENDING",
    )

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
            tus_complete.send(sender=None, upload_id=upload_id, metadata_path=m_path)

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


@api_view(["GET"])
@permission_classes([])
def tus_status_view(request, upload_id):
    file_path = upload_path(upload_id)
    m_path = meta_path(upload_id)
    try:
        upload = TusUpload.objects.get(upload_id=upload_id)
    except TusUpload.DoesNotExist:
        # Read total length from stored metadata
        meta = ast.literal_eval(m_path.read_text())
        upload_length = meta.get("upload_length")
        if file_path.exists():
            offset = file_path.stat().st_size
        # ⚠ Check for zero-byte file
        if offset == 0 and not upload_length == 0:
            # if offset == 0:
            # Either delete or flag for retry
            file_path.unlink(missing_ok=True)
            m_path.unlink(missing_ok=True)
        return Response({"error": "Not found"}, status=404)

    return Response({
        "upload_id": upload_id,
        "status": upload.status,
        "error": upload.error_message,
    })

    # return Response({
    #     "upload_id": upload_id,
    #     "status": "ERROR",
    #     "error": 'hej hopp',
    # })
