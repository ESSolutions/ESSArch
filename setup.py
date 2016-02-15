'''
    ESSArch - ESSArch is an Electronic Archive system
    Copyright (C) 2010-2014  ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
'''
 
import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'ESSArch_TP/_version.py'
versioneer.versionfile_build = None
versioneer.tag_prefix = '' # tags are like 1.2.0
versioneer.parentdir_prefix = 'ESSArch_TP-'

from setuptools import find_packages, setup  
from setuptools.command.install import install as _install  

def _post_install():  
    print 'Running inside _post_install'

class my_install(_install):  
    def run(self):
        _install.run(self)

        # the second parameter, [], can be replaced with a set of parameters if _post_install needs any
        self.execute(_post_install, [],  
                     msg="Running post install task")


if __name__ == '__main__':
    cmdclass=versioneer.get_cmdclass()
    cmdclass.update({'install': my_install})
    setup(
        name='ESSArch_TP',
        version=versioneer.get_version(),
        description='ESSArch Tools Producer',
        author='Bjorn Skog',
        author_email='info@essolutions.se',
        url='http://www.essolutions.se',
        install_requires=[
            "MySQL-python>=1.2.5",
            "pyodbc>=3.0.10",
            "pytz>=2015.4",
            "psutil>=3.2.1",
            "billiard>=3.3.0.20",
            "anyjson>=0.3.3",
            "amqp>=1.4.6",
            "kombu>=3.0.26",
            "pycparser>=2.14",
            "cffi>=1.2.1",
            "six>=1.9.0",
            "idna>=2.0",
            "pyasn1>=0.1.8",
            "enum34>=1.0.4",
            "ipaddress>=1.0.14",
            "cryptography>=1.0.1",
            "pyOpenSSL>=0.15.1",
            "pysendfile>=2.0.1",
            "nose>=1.3.7",
            "lxml>=3.4.4",
            "pyftpdlib>=1.4.0",
            "Django>=1.8.4",
            "django-picklefield>=0.3.2",
            "django-nested-inline>=0.3.5",
            "argparse>=1.3.0",
            "httplib2>=0.9.1",
            "MarkupSafe>=0.23",
            "Jinja2>=2.8",
            "Soapbox>=0.3.7",
            "django.js>=0.8.1",
            "django-eztables>=0.3.3.dev0",
            "celery>=3.1.18",
            "django-celery>=3.1.16",
            "jobtastic>=0.3.1",
            "logfileviewer>=0.6.2",
        ],
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        cmdclass=cmdclass,
    )
