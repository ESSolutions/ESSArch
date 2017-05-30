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

# ESSArch_Core dependencies
dependencies = [
  'ESSArch-EPP>=2.8.4,<=2.8.5',
  'ESSArch-TA>=1.0.1,<=1.0.3',
  'ESSArch-TP>=1.0.2,<=1.0.3',
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
        choice = raw_input().lower()
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
        print 'Warning! You are trying to install a version of ESSArch_Core \
incompatible with other software versions. If you continue, you \
will also need to upgrade other software versions as: %s' % e
        if not query_yes_no('Do you want to continue with the installation?'):
            print 'Cancel the installation...'
            sys.exit(1)
    except DistributionNotFound as e:
        pass

def _pre_install():
    print 'Running inside _pre_install'
    dependencies_check(dependencies)

def _post_install():  
    print 'Running inside _post_install'

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
            "mysqlclient>=1.3.10",
            "pyodbc>=3.0.10",
            "pytz>=2016.6.1",
            "psutil>=3.2.1",
            "billiard>=3.3.0.23",
            "anyjson>=0.3.3",
            "amqp>=1.4.9",
            "kombu>=3.0.36",
            "pycparser>=2.14",
            "cffi>=1.2.1",
            "six>=1.10.0",
            "idna>=2.0",
            "pyasn1>=0.1.8",
            "enum34>=1.0.4",
            "ipaddress>=1.0.14",
            "cryptography>=1.0.1",
            "pyOpenSSL>=0.15.1",
            "pysendfile>=2.0.1",
            "nose>=1.3.7",
            "lxml>=3.6.4",
            "pyftpdlib>=1.4.0",
            "Django>=1.10.1",
            "django-picklefield>=0.3.2",
            "django-nested-inline>=0.3.6",
            "argparse>=1.3.0",
            "httplib2>=0.9.1",
            "MarkupSafe>=0.23",
            "Jinja2>=2.8",
            "iso8601>=0.1.11",
            "django.js>=0.8.1",
            "django-eztables>=0.3.3_347e74d",
            "celery>=3.1.24",
            "django-celery>=3.2.0a1",
            "jobtastic>=0.3.1",
            "jsonfield>=1.0.3",
            "requests>=2.11.1",
            "requests-toolbelt>=0.4.0",
            "django-cors-headers>=1.1.0",
            "django-jsonfield>=1.0.1",
            "python-openid>=2.2.5",
            "oauthlib>=2.0.0",
            "requests-oauthlib>=0.7.0",
            "django-allauth>=0.27.0",
            "djangorestframework>=3.4.6",
            "django-rest-auth>=0.8.1",
            "django-filter>=0.15.2",
            "djangorestframework-filters>=0.8.1",
            "django-chunked-upload>=1.1.1",
            "jsonpickle>=0.9.3",
            "retrying>=1.3.3",
            "django-datatables-view>=1.13.0",
            "olefile>=0.43",
            "setuptools_scm>=1.15.0",
            "pytest-runner>=2.11.1",
            "opf-fido>=1.3.5",
            "scandir>=1.3",
            "natsort>=5.0.2",
            "redis>=2.10.5",
            "django-redis>=4.7.0",
            "httpretty>=0.8.14",
            "unoconv>=0.6",
            "python-ldap>=2.4.38",
            "django-auth-ldap>=1.2.12",
            "logfileviewer>=0.6.3",
            "soapfish>=0.6.0.dev0",
        ],
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
