"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import logging

from billiard.einfo import ExceptionInfo
from celery import exceptions, states as celery_states
from celery.task.base import Task
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import translation

from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.util import get_result

User = get_user_model()

logger = logging.getLogger('essarch')


class DBTask(Task):
    abstract = True
    args = []
    event_type = None
    queue = 'celery'
    hidden = False
    undo_type = False
    responsible = None
    ip = None
    step = None
    step_pos = None
    track = True
    allow_failure = False

    def __call__(self, *args, **kwargs):
        options = kwargs.pop('_options', {})

        self.args = options.get('args', [])
        self.responsible = options.get('responsible')
        self.ip = options.get('ip')
        self.step = options.get('step')
        self.step_pos = options.get('step_pos')
        self.hidden = options.get('hidden', False) or self.hidden
        if options.get('hidden') is not None:
            self.hidden = options['hidden']

        self.undo_type = options.get('undo', False)
        self.result_params = options.get('result_params', {}) or {}
        self.task_id = options.get('task_id') or self.request.id
        self.eager = options.get('eager') or self.request.is_eager
        self.allow_failure = options.get('allow_failure') or self.allow_failure

        for k, v in self.result_params.items():
            kwargs[k] = get_result(self.step, v)

        if self.track:
            ProcessTask.objects.filter(celery_id=self.task_id).update(
                hidden=self.hidden,
            )

        try:
            user = User.objects.get(pk=self.responsible)
            if user.user_profile is not None:
                with translation.override(user.user_profile.language):
                    return self._run(*args, **kwargs)
        except User.DoesNotExist:
            pass

        return self._run(*args, **kwargs)

    def _run(self, *args, **kwargs):
        self.extra_data = {}
        if self.ip:
            ip = InformationPackage.objects.select_related('submission_agreement').get(pk=self.ip)
            self.extra_data.update(fill_specification_data(ip=ip, sa=ip.submission_agreement).to_dict())

            logger.debug('{} acquiring lock for IP {}'.format(self.task_id, str(ip.pk)))
            with cache.lock(ip.get_lock_key(), blocking_timeout=300):
                logger.info('{} acquired lock for IP {}'.format(self.task_id, str(ip.pk)))

                t = self.get_processtask()
                if t.run_if and not self.parse_params(t.run_if)[0]:
                    r = None
                    t.hidden = True
                    t.save()
                else:
                    r = self._run_task(*args, **kwargs)
            logger.info('{} released lock for IP {}'.format(self.task_id, str(ip.pk)))
            return r

        return self._run_task(*args, **kwargs)

    def _run_task(self, *args, **kwargs):
        if self.step is not None:
            step = ProcessStep.objects.get(pk=self.step)
            for ancestor in step.get_ancestors(include_self=True):
                self.extra_data.update(ancestor.context)

        try:
            if self.undo_type:
                res = self.undo(*args, **kwargs)
            else:
                res = self.run(*args, **kwargs)
        except exceptions.Ignore:
            raise
        except Exception as e:
            einfo = ExceptionInfo()
            self.failure(e, self.task_id, args, kwargs, einfo)
            if self.eager:
                self.after_return(celery_states.FAILURE, e, self.task_id, args, kwargs, einfo)

            if self.allow_failure:
                ProcessTask.objects.filter(celery_id=self.task_id).update(
                    status=celery_states.FAILURE,
                    exception=einfo.exception,
                    traceback=einfo.traceback,
                )
                return None

            raise
        else:
            self.success(res, self.task_id, args, kwargs)

        return res

    def update_state(self, task_id=None, state=None, meta=None, **kwargs):
        if task_id is None:
            task_id = self.request.id

        self.backend.update_state(task_id, meta, state, request=self.request, **kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self.step is None:
            return

        try:
            step = ProcessStep.objects.get(pk=self.step)
        except ProcessStep.DoesNotExist:
            return

        with cache.lock(step.cache_lock_key, timeout=60):
            step.clear_cache()

    def create_event(self, task_id, status, args, kwargs, retval, einfo):
        if status == celery_states.SUCCESS:
            outcome = EventIP.SUCCESS
            level = logging.INFO
            kwargs.pop('_options', {})
            outcome_detail_note = self.event_outcome_success(retval, *args, **kwargs)
        else:
            outcome = EventIP.FAILURE
            level = logging.ERROR
            outcome_detail_note = einfo.traceback

        if outcome_detail_note is None:
            outcome_detail_note = ''

        try:
            agent = User.objects.values_list('username', flat=True).get(pk=self.responsible)
        except User.DoesNotExist:
            agent = None

        extra = {
            'event_type': self.event_type,
            'object': self.ip,
            'agent': agent,
            'task': ProcessTask.objects.get(celery_id=task_id).pk,
            'outcome': outcome
        }
        logger.log(level, outcome_detail_note, extra=extra)

    def failure(self, exc, task_id, args, kwargs, einfo):
        '''
        We use our own version of on_failure so that we can call it at the end
        of the current task but before the next task has started. This is
        needed to give objects created here (e.g. events) the correct
        timestamps
        '''

        if getattr(self, 'eager', True):
            self.update_state(task_id=task_id, state=celery_states.FAILURE)
            self.backend._store_result(
                task_id, self.backend.prepare_exception(exc),
                celery_states.FAILURE, traceback=einfo.traceback,
            )

        if self.event_type:
            self.create_event(task_id, celery_states.FAILURE, args, kwargs, None, einfo)

    def success(self, retval, task_id, args, kwargs):
        '''
        We use our own version of on_success so that we can call it at the end
        of the current task but before the next task has started. This is
        needed to give objects created here (e.g. events) the correct
        timestamps
        '''

        if getattr(self, 'eager', True):
            self.update_state(task_id=task_id, state=celery_states.SUCCESS)
            self.backend.store_result(task_id, retval, celery_states.SUCCESS)

        if self.event_type:
            self.create_event(task_id, celery_states.SUCCESS, args, kwargs, retval, None)

    def set_progress(self, progress, total=None):
        if not self.track:
            return

        self.update_state(meta={'current': progress, 'total': total})

    def parse_params(self, *params):
        return tuple([parseContent(param, self.extra_data) for param in params])

    def get_processtask(self):
        try:
            celery_id = self.request.id
        except AttributeError:
            celery_id = self.task_id

        return ProcessTask.objects.get(celery_id=celery_id)

    def get_information_package(self):
        return InformationPackage.objects.get(pk=self.ip)

    def event_outcome_success(self, result, *args, **kwargs):
        pass

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def undo(self, *args, **kwargs):
        pass
