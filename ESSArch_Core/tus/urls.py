from django.urls import path, re_path

from .views import tus_create_view, tus_upload_view, upload_config_view

urlpatterns = [
    path("upload-config/", upload_config_view, name="upload-config"),
    path("", tus_create_view, name="tus-create"),
    re_path(r"^(?P<upload_id>[^/]+)/?$", tus_upload_view, name="tus-upload"),
]
