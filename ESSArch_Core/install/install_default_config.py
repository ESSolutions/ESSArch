# -*- coding: UTF-8 -*-

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

import django
django.setup()

from ESSArch_Core.configuration.models import EventType, Parameter

def installDefaultConfiguration():
    print "Installing event types..."
    installDefaultEventTypes()
    print "Installing parameters..."
    installDefaultParameters()

    return 0

def installDefaultEventTypes():
    dct = {
        'Prepared IP': '10100',
        'Created IP root directory': '10200',
        'Created physical model': '10300',
        'Created SIP': '10400',
        'Submitted SIP': '10500',

        'Delivery received': '20100',
        'Delivery checked': '20200',
        'Delivery registered': '20300',
        'Delivery registered in journal system': '20310',
        'Delivery registered in archival information system': '20320',
        'Delivery receipt sent': '20400',
        'Delivery ready for hand over': '20500',
        'Delivery transferred': '20600',

        'Received the IP for long-term preservation': '30000',
        'Verified IP against archive information system': '30100',
        'Verified IP is approved for long-term preservation': '30110',
        'Created AIP': '30200',
        'Preserved AIP': '30300',
        'Cached AIP': '30310',
        'Removed the source to the SIP': '30400',
        'Removed the source to the AIP': '30410',
        'Ingest order completed': '30500',
        'Ingest order accepted': '30510',
        'Ingest order requested': '30520',
        'Created DIP': '30600',
        'DIP order requested': '30610',
        'DIP order accepted': '30620',
        'DIP order completed': '30630',
        'Moved to workarea': '30700',
        'Moved from workarea': '30710',
        'Moved to gate from workarea': '30720',

        'Unmounted the tape from drive in robot': '40100',
        'Mounted the tape in drive in robot': '40200',
        'Deactivated storage medium': '40300',
        'Quick media verification order requested': '40400',
        'Quick media verification order accepted': '40410',
        'Quick media verification order completed': '40420',
        'Storage medium delivered': '40500',
        'Storage medium received': '40510',
        'Storage medium placed': '40520',
        'Storage medium collected': '40530',
        'Storage medium robot': '40540',
        'Data written to disk storage method': '40600',
        'Data read from disk storage method': '40610',
        'Data written to tape storage method': '40700',
        'Data read from tape storage method': '40710',

        'Calculated checksum ': '50000',
        'Identified format': '50100',
        'Validated file format': '50200',
        'Validated XML file': '50210',
        'Validated logical representation against physical representation': '50220',
        'Validated checksum': '50230',
        'Virus control done': '50300',
        'Created TAR': '50400',
        'Created ZIP': '50410',
        'Updated IP status': '50500',
        'Updated IP path': '50510',
        'Generated XML file': '50600',
        'Appended events': '50610',
        'Copied schemas': '50620',
        'Uploaded file': '50700',
        'Deleted files': '50710',
        'Unpacked object': '50720',
        'Converted RES to PREMIS': '50730',
        'Deleted IP': '50740',
    }

    for key in dct:
        print '-> %s: %s' % (key, dct[key])
        EventType.objects.get_or_create(eventType=dct[key], eventDetail=key)

    return 0

def installDefaultParameters():
    dct = {
        'agent_identifier_type': 'ESS',
        'event_identifier_type': 'ESS',
        'linking_agent_identifier_type': 'ESS',
        'linking_object_identifier_type': 'ESS',
        'agent_identifier_type': 'ESS',
        'object_identifier_type': 'ESS',
        'related_object_identifier_type': 'ESS',
    }

    for key in dct:
        print '-> %s: %s' % (key, dct[key])
        Parameter.objects.get_or_create(entity=key, value=dct[key])

    return 0

if __name__ == '__main__':
    installDefaultConfiguration()
