from ESSArch_Core.profiles.models import SubmissionAgreement


def create_mets_spec(outer: bool, sa: SubmissionAgreement):
    return {
        "-name": "mets",
        "-namespace": "mets",
        "-nsmap": {
            "mets": "http://www.loc.gov/METS/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xlink": "http://www.w3.org/1999/xlink"
        },
        "-attr": [
            {
                "-name": "schemaLocation",
                "-namespace": "xsi",
                "#content": "http://www.loc.gov/METS/ "
                            "http://example.com/mets.xsd"
            },
            {
                "-name": "ID",
                "#content": "ID{% uuid4 %}"
            },
            {
                "-name": "OBJID",
                "#content": "UUID:{{OBJID}}"
            },
            {
                "-name": "TYPE",
                "#content": "SIP"
            },
            {
                "-name": "PROFILE",
                "#content": "http://example.com"
            }
        ],
        "-children": [
            {
                "-name": "metsHdr",
                "-namespace": "mets",
                "-attr": [
                    {
                        "-name": "CREATEDATE",
                        "#content": "{% now 'c' %}"
                    }
                ],
                "-children": [
                    {
                        "-name": "agent",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "ROLE",
                                "#content": "CREATOR"
                            },
                            {
                                "-name": "TYPE",
                                "#content": "ORGANIZATION"
                            }
                        ],
                        "-children": [
                            {
                                "-name": "name",
                                "-namespace": "mets",
                                "#content": "creator"
                            }
                        ]
                    },
                    {
                        "-name": "agent",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "ROLE",
                                "#content": "OTHER"
                            },
                            {
                                "-name": "OTHERROLE",
                                "#content": "SUBMITTER"
                            },
                            {
                                "-name": "TYPE",
                                "#content": "ORGANIZATION"
                            }
                        ],
                        "-children": [
                            {
                                "-name": "name",
                                "-namespace": "mets",
                                "#content": "submitter_organization"
                            }
                        ]
                    },
                    {
                        "-name": "agent",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "ROLE",
                                "#content": "OTHER"
                            },
                            {
                                "-name": "OTHERROLE",
                                "#content": "SUBMITTER"
                            },
                            {
                                "-name": "TYPE",
                                "#content": "INDIVIDUAL"
                            }
                        ],
                        "-children": [
                            {
                                "-name": "name",
                                "-namespace": "mets",
                                "#content": "submitter_individual"
                            }
                        ]
                    },
                    {
                        "-name": "altRecordID",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "TYPE",
                                "#content": "SUBMISSIONAGREEMENT"
                            }
                        ],
                        "#content": str(sa.pk)
                    },
                    {
                        "-name": "altRecordID",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "TYPE",
                                "#content": "STARTDATE"
                            }
                        ],
                        "#content": "2020-01-01 00:00:00+00:00"
                    },
                    {
                        "-name": "altRecordID",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "TYPE",
                                "#content": "ENDDATE"
                            }
                        ],
                        "#content": "2020-12-31 00:00:00+00:00"
                    },
                ]
            },
            {
                "-name": "fileSec",
                "-namespace": "mets",
                "-attr": [
                    {
                        "-name": "ID",
                        "#content": "ID{{UUID}}"
                    }
                ],
                "-children": [
                    {
                        "-name": "fileGrp",
                        "-namespace": "mets",
                        "-children": [
                            {
                                "-name": "file",
                                "-namespace": "mets",
                                "-containsFiles": True,
                                "-filters": {"href": r".+\.tar$"} if outer else {},
                                "-attr": [
                                    {
                                        "-name": "ID",
                                        "#content": "ID{{FID}}"
                                    },
                                    {
                                        "-name": "MIMETYPE",
                                        "#content": "{{FMimetype}}"
                                    },
                                    {
                                        "-name": "SIZE",
                                        "#content": "{{FSize}}"
                                    },
                                    {
                                        "-name": "USE",
                                        "#content": "{{FUse}}"
                                    },
                                    {
                                        "-name": "CREATED",
                                        "#content": "{{FCreated}}"
                                    },
                                    {
                                        "-name": "CHECKSUM",
                                        "#content": "{{FChecksum}}"
                                    },
                                    {
                                        "-name": "CHECKSUMTYPE",
                                        "#content": "{{FChecksumType}}"
                                    }
                                ],
                                "-children": [
                                    {
                                        "-name": "FLocat",
                                        "-namespace": "mets",
                                        "-attr": [
                                            {
                                                "-name": "LOCTYPE",
                                                "#content": "URL"
                                            },
                                            {
                                                "-name": "href",
                                                "-namespace": "xlink",
                                                "#content": "file:///{{href}}"
                                            },
                                            {
                                                "-name": "type",
                                                "-namespace": "xlink",
                                                "#content": "simple"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "-name": "structMap",
                "-namespace": "mets",
                "-children": [
                    {
                        "-name": "div",
                        "-namespace": "mets",
                        "-attr": [
                            {
                                "-name": "LABEL",
                                "#content": "Package"
                            }
                        ],
                        "-children": [
                            {
                                "-name": "div",
                                "-namespace": "mets",
                                "-attr": [
                                    {
                                        "-name": "LABEL",
                                        "#content": "Datafiles"
                                    }
                                ],
                                "-children": [
                                    {
                                        "-name": "fptr",
                                        "-namespace": "mets",
                                        "-containsFiles": True,
                                        "-attr": [
                                            {
                                                "-name": "FILEID",
                                                "#content": "ID{{FID}}"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


def create_premis_spec(sa: SubmissionAgreement):
    return {
        "-name": "premis",
        "-namespace": "premis",
        "-nsmap": {
            "premis": "http://www.loc.gov/premis/v3",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance"
        },
        "-attr": [
            {
                "-name": "version",
                "#content": "3.0"
            },
            {
                "-name": "schemaLocation",
                "-namespace": "xsi",
                "#content": "http://www.loc.gov/premis/v3 "
                            "http://example.com/premis.xsd"
            }
        ],
        "-children": [
            {
                "-name": "object",
                "-namespace": "premis",
                "-containsFiles": True,
                "-attr": [
                    {
                        "-name": "type",
                        "-namespace": "xsi",
                        "#content": "premis:file"
                    }
                ],
                "-children": [
                    {
                        "-name": "objectIdentifier",
                        "-namespace": "premis",
                        "-children": [
                            {
                                "-name": "objectIdentifierType",
                                "-namespace": "premis",
                                "#content": "ESS"
                            },
                            {
                                "-name": "objectIdentifierValue",
                                "-namespace": "premis",
                                "#content": "{{OBJID}}/{{href}}"
                            }
                        ]
                    },
                    {
                        "-name": "objectCharacteristics",
                        "-namespace": "premis",
                        "-children": [
                            {
                                "-name": "compositionLevel",
                                "-namespace": "premis",
                                "#content": [{"var": "composition_level", "default": 0}]
                            },
                            {
                                "-name": "fixity",
                                "-namespace": "premis",
                                "-children": [
                                    {
                                        "-name": "messageDigestAlgorithm",
                                        "-namespace": "premis",
                                        "#content": [{"var": "FChecksumType"}]
                                    },
                                    {
                                        "-name": "messageDigest",
                                        "-namespace": "premis",
                                        "#content": [{"var": "FChecksum"}]
                                    },
                                    {
                                        "-name": "messageDigestOriginator",
                                        "-namespace": "premis",
                                        "#content": [{"var": "FChecksumLib"}]
                                    }
                                ]
                            },
                            {
                                "-name": "size",
                                "-namespace": "premis",
                                "#content": [{"var": "FSize"}]
                            },
                            {
                                "-name": "format",
                                "-namespace": "premis",
                                "-children": [
                                    {
                                        "-name": "formatDesignation",
                                        "-namespace": "premis",
                                        "-children": [
                                            {
                                                "-name": "formatName",
                                                "-namespace": "premis",
                                                "#content": [{"var": "FFormatName"}]
                                            },
                                            {
                                                "-name": "formatVersion",
                                                "-namespace": "premis",
                                                "#content": [{"var": "FFormatVersion"}]
                                            }
                                        ]
                                    },
                                    {
                                        "-name": "formatRegistry",
                                        "-namespace": "premis",
                                        "-requiredParameters": ["FFormatRegistryKey"],
                                        "-children": [
                                            {
                                                "-name": "formatRegistryName",
                                                "-namespace": "premis",
                                                "#content": [{"text": "PRONOM"}]
                                            },
                                            {
                                                "-name": "formatRegistryKey",
                                                "-namespace": "premis",
                                                "#content": [{"var": "FFormatRegistryKey"}]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "-name": "storage",
                        "-namespace": "premis",
                        "-children": [
                            {
                                "-name": "contentLocation",
                                "-namespace": "premis",
                                "-children": [
                                    {
                                        "-name": "contentLocationType",
                                        "-namespace": "premis",
                                        "#content": "200"
                                    },
                                    {
                                        "-name": "contentLocationValue",
                                        "-namespace": "premis",
                                        "#content": [{"var": "_OBJID"}]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
