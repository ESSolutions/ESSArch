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

import os
import shutil
import tempfile

from celery import states as celery_states
from django.test import TestCase, TransactionTestCase
from django_redis import get_redis_connection

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.util import create_workflow


class test_status(TestCase):
    def setUp(self):
        self.step = ProcessStep.objects.create()

        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_no_steps_or_tasks(self):
        with self.assertNumQueries(2):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_nested_steps(self):
        depth = 5
        parent = self.step

        for _ in range(depth):
            parent = ProcessStep.objects.create(parent=parent)

        with self.assertNumQueries((7 * depth) + 2):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status(self):
        with self.assertNumQueries(2):
            self.step.status

        with self.assertNumQueries(0):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_nested_steps(self):
        depth = 5
        parent = self.step

        for _ in range(depth):
            parent = ProcessStep.objects.create(parent=parent)

        self.step.status

        with self.assertNumQueries(0):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_create_task(self):
        self.step.status

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        with self.assertNumQueries(8):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_add_task(self):

        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
        )

        self.step.status
        self.step.add_tasks(t)

        with self.assertNumQueries(8):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_create_child_step(self):
        self.step.status

        ProcessStep.objects.create(parent=self.step)

        with self.assertNumQueries(9):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_add_child_step(self):
        s = ProcessStep.objects.create()

        self.step.status
        self.step.add_child_steps(s)

        with self.assertNumQueries(9):
            self.assertEqual(self.step.status, celery_states.PENDING)

    def test_cached_status_run_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        self.step.status

        t.run()

        with self.assertNumQueries(8):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_run_task_in_nested_step(self):
        s = ProcessStep.objects.create(parent=self.step)
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.status

        t.run()

        with self.assertNumQueries(15):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_cached_status_run_step(self):
        s = ProcessStep.objects.create(parent=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.status
        s.run()

        with self.assertNumQueries(15):
            self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_pending_task(self):
        t = ProcessTask.objects.create(status=celery_states.PENDING)
        self.step.tasks.set([t])
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_pending_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.PENDING)

        s.tasks.set([t])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_pending_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.PENDING)
        t2 = ProcessTask.objects.create(status=celery_states.PENDING)

        s.tasks.set([t1])
        self.step.tasks.set([t2])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.PENDING)

    def test_started_task(self):
        t = ProcessTask.objects.create(status=celery_states.STARTED)
        self.step.tasks.set([t])
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_started_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.STARTED)

        s.tasks.set([t])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_started_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.STARTED)
        t2 = ProcessTask.objects.create(status=celery_states.STARTED)

        s.tasks.set([t1])
        self.step.tasks.set([t2])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_succeeded_task(self):
        t = ProcessTask.objects.create(status=celery_states.SUCCESS)
        self.step.tasks.set([t])
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.SUCCESS)

        s.tasks.set([t])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.SUCCESS)

        s.tasks.set([t1])
        self.step.tasks.set([t2])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_task(self):
        t = ProcessTask.objects.create(status=celery_states.FAILURE)
        self.step.tasks.set([t])
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_child_step(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(status=celery_states.FAILURE)

        s.tasks.set([t])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_child_step_and_task(self):
        s = ProcessStep.objects.create()
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)

        s.tasks.set([t1])
        self.step.tasks.set([t2])
        self.step.child_steps.set([s])
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_failed_task_after_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)

        self.step.tasks.set([t1, t2])
        self.assertEqual(self.step.status, celery_states.FAILURE)

    def test_started_task_after_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.STARTED)

        self.step.tasks.set([t1, t2])
        self.assertEqual(self.step.status, celery_states.STARTED)

    def test_failed_task_between_succeeded(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS)
        t2 = ProcessTask.objects.create(status=celery_states.FAILURE)
        t3 = ProcessTask.objects.create(status=celery_states.SUCCESS)

        self.step.tasks.set([t1, t2, t3])
        self.assertEqual(self.step.status, celery_states.FAILURE)


class test_progress(TestCase):
    def setUp(self):
        self.step = ProcessStep.objects.create()

        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def tearDown(self):
        get_redis_connection("default").flushall()

    def test_no_steps_or_tasks(self):
        with self.assertNumQueries(2):
            self.assertEqual(self.step.progress, 0)

    def test_nested_steps(self):
        depth = 5
        parent = self.step

        for _ in range(depth):
            parent = ProcessStep.objects.create(parent=parent)

        with self.assertNumQueries((3 * (depth + 1)) - 1):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress(self):
        with self.assertNumQueries(2):
            self.step.progress

        with self.assertNumQueries(0):
            self.step.progress

    def test_cached_progress_nested_steps(self):
        depth = 5
        parent = self.step

        for _ in range(depth):
            parent = ProcessStep.objects.create(parent=parent)

        self.step.progress

        with self.assertNumQueries(0):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_create_task(self):
        self.step.progress

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_add_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
        )

        self.step.progress
        self.step.add_tasks(t)

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_create_child_step(self):
        self.step.progress

        ProcessStep.objects.create(parent=self.step)

        with self.assertNumQueries(5):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_add_child_step(self):
        s = ProcessStep.objects.create()

        self.step.progress
        self.step.add_child_steps(s)

        with self.assertNumQueries(5):
            self.assertEqual(self.step.progress, 0)

    def test_cached_progress_run_task(self):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=self.step
        )

        self.step.progress

        t.run()

        with self.assertNumQueries(4):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_run_task_in_nested_step(self):
        s = ProcessStep.objects.create(parent=self.step)
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.progress

        t.run()

        with self.assertNumQueries(7):
            self.assertEqual(self.step.progress, 100)

    def test_cached_progress_run_step(self):
        s = ProcessStep.objects.create(parent=self.step)
        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            processstep=s
        )

        self.step.progress
        s.run()

        with self.assertNumQueries(7):
            self.assertEqual(self.step.progress, 100)

    def test_single_task(self):
        t = ProcessTask.objects.create(progress=0)
        self.step.add_tasks(t)

        with self.assertNumQueries(4):
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

    def test_single_child_step(self):
        s = ProcessStep.objects.create()
        self.step.child_steps.set([s])
        self.assertEqual(self.step.progress, 0)

    def test_nested_task(self):
        s = ProcessStep.objects.create()
        t = ProcessTask.objects.create(progress=50)

        s.add_tasks(t)
        self.step.child_steps.set([s])

        self.assertEqual(self.step.progress, 50)


class test_running_steps(TransactionTestCase):
    def setUp(self):
        Path.objects.create(entity='temp', value='temp')

    @TaskRunner()
    def test_empty_step(self):
        step = ProcessStep.objects.create()
        self.assertEqual(len(step.run().get()), 0)

    @TaskRunner()
    def test_task_with_args_in_step(self):
        x = 5
        y = 10

        step = ProcessStep.objects.create(
            name="Test",
        )

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[x, y],
            processstep=step
        )

        step.run().get()
        task.refresh_from_db()

        self.assertEqual(task.result, x + y)

    @TaskRunner()
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

        step.tasks.set([t1, t2, t3])
        step.save()
        step.run().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertEqual(t1.result, t1_val)
        self.assertEqual(t2.result, t2_val)
        self.assertEqual(t3.result, t3_val)

    @TaskRunner()
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

        step.tasks.set([t1, t2, t3])
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

    @TaskRunner()
    def test_child_steps(self):
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent=main_step, parent_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent=main_step, parent_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent=main_step, parent_pos=3
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

    @TaskRunner()
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

        step.tasks.set([t1, t2, t3])

        with self.assertRaises(ValueError):
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

        step.tasks.set([t1, t2, t3])

        with self.assertRaises(ValueError):
            step.run().get()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.FAILURE)

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertEqual(t3.status, celery_states.SUCCESS)

    @TaskRunner()
    def test_failing_with_child_steps(self):
        main_step = ProcessStep.objects.create()
        step1 = ProcessStep.objects.create(
            parent=main_step, parent_pos=1
        )
        step2 = ProcessStep.objects.create(
            parent=main_step, parent_pos=2
        )
        step3 = ProcessStep.objects.create(
            parent=main_step, parent_pos=3
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

    @TaskRunner()
    def test_references(self):
        workflow = [
            {
                "name": "ESSArch_Core.WorkflowEngine.tests.tasks.Add",
                "reference": "first",
                "args": [1, 2],
            },
            {
                "name": "ESSArch_Core.WorkflowEngine.tests.tasks.Add",
                "reference": "second",
                "args": [3, 4],
            },
            {
                "name": "ESSArch_Core.WorkflowEngine.tests.tasks.Add",
                "result_params": {
                    'x': 'first',
                    'y': 'second',
                },
            },
        ]
        w = create_workflow(workflow)
        result = w.run().get()
        self.assertEqual(result, 10)


class test_running_steps_eagerly(TransactionTestCase):
    def setUp(self):
        Path.objects.create(entity='temp', value='temp')

    @TaskRunner()
    def test_empty_step(self):
        step = ProcessStep.objects.create()
        self.assertEqual(len(step.run().get()), 0)

    @TaskRunner()
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

        step.tasks.set([t1, t2, t3])
        step.save()
        step.run()

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertEqual(t1.result, t1_val)
        self.assertEqual(t2.result, t2_val)
        self.assertEqual(t3.result, t3_val)


class test_retrying_steps(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='temp', value='temp')

    def setUp(self):
        self.test_dir = "test_dir"

        try:
            os.mkdir(self.test_dir)
        except Exception:
            pass

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_step(self):
        step = ProcessStep.objects.create()
        self.assertEqual(len(step.retry().get()), 0)

    def test_empty_nested_child_step(self):
        main_step = ProcessStep.objects.create()
        ProcessStep.objects.create(parent=main_step)

        self.assertEqual(len(main_step.retry().get()), 0)


class test_resuming_steps(TestCase):
    def setUp(self):
        self.test_dir = "test_dir"

        try:
            os.mkdir(self.test_dir)
        except Exception:
            pass

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_step(self):
        step = ProcessStep.objects.create()
        self.assertEqual(len(step.resume().get()), 0)
