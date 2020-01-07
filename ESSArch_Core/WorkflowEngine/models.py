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

import copy
import importlib
import itertools
import logging
import uuid
from urllib.parse import urljoin

import tblib
from celery import chain, group, states as celery_states
from celery.result import EagerResult
from celery.task.control import revoke
from django.core.cache import cache
from django.db import models
from django.db.models import Case, Count, Sum, When
from django.urls import reverse
from django.utils.translation import ugettext as _
from mptt.models import MPTTModel, TreeForeignKey
from picklefield.fields import PickledObjectField
from requests import RequestException
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.fields import JSONField

logger = logging.getLogger('essarch.WorkflowEngine')


def create_task(name):
    """
    Create and instantiate the task with the given name

    Args:
        name: The name of the task, including package and module
    """
    [module, task] = name.rsplit('.', 1)
    logger.debug('Importing task {} from module {}'.format(task, module))
    return getattr(importlib.import_module(module), task)()


def create_sub_task(t, step=None, immutable=True, link_error=None):
    logger.debug('Creating sub task')
    ip_id = str(t.information_package_id) if t.information_package_id is not None else None
    step_id = str(step.id) if step is not None else None
    t.params['_options'] = {
        'args': t.args,
        'responsible': t.responsible_id, 'ip': ip_id,
        'step': step_id, 'step_pos': t.processstep_pos, 'hidden': t.hidden,
        'undo': t.undo_type, 'result_params': t.result_params,
        'allow_failure': t.allow_failure,
    }

    created = create_task(t.name)

    # For some reason, __repr__ needs to be called for the link_error
    # signature to be called when an error occurs in a task
    repr(link_error)

    res = created.signature(t.args, t.params, immutable=immutable).set(
        task_id=str(t.celery_id), link_error=link_error, queue=created.queue
    )
    logger.info('Created {} sub task signature'.format('immutable' if immutable else ''))

    return res


class Process(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celery_id = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=255)
    hidden = models.BooleanField(editable=False, null=True, default=None, db_index=True)
    eager = models.BooleanField(default=True)
    time_created = models.DateTimeField(auto_now_add=True)
    result = PickledObjectField(null=True, default=None, editable=False)

    def __str__(self):
        return self.name


class ProcessStep(MPTTModel, Process):
    Type_CHOICES = (
        (0, "Receive new object"),
        (5, "The object is ready to remodel"),
        (9, "New object stable"),
        (10, "Object don't exist in AIS"),
        (11, "Object don't have any projectcode in AIS"),
        (12, "Object don't have any local policy"),
        (13, "Object already have an AIP!"),
        (14, "Object is not active!"),
        (19, "Object got a policy"),
        (20, "Object not updated from AIS"),
        (21, "Object not accepted in AIS"),
        (24, "Object accepted in AIS"),
        (25, "SIP validate"),
        (30, "Create AIP package"),
        (40, "Create package checksum"),
        (50, "AIP validate"),
        (60, "Try to remove IngestObject"),
        (1000, "Write AIP to longterm storage"),
        (1500, "Remote AIP"),
        (2009, "Remove temp AIP object OK"),
        (3000, "Archived"),
        (5000, "ControlArea"),
        (5100, "WorkArea"),
        (9999, "Deleted"),
    )

    type = models.IntegerField(null=True, choices=Type_CHOICES)
    user = models.CharField(max_length=45)
    parent_step = TreeForeignKey(
        'self',
        related_name='child_steps',
        on_delete=models.CASCADE,
        null=True
    )
    parent_step_pos = models.IntegerField(_('Parent step position'), default=0)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.CASCADE,
        related_name='steps',
        blank=True,
        null=True
    )
    parallel = models.BooleanField(default=False)
    on_error = models.ManyToManyField('ProcessTask', related_name='steps_on_errors')
    context = JSONField(default={}, null=True)

    def get_pos(self):
        return self.parent_step_pos

    def get_descendants_tasks(self):
        steps = self.get_descendants(include_self=True)
        return ProcessTask.objects.filter(processstep__in=steps)

    def add_tasks(self, *tasks):
        self.clear_cache()
        self.tasks.add(*tasks)

    def remove_tasks(self, *tasks):
        self.clear_cache()
        self.tasks.remove(*tasks)

    def clear_tasks(self):
        self.clear_cache()
        self.tasks.clear()

    def add_child_steps(self, *steps):
        self.clear_cache()
        self.child_steps.add(*steps)

    def remove_child_steps(self, *steps):
        self.clear_cache()
        self.child_steps.remove(*steps)

    def clear_child_steps(self):
        self.clear_cache()
        self.child_steps.clear()

    def task_set(self):
        """
        Gets the unique tasks connected to the process, ignoring retries and
        undos.

        Returns:
            Unique tasks connected to the process, ignoring retries and undos
        """
        return self.tasks.filter(
            undo_type=False,
            retried__isnull=True
        ).order_by("processstep_pos")

    def clear_cache(self):
        """
        Clears the cache for this step and all its ancestors
        """

        cache.delete(self.cache_status_key)
        cache.delete(self.cache_progress_key)

        if self.parent_step:
            self.parent_step.clear_cache()

    def run_children(self, tasks, steps, direct=True):

        if not tasks.exists() and not steps.exists():
            if direct:
                return EagerResult(self.celery_id, [], celery_states.SUCCESS)

            return group()

        func = group if self.parallel else chain
        result_list = sorted(itertools.chain(steps, tasks), key=lambda x: (x.get_pos(), x.time_created))

        on_error_tasks = self.on_error(manager='by_step_pos').all()
        if on_error_tasks.exists():
            on_error_group = group(create_sub_task(t, self, immutable=False) for t in on_error_tasks)
        else:
            on_error_group = None

        if direct:
            logger.debug('Creating celery workflow')
        else:
            logger.debug('Creating partial celery workflow')

        workflow = func(
            y for y in (x.resume(direct=False) if isinstance(x, ProcessStep) else create_sub_task(
                x, self, link_error=on_error_group) for x in result_list
            ) if not hasattr(y, 'tasks') or len(y.tasks))

        if direct:
            logger.info('Celery workflow created')
        else:
            logger.info('Partial celery workflow created')

        if direct:
            if self.eager:
                logger.info('Running workflow eagerly')
                return workflow.apply(link_error=on_error_group)
            else:
                logger.info('Running workflow non-eagerly')
                return workflow.apply_async(link_error=on_error_group)
        else:
            return workflow

    def run(self, direct=True):
        """
        Runs the process step by first running the child steps and then the
        tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed workflow consisting of potential child steps followed by
            tasks if called directly. The workflow "non-executed" if direct is
            false
        """

        child_steps = self.child_steps.all()
        tasks = self.tasks(manager='by_step_pos').all()

        return self.run_children(tasks, child_steps, direct)

    def undo(self, only_failed=False, direct=True):
        """
        Undos the process step by first undoing all tasks and then the
        child steps.

        Args:
            only_failed: If true, only undo the failed tasks,
                undo all tasks otherwise

        Returns:
            AsyncResult/EagerResult if there is atleast one task or child
            steps, otherwise None
        """

        child_steps = self.child_steps.all()
        tasks = self.tasks(manager='by_step_pos').all()

        if only_failed:
            tasks = tasks.filter(status=celery_states.FAILURE)

        tasks = tasks.filter(
            undo_type=False,
            undone__isnull=True
        )

        if not tasks.exists() and not child_steps.exists():
            if direct:
                return EagerResult(self.celery_id, [], celery_states.SUCCESS)

            return group()

        func = group if self.parallel else chain

        result_list = sorted(
            itertools.chain(child_steps, tasks), key=lambda x: (x.get_pos(), x.time_created), reverse=True
        )
        workflow = func(
            x.undo(only_failed=only_failed, direct=False) if isinstance(x, ProcessStep) else create_sub_task(
                x.create_undo_obj(), self
            ) for x in result_list
        )

        if direct:
            if self.eager:
                return workflow.apply()
            else:
                return workflow.apply_async()
        else:
            return workflow

    def retry(self, direct=True):
        """
        Retries the process step by first retrying all child steps and then all
        failed tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            none
        """

        child_steps = self.child_steps.all()

        tasks = self.tasks(manager='by_step_pos').filter(
            undone__isnull=False,
            retried__isnull=True
        ).order_by('processstep_pos')

        if not tasks.exists() and not child_steps.exists():
            if direct:
                return EagerResult(self.celery_id, [], celery_states.SUCCESS)

            return group()

        func = group if self.parallel else chain

        result_list = sorted(itertools.chain(child_steps, tasks), key=lambda x: (x.get_pos(), x.time_created))
        workflow = func(
            x.retry(direct=False) if isinstance(x, ProcessStep) else create_sub_task(
                x.create_retry_obj(), self
            ) for x in result_list
        )

        if direct:
            if self.eager:
                return workflow.apply()
            else:
                return workflow.apply_async()
        else:
            return workflow

    def resume(self, direct=True):
        """
        Resumes the process step by running all pending child steps and tasks

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed workflow if direct is true, the workflow non-executed
            otherwise
        """

        logger.debug('Resuming step {} ({})'.format(self.name, self.pk))
        child_steps = self.get_children()

        step_descendants = self.get_descendants(include_self=True)
        recursive_tasks = ProcessTask.objects.filter(
            processstep__in=step_descendants,
            undone__isnull=True, undo_type=False,
            status=celery_states.PENDING,
        )

        if not recursive_tasks.exists():
            if direct:
                return EagerResult(self.celery_id, [], celery_states.SUCCESS)

            return group()

        tasks = self.tasks(manager='by_step_pos').filter(
            undone__isnull=True, undo_type=False, status=celery_states.PENDING
        )

        return self.run_children(tasks, child_steps, direct)

    @property
    def cache_lock_key(self):
        return '%s_lock' % str(self.pk)

    @property
    def cache_status_key(self):
        return '%s_status' % str(self.pk)

    @property
    def cache_progress_key(self):
        return '%s_progress' % str(self.pk)

    @property
    def time_started(self):
        try:
            earliest_task = self.get_descendants(
                include_self=True
            ).exclude(tasks=None).earliest(
                'tasks__time_started'
            ).tasks.earliest('time_started')

            return earliest_task.time_started
        except ProcessTask.DoesNotExist:
            return None

    @property
    def time_done(self):
        try:
            latest_task = self.get_descendants(
                include_self=True
            ).exclude(tasks=None).latest(
                'tasks__time_done'
            ).tasks.latest('time_done')

            return latest_task.time_done
        except ProcessTask.DoesNotExist:
            return None

    @property
    def progress(self):
        """
        Gets the progress of the step based on its child steps and tasks

        Args:

        Returns:
            The progress calculated by progress/total where progress simply is
            the progress (0-100) of all the underlying tasks and the total is
            |child_steps| + |tasks|
        """

        with cache.lock(self.cache_lock_key, timeout=60):
            cached = cache.get(self.cache_progress_key)

            if cached is not None:
                return cached

            if not self.child_steps.exists() and not self.tasks.exists():
                progress = 0
                cache.set(self.cache_progress_key, progress)
                return progress

            child_steps = self.child_steps.all()
            progress = 0
            task_data = self.tasks.filter(undo_type=False, retried__isnull=True).aggregate(
                progress=Sum(Case(When(undone__isnull=False, then=0), default='progress')),
                task_count=Count('id')
            )

            total = len(child_steps) + task_data['task_count']

            if total == 0:
                cache.set(self.cache_progress_key, 100)
                return 100

            progress += sum([c.progress for c in child_steps])

            try:
                progress += task_data['progress']
            except BaseException:
                pass

            try:
                res = progress / total
                cache.set(self.cache_progress_key, res)
                return res
            except BaseException:
                cache.set(self.cache_progress_key, 0)
                return 0

    @property
    def status(self):
        """
        Gets the status of the step based on its child steps and tasks

        Args:

        Returns:
            Can be one of the following:
            SUCCESS, STARTED, FAILURE, PENDING

            Which is decided by five scenarios:

            * If there are no child steps nor tasks, then SUCCESS.
            * If there are child steps or tasks and they are all pending,
              then PENDING.
            * If a child step or task has started, then STARTED.
            * If a child step or task has failed, then FAILURE.
            * If all child steps and tasks have succeeded, then SUCCESS.
        """

        with cache.lock(self.cache_lock_key, timeout=60):
            cached = cache.get(self.cache_status_key)

            if cached is not None:
                return cached

            child_steps = self.child_steps.all()
            tasks = self.tasks.filter(undo_type=False, undone__isnull=True, retried__isnull=True)
            status = celery_states.SUCCESS

            if not child_steps.exists() and not tasks.exists():
                status = celery_states.PENDING
                cache.set(self.cache_status_key, status)
                return status

            if tasks.filter(status=celery_states.FAILURE).exists():
                cache.set(self.cache_status_key, celery_states.FAILURE)
                return celery_states.FAILURE

            if tasks.filter(status=celery_states.REVOKED).exists():
                cache.set(self.cache_status_key, celery_states.REVOKED)
                return celery_states.REVOKED

            if tasks.filter(status=celery_states.PENDING).exists():
                status = celery_states.PENDING

            if tasks.filter(status=celery_states.STARTED).exists():
                status = celery_states.STARTED

            for cs in child_steps.only('parent_step').iterator():
                if cs.status == celery_states.STARTED:
                    status = cs.status
                if (cs.status == celery_states.PENDING and
                        status != celery_states.STARTED):
                    status = cs.status
                if cs.status == celery_states.FAILURE:
                    cache.set(self.cache_status_key, cs.status)
                    return cs.status

            cache.set(self.cache_status_key, status)
            return status

    @property
    def undone(self):
        """
        Gets the undone state of the step based on its tasks and child steps

        Args:

        Returns:
            True if one or more child steps and/or tasks have undone set to
            true, false otherwise
        """

        for c in self.child_steps.iterator():
            if c.undone:
                return True

        if self.tasks.filter(undone__isnull=False, retried__isnull=True).exists():
            return True

        return False

    class Meta:
        db_table = 'ProcessStep'
        ordering = ('parent_step_pos', 'time_created')
        get_latest_by = "time_created"

    class MPTTMeta:
        parent_attr = 'parent_step'


class OrderedProcessTaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('processstep_pos', 'time_created')


class ProcessTask(Process):
    _states = list(zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    ))
    _states.sort()
    TASK_STATE_CHOICES = _states

    reference = models.CharField(max_length=255, blank=True, null=True, default=None)
    label = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        _('state'), max_length=50, default=celery_states.PENDING,
        choices=TASK_STATE_CHOICES
    )
    responsible = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, related_name='tasks', null=True
    )
    args = PickledObjectField(default=list)
    params = PickledObjectField(default=dict)
    result_params = PickledObjectField(default=dict)
    run_if = models.TextField(blank=True)
    time_started = models.DateTimeField(_('started at'), null=True, blank=True)
    time_done = models.DateTimeField(_('done at'), null=True, blank=True)
    traceback = models.TextField(blank=True)
    exception = PickledObjectField(null=True, default=None)
    meta = PickledObjectField(null=True, default=None, editable=False)
    processstep = models.ForeignKey(
        'ProcessStep', related_name='tasks', on_delete=models.CASCADE,
        null=True, blank=True
    )
    processstep_pos = models.IntegerField(_('ProcessStep position'), default=0)
    progress = models.IntegerField(default=0)
    undone = models.OneToOneField('self', on_delete=models.SET_NULL, related_name='undone_task', null=True, blank=True)
    undo_type = models.BooleanField(editable=False, default=False)
    retried = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        related_name='retried_task',
        null=True,
        blank=True
    )
    information_package = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=True)
    log = PickledObjectField(null=True, default=None)
    on_error = models.ManyToManyField('self', symmetrical=False)
    allow_failure = models.BooleanField(default=False)

    objects = models.Manager()
    by_step_pos = OrderedProcessTaskManager()

    def update_progress(self, progress):
        self.progress = (progress / 100) * 100
        self.save()

    def get_pos(self):
        return self.processstep_pos

    def get_root_step(self):
        if self.processstep is None:
            return None

        parent = self.processstep
        while parent.parent_step is not None:
            parent = parent.parent_step

        return parent

    def create_traceback(self):
        return tblib.Traceback.from_string(self.traceback).as_traceback()

    def reraise(self):
        from ESSArch_Core.celery.backends.database import DatabaseBackend

        tb = self.create_traceback()
        exc = DatabaseBackend.exception_to_python(self.exception)

        raise exc.with_traceback(tb)

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def create_remote_copy(self, session, host):
        create_remote_task_url = urljoin(host, reverse('processtask-list'))
        params = copy.deepcopy(self.params)
        params.pop('_options', None)
        ip_id = str(self.information_package.pk) if self.information_package.pk is not None else None
        data = {
            'id': str(self.pk),
            'name': self.name,
            'args': self.args,
            'params': self.params,
            'eager': self.eager,
            'information_package': ip_id,
        }
        r = session.post(create_remote_task_url, json=data, timeout=60)

        if r.status_code == 409:
            r = self.update_remote_copy(session, host)

        r.raise_for_status()
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def update_remote_copy(self, session, host):
        update_remote_task_url = urljoin(host, reverse('processtask-detail', args=(str(self.pk),)))
        params = copy.deepcopy(self.params)
        params.pop('_options', None)
        ip_id = str(self.information_package.pk) if self.information_package.pk is not None else None
        data = {
            'name': self.name,
            'args': self.args,
            'params': self.params,
            'eager': self.eager,
            'information_package': ip_id,
        }
        r = session.patch(update_remote_task_url, json=data, timeout=60)

        r.raise_for_status()
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def run_remote_copy(self, session, host):
        run_remote_task_url = urljoin(host, reverse('processtask-run', args=(str(self.pk),)))
        r = session.post(run_remote_task_url, timeout=60)
        r.raise_for_status()
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def retry_remote_copy(self, session, host):
        self.update_remote_copy(session, host)
        retry_remote_task_url = urljoin(host, reverse('processtask-retry', args=(str(self.pk),)))
        r = session.post(retry_remote_task_url, timeout=60)
        r.raise_for_status()
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def get_remote_copy(self, session, host):
        remote_task_url = urljoin(host, reverse('processtask-detail', args=(str(self.pk),)))
        r = session.get(remote_task_url, timeout=60)
        if r.status_code >= 400 and r.status_code != 404:
            r.raise_for_status()
        return r

    def reset(self):
        self.celery_id = uuid.uuid4()
        self.status = celery_states.PENDING
        self.time_started = None
        self.time_done = None
        self.traceback = ''
        self.exception = ''
        self.progress = 0
        self.save()
        return self

    def run(self):
        """
        Runs the task
        """

        t = create_task(self.name)

        ip_id = str(self.information_package_id) if self.information_package_id is not None else None
        step_id = str(self.processstep_id) if self.processstep_id is not None else None
        self.params['_options'] = {
            'responsible': self.responsible_id, 'ip':
            ip_id, 'step': step_id,
            'step_pos': self.processstep_pos, 'hidden': self.hidden,
            'allow_failure': self.allow_failure,
        }

        on_error_tasks = self.on_error(manager='by_step_pos').all()
        if on_error_tasks.exists():
            on_error_group = group(create_sub_task(error_task, immutable=False) for error_task in on_error_tasks)
        else:
            on_error_group = None

        if self.eager:
            self.params['_options']['result_params'] = self.result_params
            logger.debug('Running task eagerly ({})'.format(self.pk))
            res = t.apply(args=self.args, kwargs=self.params, task_id=str(self.celery_id), link_error=on_error_group)
        else:
            logger.debug('Running task non-eagerly ({})'.format(self.pk))
            res = t.apply_async(
                args=self.args,
                kwargs=self.params,
                task_id=str(self.celery_id),
                link_error=on_error_group,
                queue=t.queue
            )

        return res

    def undo(self):
        """
        Undos the task
        """

        t = create_task(self.name)

        undoobj = self.create_undo_obj()
        ip_id = str(self.information_package_id) if self.information_package_id is not None else None
        step_id = str(self.processstep_id) if self.processstep_id is not None else None
        self.params['_options'] = {
            'responsible': self.responsible_id, 'ip':
            ip_id, 'step': step_id, 'step_pos': self.processstep_pos,
            'hidden': self.hidden, 'undo': True,
            'allow_failure': self.allow_failure,
        }

        if undoobj.eager:
            undoobj.params['_options']['result_params'] = undoobj.result_params
            logger.debug('Undoing task eagerly ({})'.format(self.pk))
            res = t.apply(args=undoobj.args, kwargs=undoobj.params, task_id=str(undoobj.celery_id))
        else:
            logger.debug('Undoing task non-eagerly ({})'.format(self.pk))
            res = t.apply_async(args=undoobj.args, kwargs=undoobj.params, task_id=str(undoobj.celery_id),
                                queue=t.queue)

        return res

    def revoke(self):
        logger.debug('Revoking task ({})'.format(self.pk))
        revoke(self.celery_id, terminate=True)
        logger.info('Revoked task ({})'.format(self.pk))

    def retry(self):
        """
        Retries the task
        """

        logger.debug('Retrying task ({})'.format(self.pk))
        self.reset()
        return self.run()

    def create_undo_obj(self):
        """
        Create a new task that will be used to undo this task,
        also marks this task as undone
        """

        undo_obj = ProcessTask.objects.create(
            processstep=self.processstep, name=self.name, args=self.args,
            params=self.params, result_params=self.result_params,
            processstep_pos=self.processstep_pos,
            undo_type=True, status="PREPARED",
            information_package=self.information_package,
            eager=self.eager, responsible=self.responsible,
        )

        self.undone = undo_obj
        self.save(update_fields=['undone'])

        return undo_obj

    def create_retry_obj(self):
        """
        Create a new task that will be used to retry this task,
        also marks this task as retried
        """

        retry_obj = ProcessTask.objects.create(
            processstep=self.processstep, name=self.name, label=self.label, args=self.args,
            params=self.params, result_params=self.result_params, processstep_pos=self.processstep_pos,
            status="PREPARED", information_package=self.information_package,
            eager=self.eager, responsible=self.responsible,
        )

        self.retried = retry_obj
        self.save(update_fields=['retried'])

        return retry_obj

    def __str__(self):
        return '%s - %s' % (self.name, self.id)

    class Meta:
        db_table = 'ProcessTask'
        ordering = ('processstep_pos', 'time_created')
        get_latest_by = "time_created"
        unique_together = (('reference', 'processstep'))

        permissions = (
            ('can_run', 'Can run tasks'),
            ('can_undo', 'Can undo tasks'),
            ('can_revoke', 'Can revoke tasks'),
            ('can_retry', 'Can retry tasks'),
        )
