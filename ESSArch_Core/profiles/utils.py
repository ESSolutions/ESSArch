from ESSArch_Core.configuration.models import Parameter


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
]

def fill_specification_data(data={}, sa=None, ip=None):
    if sa:
        data['_SA_ID'] = str(sa.pk)
        data['_SA_NAME'] = str(sa.name)

    if ip:
        data['_OBJID'] = ip.object_identifier_value
        data['_OBJLABEL'] = ip.label
        data['_POLICYUUID'] = getattr(ip.policy, 'pk', None)
        data['_POLICYID'] = getattr(ip.policy, 'policy_id', None)
        data['_POLICYNAME'] = getattr(ip.policy, 'policy_name', None)
        data['_INFORMATIONCLASS'] = ip.information_class

        data['_OBJECT_IDENTIFIER_TYPE'] = Parameter.objects.cached('object_identifier_type')
        data['_RELATED_OBJECT_IDENTIFIER_TYPE'] = Parameter.objects.cached('related_object_identifier_type')
        data['_AGENT_IDENTIFIER_TYPE'] = Parameter.objects.cached('agent_identifier_type')

        if ip.archivist_organization:
            data['_IP_ARCHIVIST_ORGANIZATION'] = ip.archivist_organization.name

        if ip.archival_institution:
            data['_IP_ARCHIVAL_INSTITUTION'] = ip.archival_institution.name

        if ip.archival_type:
            data['_IP_ARCHIVAL_TYPE'] = ip.archival_type.name

        if ip.archival_location:
            data['_IP_ARCHIVAL_LOCATION'] = ip.archival_location.name

        profile_ids = zip([x.lower().replace(' ', '_') for x in profile_types], ["_PROFILE_" + x.upper().replace(' ', '_') + "_ID" for x in profile_types])

        for (profile_type, key) in profile_ids:
            try:
                data[key] = str(ip.get_profile(profile_type).pk)
            except AttributeError:
                pass

    return data
