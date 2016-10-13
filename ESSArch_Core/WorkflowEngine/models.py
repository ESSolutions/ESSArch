from __future__ import unicode_literals

import importlib
import uuid

from celery import chain, group, states as celery_states

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.translation import ugettext as _

from picklefield.fields import PickledObjectField

from preingest.util import available_tasks, sliceUntilAttr


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
    time_created = models.DateTimeField(auto_now_add=True)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.CASCADE,
        related_name='steps',
        blank=True,
        null=True
    )
    hidden = models.BooleanField(default=False)
    waitForParams = models.BooleanField(default=False)
    parallel = models.BooleanField(default=False)

    def task_set(self):
        """
        Gets the unique tasks connected to the process, ignoring retries and
        undos.

        Returns:
            Unique tasks connected to the process, ignoring retries and undos
        """
        return self.tasks.filter(
            undo_type=False,
            retried=False
        ).order_by("processstep_pos")

    def run(self, continuing=False, direct=True):
        """
        Runs the process step by first running the child steps and then the
        tasks.

        Args:
            continuing: True if continuing a step that was waiting for params,
                        false otherwise
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed chain consisting of potential child steps followed by
            tasks if called directly. The chain "non-executed" if direct is
            false
        """

        child_steps = self.child_steps.all()

        if continuing:
            child_steps = [
                s for s in self.child_steps.all() if s.progress() < 100
            ]

        child_steps = list(sliceUntilAttr(child_steps, "waitForParams", True))

        func = group if self.parallel else chain

        tasks = self.tasks.all()

        step_canvas = func(s.run(direct=False) for s in child_steps)
        task_canvas = func(self._create_task(t.name).s(
            taskobj=t
        ) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        return workflow() if direct else workflow

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
        tasks = self.tasks.all()

        if only_failed:
            tasks = tasks.filter(status=celery_states.FAILURE)

        tasks = tasks.filter(
            undo_type=False,
            undone=False
        )

        attempt = uuid.uuid4()

        func = group if self.parallel else chain

        task_canvas = func(self._create_task(t.name).si(
            taskobj=t.create_undo_obj(attempt=attempt),
        ) for t in reversed(tasks))
        step_canvas = func(s.undo() for s in child_steps)

        workflow = (task_canvas | step_canvas)

        return workflow() if direct else workflow

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

        child_steps = sliceUntilAttr(
            self.child_steps.all(),
            "waitForParams", True
        )

        tasks = self.tasks.filter(
            undone=True,
            retried=False
        ).order_by('processstep_pos')

        func = group if self.parallel else chain
        attempt = uuid.uuid4()

        step_canvas = func(s.retry(direct=False) for s in child_steps)
        task_canvas = func(self._create_task(t.name).s(
            taskobj=t.create_retry_obj(attempt=attempt),
        ) for t in tasks)

        workflow = (step_canvas | task_canvas)

        return workflow() if direct else workflow

    def progress(self):
        """
        Gets the progress of the step based on its child steps and tasks

        Args:

        Returns:
            The progress calculated by progress/total where progress simply is
            the progress (0-100) of all the underlying tasks and the total is
            |child_steps| + |tasks|
        """

        child_steps = self.child_steps.all()
        progress = 0
        total = len(child_steps) + len(self.task_set())

        progress += sum([c.progress() for c in child_steps])

        tasks = self.tasks.filter(
            undone=False,
            undo_type=False,
            retried=False
        )

        try:
            progress += tasks.aggregate(Sum("progress"))["progress__sum"]
        except:
            pass

        try:
            return progress / total
        except:
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

            * If there are no child steps nor tasks, then PENDING.
            * If there are child steps or tasks and they are all pending,
              then PENDING.
            * If a child step or task has started, then STARTED.
            * If a child step or task has failed, then FAILURE.
            * If all child steps and tasks have succeeded, then SUCCESS.
        """

        child_steps = self.child_steps.all()
        tasks = self.tasks.filter(undo_type=False, undone=False, retried=False)
        status = celery_states.SUCCESS

        if not child_steps and not tasks:
            return celery_states.PENDING

        for i in list(child_steps) + list(tasks):
            if i.status == celery_states.STARTED:
                status = i.status
            if (i.status == celery_states.PENDING and
                    status != celery_states.STARTED):
                status = i.status
            if i.status == celery_states.FAILURE:
                return i.status

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
        undone_tasks = self.tasks.filter(undone=True, retried=False).exists()

        return undone_child_steps or undone_tasks

    class Meta:
        db_table = u'ProcessStep'
        ordering = ('parent_step_pos',)

        def __unicode__(self):
            return '%s - %s - archiveobject:%s' % (
                self.name,
                self.id,
                self.archiveobject.ObjectUUID
            )


class ProcessTask(Process):
    TASK_STATE_CHOICES = zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    )

    celery_id = models.UUIDField(
        _('celery id'), max_length=255, null=True, editable=False
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        _('state'), max_length=50, default=celery_states.PENDING,
        choices=TASK_STATE_CHOICES
    )
    params = PickledObjectField(null=True, default={})
    result_params = PickledObjectField(null=True, default={})
    time_started = models.DateTimeField(_('started at'), null=True, blank=True)
    time_done = models.DateTimeField(_('done at'), null=True, blank=True)
    traceback = models.TextField(
        _('traceback'), blank=True, null=True, editable=False
    )
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    meta = PickledObjectField(null=True, default=None, editable=False)
    processstep = models.ForeignKey(
        'ProcessStep', related_name='tasks', on_delete=models.CASCADE,
        null=True, blank=True
    )
    processstep_pos = models.IntegerField(_('ProcessStep position'), default=0)
    attempt = models.UUIDField(default=uuid.uuid4)
    progress = models.IntegerField(default=0)
    undone = models.BooleanField(default=False)
    undo_type = models.BooleanField(editable=False, default=False)
    retried = models.BooleanField(default=False)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    def clean(self):
        """
        Validates the task
        """

        full_task_names = [k for k,v in available_tasks()]

        # Make sure that the task exists
        if self.name not in full_task_names:
            raise ValidationError("Task '%s' does not exist." % self.name)

    def run(self):
        """
        Runs the task
        """

        if not self.information_package:
            raise AttributeError(
                "An IP is required to be set on the task if not run eagerly"
            )

        return self._create_task(self.name).delay(taskobj=self)

    def run_eagerly(self, **kwargs):
        """
        Runs the task locally (as a "regular" function)
        """

        return self._create_task(self.name)(taskobj=self, eager=True)

    def undo(self):
        """
        Undos the task
        """

        return self._create_task(self.name).delay(
            taskobj=self.create_undo_obj()
        )

    def retry(self):
        """
        Retries the task
        """

        return self._create_task(self.name).delay(
            taskobj=self.create_retry_obj()
        )

    def create_undo_obj(self, attempt=uuid.uuid4()):
        """
        Create a new task that will be used to undo this task,
        also marks this task as undone

        Args:
            attempt: Which attempt the new task belongs to
        """

        self.undone = True
        self.save()

        return ProcessTask.objects.create(
            processstep=self.processstep, name="%s undo" % self.name,
            params=self.params, processstep_pos=self.processstep_pos,
            undo_type=True, attempt=attempt, status="PREPARED"
        )

    def create_retry_obj(self, attempt=uuid.uuid4()):
        """
        Create a new task that will be used to retry this task,
        also marks this task as retried

        Args:
            attempt: Which attempt the new task belongs to
        """

        self.retried = True
        self.save()

        return ProcessTask.objects.create(
            processstep=self.processstep, name=self.name, params=self.params,
            processstep_pos=self.processstep_pos, attempt=attempt,
            status="PREPARED", information_package=self.information_package,
        )

    class Meta:
        db_table = 'ProcessTask'
        ordering = ('processstep_pos',)

        def __unicode__(self):
            return '%s - %s' % (self.name, self.id)
