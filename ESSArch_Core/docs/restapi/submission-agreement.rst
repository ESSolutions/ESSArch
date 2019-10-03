=====================
Submission Agreement
=====================

.. contents::
    :local:


API endpoint that allows submission agreements to be viewed or edited.

.. http:get:: /api/submission-agreements/

..  http:example:: curl

   GET /api/submission-agreements/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

    [
        {
            "id": "77799ac6-78f1-4515-9eaa-2801e33de678",
            "name": "SA National Archive and Government SE",
            "published": true,
            "type": "Standard",
            "status": "Agreed",
            "label": "Submission Agreement National Archive x and Government x",
            "archivist_organization": "National Archive xx",
            "include_profile_transfer_project": false,
            "include_profile_content_type": false,
            "include_profile_data_selection": false,
            "include_profile_authority_information": false,
            "include_profile_archival_description": false,
            "include_profile_import": false,
            "include_profile_submit_description": false,
            "include_profile_sip": false,
            "include_profile_aip": false,
            "include_profile_dip": false,
            "include_profile_workflow": false,
            "include_profile_preservation_metadata": false,
            "profile_transfer_project": "b0aaccf6-1ca5-4638-a9cb-a6a25c1f55ab",
            "profile_content_type": null,
            "profile_data_selection": null,
            "profile_authority_information": null,
            "profile_archival_description": null,
            "profile_import": null,
            "profile_submit_description": "248d5437-e5b7-4cf8-b7d1-f84bc7b1f568",
            "profile_sip": "70a7c438-8f8d-44a5-8289-046d5408a2e9",
            "profile_aic_description": "a1f5545e-b732-4785-91ec-2d4b77bac099",
            "profile_aip": "cb823efd-b712-4d60-8e4d-505fdd1c8196",
            "profile_aip_description": "0175a83f-ea5d-427b-be0c-8b31a7920758",
            "profile_dip": "fec6203f-268e-4925-b01a-ff0c190b7f2f",
            "profile_workflow": "04293cfb-e63f-4fa3-ae31-48d789ecdbeb",
            "profile_preservation_metadata": "2da75483-4c87-4529-8ddb-d37a34c5309a",
            "profile_event": null,
            "profile_validation": null,
            "template": [
                {
                    "key": "archivist_organization",
                    "type": "input",
                    "templateOptions": {
                        "type": "text",
                        "required": true,
                        "label": "Archivist Organization"
                    }
                }
            ]
        }
    ]
