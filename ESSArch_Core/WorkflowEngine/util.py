from __future__ import absolute_import

import pyclbr

from lxml import etree

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

def sliceUntilAttr(iterable, attr, val):
    for i in iterable:
        if getattr(i, attr) == val:
            return
        yield i

def available_tasks():
    modules = ["preingest.tasks", "preingest.tests.tasks"]
    tasks = []
    for m in modules:
        module_tasks = pyclbr.readmodule(m)
        tasks = tasks + zip(
            [m+"."+t for t in module_tasks],
            module_tasks
        )
    return tasks

def create_event(eventType, eventArgs, agent, ip=None):
    """
    Creates a new event and saves it to the database

    Args:
        eventType: The event type
        eventArgs: The args that will be used to create the detail text
        agent: The agent creating the event
        ip: The information package connected to the event

    Returns:
        The created event
    """

    from ip.models import EventIP

    detail = eventType.eventDetail % tuple(eventArgs)

    return EventIP.objects.create(
        eventType=eventType, eventDetail=detail,
        linkingAgentIdentifierValue=agent,
        linkingObjectIdentifierValue=ip,
    )


def getSchemas(doc=None, filename=None):
    """
        Creates a schema based on the schemas specified in the provided XML
        file's schemaLocation attribute
    """


    if filename:
        try:
            doc = etree.ElementTree(file=filename)
        except etree.XMLSyntaxError:
            raise
        except IOError:
            raise

    res = []
    root = doc.getroot()
    xsi_NS = "%s" % root.nsmap['xsi']

    xsd_NS = "{%s}" % XSD_NAMESPACE
    NSMAP = {'xsd': XSD_NAMESPACE}

    root = etree.Element(xsd_NS + "schema", nsmap=NSMAP)
    root.attrib["elementFormDefault"] = "qualified"

    schema_locations = set(doc.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': xsi_NS}))
    for schema_location in schema_locations:
        ns_locs = schema_location.split()
        for ns, loc in zip(ns_locs[:-1], ns_locs[1:]):
            res.append([ns, loc])
            etree.SubElement(root, xsd_NS + "import", attrib={
                "namespace": ns,
                "schemaLocation": loc
            })

    return etree.XMLSchema(root)
