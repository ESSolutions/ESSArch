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

from celery import states as celery_states
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings, TestCase, TransactionTestCase

from django_redis import get_redis_connection

from ESSArch_Core.configuration.models import EventType

from ESSArch_Core.ip.models import EventIP, InformationPackage

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep, ProcessTask,
)

import os
import shutil


class test_status(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        self.step = ProcessStep.objects.create()

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_no_steps_or_tasks(self):
        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_nested_steps(self):
        depth = 5
        parent = self.step

        for i in range(depth):
            parent = ProcessStep.objects.create(parent_step=parent)

        with self.assertNumQueries(2*(depth+1)):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status(self):
        with self.assertNumQueries(2):
            self.step.status

        with self.assertNumQueries(0):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_nested_steps(self):
        depth = 5
        parent = self.step

        for i in range(depth):
            parent = ProcessStep.objects.create(parent_step=parent)

        self.step.status

        with self.assertNumQueries(0):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_create_task(self):
        self.step.status

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_add_task(self):

        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
        )

        self.step.status
        self.step.add_tasks(t)

        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_create_child_step(self):
        self.step.status

        ProcessStep.objects.create(parent_step=self.step)

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_add_child_step(self):
        s = ProcessStep.objects.create()

        self.step.status
        self.step.add_child_steps(s)

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_run_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        self.step.status

        t.run()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_run_task_in_nested_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.status

        t.run()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_undo_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={'foo': 123}, processstep=self.step
        )

        t.run()
        self.step.status
        t.undo()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_retry_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        t.run()
        t.undo()
        self.step.status
        t.retry()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_run_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.status
        s.run()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_undo_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        s.run()
        self.step.status
        s.undo()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_retry_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        s.run()
        s.undo()
        self.step.status
        s.retry()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_resume_step(self):
        test_dir = "test_dir"
        fname = os.path.join(test_dir, "foo.txt")

        try:
            os.mkdir(test_dir)
        except:
            pass

        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=s, processstep_pos=1
        )
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=s, processstep_pos=2
        )

        with self.assertRaises(AssertionError):
            s.run()

        s.undo(only_failed=True)
        open(fname, 'a').close()
        s.retry()
        self.step.status
        s.resume()

        try:
            shutil.rmtree(test_dir)
        except:
            pass

        with self.assertNumQueries(4):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_pending_task(self):
        t = ProcessTask.objects.create(status=celery_states.PENDING)
        self.step.tasks = [t]
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_pending_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.PENDING)

        s.tasks = [t]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_pending_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.PENDING)
        t2 = ProcessTask.objects.create(status=celery_states.PENDING)

        s.tasks = [t1]
        self.step.tasks = [t2]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_started_task(self):
        t = ProcessTask.objects.create(status=celery_states.STARTED)
        self.step.tasks = [t]
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_started_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.STARTED)

        s.tasks = [t]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_started_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.STARTED)
        t2 = ProcessTask.objects.create(status=celery_states.STARTED)

        s.tasks = [t1]
        self.step.tasks = [t2]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_succeeded_task(self):
        t = ProcessTask.objects.create(status=celery_states.SUCCESS)
        self.step.tasks = [t]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.SUCCESS)

        s.tasks = [t]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.SUCCESS)

        s.tasks = [t1]
        self.step.tasks = [t2]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_task(self):
        t = ProcessTask.objects.create(status=celery_states.FAILURE)
        self.step.tasks = [t]
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.FAILURE)

        s.tasks = [t]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)

        s.tasks = [t1]
        self.step.tasks = [t2]
        self.step.child_steps = [s]
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_task_after_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)

        self.step.tasks = [t1, t2]
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_started_task_after_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.STARTED)

        self.step.tasks = [t1, t2]
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_failed_task_between_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t3 = ProcessTask.objects.create(status=celery_states.SUCCESS)

        self.step.tasks = [t1, t2, t3]
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_succeeded_undone_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)

        t1.undone = t1_undo
        t1.save()

        self.step.tasks = [t1, t1_undo]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_retried_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)
        t1_retry = ProcessTask.objects.create(status=celery_states.SUCCESS)

        t1.undone = t1_undo
        t1.retried = t1_retry
        t1.save()

        self.step.tasks = [t1, t1_undo, t1_retry]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_undone_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)

        t1.undone = t1_undo
        t1.save()

        self.step.tasks = [t1, t1_undo]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_retried_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)
        t1_retry = ProcessTask.objects.create(status=celery_states.SUCCESS)

        t1.undone = t1_undo
        t1.retried = t1_retry
        t1.save()

        self.step.tasks = [t1, t1_undo, t1_retry]
        self.assertEqual(self.step.status, celery_states.SUCCESS)


class test_progress(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        self.step = ProcessStep.objects.create()

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_no_steps_or_tasks(self):
        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 100)

    def test_nested_steps(self):
        depth = 5
        parent = self.step

        for i in range(depth):
            parent = ProcessStep.objects.create(parent_step=parent)

        with self.assertNumQueries(2*(depth+1)):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress(self):
        with self.assertNumQueries(2):
            self.step.progress

        with self.assertNumQueries(0):
            self.step.progress

    def test_cached_progress_nested_steps(self):
        depth = 5
        parent = self.step

        for i in range(depth):
            parent = ProcessStep.objects.create(parent_step=parent)

        self.step.progress

        with self.assertNumQueries(0):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_create_task(self):
        self.step.progress

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_add_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
        )

        self.step.progress
        self.step.add_tasks(t)

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_create_child_step(self):
        self.step.progress

        ProcessStep.objects.create(parent_step=self.step)

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_add_child_step(self):
        s = ProcessStep.objects.create()

        self.step.progress
        self.step.add_child_steps(s)

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_run_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        self.step.progress

        t.run()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_run_task_in_nested_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.progress

        t.run()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_undo_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={'foo': 123}, processstep=self.step
        )

        t.run()
        self.step.progress
        t.undo()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_retry_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        t.run()
        t.undo()
        self.step.progress
        t.retry()

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_run_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.progress
        s.run()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_undo_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        s.run()
        self.step.progress
        s.undo()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_retry_step(self):
        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        s.run()
        s.undo()
        self.step.progress
        s.retry()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_resume_step(self):
        test_dir = "test_dir"
        fname = os.path.join(test_dir, "foo.txt")

        try:
            os.mkdir(test_dir)
        except:
            pass

        s = ProcessStep.objects.create(parent_step=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=s, processstep_pos=1
        )
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=s, processstep_pos=2
        )

        with self.assertRaises(AssertionError):
            s.run().get()

        s.undo(only_failed=True)
        open(fname, 'a').close()
        s.retry()
        self.step.progress
        s.resume()

        try:
            shutil.rmtree(test_dir)
        except:
            pass

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_single_task(self):
        t = ProcessTask.objects.create(progress=0)
        self.step.add_tasks(t)

        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 0)

        self.step.clear_tasks()

        t = ProcessTask.objects.create(progress=50)
        self.step.add_tasks(t)
        self.assertEqual(self.step.progress, 50)

        self.step.clear_tasks()

        t = ProcessTask.objects.create(progress=100)
        self.step.add_tasks(t)
        self.assertEqual(self.step.progress, 100)

    def test_multiple_tasks(self):
        t1 = ProcessTask.objects.create(progress=25)
        t2 = ProcessTask.objects.create(progress=25)
        self.step.add_tasks(t1, t2)
        self.assertEqual(self.step.progress, 25)

        self.step.clear_tasks()

        t1 = ProcessTask.objects.create(progress=100)
        t2 = ProcessTask.objects.create(progress=50)
        self.step.add_tasks(t1, t2)
        self.assertEqual(self.step.progress, 75)

        self.step.clear_tasks()

        t1 = ProcessTask.objects.create(progress=100)
        t2 = ProcessTask.objects.create(progress=100)
        self.step.add_tasks(t1, t2)
        self.assertEqual(self.step.progress, 100)

    def test_undone_task(self):
        t = ProcessTask.objects.create(progress=50)
        t_undo = ProcessTask.objects.create(undo_type=True)
        t.undone = t_undo
        t.save()
        self.step.add_tasks(t)
        self.assertEqual(self.step.progress, 0)

    def test_single_child_step(self):
        s = ProcessStep.objects.create()
        self.step.child_steps = [s]
        self.assertEqual(self.step.progress, 100)

    def test_nested_task(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(progress=50)

        s.add_tasks(t)
        self.step.child_steps = [s]

        self.assertEqual(self.step.progress, 50)


class test_running_steps(TransactionTestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

    def test_serialized_step(self):
        t1_val = 123
        t2_val = 456
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": t2_val},
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": t3_val},
            processstep_pos=2,
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.save()
        step.run().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertEqual(t1.result, t1_val)
        self.assertEqual(t2.result, t2_val)
        self.assertEqual(t3.result, t3_val)

    def test_parallel_step(self):
        t1_val = 123
        t2_val = 456
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": t2_val},
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": t3_val},
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        step.run().get()
        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.SUCCESS)
        self.assertEqual(t3.status, celery_states.SUCCESS)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_chunked_step(self):
        EventType.objects.create(eventType=1)

        step = ProcessStep.objects.create(
            name="Test",
        )

        tasks = []
        n = 10
        for i in range(n):
            t = ProcessTask(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
                params={'foo': 'bar'},
                processstep=step,
            )
            tasks.append(t)

        ProcessTask.objects.bulk_create(tasks)

        with self.assertNumQueries(len(tasks) + 3):
            res = step.chunk()

        self.assertEqual(len(res), 10)

        for t in tasks:
            t.refresh_from_db()
            self.assertEqual(t.status, celery_states.SUCCESS)
            self.assertEqual(t.progress, 100)
            self.assertIsNotNone(t.time_started)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_chunked_empty_step(self):
        step = ProcessStep.objects.create(
            name="Test",
        )

        with self.assertNumQueries(1):
            res = step.chunk()

        self.assertEqual(res, [])

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_chunked_step_with_size(self):
        EventType.objects.create(eventType=1)

        step = ProcessStep.objects.create(
            name="Test",
        )

        tasks = []
        n = 10
        size = 2

        for i in range(n):
            t = ProcessTask(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
                params={'foo': 'bar'},
                processstep=step,
            )
            tasks.append(t)

        ProcessTask.objects.bulk_create(tasks)

        with self.assertNumQueries(len(tasks) + (n/size) + 2):
            step.chunk(size=size)

        for t in tasks:
            t.refresh_from_db()
            self.assertEqual(t.status, celery_states.SUCCESS)
            self.assertEqual(t.progress, 100)
            self.assertIsNotNone(t.time_started)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_chunked_step_with_failure(self):
        EventType.objects.create(eventType=1)

        step = ProcessStep.objects.create(
            name="Test",
        )

        t1 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={'foo': 'bar'},
            processstep=step,
        )
        t2 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={'bar': 'foo'},
            processstep=step,
        )
        t3 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={'foo': 'bar'},
            processstep=step,
        )

        tasks = [t1, t2, t3]

        ProcessTask.objects.bulk_create(tasks)

        with self.assertNumQueries(len(tasks) + 3):
            step.chunk()

        for t in tasks:
            t.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t1.progress, 100)
        self.assertIsNotNone(t1.time_started)

        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t2.progress, 0)
        self.assertIsNotNone(t2.time_started)

        self.assertEqual(t3.status, celery_states.PENDING)
        self.assertEqual(t3.progress, 0)
        self.assertIsNone(t3.time_started)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_chunked_step_with_events(self):
        EventType.objects.create(eventType=1)

        step = ProcessStep.objects.create(
            name="Test",
        )

        t1 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
            params={'foo': 'bar'},
            processstep=step,
        )
        t2 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
            params={'bar': 'foo'},
            processstep=step,
        )
        t3 = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
            params={'foo': 'bar'},
            processstep=step,
        )

        tasks = [t1, t2, t3]

        ProcessTask.objects.bulk_create(tasks)

        with self.assertNumQueries(len(tasks) + 4):
            step.chunk()

        for t in tasks:
            t.refresh_from_db()

        self.assertEqual(EventIP.objects.filter(eventOutcome=1).count(), 1)
        self.assertEqual(EventIP.objects.filter(eventOutcome=0).count(), 1)

    def test_child_steps(self):
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=3
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": 456}, processstep=step2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 789}, processstep=step3
        )

        main_step.run()

        steps = ProcessStep.objects.all()
        tasks = ProcessTask.objects.filter(status=celery_states.SUCCESS)

        self.assertTrue(all([s.status == celery_states.SUCCESS for s in steps]))
        self.assertEqual(steps.count(), 4)
        self.assertEqual(tasks.count(), 3)

    def test_failing_serialized_step(self):
        step = ProcessStep.objects.create(name="Test",)

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 1},
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            processstep_pos=1,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": 2},
            processstep_pos=2,
        )

        step.tasks = [t1, t2, t3]

        with self.assertRaises(Exception):
            step.run().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.FAILURE)

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.PENDING)

    def test_failing_parallel_step(self):
        step = ProcessStep.objects.create(name="Test", parallel=True)

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 1},
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            processstep_pos=1,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": 2},
            processstep_pos=2,
        )

        step.tasks = [t1, t2, t3]

        with self.assertRaises(Exception):
            step.run().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.FAILURE)

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

    def test_failing_with_child_steps(self):
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=3
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            params={"foo": 456}, processstep=step2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 789}, processstep=step3
        )

        with self.assertRaises(Exception):
            main_step.run()

        self.assertEqual(step1.status, celery_states.SUCCESS)
        self.assertEqual(step2.status, celery_states.FAILURE)
        self.assertEqual(step3.status, celery_states.PENDING)

    def test_result_params_step(self):
        t1_val = 1
        t2_val = 2
        t3_val = 3

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t1_val, "y": t1_val},
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t2_val},
            result_params={"y": t1.id},
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t3_val},
            result_params={"y": t1.id},
            processstep_pos=2,
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.save()

        step.run().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.result, t1_val*2)
        self.assertEqual(t2.result, t1.result + t2_val)
        self.assertEqual(t3.result, t1.result + t3_val)


@override_settings(CELERY_ALWAYS_EAGER=False)
class test_running_steps_eagerly(TransactionTestCase):

    def test_run(self):
        t1_val = 123
        t2_val = 456
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": t2_val},
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": t3_val},
            processstep_pos=2,
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.save()
        step.run()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertEqual(t1.result, t1_val)
        self.assertEqual(t2.result, t2_val)
        self.assertEqual(t3.result, t3_val)

    def test_result_params(self):
        t1_val = 1
        t2_val = 2
        t3_val = 3

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t1_val, "y": t1_val},
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t2_val},
            result_params={"y": t1.id},
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={"x": t3_val},
            result_params={"y": t1.id},
            processstep_pos=2,
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.save()

        step.run()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.result, t1_val*2)
        self.assertEqual(t2.result, t1.result + t2_val)
        self.assertEqual(t3.result, t1.result + t3_val)


class test_undoing_steps(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

    def test_undo_serialized_step(self):
        step = ProcessStep.objects.create(
            name="Test",
        )

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123},
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            processstep_pos=1,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(Exception):
            step.run().get()

        step.undo().get()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertTrue(t1.undone)
        self.assertTrue(t2.undone)

        t1_undo = ProcessTask.objects.filter(
            name=t1.name, undo_type=True,
            processstep=step
        )
        t2_undo = ProcessTask.objects.filter(
            name=t2.name, undo_type=True,
            processstep=step
        )

        self.assertTrue(t1_undo.exists())
        self.assertTrue(t2_undo.exists())

    def test_undo_only_failed_serialized_step(self):
        step = ProcessStep.objects.create(name="Test")

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123},
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            processstep_pos=1,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(Exception):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo(only_failed=True).get()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertFalse(t1.undone)
        self.assertTrue(t2.undone)

        t1_undo = ProcessTask.objects.filter(name=t1.name, undo_type=True)
        t2_undo = ProcessTask.objects.filter(
            name=t2.name, undo_type=True,
            processstep=step
        )

        self.assertFalse(t1_undo.exists())
        self.assertTrue(t2_undo.exists())

    def test_undo_parallel_step(self):
        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123},
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 456},
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(Exception):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

        self.assertTrue(t1.undone)
        self.assertTrue(t2.undone)
        self.assertTrue(t3.undone)

    def test_undo_only_failed_parallel_step(self):
        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123},
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 456},
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(Exception):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo(only_failed=True).get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

        self.assertFalse(t1.undone)
        self.assertTrue(t2.undone)
        self.assertFalse(t3.undone)

    def test_undo_with_child_steps(self):
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=3
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            processstep=step2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 789}, processstep=step3
        )

        with self.assertRaises(Exception):
            main_step.run()

        main_step.undo()

        self.assertEqual(step1.status, celery_states.SUCCESS)
        self.assertEqual(step2.status, celery_states.SUCCESS)
        self.assertEqual(step3.status, celery_states.SUCCESS)


class test_retrying_steps(TestCase):
    def setUp(self):
        self.test_dir = "test_dir"

        try:
            os.mkdir(self.test_dir)
        except:
            pass

        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

    def test_retry_failed_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": t2_val},
            processstep_pos=1,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        step.undo(only_failed=True).get()

        open(t2_val, 'a').close()

        step.retry().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertFalse(t1.retried)
        self.assertTrue(t2.retried)

        file_task = step.task_set().filter(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            status=celery_states.SUCCESS
        )

        self.assertTrue(file_task.exists())

    def test_retry_all_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": t2_val},
            processstep_pos=1,
            information_package=ip,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        step.undo().get()

        open(t2_val, 'a').close()

        step.retry().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertTrue(t1.retried)
        self.assertTrue(t2.retried)

        file_task = step.task_set().filter(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            status=celery_states.SUCCESS
        )

        self.assertTrue(file_task.exists())

        first_task = step.tasks.filter(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            status=celery_states.SUCCESS, undo_type=False
        )

        self.assertEqual(first_task.count(), 2)

    def test_retry_parallel_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": t2_val},
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": t3_val},
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo().get()

        open(t2_val, 'a').close()

        step.retry().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

        self.assertTrue(t1.undone)
        self.assertTrue(t2.undone)
        self.assertTrue(t3.undone)

        self.assertTrue(t1.retried)
        self.assertTrue(t2.retried)
        self.assertTrue(t3.retried)

    def test_retry_only_failed_parallel_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": t1_val},
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": t2_val},
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": t3_val},
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo(only_failed=True).get()

        open(t2_val, 'a').close()

        step.retry().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

        self.assertFalse(t1.undone)
        self.assertTrue(t2.undone)
        self.assertFalse(t3.undone)

        self.assertFalse(t1.retried)
        self.assertTrue(t2.retried)
        self.assertFalse(t3.retried)

    def test_retry_with_child_steps(self):
        fname = os.path.join(self.test_dir, "foo.txt")

        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=3
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Third",
            params={"foo": 789}, processstep=step3
        )

        with self.assertRaises(Exception):
            main_step.run()

        main_step.undo()

        open(fname, 'a').close()

        main_step.retry()

        self.assertEqual(step1.status, celery_states.SUCCESS)
        self.assertEqual(step2.status, celery_states.SUCCESS)
        self.assertEqual(step3.status, celery_states.SUCCESS)

    def test_retry_task_with_another_task_after(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        step = ProcessStep.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step, processstep_pos=1
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        with self.assertRaises(Exception):
            step.run()

        t1.undo()
        open(fname, 'a').close()
        t1.retry()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertTrue(t1.retried)
        self.assertFalse(t2.retried)
        self.assertEqual(step.status, celery_states.PENDING)

    def test_retry_step_with_failed_task_and_another_task_after(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        step = ProcessStep.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step, processstep_pos=1
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        with self.assertRaises(Exception):
            step.run()

        step.undo()
        open(fname, 'a').close()
        step.retry()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertEqual(step.status, celery_states.SUCCESS)
        self.assertTrue(t1.retried)
        self.assertTrue(t2.retried)

    def test_retry_step_with_another_step_after(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step2
        )

        with self.assertRaises(Exception):
            main_step.run()

        step1.undo()
        open(fname, 'a').close()
        step1.retry()

        self.assertEqual(main_step.status, celery_states.PENDING)


class test_resuming_steps(TestCase):
    def setUp(self):
        self.test_dir = "test_dir"

        try:
            os.mkdir(self.test_dir)
        except:
            pass

        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

    def test_resuming_task_after_retried_task(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        step = ProcessStep.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step, processstep_pos=1
        )

        t2 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        with self.assertRaises(Exception):
            step.run()

        t1.undo()
        open(fname, 'a').close()
        t1.retry()
        t2.run()

        self.assertEqual(step.status, celery_states.SUCCESS)

    def test_resuming_multiple_tasks_after_retried_task(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        step = ProcessStep.objects.create()

        t1 = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step, processstep_pos=1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": 123}, processstep=step, processstep_pos=3
        )

        with self.assertRaises(Exception):
            step.run()

        t1.undo()
        open(fname, 'a').close()
        t1.retry()
        step.resume()

        self.assertEqual(step.status, celery_states.SUCCESS)

    def test_resuming_step_after_retried_step(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step2
        )

        with self.assertRaises(Exception):
            main_step.run()

        step1.undo()
        open(fname, 'a').close()
        step1.retry()
        step2.run()

        self.assertEqual(main_step.status, celery_states.SUCCESS)

    def test_resuming_multiple_steps_after_retried_step(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent_step=main_step, parent_step_pos=3
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step2
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Second",
            params={"foo": 123}, processstep=step3
        )

        with self.assertRaises(Exception):
            main_step.run().get()

        step1.undo()
        open(fname, 'a').close()
        step1.retry()
        main_step.resume()

        self.assertEqual(main_step.status, celery_states.SUCCESS)
