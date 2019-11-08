=====================
Events
=====================

.. contents::
    :local:


API endpoint that allows viewing (PREMIS) events

.. http:get:: /api/events/

..  http:example:: curl

   GET /api/events/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "eventType": 10100,
            "eventDateTime": "2019-10-01T01:40:35.367183+02:00",
            "eventDetail": "Prepared IP",
            "eventVersion": "nightlyx-22-gb4ebd72b-dirty",
            "eventOutcome": 0,
            "eventOutcomeDetailNote": "Prepared 4d875a89-8fe2-4636-b407-ec0d4c6b8d2b",
            "linkingAgentIdentifierValue": "superuser",
            "linkingAgentRole": "Producer",
            "information_package": "4d875a89-8fe2-4636-b407-ec0d4c6b8d2b",
            "delivery": null,
            "transfer": null
        },
        {
            "id": 2,
            "eventType": 10200,
            "eventDateTime": "2019-10-01T01:40:35.412664+02:00",
            "eventDetail": "Created IP root directory",
            "eventVersion": "nightlyx-22-gb4ebd72b-dirty",
            "eventOutcome": 0,
            "eventOutcomeDetailNote": "Created IP root directory",
            "linkingAgentIdentifierValue": "superuser",
            "linkingAgentRole": "Producer",
            "information_package": "4d875a89-8fe2-4636-b407-ec0d4c6b8d2b",
            "delivery": null,
            "transfer": null
        }
    ]

Event Types
-----------
API endpoint that allows viewing and editing (PREMIS) event types

.. http:get:: /api/event-types/

..  http:example:: curl

   GET /api/event-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "eventType": 10100,
            "eventDetail": "Prepared IP"
        },
        {
            "eventType": 10200,
            "eventDetail": "Created IP root directory"
        },
        {
            "eventType": 10300,
            "eventDetail": "Created physical model"
        },
        {
            "eventType": 10400,
            "eventDetail": "Created SIP"
        },
        {
            "eventType": 10500,
            "eventDetail": "Submitted SIP"
        }
    ]


.. http:post:: /api/event-types/

    Cretes a new event type

    :param EventType: A repository unique event identifier
    :param EventDetail: A human readable description of the event type
