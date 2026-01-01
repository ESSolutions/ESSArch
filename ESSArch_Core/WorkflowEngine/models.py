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
import time
import uuid
from urllib.parse import urljoin

import tblib
from celery import chain, current_app, group, states as celery_states
from celery.result import EagerResult
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.translation import gettext as _
from mptt.models import MPTTModel, TreeForeignKey
from picklefield.fields import PickledObjectField
from relativity.mptt import MPTTDescendants, MPTTSubtree
from requests import RequestException
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)


def create_task(name):
    """
    Create and instantiate the task with the given name

    Args:
        name: The name of the task, including package and module
    """
    logger = logging.getLogger('essarch.WorkflowEngine')
    [module, task] = name.rsplit('.', 1)
    logger.debug('Importing task {} from module {}'.format(task, module))
    return getattr(importlib.import_module(module), task)


def create_sub_task(t, step=None, immutable=True, link_error=None):
    logger = logging.getLogger('essarch.WorkflowEngine')
    if t.queue:
        logger.debug('Creating sub task in queue: {}'.format(t.queue))
    else:
        logger.debug('Creating sub task')
    ip_id = str(t.information_package_id) if t.information_package_id is not None else None
    step_id = str(step.id) if step is not None else None
    headers = {
        'responsible': t.responsible_id,
        'ip': ip_id, 'step': step_id,
        'step_pos': t.processstep_pos, 'hidden': t.hidden,
        'allow_failure': t.allow_failure,
        'result_params': t.result_params,
        'parallel': t.processstep.parallel if t.processstep else False,
    }
    headers_hack = {'headers': headers}

    created = create_task(t.name)
    if t.queue:
        created.queue = t.queue

    # For some reason, __repr__ needs to be called for the link_error
    # signature to be called when an error occurs in a task
    repr(link_error)

    res = created.signature(t.args, t.params, immutable=immutable).set(
        task_id=str(t.celery_id), link_error=link_error, queue=created.queue,
        headers=headers_hack,
    )
    logger.info('Created {} sub task signature'.format('immutable' if immutable else ''))

    return res


class Process(models.Model):
    _states = list(zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    ))
    _states.sort()
    STATE_CHOICES = _states

    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    celery_id = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    label = models.CharField(max_length=255, blank=True)
    queue = models.CharField(max_length=255, blank=True, null=True, default=None)
    hidden = models.BooleanField(null=True, default=None, db_index=True)
    eager = models.BooleanField(default=True)
    time_created = models.DateTimeField(auto_now_add=True)
    result = PickledObjectField(null=True, default=None, editable=False)

    def __str__(self):
        return self.label if self.label else self.name


class ProcessStep(MPTTModel, Process):
    run_state = models.CharField(_('state'), max_length=50, blank=True, choices=Process.STATE_CHOICES, db_index=True)
    user = models.CharField(max_length=45)
    parent = TreeForeignKey('self', related_name='child_steps', on_delete=models.CASCADE, null=True)
    parent_pos = models.IntegerField(_('Parent step position'), default=0)
    part_root = models.BooleanField(null=True, default=None, db_index=True)
    information_package = models.ForeignKey(
        'ip.InformationPackage', on_delete=models.CASCADE, related_name='steps', blank=True, null=True)
    responsible = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name='steps', null=True)
    parallel = models.BooleanField(default=False)
    on_error = models.ManyToManyField('ProcessTask', related_name='steps_on_errors')
    context = models.JSONField(default=dict, null=True)
    descendants = MPTTDescendants()
    subtree = MPTTSubtree()

    def get_pos(self):
        return self.parent_pos

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
        Gets the unique tasks connected to the process, ignoring retries

        Returns:
            Unique tasks connected to the process, ignoring retries
        """
        return self.tasks.filter(retried__isnull=True).order_by("processstep_pos")

    def clear_cache(self):
        """
        Clears the cache for this step and all its ancestors
        """

        cache.delete(self.cache_status_key)
        cache.delete(self.cache_progress_key)

        if self.parent:
            self.parent.clear_cache()

    def get_part_root(self):
        """
        Returns the part root node of this model instance's tree.
        """
        if (self.is_root_node() or self.part_root) and type(self) is self._tree_manager.tree_model:
            return self

        try:
            node = self.get_ancestors().filter(part_root=True).get()
        except ProcessStep.MultipleObjectsReturned:
            node = self.parent.get_part_root()
        except ProcessStep.DoesNotExist:
            node = self.get_root()

        return node

    def run_children(self, tasks, steps, direct=True):
        logger = logging.getLogger('essarch.WorkflowEngine')
        tasks = tasks.filter(status=celery_states.PENDING,)

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
        logger.debug('workflow: {} and link_error: {}'.format(workflow, on_error_group))

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

    def run(self, direct=True, poller=False):
        """
        Runs the process step by first running the child steps and then the
        tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise
            poller: True to run step with poller

        Returns:
            The executed workflow consisting of potential child steps followed by
            tasks if called directly. The workflow "non-executed" if direct is
            false
        """
        if poller:
            for child_step in self.get_children().filter(part_root=True, run_state=''):
                child_step.run_state = celery_states.PENDING
                child_step.save(update_fields=['run_state'])
            if not self.run_state and (self.parent is None or self.root_part is True):
                self.run_state = celery_states.PENDING
                self.save(update_fields=['run_state'])
                return True
            else:
                return False

        child_steps = self.child_steps.all()
        tasks = self.tasks(manager='by_step_pos').all()

        return self.run_children(tasks, child_steps, direct)

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

        logger = logging.getLogger('essarch.WorkflowEngine')
        logger.info('Retrying step {} ({})'.format(self.name, self.pk))
        child_steps = self.child_steps.all()

        tasks = self.tasks(manager='by_step_pos').filter(
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

        logger = logging.getLogger('essarch.WorkflowEngine')
        logger.info('Resuming step {} ({})'.format(self.name, self.pk))
        for t in ProcessTask.objects.filter(
            processstep__in=self.get_descendants(include_self=True),
            status__in=[celery_states.PENDING, celery_states.FAILURE, celery_states.REVOKED],
        ):
            t.reset()
        child_steps = self.get_children()

        step_descendants = self.get_descendants(include_self=True)
        recursive_tasks = ProcessTask.objects.filter(
            processstep__in=step_descendants,
            status=celery_states.PENDING,
        )

        if not recursive_tasks.exists():
            if direct:
                return EagerResult(self.celery_id, [], celery_states.SUCCESS)

            return group()

        tasks = self.tasks(manager='by_step_pos').filter(
            status=celery_states.PENDING
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
            ).exclude(tasks=None).filter(tasks__time_started__isnull=False).earliest(
                'tasks__time_started'
            ).tasks.filter(time_started__isnull=False).earliest('time_started')

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
            task_data = self.tasks.filter(retried__isnull=True).aggregate(
                progress=Sum('progress'),
                task_count=Count('id')
            )

            total = len(child_steps) + task_data['task_count']

            if total == 0:
                cache.set(self.cache_progress_key, 100)
                return 100

            progress += sum([c.progress for c in child_steps])

            try:
                progress += task_data['progress']
            except Exception:
                pass

            try:
                res = progress / total
                cache.set(self.cache_progress_key, res)
                return res
            except Exception:
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
            tasks = self.tasks.filter(retried__isnull=True)
            status = celery_states.SUCCESS
            partially_done = False

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

            if tasks.filter(status=celery_states.SUCCESS).exists():
                partially_done = True

            if tasks.filter(status=celery_states.PENDING).exists():
                if partially_done:
                    status = celery_states.STARTED
                else:
                    status = celery_states.PENDING

            if tasks.filter(status=celery_states.STARTED).exists():
                status = celery_states.STARTED

            partially_done = False
            for cs in child_steps.only('parent').iterator(chunk_size=1000):
                if cs.status == celery_states.STARTED:
                    status = cs.status
                if cs.status == celery_states.SUCCESS:
                    partially_done = True
                if (cs.status == celery_states.PENDING and status != celery_states.STARTED):
                    if partially_done:
                        status = celery_states.STARTED
                    else:
                        status = cs.status
                if cs.status == celery_states.FAILURE:
                    cache.set(self.cache_status_key, cs.status)
                    return cs.status

            cache.set(self.cache_status_key, status)
            return status

    class Meta:
        db_table = 'ProcessStep'
        ordering = ('parent_pos', 'time_created')
        get_latest_by = "time_created"

    class MPTTMeta:
        parent_attr = 'parent'


class OrderedProcessTaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('processstep_pos', 'time_created')


class ProcessTask(Process):
    reference = models.CharField(max_length=255, blank=True, null=True, default=None)
    status = models.CharField(_('state'), max_length=50, default=celery_states.PENDING, choices=Process.STATE_CHOICES)
    responsible = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name='tasks', null=True)
    args = PickledObjectField(default=list)
    params = PickledObjectField(default=dict)
    result_params = PickledObjectField(default=dict)
    run_if = models.TextField(blank=True)
    time_started = models.DateTimeField(_('started at'), null=True, blank=True)
    time_done = models.DateTimeField(_('done at'), null=True, blank=True)
    traceback = models.TextField(blank=True)
    exception = PickledObjectField(null=True, default=None)
    meta = PickledObjectField(null=True, default=None, editable=False)
    processstep = models.ForeignKey('ProcessStep', related_name='tasks',
                                    on_delete=models.CASCADE, null=True, blank=True)
    processstep_pos = models.IntegerField(_('ProcessStep position'), default=0)
    progress = models.IntegerField(default=0)
    retried = models.OneToOneField('self', on_delete=models.SET_NULL,
                                   related_name='retried_task', null=True, blank=True)
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
        return parent.get_root()

    def get_part_root_step(self):
        if self.processstep is None:
            return None

        parent = self.processstep
        return parent.get_part_root()

    def create_traceback(self):
        return tblib.Traceback.from_string(self.traceback).as_traceback()

    def reraise(self):
        from ESSArch_Core.celery.backends.database import DatabaseBackend

        tb = self.create_traceback()
        exc = DatabaseBackend.exception_to_python(self.exception)

        raise exc.with_traceback(tb)

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.WorkflowEngine'),
                                                              logging.DEBUG))
    def create_remote_copy(self, session, host, exclude_remote_params=True):
        logger = logging.getLogger('essarch.WorkflowEngine')
        create_remote_task_url = urljoin(host, reverse('processtask-list'))
        params = copy.deepcopy(self.params)
        params.pop('_options', None)
        if exclude_remote_params:
            params.pop('remote_host', None)
            params.pop('remote_credentials', None)
        ip_id = str(self.information_package.pk) if self.information_package.pk is not None else None
        data = {
            'id': str(self.pk),
            'name': self.name,
            'label': self.label,
            'args': self.args,
            'params': params,
            'eager': self.eager,
            'responsible': self.responsible.username if self.responsible else None,
            'information_package': ip_id,
        }
        r = session.post(create_remote_task_url, json=data, timeout=60)

        if r.status_code == 409:
            logger.exception("Problem to add task {} for IP: {} to remote server. Response: {}".format(
                self.pk, ip_id, r.text))
            r = self.update_remote_copy(session, host)

        try:
            r.raise_for_status()
        except RequestException:
            logger.exception("Problem to create_remote_copy task: {} for IP: {} to remote server. Response: {}".format(
                self.pk, self.information_package, r.text))
            raise
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.WorkflowEngine'),
                                                              logging.DEBUG))
    def update_remote_copy(self, session, host, exclude_remote_params=True):
        logger = logging.getLogger('essarch.WorkflowEngine')
        update_remote_task_url = urljoin(host, reverse('processtask-detail', args=(str(self.pk),)))
        params = copy.deepcopy(self.params)
        params.pop('_options', None)
        if exclude_remote_params:
            params.pop('remote_host', None)
            params.pop('remote_credentials', None)
        ip_id = str(self.information_package.pk) if self.information_package.pk is not None else None
        data = {
            'name': self.name,
            'label': self.label,
            'args': self.args,
            'params': self.params,
            'eager': self.eager,
            'responsible': self.responsible.username if self.responsible else None,
            'information_package': ip_id,
        }
        r = session.patch(update_remote_task_url, json=data, timeout=60)
        try:
            r.raise_for_status()
        except RequestException:
            logger.exception("Problem to update_remote_copy task: {} for IP: {} to remote server. Response: {}".format(
                self.pk, self.information_package, r.text))
            raise
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.WorkflowEngine'),
                                                              logging.DEBUG))
    def run_remote_copy(self, session, host):
        logger = logging.getLogger('essarch.WorkflowEngine')
        run_remote_task_url = urljoin(host, reverse('processtask-run', args=(str(self.pk),)))
        r = session.post(run_remote_task_url, timeout=60)
        try:
            r.raise_for_status()
        except RequestException:
            logger.exception("Problem to run_remote_copy task: {} for IP: {} to remote server. Response: {}".format(
                self.pk, self.information_package, r.text))
            raise
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.WorkflowEngine'),
                                                              logging.DEBUG))
    def retry_remote_copy(self, session, host):
        logger = logging.getLogger('essarch.WorkflowEngine')
        self.update_remote_copy(session, host)
        retry_remote_task_url = urljoin(host, reverse('processtask-retry', args=(str(self.pk),)))
        r = session.post(retry_remote_task_url, timeout=60)
        try:
            r.raise_for_status()
        except RequestException:
            logger.exception("Problem to retry_remote_copy task: {} for IP: {} to remote server. Response: {}".format(
                self.pk, self.information_package, r.text))
            raise
        return r

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.WorkflowEngine'),
                                                              logging.DEBUG))
    def get_remote_copy(self, session, host):
        logger = logging.getLogger('essarch.WorkflowEngine')
        remote_task_url = urljoin(host, reverse('processtask-detail', args=(str(self.pk),)))
        r = session.get(remote_task_url, timeout=60)
        if r.status_code >= 400 and r.status_code != 404:
            try:
                r.raise_for_status()
            except RequestException:
                logger.exception("Problem to get_remote_copy task: {} for IP: {} to remote server. Response: {}\
".format(self.pk, self.information_package, r.text))
                raise
        return r

    def reset(self):
        logger = logging.getLogger('essarch.WorkflowEngine')
        logger.info('Reset task ({})'.format(self.pk))
        self.status = celery_states.PENDING
        self.celery_id = uuid.uuid4()
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
        logger = logging.getLogger('essarch.WorkflowEngine')
        t = create_task(self.name)
        if self.queue:
            t.queue = self.queue

        ip_id = str(self.information_package_id) if self.information_package_id is not None else None
        step_id = str(self.processstep_id) if self.processstep_id is not None else None
        headers = {
            'responsible': self.responsible_id, 'ip':
            ip_id, 'step': step_id,
            'step_pos': self.processstep_pos, 'hidden': self.hidden,
            'allow_failure': self.allow_failure,
            'parallel': self.processstep.parallel if self.processstep else False,
        }

        on_error_tasks = self.on_error(manager='by_step_pos').all()
        if on_error_tasks.exists():
            on_error_group = group(create_sub_task(error_task, immutable=False) for error_task in on_error_tasks)
        else:
            on_error_group = None

        if self.eager:
            headers['result_params'] = self.result_params
            headers_hack = {'headers': headers}
            logger.debug('Running task eagerly {}({})'.format(self.celery_id, self.pk))
            res = t.apply(
                args=self.args, kwargs=self.params,
                task_id=str(self.celery_id),
                link_error=on_error_group, headers=headers_hack,
            )
        else:
            headers_hack = {'headers': headers}
            logger.debug('Running task non-eagerly {}({})'.format(self.celery_id, self.pk))
            res = t.apply_async(
                args=self.args,
                kwargs=self.params,
                task_id=str(self.celery_id),
                link_error=on_error_group,
                queue=t.queue,
                headers=headers_hack,
            )

        return res

    def revoke(self):
        logger = logging.getLogger('essarch.WorkflowEngine')
        if self.information_package:
            logger.info('Revoke task ({}) for ip {}'.format(self.pk, self.information_package))
        else:
            logger.info('Revoke task ({})'.format(self.pk))
        current_app.control.revoke(str(self.celery_id), terminate=True)
        self.status = celery_states.REVOKED
        self.save()
        if self.information_package and self.information_package.is_locked():
            time.sleep(5)
            if self.information_package.is_locked():
                self.information_package.clear_lock()
                logger.info('When task ({}) revoked, unlocked ip {}'.format(self.pk, self.information_package))

    def retry(self):
        """
        Retries the task
        """
        logger = logging.getLogger('essarch.WorkflowEngine')
        logger.info('Retrying task ({})'.format(self.pk))
        self.reset()
        return self.run()

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
        indexes = [models.Index(fields=['retried', 'processstep', 'information_package'])]

        permissions = (
            ('can_run', 'Can run tasks'),
            ('can_revoke', 'Can revoke tasks'),
            ('can_retry', 'Can retry tasks'),
        )
