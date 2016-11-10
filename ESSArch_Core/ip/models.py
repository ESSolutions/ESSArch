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
from celery import states as celery_states

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
    SubmissionAgreement as SA,
    ProfileIP,
)

from ESSArch_Core.util import (
    create_event,
    get_tree_count,
    get_tree_size,
)

from ESSArch_Core.xml.Generator.xmlGenerator import (
    downloadSchemas, find_destination
)

from scandir import scandir, walk

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
    SubmissionAgreementLocked = models.BooleanField(default=False)
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

    @property
    def ObjectSize(self):
        if os.path.exists(self.ObjectPath):
            return get_tree_size(self.ObjectPath)

    @property
    def ObjectNumItems(self):
        if os.path.exists(self.ObjectPath):
            return get_tree_count(self.ObjectPath)

    @property
    def profile_transfer_project_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="transfer_project"
        ).first()

    @property
    def profile_content_type_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="content_type"
        ).first()

    @property
    def profile_data_selection_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="data_selection"
        ).first()

    @property
    def profile_classification_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="classification"
        ).first()

    @property
    def profile_import_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="import"
        ).first()

    @property
    def profile_submit_description_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="submit_description"
        ).first()

    @property
    def profile_sip_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="sip"
        ).first()

    @property
    def profile_aip_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="aip"
        ).first()

    @property
    def profile_dip_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="dip"
        ).first()

    @property
    def profile_workflow_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="workflow"
        ).first()

    @property
    def profile_preservation_metadata_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="preservation_metadata"
        ).first()

    @property
    def profile_event_rel(self):
        return ProfileIP.objects.filter(
            ip=self, profile__profile_type="event"
        ).first()

    def profile_locked(self, profile_type):
        rel = getattr(self, "profile_%s_rel" % profile_type)

        if rel:
            return rel.LockedBy is not None

        return False

    def get_profile(self, profile_type):
        rel = getattr(self, "profile_%s_rel" % profile_type)

        if rel:
            return rel.profile

        return None

    def change_profile(self, new_profile):
        ptype = new_profile.profile_type
        try:
            pip = ProfileIP.objects.get(ip=self, profile__profile_type=ptype)
            pip.profile = new_profile
            pip.save()
        except ProfileIP.DoesNotExist:
            ProfileIP.objects.create(ip=self, profile=new_profile)

    def unlock_profile(self, ptype):
        ProfileIP.objects.filter(
            ip=self, profile__profile_type=ptype
        ).delete()

    def create(self, validate_logical_physical_representation=True,
               validate_xml_file=True, validate_file_format=True,
               validate_integrity=True):

        start_create_sip_step = ProcessStep.objects.create(
            name="Update IP Status",
            tasks=[
                ProcessTask.objects.create(
                    name="preingest.tasks.UpdateIPStatus",
                    params={
                        "ip": self,
                        "status": "Creating",
                    },
                    processstep_pos=0,
                    information_package=self
                )
            ]
        )

        event_type = EventType.objects.get(eventType=10200)

        create_event(event_type, [], "System", self)

        prepare_path = Path.objects.get(
            entity="path_preingest_prepare"
        ).value

        reception_path = Path.objects.get(
            entity="path_preingest_reception"
        ).value

        ip_prepare_path = os.path.join(prepare_path, str(self.pk))
        ip_reception_path = os.path.join(reception_path, str(self.pk))

        structure = self.get_profile('sip').structure

        info = self.get_profile('event').specification_data
        info["_OBJID"] = str(self.pk)
        info["_LABEL"] = self.Label

        events_path = os.path.join(ip_prepare_path, "ipevents.xml")
        filesToCreate = OrderedDict()
        filesToCreate[events_path] = self.get_profile('event').specification

        for fname, template in filesToCreate.iteritems():
            dirname = os.path.dirname(fname)
            downloadSchemas(
                template, dirname, structure=structure, root=self.ObjectPath
            )

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
            'FID': str(self.pk),
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

        info = self.get_profile('sip').specification_data
        info["_OBJID"] = str(self.pk)

        # ensure premis is created before mets
        filesToCreate = OrderedDict()

        if self.profile_locked('preservation_metadata'):
            premis_profile = self.get_profile('preservation_metadata')
            premis_dir, premis_name = find_destination("preservation_description_file", structure)
            premis_path = os.path.join(self.ObjectPath, premis_dir, premis_name)
            filesToCreate[premis_path] = premis_profile.specification

        mets_dir, mets_name = find_destination("mets_file", structure)
        mets_path = os.path.join(self.ObjectPath, mets_dir, mets_name)
        filesToCreate[mets_path] = self.get_profile('sip').specification

        for fname, template in filesToCreate.iteritems():
            dirname = os.path.dirname(fname)
            downloadSchemas(
                template, dirname, structure=structure, root=self.ObjectPath
            )

        t1 = ProcessTask.objects.create(
            name="preingest.tasks.GenerateXML",
            params={
                "info": info,
                "filesToCreate": filesToCreate,
                "folderToParse": ip_prepare_path,
            },
            processstep_pos=0,
            information_package=self
        )

        generate_xml_step = ProcessStep.objects.create(
            name="Generate XML",
        )
        generate_xml_step.tasks = [t0, t01, t02, t1]
        generate_xml_step.save()

        #dirname = os.path.join(ip_prepare_path, "data")
        tarname = os.path.join(ip_reception_path) + '.tar'
        zipname = os.path.join(ip_reception_path) + '.zip'

        validate_step = ProcessStep.objects.create(
            name="Validation",
        )

        if validate_xml_file:
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

            if self.profile_locked("preservation_metadata"):
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

        if validate_logical_physical_representation:
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
                    "validate_fileformat": validate_file_format,
                    "validate_integrity": validate_integrity,
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
                "status": "Created",
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
            name="Create SIP",
        )
        main_step.child_steps = [
            start_create_sip_step, generate_xml_step, validate_step,
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

        sd_profile = self.get_profile('submit_description')
        info = sd_profile.specification_data
        info["_OBJID"] = str(self.pk)
        info["_LABEL"] = self.Label

        reception = Path.objects.get(entity="path_preingest_reception").value
        infoxml = os.path.join(reception, str(self.pk) + ".xml")

        filesToCreate = {
            infoxml: sd_profile.specification
        }

        folderToParse = os.path.join(reception, str(self.pk) + ".tar")

        step.tasks.add(ProcessTask.objects.create(
            name="preingest.tasks.GenerateXML",
            params={
                "info": info,
                "filesToCreate": filesToCreate,
                "folderToParse": folderToParse,
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
                "status": "Submitted"
            },
            information_package=self
        ))

        step.save()
        step.run()

    @property
    def step_state(self):
        """
        Gets the state of the IP based on its steps

        Args:

        Returns:
            Can be one of the following:
            SUCCESS, STARTED, FAILURE, PENDING

            Which is decided by five scenarios:

            * If there are no steps, then PENDING.
            * If there are steps and they are all pending,
              then PENDING.
            * If a step has started, then STARTED.
            * If a step has failed, then FAILURE.
            * If all steps have succeeded, then SUCCESS.
        """

        steps = self.steps.all()
        state = celery_states.SUCCESS

        if not steps:
            return celery_states.PENDING

        for step in steps:
            if step.status == celery_states.STARTED:
                state = step.status
            if (step.status == celery_states.PENDING and
                    state != celery_states.STARTED):
                state = step.status
            if step.status == celery_states.FAILURE:
                return step.status

        return state

    def status(self):
        steps = self.steps.all()

        if steps:
            try:
                progress = sum([s.progress() for s in steps])
                return progress / len(steps)
            except:
                return 0

        return 0

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
