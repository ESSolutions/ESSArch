import collections
import os

from ESSArch_Core.configuration.models import Parameter, Path
from ESSArch_Core.util import find_destination

profile_types = [
    "Transfer Project",
    "Content Type",
    "Data Selection",
    "Authority Information",
    "Archival Description",
    "Import",
    "Submit Description",
    "SIP",
    "AIC Description",
    "AIP",
    "AIP Description",
    "DIP",
    "Workflow",
    "Preservation Metadata",
    "Event",
    "Validation",
]


def _remove_leading_underscores(d):
    new_mapping = type(d)()

    for k, v in d.items():
        new_key = k.lstrip('_')
        if isinstance(v, collections.Mapping):
            new_mapping[new_key] = _remove_leading_underscores(v)
        else:
            new_mapping[new_key] = v

    return new_mapping


def _fill_sa_specification_data(sa):
    return {
        '_SA_ID': str(sa.pk),
        '_SA_NAME': sa.name,
        '_IP_ARCHIVIST_ORGANIZATION': sa.archivist_organization,
    }


def fill_specification_data(data=None, sa=None, ip=None):
    data = data or {}

    if sa:
        data.update(_fill_sa_specification_data(sa))

    if ip:
        if not sa and ip.submission_agreement is not None:
            sa = ip.submission_agreement
            data.update(_fill_sa_specification_data(sa))

        data['_OBJID'] = ip.object_identifier_value
        data['_OBJUUID'] = str(ip.pk)
        data['_OBJLABEL'] = ip.label
        data['_OBJPATH'] = ip.object_path
        data['_INNER_IP_OBJID'] = ip.sip_objid
        data['_INNER_IP_PATH'] = ip.sip_path
        data['_STARTDATE'] = ip.start_date
        data['_ENDDATE'] = ip.end_date
        data['_INFORMATIONCLASS'] = ip.information_class

        data['_CONTENT_METS_PATH'] = ip.content_mets_path
        data['_CONTENT_METS_CREATE_DATE'] = ip.content_mets_create_date
        data['_CONTENT_METS_SIZE'] = ip.content_mets_size
        data['_CONTENT_METS_DIGEST_ALGORITHM'] = ip.get_content_mets_digest_algorithm_display()
        data['_CONTENT_METS_DIGEST'] = ip.content_mets_digest

        data['_PACKAGE_METS_PATH'] = ip.package_mets_path
        data['_PACKAGE_METS_CREATE_DATE'] = ip.package_mets_create_date
        data['_PACKAGE_METS_SIZE'] = ip.package_mets_size
        data['_PACKAGE_METS_DIGEST_ALGORITHM'] = ip.get_package_mets_digest_algorithm_display()
        data['_PACKAGE_METS_DIGEST'] = ip.package_mets_digest

        data['_TEMP_CONTAINER_PATH'] = ip.get_temp_container_path()
        data['_TEMP_METS_PATH'] = ip.get_temp_container_xml_path()
        data['_TEMP_AIC_METS_PATH'] = ip.get_temp_container_aic_xml_path() if ip.aic else None

        if ip.get_package_type_display() in ['SIP', 'AIP']:
            ip_profile = ip.get_profile(ip.get_package_type_display().lower())
            if ip_profile is not None:
                premis_dir, premis_file = find_destination("preservation_description_file", ip_profile.structure)
                if premis_dir is not None and premis_file is not None:
                    data['_PREMIS_PATH'] = os.path.join(ip.object_path, premis_dir, premis_file)
            data['allow_unknown_file_types'] = ip.get_allow_unknown_file_types()

        try:
            # do we have a transfer project profile?
            ip.get_profile('transfer_project')
        except AttributeError:
            container = 'TAR'
        else:
            container = ip.get_container_format()

        data['_IP_CONTAINER_FORMAT'] = container.upper()

        if ip.policy is not None:
            data['_POLICYUUID'] = ip.policy.pk
            data['_POLICYID'] = ip.policy.policy_id
            data['_POLICYNAME'] = ip.policy.policy_name
            data['POLICY_INGEST_PATH'] = ip.policy.ingest_path.value
        else:
            try:
                # do we have a transfer project profile?
                ip.get_profile('transfer_project')
            except AttributeError:
                pass
            else:
                transfer_project_data = ip.get_profile_data('transfer_project')
                data['_POLICYUUID'] = transfer_project_data.get('storage_policy_uuid')
                data['_POLICYID'] = transfer_project_data.get('storage_policy_id')
                data['_POLICYNAME'] = transfer_project_data.get('storage_policy_name')

        data['_AGENTS'] = {}
        for a in ip.agents.all():
            agent = {
                '_AGENTS_NAME': a.name,
                '_AGENTS_NOTES': [{'_AGENTS_NOTE': n.note} for n in a.notes.all()],
            }

            if a.other_role:
                agent['_AGENTS_ROLE'] = 'OTHER'
                agent['_AGENTS_OTHERROLE'] = a.role
            else:
                agent['_AGENTS_ROLE'] = a.role

            if a.other_type:
                agent['_AGENTS_TYPE'] = 'OTHER'
                agent['_AGENTS_OTHERTYPE'] = a.type
            else:
                agent['_AGENTS_TYPE'] = a.type

            agent_key = '{role}_{type}'.format(role=a.role.upper(), type=a.type.upper())
            data['_AGENTS'][agent_key] = agent

        profile_ids = zip(
            [x.lower().replace(' ', '_') for x in profile_types],
            ["_PROFILE_" + x.upper().replace(' ', '_') + "_ID" for x in profile_types]
        )

        for (profile_type, key) in profile_ids:
            try:
                data[key] = str(ip.get_profile(profile_type).pk)
            except AttributeError:
                pass

    for p in Parameter.objects.iterator():
        data['_PARAMETER_%s' % p.entity.upper()] = p.value

    for p in Path.objects.iterator():
        data['_PATH_%s' % p.entity.upper()] = p.value

    without_underscores = _remove_leading_underscores(data)
    data.update(without_underscores)
    return data
