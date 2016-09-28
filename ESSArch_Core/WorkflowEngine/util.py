from __future__ import absolute_import

import pyclbr

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

def create_event(eventType, detail, agent, ip=None):
    """
    Creates a new event and saves it to the database

    Args:
        eventType: The event type
        detail: The detail of the event
        agent: The agent creating the event
        ip: The information package connected to the event

    Returns:
        The created event
    """

    from configuration.models import EventType
    from ip.models import EventIP

    return EventIP.objects.create(
        eventType=EventType.objects.get(
            eventType=eventType
        ),
        eventDetail=detail,
        linkingAgentIdentifierValue=agent,
        linkingObjectIdentifierValue=ip,
    )
