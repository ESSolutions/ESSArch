=====================
Notifications
=====================

.. contents::
    :local:


API endpoint that allows viewing notifications

.. http:get:: /api/notifications/

..  http:example:: curl

   GET /api/notifications/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 40,
            "user": {
                "id": 2,
                "username": "admin",
                "first_name": "Glenn",
                "last_name": "Grönberg",
                "email": "glenn@example.com",
                "last_login": "2019-09-01T15:42:04.583329+02:00",
                "date_joined": "2019-09-01T01:18:51.803330+02:00"
            },
            "level": "success",
            "message": "8f87b969-9455-45ec-8c21-45c45e619772 is now preserved",
            "time_created": "2019-10-02T22:17:38.728753+02:00",
            "seen": false
        }
    ]
