from __future__ import absolute_import

import pyclbr

def sliceUntilAttr(iterable, attr, val):
    for i in iterable:
        if getattr(i, attr) == val:
            return
        yield i

def available_tasks():
    return pyclbr.readmodule("preingest.tasks")
