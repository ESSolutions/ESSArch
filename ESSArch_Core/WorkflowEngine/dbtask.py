from __future__ import absolute_import, division

import time

from celery import states as celery_states, Task

from configuration.models import EventType

from django.db import (
    OperationalError,
)

from django.utils import timezone

from ip.models import InformationPackage

from preingest.models import ProcessTask

from preingest.util import create_event

class DBTask(Task):
    def __call__(self, *args, **kwargs):
        try:
            self.taskobj = kwargs['taskobj']
        except KeyError:
            print "Task requires taskobj set to a ProcessTask"

        self.eager = kwargs.get("eager", False)

        if self.eager:
            return self.run(**self.taskobj.params)

        try:
            prev_result_dict = args[0]
        except IndexError:
            prev_result_dict = {}

        for k, v in self.taskobj.result_params.iteritems():
            self.taskobj.params[k] = prev_result_dict[v]

        self.taskobj.celery_id = self.request.id
        self.taskobj.status=celery_states.STARTED
        self.taskobj.time_started = timezone.now()
        self.taskobj.save()

        if self.taskobj.undo_type:
            return self.undo(**self.taskobj.params)
        else:
            prev_result_dict[self.taskobj.id] = self.run(**self.taskobj.params)
            return prev_result_dict

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if not self.eager:
            try:
                self.taskobj.status = status
                self.taskobj.time_done = timezone.now()
                self.taskobj.save()
            except OperationalError:
                print "Database locked, trying again after 2 seconds"
                time.sleep(2)
                self.taskobj.status = status
                self.taskobj.time_done = timezone.now()
                self.taskobj.save()

            if hasattr(self, "event_type"):
                if not isinstance(self.taskobj.information_package, InformationPackage):
                    raise AttributeError(
                        "An IP is required to be set on the task to create an event"
                    )

                event_type = EventType.objects.get(eventType=self.event_type)
                event_args = self.get_event_args(**self.taskobj.params)

                create_event(
                    event_type, event_args, "System",
                    self.taskobj.information_package
                )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if not self.eager:
            self.taskobj.traceback = einfo.traceback
            self.taskobj.save()

            ProcessTask.objects.filter(
                attempt=self.taskobj.attempt,
                processstep_pos__gt=self.taskobj.processstep_pos
            ).update(status=celery_states.FAILURE)

    def on_success(self, retval, task_id, args, kwargs):
        if not self.eager:
            try:
                self.taskobj.result = retval.get(self.taskobj.id, None)
            except AttributeError:
                self.taskobj.result = None

            self.taskobj.save()

    def set_progress(self, progress, total=None):
        if not self.eager:
            self.update_state(state=celery_states.PENDING,
                              meta={'current': progress, 'total': total})

            self.taskobj.progress = (progress/total) * 100
            self.taskobj.save()


    def get_event_args(self, *args, **kwargs):
        return []

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def undo(self, *args, **kwargs):
        raise NotImplementedError()
