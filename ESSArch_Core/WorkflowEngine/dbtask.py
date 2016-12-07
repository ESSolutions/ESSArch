from __future__ import absolute_import, division

from _version import get_versions

import time

from billiard.einfo import ExceptionInfo

from celery import states as celery_states, Task

from ESSArch_Core.configuration.models import EventType

from django.db import (
    DatabaseError,
    OperationalError,
)

from django.utils import timezone

from ESSArch_Core.ip.models import EventIP, InformationPackage

from ESSArch_Core.WorkflowEngine.models import ProcessTask

class DBTask(Task):
    def __call__(self, *args, **kwargs):
        try:
            self.taskobj = kwargs['taskobj']
        except KeyError:
            print "Task requires taskobj set to a ProcessTask"

        self.eager = kwargs.get("eager", False)

        try:
            prev_result_dict = args[0]
        except IndexError:
            prev_result_dict = {}

        for k, v in self.taskobj.result_params.iteritems():
            self.taskobj.params[k] = prev_result_dict[v]

        self.taskobj.celery_id = self.request.id
        self.taskobj.status=celery_states.STARTED
        self.taskobj.time_started = timezone.now()
        self.taskobj.save(
            update_fields=[
                'params', 'celery_id', 'status', 'time_started'
            ]
        )

        if self.eager:
            try:
                res = self.run(**self.taskobj.params)
                self.taskobj.result = res
                self.taskobj.status = celery_states.SUCCESS
                self.taskobj.time_done = timezone.now()

                try:
                    self.taskobj.save(update_fields=['result', 'status', 'time_done'])
                except DatabaseError:
                    self.taskobj.save()

                if self.taskobj.log:
                    self.create_event(
                        0, self.event_outcome_success(**self.taskobj.params)
                    )

                return res
            except:
                self.taskobj.einfo = ExceptionInfo()
                self.taskobj.status = celery_states.FAILURE
                self.taskobj.time_done = timezone.now()

                try:
                    self.taskobj.save(update_fields=['einfo', 'status', 'time_done'])
                except DatabaseError:
                    self.taskobj.save()

                outcome = 1
                outcome_detail_note = self.taskobj.einfo.traceback
                self.create_event(
                    outcome, outcome_detail_note
                )
                raise

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
                self.taskobj.save(update_fields=['status', 'time_done'])
            except OperationalError:
                print "Database locked, trying again after 2 seconds"
                time.sleep(2)
                self.taskobj.save(update_fields=['status', 'time_done'])

    def create_event(self, outcome, outcome_detail_note):
        log = self.taskobj.log

        if not log in [EventIP,] or not self.event_type: # check if log is an event class
            return

        event_type = EventType.objects.get(eventType=self.event_type)

        application = None
        if not self.eager:
            application=self.taskobj

        event = log.objects.create(
            eventType=event_type, eventOutcome=outcome,
            eventVersion=get_versions()['version'],
            eventOutcomeDetailNote=outcome_detail_note,
            eventApplication=application, linkingAgentIdentifierValue='System',
        )

        if log == EventIP:
            if not isinstance(self.taskobj.information_package, InformationPackage):
                raise AttributeError(
                    "An IP is required to be set on the task to create an IP event"
                )

            event.linkingObjectIdentifierValue = self.taskobj.information_package
            event.save(update_fields=['linkingObjectIdentifierValue'])

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if not self.eager:
            self.taskobj.einfo = einfo
            self.taskobj.save(update_fields=['einfo'])

            ProcessTask.objects.filter(
                attempt=self.taskobj.attempt,
                processstep_pos__gt=self.taskobj.processstep_pos
            ).update(status=celery_states.FAILURE)

            outcome = 1
            outcome_detail_note = einfo.traceback
            self.create_event(
                outcome, outcome_detail_note
            )

    def on_success(self, retval, task_id, args, kwargs):
        if not self.eager:
            try:
                self.taskobj.result = retval.get(self.taskobj.id, None)
            except AttributeError:
                self.taskobj.result = None

            self.taskobj.save(update_fields=['result'])

            outcome = 0
            outcome_detail_note = self.event_outcome_success(
                **self.taskobj.params
            )
            self.create_event(
                outcome, outcome_detail_note
            )

    def set_progress(self, progress, total=None):
        self.update_state(state=celery_states.PENDING,
                          meta={'current': progress, 'total': total})

        self.taskobj.progress = (progress/total) * 100
        self.taskobj.save(update_fields=['progress'])


    def event_outcome_success(self, *args, **kwargs):
        raise NotImplementedError()

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def undo(self, *args, **kwargs):
        raise NotImplementedError()
