from celery import states as celery_states
from django.conf import settings
from django.test import TestCase

from ESSArch_Core.ip.models import InformationPackage

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep, ProcessTask,
)

import os
import shutil


class test_status(TestCase):
    def setUp(self):
        self.step = ProcessStep.objects.create()

    def test_no_steps_or_tasks(self):
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
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS, undone=True)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)

        self.step.tasks = [t1, t1_undo]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_succeeded_retried_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.SUCCESS, undone=True)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)
        t1_retry = ProcessTask.objects.create(status=celery_states.SUCCESS)

        self.step.tasks = [t1, t1_undo, t1_retry]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_undone_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE, undone=True)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)

        self.step.tasks = [t1, t1_undo]
        self.assertEqual(self.step.status, celery_states.SUCCESS)

    def test_failed_retried_task(self):
        t1 = ProcessTask.objects.create(status=celery_states.FAILURE, undone=True, retried=True)
        t1_undo = ProcessTask.objects.create(status=celery_states.SUCCESS, undo_type=True)
        t1_retry = ProcessTask.objects.create(status=celery_states.SUCCESS)

        self.step.tasks = [t1, t1_undo, t1_retry]
        self.assertEqual(self.step.status, celery_states.SUCCESS)


class test_running_steps(TestCase):
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

        res = step.run().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertEqual(res.get(t1.id), t1_val)
        self.assertEqual(res.get(t2.id), t2_val)
        self.assertEqual(res.get(t3.id), t3_val)

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

        res = step.run().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()

        self.assertEqual(res.get(t1.id), t1_val*2)
        self.assertEqual(res.get(t2.id), res.get(t1.id) + t2_val)
        self.assertEqual(res.get(t3.id), res.get(t1.id) + t3_val)


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
            name=t1.name + " undo", undo_type=True,
            processstep=step
        )
        t2_undo = ProcessTask.objects.filter(
            name=t2.name + " undo", undo_type=True,
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

        t1_undo = ProcessTask.objects.filter(name=t1.name + " undo")
        t2_undo = ProcessTask.objects.filter(
            name=t2.name + " undo", undo_type=True,
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
            status=celery_states.SUCCESS
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

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        with self.assertRaises(Exception):
            step.run()

        t1.undo()
        open(fname, 'a').close()
        t1.retry()

        self.assertEqual(step.status, celery_states.PENDING)

    def test_retry_step_with_failed_task_and_another_task_after(self):
        fname = os.path.join(self.test_dir, "foo.txt")
        step = ProcessStep.objects.create()

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}, processstep=step, processstep_pos=1
        )

        ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": 123}, processstep=step, processstep_pos=2
        )

        with self.assertRaises(Exception):
            step.run()

        step.undo()
        open(fname, 'a').close()
        step.retry()

        self.assertEqual(step.status, celery_states.SUCCESS)

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
