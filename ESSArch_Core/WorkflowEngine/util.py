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
