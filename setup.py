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

import os

import versioneer
from setuptools import find_packages, setup

versioneer.VCS = 'git'
versioneer.versionfile_source = 'ESSArch_Core/_version.py'
versioneer.versionfile_build = None
versioneer.tag_prefix = ''  # tags are like 1.2.0
versioneer.parentdir_prefix = 'ESSArch_Core-'


def get_requirements(env):
    path = os.path.join('requirements/{}.txt').format(env)
    with open(path) as fp:
        return [x.strip() for x in fp.read().split('\n') if not x.startswith('#')]


if __name__ == '__main__':
    cmdclass = versioneer.get_cmdclass()
    setup(
        name='ESSArch',
        version=versioneer.get_version(),
        description='ESSArch',
        long_description=open("README.md").read(),
        long_description_content_type='text/markdown',
        author='Henrik Ek',
        author_email='henrik@essolutions.se',
        url='http://www.essolutions.se',
        entry_points={
            'console_scripts': [
                'essarch = ESSArch_Core.cli.main:cli',
            ],
            'celery.result_backends': [
                'processtask = ESSArch_Core.celery.backends.database:DatabaseBackend',
            ],
        },
        project_urls={
            'Documentation': 'http://docs.essarch.org/',
            'Source Code': 'https://github.com/ESSolutions/ESSArch/tree/%s' % versioneer.get_versions()['full'],
            'Travis CI': 'https://travis-ci.org/ESSolutions/ESSArch',
        },
        classifiers=[
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Natural Language :: English",
            "Natural Language :: Swedish",
            "Operating System :: POSIX :: Linux",
            "Operating System :: Microsoft :: Windows",
            "Programming Language :: Python",
            "Framework :: Django",
            "Topic :: System :: Archiving",
        ],
        install_requires=get_requirements('base'),
        extras_require={
            "docs": get_requirements('docs'),
            "tests": get_requirements('tests'),
            "ldap": ["django-auth-ldap==2.0.0"],
            "saml2": ["djangosaml2==0.17.2"],
            "libreoffice_file_conversion": ["unoconv==0.8.2"],
            "ms_office_file_conversion": ["comtypes==1.1.7;platform_system=='Windows'"],
            "iis": ["wfastcgi==3.0.0"],
            "mssql": ["django-mssql-backend==2.2.0"],
            "mysql": ["mysqlclient==1.4.4"],
            "postgres": ["psycopg2==2.8.3"],
            "logstash": ["python-logstash-async==1.5.1"],
        },
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
