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

from celery import current_app, states as celery_states, Task
from celery.result import allow_join_result

from ESSArch_Core.configuration.models import EventType

from django.db import (
    IntegrityError,
    OperationalError,
)
from django.utils import timezone

from ESSArch_Core.ip.models import EventIP

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask

from ESSArch_Core.util import (
    truncate
)


class DBTask(Task):
    event_type = None
    queue = 'celery'
    hidden = False
    undo_type = False
    responsible = None
    ip = None
    step = None
    step_pos = None

    def __call__(self, *args, **kwargs):
        options = kwargs.pop('_options', {})

        self.responsible = options.get('responsible')
        self.ip = options.get('ip')
        self.step = options.get('step')
        self.step_pos = options.get('step_pos')
        self.hidden = options.get('hidden', False) or self.hidden
        self.undo_type = options.get('undo', False)

        result_params = options.get('result_params', {}) or {}

        with allow_join_result():
            for k, v in result_params.iteritems():
                if self.request.is_eager:
                    kwargs[k] = ProcessTask.objects.values_list('result', flat=True).get(pk=v)
                else:
                    kwargs[k] = current_app.AsyncResult(str(v)).get()

        task_id = self.request.id

        ProcessTask.objects.filter(pk=task_id).update(
            hidden=self.hidden,
            status=celery_states.STARTED,
            time_started=timezone.now()
        )

        if self.undo_type:
            if self.request.is_eager:
                try:
                    res = self.undo(**kwargs)
                    return res
                except Exception as e:
                    einfo = ExceptionInfo()
                    self.on_failure(e, task_id, args, kwargs, einfo)
                    self.after_return(celery_states.FAILURE, e, task_id, args, kwargs, einfo)
                    raise
            else:
                return self.undo(**kwargs)
        else:
            if self.request.is_eager:
                try:
                    res = self.run(**kwargs)
                except Exception as e:
                    einfo = ExceptionInfo()
                    self.on_failure(e, task_id, args, kwargs, einfo)
                    self.after_return(celery_states.FAILURE, e, task_id, args, kwargs, einfo)
                    raise
            else:
                res = self.run(**kwargs)

            return res

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        try:
            step = ProcessStep.objects.get(pk=self.step)
            step.clear_cache()
        except ProcessStep.DoesNotExist:
            pass

    def create_event(self, task_id, status, args, kwargs, retval, einfo):
        if status == celery_states.SUCCESS:
            outcome = 0
            kwargs.pop('_options', {})
            outcome_detail_note = self.event_outcome_success(**kwargs)
        else:
            outcome = 1
            outcome_detail_note = einfo.traceback

        return EventIP(
            eventType_id=self.event_type, eventOutcome=outcome,
            eventVersion=get_versions()['version'],
            eventOutcomeDetailNote=truncate(outcome_detail_note, 1024),
            eventApplication_id=task_id,
            linkingAgentIdentifierValue_id=self.responsible,
            linkingObjectIdentifierValue_id=self.ip
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        time_done = timezone.now()
        try:
            ProcessTask.objects.filter(pk=task_id).update(
                einfo=einfo,
                status=celery_states.FAILURE,
                time_done=time_done,
            )
        except OperationalError:
            print "Database locked, trying again after 2 seconds"
            time.sleep(2)
            ProcessTask.objects.filter(pk=task_id).update(
                einfo=einfo,
                status=celery_states.FAILURE,
                time_done=time_done,
            )

        if self.event_type:
            event = self.create_event(task_id, celery_states.FAILURE, args, kwargs, None, einfo)
            try:
                event.save(force_insert=True)
            except IntegrityError:
                pass

    def on_success(self, retval, task_id, args, kwargs):
        time_done = timezone.now()
        try:
            ProcessTask.objects.filter(pk=task_id).update(
                result=retval,
                status=celery_states.SUCCESS,
                time_done=time_done,
            )
        except OperationalError:
            print "Database locked, trying again after 2 seconds"
            time.sleep(2)
            ProcessTask.objects.filter(pk=task_id).update(
                result=retval,
                status=celery_states.SUCCESS,
                time_done=time_done,
            )

        if self.event_type:
            event = self.create_event(task_id, celery_states.SUCCESS, args, kwargs, None, retval)
            try:
                event.save(force_insert=True)
            except IntegrityError:
                pass

    def set_progress(self, progress, total=None):
        task_id = self.request.id

        self.update_state(state=celery_states.PENDING,
                          meta={'current': progress, 'total': total})

        ProcessTask.objects.filter(pk=task_id).update(
            progress=(progress/total) * 100,
        )

    def event_outcome_success(self, *args, **kwargs):
        raise NotImplementedError()

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def undo(self, *args, **kwargs):
        raise NotImplementedError()
