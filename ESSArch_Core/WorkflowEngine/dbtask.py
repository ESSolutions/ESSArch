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
from contextlib import nullcontext

from billiard.einfo import ExceptionInfo
from celery import Task, exceptions, states as celery_states
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import translation
from redis.exceptions import LockNotOwnedError
from tenacity import (
    RetryError,
    Retrying,
    stop_after_delay,
    wait_random_exponential,
)

from ESSArch_Core.db.utils import check_db_connection
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.util import get_result

User = get_user_model()

# import time
# from contextlib import contextmanager
#
# LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes
#
# @contextmanager
# def cache_lock(lock_id):
#     timeout_at = time.monotonic() + LOCK_EXPIRE - 3
#     # cache.add fails if the key already exists
#     # Second value is arbitrary
#     status = cache.add(lock_id, "lock", timeout=LOCK_EXPIRE)
#     try:
#         yield status
#     finally:
#         if time.monotonic() < timeout_at and status:
#             # don't release the lock if we exceeded the timeout
#             # to lessen the chance of releasing an expired lock
#             # owned by someone else
#             # also don't release the lock if we didn't acquire it
#             cache.delete(lock_id)


class DBTask(Task):
    abstract = True
    event_type = None
    queue = 'celery'
    track = True
    logger = logging.getLogger('essarch')

    def __call__(self, *args, **kwargs):
        for k, v in self.result_params.items():
            kwargs[k] = get_result(self.step, v)

        try:
            user = User.objects.get(pk=self.responsible)
            if user.user_profile is not None:
                with translation.override(user.user_profile.language):
                    return self._run(*args, **kwargs)
        except User.DoesNotExist:
            pass

        return self._run(*args, **kwargs)

    @property
    def headers(self):
        if self.eager:
            return self.request.headers['headers']

        if self.request.headers:
            return self.request.headers
        return {}

    @property
    def result_params(self):
        return self.headers.get('result_params', {})

    @property
    def allow_failure(self):
        return self.headers.get('allow_failure', False)

    @property
    def hidden(self):
        return self.headers.get('hidden', False)

    @property
    def responsible(self):
        return self.headers.get('responsible')

    @property
    def ip(self):
        return self.headers.get('ip')

    @property
    def step(self):
        return self.headers.get('step')

    @property
    def step_pos(self):
        return self.headers.get('step_pos')

    @property
    def parallel(self):
        return self.headers.get('parallel', False)

    @property
    def task_id(self):
        return self.request.id

    @property
    def eager(self):
        return self.request.is_eager

    def _run(self, *args, **kwargs):
        self.extra_data = {}
        if self.ip:
            try:
                for attempt in Retrying(stop=stop_after_delay(30), wait=wait_random_exponential(multiplier=1, max=60)):
                    with attempt:
                        try:
                            ip = InformationPackage.objects.select_related('submission_agreement').get(pk=self.ip)
                        except InformationPackage.DoesNotExist as e:
                            self.logger.warning(
                                'Exception in _run for task: {} ({}), step_id: {}, DoesNotExist when get ip: {} \
- retry'.format(self.name, self.task_id, self.step, self.ip))
                            raise e
            except RetryError:
                self.logger.warning('RetryError in _run for task: {} ({}), step_id: {}, \
DoesNotExist when get ip: {} - try to _run_task without IP'.format(self.name, self.task_id, self.step, self.ip))
                return self._run_task(*args, **kwargs)

            ip.refresh_from_db()
            updated_data = fill_specification_data(ip=ip, sa=ip.submission_agreement)
            updated_data_dict = updated_data.to_dict()
            self.extra_data.update(updated_data_dict)
            # if self.name == 'ESSArch_Core.tasks.ValidateXMLFile':
            #     self.logger.info('dbtask: {} - ip: {}, updated_data: {}'.format(self.name, ip, repr(updated_data)))
            #     self.logger.info('dbtask: {} - ip: {}, updated_data_dict: {}'.format(self.name, ip,
            #                                                                           repr(updated_data_dict)))
            #     self.logger.info('dbtask: {} - ip: {}, extra_data: {}'.format(self.name, ip, repr(self.extra_data)))

            if self.parallel:
                cm = nullcontext()
            else:
                cm = cache.lock(ip.get_lock_key(), timeout=300)
            try:
                if ip.is_locked():
                    if not self.parallel:
                        self.logger.warning(
                            'IP: {} is already locked when task: {} ({}) try to acquire lock'.format(
                                ip, self.name, self.task_id))
                    else:
                        self.logger.warning(
                            'IP: {} is already locked when task: {} ({}) try to run task in parallel'.format(
                                ip, self.name, self.task_id))
                with cm:
                    if not self.parallel:
                        self.logger.info('Task: {} ({}) acquired lock for IP {}'.format(self.name, self.task_id, ip))
                    else:
                        self.logger.info('Task: {} ({}) is running in parallel for IP: {}'.format(
                            self.name, self.task_id, ip))
                    try:
                        for attempt in Retrying(stop=stop_after_delay(30),
                                                wait=wait_random_exponential(multiplier=1, max=60)):
                            with attempt:
                                try:
                                    t = self.get_processtask()
                                except ProcessTask.DoesNotExist:
                                    self.logger.warning(
                                        'Exception in _run for task: {} ({}), step_id: {}, ip: {}, DoesNotExist when \
get ProcessTask - retry'.format(self.name, self.task_id, self.step, self.ip))
                                    raise
                    except RetryError:
                        self.logger.warning('RetryError in _run for task: {} ({}), step_id: {}, ip: {}, DoesNotExist \
when get ProcessTask'.format(self.name, self.task_id, self.step, self.ip))
                        raise

                    if t.run_if and not self.parse_params(t.run_if)[0]:
                        r = None
                        t.hidden = True
                        t.save()
                    else:
                        r = self._run_task(*args, **kwargs)
                if not self.parallel:
                    self.logger.info('{} released lock for IP: {}'.format(self.task_id, str(ip)))
            except LockNotOwnedError:
                self.logger.warning('Task: {} ({}) LockNotOwnedError for IP: {}'.format(
                    self.name, self.task_id, str(ip)))
                r = None
            return r

        return self._run_task(*args, **kwargs)

    def _run_task(self, *args, **kwargs):
        if self.step is not None:
            try:
                step = ProcessStep.objects.get(pk=self.step)
                for ancestor in step.get_ancestors(include_self=True):
                    self.extra_data.update(ancestor.context)
            except ProcessStep.DoesNotExist:
                self.logger.warning('Exception in _run_task for task: {} ({}), step_id: {}, DoesNotExist when get \
step, (self.ip: {})'.format(self.name, self.task_id, self.step, self.ip))

        try:
            if self.eager:
                self.backend._store_result(
                    self.task_id, None, celery_states.STARTED,
                    request=self.request,
                )
            res = self.run(*args, **kwargs)
        except exceptions.Ignore:
            raise
        except Exception as e:
            einfo = ExceptionInfo()
            self.failure(e, einfo)
            if self.eager:
                self.after_return(celery_states.FAILURE, e, self.task_id, args, kwargs, einfo)

            if self.allow_failure:
                ProcessTask.objects.filter(celery_id=self.task_id).update(
                    status=celery_states.FAILURE,
                    exception=einfo.exception,
                    traceback=einfo.traceback,
                )
                self.logger.error('Task with flag "allow failure" failed with exception {}'.format(einfo.exception))
                return None

            raise
        else:
            self.success(res, args, kwargs)

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

        # with cache_lock(step.cache_lock_key):
        with cache.lock(step.cache_lock_key, timeout=60):
            step.clear_cache()

        return super().after_return(status, retval, task_id, args, kwargs, einfo)

    def create_event(self, status, msg, retval, einfo):
        check_db_connection()
        if status == celery_states.SUCCESS:
            outcome = EventIP.SUCCESS
            level = logging.INFO
        else:
            outcome = EventIP.FAILURE
            level = logging.ERROR

        outcome_detail_note = msg

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
            'task': ProcessTask.objects.get(celery_id=self.task_id).pk,
            'outcome': outcome
        }
        self.logger.log(level, outcome_detail_note, extra=extra)

    def failure(self, exc, einfo):
        '''
        We use our own version of on_failure so that we can call it at the end
        of the current task but before the next task has started. This is
        needed to give objects created here (e.g. events) the correct
        timestamps
        '''

        if self.eager:
            self.update_state(task_id=self.task_id, state=celery_states.FAILURE)
            self.backend._store_result(
                self.task_id, self.backend.prepare_exception(exc),
                celery_states.FAILURE, traceback=einfo.traceback,
            )

        if self.event_type:
            msg = einfo.traceback
            self.create_event(celery_states.FAILURE, msg, None, einfo)

    def create_success_event(self, msg, retval=None):
        return self.create_event(celery_states.SUCCESS, msg, retval, None)

    def create_event_from_task_log_dict(self, msg):
        t = self.get_processtask()
        if type(t.log) is dict or t.log is True:
            self.event_type = t.log.get('event_type', self.event_type)
            msg = t.log.get('msg', msg)
            outcome = t.log.get('outcome', 'SUCCESS')
            self.create_event(outcome, msg, None, None)
            return True
        else:
            return False

    def success(self, retval, args, kwargs):
        '''
        We use our own version of on_success so that we can call it at the end
        of the current task but before the next task has started.
        '''

        if self.eager:
            self.update_state(task_id=self.task_id, state=celery_states.SUCCESS)
            self.backend.store_result(self.task_id, retval, celery_states.SUCCESS)

    def set_progress(self, progress, total=None):
        if not self.track:
            return

        self.update_state(meta={'current': progress, 'total': total})

    def parse_params(self, *params):
        return tuple([parseContent(param, self.extra_data) for param in params])

    def get_processtask(self):
        return ProcessTask.objects.get(celery_id=self.task_id)

    def get_information_package(self):
        return InformationPackage.objects.get(pk=self.ip)

    def run(self, *args, **kwargs):
        raise NotImplementedError()
