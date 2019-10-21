=====================
Storage
=====================

.. contents::
    :local:

Storage Object
--------------

API endpoint that allows Storage Objects to be viewed or edited.

.. http:get:: /api/storage-objects/

..  http:example:: curl

   GET /api/storage-objects/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "594db8cc-4af9-4bc2-8f46-e380e509e1aa",
            "content_location_type": 200,
            "content_location_value": "/ESSArch/data/store/cache/6408e64d-5974-4996-91cd-ec3df79e6c14.tar",
            "last_changed_local": "2019-10-01T10:10:10.483139+02:00",
            "last_changed_external": null,
            "ip": "6408e64d-5974-4996-91cd-ec3df79e6c14",
            "medium_id": "Default Cache Storage Target 1",
            "target_name": "Default Cache Storage Target 1",
            "target_target": "/ESSArch/data/store/cache",
            "storage_medium": "3a8400bb-2f33-42fb-8251-fa2f8a777154",
            "container": false
        }
    ]

Storage Medium
--------------

API endpoint that allows Storage Mediums to be viewed or edited.

.. http:get:: /api/storage-mediums/

..  http:example:: curl

   GET /api/storage-mediums/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
                "id": "923b919d-4663-4474-91cc-746cc3aad5a7",
                "medium_id": "Default Storage Target 1",
                "status": 20,
                "status_display": "Write",
                "location": "Media_Site-X",
                "location_status": 50,
                "location_status_display": "Robot",
                "block_size": 1024,
                "format": 103,
                "used_capacity": 2576512,
                "num_of_mounts": 0,
                "create_date": "2019-10-01T02:42:44.325991+02:00",
                "agent": "ESS",
                "storage_target": "46989670-adcc-41e8-bb54-a9f8bec35128",
                "tape_slot": null,
                "tape_drive": null
            },
            {
                "id": "910fa3b6-5c80-47d1-97a5-9195df5eb8dd",
                "medium_id": "Default Long-term Storage Target 1",
                "status": 20,
                "status_display": "Write",
                "location": "Media_Site-X",
                "location_status": 50,
                "location_status_display": "Robot",
                "block_size": 1024,
                "format": 103,
                "used_capacity": 2714650,
                "num_of_mounts": 0,
                "create_date": "2019-10-01T02:42:46.795739+02:00",
                "agent": "ESS",
                "storage_target": "2b8fc4be-7a28-4260-a225-65cd06ab23b7",
                "tape_slot": null,
                "tape_drive": null
            }
        ]


Storage Methods
---------------

API endpoint that allows storage methods to be viewed or edited.

.. http:get:: /api/storage-methods/

..  http:example:: curl

   GET /api/storage-methods/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
                "id": "5e0ebe69-57ad-4034-8c99-c8525039a1d5",
                "name": "Default Long-term Storage Method 1",
                "enabled": true,
                "type": 200,
                "targets": [
                    "2b8fc4be-7a28-4260-a225-65cd06ab23b7"
                ],
                "containers": true,
                "storage_method_target_relations": [
                    {
                        "id": "6a700132-226f-4471-b22a-cd5e6d12711a",
                        "name": "Default Long-term Storage Method Target Relation 1",
                        "status": 1,
                        "storage_target": {
                            "id": "2b8fc4be-7a28-4260-a225-65cd06ab23b7",
                            "name": "Default Long-term Storage Target 1",
                            "status": true,
                            "type": 200,
                            "default_block_size": 1024,
                            "default_format": 103,
                            "min_chunk_size": 0,
                            "min_capacity_warning": 0,
                            "max_capacity": 0,
                            "remote_server": "",
                            "master_server": "",
                            "target": "/ESSArch/data/store/longterm_disk1"
                        },
                        "storage_method": "5e0ebe69-57ad-4034-8c99-c8525039a1d5"
                    }
                ]
            },
            {
                "id": "c7d2b90e-0c54-4a65-b1a1-b09b9faca5f8",
                "name": "Default Storage Method 1",
                "enabled": true,
                "type": 200,
                "targets": [
                    "46989670-adcc-41e8-bb54-a9f8bec35128"
                ],
                "containers": false,
                "storage_method_target_relations": [
                    {
                        "id": "bfefc99f-110a-474c-a910-15983ac93921",
                        "name": "Default Storage Method Target Relation 1",
                        "status": 1,
                        "storage_target": {
                            "id": "46989670-adcc-41e8-bb54-a9f8bec35128",
                            "name": "Default Storage Target 1",
                            "status": true,
                            "type": 200,
                            "default_block_size": 1024,
                            "default_format": 103,
                            "min_chunk_size": 0,
                            "min_capacity_warning": 0,
                            "max_capacity": 0,
                            "remote_server": "",
                            "master_server": "",
                            "target": "/ESSArch/data/store/disk1"
                        },
                        "storage_method": "c7d2b90e-0c54-4a65-b1a1-b09b9faca5f8"
                    }
                ]
            }
        ]


Storage Method Target Relation
------------------------------

API endpoint that allows Storage Method Target Relations to be viewed or edited.

.. http:get:: /api/storage-method-target-relations/

..  http:example:: curl

   GET /api/storage-method-target-relations/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "6a700132-226f-4471-b22a-cd5e6d12711a",
            "name": "Default Long-term Storage Method Target Relation 1",
            "status": 1,
            "storage_target": {
                "id": "2b8fc4be-7a28-4260-a225-65cd06ab23b7",
                "name": "Default Long-term Storage Target 1",
                "status": true,
                "type": 200,
                "default_block_size": 1024,
                "default_format": 103,
                "min_chunk_size": 0,
                "min_capacity_warning": 0,
                "max_capacity": 0,
                "remote_server": "",
                "master_server": "",
                "target": "/ESSArch/data/store/longterm_disk1"
            },
            "storage_method": "5e0ebe69-57ad-4034-8c99-c8525039a1d5"
        },
        {
            "id": "bfefc99f-110a-474c-a910-15983ac93921",
            "name": "Default Storage Method Target Relation 1",
            "status": 1,
            "storage_target": {
                "id": "46989670-adcc-41e8-bb54-a9f8bec35128",
                "name": "Default Storage Target 1",
                "status": true,
                "type": 200,
                "default_block_size": 1024,
                "default_format": 103,
                "min_chunk_size": 0,
                "min_capacity_warning": 0,
                "max_capacity": 0,
                "remote_server": "",
                "master_server": "",
                "target": "/ESSArch/data/store/disk1"
            },
            "storage_method": "c7d2b90e-0c54-4a65-b1a1-b09b9faca5f8"
        }
    ]


Storage Policy
--------------

API endpoint that allows Storage Method Target Relations to be viewed or edited.

.. http:get:: /api/storage-policies/

..  http:example:: curl

   GET /api/storage-policies/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "0804f3d1-c259-4e20-9859-cd1d25022072",
            "index": true,
            "cache_minimum_capacity": 0,
            "cache_maximum_age": 0,
            "policy_id": "1",
            "policy_name": "default",
            "policy_stat": false,
            "ais_project_name": "",
            "ais_project_id": "",
            "mode": 0,
            "wait_for_approval": true,
            "checksum_algorithm": 0,
            "validate_checksum": true,
            "validate_xml": true,
            "ip_type": 1,
            "preingest_metadata": 0,
            "ingest_metadata": 4,
            "information_class": 0,
            "ingest_delete": true,
            "receive_extract_sip": true,
            "cache_storage": {
                "id": "1064f31c-0cc9-4ef3-8e06-20df20d9d047",
                "name": "Default Cache Storage Method",
                "enabled": true,
                "type": 200,
                "targets": [
                    "5b22d837-dcc5-4034-99a3-56634f76d469"
                ],
                "containers": false,
                "storage_method_target_relations": [
                    {
                        "id": "2ec9560c-62d7-43c3-b3be-7b90bab5fe9e",
                        "name": "Default Cache Storage Method Target Relation 1",
                        "status": 1,
                        "storage_target": {
                            "id": "5b22d837-dcc5-4034-99a3-56634f76d469",
                            "name": "Default Cache Storage Target 1",
                            "status": true,
                            "type": 200,
                            "default_block_size": 1024,
                            "default_format": 103,
                            "min_chunk_size": 0,
                            "min_capacity_warning": 0,
                            "max_capacity": 0,
                            "remote_server": "",
                            "master_server": "",
                            "target": "/ESSArch/data/store/cache"
                        },
                        "storage_method": "1064f31c-0cc9-4ef3-8e06-20df20d9d047"
                    }
                ]
            },
            "ingest_path": {
                "id": "ae821b0b-5e8a-426a-9271-046799c5fef3",
                "entity": "ingest",
                "value": "/ESSArch/data/ingest/packages"
            },
            "storage_methods": [
                {
                    "id": "1064f31c-0cc9-4ef3-8e06-20df20d9d047",
                    "name": "Default Cache Storage Method",
                    "enabled": true,
                    "type": 200,
                    "targets": [
                        "5b22d837-dcc5-4034-99a3-56634f76d469"
                    ],
                    "containers": false,
                    "storage_method_target_relations": [
                        {
                            "id": "2ec9560c-62d7-43c3-b3be-7b90bab5fe9e",
                            "name": "Default Cache Storage Method Target Relation 1",
                            "status": 1,
                            "storage_target": {
                                "id": "5b22d837-dcc5-4034-99a3-56634f76d469",
                                "name": "Default Cache Storage Target 1",
                                "status": true,
                                "type": 200,
                                "default_block_size": 1024,
                                "default_format": 103,
                                "min_chunk_size": 0,
                                "min_capacity_warning": 0,
                                "max_capacity": 0,
                                "remote_server": "",
                                "master_server": "",
                                "target": "/ESSArch/data/store/cache"
                            },
                            "storage_method": "1064f31c-0cc9-4ef3-8e06-20df20d9d047"
                        }
                    ]
                },
                {
                    "id": "5e0ebe69-57ad-4034-8c99-c8525039a1d5",
                    "name": "Default Long-term Storage Method 1",
                    "enabled": true,
                    "type": 200,
                    "targets": [
                        "2b8fc4be-7a28-4260-a225-65cd06ab23b7"
                    ],
                    "containers": true,
                    "storage_method_target_relations": [
                        {
                            "id": "6a700132-226f-4471-b22a-cd5e6d12711a",
                            "name": "Default Long-term Storage Method Target Relation 1",
                            "status": 1,
                            "storage_target": {
                                "id": "2b8fc4be-7a28-4260-a225-65cd06ab23b7",
                                "name": "Default Long-term Storage Target 1",
                                "status": true,
                                "type": 200,
                                "default_block_size": 1024,
                                "default_format": 103,
                                "min_chunk_size": 0,
                                "min_capacity_warning": 0,
                                "max_capacity": 0,
                                "remote_server": "",
                                "master_server": "",
                                "target": "/ESSArch/data/store/longterm_disk1"
                            },
                            "storage_method": "5e0ebe69-57ad-4034-8c99-c8525039a1d5"
                        }
                    ]
                },
                {
                    "id": "c7d2b90e-0c54-4a65-b1a1-b09b9faca5f8",
                    "name": "Default Storage Method 1",
                    "enabled": true,
                    "type": 200,
                    "targets": [
                        "46989670-adcc-41e8-bb54-a9f8bec35128"
                    ],
                    "containers": false,
                    "storage_method_target_relations": [
                        {
                            "id": "bfefc99f-110a-474c-a910-15983ac93921",
                            "name": "Default Storage Method Target Relation 1",
                            "status": 1,
                            "storage_target": {
                                "id": "46989670-adcc-41e8-bb54-a9f8bec35128",
                                "name": "Default Storage Target 1",
                                "status": true,
                                "type": 200,
                                "default_block_size": 1024,
                                "default_format": 103,
                                "min_chunk_size": 0,
                                "min_capacity_warning": 0,
                                "max_capacity": 0,
                                "remote_server": "",
                                "master_server": "",
                                "target": "/ESSArch/data/store/disk1"
                            },
                            "storage_method": "c7d2b90e-0c54-4a65-b1a1-b09b9faca5f8"
                        }
                    ]
                }
            ]
        }
    ]



Storage Target
--------------

API endpoint that allows Storage Targets Relations to be viewed or edited.

.. http:get:: /api/storage-targets/

..  http:example:: curl

   GET /api/storage-targets/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "2b8fc4be-7a28-4260-a225-65cd06ab23b7",
            "name": "Default Long-term Storage Target 1",
            "status": true,
            "type": 200,
            "default_block_size": 1024,
            "default_format": 103,
            "min_chunk_size": 0,
            "min_capacity_warning": 0,
            "max_capacity": 0,
            "remote_server": "",
            "master_server": "",
            "target": "/ESSArch/data/store/longterm_disk1"
        },
        {
            "id": "46989670-adcc-41e8-bb54-a9f8bec35128",
            "name": "Default Storage Target 1",
            "status": true,
            "type": 200,
            "default_block_size": 1024,
            "default_format": 103,
            "min_chunk_size": 0,
            "min_capacity_warning": 0,
            "max_capacity": 0,
            "remote_server": "",
            "master_server": "",
            "target": "/ESSArch/data/store/disk1"
        }
    ]


