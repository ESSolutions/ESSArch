=====================
Search
=====================

.. contents::
    :local:

API endpoint to make queries and retrieve results

Retrieve results
-----------------


.. http:get:: /api/search

..  http:example:: curl

   GET /api/search/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

   {
    "hits": [
        {
            "_index": "component-20191001011857",
            "_type": "doc",
            "_id": "4656f463-6a74-41bd-ad15-5e6500b97571",
            "_score": 0.0,
            "_source": {
                "structure_units": [
                    {
                        "name": "Kommunstyrelsens protokoll med bilagor",
                        "reference_code": "A1",
                        "id": "121",
                        "structure": {
                            "name": "Allmänna Arkivschemat",
                            "id": "102974f1-3d4d-4cfc-9d82-946a9c5521b2",
                            "type": {
                                "name": "förteckningsplan",
                                "id": "2"
                            }
                        }
                    }
                ],
                "name": " En volym med Protokoll",
                "current_version": true,
                "reference_code": "1",
                "archive": {
                    "name": "Kommunstyrelsens arkiv",
                    "reference_code": "12345",
                    "id": "90128ca4-1842-444f-8a27-59391736d6fc"
                },
                "id": "4656f463-6a74-41bd-ad15-5e6500b97571",
                "type": "volym",
                "desc": "",
            }
            {
                "_index": "document-20191001011859",
                "_type": "doc",
                "_id": "746b511c-11a3-49ae-acd3-08180e9fb657",
                "_score": 0.0,
                "_source": {
                    "extension": "xsd",
                    "filename": "premis.xsd",
                    "size": 52845,
                    "attachment": {
                        "content_type": "application/xml",
                        "language": "lt",
                        "content_length": 4472
                    },
                    "ip": "2d9172db-a660-478d-919b-b07228fe5786",
                    "name": "premis.xsd",
                    "current_version": true,
                    "modified": "2019-09-01T02:40:28+02:00",
                    "href": "content/2d9172db-a660-478d-919b-b07228fe5786/metadata",
                    "type": "document"
                }
            },
        {
            "_index": "document-20191001011859",
            "_type": "doc",
            "_id": "f3b1ed2a-b2b3-44a9-94b1-a71d78609487",
            "_score": 0.0,
            "_source": {
                "extension": "pdf",
                "filename": "filnamn.pdf",
                "size": 3180,
                "attachment": {
                    "content_type": "application/pdf",
                    "language": "lt",
                    "content_length": 386
                },
                "ip": "2d9172db-a660-478d-919b-b07228fe5786",
                "name": "xlink.xsd",
                "current_version": true,
                "modified": "2019-09-01T02:40:28+02:00",
                "href": "content/2d9172db-a660-478d-919b-b07228fe5786/metadata",
                "type": "document"
            }
        ]
    }


Filters
--------
The most commonly used filters used by ESSArch to retrieve objects.


.. http:get:: /api/search/<uuid>

Retrieves one single indexed object


.. http:get:: /api/search/indices=<index>,<index>

Retrieves objects from a particular index


.. http:get:: /api/search/extension=<extension>,<extension>

Retrieves objects filtered by extensions e.g. xml, pdf, docx etc


.. http:get:: /api/search/type=<type>

Retrieves objects filtered by type e.g. box, document, image, folder etc


.. http:get:: /api/search/agents=<agent id>,<agent id>

Retrieves results from one or more authority record


.. http:get:: /api/agents/archives=<archive id>,<archive id>

Retrieves results from one or more top-level resources (Fonds/Archives)


Combining filters
-----------------
One or more filters can be combined in a query by adding a **&** between filters.

.. http:get:: /api/agents/archives=<archive id>&extension=pdf%q=meeting minutes

The above query would retrieve all pdf documents containing the phrase "meeting minutes" from a particular
top-level resource (Fond/Archive)


Stored Search
--------------

Api endpoint that allows stored searches to be viewed or edited

.. http:get:: /api/me/searches/

Retrieves the stored searches for the logged in user

..  http:example:: curl

   GET /api/me/searches/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": 2,
            "name": "My saved search",
            "user": "superuser",
            "query": {
                "q": "protokoll",
                "type": [
                    {
                        "key": "document",
                        "doc_count": 3,
                        "text": "document (3)",
                        "a_attr": {
                            "title": "document"
                        },
                        "state": {
                            "opened": true,
                            "selected": false
                        },
                        "type": "document",
                        "children": []
                    }
                ],
                "page": 1,
                "page_size": 25,
                "extension": {},
                "archives": [
                    {
                        "id": "90128ca4-1842-444f-8a27-59391736d6fc",
                        "elastic_index": "archive",
                        "name": "Kommunstyrelsens arkiv",
                        "type": 1,
                        "create_date": "2019-09-01T02:23:14.832757+02:00",
                        "start_date": "1980-01-01T00:00:00+01:00",
                        "end_date": null
                    }
                ]
            }
        }
    ]

.. http:post:: /me/searches/

   Stores a search for the logged in user

   :param name: The stored search name
   :param query: The query to be stored
