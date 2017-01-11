import traceback

from celery import states as celery_states

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


class test_running_tasks(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

        self.user = User.objects.create(username="user1")

    def test_create_nonexistent_task(self):
        """
        Creates a task with a name that doesn't exist.
        """

        with self.assertRaises(ValidationError):
            task = ProcessTask(
                name="nonexistent task",
                responsible=self.user
            )

            task.full_clean()

    def test_create_existing_task(self):
        """
        Creates a task with a name that does exist.
        """

        task = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            responsible=self.user
        )

        task.full_clean()

    def test_run_with_wrong_params(self):
        """
        Runs a task with nonexistent parameters.
        """

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
                params={
                    "bar": 123
                },
                information_package=InformationPackage.objects.create()
            )

            task.run()

    def test_run_with_too_many_params(self):
        """
        Runs a task with too many parameters.
        """

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
                params={
                    "foo": 123,
                    "bar": 456
                },
                information_package=InformationPackage.objects.create()
            )

            task.run()

    def test_on_success(self):
        """
        Runs a correct task and checks if the result is saved and that the
        traceback is empty.
        """

        foo = 123

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={
                "foo": foo
            },
            information_package=InformationPackage.objects.create()
        )

        task.run()
        self.assertIsNone(task.traceback)
        self.assertEqual(foo, task.result)

    def test_on_failure(self):
        """
        Runs an incorrect task and checks if the result is empty and that the
        traceback is nonempty.
        """

        foo = 123
        try:
            task = ProcessTask(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
                params={
                    "bar": foo
                },
                information_package=InformationPackage.objects.create()
            )
            task.run()
        except TypeError:
            tb = traceback.format_exc()
            self.assertEqual(tb, task.traceback)
            self.assertIsNone(task.result)
            self.assertIsNotNone(task.traceback)

    def test_running_non_eagerly(self):
        settings.CELERY_ALWAYS_EAGER = False
        foo = 123

        task = ProcessTask(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": foo}
        )

        res = task.run().get().get(task.pk)
        self.assertEqual(res, foo)


class test_undoing_tasks(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    def test_undo_successful_task(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'x': x, 'y': y}
        )

        task.run()
        self.assertEqual(task.status, celery_states.SUCCESS)

        res = task.undo()
        self.assertEqual(res.get(), x-y)
        self.assertTrue(task.undone)
        self.assertFalse(task.undo_type)
        self.assertFalse(task.retried)

        self.assertEqual(task.status, celery_states.SUCCESS)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Add undo")
        self.assertIsNotNone(undo_task)
        self.assertTrue(undo_task.undo_type)

    def test_undo_failed_task(self):
        task = ProcessTask.objects.create(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail")

        with self.assertRaises(Exception):
            task.run()

        self.assertEqual(task.status, celery_states.FAILURE)

        task.undo()
        self.assertTrue(task.undone)
        self.assertFalse(task.undo_type)
        self.assertFalse(task.retried)
        self.assertEqual(task.status, celery_states.FAILURE)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail undo")
        self.assertIsNotNone(undo_task)
        self.assertTrue(undo_task.undo_type)
