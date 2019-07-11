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

from setuptools import find_packages, setup
import versioneer


versioneer.VCS = 'git'
versioneer.versionfile_source = 'ESSArch_Core/_version.py'
versioneer.versionfile_build = None
versioneer.tag_prefix = ''  # tags are like 1.2.0
versioneer.parentdir_prefix = 'ESSArch_Core-'

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
        install_requires=[
            "celery[tblib]==4.3.0",
            "cffi==1.12.3",
            "channels==2.1.7",
            "channels_redis==2.3.3",
            "chardet==3.0.4",
            "click==7.0",
            "crontab==0.22.5",
            "cryptography==2.7",
            "daphne==2.2.5",
            "dj-database-url==0.5.0",
            "django==2.2.3",
            "django-cors-headers==2.5.2",
            "django-filter==2.1.0",
            "django-groups-manager==0.6.2",
            "django-guardian==2.0.0",
            "django-mptt==0.9.1",
            "django-nested-inline==0.3.7",
            "django-picklefield==2.0",
            "django-redis==4.10.0",
            "django-rest-auth[with_social]==0.9.5",
            "djangorestframework==3.9.4",
            "drf-dynamic-fields==0.3.1",
            "drf-extensions==0.4.0",
            "drf-proxy-pagination==0.2.0",
            "elasticsearch-dsl==6.3.1",
            "glob2==0.7",
            "jsonfield==2.0.2",
            "lxml==4.3.4",
            "natsort==6.0.0",
            "opf-fido==1.3.12",
            "pyfakefs==3.5.8",
            "python-dateutil==2.8.0",
            "pywin32==224;platform_system=='Windows'",
            "redis==3.2.1",
            "regex==2018.08.29",
            "requests==2.22.0",
            "requests_toolbelt==0.9.1",
            "tenacity==5.0.4",
            "wand==0.5.5",
            "weasyprint==46",
        ],
        extras_require={
            "docs": ["sphinx==1.8.5", "sphinx-intl==0.9.11",
                     "sphinx-rtd-theme==0.4.3", "sphinxcontrib-httpdomain==1.7.0",
                     "sphinxcontrib-httpexample==0.10.3",
                     "sphinxcontrib-inlinesyntaxhighlight==0.2"],
            "tests": ["coverage==4.5.3", "fakeredis[lua]==1.0.3", "django-test-without-migrations==0.6"],
            "s3": ["boto3==1.9.186"],
            "ldap": ["django-auth-ldap==2.0.0"],
            "saml2": ["djangosaml2==0.17.2"],
            "libreoffice_file_conversion": ["unoconv==0.8.2"],
            "ms_office_file_conversion": ["comtypes==1.1.7;platform_system=='Windows'"],
            "iis": ["wfastcgi==3.0.0"],
            "mssql": ["django-mssql-backend==2.2.0"],
            "mysql": ["mysqlclient==1.3.13"],
            "postgres": ["psycopg2==2.7.5"],
            "logstash": ["python-logstash-async==1.5.0"],
        },
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
