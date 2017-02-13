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
    OperationalError,
)
from django.db.models import F
from django.db.models.functions import Coalesce
from django.utils import timezone

from ESSArch_Core.ip.models import EventIP

from ESSArch_Core.WorkflowEngine.models import ProcessTask

from ESSArch_Core.util import (
    truncate
)


class DBTask(Task):
    event_type = None
    queue = 'celery'
    hidden = False

    def __call__(self, *args, **kwargs):
        celery_always_eager = hasattr(settings, 'CELERY_ALWAYS_EAGER') and settings.CELERY_ALWAYS_EAGER
        celery_eager_propagates_exceptions = hasattr(settings, 'CELERY_EAGER_PROPAGATES_EXCEPTIONS') and settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS

        task_id = self.request.id

        ProcessTask.objects.filter(pk=task_id).update(
            hidden=Coalesce(F('hidden'), self.hidden),
            status=celery_states.STARTED,
            time_started=timezone.now()
        )

        try:
            undo_type = args[0]
        except IndexError:
            undo_type = False

        if undo_type:
            if celery_always_eager and celery_eager_propagates_exceptions:
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
            if celery_always_eager and celery_eager_propagates_exceptions:
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

    def apply(self, *args, **kwargs):
        celery_always_eager = hasattr(settings, 'CELERY_ALWAYS_EAGER') and settings.CELERY_ALWAYS_EAGER

        result_params = kwargs.get('result_params', {}) or {}

        for k, v in result_params.iteritems():
            if celery_always_eager:
                args[1][k] = ProcessTask.objects.values_list('result', flat=True).get(pk=v)
            else:
                args[1][k] = self.AsyncResult(str(v)).get()

        return super(DBTask, self).apply(*args, **kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        t = ProcessTask.objects.only('processstep').select_related('processstep').get(pk=task_id)
        try:
            t.processstep.clear_cache()
        except AttributeError:
            pass

        self.create_event(task_id, status, args, kwargs, retval, einfo)

    def create_event(self, task_id, status, args, kwargs, retval, einfo):
        if not self.event_type:
            return

        event_type = EventType.objects.filter(eventType=self.event_type).first()

        if event_type is None:
            return

        if status == celery_states.SUCCESS:
            outcome = 0
            outcome_detail_note = self.event_outcome_success(**kwargs)
        else:
            outcome = 1
            outcome_detail_note = einfo.traceback

        task = ProcessTask.objects.only('responsible_id', 'information_package_id').get(pk=task_id)

        EventIP.objects.create(
            eventType=event_type, eventOutcome=outcome,
            eventVersion=get_versions()['version'],
            eventOutcomeDetailNote=truncate(outcome_detail_note, 1024),
            eventApplication_id=task_id,
            linkingAgentIdentifierValue_id=task.responsible_id,
            linkingObjectIdentifierValue_id=task.information_package_id,
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
