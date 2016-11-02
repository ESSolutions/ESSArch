"""
    ESSArch Tools - ESSArch is an Electronic Preservation Platform
    Copyright (C) 2005-2016  ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

# Create your models here.
from collections import OrderedDict

from django.conf import settings
from django.db import models

from ESSArch_Core.configuration.models import (
    EventType, Path,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep, ProcessTask,
)

from ESSArch_Core.profiles.models import (
    ProfileLock, SubmissionAgreement as SA
)

from ESSArch_Core.util import (
    create_event,
)

import json, os, uuid


class ArchivalInstitution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalInstitution'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivistOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivistOrganization'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalType'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalLocation'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class InformationPackage(models.Model):
    """
    Informaion Package
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    Label = models.CharField(max_length=255)
    Content = models.CharField(max_length=255)
    Responsible = models.CharField(max_length=255)
    CreateDate = models.DateTimeField(auto_now_add=True)
    State = models.CharField(max_length=255)
    ObjectSize = models.CharField(max_length=255)
    ObjectNumItems = models.CharField(max_length=255)
    ObjectPath = models.CharField(max_length=255)
    Startdate = models.DateTimeField(null=True)
    Enddate = models.DateTimeField(null=True)
    OAIStype = models.CharField(max_length=255)
    SubmissionAgreement = models.ForeignKey(
        SA,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True,
    )
    ArchivalInstitution = models.ForeignKey(
        ArchivalInstitution,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivistOrganization = models.ForeignKey(
        ArchivistOrganization,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivalType = models.ForeignKey(
        ArchivalType,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivalLocation = models.ForeignKey(
        ArchivalLocation,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )

    def create(self):
        event_type = EventType.objects.get(eventType=10200)

        create_event(event_type, [], "System", self)

        prepare_path = Path.objects.get(
            entity="path_preingest_prepare"
        ).value

        ip_prepare_path = os.path.join(prepare_path, str(self.pk))
        sa = self.SubmissionAgreement

        schemas = sa.profile_transfer_project_rel.active().schemas
        structure = sa.profile_sip_rel.active().structure

        copy_schemas_step = ProcessStep.objects.create(
            name="Copy schemas",
        )

        for schema in schemas:
            copy_schemas_step.tasks.add(
                ProcessTask.objects.create(
                    name="preingest.tasks.CopySchemas",
                    params={
                        "schema": schema,
                        "root": ip_prepare_path,
                        "structure": structure,
                    },
                    processstep_pos=0,
                    information_package=self
                )
            )

        copy_schemas_step.save()

        info = sa.profile_event_rel.active().specification_data

        events_path = os.path.join(ip_prepare_path, "ipevents.xml")
        filesToCreate = OrderedDict()
        filesToCreate[events_path] = sa.profile_event_rel.active().specification

        t0 = ProcessTask.objects.create(
            name="preingest.tasks.GenerateXML",
            params={
                "info": info,
                "filesToCreate": filesToCreate,
            },
            processstep_pos=0,
            information_package=self
        )

        t01 = ProcessTask.objects.create(
            name="preingest.tasks.AppendEvents",
            params={
                "filename": events_path,
                "events": self.events.all(),
            },
            processstep_pos=0,
            information_package=self
        )

        spec = {
            "-name": "object",
            "-namespace": "premis",
            "-children": [
                {
                    "-name": "objectIdentifier",
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "objectIdentifierType",
                            "-namespace": "premis",
                            "#content": [{"var": "FIDType"}],
                            "-children": []
                        },
                        {
                            "-name": "objectIdentifierValue",
                            "-namespace": "premis",
                            "#content": [{"text":"ID"},{"var": "FID"}],
                            "-children": []
                        }
                    ]
                },
                {
                    "-name": "objectCharacteristics",
                    "-namespace": "premis",
                    "-children": [
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
                                            "#content": [{"var": "FFormatName"}],
                                            "-children": []
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
                                    "#content": [{"var": "FLocationType"}],
                                    "-children": []
                                },
                                {
                                    "-name": "contentLocationValue",
                                    "-namespace": "premis",
                                    "#content": [{"text": "file:///"},{"var": "FName"}],
                                    "-children": []
                                }
                            ]
                        }
                    ]
                }
            ],
            "-attr": [
                {
                  "-name": "type",
                  '-namespace': 'xsi',
                  "-req": "1",
                  "#content": [{"text":"premis:file"}]
                }
            ],
        }

        info = {
            'FIDType': "UUID",
            'FID': "ID%s" % str(self.pk),
            'FFormatName': 'TAR',
            'FLocationType': 'URI',
            'FName': self.ObjectPath,
        }

        t02 = ProcessTask.objects.create(
            name="preingest.tasks.InsertXML",
            params={
                "filename": events_path,
                "elementToAppendTo": "premis",
                "spec": spec,
                "info": info,
                "index": 0
            },
            processstep_pos=0,
            information_package=self
        )

        info = sa.profile_sip_rel.active().specification_data

        # ensure premis is created before mets
        filesToCreate = OrderedDict()

        premis_profile = sa.profile_preservation_metadata_rel.active()
        if premis_profile.locked(sa, self):
            premis_path = os.path.join(ip_prepare_path, "premis.xml")
            filesToCreate[premis_path] = sa.profile_preservation_metadata_rel.active().specification

        mets_path = os.path.join(ip_prepare_path, "mets.xml")
        filesToCreate[mets_path] = sa.profile_sip_rel.active().specification

        t1 = ProcessTask.objects.create(
            name="preingest.tasks.GenerateXML",
            params={
                "info": info,
                "filesToCreate": filesToCreate,
                "folderToParse": ip_prepare_path
            },
            processstep_pos=0,
            information_package=self
        )

        generate_xml_step = ProcessStep.objects.create(
            name="Generate XML",
        )
        generate_xml_step.tasks = [t0, t01, t02, t1]
        generate_xml_step.save()

        filename = "foo.csv"
        fileformat = "Comma Seperated Spreadsheet"
        xmlfile = "premis.xml"
        schemafile = "premis.xsd"
        logical = "logical"
        physical = "physical"
        checksum = uuid.uuid4()
        #dirname = os.path.join(ip_prepare_path, "data")
        tarname = os.path.join(ip_prepare_path) + '.tar'
        zipname = os.path.join(ip_prepare_path) + '.zip'

        validate_step = ProcessStep.objects.create(
            name="Validation",
        )

        validate_step.tasks.add(
            ProcessTask.objects.create(
                name="preingest.tasks.ValidateXMLFile",
                params={
                    "xml_filename": events_path,
                },
                processstep_pos=0,
                information_package=self
            )
        )

        validate_step.tasks.add(
            ProcessTask.objects.create(
                name="preingest.tasks.ValidateXMLFile",
                params={
                    "xml_filename": mets_path,
                },
                processstep_pos=0,
                information_package=self
            )
        )

        if premis_profile.locked(sa, self):
            validate_step.tasks.add(
                ProcessTask.objects.create(
                    name="preingest.tasks.ValidateXMLFile",
                    params={
                        "xml_filename": premis_path,
                    },
                    processstep_pos=0,
                    information_package=self
                )
            )

        validate_step.tasks.add(
            ProcessTask.objects.create(
                name="preingest.tasks.ValidateLogicalPhysicalRepresentation",
                params={
                    "mets_path": mets_path,
                    "ip": self
                },
                processstep_pos=0,
                information_package=self
            )
        )

        validate_step.tasks.add(
            ProcessTask.objects.create(
                name="preingest.tasks.ValidateFiles",
                params={
                    "ip": self,
                    "mets_path": mets_path,
                },
                processstep_pos=0,
                information_package=self
            )
        )

        validate_step.save()

        t6 = ProcessTask.objects.create(
            name="preingest.tasks.CreateTAR",
            params={
                "dirname": ip_prepare_path,
                "tarname": tarname,
            },
            processstep_pos=0,
            information_package=self
        )

        t7 = ProcessTask.objects.create(
            name="preingest.tasks.CreateZIP",
            params={
                "dirname": ip_prepare_path,
                "zipname": zipname,
            },
            processstep_pos=0,
            information_package=self
        )

        t8 = ProcessTask.objects.create(
            name="preingest.tasks.UpdateIPStatus",
            params={
                "ip": self,
                "status": "CREATED",
            },
            processstep_pos=0,
            information_package=self
        )

        create_sip_step = ProcessStep.objects.create(
                name="Create SIP"
        )
        create_sip_step.tasks = [t6, t7, t8]
        create_sip_step.save()

        main_step = ProcessStep.objects.create(
            name="Create IP",
        )
        main_step.child_steps = [
            generate_xml_step, copy_schemas_step, validate_step,
            create_sip_step
        ]
        main_step.information_package = self
        main_step.save()
        main_step.run()

    def submit(self):
        step = ProcessStep.objects.create(
            name="Submit SIP",
            information_package = self
        )

        sa = self.SubmissionAgreement

        sip_profile = sa.profile_sip_rel.active()
        info = sip_profile.specification_data
        info['agents'] = info['agents'].values()

        prepare = Path.objects.get(entity="path_preingest_prepare").value
        infoxml = os.path.join(prepare, str(self.pk) + ".xml")

        filesToCreate = {
            infoxml: sip_profile.specification
        }

        folderToParse = self.ObjectPath + ".tar"

        step.tasks.add(ProcessTask.objects.create(
            name="preingest.tasks.GenerateXML",
            params={
                "info": info,
                "filesToCreate": filesToCreate,
                "folderToParse": folderToParse
            },
            information_package=self
        ))

        step.tasks.add(ProcessTask.objects.create(
            name="preingest.tasks.SubmitSIP",
            params={
                "ip": self
            },
            information_package=self
        ))

        step.tasks.add(ProcessTask.objects.create(
            name="preingest.tasks.UpdateIPStatus",
            params={
                "ip": self,
                "status": "SUBMITTED"
            },
            information_package=self
        ))

        step.save()
        step.run()

    def status(self):
        steps = self.steps.all()

        if steps:
            try:
                progress = sum([s.progress() for s in steps])
                return progress / len(steps)
            except:
                return 0

        return 0

    def locks(self):
        return ProfileLock.objects.filter(
            information_package=self,
            submission_agreement=self.SubmissionAgreement
        )

    class Meta:
        ordering = ["id"]
        verbose_name = 'Information Package'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.Label, self.pk)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in InformationPackage._meta.fields
        }


class EventIP(models.Model):
    """
    Events related to IP
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eventType = models.ForeignKey(
        'configuration.EventType',
        on_delete=models.CASCADE
    )
    eventDateTime = models.DateTimeField(auto_now_add=True)
    eventDetail = models.CharField(max_length=255) # For example "Prepare IP"
    eventApplication = models.CharField(max_length=255)
    eventVersion = models.CharField(max_length=255)
    eventOutcome = models.CharField(max_length=255) # Success (0) or Fail (1)
    eventOutcomeDetailNote = models.CharField(max_length=1024) # Result or traceback from IP
    linkingAgentIdentifierValue = models.CharField(max_length=255)
    linkingObjectIdentifierValue = models.ForeignKey(
        'InformationPackage',
        on_delete=models.CASCADE,
        related_name='events'
    )

    class Meta:
        ordering = ["eventType"]
        verbose_name = 'Events related to IP'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s (%s)' % (self.eventDetail, self.id)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in EventIP._meta.fields
        }
