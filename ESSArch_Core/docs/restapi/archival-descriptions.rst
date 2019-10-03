===============================
Archival description management
===============================

API endpoints for viewing, creation, updating and deleting posts in ESSArchs ARchival description management functionality.

.. contents::
    :local:

Agents
-------
API endpoint that allows authority records (Agents) to be viewed or edited.

.. http:get:: /api/agents/

..  http:example:: curl

   GET /api/agents/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=






Agent Type
----------
API endpoint that allows agent types to be viewed or edited

.. http:get:: /api/agent-types/

..  http:example:: curl

   GET /api/agent-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
        "id": "16510d49-0bfb-4e99-858b-7e891e769ace",
        "main_type": {
            "id": 3,
            "name": "enskild"
        },
        "sub_type": "förening",
        "cpf": "corporatebody"
        }
    ]

.. http:post:: /api/agent-types/

..  http:example:: curl

   POST /api/agent-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 201 Created
   Content-Type: application/json

    {
        "main_type": {
            "name": "enskild"
        },
        "sub_type": "förening",
        "cpf": "corporatebody"
    }


Agent Identifier Type
----------------------
API endpoint that allows agent identifier types to be viewed or edited

.. http:get:: /api/agent-identifier-types/

..  http:example:: curl

   GET /api/agent-identifier-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "orgnr"
        }
    ]

.. http:post:: /api/agent-identifier-types/

Agent Name Types
-----------------

API endpoint that allows agent name types to be viewed or edited

.. http:get:: /api/agent-name-types/

..  http:example:: curl

   GET /api/agent-name-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "auktoriserad",
            "authority": true
        },
        {
            "id": 2,
            "name": "förkortning",
            "authority": false
        }
    ]

.. http:post:: /api/agent-name-types/


Agent Note Types
----------------
API endpoint that allows agent note types to be viewed or edited

.. http:get:: /api/agent-note-types/

..  http:example:: curl

   GET /api/agent-note-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "historik",
            "history": true
        },
        {
            "id": 2,
            "name": "administrativ anmärkning",
            "history": false
        },
        {
            "id": 3,
            "name": "allmän anmärkning",
            "history": false
        }
    ]

.. http:post:: /api/agent-note-types/


Agent Place Type
----------------
API endpoint that allows Agent place types to be viewed or edited.

.. http:get:: /api/agent-place-types/

..  http:example:: curl

   GET /api/agent-place-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "verksamhetsort"
        },
        {
            "id": 2,
            "name": "lokaliseringssort"
        },
        {
            "id": 3,
            "name": "födelseort"
        },
        {
            "id": 4,
            "name": "dödsort"
        }
    ]


.. http:post:: /api/agent-place-types/




Agent Relation Types
--------------------

API endpoint that allows agent relation types to be viewed or edited

.. http:get:: /api/agent-relation-types/

..  http:example:: curl

   GET /api/agent-relation-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "föregångare till",
            "mirrored_type": {
                "id": 2,
                "name": "efterföljare till"
            }
        },
        {
            "id": 2,
            "name": "efterföljare till",
            "mirrored_type": {
                "id": 1,
                "name": "föregångare till"
            }
        }
    ]

.. http:post:: /api/agent-relation-types/

Authority Types
---------------

API endpoint that allows authority types to be viewed or edited

.. http:get:: /api/authority-types/

..  http:example:: curl

   GET /api/authority-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "konstituerande protokoll"
        },
        {
            "id": 2,
            "name": "bolagsordning"
        }
    ]

.. http:post:: /api/authority-types/

Deliveries
----------

API endpoint that allows deliveries to be viewed or edited

.. http:get:: /api/deliveries/

..  http:example:: curl

   GET /api/deliveries/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    {
        "id": 1,
        "name": "Leverans av allmänna handlingar",
        "type": 1,
        "description": "En mängd handlingar",
        "submission_agreement": "77799ac6-78f1-4515-9eaa-2801e33de678",
        "producer_organization": "a3c845cc-e57b-4382-89cd-d0267f965756",
        "reference_code": "dnr 2019/123"
    }

.. http:post:: /api/deliveries/

Delivery Types
--------------

API endpoint that allows delivery types to be viewed or edited

.. http:get:: /api/delivery-types/

..  http:example:: curl

   GET /api/delivery-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "deposition"
        },
        {
            "id": 2,
            "name": "gåva"
        },
        {
            "id": 3,
            "name": "leverans"
        }
    ]

.. http:post:: /api/delivery-types/

Location
--------

API endpoint that allows locations to be viewed or edited

.. http:get:: /api/locations/

..  http:example:: curl

   GET /api/locations/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "name": "Centralarkivet",
            "parent": null,
            "level_type": 1,
            "function": 1,
            "metric": 1,
            "capacity": 100000
        }
    ]


.. http:post:: /api/locations/


Location Level Type
-------------------

API endpoint that allows location level types to be viewed or edited

.. http:get:: /api/location-level-types/

..  http:example:: curl

   GET /api/location-level-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "byggnad"
        },
        {
            "id": 2,
            "name": "våning"
        },
        {
            "id": 3,
            "name": "rum"
        },
        {
            "id": 4,
            "name": "hylla"
        },
        {
            "id": 5,
            "name": "hyllsektion"
        }
    ]

.. http:post:: /api/location-level-types/

Location Function Type
----------------------

API endpoint that allows location function types to be viewed or edited

.. http:get:: /api/location-function-types/

..  http:example:: curl

   GET /api/location-function-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "tills vidare"
        },
        {
            "id": 2,
            "name": "tillfällig"
        }
    ]

.. http:post:: /api/location-function-types/


Language
--------

API endpoint that allows language types to be viewed or edited

.. http:get:: /api/languages/

..  http:example:: curl

   GET /api/languages/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "en",
            "name_en": "English"
        },
        {
            "id": "cv",
            "name_en": "Chuvash"
        },
        {
            "id": "dz",
            "name_en": "Dzongkha"
        }
    ]

.. http:post:: /api/languages/


Metric Type
-----------

API endpoint that allows metric types to be viewed or edited

.. http:get:: /api/metric-types/

..  http:example:: curl

   GET /api/metric-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "meter"
        },
        {
            "id": 2,
            "name": "centimeter"
        },
        {
            "id": 3,
            "name": "millimeter"
        }
    ]

.. http:post:: /api/metric-types/

Node Relation Type
------------------

API endpoint that allows node relation types to be viewed or edited

.. http:get:: /api/node-relation-types/

..  http:example:: curl

   GET /api/node-relation-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "ingår i"
        },
        {
            "id": 2,
            "name": "här i även"
        }
    ]

.. http:post:: /api/node-relation-types/


Node Note Type
--------------

API endpoint that allows node note types to be viewed or edited

.. http:get:: /api/node-note-types/

..  http:example:: curl

   GET /api/node-note-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "historik"
        },
        {
            "id": 2,
            "name": "administrativ anmärkning"
        },
        {
            "id": 3,
            "name": "allmän anmärkning"
        }
    ]

.. http:post:: /api/node-note-types/


Node Relation Type
------------------

API endpoint that allows node relation types to be viewed or edited

.. http:get:: /api/node-relation-types/

..  http:example:: curl

   GET /api/node-relation-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "ingår i"
        },
        {
            "id": 2,
            "name": "här i även"
        }
    ]

.. http:post:: /api/node-relation-types/


Node Identifier Type
--------------------

API endpoint that allows node identifier types to be viewed or edited

.. http:get:: /api/node-identifier-types/

..  http:example:: curl

   GET /api/node-identifier-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "Eget id"
        }
    ]


.. http:post:: /api/node-identifier-types/

Node Note Type
--------------

API endpoint that allows node note types to be viewed or edited

.. http:get:: /api/node-note-types/

..  http:example:: curl

   GET /api/node-note-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "historik"
        },
        {
            "id": 2,
            "name": "administrativ anmärkning"
        },
        {
            "id": 3,
            "name": "allmän anmärkning"
        }
    ]

.. http:post:: /api/node-note-types/

Structures
----------
API endpoint that allows structures to be viewed or edited

.. http:get:: /api/structures/

..  http:example:: curl

   GET /api/structures/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "102974f1-3d4d-4cfc-9d82-946a9c5521b2",
            "name": "Allmänna Arkivschemat",
            "type": {
                "id": 2,
                "name": "förteckningsplan",
                "instance_name": "förteckning",
                "editable_instances": true,
                "movable_instance_units": true,
                "editable_instance_relations": true
            },
            "description": "",
            "template": "3642bdc5-baca-433e-82aa-f68e91e5d75e",
            "is_template": false,
            "version": "1.0",
            "create_date": "2019-10-01T02:23:14.842222+02:00",
            "revise_date": "2019-10-01T02:23:14.842511+02:00",
            "start_date": null,
            "end_date": null,
            "specification": {},
            "rule_convention_type": null,
            "created_by": null,
            "revised_by": null,
            "published": false,
            "published_date": null,
            "related_structures": [],
            "is_editable": true
        }
    ]

.. http:post:: /api/structures/

Structure Units
---------------
API endpoint that allows structure units to be viewed or edited


.. http:get:: /api/structure-units/

..  http:example:: curl

   GET /api/structure-units/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

   [
    {
        "id": 1,
        "parent": null,
        "name": "Protokoll",
        "type": {
            "id": 6,
            "name": "Huvudavdelning",
            "structure_type": {
                "id": 2,
                "name": "förteckningsplan",
                "instance_name": "förteckning",
                "editable_instances": true,
                "movable_instance_units": true,
                "editable_instance_relations": true
            }
        },
        "description": "Huvudavdeling i vilken protokoll förtecknas",
        "reference_code": "A",
        "start_date": null,
        "end_date": null,
        "is_leaf_node": true,
        "is_unit_leaf_node": true,
        "structure": "3642bdc5-baca-433e-82aa-f68e91e5d75e",
        "identifiers": [],
        "notes": [],
        "related_structure_units": [],
        "archive": null
    }
    ]

.. http:post:: /api/structure-units/




Structure Type
--------------

API endpoint that allows structure types to be viewed or edited

.. http:get:: /api/structure-types/

..  http:example:: curl


   GET /api/structure-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 1,
            "name": "klassificeringsstruktur",
            "instance_name": "klassificeringsstruktur",
            "editable_instances": true,
            "movable_instance_units": true,
            "editable_instance_relations": true
        },
        {
            "id": 2,
            "name": "förteckningsplan",
            "instance_name": "förteckning",
            "editable_instances": true,
            "movable_instance_units": true,
            "editable_instance_relations": true
        }
    ]

.. http:post:: /api/structure-types/

   :param name: Name of the structure type
   :param instance_name: Named to be used on instances of a structure
   :param editable_instances: true/false
   :param movable_instance_units: true/false
   :param editable_instance_relations: true/false
   :status 201: Created

Tag
---

API endpoint that allows tags to be viewed or edited

.. http:get:: /api/tags/

..  http:example:: curl

   GET /api/tags/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "cad97d84-93c1-4429-91fc-fd99f78c302a",
            "current_version": {
                "id": "60e6f36a-0da5-4b0e-bc08-70f4e531522d",
                "elastic_index": "component",
                "name": "1",
                "type": 2,
                "create_date": "2019-10-01T10:57:03.360601+02:00",
                "start_date": null,
                "end_date": null
            },
            "other_versions": [],
            "structures": [
                {
                    "id": "73acbd15-5dc0-4cc9-aad8-5b472c4965aa",
                    "parent": "2766e12a-1839-4677-9196-a2bcb2384c28",
                    "structure": {
                        "id": "102974f1-3d4d-4cfc-9d82-946a9c5521b2",
                        "name": "Allmänna Arkivschemat",
                        "type": {
                            "id": 2,
                            "name": "förteckningsplan",
                            "instance_name": "förteckning",
                            "editable_instances": true,
                            "movable_instance_units": true,
                            "editable_instance_relations": true
                        },
                        "description": "",
                        "template": "3642bdc5-baca-433e-82aa-f68e91e5d75e",
                        "is_template": false,
                        "version": "1.0",
                        "create_date": "2019-10-01T02:23:14.842222+02:00",
                        "revise_date": "2019-10-01T02:23:14.842511+02:00",
                        "start_date": null,
                        "end_date": null,
                        "specification": {},
                        "rule_convention_type": null,
                        "created_by": null,
                        "revised_by": null,
                        "published": false,
                        "published_date": null,
                        "related_structures": [],
                        "is_editable": true
                    }
                }
            ]
        },

         {
            "id": "facc5cca-8216-4569-98dc-ba16e9034d2e",
            "current_version": {
                "id": "73dd9294-bb60-4c28-90f8-940bc40dddff",
                "elastic_index": "document",
                "name": "document.pdf",
                "type": 5,
                "create_date": "2019-10-01T10:10:20.235085+02:00",
                "start_date": null,
                "end_date": null
            },
            "other_versions": [],
            "structures": []
        }
    ]

.. http:post:: /api/tags/

.. http:post:: /api/tag-version-types/

   Creates a new tag. Tags are either top-level resources or nodes referenced in a structure instance.

   :status 201: Created


Tag Version Type
----------------

API endpoint that allows tag version types to be viewed or edited

.. http:get:: /api/tag-version-types/

..  http:example:: curl

   GET /api/tag-version-types/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "pk": 1,
            "name": "Arkiv",
            "archive_type": true,
            "information_package_type": false
        },
        {
            "pk": 2,
            "name": "volym",
            "archive_type": false,
            "information_package_type": false
        },
        {
            "pk": 3,
            "name": "AIP",
            "archive_type": false,
            "information_package_type": true
        }
    ]


.. http:post:: /api/tag-version-types/

   Creates a new tag version type

   :param name: Name or title of the tag version type
   :param archive_type: true if type is to be an archive type
   :param information_package_type: true if type is to be a information package type
   :status 201: Created


Ref Code
---------

API endpoint that allows ref codes to be viewed or edited

.. http:get:: /api/ref-codes/

..  http:example:: curl

   GET /api/ref-codes/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "ec8c2a75-c884-4895-a9bd-662dc738f671",
            "country": "SE",
            "repository_code": "GKP"
        }
    ]


.. http:post:: /api/ref-codes/


   Creates a new ref code

   :param country: The id of a country
   :param repository_code: A repository code
   :status 201: Created




Transfers
---------
API endpoint that allows transfers to be viewed or edited

.. http:get:: /api/transfers/

..  http:example:: curl

   GET /api/transfers/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "9fed2da7-90ae-4aba-869f-c9cee34a7314",
            "name": "Digitalt register",
            "delivery": 1,
            "submitter_organization": "Grönköpings kulturnämnd",
            "submitter_organization_main_address": "Gröna gatan 1",
            "submitter_individual_name": "Glenn Grönlund",
            "submitter_individual_phone": "08-123 456",
            "submitter_individual_email": "gronlund@example.com",
            "description": "Överföring av det digitala registret"
        },
        {
            "id": "38cad147-a370-4ba1-81b6-1eff46e9dcf4",
            "name": "Pappersakter",
            "delivery": 1,
            "submitter_organization": "Grönköpings kulturnämnd",
            "submitter_organization_main_address": "Gröna gatan 1",
            "submitter_individual_name": "Glenn Grönlund",
            "submitter_individual_phone": "08-123 456",
            "submitter_individual_email": "gronlund@example.com",
            "description": "Överföring av pappersakter"
        }
    ]


.. http:post:: /api/transfers/

   creates a new transfer

   :param name: The transfers name
   :param delivery: Id of the delivery in Deliveries_
   :param submitter_organization: The organization responsible for the transfer.
   :param submitter_organization_main_address: The address to the organization responsible for the transfer.
   :param submitter_individual_name: The named individual responsible for the transfer
   :param submitter_individual_email: The email to the individual responsible for the transfer
   :param description: A description of the transfer e.g. what is being transferred
   :status 201: Created



