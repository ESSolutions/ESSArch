"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2021 ES Solutions AB

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

import django

django.setup()

from django.conf import settings  # noqa isort:skip
from django.core.exceptions import ObjectDoesNotExist  # noqa isort:skip

from ESSArch_Core.configuration.models import StoragePolicy  # noqa isort:skip
from ESSArch_Core.profiles.models import (  # noqa isort:skip
    SubmissionAgreement,
    Profile,
)


def installSAProfiles(config_file=None):

    if config_file:
        SAProfiles(config_file)
    else:
        SAProfiles('templates/SE_PROFILES_ESS.json')    # SE Standard profiles
        SAProfiles('templates/SE_SA_ESS.json')          # SE standard SA
        SAProfiles('templates/NO_PROFILES_ESS.json')    # NO Standard profiles
        SAProfiles('templates/NO_SA_ESS.json')          # NO standard SA
        SAProfiles('templates/EARK_PROFILES_ESS.json')  # EARK Standard profiles
        SAProfiles('templates/EARK_SA_ESS.json')        # EARK standard SA

    return 0


def SAProfiles(config_file=None):

    # Identify path
    if os.getcwd() == settings.BASE_DIR + '/install':
        inst_dir = settings.BASE_DIR
    elif os.getcwd() == '/ESSArch/config/optional':
        inst_dir = os.getcwd()
    elif os.getcwd() == '/ESSArch/config/custom':
        inst_dir = os.path.join(os.getcwd(), config_file.split('/').pop(-3).lower() + '/')
    else:
        print('Unable to proceed because you are in the wrong directory: %s' % os.getcwd())
        return None

    sa = []
    config = json.loads(open(os.path.join(config_file)).read())
    profile_list = list(config.keys())
    profile_template_path = config_file.split('/').pop(-2).lower() + '/'
    profile_nation_path = config_file.split('/').pop(-1).split('_').pop(0).lower() + '/'

    # create SA and profiles
    for profile_description in profile_list:
        if len(config[profile_description]) != 0:
            profile_config = config[profile_description]
            profile_name = profile_config['name']

            # if profile is SA
            if profile_description == 'SA':

                profile_path = os.path.join(profile_template_path, profile_nation_path, profile_config['profile'])
                profile_file = os.path.join(inst_dir, profile_path)
                profile_spec = json.loads(open(profile_file).read())

                # check if SA already exist
                try:
                    sa = SubmissionAgreement.objects.get(name=profile_name)
                    sa_exist = sa.name
                except ObjectDoesNotExist:
                    sa_exist = []

                # SA already exist - use it
                if profile_name == sa_exist:
                    print('Submission Agreement %s already exist - not added' % sa_exist)
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

                    print('Installed Submission Agreement %s' % profile_name)

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
                        print('Existing profile %s is now attached to SA %s' % (profile.name, sa_profile_name))
                    else:
                        print('Profile %s already exist - not added' % profile_name)

                # profile does not exist - add it
                if profile_name != sa_profile_name:

                    profile_path = os.path.join(profile_template_path, profile_nation_path, profile_config['profile'])
                    profile_file = os.path.join(inst_dir, profile_path)
                    profile_spec = json.loads(open(profile_file).read())

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

                    profile_type = 'profile_' + profile_config['profile_type']
                    profile, _ = Profile.objects.update_or_create(name=profile_name, defaults=profile_config)

                    # if SA exist attach added new profile
                    if sa:
                        setattr(sa, profile_type, profile)
                        sa.save()
                        print('Installed new profile %s and attached it to SA %s' % (profile.name, sa.name))
                    else:
                        print('Installed new profile %s' % profile_name)

    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        installSAProfiles(config_file)
    else:
        installSAProfiles()
