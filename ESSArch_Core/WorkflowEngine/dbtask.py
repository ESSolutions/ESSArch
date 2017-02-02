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

from __future__ import absolute_import, division

from _version import get_versions

import time

from billiard.einfo import ExceptionInfo

from celery import states as celery_states, Task

from ESSArch_Core.configuration.models import EventType

from django.conf import settings

from django.db import (
    DatabaseError,
    OperationalError,
)

from django.utils import timezone

from ESSArch_Core.ip.models import EventIP, InformationPackage

from ESSArch_Core.WorkflowEngine.models import ProcessTask

from ESSArch_Core.util import (
    truncate
)


class DBTask(Task):
    event_type = None
    queue = 'celery'
    hidden = False

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

        if self.taskobj.result_params:
            for k, v in self.taskobj.result_params.iteritems():
                self.taskobj.params[k] = prev_result_dict[v]

        self.taskobj.hidden = self.taskobj.hidden or self.hidden
        self.taskobj.celery_id = self.request.id
        self.taskobj.status = celery_states.STARTED
        self.taskobj.time_started = timezone.now()
        self.taskobj.save(update_fields=['hidden', 'celery_id', 'status', 'time_started'])

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

        celery_always_eager = hasattr(settings, 'CELERY_ALWAYS_EAGER') and settings.CELERY_ALWAYS_EAGER
        celery_eager_propagates_exceptions = hasattr(settings, 'CELERY_EAGER_PROPAGATES_EXCEPTIONS') and settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS

        if self.taskobj.undo_type:
            if celery_always_eager and celery_eager_propagates_exceptions:
                try:
                    res = self.undo(**self.taskobj.params)
                    prev_result_dict[self.taskobj.id] = res
                    self.on_success(prev_result_dict, None, args, kwargs)
                    return res
                except Exception as e:
                    einfo = ExceptionInfo()
                    self.on_failure(e, None, args, kwargs, einfo)
                    self.after_return(celery_states.FAILURE, e, None, args, kwargs, einfo)
                    raise
            else:
                return self.undo(**self.taskobj.params)
        else:
            if celery_always_eager and celery_eager_propagates_exceptions:
                try:
                    res = self.run(**self.taskobj.params)
                    prev_result_dict[self.taskobj.id] = res
                    self.on_success(prev_result_dict, None, args, kwargs)
                except Exception as e:
                    einfo = ExceptionInfo()
                    self.on_failure(e, None, args, kwargs, einfo)
                    self.after_return(celery_states.FAILURE, e, None, args, kwargs, einfo)
                    raise
            else:
                prev_result_dict[self.taskobj.id] = self.run(**self.taskobj.params)

            self.create_event(None, "")
            return prev_result_dict

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        self.taskobj.refresh_from_db()
        if not self.eager:
            try:
                try:
                    self.taskobj.result = retval.get(self.taskobj.pk, None)
                except AttributeError:
                    self.taskobj.result = None

                self.taskobj.status = status
                self.taskobj.time_done = timezone.now()
                self.taskobj.save(update_fields=['status', 'time_done', 'result'])
            except OperationalError:
                print "Database locked, trying again after 2 seconds"
                time.sleep(2)
                self.taskobj.save(update_fields=['status', 'time_done', 'result'])

    def create_event(self, outcome, outcome_detail_note):
        log = self.taskobj.log

        if log not in [EventIP] or not self.event_type:  # check if log is an event class
            return

        event_type = EventType.objects.get(eventType=self.event_type)

        application = self.taskobj

        event = log.objects.create(
            eventType=event_type, eventOutcome=outcome,
            eventVersion=get_versions()['version'],
            eventOutcomeDetailNote=truncate(outcome_detail_note, 1024),
            eventApplication=application,
            linkingAgentIdentifierValue=self.taskobj.responsible,
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
            self.taskobj.refresh_from_db()
            self.taskobj.einfo = einfo
            self.taskobj.save(update_fields=['einfo'])

            ProcessTask.objects.filter(
                attempt=self.taskobj.attempt,
                processstep_pos__gt=self.taskobj.processstep_pos
            ).update(status=celery_states.FAILURE)

            try:
                event = self.taskobj.event
                event.eventOutcome = 1
                event.eventOutcomeDetailNote = einfo.traceback
                event.save()
            except EventIP.DoesNotExist:
                pass

    def on_success(self, retval, task_id, args, kwargs):
        if self.taskobj.log and not self.eager:
            EventIP.objects.filter(eventApplication=self.taskobj).update(
                eventOutcome=0,
                eventOutcomeDetailNote=self.event_outcome_success(
                    **self.taskobj.params
                )
            )

    def set_progress(self, progress, total=None):
        if not self.eager:
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
