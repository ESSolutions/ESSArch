from celery import states as celery_states
from django.conf import settings
from django.test import TestCase

from configuration.models import (
    EventType,
    Path,
)

from ip.models import InformationPackage

from preingest.models import (
    ProcessStep, ProcessTask,
)

import os
import shutil

class test_running_steps(TestCase):
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

    def test_serialized_step(self):
        t1_val = 123
        t2_val = 456
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Second",
            params={
                "foo": t2_val,
            },
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
            processstep_pos=2,
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.save()

        res = step.run().get()

        self.assertEqual(step.status, celery_states.SUCCESS)

        self.assertTrue(t1.id in res)
        self.assertTrue(t2.id in res)
        self.assertTrue(t3.id in res)

        self.assertEqual(res[t1.id], t1_val)
        self.assertEqual(res[t2.id], t2_val)
        self.assertEqual(res[t3.id], t3_val)

    def test_result_params_step(self):
        t1_val = 1
        t2_val = 2
        t3_val = 3

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Add",
            params={
                "x": t1_val,
                "y": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Add",
            params={
                "x": t2_val
            },
            result_params={
                "y": t1.id
            },
            processstep_pos=1,
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Add",
            params={
                "x": t3_val,
            },
            result_params={
                "y": t1.id
            },
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

        self.assertTrue(t1.id in res)
        self.assertTrue(t2.id in res)
        self.assertTrue(t3.id in res)

        self.assertEqual(res[t1.id], t1_val*2)
        self.assertEqual(res[t2.id], res[t1.id] + t2_val)
        self.assertEqual(res[t3.id], res[t1.id] + t3_val)

    def test_undo_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            processstep_pos=1,
            information_package=ip,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo().get()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertIsNone(t1.traceback)
        self.assertIsNotNone(t2.traceback)

        self.assertTrue(t1.undone)
        self.assertTrue(t2.undone)

        task_names = step.tasks.values_list("name", flat=True)

        self.assertIn("%s undo" % t1.name, task_names)
        self.assertIn("%s undo" % t2.name, task_names)

    def test_undo_only_failed_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            processstep_pos=1,
            information_package=ip,
        )

        step.tasks = [t1, t2]
        step.save()

        with self.assertRaises(AssertionError):
            step.run().get()

        self.assertEqual(step.status, celery_states.FAILURE)

        step.undo(only_failed=True).get()

        t1.refresh_from_db()
        t2.refresh_from_db()

        self.assertIsNone(t1.traceback)
        self.assertIsNotNone(t2.traceback)

        self.assertFalse(t1.undone)
        self.assertTrue(t2.undone)

        task_names = step.tasks.values_list("name", flat=True)

        self.assertNotIn("%s undo" % t1.name, task_names)
        self.assertIn("%s undo" % t2.name, task_names)

    def test_retry_failed_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            processstep_pos=1,
            information_package=ip,
        )

        step.tasks = [t1, t2]
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

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertFalse(t1.retried)
        self.assertTrue(t2.retried)

        file_task = step.task_set().filter(
            name="preingest.tests.tasks.FailIfFileNotExists",
            status=celery_states.SUCCESS
        )

        self.assertTrue(file_task.exists())
        self.assertEqual(file_task.first().status, celery_states.SUCCESS)

    def test_retry_all_serialized_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            processstep_pos=0,
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            processstep_pos=1,
            information_package=ip,
        )

        step.tasks = [t1, t2]
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

        self.assertEqual(t1.status, celery_states.SUCCESS)
        self.assertEqual(t2.status, celery_states.FAILURE)
        self.assertTrue(t1.retried)
        self.assertTrue(t2.retried)

        file_task = step.task_set().filter(
            name="preingest.tests.tasks.FailIfFileNotExists",
            status=celery_states.SUCCESS
        )

        self.assertTrue(file_task.exists())
        self.assertEqual(file_task.first().status, celery_states.SUCCESS)

        first_task = step.tasks.filter(
            name="preingest.tests.tasks.First undo",
        )

        self.assertTrue(first_task.exists())

    def test_parallel_step(self):
        t1_val = 123
        t2_val = 456
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Second",
            params={
                "foo": t2_val,
            },
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
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

    def test_undo_parallel_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(AssertionError):
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
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
            information_package=ip,
        )

        step.tasks = [t1, t2, t3]
        step.parallel = True
        step.save()

        with self.assertRaises(AssertionError):
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

    def test_retry_parallel_step(self):
        t1_val = 123
        t2_val = os.path.join(self.test_dir, "foo.txt")
        t3_val = 789

        step = ProcessStep.objects.create(
            name="Test",
        )

        ip = InformationPackage.objects.create()

        t1 = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
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
            name="preingest.tests.tasks.First",
            params={
                "foo": t1_val,
            },
            information_package=ip,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tests.tasks.FailIfFileNotExists",
            params={
                "filename": t2_val,
            },
            information_package=ip,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tests.tasks.Third",
            params={
                "foo": t3_val,
            },
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
