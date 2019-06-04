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

from ESSArch_Core.configuration.models import EventType, Parameter, Site  # noqa


def installDefaultConfiguration():
    print("Installing event types...")
    installDefaultEventTypes()
    print("Installing parameters...")
    installDefaultParameters()
    print("Installing site...")
    installDefaultSite()

    return 0


def installDefaultEventTypes():
    ip_cat = EventType.CATEGORY_INFORMATION_PACKAGE
    delivery_cat = EventType.CATEGORY_DELIVERY

    dct = {
        'Prepared IP': {'eventType': '10100', 'category': ip_cat},
        'Created IP root directory': {'eventType': '10200', 'category': ip_cat},
        'Created physical model': {'eventType': '10300', 'category': ip_cat},
        'Created SIP': {'eventType': '10400', 'category': ip_cat},
        'Submitted SIP': {'eventType': '10500', 'category': ip_cat},

        'Delivery received': {'eventType': '20100', 'category': delivery_cat},
        'Delivery checked': {'eventType': '20200', 'category': delivery_cat},
        'Delivery registered': {'eventType': '20300', 'category': delivery_cat},
        'Delivery registered in journal system': {'eventType': '20310', 'category': delivery_cat},
        'Delivery registered in archival information system': {'eventType': '20320', 'category': delivery_cat},
        'Delivery receipt sent': {'eventType': '20400', 'category': delivery_cat},
        'Delivery ready for hand over': {'eventType': '20500', 'category': delivery_cat},
        'Delivery transferred': {'eventType': '20600', 'category': delivery_cat},
        'Delivery approved': {'eventType': '20700', 'category': delivery_cat},
        'Delivery rejected': {'eventType': '20800', 'category': delivery_cat},

        'Received the IP for long-term preservation': {'eventType': '30000', 'category': ip_cat},
        'Verified IP against archive information system': {'eventType': '30100', 'category': ip_cat},
        'Verified IP is approved for long-term preservation': {'eventType': '30110', 'category': ip_cat},
        'Created AIP': {'eventType': '30200', 'category': ip_cat},
        'Preserved AIP': {'eventType': '30300', 'category': ip_cat},
        'Cached AIP': {'eventType': '30310', 'category': ip_cat},
        'Removed the source to the SIP': {'eventType': '30400', 'category': ip_cat},
        'Removed the source to the AIP': {'eventType': '30410', 'category': ip_cat},
        'Ingest order completed': {'eventType': '30500', 'category': ip_cat},
        'Ingest order accepted': {'eventType': '30510', 'category': ip_cat},
        'Ingest order requested': {'eventType': '30520', 'category': ip_cat},
        'Created DIP': {'eventType': '30600', 'category': ip_cat},
        'DIP order requested': {'eventType': '30610', 'category': ip_cat},
        'DIP order accepted': {'eventType': '30620', 'category': ip_cat},
        'DIP order completed': {'eventType': '30630', 'category': ip_cat},
        'Moved to workarea': {'eventType': '30700', 'category': ip_cat},
        'Moved from workarea': {'eventType': '30710', 'category': ip_cat},
        'Moved to gate from workarea': {'eventType': '30720', 'category': ip_cat},

        'Unmounted the tape from drive in robot': {'eventType': '40100', 'category': ip_cat},
        'Mounted the tape in drive in robot': {'eventType': '40200', 'category': ip_cat},
        'Deactivated storage medium': {'eventType': '40300', 'category': ip_cat},
        'Quick media verification order requested': {'eventType': '40400', 'category': ip_cat},
        'Quick media verification order accepted': {'eventType': '40410', 'category': ip_cat},
        'Quick media verification order completed': {'eventType': '40420', 'category': ip_cat},
        'Storage medium delivered': {'eventType': '40500', 'category': ip_cat},
        'Storage medium received': {'eventType': '40510', 'category': ip_cat},
        'Storage medium placed': {'eventType': '40520', 'category': ip_cat},
        'Storage medium collected': {'eventType': '40530', 'category': ip_cat},
        'Storage medium robot': {'eventType': '40540', 'category': ip_cat},
        'Data written to disk storage method': {'eventType': '40600', 'category': ip_cat},
        'Data read from disk storage method': {'eventType': '40610', 'category': ip_cat},
        'Data written to tape storage method': {'eventType': '40700', 'category': ip_cat},
        'Data read from tape storage method': {'eventType': '40710', 'category': ip_cat},

        'Calculated checksum ': {'eventType': '50000', 'category': ip_cat},
        'Identified format': {'eventType': '50100', 'category': ip_cat},
        'Validated file format': {'eventType': '50200', 'category': ip_cat},
        'Validated XML file': {'eventType': '50210', 'category': ip_cat},
        'Validated logical representation against physical representation': {'eventType': '50220', 'category': ip_cat},
        'Validated checksum': {'eventType': '50230', 'category': ip_cat},
        'Compared XML files': {'eventType': '50240', 'category': ip_cat},
        'Virus control done': {'eventType': '50300', 'category': ip_cat},
        'Created TAR': {'eventType': '50400', 'category': ip_cat},
        'Created ZIP': {'eventType': '50410', 'category': ip_cat},
        'Updated IP status': {'eventType': '50500', 'category': ip_cat},
        'Updated IP path': {'eventType': '50510', 'category': ip_cat},
        'Generated XML file': {'eventType': '50600', 'category': ip_cat},
        'Appended events': {'eventType': '50610', 'category': ip_cat},
        'Copied schemas': {'eventType': '50620', 'category': ip_cat},
        'Parsed events file': {'eventType': '50630', 'category': ip_cat},
        'Uploaded file': {'eventType': '50700', 'category': ip_cat},
        'Deleted files': {'eventType': '50710', 'category': ip_cat},
        'Unpacked object': {'eventType': '50720', 'category': ip_cat},
        'Converted RES to PREMIS': {'eventType': '50730', 'category': ip_cat},
        'Deleted IP': {'eventType': '50740', 'category': ip_cat},
        'Converted file': {'eventType': '50750', 'category': ip_cat},
    }

    for key, val in dct.items():
        print('-> %s: %s' % (key, val['eventType']))
        EventType.objects.update_or_create(
            eventType=val['eventType'],
            defaults={
                'eventDetail': key,
                'category': val['category'],
            },
        )

    return 0


def installDefaultParameters():
    dct = {
        'agent_identifier_type': 'ESS',
        'agent_identifier_value': 'ESS',
        'event_identifier_type': 'ESS',
        'linking_agent_identifier_type': 'ESS',
        'linking_object_identifier_type': 'ESS',
        'object_identifier_type': 'ESS',
        'related_object_identifier_type': 'ESS',
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        Parameter.objects.get_or_create(entity=key, defaults={'value': dct[key]})

    return 0


def installDefaultSite():
    Site.objects.get_or_create(name='ESSArch')


if __name__ == '__main__':
    installDefaultConfiguration()
