import django

django.setup()
from ESSArch_Core.tags.models import (  # noqa isort:skip
    StructureUnitGroupObjects,
    TagVersionGroupObjects,
    TagVersionType,
)
from ESSArch_Core.ip.models import InformationPackageGroupObjects  # noqa isort:skip
from ESSArch_Core.agents.models import Agent, AgentGroupObjects  # noqa isort:skip
from ESSArch_Core.access.models import AccessAidGroupObjects  # noqa isort:skip

# agent_id = '80cf7d20-e727-46d1-84d0-f5814612b245'
# agent_id = '4f5ba552-1e8a-4566-8224-d410213467a6'
agent_id = 'd85f8fbd-2ee1-4f10-b15f-7405d94fde10'

print_agent_without_group = True
print_archive_without_group = True
print_structure_without_group = False
print_node_without_group = False
print_ip_without_group = True
print_aid_without_group = True

tv_type_aip = TagVersionType.objects.get(name='AIP')
agent_obj = Agent.objects.get(id=agent_id)
try:
    group = agent_obj.get_organization().group
    print('Agent: {}, group: {}'.format(agent_obj, group))
except AgentGroupObjects.DoesNotExist:
    if print_agent_without_group:
        print('Agent: {}, group: {}'.format(agent_obj, 'XXXXXXXXXXXXXXX'))
for tva_obj in agent_obj.tags.all():
    try:
        group = tva_obj.get_organization().group
        print('Archive (tva_obj): {}, group: {}'.format(tva_obj, group))
    except TagVersionGroupObjects.DoesNotExist:
        if print_archive_without_group:
            print('Archive (tva_obj): {}, group: {}'.format(tva_obj, 'XXXXXXXXXXXXXXX'))
    for st_obj in tva_obj.get_structures().all():
        for su_obj in st_obj.structure.units.all():
            try:
                group = su_obj.get_organization().group
                print('Structure (su_obj): {}, group: {}'.format(su_obj, group))
            except StructureUnitGroupObjects.DoesNotExist:
                if print_structure_without_group:
                    print('Structure (su_obj): {}, group: {}'.format(su_obj, 'XXXXXXXXXXXXXXX'))
            for ts_obj in su_obj.tagstructure_set.all():
                tag_obj = ts_obj.tag
                for tv_obj in tag_obj.versions.all():
                    try:
                        group = tv_obj.get_organization().group
                        print('Node (tv_obj): {}, group: {}'.format(tv_obj, group))
                    except TagVersionGroupObjects.DoesNotExist:
                        if print_node_without_group:
                            print('Node (tv_obj): {}, group: {}'.format(tv_obj, 'XXXXXXXXXXXXXXX'))
                if tag_obj.current_version.type == tv_type_aip and tag_obj.information_package:
                    try:
                        group = tag_obj.information_package.get_organization().group
                        print('IP (ip_obj): {}, group: {}'.format(tag_obj, group))
                    except InformationPackageGroupObjects.DoesNotExist:
                        if print_ip_without_group:
                            print('IP (ip_obj): {}, group: {}'.format(tag_obj, 'XXXXXXXXXXXXXXX'))
            for aid_obj in su_obj.access_aids.all():
                try:
                    group = aid_obj.get_organization().group
                    print('AID (aid_obj): {}, group: {}'.format(aid_obj, group))
                except AccessAidGroupObjects.DoesNotExist:
                    if print_aid_without_group:
                        print('AID (aid_obj): {}, group: {}'.format(aid_obj, 'XXXXXXXXXXXXXXX'))
