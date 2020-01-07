import collections
from collections.abc import Mapping

from django.core.exceptions import ObjectDoesNotExist

from ESSArch_Core.configuration.models import Parameter, Path

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


class LazyDict(Mapping):
    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key):
        val = self._raw_dict.__getitem__(key)
        if isinstance(val, tuple) and callable(val[0]):
            func, *args = val
            return func(*args)

        return val

    def __setitem__(self, key, value):
        if key.startswith('_'):
            self._raw_dict.__setitem__(key, value)
            self._raw_dict.__setitem__(key[1:], value)
        else:
            return self._raw_dict.__setitem__(key, value)

    def to_dict(self):
        d = {}
        for k, v in self._raw_dict.items():
            d[k] = v
        return d

    def copy(self):
        return LazyDict(self._raw_dict.copy())

    def update(self, data):
        data.update(_remove_leading_underscores(data))
        return self._raw_dict.update(data)

    def __iter__(self):
        return iter(self._raw_dict)

    def __len__(self):
        return len(self._raw_dict)


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


def _get_profile_id_by_type(profile_type, ip):
    try:
        return str(ip.get_profile(profile_type).pk)
    except AttributeError:
        return None


def _get_agents(ip):
    agents = {}

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
        agents[agent_key] = agent

    return agents


def fill_specification_data(data=None, sa=None, ip=None, ignore=None):
    data = data or {}
    ignore = ignore or []

    data = LazyDict(data)

    if sa:
        data.update(_fill_sa_specification_data(sa))

    if ip:
        if not sa and ip.submission_agreement is not None:
            sa = ip.submission_agreement
            data.update(_fill_sa_specification_data(sa))

        if ip.submission_agreement_data is not None:
            for k, v in ip.submission_agreement_data.data.items():
                data['SA_{}'.format(k)] = v

        data['_OBJID'] = ip.object_identifier_value
        data['_OBJUUID'] = str(ip.pk)
        data['_OBJLABEL'] = ip.label
        data['_OBJPATH'] = ip.object_path
        data['_INNER_IP_OBJID'] = ip.sip_objid
        data['_INNER_IP_PATH'] = ip.sip_path
        data['_STARTDATE'] = ip.start_date
        data['_ENDDATE'] = ip.end_date
        data['_INFORMATIONCLASS'] = ip.information_class

        if '_CTS_PATH' not in ignore:
            data['_CTS_PATH'] = (ip.get_content_type_file,)
        if '_CTS_SCHEMA_PATH' not in ignore:
            data['_CTS_SCHEMA_PATH'] = (ip.get_content_type_schema_file,)

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

        data['_TEMP_CONTAINER_PATH'] = (ip.get_temp_container_path,)
        data['_TEMP_METS_PATH'] = (ip.get_temp_container_xml_path,)
        data['_TEMP_AIC_METS_PATH'] = (ip.get_temp_container_aic_xml_path,) if ip.aic else None

        if ip.get_package_type_display() in ['SIP', 'DIP', 'AIP']:
            data['_PREMIS_PATH'] = (ip.get_premis_file_path,)
            data['allow_unknown_file_types'] = (ip.get_allow_unknown_file_types,)

        data['_IP_CONTAINER_FORMAT'] = (ip.get_container_format,)
        data['_IP_PACKAGE_TYPE'] = ip.get_package_type_display()

        if ip.policy is not None:
            data['_POLICYUUID'] = ip.policy.pk
            data['_POLICYID'] = ip.policy.policy_id
            data['_POLICYNAME'] = ip.policy.policy_name
            data['POLICY_INGEST_PATH'] = ip.policy.ingest_path.value
        else:
            try:
                transfer_project_data = ip.get_profile_data('transfer_project')
                data['_POLICYUUID'] = transfer_project_data.get('storage_policy_uuid')
                data['_POLICYID'] = transfer_project_data.get('storage_policy_id')
                data['_POLICYNAME'] = transfer_project_data.get('storage_policy_name')
            except ObjectDoesNotExist:
                pass

        data['_AGENTS'] = (_get_agents, ip,)

        profile_ids = zip(
            [x.lower().replace(' ', '_') for x in profile_types],
            ["_PROFILE_" + x.upper().replace(' ', '_') + "_ID" for x in profile_types]
        )

        for (profile_type, key) in profile_ids:
            data[key] = (_get_profile_id_by_type, profile_type, ip)

    for p in Parameter.objects.iterator():
        data['_PARAMETER_%s' % p.entity.upper()] = p.value

    for p in Path.objects.iterator():
        data['_PATH_%s' % p.entity.upper()] = p.value

    return data
