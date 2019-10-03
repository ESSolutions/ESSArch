=====================
 Information Packages
=====================

.. contents::
    :local:

.. http:get:: /information-packages/

    The information packages visible to the logged in user

..  http:example:: curl

   GET /api/information-packages/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "968a202b-5c66-4f40-ae0e-6acbb75ce8a6",
            "label": "IP 001",
            "object_identifier_value": "968a202b-5c66-4f40-ae0e-6acbb75ce8a6",
            "package_type": 1,
            "package_type_display": "AIC",
            "responsible": {
                "id": 2,
                "username": "superuser",
                "first_name": "superuser",
                "last_name": "Lastname",
                "email": "superuser@essolutions.se",
                "last_login": "2019-09-01T15:42:04.583329+02:00",
                "date_joined": "2019-09-01T01:18:51.803330+02:00"
            },
            "create_date": "2019-09-02T22:15:35.506997+02:00",
            "entry_date": null,
            "state": "",
            "status": 100,
            "step_state": "SUCCESS",
            "archived": false,
            "cached": false,
            "aic": null,
            "information_packages": [
                {
                    "id": "8f87b969-9455-45ec-8c21-45c45e619772",
                    "label": "IP 001",
                    "object_identifier_value": "8f87b969-9455-45ec-8c21-45c45e619772",
                    "object_size": 394467,
                    "object_path": "/ESSArch/data/ingest/packages/8f87b969-9455-45ec-8c21-45c45e619772",
                    "submission_agreement": "77799ac6-78f1-4515-9eaa-2801e33de678",
                    "submission_agreement_locked": true,
                    "package_type": 2,
                    "package_type_display": "AIP",
                    "responsible": {
                        "id": 2,
                        "username": "superuser",
                        "first_name": "superuser",
                        "last_name": "Lastname",
                        "email": "superuser@essolutions.se",
                        "last_login": "2019-10-01T15:42:04.583329+02:00",
                        "date_joined": "2019-10-01T01:18:51.803330+02:00"
                    },
                    "create_date": "2019-09-02T22:11:03.386016+02:00",
                    "object_num_items": 10,
                    "entry_date": "2019-09-02T22:12:11.487692+02:00",
                    "state": "Preserved",
                    "status": 100.0,
                    "step_state": "SUCCESS",
                    "archived": true,
                    "cached": false,
                    "aic": "968a202b-5c66-4f40-ae0e-6acbb75ce8a6",
                    "generation": 0,
                    "agents": {
                        "ARCHIVIST_ORGANIZATION": {
                            "id": 1,
                            "role": "ARCHIVIST",
                            "type": "ORGANIZATION",
                            "name": "National Archive xx",
                            "code": "",
                            "notes": []
                        },
                        "CREATOR_ORGANIZATION": {
                            "id": 2,
                            "role": "CREATOR",
                            "type": "ORGANIZATION",
                            "name": "the creator",
                            "code": "",
                            "notes": []
                        },
                        "SUBMITTER_ORGANIZATION": {
                            "id": 3,
                            "role": "SUBMITTER",
                            "type": "ORGANIZATION",
                            "name": "the submitter organization",
                            "code": "",
                            "notes": []
                        },
                        "SUBMITTER_INDIVIDUAL": {
                            "id": 4,
                            "role": "SUBMITTER",
                            "type": "INDIVIDUAL",
                            "name": "the submitter individual",
                            "code": "",
                            "notes": []
                        },
                        "PRODUCER_ORGANIZATION": {
                            "id": 5,
                            "role": "PRODUCER",
                            "type": "ORGANIZATION",
                            "name": "the producer organization",
                            "code": "",
                            "notes": []
                        },
                        "PRODUCER_INDIVIDUAL": {
                            "id": 6,
                            "role": "PRODUCER",
                            "type": "INDIVIDUAL",
                            "name": "the producer individual",
                            "code": "",
                            "notes": []
                        },
                        "IPOWNER_ORGANIZATION": {
                            "id": 7,
                            "role": "IPOWNER",
                            "type": "ORGANIZATION",
                            "name": "the ip owner",
                            "code": "",
                            "notes": []
                        },
                        "PRESERVATION_ORGANIZATION": {
                            "id": 8,
                            "role": "PRESERVATION",
                            "type": "ORGANIZATION",
                            "name": "the preservation organization",
                            "code": "",
                            "notes": []
                        },
                        "ARCHIVIST_SOFTWARE": {
                            "id": 9,
                            "role": "ARCHIVIST",
                            "type": "SOFTWARE",
                            "name": "the system name",
                            "code": "",
                            "notes": [
                                {
                                    "id": 2,
                                    "note": "the system type"
                                },
                                {
                                    "id": 1,
                                    "note": "the system version"
                                }
                            ]
                        }
                    },
                    "policy": "0804f3d1-c259-4e20-9859-cd1d25022072",
                    "message_digest": "",
                    "message_digest_algorithm": null,
                    "content_mets_create_date": "2019-09-02T22:15:39.025062+02:00",
                    "content_mets_size": 7766,
                    "content_mets_digest_algorithm": 3,
                    "content_mets_digest": "39843dab5d59bb616c3e3def2206d1c9fb97fc3795a9cba053db2e15c76b1c59",
                    "package_mets_create_date": "2019-10-02T22:17:36.347231+02:00",
                    "package_mets_size": 4000,
                    "package_mets_digest_algorithm": 3,
                    "package_mets_digest": "0b74182111e3ea118af910e666eb53a3af7ab535671fe5921e22e152b01afbd6",
                    "start_date": "2016-11-10T00:00:00+01:00",
                    "end_date": "2016-12-20T00:00:00+01:00",
                    "permissions": [
                        "preserve",
                        "add_to_ingest_workarea_as_tar",
                        "get_tar_from_storage",
                        "delete_informationpackage",
                        "preserve_dip",
                        "view_informationpackage",
                        "submit_sip",
                        "add_to_ingest_workarea",
                        "get_from_storage_as_new",
                        "see_other_user_ip_files",
                        "delete_first_generation",
                        "get_from_storage",
                        "lock_sa",
                        "query",
                        "add_informationpackage",
                        "see_all_in_workspaces",
                        "can_receive_remote_files",
                        "delete_last_generation",
                        "receive",
                        "create_sip",
                        "set_uploaded",
                        "change_sa",
                        "unlock_profile",
                        "diff-check",
                        "prepare_ip",
                        "delete_archived",
                        "add_to_ingest_workarea_as_new",
                        "change_informationpackage",
                        "transfer_sip",
                        "can_upload"
                    ],
                    "appraisal_date": null,
                    "workarea": [],
                    "first_generation": true,
                    "last_generation": true,
                    "organization": {
                        "id": 1,
                        "name": "Default",
                        "group_type": 1
                    },
                    "profile_Transfer Project": null,
                    "profile_Content Type": null,
                    "profile_Data Selection": null,
                    "profile_Authority Information": null,
                    "profile_Archival Description": null,
                    "profile_Import": null,
                    "profile_Submit Description": null,
                    "profile_SIP": null,
                    "profile_AIC Description": null,
                    "profile_AIP": null,
                    "profile_AIP Description": null,
                    "profile_DIP": null,
                    "profile_Workflow": null,
                    "profile_Preservation Metadata": null,
                    "profile_Event": null,
                    "profile_Validation": null,
                    "profile_aic_description": {
                        "id": "1daf25f4-1b65-4b20-b064-0dc17e8e0bb9",
                        "profile": "a1f5545e-b732-4785-91ec-2d4b77bac099",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "AIC Description SE",
                        "profile_type": "aic_description",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "01acbbaa-ed1b-40c9-999d-85dc3bcb9939"
                        ]
                    },
                    "profile_aip": {
                        "id": "211dbe2c-200b-4326-8f46-822a9f3c993e",
                        "profile": "cb823efd-b712-4d60-8e4d-505fdd1c8196",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "AIP SE",
                        "profile_type": "aip",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "2456d3f5-1f2a-4096-9e6d-5ba118207ce3"
                        ]
                    },
                    "profile_aip_description": {
                        "id": "7c4aaeb6-5f67-47f8-a522-be42a312cd15",
                        "profile": "0175a83f-ea5d-427b-be0c-8b31a7920758",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "AIP Description SE",
                        "profile_type": "aip_description",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "f48b8611-e22f-4232-bda0-290c329cd88a"
                        ]
                    },
                    "profile_dip": {
                        "id": "d61cf0b1-cf74-4294-a77a-915a24d6fdf5",
                        "profile": "fec6203f-268e-4925-b01a-ff0c190b7f2f",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "DIP SE",
                        "profile_type": "dip",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "5d7e7689-52c4-4218-8375-26815ba7cc4c"
                        ]
                    },
                    "profile_workflow": {
                        "id": "5eb12e32-baf1-4427-b9fb-7d8d91e8031b",
                        "profile": "04293cfb-e63f-4fa3-ae31-48d789ecdbeb",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "Workflow SE",
                        "profile_type": "workflow",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "7da4d001-c5ec-48ae-81ee-c6e74b3f13e8"
                        ]
                    },
                    "profile_transfer_project": {
                        "id": "c2b46f5f-a2d0-4843-b3c7-728471fe3a28",
                        "profile": "b0aaccf6-1ca5-4638-a9cb-a6a25c1f55ab",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "Transfer Project Profile SE",
                        "profile_type": "transfer_project",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "302575dc-7d0c-4bcb-a758-86a86316a8e2"
                        ]
                    },
                    "profile_submit_description": {
                        "id": "0d998530-4c9b-419d-8c05-cde6082799ba",
                        "profile": "248d5437-e5b7-4cf8-b7d1-f84bc7b1f568",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "Submit description of a single SIP SE",
                        "profile_type": "submit_description",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "ce041501-0f27-4702-a739-9a7b9890b207"
                        ]
                    },
                    "profile_sip": {
                        "id": "f3329082-e1f9-4942-8b9c-a68c6acaca90",
                        "profile": "70a7c438-8f8d-44a5-8289-046d5408a2e9",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "SIP SE",
                        "profile_type": "sip",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "2e74206d-22e0-4ee8-90af-d9acae905f63"
                        ]
                    },
                    "profile_preservation_metadata": {
                        "id": "1e27c806-0090-490f-acf1-a441545d721f",
                        "profile": "2da75483-4c87-4529-8ddb-d37a34c5309a",
                        "ip": "8f87b969-9455-45ec-8c21-45c45e619772",
                        "profile_name": "Preservation profile SE",
                        "profile_type": "preservation_metadata",
                        "included": false,
                        "LockedBy": 2,
                        "Unlockable": false,
                        "data_versions": [
                            "78c13139-31b4-4442-a33b-dd48f4ef5b13"
                        ]
                    }
                }
            ],
            "generation": null,
            "policy": null,
            "message_digest": "",
            "agents": {},
            "message_digest_algorithm": null,
            "submission_agreement": null,
            "object_path": "",
            "submission_agreement_locked": false,
            "workarea": [],
            "object_size": 0,
            "first_generation": true,
            "last_generation": true,
            "start_date": "2016-11-10T00:00:00+01:00",
            "end_date": "2016-12-20T00:00:00+01:00",
            "new_version_in_progress": null,
            "appraisal_date": null,
            "permissions": [
                "preserve",
                "add_to_ingest_workarea_as_tar",
                "get_tar_from_storage",
                "delete_informationpackage",
                "preserve_dip",
                "view_informationpackage",
                "submit_sip",
                "add_to_ingest_workarea",
                "get_from_storage_as_new",
                "see_other_user_ip_files",
                "delete_first_generation",
                "get_from_storage",
                "lock_sa",
                "query",
                "add_informationpackage",
                "see_all_in_workspaces",
                "can_receive_remote_files",
                "delete_last_generation",
                "receive",
                "create_sip",
                "set_uploaded",
                "change_sa",
                "unlock_profile",
                "diff-check",
                "prepare_ip",
                "delete_archived",
                "add_to_ingest_workarea_as_new",
                "change_informationpackage",
                "transfer_sip",
                "can_upload"
            ],
            "organization": null
        }
    ]
