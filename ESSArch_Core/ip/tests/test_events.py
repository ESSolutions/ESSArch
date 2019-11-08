from django.test import TestCase
from lxml import etree

from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.ip.models import EventIP, InformationPackage


class EventIPManagerTestCase(TestCase):
    def setUp(self):
        self.id_val = '01994642-17c6-474e-923f-1b58fb137f30'
        self.event_type = EventType.objects.create(
            eventType=10, eventDetail='Testing type',
            category=EventType.CATEGORY_INFORMATION_PACKAGE,
        )
        self.time = '2017-06-05 15:54:33.521858+00:00'
        self.user = 'essuser'
        self.objid = 'foo'

        self.root = etree.fromstring('''
            <premis:premis
                xmlns:premis="http://www.loc.gov/premis/v3"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                version="3.0"
                xsi:schemaLocation="http://www.loc.gov/premis/v3 http://www.loc.gov/standards/premis/premis.xsd"
            >
                <premis:event>
                  <premis:eventIdentifier>
                    <premis:eventIdentifierType>ESS</premis:eventIdentifierType>
                    <premis:eventIdentifierValue>{id_val}</premis:eventIdentifierValue>
                  </premis:eventIdentifier>
                  <premis:eventType>{event_type}</premis:eventType>
                  <premis:eventDateTime>{time}</premis:eventDateTime>
                  <premis:eventDetailInformation>
                    <premis:eventDetail>Parsing detail</premis:eventDetail>
                  </premis:eventDetailInformation>
                  <premis:eventOutcomeInformation>
                    <premis:eventOutcome>0</premis:eventOutcome>
                    <premis:eventOutcomeDetail>
                      <premis:eventOutcomeDetailNote>Updated status</premis:eventOutcomeDetailNote>
                    </premis:eventOutcomeDetail>
                  </premis:eventOutcomeInformation>
                  <premis:linkingAgentIdentifier>
                    <premis:linkingAgentIdentifierType>ESS</premis:linkingAgentIdentifierType>
                    <premis:linkingAgentIdentifierValue>{user}</premis:linkingAgentIdentifierValue>
                  </premis:linkingAgentIdentifier>
                  <premis:linkingObjectIdentifier>
                    <premis:linkingObjectIdentifierType>ESS</premis:linkingObjectIdentifierType>
                    <premis:linkingObjectIdentifierValue>{objid}</premis:linkingObjectIdentifierValue>
                  </premis:linkingObjectIdentifier>
                </premis:event>
            </premis:premis>
        '''.format(id_val=self.id_val, event_type=self.event_type.eventType,
                   time=self.time, user=self.user, objid=self.objid,))

        self.el = self.root.xpath("./*[local-name()='event']")[0]

    def test_parse(self):
        event = EventIP.objects.from_premis_element(self.el)

        self.assertEqual(event.eventIdentifierValue, self.id_val)
        self.assertEqual(event.eventType.eventType, self.event_type.eventType)
        self.assertEqual(event.eventDateTime, self.time)
        self.assertEqual(event.eventOutcome, "0")
        self.assertEqual(event.eventOutcomeDetailNote, "Updated status")
        self.assertEqual(event.linkingAgentIdentifierValue, self.user)
        self.assertEqual(event.linkingObjectIdentifierValue, self.objid)

    def test_parse_existing_ip(self):
        ip = InformationPackage.objects.create(object_identifier_value=self.objid)
        event = EventIP.objects.from_premis_element(self.el)

        self.assertEqual(event.linkingObjectIdentifierValue, str(ip.pk))
