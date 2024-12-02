"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2024 ES Solutions AB

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
import os
import sys

import click
import django
from django.core.exceptions import ObjectDoesNotExist

django.setup()

from ESSArch_Core.configuration.models import StoragePolicy  # noqa isort:skip
from ESSArch_Core.profiles.models import Profile, SubmissionAgreement  # noqa isort:skip


def installSAProfiles(nation, config_file=None, inst_dir=None):
    click.secho("Installing SA and related profiles ...", fg='green')

    if not inst_dir:
        inst_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

    nation = nation.lower()
    profile_template_path = os.path.join(inst_dir, 'templates', nation.lower())

    if not config_file:
        if nation == "se" or nation == "no" or nation == "eu":
            # Standard SA and profiles as defined by nation
            config_file = nation.upper() + '_' + 'SA.json'
        else:
            click.secho('-> You have not specified any config file', fg='red')
            return 1

    if os.path.exists(os.path.join(profile_template_path, config_file)):
        SAProfiles(profile_template_path, config_file)
    else:
        click.secho('-> You have not specified any nation (SE/NO/EU or se/no/eu) nor existing config file', fg='red')
        return 1


def SAProfiles(profile_template_path, config_file):

    sa = []

    config = json.loads(open(os.path.join(profile_template_path, config_file), encoding="utf8").read())
    profile_list = list(config.keys())

    # create SA and profiles
    for profile_description in profile_list:
        if len(config[profile_description]) != 0:
            profile_config = config[profile_description]
            profile_name = profile_config['name']

            # if profile is SA
            if profile_description == 'SA':

                profile_file = os.path.join(profile_template_path, profile_config['profile'])
                profile_spec = json.loads(open(profile_file, encoding="utf8").read())

                # check if SA already exist
                try:
                    sa = SubmissionAgreement.objects.get(name=profile_name)
                    sa_exist = sa.name
                except ObjectDoesNotExist:
                    sa_exist = []

                # SA already exist - use it
                if profile_name == sa_exist:
                    click.secho('-> Submission Agreement %s already exist - not added' % sa_exist, fg='red')
                    break
                else:
                    try:
                        policy = StoragePolicy.objects.get(policy_name=profile_config['policy'])
                    except StoragePolicy.DoesNotExist:
                        policy = StoragePolicy.objects.first()
                        if policy is None:
                            raise

                    profile_config['policy'] = policy
                    profile_config['template'] = profile_spec['template']
                    del profile_config['profile']

                    profile_name = profile_config['name']
                    sa, _ = SubmissionAgreement.objects.update_or_create(name=profile_name, defaults=profile_config)

                    click.secho('-> Installed Submission Agreement %s' % profile_name)

            else:   # if profile not SA:

                # check if profile already exist
                try:
                    sa_profile_name = Profile.objects.get(name=profile_name).name
                except ObjectDoesNotExist:
                    sa_profile_name = []

                # profile already exist - use it
                if profile_name == sa_profile_name:
                    profile_type = 'profile_' + Profile.objects.get(name=profile_name).profile_type
                    profile = Profile.objects.get(name=profile_name)

                    # if SA exist attach existing profile
                    if sa:
                        setattr(sa, profile_type, profile)
                        sa.save()
                        click.secho('-> Existing profile %s is now attached to SA %s' % (profile.name, sa.name))
                    else:
                        click.secho('-> Profile %s already exist - not added' % profile_name, fg='red')

                # if profile does not exist - add it
                if profile_name != sa_profile_name:
                    if 'profile' not in profile_config.keys():
                        click.secho('-> You have not specified profile configuration for %s in config file' %
                                    profile_name, fg='red')
                        return 1

                    profile_file = os.path.join(profile_template_path, profile_config['profile'])
                    profile_spec = json.loads(open(profile_file, encoding="utf8").read())

                    del profile_config['profile']

                    if len(profile_spec['structure']) != 0:
                        profile_config.update({'structure': profile_spec['structure']})
                    else:
                        profile_config.update({'structure': []})

                    if len(profile_spec['template']) != 0:
                        profile_config.update({'template': profile_spec['template']})
                    else:
                        profile_config.update({'template': []})

                    if len(profile_spec['specification']) != 0:
                        profile_config.update({'specification': profile_spec['specification']})
                    else:
                        profile_config.update({'specification': {}})

                    if 'specification_data' in profile_spec.keys() and len(profile_spec['specification_data']) != 0:
                        profile_config.update({'specification_data': profile_spec['specification_data']})
                    else:
                        profile_config.update({'specification_data': {}})

                    profile_type = 'profile_' + profile_config['profile_type']
                    profile, _ = Profile.objects.update_or_create(name=profile_name, defaults=profile_config)

                    # if SA exist attach added new profile
                    if sa:
                        setattr(sa, profile_type, profile)
                        sa.save()
                        click.secho('-> Installed new profile %s and attached it to SA %s' % (profile.name, sa.name))
                    else:
                        click.secho('-> Installed new profile %s' % profile_name)

    return 0


if __name__ == '__main__':
    if len(sys.argv) == 2:
        nation = sys.argv[1]
        installSAProfiles(nation)
    elif len(sys.argv) == 3:
        nation = sys.argv[1]
        config_file = sys.argv[2]
        installSAProfiles(nation, config_file)
    elif len(sys.argv) == 4:
        nation = sys.argv[1]
        config_file = sys.argv[2]
        inst_dir = sys.argv[3]
        installSAProfiles(nation, config_file, inst_dir)
    else:
        click.secho('-> You have not specified any nation (SE/NO/EU or se/no/eu)', fg='red')
