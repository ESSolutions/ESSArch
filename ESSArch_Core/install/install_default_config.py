"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

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
import json
from pathlib import Path

import click
import django
from django.db import transaction

django.setup()

from pydoc import locate  # noqa isort:skip

from django.conf import settings  # noqa isort:skip
from django.contrib.auth import get_user_model  # noqa isort:skip
from django.contrib.auth.models import Permission  # noqa isort:skip
from django.db.models import Q  # noqa isort:skip
from groups_manager.models import GroupType  # noqa isort:skip
from elasticsearch.client import IngestClient  # noqa isort:skip
from elasticsearch_dsl.connections import get_connection  # noqa isort:skip

from ESSArch_Core.search import alias_migration  # noqa isort:skip
from ESSArch_Core.auth.models import Group, GroupMemberRole, Member  # noqa isort:skip
from ESSArch_Core.configuration.models import (  # noqa isort:skip
    EventType,
    Feature,
    Parameter,
    Path as cmPath,
    Site,
    StoragePolicy,
    MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT,
)
from ESSArch_Core.storage.models import (  # noqa isort:skip
    DISK,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)

User = get_user_model()


def installDefaultConfiguration():

    installDefaultFeatures()
    installDefaultEventTypes()
    installDefaultParameters()
    installDefaultSite()
    installRoles()
    installUsers()
    installDefaultPaths()
    installDefaultStoragePolicies()
    installDefaultStorageMethods()
    installDefaultStorageTargets()
    installDefaultStorageMethodTargetRelations()
    installPipelines()
    installSearchIndices()

    return 0


def installDefaultFeatures():
    click.echo('Installing default features:')

    features = [
        {
            'name': 'archival descriptions',
            'enabled': True,
        },
        {
            'name': 'receive',
            'enabled': True,
        },
        {
            'name': 'transfer',
            'enabled': False,
        },
    ]

    for feature in features:
        click.secho('- {}... '.format(feature['name']), nl=False)
        f, _ = Feature.objects.get_or_create(
            name=feature['name'],
            defaults={
                'enabled': feature['enabled'],
                'description': feature.get('description', ''),
            }
        )
        click.secho('enabled' if f.enabled else 'disabled', fg='green' if f.enabled else 'red')

    return


def sync_event_types(event_definitions, dry_run=False, update_existing=False, remove_extra=False):
    """
    Sync EventType objects.

    event_definitions = {
        "Event detail": {
            "eventType": "10100",
            "category": EventType.CATEGORY_...
        },
        ...
    }
    """

    mode = "DRY-RUN" if dry_run else "APPLY"
    click.secho(
        f"\nSyncing event types [{mode}]",
        fg="cyan",
        bold=True,
    )

    if remove_extra:
        click.secho("  Extra events WILL be removed", fg="yellow")
    else:
        click.echo("  Extra events will NOT be removed")

    # --------------------------------
    # Desired state
    # --------------------------------
    desired_by_code = {
        v["eventType"]: {
            "eventDetail": k,
            "category": v["category"],
        }
        for k, v in event_definitions.items()
    }

    desired_codes = set(desired_by_code.keys())

    # --------------------------------
    # Existing state
    # --------------------------------
    existing_events = EventType.objects.all()
    existing_by_code = {e.eventType: e for e in existing_events}
    existing_codes = set(existing_by_code.keys())

    # --------------------------------
    # Diff
    # --------------------------------
    to_create = desired_codes - existing_codes
    to_check = desired_codes & existing_codes
    extra = existing_codes - desired_codes

    created = updated = unchanged = removed = 0

    # --------------------------------
    # Create missing
    # --------------------------------
    for code in to_create:
        data = desired_by_code[code]
        click.secho(
            f"  [+] {'Would create' if dry_run else 'Created'}: "
            f"{code} - {data['eventDetail']}",
            fg="green",
        )

        if not dry_run:
            EventType.objects.create(
                eventType=code,
                eventDetail=data["eventDetail"],
                category=data["category"],
            )
        created += 1

    # --------------------------------
    # Update / verify existing
    # --------------------------------
    for code in to_check:
        obj = existing_by_code[code]
        data = desired_by_code[code]

        changes = {}

        if obj.eventDetail != data["eventDetail"]:
            changes["eventDetail"] = (obj.eventDetail, data["eventDetail"])

        if obj.category != data["category"]:
            changes["category"] = (obj.category, data["category"])

        if changes:
            click.secho(
                f"  [~] {'Would update' if (dry_run or not update_existing) else 'Updated'}: {code}",
                fg="yellow",
            )
            for field, (old, new) in changes.items():
                click.echo(f"      - {field}: '{old}' → '{new}'")

            if not (dry_run or not update_existing):
                for field, (_, new) in changes.items():
                    setattr(obj, field, new)
                obj.save()

            updated += 1
        else:
            click.echo(f"  [=] OK: {code} - {obj.eventDetail}")
            unchanged += 1

    # --------------------------------
    # Extra events
    # --------------------------------
    for code in extra:
        obj = existing_by_code[code]
        msg = f"  [!] Extra: {code} - {obj.eventDetail}"

        if remove_extra:
            click.secho(
                msg + (f" → {'Would delete' if dry_run else 'Deleted'}"),
                fg="red",
            )
            if not dry_run:
                obj.delete()
            removed += 1
        else:
            click.secho(msg, fg="yellow")

    # --------------------------------
    # Summary
    # --------------------------------
    click.secho("\nSummary", bold=True)
    click.echo(f"  Created:   {created}")
    click.echo(f"  Updated:   {updated}")
    click.echo(f"  Unchanged: {unchanged}")
    click.echo(f"  Extra:     {len(extra)}")
    click.echo(f"  Removed:   {removed}")

    if dry_run:
        click.secho("\nDry-run complete - no changes were made.", fg="blue")
    else:
        click.secho("\nEvent type sync complete.", fg="green")


def installDefaultEventTypes(dry_run=False, update_existing=False, remove_extra=False):
    click.echo("Installing event types...")

    ip_cat = EventType.CATEGORY_INFORMATION_PACKAGE
    delivery_cat = EventType.CATEGORY_DELIVERY

    event_definitions = {
        'Prepared IP': {'eventType': 10100, 'category': ip_cat},
        'Created IP root directory': {'eventType': 10200, 'category': ip_cat},
        'Created physical model': {'eventType': 10300, 'category': ip_cat},
        'Created SIP': {'eventType': 10400, 'category': ip_cat},
        'Submitted SIP': {'eventType': 10500, 'category': ip_cat},

        'Delivery received': {'eventType': 20100, 'category': delivery_cat},
        'Delivery checked': {'eventType': 20200, 'category': delivery_cat},
        'Delivery registered': {'eventType': 20300, 'category': delivery_cat},
        'Delivery registered in journal system': {'eventType': 20310, 'category': delivery_cat},
        'Delivery registered in archival information system': {'eventType': 20320, 'category': delivery_cat},
        'Delivery receipt sent': {'eventType': 20400, 'category': delivery_cat},
        'Delivery ready for hand over': {'eventType': 20500, 'category': delivery_cat},
        'Delivery transferred': {'eventType': 20600, 'category': delivery_cat},
        'Delivery approved': {'eventType': 20700, 'category': delivery_cat},
        'Delivery rejected': {'eventType': 20800, 'category': delivery_cat},

        'Received the IP for long-term preservation': {'eventType': 30000, 'category': ip_cat},
        'Verified IP against archive information system': {'eventType': 30100, 'category': ip_cat},
        'Verified IP is approved for long-term preservation': {'eventType': 30110, 'category': ip_cat},
        'Created AIP': {'eventType': 30200, 'category': ip_cat},
        'Preserved AIP': {'eventType': 30300, 'category': ip_cat},
        'Cached AIP': {'eventType': 30310, 'category': ip_cat},
        'Clean up SIP preparation files': {'eventType': 30400, 'category': ip_cat},
        'Clean up AIP preparation files': {'eventType': 30410, 'category': ip_cat},
        'Ingest order completed': {'eventType': 30500, 'category': ip_cat},
        'Ingest order accepted': {'eventType': 30510, 'category': ip_cat},
        'Ingest order requested': {'eventType': 30520, 'category': ip_cat},
        'Created DIP': {'eventType': 30600, 'category': ip_cat},
        'DIP order requested': {'eventType': 30610, 'category': ip_cat},
        'DIP order accepted': {'eventType': 30620, 'category': ip_cat},
        'DIP order completed': {'eventType': 30630, 'category': ip_cat},
        'Moved to workspace': {'eventType': 30700, 'category': ip_cat},
        'Moved from workspace': {'eventType': 30710, 'category': ip_cat},
        'Moved to gate from workspace': {'eventType': 30720, 'category': ip_cat},
        'Retrieved from storage': {'eventType': 30800, 'category': ip_cat},

        'Unmounted the tape from drive in robot': {'eventType': 40100, 'category': ip_cat},
        'Mounted the tape in drive in robot': {'eventType': 40200, 'category': ip_cat},
        'Deactivated storage medium': {'eventType': 40300, 'category': ip_cat},
        'Quick media verification order requested': {'eventType': 40400, 'category': ip_cat},
        'Quick media verification order accepted': {'eventType': 40410, 'category': ip_cat},
        'Quick media verification order completed': {'eventType': 40420, 'category': ip_cat},
        'Storage medium delivered': {'eventType': 40500, 'category': ip_cat},
        'Storage medium received': {'eventType': 40510, 'category': ip_cat},
        'Storage medium placed': {'eventType': 40520, 'category': ip_cat},
        'Storage medium collected': {'eventType': 40530, 'category': ip_cat},
        'Storage medium robot': {'eventType': 40540, 'category': ip_cat},
        'Data written to disk storage method': {'eventType': 40600, 'category': ip_cat},
        'Data read from disk storage method': {'eventType': 40610, 'category': ip_cat},
        'Data written to CAS storage method': {'eventType': 40620, 'category': ip_cat},
        'Data read from CAS storage method': {'eventType': 40630, 'category': ip_cat},
        'Data written to tape storage method': {'eventType': 40700, 'category': ip_cat},
        'Data read from tape storage method': {'eventType': 40710, 'category': ip_cat},

        'Calculated checksum ': {'eventType': 50000, 'category': ip_cat},
        'Identified format': {'eventType': 50100, 'category': ip_cat},
        'Validated file format': {'eventType': 50200, 'category': ip_cat},
        'Validated XML file': {'eventType': 50210, 'category': ip_cat},
        'Redundancy check': {'eventType': 50220, 'category': ip_cat},
        'Validated checksum': {'eventType': 50230, 'category': ip_cat},
        'Compared XML files': {'eventType': 50240, 'category': ip_cat},
        'Virus control done': {'eventType': 50300, 'category': ip_cat},
        'Created TAR': {'eventType': 50400, 'category': ip_cat},
        'Created ZIP': {'eventType': 50410, 'category': ip_cat},
        'Updated IP status': {'eventType': 50500, 'category': ip_cat},
        'Updated IP path': {'eventType': 50510, 'category': ip_cat},
        'Generated XML file': {'eventType': 50600, 'category': ip_cat},
        'Appended events': {'eventType': 50610, 'category': ip_cat},
        'Copied schemas': {'eventType': 50620, 'category': ip_cat},
        'Parsed events file': {'eventType': 50630, 'category': ip_cat},
        'Uploaded file': {'eventType': 50700, 'category': ip_cat},
        'Deleted files': {'eventType': 50710, 'category': ip_cat},
        'Unpacked object': {'eventType': 50720, 'category': ip_cat},
        'Converted RES to PREMIS': {'eventType': 50730, 'category': ip_cat},
        'Deleted IP': {'eventType': 50740, 'category': ip_cat},
        'Conversion': {'eventType': 50750, 'category': ip_cat},
        'Action tool': {'eventType': 50760, 'category': ip_cat},
        'Index delivery': {'eventType': 50770, 'category': ip_cat},
        'Subsume delivery': {'eventType': 50771, 'category': ip_cat},
        'AccessAid delivery': {'eventType': 50772, 'category': ip_cat},
    }

    sync_event_types(event_definitions, dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)

    return 0


def normalize_permission(permission):
    if len(permission) == 3:
        codename, app, model = permission
        return codename, app, model, None
    elif len(permission) == 4:
        return tuple(permission)
    else:
        raise ValueError(f"Invalid permission format: {permission}")


def sync_role_permissions(role, permission_defs, dry_run=False, remove_extra=False):
    """
    Sync permissions for a role.

    :param role: GroupMemberRole instance
    :param permission_defs: list of (codename, app_label, model)
    :param dry_run: if True, no DB changes are made
    :param remove_extra: if True, extra permissions are removed
    """

    mode = "DRY-RUN" if dry_run else "APPLY"
    click.secho(
        f"\nSyncing permissions for role '{role.label}' [{mode}]",
        fg="cyan",
        bold=True,
    )

    # Normalize permissions
    normalized = [normalize_permission(p) for p in permission_defs]

    requested_keys = {
        (codename, app, model)
        for codename, app, model, _ in normalized
    }

    description_lookup = {
        (codename, app, model): description
        for codename, app, model, description in normalized
    }

    all_permissions = Permission.objects.select_related("content_type").all()

    permission_lookup = {
        (p.codename, p.content_type.app_label, p.content_type.model): p
        for p in all_permissions
    }

    desired_permissions = []
    missing_in_db = []

    for key in requested_keys:
        perm = permission_lookup.get(key)
        if perm:
            desired_permissions.append(perm)
        else:
            missing_in_db.append(key)

    # --------------------------------
    # Missing permissions in DB
    # --------------------------------
    for codename, app, model in missing_in_db:
        click.secho(
            f"  [x] Missing in DB: {app}.{model}.{codename}",
            fg="red",
        )

    desired_set = set(desired_permissions)
    current_set = set(role.permissions.all())

    # --------------------------------
    # Diff
    # --------------------------------
    to_add = desired_set - current_set
    already_present = desired_set & current_set
    extra = current_set - desired_set

    # --------------------------------
    # Add missing permissions
    # --------------------------------
    if to_add:
        for perm in to_add:
            desc = description_lookup.get(
                (perm.codename, perm.content_type.app_label, perm.content_type.model)
            )
            click.secho(
                f"  [+] {'Would add' if dry_run else 'Added'}: "
                f"{perm.content_type.app_label}.{perm.codename} - {desc}",
                fg="green",
            )

        if not dry_run:
            role.permissions.add(*to_add)

    # --------------------------------
    # Existing permissions
    # --------------------------------
    for perm in already_present:
        click.echo(f"  [=] Exists: {perm.content_type.app_label}.{perm.codename}")

    # --------------------------------
    # Extra permissions
    # --------------------------------
    if extra:
        for perm in extra:
            click.secho(
                f"  [!] Extra: {perm.content_type.app_label}.{perm.codename}" +
                (" → Would remove" if dry_run else " → Removed" if remove_extra else ""),
                fg="yellow" if not remove_extra else "red"
            )

        if remove_extra and not dry_run:
            role.permissions.remove(*extra)

    # --------------------------------
    # Summary
    # --------------------------------
    click.secho("\nSummary", bold=True)
    click.echo(f"  Added:         {len(to_add)}")
    click.echo(f"  Existing:      {len(already_present)}")
    click.echo(f"  Extra:         {len(extra)}")
    click.echo(f"  Missing in DB: {len(missing_in_db)}")

    if dry_run:
        click.secho("\nDry-run complete - no changes were made.", fg="blue")
    else:
        click.secho("\nPermission sync complete.", fg="green")


def get_or_create_role(label, aliases=None):
    aliases = aliases or []

    query = Q(label=label)
    for alias in aliases:
        query |= Q(label=alias)

    try:
        role = GroupMemberRole.objects.get(query)
        click.secho(f"-> role '{label}' already exists", fg="yellow")
    except GroupMemberRole.MultipleObjectsReturned:
        click.secho(f"-> multiple roles found for '{label}'", fg="red")
        role = GroupMemberRole.objects.filter(query).first()
    except GroupMemberRole.DoesNotExist:
        click.echo(f"-> installing role '{label}'")
        role, _ = GroupMemberRole.objects.get_or_create(label=label)

    return role


def installRoles(dry_run=False, remove_extra=False, config_file=None, root_dir=None):
    click.echo("Installing roles...")

    if not root_dir:
        root_dir = Path(__file__).resolve().parent.parent

    if not config_file:
        config_file = 'templates/roles_permissions.json'

    config_path = Path(root_dir) / config_file

    if not config_path.exists():
        click.secho(f"Config file not found at {config_path}", fg="red")
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, encoding="utf8") as f:
        config = json.load(f)

    created_roles = []

    for role_label, role_data in config.items():
        role = get_or_create_role(
            role_label,
            aliases=role_data.get("aliases", [])
        )

        permissions = role_data.get("permissions", [])

        sync_role_permissions(
            role,
            permissions,
            dry_run=dry_run,
            remove_extra=remove_extra,
        )

        created_roles.append(role)

    return created_roles


def sync_parameters(parameter_definitions, dry_run=False, update_existing=False, remove_extra=False):
    """
    Sync Parameter objects.

    parameter_definitions = {
        "entity": "value",
        ...
    }
    """

    mode = "DRY-RUN" if dry_run else "APPLY"
    click.secho(
        f"\nSyncing parameters [{mode}]",
        fg="cyan",
        bold=True,
    )

    if remove_extra:
        click.secho("  Extra parameters WILL be removed", fg="yellow")
    else:
        click.echo("  Extra parameters will NOT be removed")

    # --------------------------------
    # Normalize desired state
    # --------------------------------
    desired = {
        str(k).strip(): str(v).strip()
        for k, v in parameter_definitions.items()
    }

    desired_keys = set(desired.keys())

    # --------------------------------
    # Existing state
    # --------------------------------
    existing_qs = Parameter.objects.all()
    existing = {
        str(p.entity).strip(): p
        for p in existing_qs
    }
    existing_keys = set(existing.keys())

    # --------------------------------
    # Diff
    # --------------------------------
    to_create = desired_keys - existing_keys
    to_check = desired_keys & existing_keys
    extra = existing_keys - desired_keys

    created = updated = unchanged = removed = 0

    # --------------------------------
    # Create missing
    # --------------------------------
    for key in sorted(to_create):
        value = desired[key]
        click.secho(
            f"  [+] {'Would create' if dry_run else 'Created'}: "
            f"{key} = '{value}'",
            fg="green",
        )

        if not dry_run:
            Parameter.objects.create(
                entity=key,
                value=value,
            )
        created += 1

    # --------------------------------
    # Update / verify existing
    # --------------------------------
    for key in sorted(to_check):
        obj = existing[key]
        desired_value = desired[key]
        current_value = str(obj.value).strip()

        if current_value != desired_value:
            click.secho(
                f"  [~] {'Would update' if (dry_run or not update_existing) else 'Updated'}: {key}",
                fg="yellow",
            )
            click.echo(f"      - value: '{current_value}' → '{desired_value}'")

            if not (dry_run or not update_existing):
                obj.value = desired_value
                obj.save()

            updated += 1
        else:
            click.echo(f"  [=] OK: {key} = '{current_value}'")
            unchanged += 1

    # --------------------------------
    # Extra parameters
    # --------------------------------
    for key in sorted(extra):
        obj = existing[key]
        msg = f"  [!] Extra: {key} = '{obj.value}'"

        if remove_extra:
            click.secho(
                msg + (f" → {'Would delete' if dry_run else 'Deleted'}"),
                fg="red",
            )
            if not dry_run:
                obj.delete()
            removed += 1
        else:
            click.secho(msg, fg="yellow")

    # --------------------------------
    # Summary
    # --------------------------------
    click.secho("\nSummary", bold=True)
    click.echo(f"  Created:   {created}")
    click.echo(f"  Updated:   {updated}")
    click.echo(f"  Unchanged: {unchanged}")
    click.echo(f"  Extra:     {len(extra)}")
    click.echo(f"  Removed:   {removed}")

    if dry_run:
        click.secho("\nDry-run complete - no changes were made.", fg="blue")
    else:
        click.secho("\nParameter sync complete.", fg="green")


def installDefaultParameters(dry_run=False, update_existing=False, remove_extra=False):
    click.echo("Installing parameters...")

    site_name = 'Site-X'
    parameter_definitions = {
        'agent_identifier_type': 'ESS',
        'agent_identifier_value': 'ESS',
        'event_identifier_type': 'ESS',
        'linking_agent_identifier_type': 'ESS',
        'linking_object_identifier_type': 'ESS',
        'object_identifier_type': 'ESS',
        'related_object_identifier_type': 'ESS',
        'site_name': site_name,
        'medium_location': 'Media_%s' % site_name,
    }

    sync_parameters(parameter_definitions, dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)

    return 0


def installDefaultSite():
    click.echo("Installing site...")

    Site.objects.get_or_create(name='ESSArch')


def sync_membership_roles(group_member, desired_roles, dry_run=False, remove_extra=False):
    current_roles = set(group_member.roles.all())

    to_add = desired_roles - current_roles
    to_remove = current_roles - desired_roles

    for role in to_add:
        click.secho(f"      [+] Role add: {role.label} in {group_member.group.name}", fg="green")

    for role in to_remove:
        if remove_extra:
            click.secho(f"      [-] Role remove: {role.label} in {group_member.group.name}", fg="red")
        else:
            click.secho(f"      [!] Extra Role: {role.label} in {group_member.group.name}", fg="yellow")

    if not dry_run:
        if to_add:
            group_member.roles.add(*to_add)

        if remove_extra and to_remove:
            group_member.roles.remove(*to_remove)


def sync_user_fields(user, user_data, dry_run=False, update_passwords=False, is_new_user=False):
    changes = []

    field_mapping = {
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "email": user_data.get("email", ""),
        "is_staff": user_data.get("is_staff", False),
        "is_superuser": user_data.get("is_superuser", False),
    }

    for field, new_value in field_mapping.items():
        old_value = getattr(user, field)
        if old_value != new_value:
            changes.append((field, old_value, new_value))
            setattr(user, field, new_value)

    # Password handling
    if "password" in user_data:
        if is_new_user or update_passwords:
            if not user.check_password(user_data["password"]):
                user.set_password(user_data["password"])
                changes.append(("password", "***", "***"))

    # Output changes
    for field, old, new in changes:
        if is_new_user:
            click.secho(
                f"   [+] Set {field}: {new}",
                fg="green"
            )
        else:
            click.secho(
                f"   [~] Update {field}: {old} → {new}",
                fg="yellow"
            )

    if changes and not dry_run:
        user.save()

    return changes


def sync_user(
    user_data,
    role_lookup,
    organization_type,
    org_cache,
    dry_run=False,
    remove_extra=False,
    update_existing=False,
    update_passwords=False,
):
    username = user_data["username"]

    user, created = User.objects.get_or_create(username=username)

    if created:
        click.secho(f"-> Creating user '{username}'", fg="green")
    else:
        click.secho(f"-> User '{username}' already exists", fg="yellow")

    # --------------------------------
    # Update user fields
    # --------------------------------
    if created or update_existing:
        sync_user_fields(user, user_data, dry_run=dry_run, update_passwords=update_passwords,
                         is_new_user=created)

    # Ensure Member exists
    member, _ = Member.objects.get_or_create(django_user=user)

    # --------------------------------
    # Desired orgs from JSON
    # --------------------------------
    desired_orgs = {
        org["name"]: org.get("roles", [])
        for org in user_data.get("organizations", [])
    }

    # Current memberships
    current_memberships = {
        gm.group.name: gm
        for gm in member.group_membership.select_related("group").all()
        if gm.group.group_type and
        gm.group.group_type.codename == "organization"
    }

    # --------------------------------
    # Add or update memberships
    # --------------------------------
    for org_name, role_names in desired_orgs.items():

        if org_name not in org_cache:
            org, _ = Group.objects.get_or_create(
                name=org_name,
                group_type=organization_type
            )
            org_cache[org_name] = org

        organization = org_cache[org_name]

        desired_roles = {
            role_lookup[r]
            for r in role_names
            if r in role_lookup
        }

        if org_name not in current_memberships:
            click.secho(
                f"   [+] Add membership '{org_name}' roles={role_names}",
                fg="green"
            )

            if not dry_run:
                gm = organization.add_member(member, roles=list(desired_roles))
        else:
            gm = current_memberships[org_name]
            sync_membership_roles(
                gm,
                desired_roles,
                dry_run=dry_run,
                remove_extra=remove_extra,
            )

    # --------------------------------
    # Remove extra memberships
    # --------------------------------
    for org_name, gm in current_memberships.items():
        if org_name not in desired_orgs:
            if remove_extra:
                click.secho(f"   [-] Remove membership '{org_name}'", fg="red")
            else:
                click.secho(f"   [!] Extra membership '{org_name}'", fg="yellow")
            if not dry_run and remove_extra:
                gm.delete()


def installUsers(
    dry_run=False,
    remove_extra=False,
    update_existing=False,
    update_passwords=False,
    config_file=None,
    root_dir=None,
):
    click.echo("Syncing users from JSON config...")

    if not root_dir:
        root_dir = Path(__file__).resolve().parent.parent

    if not config_file:
        config_file = "templates/users.json"

    config_path = Path(root_dir) / config_file

    if not config_path.exists():
        raise FileNotFoundError(f"Users config not found at {config_path}")

    with open(config_path, encoding="utf8") as f:
        config = json.load(f)

    users_data = config.get("users", [])

    # Collect all role codenames from JSON
    role_names = {
        role
        for user in users_data
        for org in user.get("organizations", [])
        for role in org.get("roles", [])
    }

    # Fetch roles from DB
    roles = GroupMemberRole.objects.filter(label__in=role_names)
    role_lookup = {role.label: role for role in roles}

    missing_roles = role_names - set(role_lookup.keys())
    if missing_roles:
        raise ValueError(f"Missing roles in database: {missing_roles}")

    organization_type, _ = GroupType.objects.get_or_create(label="organization")

    org_cache = {}

    with transaction.atomic():

        for user_data in users_data:
            sync_user(
                user_data,
                role_lookup,
                organization_type,
                org_cache,
                dry_run=dry_run,
                remove_extra=remove_extra,
                update_existing=update_existing,
                update_passwords=update_passwords,
            )

    click.secho("\nUser sync complete.", fg="green")


def sync_paths(path_definitions, dry_run=False, update_existing=False, remove_extra=False):
    """
    Sync cmPath objects.

    path_definitions = {
        "entity": "/absolute/path",
        ...
    }
    """

    mode = "DRY-RUN" if dry_run else "APPLY"
    click.secho(
        f"\nSyncing paths [{mode}]",
        fg="cyan",
        bold=True,
    )

    if remove_extra:
        click.secho("  Extra paths WILL be removed", fg="yellow")
    else:
        click.echo("  Extra paths will NOT be removed")

    # --------------------------------
    # Normalize desired state
    # --------------------------------
    desired = {
        str(k).strip(): str(v).strip()
        for k, v in path_definitions.items()
    }

    desired_keys = set(desired.keys())

    # --------------------------------
    # Existing state
    # --------------------------------
    existing_qs = cmPath.objects.all()
    existing = {
        str(p.entity).strip(): p
        for p in existing_qs
    }
    existing_keys = set(existing.keys())

    # --------------------------------
    # Diff
    # --------------------------------
    to_create = desired_keys - existing_keys
    to_check = desired_keys & existing_keys
    extra = existing_keys - desired_keys

    created = updated = unchanged = removed = 0

    # --------------------------------
    # Create missing
    # --------------------------------
    for key in sorted(to_create):
        value = desired[key]
        click.secho(
            f"  [+] {'Would create' if dry_run else 'Created'}: "
            f"{key} = '{value}'",
            fg="green",
        )

        if not dry_run:
            cmPath.objects.create(
                entity=key,
                value=value,
            )
        created += 1

    # --------------------------------
    # Update / verify existing
    # --------------------------------
    for key in sorted(to_check):
        obj = existing[key]
        desired_value = desired[key]
        current_value = str(obj.value).strip()

        if current_value != desired_value:
            click.secho(
                f"  [~] {'Would update' if (dry_run or not update_existing) else 'Updated'}: {key}",
                fg="yellow",
            )
            click.echo(f"      - value: '{current_value}' → '{desired_value}'")

            if not (dry_run or not update_existing):
                obj.value = desired_value
                obj.save()

            updated += 1
        else:
            click.echo(f"  [=] OK: {key} = '{current_value}'")
            unchanged += 1

    # --------------------------------
    # Extra paths
    # --------------------------------
    for key in sorted(extra):
        obj = existing[key]
        msg = f"  [!] Extra: {key} = '{obj.value}'"

        if remove_extra:
            click.secho(
                msg + (f" → {'Would delete' if dry_run else 'Deleted'}"),
                fg="red",
            )
            if not dry_run:
                obj.delete()
            removed += 1
        else:
            click.secho(msg, fg="yellow")

    # --------------------------------
    # Summary
    # --------------------------------
    click.secho("\nSummary", bold=True)
    click.echo(f"  Created:   {created}")
    click.echo(f"  Updated:   {updated}")
    click.echo(f"  Unchanged: {unchanged}")
    click.echo(f"  Extra:     {len(extra)}")
    click.echo(f"  Removed:   {removed}")

    if dry_run:
        click.secho("\nDry-run complete - no changes were made.", fg="blue")
    else:
        click.secho("\nPath sync complete.", fg="green")


def installDefaultPaths(dry_run=False, update_existing=False, remove_extra=False):
    click.echo("Installing paths...")

    path_definitions = {
        'mimetypes_definitionfile': (Path(settings.CONFIG_DIR) / 'mime.types').as_posix(),
        'preingest': (Path(settings.DATA_DIR) / 'preingest/packages').as_posix(),
        'preingest_reception': (Path(settings.DATA_DIR) / 'preingest/reception').as_posix(),
        'ingest': (Path(settings.DATA_DIR) / 'ingest/packages').as_posix(),
        'ingest_reception': (Path(settings.DATA_DIR) / 'ingest/reception').as_posix(),
        'ingest_transfer': (Path(settings.DATA_DIR) / 'ingest/transfer').as_posix(),
        'ingest_unidentified': (Path(settings.DATA_DIR) / 'ingest/uip').as_posix(),
        'access_workarea': (Path(settings.DATA_DIR) / 'workspace').as_posix(),
        'ingest_workarea': (Path(settings.DATA_DIR) / 'workspace').as_posix(),
        'disseminations': (Path(settings.DATA_DIR) / 'disseminations').as_posix(),
        'orders': (Path(settings.DATA_DIR) / 'orders').as_posix(),
        'verify': (Path(settings.DATA_DIR) / 'verify').as_posix(),
        'temp': (Path(settings.DATA_DIR) / 'temp').as_posix(),
        'appraisal_reports': (Path(settings.DATA_DIR) / 'reports/appraisal').as_posix(),
        'conversion_reports': (Path(settings.DATA_DIR) / 'reports/conversion').as_posix(),
        'receipts': (Path(settings.DATA_DIR) / 'receipts').as_posix(),
        'export': (Path(settings.DATA_DIR) / 'export').as_posix(),
    }

    sync_paths(path_definitions, dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)

    return 0


def installDefaultStoragePolicies():
    click.echo("Installing storage policies...")

    cache_method, created_cache_method = StorageMethod.objects.get_or_create(
        name='Default Cache Storage Method',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': False,
        }
    )

    if created_cache_method:
        cache_target, created_cache_target = StorageTarget.objects.get_or_create(
            name='Default Cache Storage Target 1',
            defaults={
                'status': True,
                'type': DISK,
                'target': (Path(settings.DATA_DIR) / 'store/cache').as_posix(),
            }
        )

        if created_cache_target:
            StorageMedium.objects.get_or_create(
                medium_id='Default Cache Disk 1',
                defaults={
                    'storage_target': cache_target,
                    'status': 20,
                    'location': Parameter.objects.get(entity='medium_location').value,
                    'location_status': 50,
                    'block_size': cache_target.default_block_size,
                    'format': cache_target.default_format,
                    'agent': Parameter.objects.get(entity='agent_identifier_value').value,
                }
            )

        StorageMethodTargetRelation.objects.create(
            name='Default Cache Storage Method Target Relation 1',
            status=True,
            storage_method=cache_method,
            storage_target=cache_target,
        )

    ingest = cmPath.objects.get(entity='ingest')

    policy, created_policy = StoragePolicy.objects.get_or_create(
        policy_id='1',
        defaults={
            'checksum_algorithm': MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT['MD5'],
            'policy_name': 'default',
            'policy_stat': True,
            # 'cache_storage': cache_method,
            'cache_storage': None,
            'ingest_path': ingest,
            'receive_extract_sip': True,
            'cache_minimum_capacity': 0,
            'cache_maximum_age': 0,
        }
    )

    # if created_policy or created_cache_method:
    #     policy.storage_methods.add(cache_method)

    return 0


def installDefaultStorageMethods():
    click.echo("Installing storage methods...")

    sm1, _ = StorageMethod.objects.get_or_create(
        name='Default Storage Method 1',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': False,
        }
    )

    sm2, _ = StorageMethod.objects.get_or_create(
        name='Default Long-term Storage Method 1',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': True,
        }
    )

    default_policy = StoragePolicy.objects.get(policy_name='default')
    default_policy.storage_methods.add(sm1, sm2)

    return 0


def installDefaultStorageTargets():
    click.echo("Installing storage targets...")
    target, created = StorageTarget.objects.get_or_create(
        name='Default Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': (Path(settings.DATA_DIR) / 'store/disk1').as_posix(),
        }
    )

    if created:
        StorageMedium.objects.get_or_create(
            medium_id='Default Storage Disk 1',
            defaults={
                'storage_target': target,
                'status': 20,
                'location': Parameter.objects.get(entity='medium_location').value,
                'location_status': 50,
                'block_size': target.default_block_size,
                'format': target.default_format,
                'agent': Parameter.objects.get(entity='agent_identifier_value').value,
            }
        )

    target, created = StorageTarget.objects.get_or_create(
        name='Default Long-term Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': (Path(settings.DATA_DIR) / 'store/longterm_disk1').as_posix(),
        }
    )

    if created:
        StorageMedium.objects.get_or_create(
            medium_id='Default Long-term Storage Disk 1',
            defaults={
                'storage_target': target,
                'status': 20,
                'location': Parameter.objects.get(entity='medium_location').value,
                'location_status': 50,
                'block_size': target.default_block_size,
                'format': target.default_format,
                'agent': Parameter.objects.get(entity='agent_identifier_value').value,
            }
        )

    return 0


def installDefaultStorageMethodTargetRelations():
    click.echo("Installing storage method target relations...")

    StorageMethodTargetRelation.objects.get_or_create(
        name='Default Storage Method Target Relation 1',
        storage_method=StorageMethod.objects.get(name='Default Storage Method 1'),
        storage_target=StorageTarget.objects.get(name='Default Storage Target 1'),
        defaults={
            'status': True,
        }
    )

    StorageMethodTargetRelation.objects.get_or_create(
        name='Default Long-term Storage Method Target Relation 1',
        storage_method=StorageMethod.objects.get(name='Default Long-term Storage Method 1'),
        storage_target=StorageTarget.objects.get(name='Default Long-term Storage Target 1'),
        defaults={
            'status': True,
        }
    )

    return 0


def installPipelines():
    click.echo("Installing Elasticsearch pipelines...")

    conn = get_connection()
    client = IngestClient(conn)
    client.put_pipeline(id='ingest_attachment', body={
        'description': "Extract attachment information",
        'processors': [
            {
                "attachment": {
                    "field": "data",
                    "indexed_chars": "-1"
                },
                "remove": {
                    "field": "data"
                }
            }
        ]
    })
    client.put_pipeline(id='add_timestamp', body={
        'description': "Adds an index_date timestamp",
        'processors': [
            {
                "set": {
                    "field": "index_date",
                    "value": "{{_ingest.timestamp}}",
                },
            },
        ]
    })


def installSearchIndices():
    click.echo("Installing search indices...")

    for _index_name, index_class in settings.ELASTICSEARCH_INDEXES['default'].items():
        doctype = locate(index_class)
        alias_migration.setup_index(doctype)

    print('done')


if __name__ == '__main__':
    installDefaultConfiguration()
