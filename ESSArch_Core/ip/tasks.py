import copy
import logging
import os
import pathlib
import tarfile
from datetime import timedelta
from time import sleep
from urllib.parse import urljoin

import requests
from celery import states as celery_states
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext
from elasticsearch import NotFoundError
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential,
)

from ESSArch_Core.auth.models import Member, Notification
from ESSArch_Core.config.celery import app
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.crypto import decrypt_remote_credentials
from ESSArch_Core.essxml.Generator.xmlGenerator import (
    XMLGenerator,
    parseContent,
)
from ESSArch_Core.essxml.util import parse_submit_description
from ESSArch_Core.fixity.receipt import get_backend as get_receipt_backend
from ESSArch_Core.fixity.transformation import get_backend as get_transformer
from ESSArch_Core.fixity.validation import (
    _validate_directory as validate_directory,
    get_backend as get_validator,
)
from ESSArch_Core.ip.models import EventIP, InformationPackage, Workarea
from ESSArch_Core.ip.serializers import (
    InformationPackageReceptionReceiveSerializer,
)
from ESSArch_Core.ip.utils import (
    download_schemas,
    fill_specification_data,
    generate_aic_mets,
    generate_content_metadata,
    generate_content_mets,
    generate_events_xml,
    generate_package_mets,
    generate_premis,
    parse_submit_description_from_ip,
)
from ESSArch_Core.profiles.models import ProfileIP, SubmissionAgreement
from ESSArch_Core.storage.copy import copy_file, enough_space_available
from ESSArch_Core.storage.exceptions import (
    NoSpaceLeftError,
    NoWriteableStorage,
)
from ESSArch_Core.storage.models import StorageMethod, StorageTarget
from ESSArch_Core.tags.models import (
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)
from ESSArch_Core.util import (
    delete_path,
    get_premis_ip_object_element_spec,
    normalize_path,
    zip_directory,
)
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


@app.task(bind=True, event_type=10500)
def SubmitSIP(self, delete_source=False, update_path=True):
    ip = InformationPackage.objects.get(pk=self.ip)

    reception = Path.objects.get(entity="ingest_reception").value
    container_format = ip.get_container_format()
    src = ip.object_path

    try:
        remote = ip.get_profile_data('transfer_project').get(
            'preservation_organization_receiver_url'
        )
    except AttributeError:
        remote = None

    session = None

    if remote:
        dst, remote_user, remote_pass = remote.split(',')
        dst = urljoin(dst, 'api/ip-reception/upload/')

        session = requests.Session()
        session.verify = settings.REQUESTS_VERIFY
        session.auth = (remote_user, remote_pass)
    else:
        dst = os.path.join(reception, ip.object_identifier_value + ".%s" % container_format)

    block_size = 8 * 1000000  # 8MB
    copy_file(src, dst, requests_session=session, block_size=block_size)

    src_xml = os.path.join(os.path.dirname(src), ip.object_identifier_value + ".xml")
    if not remote:
        dst_xml = os.path.join(reception, ip.object_identifier_value + ".xml")
    else:
        dst_xml = dst
    copy_file(src_xml, dst_xml, requests_session=session, block_size=block_size)

    if update_path and not remote:
        ip.object_path = dst
        ip.package_mets_path = dst_xml
        ip.save()

    if delete_source:
        delete_path(src)
        delete_path(src_xml)

    self.set_progress(100, total=100)


@app.task(bind=True, event_type=20600)
def TransferIP(self):
    ip = InformationPackage.objects.get(pk=self.ip)
    src = ip.object_path
    srcdir, srcfile = os.path.split(src)

    remote = ip.get_profile_data('transfer_project').get('transfer_destination_url')
    session = None
    if remote:
        dst, remote_user, remote_pass = remote.split(',')

        session = requests.Session()
        session.verify = settings.REQUESTS_VERIFY
        session.auth = (remote_user, remote_pass)

    if not remote:
        dst = Path.objects.get(entity="ingest_transfer").value

    block_size = 8 * 1000000  # 8MB
    copy_file(src, dst, requests_session=session, block_size=block_size)

    self.set_progress(50, total=100)

    objid = ip.object_identifier_value
    src = ip.get_events_file_path()
    if os.path.isfile(src):
        if not remote:
            xml_dst = os.path.join(os.path.dirname(dst), "%s_ipevents.xml" % objid)
        else:
            xml_dst = dst
        copy_file(src, xml_dst, requests_session=session, block_size=block_size)

    self.set_progress(75, total=100)

    src = os.path.join(srcdir, "%s.xml" % objid)
    if remote:
        xml_dst = dst
    else:
        xml_dst = os.path.join(dst, "%s.xml" % objid)

    copy_file(src, xml_dst, requests_session=session, block_size=block_size)
    self.set_progress(100, total=100)
    self.create_success_event("Transferred IP")
    return dst


@app.task(bind=True)
def PrepareAIP(self, sip_path):
    sip_path, = self.parse_params(sip_path)
    sip_path = pathlib.Path(sip_path)
    user = User.objects.get(pk=self.responsible)
    perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
    organization = user.user_profile.current_organization

    object_identifier_value = sip_path.stem
    existing_sip = InformationPackage.objects.filter(
        Q(
            Q(object_path=sip_path) |
            Q(object_identifier_value=object_identifier_value),
        ),
        package_type=InformationPackage.SIP
    ).first()
    xmlfile = sip_path.with_suffix('.xml')
    if os.path.exists(xmlfile):
        xmlfile_posix = xmlfile.as_posix()
    else:
        xmlfile_posix = ''

    if existing_sip is None:
        parsed = parse_submit_description(xmlfile.as_posix(), srcdir=sip_path.parent)
        parsed_sa = parsed.get('altrecordids', {}).get('SUBMISSIONAGREEMENT', [None])[0]

        if parsed_sa is not None:
            raise ValueError('No submission agreement found in xml')

        sa = SubmissionAgreement.objects.get(pk=parsed_sa)

        with transaction.atomic():
            ip = InformationPackage.objects.create(
                object_identifier_value=object_identifier_value,
                sip_objid=object_identifier_value,
                sip_path=sip_path.as_posix(),
                package_type=InformationPackage.AIP,
                state='Prepared',
                responsible=user,
                submission_agreement=sa,
                submission_agreement_locked=True,
                object_path=sip_path.as_posix(),
                package_mets_path=xmlfile_posix,
            )

            member = Member.objects.get(django_user=user)
            user_perms = perms.pop('owner', [])

            organization.assign_object(ip, custom_permissions=perms)
            organization.add_object(ip)

            for perm in user_perms:
                perm_name = get_permission_name(perm, ip)
                assign_perm(perm_name, member.django_user, ip)

            # refresh date fields to convert them to datetime instances instead of
            # strings to allow further datetime manipulation
            ip.refresh_from_db(fields=['entry_date', 'start_date', 'end_date'])

            ProfileIP.objects.filter(ip=ip).delete()
            ip.submission_agreement.lock_to_information_package(ip, user)
            for profile_ip in ProfileIP.objects.filter(ip=ip).iterator(chunk_size=1000):
                profile_ip.lock(user)
    else:
        with transaction.atomic():
            ip = existing_sip
            ip.sip_objid = object_identifier_value
            ip.sip_path = sip_path.as_posix()
            ip.package_type = InformationPackage.AIP
            ip.responsible = user
            ip.state = 'Prepared'
            ip.object_path = sip_path.as_posix()
            ip.package_mets_path = xmlfile_posix

    ip.generation = 0
    ip.aic = InformationPackage.objects.create(
        package_type=InformationPackage.AIC,
        responsible=ip.responsible,
        label=ip.label,
        start_date=ip.start_date,
        end_date=ip.end_date,
    )
    ip.save()

    return str(ip.pk)


@app.task(bind=True, event_type=50600)
def GenerateContentMets(self):
    generate_content_mets(self.get_information_package())
    ip = self.get_information_package()
    msg = 'Generated {xml}'.format(xml=ip.content_mets_path)
    self.create_success_event(msg)


@app.task(bind=True, event_type=50600)
def GeneratePackageMets(self, package_path=None, xml_path=None):
    package_path, xml_path = self.parse_params(package_path, xml_path)
    ip = self.get_information_package()
    package_path = package_path if package_path else ip.object_path
    xml_path = xml_path if xml_path else os.path.splitext(package_path)[0] + '.xml'

    generate_package_mets(ip, package_path, xml_path)
    msg = 'Generated {xml}'.format(xml=xml_path)
    self.create_success_event(msg)
    return xml_path


@app.task(bind=True)
def GenerateAICMets(self, xml_path):
    xml_path, = self.parse_params(xml_path)
    ip = self.get_information_package()
    generate_aic_mets(ip, xml_path)
    msg = 'Generated {xml}'.format(xml=xml_path)
    self.create_success_event(msg)
    return xml_path


@app.task(bind=True, event_type=50600)
def GeneratePremis(self):
    generate_premis(self.get_information_package())
    ip = self.get_information_package()
    data = fill_specification_data(ip=ip)
    premis_path = parseContent(ip.get_premis_file_path(), data)
    msg = 'Generated {xml}'.format(xml=premis_path)
    self.create_success_event(msg)


@app.task(bind=True, event_type=50600)
def GenerateContentMetadata(self):
    generate_content_metadata(self.get_information_package())
    ip = self.get_information_package()
    msg = 'Generated {xml}'.format(xml=ip.content_mets_path)
    generate_premis = ip.profile_locked('preservation_metadata')
    if generate_premis:
        data = fill_specification_data(ip=ip)
        premis_path = parseContent(ip.get_premis_file_path(), data)
        msg = '{msg} and {xml}'.format(msg=msg, xml=premis_path)
    self.create_success_event(msg)
    return msg


@app.task(bind=True, event_type=50600)
def GenerateEventsXML(self):
    generate_events_xml(self.get_information_package())
    ip = self.get_information_package()
    msg = 'Generated {xml}'.format(xml=ip.get_events_file_path())
    self.create_success_event(msg)
    return msg


@app.task(bind=True)
def DownloadSchemas(self, verify=settings.REQUESTS_VERIFY):
    logger = logging.getLogger('essarch.core.ip.tasks.DownloadSchemas')
    download_schemas(self.get_information_package(), logger, verify)


@app.task(bind=True)
def AddPremisIPObjectElementToEventsFile(self):
    ip = self.get_information_package()
    info = {
        'FIDType': "UUID",
        'FID': ip.object_identifier_value,
        'FFormatName': ip.get_container_format().upper(),
        'FLocationType': 'URI',
        'FName': ip.object_path,
    }
    spec = get_premis_ip_object_element_spec()
    info = fill_specification_data(info, ip=ip)
    xmlfile = os.path.join(ip.object_path, ip.get_events_file_path())

    generator = XMLGenerator(filepath=xmlfile)
    target = generator.find_element('premis')
    generator.insert_from_specification(target, spec, data=info, index=0)
    generator.write(xmlfile)
    return 'Add premis IP to {}'.format(xmlfile)


@app.task(bind=True, event_type=10300)
def CreatePhysicalModel(self, structure=None, root=""):
    """
    Creates the IP physical model based on a logical model.

    Args:
        structure: A dict specifying the logical model.
        root: The root directory to be used
    """

    ip = self.get_information_package()
    created = ip.create_physical_model(structure, root)

    self.set_progress(1, total=1)

    ip.state = "Prepared"
    ip.save(update_fields=['state'])

    msg = "Created physical model"
    self.create_success_event(msg)

    return created


@app.task(bind=True)
@retry(reraise=True, retry=retry_if_exception_type(NoSpaceLeftError),
       wait=wait_exponential(max=60), stop=stop_after_delay(600))
def CreateContainer(self, src, dst):
    src, dst = self.parse_params(src, dst)

    ip = self.get_information_package()
    container_format = ip.get_container_format().lower()
    tpp = ip.get_profile_rel('transfer_project').profile
    compress = tpp.specification_data.get('container_format_compression', False)

    dst = normalize_path(dst)

    if os.path.isdir(dst):
        dst_filename = ip.object_identifier_value + '.' + ip.get_container_format().lower()
        dst = os.path.join(dst, dst_filename)

    enough_space_available(os.path.dirname(dst), src, True)

    if container_format == 'zip':
        self.event_type = 50410
        zip_directory(dirname=src, zipname=dst, compress=compress)
    else:
        self.event_type = 50400
        compression = ':gz' if compress else ''
        base_dir = os.path.basename(os.path.normpath(src))
        with tarfile.open(dst, 'w%s' % compression) as new_tar:
            new_tar.format = settings.TARFILE_FORMAT
            new_tar.add(src, base_dir)

    msg = "Created {}".format(dst)
    self.create_success_event(msg)

    return dst


@app.task(bind=True)
@transaction.atomic
def ParseSubmitDescription(self):
    parse_submit_description_from_ip(self.get_information_package())

    ip = self.get_information_package()
    msg = "Parsed submit description at {}".format(ip.package_mets_path)
    self.create_success_event(msg)


@app.task(bind=True, event_type=50630)
@transaction.atomic
def ParseEvents(self):
    logger = logging.getLogger('essarch.core.ip.tasks.ParseEvents')

    ip = self.get_information_package()
    xmlfile_path = ip.get_events_file_path(from_container=True)
    try:
        xmlfile = ip.open_file(xmlfile_path, 'rb')
    except (FileNotFoundError, KeyError):
        logger.debug('No events file found at "{}"'.format(xmlfile_path))
        return

    events = EventIP.objects.from_premis_file(xmlfile, save=False)
    EventIP.objects.bulk_create(events, 100)

    msg = "Parsed events from %s" % xmlfile_path
    self.create_success_event(msg)


@app.task(bind=True)
def Transform(self, backend, path=None):
    ip = self.get_information_package()
    user = User.objects.filter(pk=self.responsible).first()
    backend = get_transformer(backend, ip=ip, responsible=user)
    if path is None and ip is not None:
        path = ip.object_path
    backend.transform(path)


@app.task(bind=True)
def Validate(self, backend, path=None, context=None, include=None,
             exclude=None, options=None, required=False, stylesheet=None,
             **kwargs):

    validators = []

    ip = self.get_information_package()

    if path is None and ip is not None:
        path = ip.object_path
    backend_name = backend
    user = User.objects.filter(pk=self.responsible).first()
    profile_data = fill_specification_data(data=options, ip=ip)
    backend = get_validator(backend)

    if include:

        if isinstance(include, str):
            include = include.split(',')

        include = [os.path.join(path, included) for included in include]

    if exclude:
        if isinstance(exclude, str):
            exclude = exclude.split(',')

        exclude = [os.path.join(path, excluded) for excluded in exclude]

    validator_instance = backend(context=context,
                                 include=include,
                                 exclude=exclude,
                                 options=options,
                                 data=profile_data,
                                 required=required,
                                 task=self.get_processtask(),
                                 ip=ip,
                                 responsible=user,
                                 stylesheet=stylesheet
                                 )

    validators.append(validator_instance)

    validate_directory(path=path,
                       validators=validators,
                       ip=ip,
                       responsible=user)

    Notification.objects.create(
        message=gettext('{backend} job done for {ip}').format(
            backend=backend_name,
            ip=ip
        ),
        level=logging.INFO,
        user_id=self.responsible,
        refresh=True
    )


@app.task(bind=True)
def PreserveInformationPackage(self, storage_method_pk, temp_path=None):
    ip = self.get_information_package()
    policy = ip.policy

    if policy is None:
        raise ValueError('{} has no policy'.format(ip))

    storage_method = StorageMethod.objects.get(pk=storage_method_pk)
    policy_methods = policy.storage_methods.all()

    if storage_method not in policy_methods:
        raise ValueError('{} not part of {}'.format(storage_method, policy))

    if not storage_method.enabled:
        raise NoWriteableStorage('Storage method "{}" is disabled'.format(storage_method.name))

    try:
        storage_target = storage_method.enabled_target
    except StorageTarget.DoesNotExist:
        raise NoWriteableStorage('No writeable target available for "{}"'.format(storage_method.name))

    if storage_method.containers or storage_target.remote_server:
        src = [
            ip.get_temp_container_path(temp_path),
            ip.get_temp_container_xml_path(temp_path),
        ]
        if ip.profile_locked('aic_description'):
            src.append(ip.get_temp_container_aic_xml_path(temp_path))
    else:
        if temp_path:
            src = [ip.get_temp_object_path(temp_path)]
        else:
            src = [ip.object_path]

    storage_object_pk, medium_id, write_size, mb_per_sec, time_elapsed = ip.preserve(
        src, storage_target, storage_method.containers, self.get_processtask())

    time_elapsed_round = round(time_elapsed)
    time_elapsed_sec = time_elapsed_round if time_elapsed_round > 1 else 1
    msg = "Information package written to {} ({}), WriteSize: {}, WriteTime: {} ({:.2f} MB/Sec)".format(
        medium_id, storage_target.name, write_size, timedelta(seconds=round(time_elapsed_sec)), mb_per_sec
    )
    if storage_method.type == 200:
        self.event_type = 40600
    elif storage_method.type == 300:
        self.event_type = 40700
    elif storage_method.type == 400:
        self.event_type = 40620
    self.create_success_event(msg)

    return "{}, {} ({}), {:.2f} MB/Sec".format(storage_object_pk, medium_id, storage_target.name, mb_per_sec)


@app.task(bind=True)
def WriteInformationPackageToSearchIndex(self):
    ip = self.get_information_package()
    ip.write_to_search_index(self.get_processtask())


@app.task(bind=True)
def CreateReceipt(self, task_id=None, backend=None, template=None, destination=None, outcome=None,
                  short_message=None, message=None, date=None, **kwargs):
    try:
        ip = self.get_information_package()
    except ObjectDoesNotExist:
        self.logger.warning('exception ip DoesNotExist in CreateReceipt. task_id: {}, ip: {}'.format(task_id, self.ip))
        ip = None
    template, destination, outcome, short_message, message, date = self.parse_params(
        template, destination, outcome, short_message, message, date
    )
    if date is None:
        date = timezone.now()

    backend = get_receipt_backend(backend)
    if task_id is None:
        task = self.get_processtask()
    else:
        try:
            task = ProcessTask.objects.get(celery_id=task_id)
        except ProcessTask.DoesNotExist as e:
            self.logger.warning('exception ProcessTask DoesNotExist for failed task_id: {} in CreateReceipt. ip: {}, \
CreateReceipt_task_id: {}'.format(task_id, self.ip, self.get_processtask()))
            self.logger.exception(e)
            task = None

    return backend.create(template, destination, outcome, short_message, message, date, ip=ip, task=task, **kwargs)


@app.task(bind=True, event_type=30300)
def MarkArchived(self, remote_host=None, remote_credentials=None):
    requests_session = None
    if remote_credentials:
        user, passw = decrypt_remote_credentials(remote_credentials)
        requests_session = requests.Session()
        requests_session.verify = settings.REQUESTS_VERIFY
        requests_session.auth = (user, passw)

        task = self.get_processtask()
        r = task.get_remote_copy(requests_session, remote_host)
        if r.status_code == 404:
            # the task does not exist
            task.create_remote_copy(requests_session, remote_host)
            task.run_remote_copy(requests_session, remote_host)
        else:
            remote_data = r.json()
            task.status = remote_data['status']
            task.progress = remote_data['progress']
            task.result = remote_data['result']
            task.traceback = remote_data['traceback']
            task.exception = remote_data['exception']
            task.save()

            if task.status == celery_states.PENDING:
                task.run_remote_copy(requests_session, remote_host)
            elif task.status != celery_states.SUCCESS:
                self.logger.debug('task.status: {}'.format(task.status))
                task.retry_remote_copy(requests_session, remote_host)
                task.status = celery_states.PENDING

        while task.status not in celery_states.READY_STATES:
            requests_session = requests.Session()
            requests_session.verify = settings.REQUESTS_VERIFY
            requests_session.auth = (user, passw)
            r = task.get_remote_copy(requests_session, remote_host)

            remote_data = r.json()
            task.status = remote_data['status']
            task.progress = remote_data['progress']
            task.result = remote_data['result']
            task.traceback = remote_data['traceback']
            task.exception = remote_data['exception']
            task.save()

            sleep(5)

        if task.status in celery_states.EXCEPTION_STATES:
            task.reraise()
    else:
        ip = self.get_information_package()
        ip.archived = True
        ip.state = 'Preserved'
        ip.save()

    msg = "Preserved AIP (%s)" % ip.object_identifier_value
    self.create_success_event(msg)


@app.task(bind=True)
def InsertArchivalDescription(self, data):
    ip = self.get_information_package()
    serializer = InformationPackageReceptionReceiveSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer_data = serializer.validated_data

    archive = serializer_data.get('archive')
    structure = serializer_data.get('structure')
    structure_unit = serializer_data.get('structure_unit')
    archive_structure = TagStructure.objects.get(tag=archive.tag, structure=structure)

    tag = Tag.objects.create(
        information_package=ip,
    )
    TagVersion.objects.create(
        name=ip.label or ip.object_identifier_value,
        reference_code=ip.object_identifier_value,
        tag=tag,
        type=TagVersionType.objects.get(information_package_type=True),
        elastic_index='component',
    )
    TagStructure.objects.create(
        tag=tag,
        structure=structure,
        structure_unit=structure_unit,
        parent=archive_structure,
    )


@app.task(bind=True)
def PostPreservationCleanup(self):
    ip = self.get_information_package()

    paths = Path.objects.filter(entity__in=[
        'preingest_reception', 'preingest', 'ingest_reception',
    ]).values_list('value', flat=True)

    for p in paths:
        delete_path(os.path.join(p, ip.object_identifier_value))
        delete_path(os.path.join(p, ip.object_identifier_value) + '.tar')
        delete_path(os.path.join(p, ip.object_identifier_value) + '.xml')


@app.task(bind=True)
def DeleteInformationPackage(self, from_db=False, delete_files=True):
    ip = self.get_information_package()

    old_state = ip.state
    ip.state = 'Deleting'
    ip.save()

    ip.delete_temp_files()

    task = self.get_processtask()
    for ProcessTask_obj in ip.processtask_set.exclude(status='SUCCESS').exclude(id=task.id):
        ProcessTask_obj.revoke()

    try:
        ip.delete_workareas()
        if delete_files:
            ip.delete_files()
    except BaseException:
        ip.state = old_state
        ip.save()
        raise

    self.set_progress(99, 100)

    logger = logging.getLogger('essarch.core.ip.tasks.DeleteInformationPackage')

    if settings.ELASTICSEARCH_CONNECTIONS['default']['hosts'][0]['host']:
        try:
            ip.get_doc().delete()
        except NotFoundError:
            if ip.archived:
                logger.warning('Information package document not found: {}'.format(ip.pk))

    if from_db:
        with transaction.atomic():
            ip.informationpackagegroupobjects_set.all().delete()
            ip.delete()
    else:
        ip.state = 'deleted'
        ip.save()

    Notification.objects.create(message=gettext('{ip} has been deleted').format(ip=ip),
                                level=logging.INFO, user_id=self.responsible, refresh=True)


@app.task(bind=True)
def CreateWorkarea(self, ip, user, type, read_only):
    ip = InformationPackage.objects.get(pk=ip)
    user = User.objects.get(pk=user)
    Workarea.objects.update_or_create(ip=ip, user=user, defaults={
        'type': type,
        'read_only': read_only,
    })
    Notification.objects.create(
        message=gettext("{ip} is now in workspace").format(ip=ip),
        level=logging.INFO, user=user, refresh=True
    )


@app.task(bind=True)
def DeleteWorkarea(self, pk):
    workarea = Workarea.objects.get(pk=pk)
    workarea.delete_files()
    workarea.delete()
