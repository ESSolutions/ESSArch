"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2020 ES Solutions AB

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
    Web - https://www.essolutions.se
    Email - essarch@essolutions.se
"""

import os

from setuptools import find_packages, setup

import versioneer


def get_requirements(env):
    path = os.path.join('requirements/{}.txt').format(env)
    with open(path) as fp:
        return [x.strip() for x in fp.read().split('\n') if not x.startswith('#')]


def get_optional(name):
    for req in get_requirements('optional'):
        if req.startswith(name):
            return req

    raise ValueError('Could not find optional requirement: "{}"'.format(name))


if __name__ == '__main__':
    versions_dict = versioneer.get_versions()
    cmdclass = versioneer.get_cmdclass()
    setup(
        name='essarch',
        version=versions_dict['version'],
        description='ESSArch (ES Solutions Archive)',
        long_description=open("README.md").read(),
        long_description_content_type='text/markdown',
        author='Henrik Ek',
        author_email='henrik@essolutions.se',
        url='https://www.essolutions.se',
        entry_points={
            'console_scripts': [
                'essarch = ESSArch_Core.cli.main:cli',
            ],
            'celery.result_backends': [
                'processtask = ESSArch_Core.celery.backends.database:DatabaseBackend',
            ],
        },
        project_urls={
            'Documentation': 'https://docs.essarch.org/',
            'Source Code': 'https://github.com/ESSolutions/ESSArch/tree/%s' % versions_dict['full-revisionid'],
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
            "dev": get_requirements('dev'),
            "lint": get_requirements('lint'),
            "optional": get_requirements('optional'),
            "ldap": [get_optional("django-auth-ldap")],
            "saml2": [get_optional("djangosaml2"), get_optional("pysaml2")],
            "libreoffice_file_conversion": [get_optional("unoconv")],
            "ms_office_file_conversion": [get_optional("comtypes")],
            "iis": [get_optional("wfastcgi")],
            "apache": [get_optional("mod-wsgi")],
            "mssql": [get_optional("mssql-django")],
            "mysql": [get_optional("mysqlclient")],
            "postgres": [get_optional("psycopg2")],
            "logstash": [get_optional("python-logstash-async")],
        },
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
