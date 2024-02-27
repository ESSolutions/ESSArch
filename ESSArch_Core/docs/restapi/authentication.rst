================
 Authentication
================

By default, ESSArch is configured with the following authentication schemes:


.. code-block:: python

   AUTHENTICATION_BACKENDS = [
       'django.contrib.auth.backends.ModelBackend',
       'ESSArch_Core.auth.backends.GroupRoleBackend',
       'guardian.backends.ObjectPermissionBackend',
   ]

   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': (
           'rest_framework.authentication.SessionAuthentication',
           'rest_framework.authentication.BasicAuthentication',
           'knox.auth.TokenAuthentication',
       )
   }

This can be altered in the local configuration file.

Token Authentication
=====================

With ``knox.auth.TokenAuthentication`` enabled, HTTP Token
Auth can be used to authenticate the user in API requests.

Get token
----------------------------

.. http:example:: curl

  POST /api/auth/token_login/ HTTP/1.1
  Host: localhost
  Accept: application/json
  Content-Type: application/json

  {
    "username": "admin",
    "password": "admin"
  }


  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "expiry":"2023-03-18T02:26:11.639928+01:00",
    "token":"b6e06b94162ab7ddbc03ea81ae70cca1e654fd6"
  }

Use token in request
----------------------------

..  http:example:: curl

  GET /api/me/ HTTP/1.1
  Host: localhost
  Accept: application/json
  Authorization: Token b6e06b94162ab7ddbc03ea81ae70cca1e654fd6


  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "url": "https://localhost/api/me/",
    "id": 4,
    "username": "admin",
    "first_name": "Firstname",
    "last_name": "Lastname",
    "email": "admin@example.com",
    "organizations": [
      {
        "id": 1,
        "name": "Default",
        "group_type": 1
      }
    ],
    "is_staff": true,
    "is_active": true,
    "is_superuser": false,
    "last_login": "2018-09-28T08:34:25.905182+02:00",
    "date_joined": "2018-08-04T17:54:42+02:00",
    "permissions": [
      "ip.get_from_storage_as_new",
      "ip.delete_archived",
      "ip.delete_last_generation",
      "storage.storage_migration",
      "profiles.add_profile",
      "ip.diff-check",
      "tags.create_archive"
    ],
    "user_permissions": [],
    "ip_list_columns": [
      "label",
      "object_identifier_value",
      "start_date",
      "end_date",
      "delete"
    ],
    "ip_list_view_type": "ip",
    "file_browser_view_type": "grid",
    "current_organization": {
      "id": 1,
      "name": "Default",
      "group_type": 1
    },
    "notifications_enabled": true
  }

Basic Authentication
=====================

With ``rest_framework.authentication.BasicAuthentication`` enabled, `HTTP Basic
Auth`_ can be used to authenticate the user in API requests.

..  http:example:: curl

   GET /api/me/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

   {
     "url": "http://localhost/api/me/",
     "id": 4,
     "username": "admin",
     "first_name": "Firstname",
     "last_name": "Lastname",
     "email": "admin@example.com",
     "organizations": [
       {
         "id": 1,
         "name": "Default",
         "group_type": 1
       }
     ],
     "is_staff": true,
     "is_active": true,
     "is_superuser": false,
     "last_login": "2018-09-28T08:34:25.905182+02:00",
     "date_joined": "2018-08-04T17:54:42+02:00",
     "permissions": [
       "ip.get_from_storage_as_new",
       "ip.delete_archived",
       "ip.delete_last_generation",
       "storage.storage_migration",
       "profiles.add_profile",
       "ip.diff-check",
       "tags.create_archive"
     ],
     "user_permissions": [],
     "ip_list_columns": [
       "label",
       "object_identifier_value",
       "start_date",
       "end_date",
       "delete"
     ],
     "ip_list_view_type": "ip",
     "file_browser_view_type": "grid",
     "current_organization": {
       "id": 1,
       "name": "Default",
       "group_type": 1
     },
     "notifications_enabled": true
   }


Session Authentication
==========================

After acquiring a session using, for example, basic authentication, it can be used to authenticate users on subsequent requests using ``rest_framework.authentication.SessionAuthentication``.

.. _HTTP Basic Auth: https://tools.ietf.org/html/rfc7617
