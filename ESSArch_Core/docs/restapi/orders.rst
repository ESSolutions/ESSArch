=====================
Orders
=====================

.. contents::
    :local:

Orders
------

API endpoint that allows orders to be viewed or edited.

.. http:get:: /api/orders/

..  http:example:: curl

   GET /api/orders/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "929c7870-732f-4a53-a738-59e4d0cf0f93",
            "label": "Min beställning",
            "responsible": {
                "id": 6,
                "username": "Glenn",
                "first_name": "Glenn",
                "last_name": "Grönberg",
                "email": "glenn@example.com",
                "last_login": "2019-10-01T10:59:36.571284+02:00",
                "date_joined": "2019-10-01T02:07:49+02:00"
            },
            "information_packages": [
                "http://127.0.0.1:8000/api/information-packages/b8c50228-890b-45fb-a705-7cf16de5d55c/"
            ]
        }
    ]

.. http:post:: /api/orders/

   creates a new order

   :param name: A label for the order
   :param responsible: The user responsible for the order
   :param information_packages: IP's included in the order
