from django.urls import re_path

from .views import tus_create_view, tus_status_view, tus_upload_view

urlpatterns = [
    re_path(r"^$", tus_create_view, name="tus-create"),
    re_path(r"^(?P<upload_id>[^/]+)/?$", tus_upload_view, name="tus-upload"),
    re_path(r'^(?P<upload_id>[^/]+)/status', tus_status_view),
]
