"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'ESSArch_Core/_version.py'
versioneer.versionfile_build = None
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'ESSArch_Core-'

from setuptools import find_packages, setup
from setuptools.command.install import install as _install
import sys
from pkg_resources import require as pkg_check, DistributionNotFound, VersionConflict

try:
    input = raw_input
except NameError:
    pass

# ESSArch_Core dependencies
dependencies = [
  'ESSArch-EPP>=2.8.4,<=2.8.5',
  'ESSArch-PP>=3.0.0.*,<=3.0.1.*',
  'ESSArch-TA>=1.0.3.*,<=1.2.1.*',
  'ESSArch-TP>=1.0.3.*,<=1.2.1.*',
]


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write('\n' + question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def dependencies_check(dependencies):
    try:
        pkg_check(dependencies)
    except VersionConflict as e:
        print ('Warning! You are trying to install a version of ESSArch_Core \
incompatible with other software versions. If you continue, you \
will also need to upgrade other software versions as: %s' % e)
        if not query_yes_no('Do you want to continue with the installation?'):
            print ('Cancel the installation...')
            sys.exit(1)
    except DistributionNotFound as e:
        pass


def _pre_install():
    print ('Running inside _pre_install')
    dependencies_check(dependencies)


def _post_install():
    print ('Running inside _post_install')


class my_install(_install):
    def run(self):
        self.execute(_pre_install, [],
             msg="Running pre install task")

        _install.run(self)

        # the second parameter, [], can be replaced with a set of parameters if _post_install needs any
        self.execute(_post_install, [],
                     msg="Running post install task")


if __name__ == '__main__':
    cmdclass=versioneer.get_cmdclass()
    cmdclass.update({'install': my_install})
    setup(
        name='ESSArch_Core',
        version=versioneer.get_version(),
        description='ESSArch Core',
        author='Henrik Ek',
        author_email='info@essolutions.se',
        url='http://www.essolutions.se',
        install_requires=[
            "celery==4.2.1",
            "cffi==1.11.5",
            "channels==2.1.5",
            "channels_redis==2.3.1",
            "chardet>=3.0.2,<3.1.0",
            "crontab==0.22.2",
            "daphne==2.2.3",
            "django>=1.11,<1.12",
            "django-cors-headers==2.4.0",
            "django-filter==1.1",
            "django-groups-manager==0.6.0",
            "django-guardian==1.4.9",
            "django-jsonfield==1.0.1",
            "django-mptt==0.9.1",
            "django-nested-inline==0.3.7",
            "django-picklefield==1.1.0",
            "django-redis==4.9.0",
            "django-rest-auth[with_social]==0.9.3",
            "djangorestframework>=3.8,<3.9",
            "drf-dynamic-fields==0.3.0",
            "drf-extensions>=0.4,<0.5",
            "drf-proxy-pagination==0.1.1",
            "elasticsearch-dsl==6.2.1",
            "glob2==0.6",
            "httpretty==0.9.5",
            "jsonpickle==1.0",
            "lxml>=4.2,<4.3",
            "mock==2.0.0",
            "natsort==5.4.1",
            "opf-fido==1.3.7",
            "pyfakefs==3.4.3",
            "redis==2.10.6",
            "regex==2018.08.29",
            "requests==2.20.0",
            "requests_toolbelt==0.8.0",
            "retrying==1.3.3",
            "scandir==1.9.0",
            "six==1.10.0",
            "weasyprint==43",
        ],
        extras_require={
            "docs": ["sphinx==1.8.1", "sphinx-intl==0.9.11",
                "sphinx-rtd-theme==0.4.1", "sphinxcontrib-httpdomain==1.7.0",
                "sphinxcontrib-httpexample==0.9.1",
                "sphinxcontrib-inlinesyntaxhighlight==0.2"],
            "tests": ["fakeredis==0.14.0"],
            "s3":  ["boto3==1.9.14"],
            "ldap":  ["django-auth-ldap>=1.7,<1.8"],
            "saml2":  ["djangosaml2>=0.17,<0.18"],
            "libreoffice_file_conversion":  ["unoconv>=0.8,<0.9"],
            "ms_office_file_conversion":  ["comtypes>=1.1,<1.2;platform_system=='Windows'"],
            "iis": ["wfastcgi==3.0.0"],
            "mssql": ["django-pyodbc-azure==1.11.15.0"],
            "mysql": ["mysqlclient==1.3.13"],
            "postgres": ["psycopg2==2.7.5"],
        },
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
