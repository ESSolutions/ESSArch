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

from setuptools import setup

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
    setup(
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
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
    )
