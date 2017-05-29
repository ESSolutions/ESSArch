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
    connection,
    IntegrityError,
    OperationalError,
    transaction,
)
from django.utils import timezone

from ESSArch_Core.ip.models import EventIP

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask

from ESSArch_Core.util import (
    truncate
)


class DBTask(Task):
    args = []
    event_type = None
    queue = 'celery'
    hidden = False
    undo_type = False
    responsible = None
    ip = None
    step = None
    step_pos = None
    chunk = False

    def __call__(self, *args, **kwargs):
        options = kwargs.pop('_options', {})
        self.chunk = options.get('chunk', False)

        self.args = options.get('args', [])
        self.responsible = options.get('responsible')
        self.ip = options.get('ip')
        self.step = options.get('step')
        self.step_pos = options.get('step_pos')
        self.hidden = options.get('hidden', False) or self.hidden
        self.undo_type = options.get('undo', False)
        self.result_params = options.get('result_params', {}) or {}
        self.task_id = options.get('task_id') or self.request.id
        self.eager = options.get('eager') or self.request.is_eager

        if self.chunk:
            res = []
            events = []
            if not connection.features.autocommits_when_autocommit_is_off:
                transaction.set_autocommit(False)
            try:
                for a in args:
                    a_options = a.pop('_options')
                    self.eager = True
                    self.task_id = a_options['task_id']
                    self.args = a_options['args']

                    self.progress = 0
                    hidden = a_options.get('hidden', False) or self.hidden
                    time_started=timezone.now()
                    try:
                        retval = self._run(*self.args, **a)
                    except:
                        ProcessTask.objects.filter(pk=self.task_id).update(
                            hidden=hidden,
                            time_started=time_started,
                            progress=self.progress
                        )
                        einfo = ExceptionInfo()
                        if self.event_type:
                            event = self.create_event(self.task_id, celery_states.FAILURE, args, a, None, einfo)
                            events.append(event)
                        raise
                    else:
                        self.success(retval, self.task_id, None, kwargs)
                        ProcessTask.objects.filter(pk=self.task_id).update(
                            result=retval,
                            status=celery_states.SUCCESS,
                            hidden=hidden,
                            time_started=time_started,
                            time_done=timezone.now(),
                            progress=100
                        )
                        res.append(retval)
                        if self.event_type:
                            event = self.create_event(self.task_id, celery_states.SUCCESS, self.args, a, retval, None)
                            events.append(event)
            except:
                raise
            else:
                return res
            finally:
                try:
                    EventIP.objects.bulk_create(events)
                except IntegrityError:
                    pass

                if not connection.features.autocommits_when_autocommit_is_off:
                    transaction.commit()
                    transaction.set_autocommit(True)

        with allow_join_result():
            for k, v in self.result_params.iteritems():
                if self.eager:
                    kwargs[k] = ProcessTask.objects.values_list('result', flat=True).get(pk=v)
                else:
                    kwargs[k] = current_app.AsyncResult(str(v)).get()

        ProcessTask.objects.filter(pk=self.task_id).update(
            hidden=self.hidden,
            status=celery_states.STARTED,
            time_started=timezone.now()
        )

        return self._run(*args, **kwargs)

    def _run(self, *args, **kwargs):
        if self.undo_type:
            try:
                res = self.undo(*args, **kwargs)
            except Exception as e:
                einfo = ExceptionInfo()
                self.failure(e, self.task_id, args, kwargs, einfo)

                if self.eager:
                    self.after_return(celery_states.FAILURE, e, self.task_id, args, kwargs, einfo)
                raise
            else:
                self.success(res, self.task_id, args, kwargs)

            return res
        else:
            try:
                res = self.run(*args, **kwargs)
            except Exception as e:
                einfo = ExceptionInfo()
                self.failure(e, self.task_id, args, kwargs, einfo)
                if self.eager:
                    self.after_return(celery_states.FAILURE, e, self.task_id, args, kwargs, einfo)
                raise
            else:
                self.success(res, self.task_id, args, kwargs)

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
            outcome_detail_note = self.event_outcome_success(*args, **kwargs)
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

    def failure(self, exc, task_id, args, kwargs, einfo):
        '''
        We use our own version of on_failure so that we can call it at the end
        of the current task but before the next task has started. This is
        needed to give objects created here (e.g. events) the correct
        timestamps
        '''

        time_done = timezone.now()
        tb = einfo.traceback
        exception = "%s: %s" % (einfo.type.__name__, einfo.exception)

        try:
            ProcessTask.objects.filter(pk=task_id).update(
                traceback=tb,
                exception=exception,
                status=celery_states.FAILURE,
                time_done=time_done,
            )
        except OperationalError:
            print "Database locked, trying again after 2 seconds"
            time.sleep(2)
            ProcessTask.objects.filter(pk=task_id).update(
                traceback=tb,
                exception=exception,
                status=celery_states.FAILURE,
                time_done=time_done,
            )

        if not self.chunk and self.event_type:
            event = self.create_event(task_id, celery_states.FAILURE, args, kwargs, None, einfo)
            try:
                with transaction.atomic():
                    event.save(force_insert=True)
            except IntegrityError as e:
                pass

    def success(self, retval, task_id, args, kwargs):
        '''
        We use our own version of on_success so that we can call it at the end
        of the current task but before the next task has started. This is
        needed to give objects created here (e.g. events) the correct
        timestamps
        '''

        if self.chunk:
            return
        time_done = timezone.now()
        try:
            ProcessTask.objects.filter(pk=task_id).update(
                result=retval,
                status=celery_states.SUCCESS,
                time_done=time_done,
                progress=100
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
                with transaction.atomic():
                    event.save(force_insert=True)
            except IntegrityError as e:
                pass

    def set_progress(self, progress, total=None):
        if not self.eager:
            self.update_state(state=celery_states.PENDING,
                              meta={'current': progress, 'total': total})

        percent = (progress/total) * 100

        if self.chunk:
            self.progress = percent
        else:
            ProcessTask.objects.filter(pk=self.task_id).update(
                progress=percent
            )

    def event_outcome_success(self, *args, **kwargs):
        raise NotImplementedError()

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def undo(self, *args, **kwargs):
        raise NotImplementedError()
