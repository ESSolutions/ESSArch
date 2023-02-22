"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2023 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""
import django
from django.contrib.contenttypes.models import ContentType

django.setup()

from ESSArch_Core.tags.models import (  # noqa isort:skip
    StructureUnit,
    TagVersion,
)
from ESSArch_Core.ip.models import InformationPackage  # noqa isort:skip
from ESSArch_Core.auth.models import Group, GroupGenericObjects  # noqa isort:skip
from ESSArch_Core.agents.models import Agent  # noqa isort:skip
from ESSArch_Core.access.models import AccessAid  # noqa isort:skip


def migrate(klass, group):
    ctype = ContentType.objects.get_for_model(klass)
    num = 0
    total_num = GroupGenericObjects.objects.filter(group=group, content_type=ctype).count()
    for gg_obj in GroupGenericObjects.objects.filter(group=group, content_type=ctype):
        go_obj, created = group.add_object(gg_obj.content_object)
        num += 1
        if created:
            print('{} ({}) - {} object {} - added to group {}'.format(num,
                  total_num, ctype.name, gg_obj.content_object, group))
        else:
            print('{} ({}) - {} object: {} - already related to group {}'.format(
                num, total_num, ctype.name, gg_obj.content_object, group))


def main():
    for group_obj in Group.objects.filter(group_type__codename='organization'):
        print('group_obj: {}'.format(group_obj))
        migrate(InformationPackage, group_obj)
        migrate(AccessAid, group_obj)
        migrate(Agent, group_obj)
        migrate(TagVersion, group_obj)
        migrate(StructureUnit, group_obj)


# python -c 'from ESSArch_Core.install import migrate_groupgeneric_to_groupfk; migrate_groupgeneric_to_groupfk.main()'
if __name__ == '__main__':
    main()
