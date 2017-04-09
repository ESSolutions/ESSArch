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

from __future__ import unicode_literals

import importlib
import uuid

from celery import chain, group, states as celery_states
from celery.result import EagerResult

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, Count, Sum, When
from django.utils import timezone
from django.utils.translation import ugettext as _

from picklefield.fields import PickledObjectField

from ESSArch_Core.util import available_tasks, chunks, flatten, sliceUntilAttr

class Process(models.Model):
    def _create_task(self, name):
        """
        Create and instantiate the task with the given name

        Args:
            name: The name of the task, including package and module
        """
        [module, task] = name.rsplit('.', 1)
        return getattr(importlib.import_module(module), task)()

    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eager = models.BooleanField(default=True)
    time_created = models.DateTimeField(auto_now_add=True)
    result = PickledObjectField(null=True, default=None, editable=False)

    def __unicode__(self):
        return self.name


class ProcessStep(Process):
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

    name = models.CharField(max_length=256)
    type = models.IntegerField(null=True, choices=Type_CHOICES)
    user = models.CharField(max_length=45)
    parent_step = models.ForeignKey(
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
    hidden = models.BooleanField(default=False)
    parallel = models.BooleanField(default=False)

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

    def run(self, direct=True):
        """
        Runs the process step by first running the child steps and then the
        tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed chain consisting of potential child steps followed by
            tasks if called directly. The chain "non-executed" if direct is
            false
        """

        def create_sub_task(t):
            created = self._create_task(t.name)
            t.params['_options'] = {
                'responsible': t.responsible_id, 'ip': t.information_package_id,
                'step': self.id, 'step_pos': t.processstep_pos, 'hidden': t.hidden,
                'result_params': t.result_params,
            }
            return created.si(**t.params).set(task_id=str(t.pk), queue=created.queue)

        func = group if self.parallel else chain

        child_steps = self.child_steps.all()
        tasks = self.tasks(manager='by_step_pos').all()

        if not tasks.exists() and not child_steps.exists():
            if direct:
                return EagerResult(self.pk, [], celery_states.SUCCESS)

            return group()

        step_canvas = func(s.run(direct=False) for s in child_steps) if child_steps else chain()
        task_canvas = func(create_sub_task(t) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        if direct:
            if self.eager:
                return workflow.apply()
            else:
                return workflow.apply_async()
        else:
            return workflow

    def chunk(self, size=None, direct=True):
        def create_options(task):
            return {
                'responsible': task.responsible_id, 'ip': task.information_package_id,
                'step': self.pk, 'step_pos': task.processstep_pos, 'hidden': task.hidden,
                'task_id': task.pk
            }

        tasks = self.tasks.all().order_by('time_created').iterator()

        try:
            first = tasks.next()
        except StopIteration:
            return []

        t = self._create_task(first.name)

        first.params['_options'] = create_options(first)
        params = [first.params]

        for task in tasks:
            task.params['_options'] = create_options(task)
            params.append(task.params)

        if size is None:
            size = len(params)

        res = []

        for param_chunk in chunks(params, size):
            res.append(t.apply_async(args=params, kwargs={'_options': {'chunk': True}}, queue=t.queue).get())

        return flatten(res)

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

        def create_sub_task(t):
            t = t.create_undo_obj()
            t.params['_options'] = {
                'responsible': t.responsible_id, 'ip': t.information_package_id,
                'step': self.id, 'step_pos': t.processstep_pos, 'hidden': t.hidden,
                'undo': True, 'result_params': t.result_params,
            }
            created = self._create_task(t.name)
            return created.si(True, **t.params).set(task_id=str(t.pk), queue=created.queue)

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
                return EagerResult(self.pk, [], celery_states.SUCCESS)

            return group()

        func = group if self.parallel else chain

        task_canvas = func(create_sub_task(t) for t in tasks.reverse())
        step_canvas = func(s.undo(direct=False) for s in child_steps.reverse())

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (task_canvas | step_canvas)

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

        def create_sub_task(t):
            t = t.create_retry_obj()
            t.params['_options'] = {
                'responsible': t.responsible_id, 'ip': t.information_package_id,
                'step': self.id, 'step_pos': t.processstep_pos, 'hidden': t.hidden,
                'result_params': t.result_params,
            }
            created = self._create_task(t.name)
            return created.si(False, **t.params).set(task_id=str(t.pk), queue=created.queue)

        child_steps = self.child_steps.all()

        tasks = self.tasks(manager='by_step_pos').filter(
            undone__isnull=False,
            retried__isnull=True
        ).order_by('processstep_pos')

        if not tasks.exists() and not child_steps.exists():
            if direct:
                return EagerResult(self.pk, [], celery_states.SUCCESS)

            return group()

        func = group if self.parallel else chain

        step_canvas = func(s.retry(direct=False) for s in child_steps)
        task_canvas = func(create_sub_task(t) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

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

        def create_sub_task(t):
            created = self._create_task(t.name)
            t.params['_options'] = {
                'responsible': t.responsible_id, 'ip': t.information_package_id,
                'step': self.id, 'step_pos': t.processstep_pos, 'hidden': t.hidden,
                'result_params': t.result_params
            }
            return created.si(**t.params).set(task_id=str(t.pk), queue=created.queue)

        func = group if self.parallel else chain

        child_steps = self.child_steps.filter(tasks__status=celery_states.PENDING)
        tasks = self.tasks(manager='by_step_pos').filter(undone__isnull=True, undo_type=False, status=celery_states.PENDING)

        if not tasks.exists() and not child_steps.exists():
            return EagerResult(self.pk, [], celery_states.SUCCESS)

        step_canvas = func(s.run(direct=False) for s in child_steps)
        task_canvas = func(create_sub_task(t) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        if direct:
            if self.eager:
                return workflow.apply()
            else:
                return workflow.apply_async()
        else:
            return workflow

    @property
    def cache_status_key(self):
        return '%s_status' % str(self.pk)

    @property
    def cache_progress_key(self):
        return '%s_progress' % str(self.pk)

    @property
    def time_started(self):
        if self.tasks.exists():
            return self.tasks.first().time_started

    @property
    def time_done(self):
        if self.tasks.exists():
            return self.tasks.first().time_done

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

        cached = cache.get(self.cache_progress_key)

        if cached:
            return cached

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
        except:
            pass

        try:
            res = progress / total
            cache.set(self.cache_progress_key, res)
            return res
        except:
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

        cached = cache.get(self.cache_status_key)

        if cached:
            return cached

        child_steps = self.child_steps.all()
        tasks = self.tasks.filter(undo_type=False, undone__isnull=True, retried__isnull=True)
        status = celery_states.SUCCESS

        if not child_steps and not tasks:
            cache.set(self.cache_status_key, status)
            return status

        for i in list(child_steps) + list(tasks):
            istatus = i.status
            if istatus == celery_states.STARTED:
                status = istatus
            if (istatus == celery_states.PENDING and
                    status != celery_states.STARTED):
                status = istatus
            if istatus == celery_states.FAILURE:
                cache.set(self.cache_status_key, istatus)
                return istatus

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

        child_steps = self.child_steps.all()
        undone_child_steps = any(c.undone for c in child_steps)
        undone_tasks = self.tasks.filter(undone__isnull=False, retried__isnull=True).exists()

        return undone_child_steps or undone_tasks

    class Meta:
        db_table = u'ProcessStep'
        ordering = ('parent_step_pos', 'time_created')
        get_latest_by = "time_created"

        def __unicode__(self):
            return '%s - %s - archiveobject:%s' % (
                self.name,
                self.id,
                self.archiveobject.ObjectUUID
            )


class OrderedProcessTaskManager(models.Manager):
    def get_queryset(self):
        return super(OrderedProcessTaskManager, self).get_queryset().order_by('processstep_pos')


class ProcessTask(Process):
    TASK_STATE_CHOICES = zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    )

    name = models.CharField(max_length=255)
    status = models.CharField(
        _('state'), max_length=50, default=celery_states.PENDING,
        choices=TASK_STATE_CHOICES
    )
    responsible = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, related_name='tasks', null=True
    )
    params = PickledObjectField(null=True, default={})
    result_params = PickledObjectField(null=True)
    time_started = models.DateTimeField(_('started at'), null=True, blank=True)
    time_done = models.DateTimeField(_('done at'), null=True, blank=True)
    traceback = models.TextField(blank=True)
    exception = models.TextField(blank=True)
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    meta = PickledObjectField(null=True, default=None, editable=False)
    processstep = models.ForeignKey(
        'ProcessStep', related_name='tasks', on_delete=models.CASCADE,
        null=True, blank=True
    )
    processstep_pos = models.IntegerField(_('ProcessStep position'), default=0)
    progress = models.IntegerField(default=0)
    undone = models.OneToOneField('self', on_delete=models.SET_NULL, related_name='undone_task', null=True, blank=True)
    undo_type = models.BooleanField(editable=False, default=False)
    retried = models.OneToOneField('self', on_delete=models.SET_NULL, related_name='retried_task', null=True, blank=True)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    log = PickledObjectField(null=True, default=None)

    objects = models.Manager()
    by_step_pos = OrderedProcessTaskManager()

    def clean(self):
        """
        Validates the task
        """

        full_task_names = [k for k, v in available_tasks()]

        # Make sure that the task exists
        if self.name not in full_task_names:
            raise ValidationError("Task '%s' does not exist." % self.name)

    def run(self):
        """
        Runs the task
        """

        t = self._create_task(self.name)

        self.params['_options'] = {
            'responsible': self.responsible_id, 'ip': self.information_package_id,
            'step': self.processstep_id, 'step_pos': self.processstep_pos, 'hidden': self.hidden,
        }

        if self.eager:
            self.params['_options']['result_params'] = self.result_params
            res = t.apply(kwargs=self.params, task_id=str(self.pk))
        else:
            res = t.apply_async(kwargs=self.params, task_id=str(self.pk), queue=t.queue)

        return res

    def undo(self):
        """
        Undos the task
        """

        t = self._create_task(self.name)

        undoobj = self.create_undo_obj()
        self.params['_options'] = {
            'responsible': self.responsible_id, 'ip': self.information_package_id,
            'step': self.processstep_id, 'step_pos': self.processstep_pos, 'hidden': self.hidden,
            'undo': True,
        }

        res = t.apply_async(args=(True,), kwargs=undoobj.params, task_id=str(undoobj.pk), queue=t.queue)
        return res

    def retry(self):
        """
        Retries the task
        """

        t = self._create_task(self.name)

        retryobj = self.create_retry_obj()
        self.params['_options'] = {
            'responsible': self.responsible_id, 'ip': self.information_package_id,
            'step': self.processstep_id, 'step_pos': self.processstep_pos, 'hidden': self.hidden,
        }

        res = t.apply_async(kwargs=retryobj.params, task_id=str(retryobj.pk), queue=t.queue)
        return res

    def create_undo_obj(self):
        """
        Create a new task that will be used to undo this task,
        also marks this task as undone
        """


        undo_obj = ProcessTask.objects.create(
            processstep=self.processstep, name=self.name,
            params=self.params, result_params=self.result_params,
            processstep_pos=self.processstep_pos,
            undo_type=True, status="PREPARED",
            information_package=self.information_package
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
            processstep=self.processstep, name=self.name, params=self.params,
            result_params=self.result_params, processstep_pos=self.processstep_pos,
            status="PREPARED", information_package=self.information_package,
            retried_task=self
        )

        self.retried = retry_obj
        self.save(update_fields=['retried'])

        return retry_obj

    class Meta:
        db_table = 'ProcessTask'
        get_latest_by = "time_created"

        permissions = (
            ('can_undo', 'Can undo tasks'),
            ('can_retry', 'Can retry tasks'),
        )

        def __unicode__(self):
            return '%s - %s' % (self.name, self.id)
