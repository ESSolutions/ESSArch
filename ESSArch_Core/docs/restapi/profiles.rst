=====================
 Profiles
=====================

.. contents::
    :local:

Profiles
--------

API endpoint that allows profiles to be viewed or edited.

.. http:get:: /api/profiles/

.. http:example:: curl

   GET /api/profiles/ HTTP/1.1
   Host: localhost
   Accept: application/json
   Authorization: Basic YWRtaW46YWRtaW4=


   HTTP/1.1 200 OK
   Content-Type: application/json

   [
       {
            "id": "a1f5545e-b732-4785-91ec-2d4b77bac099",
            "profile_type": "aic_description",
            "name": "AIC Description SE",
            "type": "Implementation",
            "status": "Draft",
            "label": "AIC Description profile for SE Packages",
            "schemas": {},
            "representation_info": "Documentation 1",
            "preservation_descriptive_info": "Documentation 2",
            "supplemental": "Documentation 3",
            "access_constraints": "Documentation 4",
            "datamodel_reference": "Documentation 5",
            "cm_release_date": "",
            "cm_change_authority": "",
            "cm_change_description": "",
            "cm_sections_affected": "",
            "cm_version": "",
            "additional": "Documentation 6",
            "submission_method": "Electronically",
            "submission_schedule": "Once",
            "submission_data_inventory": "According to submit description",
            "structure": [],
            "template": [],
            "specification_data": {
                "_PARAMETER_AGENT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_AGENT_IDENTIFIER_VALUE": "ESS",
                "_PARAMETER_EVENT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_LINKING_AGENT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_LINKING_OBJECT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_MEDIUM_LOCATION": "Media_Site-X",
                "_PARAMETER_OBJECT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_RELATED_OBJECT_IDENTIFIER_TYPE": "ESS",
                "_PARAMETER_SITE_NAME": "Site-X",
                "_PATH_ACCESS_WORKAREA": "/ESSArch/data/workspace",
                "_PATH_APPRAISAL_REPORTS": "/ESSArch/data/reports/appraisal",
                "_PATH_CONVERSION_REPORTS": "/ESSArch/data/reports/conversion",
                "_PATH_DISSEMINATIONS": "/ESSArch/data/disseminations",
                "_PATH_INGEST": "/ESSArch/data/ingest/packages",
                "_PATH_INGEST_RECEPTION": "/ESSArch/data/ingest/reception",
                "_PATH_INGEST_UNIDENTIFIED": "/ESSArch/data/ingest/uip",
                "_PATH_INGEST_WORKAREA": "/ESSArch/data/workspace",
                "_PATH_MIMETYPES_DEFINITIONFILE": "/ESSArch/config/mime.types",
                "_PATH_ORDERS": "/ESSArch/data/orders",
                "_PATH_PREINGEST": "/ESSArch/data/preingest/packages",
                "_PATH_PREINGEST_RECEPTION": "/ESSArch/data/preingest/reception",
                "_PATH_TEMP": "/ESSArch/data/temp",
                "_PATH_VERIFY": "/ESSArch/data/verify",
                "PARAMETER_AGENT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_AGENT_IDENTIFIER_VALUE": "ESS",
                "PARAMETER_EVENT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_LINKING_AGENT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_LINKING_OBJECT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_MEDIUM_LOCATION": "Media_Site-X",
                "PARAMETER_OBJECT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_RELATED_OBJECT_IDENTIFIER_TYPE": "ESS",
                "PARAMETER_SITE_NAME": "Site-X",
                "PATH_ACCESS_WORKAREA": "/ESSArch/data/workspace",
                "PATH_APPRAISAL_REPORTS": "/ESSArch/data/reports/appraisal",
                "PATH_CONVERSION_REPORTS": "/ESSArch/data/reports/conversion",
                "PATH_DISSEMINATIONS": "/ESSArch/data/disseminations",
                "PATH_INGEST": "/ESSArch/data/ingest/packages",
                "PATH_INGEST_RECEPTION": "/ESSArch/data/ingest/reception",
                "PATH_INGEST_UNIDENTIFIED": "/ESSArch/data/ingest/uip",
                "PATH_INGEST_WORKAREA": "/ESSArch/data/workspace",
                "PATH_MIMETYPES_DEFINITIONFILE": "/ESSArch/config/mime.types",
                "PATH_ORDERS": "/ESSArch/data/orders",
                "PATH_PREINGEST": "/ESSArch/data/preingest/packages",
                "PATH_PREINGEST_RECEPTION": "/ESSArch/data/preingest/reception",
                "PATH_TEMP": "/ESSArch/data/temp",
                "PATH_VERIFY": "/ESSArch/data/verify"
            }

        }
    ]

.. http:post:: /api/profiles/


